"""Billing-shape tests: monthly checkout carries the 14-day trial, /pricing notes it."""

import http.client
import pathlib
import tempfile
import threading
import unittest
import urllib.request

from agent_workforce import web

ENV = {
    "STRIPE_SECRET_KEY": "sk_test_x",
    "STRIPE_WEBHOOK_SECRET": "whsec_test",
    "STRIPE_PRICES": "team=price_123,business=price_456,enterprise=price_789",
    "PUBLIC_URL": "https://example.test",
}


class BillingShapeTests(unittest.TestCase):
    def test_monthly_checkout_carries_trial_and_correct_price(self):
        with tempfile.TemporaryDirectory() as t:
            srv = web.make_server("127.0.0.1", 0, pathlib.Path(t), env=ENV)
            billing = srv.RequestHandlerClass.billing
            sent = {}
            billing._stripe = lambda path, form: sent.update(form) or {"url": "https://checkout.test/s"}
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=30)
                conn.request("POST", "/billing/checkout", "plan=enterprise")
                res = conn.getresponse()
                self.assertEqual((res.status, res.getheader("Location")), (303, "https://checkout.test/s"))
                conn.close()
                self.assertEqual(sent["mode"], "subscription")
                self.assertEqual(sent["line_items[0][price]"], "price_789")
                self.assertEqual(sent["subscription_data[trial_period_days]"], "14")
            finally:
                srv.shutdown()
                srv.server_close()

    def test_pricing_page_notes_trial_when_billing_enabled(self):
        with tempfile.TemporaryDirectory() as t:
            srv = web.make_server("127.0.0.1", 0, pathlib.Path(t), env=ENV)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                body = urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/pricing", timeout=30).read()
                self.assertIn(b"Subscribe", body)
                self.assertIn(b"14-day free trial", body)
            finally:
                srv.shutdown()
                srv.server_close()


if __name__ == "__main__":
    unittest.main()
