"""Bulk import from CSV: agents (from an inventory or HR sheet), monthly spend (from a billing export) and credentials.

Every row is checked before anything changes; one bad row refuses the whole file and names its line.
Imports can be re-run safely: existing agents are updated rather than duplicated, spend sets the month's total
for each agent (so the same billing export imported twice is not counted twice), and credentials already on
record are skipped.
"""

from __future__ import annotations

import csv
import math
from datetime import date

from .core import ONBOARDING, Workforce

KINDS = ("agents", "spend", "credentials")
COLUMNS = {
    "agents": ("agent_id", "role", "manager", "cost_center", "monthly_budget"),
    "spend": ("agent_id", "month", "cost"),
    "credentials": ("agent_id", "credential"),
}


def _rows(path: str, kind: str) -> list[tuple[int, dict]]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = [(h or "").strip().lower().replace(" ", "_").replace("-", "_") for h in reader.fieldnames or []]
        missing = [c for c in COLUMNS[kind] if c not in header]
        if missing:
            raise ValueError(f"{path}: missing column(s) {missing}; {kind} needs {list(COLUMNS[kind])}")
        out = []
        for n, raw in enumerate(reader, 2):
            row = {h: (v or "").strip() for h, v in zip(header, raw.values())}
            if any(row.values()):
                out.append((n, row))
    if not out:
        raise ValueError(f"{path}: no rows")
    return out


def _money(where: str, v: str) -> float:
    try:
        x = float(v.replace(",", "").replace("$", ""))
    except ValueError:
        raise ValueError(f"{where}: {v!r} is not an amount") from None
    if not (math.isfinite(x) and x >= 0):
        raise ValueError(f"{where}: amount must be >= 0")
    return x


def import_csv(wf: Workforce, kind: str, path: str) -> dict:
    """Apply the file to wf. Returns counts; raises ValueError (and changes nothing) on any bad row."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    rows = _rows(path, kind)
    plan, seen = [], set()
    for n, r in rows:
        where = f"{path} line {n}"
        aid = r["agent_id"]
        if not aid:
            raise ValueError(f"{where}: agent_id is empty")
        if kind == "agents":
            if aid in seen:
                raise ValueError(f"{where}: {aid} appears twice")
            seen.add(aid)
            for col in ("role", "manager", "cost_center"):
                if not r[col]:
                    raise ValueError(f"{where}: {col} is empty")
            budget = _money(where, r["monthly_budget"])
            template = r.get("template") or "default"
            if template not in ONBOARDING:
                raise ValueError(f"{where}: template must be one of {sorted(ONBOARDING)}")
            try:
                start = date.fromisoformat(r["start"]) if r.get("start") else date.today()
            except ValueError:
                raise ValueError(f"{where}: start {r['start']!r} is not a date like 2026-11-01") from None
            plan.append((aid, r["role"], r["manager"], r["cost_center"], budget, start, template))
        else:
            known = aid in wf.workers or aid in {p[0] for p in plan}
            if not known:
                raise ValueError(f"{where}: no agent {aid!r}; import agents first")
            if kind == "spend":
                month = r["month"][:7]
                try:
                    date.fromisoformat(f"{month}-01")
                except ValueError:
                    raise ValueError(f"{where}: month {r['month']!r} is not like 2026-11") from None
                plan.append((aid, month, _money(where, r["cost"])))
            else:
                if not r["credential"]:
                    raise ValueError(f"{where}: credential is empty")
                if wf.workers[aid].status == "offboarded":
                    raise ValueError(f"{where}: {aid} is offboarded")
                plan.append((aid, r["credential"]))
    counts = {"added": 0, "updated": 0, "skipped": 0}
    if kind == "agents":
        for aid, role, manager, cc, budget, start, template in plan:
            if aid in wf.workers:
                w = wf.workers[aid]
                changed = (w.role, w.manager, w.cost_center, w.monthly_budget) != (role, manager, cc, budget)
                w.role, w.manager, w.cost_center, w.monthly_budget = role, manager, cc, budget
                counts["updated" if changed else "skipped"] += 1
            else:
                wf.hire(aid, role, manager, cc, budget, start, template)
                counts["added"] += 1
    elif kind == "spend":
        totals: dict[tuple[str, str], float] = {}
        for aid, month, cost in plan:  # several lines for one agent and month add up within the file
            totals[(aid, month)] = totals.get((aid, month), 0.0) + cost
        for (aid, month), total in totals.items():
            w = wf.workers[aid]
            counts["updated" if month in w.spend else "added"] += 1
            w.spend[month] = round(total, 2)
    else:
        for aid, cred in plan:
            if cred in wf.workers[aid].credentials:
                counts["skipped"] += 1
            else:
                wf.grant_credential(aid, cred)
                counts["added"] += 1
    return counts
