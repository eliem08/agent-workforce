"""Operating commands: the agent system of record against a persistent store (also served by the web app)."""

import json
import os
from dataclasses import asdict
from datetime import date

from .core import ONBOARDING, Worker, Workforce

OPS = ("hire", "checklist", "credential", "activate", "spend", "monthly-review", "offboard", "roster", "report")


def load(path: str) -> Workforce:
    wf = Workforce()
    try:
        with open(path, encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except FileNotFoundError:
        return wf
    if not isinstance(doc, dict) or not isinstance(doc.get("workers"), dict):
        raise ValueError(f"{path}: not an agent-workforce store")
    for k, v in doc["workers"].items():
        v["start"] = date.fromisoformat(v["start"])
        wf.workers[k] = Worker(**v)
    return wf


def save(wf: Workforce, path: str):
    doc = {"workers": {k: {**asdict(w), "start": w.start.isoformat()} for k, w in wf.workers.items()}}
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
    os.replace(tmp, path)


def _month(text: str | None) -> str:
    text = text or date.today().strftime("%Y-%m")
    try:
        date.fromisoformat(f"{text}-01")
    except ValueError:
        raise ValueError(f"{text!r} is not a month like 2026-11") from None
    return text


def add_ops(sub):
    store = os.environ.get("AGENT_WORKFORCE_STORE", "workforce.json")
    p = sub.add_parser("hire", help="open a record for a new agent and start its onboarding checklist")
    p.add_argument("agent_id")
    p.add_argument("--role", required=True)
    p.add_argument("--manager", required=True, help="the person accountable for this agent")
    p.add_argument("--cost-center", required=True)
    p.add_argument("--monthly-budget", type=float, required=True)
    p.add_argument("--template", choices=sorted(ONBOARDING), default="default")
    p.add_argument("--start", help="YYYY-MM-DD, default today")
    p = sub.add_parser("checklist", help="show the onboarding checklist, or tick an item with --done")
    p.add_argument("agent_id")
    p.add_argument("--done", action="append", default=[], help="item completed (repeatable)")
    p = sub.add_parser("credential", help="record a credential the agent holds, so offboarding can revoke it")
    p.add_argument("agent_id")
    p.add_argument("credential", help="a name or reference, never the secret itself")
    sub.add_parser("activate", help="move a fully onboarded agent to probation").add_argument("agent_id")
    p = sub.add_parser("spend", help="record what an agent cost in a month")
    p.add_argument("agent_id")
    p.add_argument("cost", type=float)
    p.add_argument("--month", help="YYYY-MM, default this month")
    p = sub.add_parser("monthly-review", help="score the month and apply the outcome (keep, PIP, suspend)")
    p.add_argument("agent_id")
    p.add_argument("--tasks", type=float, required=True)
    p.add_argument("--successes", type=float, required=True)
    p.add_argument("--cost", type=float, default=0)
    p.add_argument("--escalations", type=float, default=0)
    p.add_argument("--incidents", type=float, default=0)
    p.add_argument("--target-cost-per-task", type=float, default=1.0)
    p.add_argument("--month", help="YYYY-MM, default this month")
    p = sub.add_parser("offboard", help="retire an agent: prints exactly what to revoke and hand over")
    p.add_argument("agent_id")
    p.add_argument("--reason", required=True)
    sub.add_parser("roster", help="every agent, its status and manager")
    sub.add_parser("report", help="headcount, spend and budget by cost centre").add_argument("--month")
    for name in OPS:
        sub.choices[name].add_argument("--store", default=store)


def run_ops(a) -> int:
    try:
        wf = load(a.store)
        agent = getattr(a, "agent_id", None)
        if agent is not None and a.cmd != "hire" and agent not in wf.workers:
            raise ValueError(f"no agent {agent!r}; see `roster`")
        _run(wf, a)
        save(wf, a.store)
        return 0
    except (ValueError, KeyError) as e:
        print(f"refused: {e.args[0] if e.args else e}")
        return 1


def _run(wf: Workforce, a):
    c = a.cmd
    if c == "hire":
        start = date.fromisoformat(a.start) if a.start else date.today()
        w = wf.hire(a.agent_id, a.role, a.manager, a.cost_center, a.monthly_budget, start, a.template)
        print(f"hired {w.agent_id} as {w.role}; onboarding has {len(w.checklist)} steps (see `checklist`)")
    elif c == "checklist":
        for item in a.done:
            wf.complete(a.agent_id, item)
        w = wf.workers[a.agent_id]
        for item, done in w.checklist.items():
            print(f"  [{'x' if done else ' '}] {item}")
        left = sum(not d for d in w.checklist.values())
        print(f"{left} left" if left else "complete: run `activate`")
    elif c == "credential":
        wf.grant_credential(a.agent_id, a.credential)
        print(f"{a.agent_id} holds {len(wf.workers[a.agent_id].credentials)} credential(s)")
    elif c == "activate":
        wf.activate(a.agent_id)
        print(f"{a.agent_id} is on probation")
    elif c == "spend":
        month = _month(a.month)
        wf.record_spend(a.agent_id, month, a.cost)
        w = wf.workers[a.agent_id]
        over = "  OVER BUDGET" if w.spend[month] > w.monthly_budget else ""
        print(f"{a.agent_id} {month}: ${w.spend[month]:,.2f} of ${w.monthly_budget:,.2f}{over}")
    elif c == "monthly-review":
        metrics = {k: getattr(a, k) for k in ("tasks", "successes", "cost", "escalations", "incidents")}
        metrics["target_cost_per_task"] = a.target_cost_per_task
        r = wf.monthly_review(a.agent_id, metrics, _month(a.month))
        print(f"{a.agent_id} {r['period']}: {r['rating']} (score {r['score']}) -> {r['action']}")
        print(
            f"  success {r['success_rate']:.0%}, ${r['cost_per_task']:.2f}/task, escalations {r['escalation_rate']:.0%}"
        )
        print(f"  status is now {wf.workers[a.agent_id].status}")
    elif c == "offboard":
        plan = wf.offboard(a.agent_id, a.reason)
        print(f"offboarded {a.agent_id}: {a.reason}")
        print(f"  revoke: {', '.join(plan['revoke']) or 'nothing recorded'}")
        print(f"  hand over to: {plan['transfer_to']}")
        print(f"  archive: {', '.join(plan['archive'])}")
        print(f"  lifetime cost ${plan['lifetime_cost']:,.2f} over {plan['reviews']} review(s)")
    elif c == "roster":
        for w in wf.workers.values():
            print(f"{w.agent_id:<20}{w.status:<12}{w.role:<20}{w.manager:<14}{w.cost_center}")
        if not wf.workers:
            print("no agents yet")
    else:
        month = _month(a.month)
        rows = wf.report(month)
        for cc, r in sorted(rows.items()):
            over = f"  over: {', '.join(r['over_budget'])}" if r["over_budget"] else ""
            print(f"{cc:<16}{r['headcount']:>3} agents  ${r['spend']:>10,.2f} of ${r['budget']:>10,.2f}{over}")
        if not rows:
            print(f"no active agents in {month}")
