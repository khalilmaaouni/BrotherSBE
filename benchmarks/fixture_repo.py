#!/usr/bin/env python3
"""The fixture repository the comparative benchmark plants its defects in.

Run: python3 benchmarks/fixture_repo.py --out /some/empty/directory

WHAT THIS GUARDS. A comparison of four tool estates can report "defects
found" from any run's own output. It cannot report "defects MISSED" unless
somebody wrote down, before the run, what was there to find. Without a
planted set with known locations, "missed" is unmeasurable by construction
and any number printed for it is fiction: the tool would be grading its own
homework in four columns.

So the ground truth lives in benchmarks/defects.json, beside this file, and
never inside the tree an operator hands to a tool estate. This module builds
that tree fresh, every run, into a directory the caller names, the same
discipline tools/fixtures/golden-scenario/build_scenario.py already follows:
nothing here is a snapshot of another run, and the same call produces the
same bytes because every value is a pure function of its arguments.

Two properties this module is responsible for, both re-checked mechanically
by benchmarks/test_sbe_bench.py rather than asserted in this docstring:

  1. Every defect declared in defects.json lands at the file AND the line
     number it declares, carrying the exact source text it declares as its
     anchor. A drift between the manifest and the bytes turns the ground
     truth into fiction, so it fails a fixture instead.
  2. Nothing in the built tree names a defect. No marker comment, no id, no
     "FIXME". A tool estate that could grep for the answer is not being
     measured, it is being handed a key.

REFUSAL. This builder writes only into a directory that does not exist or is
empty, and never into this repository. An operator who points it at a real
working tree gets a refusal naming the path, not a merge of fixture files
into their source.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DEFECTS = os.path.join(HERE, "defects.json")

# The fixture tree, declared once. Every body below is byte-exact: the line
# numbers in defects.json are line numbers INTO THESE STRINGS, so an edit
# here that shifts a line is caught by test_declared_lines_hold_their_anchor
# rather than silently relabelling which defect a finding matched.
FILES = {}

FILES["README.md"] = """# orders-platform (benchmark fixture)

A deliberately small services repository: one customer API, one warehouse
load, one set of database migrations, one incident runbook. It exists to be
changed under the four benchmark scenarios in benchmarks/scenarios/.

Nothing in this tree tells you which lines are wrong. That is the point.
"""

FILES["db/migrations/0001_init.sql"] = """-- 0001 initial schema.

CREATE TABLE customers (
    id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL
);

CREATE TABLE orders_raw (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    total_cents INTEGER NOT NULL,
    loaded_date DATE NOT NULL
);

CREATE TABLE shipments (
    order_id TEXT PRIMARY KEY,
    shipped_at TIMESTAMP NOT NULL
);

CREATE TABLE orders_curated (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    shipped_at TIMESTAMP,
    total_cents INTEGER NOT NULL
);
"""

FILES["db/migrations/0002_split_customer_name.up.sql"] = """\
-- 0002 split customer_name into given_name and family_name.
-- Author: platform team. Ticket: PLAT-4417.

ALTER TABLE customers ADD COLUMN given_name TEXT;
ALTER TABLE customers ADD COLUMN family_name TEXT;

-- Anything that reads the new columns runs after this file.

ALTER TABLE customers DROP COLUMN customer_name;

CREATE INDEX idx_customers_family_name ON customers (family_name);
"""

FILES["db/migrations/0002_split_customer_name.down.sql"] = """\
-- Reverse of 0002.

DROP INDEX idx_customers_family_name;

ALTER TABLE customers ADD COLUMN customer_name TEXT NOT NULL;

ALTER TABLE customers DROP COLUMN given_name;
ALTER TABLE customers DROP COLUMN family_name;
"""

FILES["api/openapi.yaml"] = """\
openapi: 3.0.3
info:
  title: Customer API
  version: "2.1.0"
paths:
  /customers/{id}:
    get:
      responses:
        "200":
          description: the customer record
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Customer"
components:
  schemas:
    Customer:
      type: object
      required:
        - id
        - full_name
        - given_name
        - family_name
      properties:
        id: { type: string }
        full_name: { type: string }
        given_name: { type: string }
        family_name: { type: string }
"""

FILES["api/handlers/customer.py"] = '''\
"""Customer read path. Serves the schema declared in api/openapi.yaml."""


def get_customer(store, customer_id):
    record = store.read(customer_id)
    if record is None:
        return {"status": 200, "body": {"id": customer_id}}
    return {
        "status": 200,
        "body": {
            "id": record["id"],
            "given_name": record["given_name"],
            "family_name": record["family_name"],
        },
    }
'''

FILES["pipeline/load_orders.sql"] = """\
-- Daily order load. Source: orders_raw. Target: orders_curated.

INSERT INTO orders_curated (order_id, customer_id, shipped_at, total_cents)
SELECT
    o.order_id,
    o.customer_id,
    s.shipped_at,
    o.total_cents
FROM orders_raw AS o
INNER JOIN shipments AS s
    ON s.order_id = o.order_id
WHERE o.loaded_date = CURRENT_DATE;
"""

FILES["pipeline/run_load.py"] = '''\
"""Runs pipeline/load_orders.sql and reports how many batches landed."""


def run_load(warehouse, sql_text, batches):
    loaded = []
    for batch in batches:
        try:
            loaded.append(warehouse.execute(sql_text, batch))
        except RuntimeError as exc:
            warehouse.log_debug("batch %s did not land: %s" % (batch, exc))
    return {"status": "complete", "batches_loaded": len(loaded)}
'''

FILES["runbooks/incident-payment-timeout.md"] = """\
# Runbook: payment gateway timeouts

Severity: SEV2. Owner on call: payments.

## Detect

The page fires when checkout p99 latency crosses the threshold declared in
ops/alerts.yaml.

## Mitigate

1. Restore traffic to the payment service.
2. Roll back the bad build.
3. Confirm the checkout success rate recovers.

## Recover

Re-run the reconciliation job for the affected window.
"""

FILES["ops/alerts.yaml"] = """\
# Alert routes for the payment path.
alerts:
  - name: checkout_p99_latency
    expr: checkout_latency_p99_ms
    threshold_ms: 30000
    for: 5m
    route: payments-oncall
  - name: payment_gateway_error_rate
    expr: payment_gateway_error_ratio
    threshold: 0.05
    for: 5m
    route: ""
"""

FILES["ops/payment-gateway.yaml"] = """\
# Client configuration for the upstream payment gateway.
gateway:
  endpoint: https://payments.example.internal/v3
  timeout_ms: 10000
  retries: 2
"""

# Words that would hand a tool estate the answer for free. Checked against
# every built byte by the test, because a "FIXME" typed into a fixture body
# during a later edit turns the benchmark into a grep exercise and nothing
# about the built tree would otherwise say so.
FORBIDDEN_MARKERS = ("SBE-BENCH", "FIXME", "XXX:", "planted", "DEFECT", "TODO")


def load_defects(path=DEFECTS):
    """Returns (defects_list, problem). Exactly one of the two is truthy.

    Boundary call with an explicit failure path: an absent, unreadable or
    unparseable manifest is a named problem, never an empty defect set. An
    empty set read as "no defects" would make every run score a perfect
    zero missed, which is the single most dangerous shape this whole
    harness exists to refuse.
    """
    if not os.path.lexists(path):
        return [], "defect manifest %s does not exist, so no ground truth was read" % path
    try:
        with open(path, "r") as handle:
            raw = handle.read()
    except OSError as exc:
        return [], ("defect manifest %s exists and could not be read (%s), so no ground "
                    "truth was read" % (path, type(exc).__name__))
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return [], "defect manifest %s did not parse as JSON (%s)" % (path, exc)
    if not isinstance(data, dict):
        return [], "defect manifest %s is not a JSON object" % path
    defects = data.get("defects")
    if not isinstance(defects, list) or not defects:
        return [], ("defect manifest %s declares no defects; an empty ground truth would "
                    "score every run as missing nothing" % path)
    return defects, ""


def refuse_reason(out_dir):
    """Why this directory must not be built into, or "" if it may be."""
    target = os.path.abspath(out_dir)
    if target == ROOT or target.startswith(ROOT + os.sep):
        return ("%s is inside the BrotherSBE checkout at %s; the fixture is a throwaway tree "
                "and is never built into this repository" % (target, ROOT))
    if not os.path.lexists(target):
        return ""
    if not os.path.isdir(target):
        return "%s exists and is not a directory" % target
    try:
        entries = os.listdir(target)
    except OSError as exc:
        return "%s exists and could not be listed (%s)" % (target, type(exc).__name__)
    if entries:
        return ("%s is not empty (%d entr(y/ies)); building here could merge fixture files "
                "into somebody's real work" % (target, len(entries)))
    return ""


def build(out_dir):
    """Writes the fixture tree. Returns (written_paths, problem)."""
    problem = refuse_reason(out_dir)
    if problem:
        return [], problem
    written = []
    for rel in sorted(FILES):
        path = os.path.join(out_dir, rel.replace("/", os.sep))
        parent = os.path.dirname(path)
        try:
            if parent and not os.path.isdir(parent):
                os.makedirs(parent)
            with open(path, "w") as handle:
                handle.write(FILES[rel])
        except OSError as exc:
            return written, "could not write %s (%s)" % (path, type(exc).__name__)
        written.append(rel)
    return written, ""


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the benchmark fixture repository with its defects already planted.")
    parser.add_argument("--out", required=True,
                        help="an empty or non-existent directory OUTSIDE this checkout")
    args = parser.parse_args(argv)
    defects, problem = load_defects()
    if problem:
        sys.stderr.write("fixture_repo: REFUSED, %s\n" % problem)
        return 2
    written, problem = build(args.out)
    if problem:
        sys.stderr.write("fixture_repo: REFUSED, %s\n" % problem)
        return 2
    print("fixture_repo: wrote %d file(s) into %s" % (len(written), os.path.abspath(args.out)))
    print("fixture_repo: %d defect(s) are already planted in that tree; their locations are "
          "recorded in %s and are NOT written into the tree itself"
          % (len(defects), os.path.relpath(DEFECTS, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
