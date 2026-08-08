---
slug: data-and-warehouse
title: Scenario, the warehouse and the reported figure
part: "5"
verified-against: 1.0.0-rc.28
---

# Scenario, the warehouse and the reported figure

Snowflake, Databricks, Power BI, Azure Data Factory and Microsoft Fabric. This
is the scenario where the gates bite hardest, because every failure here is
silent by nature: a wrong number is formatted exactly like a right one.

The BrotherSBE commands below are the real ones. The vendor-side SQL and
pipeline snippets are illustrative shapes rather than output from a run on your
estate, and they are marked **UNVERIFIED** where that is the case, because
labelling that next to the claim rather than in a footnote is the rule.

## Where the money is: the four traps

**The grain trap.** A join fans out, one order becomes three rows, and revenue
is overstated by exactly the average line count. It passes every test that
checks for nulls and types. Caught in the data phase, by writing the grain in
words before writing SQL, and by the datamodel check refusing a relationship
that carries no cardinality.

**The two-owners trap.** The CRM and the billing system both believe they own
`customer`. Two dashboards disagree and both are internally consistent. Caught
by the rule that every entity names its system of record, and by nothing else.

**The unrehearsed reverse.** The migration ran. Nobody ever ran the rollback,
and you find out during the incident. The migration gate demands forward and
reverse both against a restored copy, with matching row counts.

**The number nobody can re-derive.** Someone asks where the figure came from
and the answer is a notebook that no longer runs. The numbers gate demands a
pinned snapshot and a genuinely different second derivation.

## Day one on a warehouse repository

```bash
sbe adopt .                       # dry run, changes nothing
sbe adopt . --apply               # only when you have read the dry run
mkdir -p design/daily-revenue
python3 tools/sbe_intake.py design/daily-revenue
```

Anything touching revenue answers yes to "money", so it is T3. All seven
artifacts. That is the correct answer and it is worth sitting with.

## The data model phase, concretely

State the grain in one sentence before any SQL exists.

> `fct_daily_revenue` is one row per (`order_date`, `product_line`,
> `currency`). Its system of record for order amounts is the billing system,
> not the CRM. `order` to `order_line` is one-to-many mandatory.

That paragraph is what stops the fan-out. The check enforces the *shape* of it
(every entity names an owner, every relationship carries a cardinality) and
cannot enforce that you picked the right owner. Human review, and the tool says
so.

## The numbers gate, per platform

The gate wants three things: a pinned snapshot identifier, a second derivation
whose text genuinely differs, and zero drift between the real numbers.

**Snowflake.** Pin the snapshot with a query id or a time-travel offset, so the
re-run reads the same bytes:

```sql
-- derivation A, the model
SELECT order_date, SUM(net_amount) AS revenue
FROM analytics.fct_daily_revenue AT (STATEMENT => '01b2c3d4-0000-0000')
GROUP BY order_date;

-- derivation B, from the source, deliberately not the same shape
SELECT o.order_date, SUM(l.quantity * l.unit_price - l.discount) AS revenue
FROM raw.orders o JOIN raw.order_lines l ON l.order_id = o.order_id
GROUP BY o.order_date;
```

**UNVERIFIED**: not executed against a Snowflake account by this project.

The point of derivation B is that it walks a different path. Two queries
against the same view differ in text and prove nothing, and the gate cannot
tell the difference, which is stated in the honest limits and worth
remembering exactly here.

**Databricks.** Pin a Delta table version, which is the cleanest snapshot pin
of the four platforms:

```sql
SELECT order_date, SUM(net_amount) FROM analytics.fct_daily_revenue
VERSION AS OF 412 GROUP BY order_date;
```

**UNVERIFIED**: not executed against a Databricks workspace by this project.
Databricks work in this repository routes through the Databricks skills and
the `databricks` CLI, which is the documented invocation and should not be
improvised around.

**Power BI.** The trap here is different. Power BI is usually the place the
figure is *seen*, not where it is computed, so the reconciliation you owe is
between the semantic model measure and the warehouse table underneath it. Name
the measure, name the table, and re-derive the measure's definition in SQL.

A DAX measure that quietly filters on a role-playing date dimension is the most
common way a Power BI number stops matching a correct warehouse table.

**Azure.** Data Factory and Fabric pipelines are where the `ran` gate earns its
keep. A pipeline that succeeded is not a pipeline that processed rows. Register
the reconciliation as a check and run it through the evidence wrapper so the
receipt records a real exit code and a real duration:

```bash
sbe evidence run --check daily-revenue-reconciliation -- \
  python3 scripts/reconcile_daily_revenue.py --date 2026-08-07
```

There is no argument on that path that changes what runs. The command comes
from the registry, not from what you typed beside it.

## The migration gate, for a schema change

Adding a column, changing a type, repartitioning a large table. Forward and
reverse both against a **restored copy**, a rehearsal id recorded as a string,
and whole matching row counts.

Two honest points. A receipt with no row counts is NO-DATA, not a pass, and the
gate says what it compared instead of asserting a comparison it never made.
And nothing resolves the rehearsal id against your job system, so that id is a
pointer for a human to follow.

## The linter that matters most in a warehouse

The silent-failure linter reads SQL wherever it is written, in a `.sql` file or
embedded in Python, and the pattern it hunts hardest here is the
conflict-skipping upsert:

```sql
INSERT INTO analytics.dim_customer (customer_id, name)
SELECT customer_id, name FROM staging.customers
ON CONFLICT (customer_id) DO NOTHING;
```

`DO NOTHING` on a dimension load is how updates silently stop arriving. The
lint stops at the statement's semicolon, so a legitimate
`ON CONFLICT ... DO UPDATE` beside it is not swept in. If you genuinely want
the skip, say why in the diff:

```sql
-- sbe: allow-silent replays are idempotent by design, the row is immutable after insert
```

A bare marker waives nothing. The reason is read.

## Which reviewer you get

`sbe review-route` reads the diff and picks deterministically. A change under a
models or SQL directory routes to `data-reviewer`, which covers grain, joins
and fan-out, keys, systems of record, historization, reconciliation, freshness
and cost. A schema migration adds `migration-reviewer`. At most two
specialists, and zero is a legal result: the router never claims a clean review
it did not perform.

## Week one and month one

**Week one.** Wire `sbe verify` and `sbe score --strict` into CI on the
warehouse repository. Register your two most important reconciliations as
checks so `sbe evidence run --check` can resolve them.

**Month one.** Every reported figure that reaches a decision has a second
derivation. When Finance asks where a number came from, the answer is a
receipt, not a person's memory.
