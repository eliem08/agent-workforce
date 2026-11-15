import contextlib
import io
import os
import tempfile
import unittest

from agent_workforce.__main__ import main
from agent_workforce.core import ONBOARDING
from agent_workforce.ops import load

HIRE = ["--role", "support", "--manager", "dana", "--cost-center", "cx", "--monthly-budget", "500"]


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main(list(argv))
    return code, out.getvalue()


class WorkforceOpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "wf.json")
        self.s = ["--store", self.path]

    def tearDown(self):
        self.tmp.cleanup()

    def ok(self, *argv):
        code, out = run(*argv, *self.s)
        self.assertEqual(code, 0, out)
        return out

    def onboard(self, agent="bot-1"):
        self.ok("hire", agent, *HIRE)
        done = [x for item in ONBOARDING["default"] for x in ("--done", item)]
        self.assertIn("complete", self.ok("checklist", agent, *done))
        self.ok("activate", agent)

    def test_lifecycle_from_hire_to_offboard(self):
        self.ok("hire", "bot-1", *HIRE)
        self.assertEqual(run("activate", "bot-1", *self.s)[0], 1)  # checklist not done
        self.assertIn("5 left", self.ok("checklist", "bot-1", "--done", "identity_created"))
        self.ok("checklist", "bot-1", *[x for i in ONBOARDING["default"][1:] for x in ("--done", i)])
        self.ok("activate", "bot-1")
        self.ok("credential", "bot-1", "zendesk-api-key")
        self.assertIn("OVER BUDGET", self.ok("spend", "bot-1", "620", "--month", "2026-11"))
        out = self.ok("monthly-review", "bot-1", "--tasks", "100", "--successes", "97", "--cost", "80")
        self.assertIn("exceeds", out)
        self.assertEqual(load(self.path).workers["bot-1"].status, "active")
        self.assertIn("over: bot-1", self.ok("report", "--month", "2026-11"))
        plan = self.ok("offboard", "bot-1", "--reason", "replaced")
        self.assertIn("revoke: zendesk-api-key", plan)
        self.assertEqual(load(self.path).workers["bot-1"].credentials, [])
        self.assertEqual(run("offboard", "bot-1", "--reason", "again", *self.s)[0], 1)

    def test_bad_month_suspends_the_agent(self):
        self.onboard()
        out = self.ok("monthly-review", "bot-1", "--tasks", "100", "--successes", "40")
        self.assertIn("suspended", out)

    def test_refusals(self):
        self.onboard()
        for argv in (
            ["hire", "bot-1", *HIRE],  # duplicate id
            ["spend", "ghost", "5"],
            ["spend", "bot-1", "5", "--month", "November"],
            ["checklist", "bot-1", "--done", "not_an_item"],
            ["monthly-review", "bot-1", "--tasks", "10", "--successes", "11"],
        ):
            with self.subTest(argv=argv):
                self.assertEqual(run(*argv, *self.s)[0], 1)


if __name__ == "__main__":
    unittest.main()
