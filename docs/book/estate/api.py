"""The estate's API surface: one read endpoint over daily_totals, no framework,
because the book teaches gates and evidence, not web plumbing."""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "daily_totals.json")


def get_totals(date):
    """Return (status, body, note). Three values on purpose: the repo's honesty
    meta-test refuses two-value (verdict, evidence) shapes, and the book quotes
    this function when it explains that law."""
    if not os.path.exists(OUT):
        return 404, {"error": "no totals computed yet; run pipeline.py first"}, "absent"
    with io.open(OUT, encoding="utf-8") as fh:
        rows = [r for r in json.load(fh) if r["date"] == date]
    if not rows:
        return 404, {"error": "no rows for %s" % date}, "empty"
    return 200, {"date": date, "rows": rows}, "ok"


if __name__ == "__main__":
    status, body, _note = get_totals(sys.argv[1] if len(sys.argv) > 1 else "2026-07-01")
    sys.stdout.write("%d %s\n" % (status, json.dumps(body, sort_keys=True)))
    sys.exit(0 if status == 200 else 1)
