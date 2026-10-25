"""Stateless commands: read a JSON request, print a JSON decision (also served by the web app)."""

import json

from .core import review


def add_commands(sub):
    r = sub.add_parser("review", help="monthly performance review for one agent")
    r.add_argument("metrics", help="JSON: tasks, successes, cost, escalations, incidents, target_cost_per_task")


def run(a):
    with open(a.metrics, encoding="utf-8-sig") as fh:
        metrics = json.load(fh)
    if not isinstance(metrics, dict):
        raise ValueError("metrics must be a JSON object")
    out = review(metrics)
    print(json.dumps(out, indent=2))
    return 0 if out["action"] in ("keep", "expand_scope") else 1
