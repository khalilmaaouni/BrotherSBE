# BrotherSBE for Data Engineers (Snowflake and Databricks), design spec

Approved by the founder through question windows on 2026-07-30, four decisions recorded
below. Sibling spec: `2026-07-30-infra-engineer-book-design.md`. Parent program spec:
`2026-07-30-team-docs-collab-book-design.md`. Status: APPROVED DESIGN.

## Why this book exists

The base book teaches the product on a small local estate. A data engineer working in
Snowflake and Databricks needs the same lessons in their own vocabulary: warehouses,
models, marts, medallion layers, jobs, catalogs, grants, and the number that a director
will ask about at the wrong moment. This book is that translation, and it is a separate
volume so nobody reads Kubernetes chapters to reach their own.

## Decisions taken (founder, 2026-07-30, via windows)

| Decision | Answer |
|---|---|
| Honesty for output this machine cannot produce | Runnable local core; every platform-specific block labeled NOT EXECUTED HERE with its reason and the command a reader runs on their own estate; every platform fact cited to official documentation |
| Shape | Its own volume, reusing the base book's builder and replay harness |
| Sequencing | Specced now, built after Loop 1 lands its builder and harness |
| Client anonymity | No client or project name anywhere; already enforced mechanically by `TestNoPrivateNameShips` |

## Verified machine facts that shape this design (checked 2026-07-30, not assumed)

`databricks`, `snow`, `snowsql`, `aws`, `az`, `kubectl`, `terraform`, `docker` are ALL
ABSENT from this machine; `python3` (3.9.6) and `jq` are present. Therefore no Snowflake
or Databricks command can be executed while authoring, and the book says so at the point
of every such block rather than in a footnote. What CAN be executed and therefore IS real
in this book: every BrotherSBE command, and every local validation of the estate's own
artifacts.

## The estate: `docs/book-data/estate/`

JSON-native on purpose, so Python's standard library can genuinely validate it (dbt's own
truth files are JSON, and this also makes the estate the natural fixture for the L6 dbt
adapter):

- `warehouse/ddl/` Snowflake-flavored DDL as `.sql` files: a raw landing table, a cleaned
  staging view, a `daily_revenue` mart with an explicit grain comment, and one destructive
  migration (a column drop) used by the migration-gate chapter.
- `warehouse/derivations/` two independent SQL derivations of the same headline number,
  written to differ in method and not merely in alias, because that difference is exactly
  what the numbers gate demands and what row 6 of the bypass table says it cannot yet
  prove.
- `dbt/manifest.json` and `dbt/run_results.json` in dbt's real shapes, enough to carry
  model names, tests, and freshness, so the chapters can show what an adapter will read.
- `databricks/bundle.json` an Asset Bundle in JSON form, plus `databricks/job.json` for a
  scheduled job, both structurally validated locally.
- `transform.py` a stdlib transform that really runs here over `orders.csv`, producing the
  same numbers the SQL claims, so the two-derivation lesson has a locally provable half.
- `validate_estate.py` the estate's own checker: DDL grain comments present, both
  derivations parse and differ beyond formatting, manifest and run_results match schema,
  bundle and job JSON well formed. Runs in this repo's CI as `tools/test_sbe_book_data.py`.

## Chapters, `docs/book-data/`

Part I, for the analysts and leads who consume the outputs (chapters 01 to 03): the wrong
number problem told from the warehouse; what a gate refuses and why that protects them;
reading `sbe status` on a data change.

Part II, the engineer core (04 to 10): the first loop on a mart change; the numbers gate
with two real derivations, including the honest limit that a renamed alias defeats a text
comparison and lineage is the fix (an L6 item, marked); the migration gate on the column
drop, with a rehearsal receipt, row counts, and the value-checksum hole named; freshness
and the limits of what a receipt proves; jobs and orchestration, Databricks Asset Bundles
and jobs beside a Snowflake task, both as commands a reader runs; catalogs and grants,
Unity Catalog and Snowflake RBAC as the approval-adjacent surface where the approval gate
already applies; cost and warehouse sizing as a gated decision with its blast radius.

Part III (11 to 12): coordinating with analysts and with a second engineer through one
vault; and a cookbook of data-shaped recipes (new mart, backfill, schema change that
raises the tier, incident on a bad number, adopting an existing warehouse repo).

## Non-negotiables for the writers

Every platform command carries the label `NOT EXECUTED HERE` with the reason (no
credentials or CLI on the authoring machine) and the exact command the reader runs.
Every platform fact, name, and flag comes from official documentation or the installed
Databricks skills, cited inline, never from memory; the Databricks chapters load
`databricks-core` first and then the product skill that matches the chapter, per this
machine's standing instruction. Every BrotherSBE command block is real, re-executed
output, checked by the replay harness. Maturity language stays INTERNAL-EVAL, and no
chapter claims the product has run on a real Snowflake or Databricks estate, because it
has not.

## Testing

`tools/test_sbe_book_data.py`: the estate validates; both derivations differ beyond
formatting; the dbt files parse to their expected keys; every chapter has a single h1 and
at least one Mermaid diagram; every platform block carries the NOT EXECUTED HERE label
(a grep-based fixture, so an unlabeled block fails the suite); the book builds. Plus the
replay harness over every BrotherSBE block. Every fixture calibrated the house way.
