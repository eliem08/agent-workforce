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

    def _onboard(self, agent_id="a1"):
        for item in list(self.wf.workers[agent_id].checklist):
            self.wf.complete(agent_id, item)
        self.wf.activate(agent_id)

    def test_offboarded_agent_cannot_be_reactivated_or_rehired_over(self):
        self._onboard()
        self.wf.offboard("a1", "retired")
        with self.assertRaises(ValueError):
            self.wf.activate("a1")
        with self.assertRaises(ValueError):
            self.wf.offboard("a1", "again")
        with self.assertRaises(ValueError):
            self.wf.hire("a1", "clerk", "boss", "Finance", 100, date(2026, 5, 1))
        self.assertEqual(self.wf.workers["a1"].status, "offboarded")

    def test_unacceptable_review_suspends_the_agent(self):
        self._onboard()
        r = self.wf.monthly_review("a1", {"tasks": 100, "successes": 90, "incidents": 3}, "2026-02")
        self.assertEqual(r["action"], "offboard")
        self.assertEqual(self.wf.workers["a1"].status, "suspended")

    def test_inflated_or_negative_metrics_are_rejected(self):
        for metrics in ({"tasks": 10, "successes": 50}, {"tasks": 10, "successes": 9, "incidents": -4}):
            with self.subTest(metrics=metrics), self.assertRaises(ValueError):
                review(metrics)

    def test_granted_credentials_land_in_the_revoke_plan(self):
        self.wf.hire("a2", "sdr", "boss", "Sales", 100, date(2026, 1, 1))
        self.wf.grant_credential("a2", "crm:write")
        self.wf.grant_credential("a2", "crm:write")
        self.assertEqual(self.wf.offboard("a2", "done")["revoke"], ["crm:write"])
        with self.assertRaises(ValueError):
            self.wf.grant_credential("a2", "mail:send")

    def test_spend_must_be_finite_and_non_negative(self):
        for cost in (float("nan"), -500):
            with self.subTest(cost=cost), self.assertRaises(ValueError):
                self.wf.record_spend("a1", "2026-02", cost)


if __name__ == "__main__":
    unittest.main()
