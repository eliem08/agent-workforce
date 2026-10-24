"""System of record for AI agents: onboarding, reviews, offboarding and reporting."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

__all__ = ["Worker", "Workforce", "ONBOARDING", "review"]

ONBOARDING = {
    "default": ["identity_created", "scopes_granted", "budget_set", "runbook_linked", "escalation_contact", "eval_suite_passed"],
    "finance": ["identity_created", "scopes_granted", "budget_set", "runbook_linked", "escalation_contact", "eval_suite_passed",
                "dual_approval_configured", "audit_log_enabled"],
}


@dataclass
class Worker:
    agent_id: str
    role: str
    manager: str
    cost_center: str
    monthly_budget: float
    start: date
    status: str = "onboarding"
    checklist: dict = field(default_factory=dict)
    credentials: list = field(default_factory=list)
    artifacts: list = field(default_factory=list)
    spend: dict = field(default_factory=dict)  # "YYYY-MM" -> cost
    reviews: list = field(default_factory=list)


def review(metrics: dict) -> dict:
    """metrics: tasks, successes, cost, escalations, incidents (critical incidents)."""
    tasks = max(metrics.get("tasks", 0), 1)
    success = metrics.get("successes", 0) / tasks
    cost_per_task = metrics.get("cost", 0) / tasks
    esc_rate = metrics.get("escalations", 0) / tasks
    incidents = metrics.get("incidents", 0)
    target_cpt = metrics.get("target_cost_per_task", 1.0)
    score = 100 * success - 40 * esc_rate - 15 * max(0, cost_per_task / target_cpt - 1) - 25 * incidents
    if incidents >= 2 or success < 0.6:
        rating, action = "unacceptable", "offboard"
    elif score >= 92:
        rating, action = "exceeds", "expand_scope"
    elif score >= 82:
        rating, action = "meets", "keep"
    else:
        rating, action = "below", "pip"
    return {"score": round(score, 1), "rating": rating, "action": action, "success_rate": round(success, 3),
            "cost_per_task": round(cost_per_task, 3), "escalation_rate": round(esc_rate, 3)}


class Workforce:
    def __init__(self):
        self.workers: dict[str, Worker] = {}

    def hire(self, agent_id, role, manager, cost_center, monthly_budget, start: date, template="default") -> Worker:
        w = Worker(agent_id, role, manager, cost_center, monthly_budget, start)
        w.checklist = {item: False for item in ONBOARDING[template]}
        self.workers[agent_id] = w
        return w

    def complete(self, agent_id, item):
        w = self.workers[agent_id]
        if item not in w.checklist:
            raise KeyError(f"{item} not in checklist")
        w.checklist[item] = True

    def activate(self, agent_id):
        w = self.workers[agent_id]
        missing = [k for k, done in w.checklist.items() if not done]
        if missing:
            raise ValueError(f"onboarding incomplete: {missing}")
        w.status = "probation"

    def record_spend(self, agent_id, month: str, cost: float):
        w = self.workers[agent_id]
        w.spend[month] = w.spend.get(month, 0) + cost

    def monthly_review(self, agent_id, metrics: dict, period: str) -> dict:
        w = self.workers[agent_id]
        if w.status in ("onboarding", "offboarded"):
            raise ValueError(f"cannot review agent in status {w.status}")
        r = review(metrics)
        r["period"] = period
        w.reviews.append(r)
        if r["action"] == "pip":
            w.status = "pip"
        elif r["action"] in ("keep", "expand_scope"):
            w.status = "active"
        return r

    def offboard(self, agent_id, reason: str) -> dict:
        w = self.workers[agent_id]
        plan = {
            "agent": agent_id,
            "reason": reason,
            "revoke": list(w.credentials),
            "transfer_to": w.manager,
            "artifacts": list(w.artifacts),
            "archive": [f"logs/{agent_id}/", f"traces/{agent_id}/"],
            "lifetime_cost": round(sum(w.spend.values()), 2),
            "reviews": len(w.reviews),
        }
        w.status, w.credentials = "offboarded", []
        return plan

    def report(self, month: str) -> dict:
        by_cc = defaultdict(lambda: {"headcount": 0, "spend": 0.0, "budget": 0.0, "over_budget": []})
        for w in self.workers.values():
            if w.status == "offboarded":
                continue
            cc = by_cc[w.cost_center]
            cc["headcount"] += 1
            spent = w.spend.get(month, 0)
            cc["spend"] += spent
            cc["budget"] += w.monthly_budget
            if spent > w.monthly_budget:
                cc["over_budget"].append(w.agent_id)
        return dict(by_cc)
