import argparse
import csv
import os
import sys
from datetime import date

from .core import Workforce


def demo():
    wf = Workforce()
    ap = wf.hire(
        "ap-clerk-1", "Accounts payable clerk", "maria@acme.com", "Finance", 300, date(2026, 9, 1), template="finance"
    )
    for cred in ("quickbooks:write", "gmail:ap@acme.com", "bank:read"):
        wf.grant_credential("ap-clerk-1", cred)
    ap.artifacts = ["vendor-master.xlsx", "ap-runbook.md"]
    for item in list(ap.checklist):
        wf.complete("ap-clerk-1", item)
    wf.activate("ap-clerk-1")
    wf.hire("sdr-1", "Outbound SDR", "tom@acme.com", "Sales", 500, date(2026, 9, 15))
    for item in [
        "identity_created",
        "scopes_granted",
        "budget_set",
        "runbook_linked",
        "escalation_contact",
        "eval_suite_passed",
    ]:
        wf.complete("sdr-1", item)
    wf.activate("sdr-1")
    wf.record_spend("ap-clerk-1", "2026-10", 210)
    wf.record_spend("sdr-1", "2026-10", 640)
    print(
        "ap-clerk-1 review:",
        wf.monthly_review(
            "ap-clerk-1",
            {"tasks": 400, "successes": 392, "cost": 210, "escalations": 6, "target_cost_per_task": 0.6},
            "2026-10",
        ),
    )
    print(
        "sdr-1 review:     ",
        wf.monthly_review(
            "sdr-1",
            {
                "tasks": 900,
                "successes": 610,
                "cost": 640,
                "escalations": 80,
                "incidents": 1,
                "target_cost_per_task": 0.5,
            },
            "2026-10",
        ),
    )
    print("report 2026-10:", wf.report("2026-10"))
    print("offboard:", wf.offboard("ap-clerk-1", "replaced by v2"))


def _run(argv=None):
    ap = argparse.ArgumentParser(prog="agent-workforce")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo")
    ap.parse_args(argv)
    demo()
    return 0


def main(argv=None):
    """Run the CLI; a bad input file or argument exits 2 with a one-line error instead of a traceback.

    Set AGENT_ECONOMY_DEBUG=1 to see the full traceback.
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        return _run(argv)
    except (OSError, ValueError, KeyError, csv.Error) as e:
        if os.environ.get("AGENT_ECONOMY_DEBUG"):
            raise
        msg = e.args[0] if isinstance(e, KeyError) and e.args else e
        print(f"error: {msg}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
