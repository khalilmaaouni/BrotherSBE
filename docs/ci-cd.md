# CI/CD

BrotherSBE should normally be introduced to CI/CD in stages.

Do not make every check blocking on the first day.

The exact step order the shipped workflow runs, and why gates come first, is documented in [CI-ORDER.md](CI-ORDER.md). The workflow itself is [.github/workflows/brothersbe-gates.yml](../.github/workflows/brothersbe-gates.yml); it guards nothing until you copy it into your own repository.

## Stage 1: Advisory

Run BrotherSBE without strict enforcement.

Example:

```bash
sbe impact . --base origin/main
sbe verify design/my-change
```

Use this period to measure:

```text
useful findings
false positives
missing checks
NO-DATA frequency
unmeasured paths
workflow overhead
```

## Stage 2: Register the checks that matter

Your team must define which commands count as proof.

Examples:

```text
unit test suite
API compatibility test
Snowflake reconciliation
migration rehearsal
data-quality query
integration test
```

Register each one in `.sbe/checks.yml`, naming its executable, arguments, working directory and the files it is evidence for. Then run it by id through the evidence wrapper:

```bash
sbe evidence run --check reconcile-orders --out .sbe/evidence/reconcile-orders.json
```

The registry entry defines what runs; nothing on the command line replaces it. A free-form run (`sbe evidence run --out <receipt> -- <command>`) mints advisory evidence only and satisfies no required policy check.

## Stage 3: Review verdict quality

BrotherSBE distinguishes:

```text
PASS
FAIL
NO-DATA
```

CI systems often reduce results to green or red.

Do not lose the `NO-DATA` information in that reduction.

Read the BrotherSBE verdict block. A required CI check compares a name to a conclusion; it has no opinion about whether anything was examined. A job skipped by a condition still reports success to a merge rule.

## Stage 4: Strict selected controls

After a check has proven useful, selected controls can become enforcing.

Example:

```bash
sbe impact . --base origin/main --strict --intake design/my-change/00-intake.json
```

Strict mode should be introduced deliberately, and it moves only by a human editing the CI workflow, visible in the diff. A session instruction never waives a hard gate.

## What BrotherSBE does not provide

BrotherSBE does not replace:

```text
branch protection
repository merge checks
deployment approvals
cloud IAM
production credentials policy
release management
```

BrotherSBE produces verdicts and evidence.

Your engineering platform decides what those verdicts are allowed to block. On GitHub that is branch protection or rulesets; on Bitbucket it is branch permissions and merge checks; the same applies to any host.

One wiring note for the approval gate: it passes only on a signature the CI host verified. A CI agent with no reviewer public keys imported produces an unverifiable signature and the gate reports NO-DATA, not PASS.

## Recommended PR sequence

```text
PR opened
  |
BrotherSBE impact
  |
design checks
  |
registered project tests
  |
evidence receipts
  |
specialist review
  |
BrotherSBE verify/status
  |
branch policy
  |
human merge
```

## Important rule

A CI job being green does not automatically mean:

```text
the intended check executed
```

or:

```text
the requirement was proven
```

BrotherSBE exists to make that distinction visible.
