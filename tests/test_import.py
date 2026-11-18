"""CSV import of agents, spend and credentials: all-or-nothing, and safe to re-run."""

import contextlib
import io
import os
import pathlib
import tempfile
import unittest

from agent_workforce.__main__ import main

EX = pathlib.Path(__file__).resolve().parent.parent / "examples"


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main(list(argv))
    return code, out.getvalue()


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = os.path.join(self.tmp.name, "wf.json")

    def tearDown(self):
        self.tmp.cleanup()

    def w(self, *argv):
        return run(*argv, "--store", self.store)

    def csv(self, name, text):
        p = pathlib.Path(self.tmp.name) / name
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_agents_then_spend_then_report(self):
        code, out = self.w("import", "agents", str(EX / "agents.csv"))
        self.assertEqual(code, 0, out)
        self.assertIn("3 added", out)
        code, out = self.w("import", "spend", str(EX / "spend.csv"))
        self.assertEqual(code, 0, out)
        _, out = self.w("report", "--month", "2026-11")
        self.assertIn("CX", out)
        self.assertIn("$  1,152.95", out)  # two lines for support-bot add up
        self.assertIn("over: sdr-agent", out)  # 1,034 against a 900 budget

    def test_reimport_is_safe(self):
        self.w("import", "agents", str(EX / "agents.csv"))
        self.w("import", "spend", str(EX / "spend.csv"))
        _, out = self.w("import", "spend", str(EX / "spend.csv"))
        self.assertIn("0 added, 3 updated", out)
        _, out = self.w("report", "--month", "2026-11")
        self.assertIn("1,152.95", out)  # not doubled
        _, out = self.w("import", "agents", str(EX / "agents.csv"))
        self.assertIn("0 added, 0 updated, 3 unchanged", out)
        moved = self.csv(
            "moved.csv", "agent_id,role,manager,cost_center,monthly_budget\nsdr-agent,SDR,kim@acme.com,SALES,1500\n"
        )
        _, out = self.w("import", "agents", moved)
        self.assertIn("1 updated", out)
        _, out = self.w("roster")
        self.assertIn("kim@acme.com", out)

    def test_credentials_feed_offboarding(self):
        self.w("import", "agents", str(EX / "agents.csv"))
        creds = self.csv(
            "c.csv", "agent_id,credential\nsupport-bot,zendesk-api (vault: cx/zd)\nsupport-bot,slack-bot\n"
        )
        self.assertIn("2 added", self.w("import", "credentials", creds)[1])
        self.assertIn("0 added", self.w("import", "credentials", creds)[1])
        _, out = self.w("offboard", "support-bot", "--reason", "replaced")
        self.assertIn("zendesk-api (vault: cx/zd), slack-bot", out)

    def test_one_bad_row_changes_nothing(self):
        bad = self.csv(
            "bad.csv",
            "agent_id,role,manager,cost_center,monthly_budget\na1,r,m,CC,100\na2,r,m,CC,-5\n",
        )
        code, out = self.w("import", "agents", bad)
        self.assertEqual(code, 1)
        self.assertIn("line 3", out)
        self.assertIn("no agents yet", self.w("roster")[1])
        for name, text, msg in (
            ("s.csv", "agent_id,month,cost\nghost,2026-11,5\n", "import agents first"),
            ("m.csv", "agent_id,month\nx,2026-11\n", "missing column"),
            ("d.csv", "agent_id,role,manager,cost_center,monthly_budget\nx,r,m,C,1\nx,r,m,C,1\n", "twice"),
            ("e.csv", "agent_id,month,cost\n", "no rows"),
        ):
            code, out = self.w(
                "import", "spend" if name in ("s.csv", "m.csv", "e.csv") else "agents", self.csv(name, text)
            )
            self.assertEqual(code, 1, name)
            self.assertIn(msg, out, name)


if __name__ == "__main__":
    unittest.main()
