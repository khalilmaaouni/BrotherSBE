# External proof, round one: three real estates, 2026-07-31

The essentials program requires the complete flow to run in external
repositories before any first-rank claim. This is the first such round:
three public repositories, cloned read-only, each taken through adopt, init,
intake, a real dossier for a real merged change, plan, evidence, converge,
and status, plus deliberate attack rounds. Every number and quote below comes
from those runs. This round was executed by this project's own maintainers'
agents, not by an external team, and no claim of third-party adoption is
made: maturity stays INTERNAL-EVAL, now with foreign-tree evidence.

## The estates

1. API: the FastAPI full-stack template (backend routes, SQLModel models,
   alembic migrations). Range: the real merged change #2356 refactoring
   UserUpdate/ItemUpdate model types.
2. Data: jaffle_shop_duckdb (dbt models over duckdb). Range: the real merged
   change #6 making the SQL portable to TSQL, touching two models.
3. Infra: sentry self-hosted (docker compose, install scripts). Range: the
   real merged change #4419 adding a consumer to the compose file.

## What the tools caught, correctly, on foreign trees

- Plan citations FAILed by task id on a hand-planted bogus anchor, twice
  (estates A and B), naming the exact unresolvable row or heading.
- The compatibility gate refused to invent a missing compatibility claim for
  a contract-declaring intake, on two estates, until the dossier itself
  supported one.
- The decision-bearing calculation rule caught a numeric revenue claim with a
  single underived check (estate B) exactly as specified.
- Converge SCOPE named every file of an undocumented 41-commit range
  individually (estate A) instead of waving it through or refusing vaguely.
- Converge VERIFICATION and status --team both caught receipts bound to a
  commit the estate had moved past, naming both shas, on all three estates.
- Converge CONTRACTS refused to PASS over a changed contract-shaped file it
  cannot parse (a Python SQLModel file), saying unread rather than clean.
- sbe design FAILed an intentionally incomplete T3 dossier listing every
  missing artifact; sbe work finish refused closure without a receipt.

## What broke, and what happened to each

Fixed the same night, each with a calibrated regression test:

1. CRITICAL: the receipt matchers in converge and work compared a rejoined
   argv against the plan's raw quoted command text, so any verification
   command containing a quote or space could NEVER bind its own receipt.
   Two estates hit it independently; both matchers now canonicalize through
   shlex (tools/test_sbe_converge.py TestQuotedCommandReceipts,
   tools/test_sbe_work.py TestQuotedVerifyCommandReceipt).
2. CRITICAL: converge ignored every detector's content pattern, so every
   changed .sql, and via the destructive detector's path pattern every .py,
   counted migration-shaped; a SELECT-only dbt model FAILed a dossier for
   lacking a data model it never needed. Detector kinds now honor content
   patterns against head-side content
   (TestSqlModelIsNotAMigration).
3. MAJOR: the 07-verification table parser split on every literal pipe, so a
   markdown-escaped pipe inside a check command silently truncated the
   command into a phantom cell. Escaped pipes now survive
   (tools/test_sbe_plan.py TestExternalProofRepairs).
4. MAJOR: both the derivation and validation sides of the migration-triplet
   rule triggered on ANY backticked path in the data model's Physical
   section, forcing authors of migration-free changes to invent reversal
   plans for migrations that do not exist. Both sides now trigger only on
   migration-shaped paths (same suite).

Open, named, and owned by a next session:

5. MAJOR: sbe adopt proposes protectedPaths and CODEOWNERS entries from this
   repository's own layout, none of which exist in a foreign clone. The fix
   (propose only paths that exist, name the dropped categories) is designed
   and was reverted tonight only because eight adoption-suite contracts pin
   the current shape and deserve a deliberate rewrite, not a 4am one.
6. MAJOR: converge SCOPE matches ownership by file path only; a later range
   touching the same files for an unrelated reason still reads as in scope.
   Deep design work; recorded in KNOWN-LIMITS.
7. MINOR: sbe plan --write does not cross-check the tier's required-artifact
   list (sbe design owns that gate); an advisory line is worth adding.
8. MINOR: subcommand help (-h) prints correct help but exits 2 across several
   tools; the known help-exit sweep item, still open.

False blockers observed: two, both from defect 1 and both gone with it.
Frictions a paying engineer would name: -h behavior, sbe intake being
interactive-only, and evidence run's `--` syntax being underdocumented.

## Measurements

Estate wall-clock minutes (agent-reported): A 50, B 44, C 32. Install plus
init: about 3 minutes per estate. Dossier-to-plan on a real change: 8 to 20
minutes, dominated by dossier authoring. Detection results and defect counts
are the lists above; zero crashes, zero data loss, no estate tree corrupted.

## What this round does not prove

No external team ran anything; friction numbers are agent-experienced, not
human-experienced; only one range per estate ran the full path; the live
GitHub approval path stayed untested (no token on this machine); and the
comparison against leading alternatives the essentials program calls for has
not begun.
