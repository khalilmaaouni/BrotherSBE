# Snowflake and ELT

This guide shows how BrotherSBE is applied to a Snowflake data engineering change.

The platform-specific patterns here still need validation against your own Snowflake estate and conventions.

## Example change

Finance reports that daily revenue in a dashboard does not reconcile with the source ledger.

The engineering task is not simply:

```text
fix SQL
```

The task is:

```text
define the correct grain
identify the system of record
find the fan-out or transformation error
fix the model
prove the corrected number
make the result reproducible
```

## 1. Start and score the change

```text
/brothersbe:start
```

```bash
mkdir -p design/daily-revenue
sbe intake design/daily-revenue
```

A revenue reconciliation is likely high risk because it affects money and downstream decisions.

## 2. Define the data model before SQL

In `05-data-model.md`, write the grain in plain language.

Example:

```text
fct_daily_revenue

Grain:
one row per order_date x product_line x currency
```

Name the system of record.

Example:

```text
Order amount:
Billing system

Customer attributes:
CRM

Product attributes:
ERP
```

Write cardinality.

Example:

```text
order 1:N order_line
customer 1:N order
```

### Why this matters

A join can be syntactically correct while multiplying rows.

Null checks, type checks, and a green pipeline may all pass while revenue is overstated.

## 3. Design the ELT path

Write the actual flow.

```text
Source
  |
Raw
  |
Staging
  |
Transformation
  |
Business fact/dimension
  |
Semantic/reporting layer
```

Define:

```text
keys
deduplication
incremental strategy
late-arriving data
historisation
schema change behaviour
reprocessing
freshness
downstream consumers
reconciliation
```

## 4. Validate the design

```bash
sbe design design/daily-revenue
```

Fix structural failures before generating the implementation.

## 5. Implement

```text
/brothersbe:work
```

A scoped worker can implement the SQL or orchestration change.

Keep separate workers for separate responsibilities where useful.

Example:

```text
Worker A:
Snowflake model

Worker B:
reconciliation check

Worker C:
backend/consumer change
```

## 6. Register real validation

Useful data engineering checks include:

```text
row counts
uniqueness
duplicates
null thresholds
referential integrity
source-to-target reconciliation
freshness
expected ranges
incremental-load behaviour
backfill completeness
```

Register the reconciliation as a check in `.sbe/checks.yml`, naming the executable, its arguments and the files it is evidence for. Then run it by id:

```bash
sbe evidence run --check reconcile-daily-revenue --out .sbe/evidence/reconcile-daily-revenue.json
```

The registry entry defines what runs. Nothing typed on the command line replaces it, which is what stops a receipt being minted for the wrong command.

## 7. Pin the Snowflake state

Two validations should not compare moving data.

For reproducible Snowflake validation, use an estate-approved pin such as:

```text
Query ID
Time Travel point/offset
```

Where a restorable copy is needed, a zero-copy clone can be part of the test setup.

The important requirement is:

```text
both derivations read the same intended state
```

## 8. Use a second derivation

Do not prove a number by re-running the same transformation.

Example:

```text
Primary path:

analytics.fct_daily_revenue
        |
SUM(net_amount)
```

Second path:

```text
raw orders
   +
raw order lines
   |
quantity * unit_price - discount
   |
independently derived revenue
```

Then compare the two outputs.

BrotherSBE checks that the recorded derivations differ in text and that the recorded figures reconcile against the pinned state.

It cannot prove that the two logical paths are truly independent. Two queries over the same broken view still agree.

A human data engineer owns that judgement, and the gate prints this limit on every run.

## 9. Migration and backfill

For schema changes and backfills, define and test:

```text
forward operation
reverse operation
restore/rehearsal
row counts before
row counts after reverse
reconciliation
downstream compatibility
```

Register the rehearsal script as a check, then:

```bash
sbe evidence run --check migration-rehearsal --out .sbe/evidence/migration-rehearsal.json
```

The rule is:

```text
a rollback script existing is not evidence that rollback works
```

## 10. Review

```text
/brothersbe:review
```

Data review challenges:

```text
grain
fan-out
keys
systems of record
historisation
freshness
reconciliation
quality
cost
```

Migration review challenges:

```text
forward/reverse
lock duration
mixed-schema compatibility
rollback time
backfill safety
```

## 11. Verify and status

```text
/brothersbe:verify
```

```text
/brothersbe:status
```

The final question is:

```text
Can another engineer reproduce why this number is correct?
```

Not:

```text
Did the SQL finish successfully?
```
