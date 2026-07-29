"""The nightly pipeline the book follows. Small on purpose: three source rows,
one aggregation, one output table, so every gate and receipt in the book has a
surface a reader can hold in one look. Standard library only."""
import argparse
import csv
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "orders.csv")
OUT = os.path.join(HERE, "daily_totals.json")

ORDERS = [
    {"order_id": "A-1001", "date": "2026-07-01", "region": "EU", "amount_eur": "120.50"},
    {"order_id": "A-1002", "date": "2026-07-01", "region": "EU", "amount_eur": "89.00"},
    {"order_id": "A-1003", "date": "2026-07-01", "region": "US", "amount_eur": "240.00"},
]


def ensure_source():
    """The book's chapter 4 deletes this file to show a NO-DATA morning."""
    if os.path.exists(SOURCE):
        return SOURCE
    with io.open(SOURCE, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(ORDERS[0]))
        writer.writeheader()
        writer.writerows(ORDERS)
    return SOURCE


def run(date):
    ensure_source()
    totals = {}
    with io.open(SOURCE, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["date"] != date:
                continue
            key = row["region"]
            totals[key] = totals.get(key, 0.0) + float(row["amount_eur"])
    rows = [{"date": date, "region": r, "total_eur": round(t, 2)}
            for r, t in sorted(totals.items())]
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2, sort_keys=True)
    sys.stdout.write("read %d orders from %s\n" % (len(ORDERS), os.path.basename(SOURCE)))
    sys.stdout.write("aggregated %d region(s) for %s\n" % (len(rows), date))
    sys.stdout.write("wrote %d rows to daily_totals\n" % (len(rows) + 1))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    return run(args.date)


if __name__ == "__main__":
    sys.exit(main())
