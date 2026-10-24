import unittest
from datetime import date

from agent_workforce import Workforce, review


class Tests(unittest.TestCase):
    def setUp(self):
        self.wf = Workforce()
        self.w = self.wf.hire("a1", "clerk", "boss", "Finance", 100, date(2026, 1, 1))
        self.w.credentials = ["k1", "k2"]

    def test_cannot_activate_until_onboarded(self):
        with self.assertRaises(ValueError):
            self.wf.activate("a1")
        for item in list(self.w.checklist):
            self.wf.complete("a1", item)
        self.wf.activate("a1")
        self.assertEqual(self.w.status, "probation")

    def test_review_ratings(self):
        self.assertEqual(
            review({"tasks": 100, "successes": 99, "cost": 50, "escalations": 1})["action"], "expand_scope"
        )
        self.assertEqual(review({"tasks": 100, "successes": 80, "cost": 50, "escalations": 10})["action"], "pip")
        self.assertEqual(review({"tasks": 100, "successes": 99, "incidents": 2})["action"], "offboard")
        self.assertEqual(review({"tasks": 100, "successes": 50})["rating"], "unacceptable")

    def test_review_changes_status(self):
        for item in list(self.w.checklist):
            self.wf.complete("a1", item)
        self.wf.activate("a1")
        self.wf.monthly_review("a1", {"tasks": 10, "successes": 7, "escalations": 2}, "2026-02")
        self.assertEqual(self.w.status, "pip")

    def test_offboard_and_report(self):
        self.wf.record_spend("a1", "2026-02", 150)
        rep = self.wf.report("2026-02")
        self.assertEqual(rep["Finance"]["over_budget"], ["a1"])
        plan = self.wf.offboard("a1", "retired")
        self.assertEqual(plan["revoke"], ["k1", "k2"])
        self.assertEqual(plan["lifetime_cost"], 150)
        self.assertEqual(self.w.credentials, [])
        self.assertEqual(self.wf.report("2026-02"), {})
        with self.assertRaises(ValueError):
            self.wf.monthly_review("a1", {"tasks": 1}, "2026-03")


if __name__ == "__main__":
    unittest.main()
