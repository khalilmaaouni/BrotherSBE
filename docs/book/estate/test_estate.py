"""The estate's own suite: four tests the book runs in chapter 3."""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


class TestEstate(unittest.TestCase):
    def setUp(self):
        for name in ("daily_totals.json", "orders.csv"):
            path = os.path.join(HERE, name)
            if os.path.exists(path):
                os.remove(path)

    def _pipeline(self, date):
        return subprocess.run([sys.executable, os.path.join(HERE, "pipeline.py"),
                               "--date", date], capture_output=True, text=True)

    def test_the_pipeline_totals_by_region(self):
        self._pipeline("2026-07-01")
        with open(os.path.join(HERE, "daily_totals.json")) as fh:
            rows = json.load(fh)
        self.assertEqual([r["region"] for r in rows], ["EU", "US"])
        self.assertEqual(rows[0]["total_eur"], 209.5)

    def test_a_date_with_no_orders_writes_no_rows(self):
        self._pipeline("2026-07-02")
        with open(os.path.join(HERE, "daily_totals.json")) as fh:
            self.assertEqual(json.load(fh), [])

    def test_the_api_serves_what_the_pipeline_wrote(self):
        self._pipeline("2026-07-01")
        out = subprocess.run([sys.executable, os.path.join(HERE, "api.py"),
                              "2026-07-01"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0)
        self.assertIn('"region": "EU"', out.stdout)

    def test_the_api_refuses_before_the_pipeline_ran(self):
        out = subprocess.run([sys.executable, os.path.join(HERE, "api.py"),
                              "2026-07-01"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn("run pipeline.py first", out.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
