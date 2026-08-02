# Estate Matrix

Status: founder-gated, not yet run. This document names the independent estates (repository
types) BrotherSBE's full consumer workflow must run against, and what each one is expected to
prove. It backs control D13-C03 (review 21.5, Deliverable control matrix: "Five independent
estate types ... Exact fixture/result manifests from unrelated repositories") and draws its
list of estate types from review 12.2, Repository matrix.

Review 12.2 lists twelve repository types in total. This kit uses six of them: the five review
13's external validation section treats as the core independent-estate proof, plus the
malicious fixture, because a security-relevant estate belongs in every run of this matrix, not
only the dedicated security audit (review 13.3):

1. Small Python API (review 12.2, item 1)
2. Node/TypeScript service (review 12.2, item 2)
3. Data/dbt project (review 12.2, item 4)
4. SQL migration project (review 12.2, item 5)
5. Mixed monorepo (review 12.2, item 7)
6. Malicious/poisoned repository fixture (review 12.2, item 12)

"Independent" means each estate is a genuinely different repository, not a renamed copy of
another one on this list, not authored by anyone who built BrotherSBE, and not a repository
BrotherSBE's own test suite already runs against. The whole point of D13-C03 is proof from
repositories BrotherSBE has never seen (review 13.3's same standard: the auditor "must not
rely on maintainer explanations").

## What "run the consumer workflow" means here

For each estate, run the full path a real adopting team would use, not just the guided skills:

1. `sbe adopt` (dry run first, per docs/CLI.md) to check installation readiness.
2. `sbe init` to lay down BrotherSBE's local footprint.
3. `/brothersbe:start` through to a completed, evidence-backed change, exactly as in the
   beginner study's journey (`beginner-study.md`, section 3), but here run by whoever normally
   owns that estate, or by an engineer standing in for one if the estate is a fixture.
4. The consumer CI surface: wiring `tools/sbe_gate.py --strict`, `tools/sbe_design.py --strict`,
   and `tools/sbe_score.py --strict` (or the packaged GitHub Action) into that estate's own CI,
   and confirming it actually blocks a bad change and passes a good one.

## Per-estate expected outcomes

| Estate | What it is | Why this estate | Expected outcome |
|---|---|---|---|
| 1. Small Python API | A small, realistic REST or RPC service in Python with a handful of endpoints, its own tests, and no BrotherSBE history. | Baseline backend estate; the same shape the beginner study uses (`beginner-study.md`, section 3.2), so results are cross-checkable between the two studies. | Clean adopt and init; a modest change (matching one of the beginner study's outcome prompts) reaches a passing, evidence-backed PR-ready state with a T0 or T1 tier; consumer CI blocks a deliberately reintroduced idempotency defect and passes the clean baseline. |
| 2. Node/TypeScript service | A small Node or TypeScript backend service, different language and package ecosystem from estate 1. | Proves BrotherSBE's checks are not accidentally Python-specific; a different linting and dependency surface (`tools/sbe_score.py`'s stated language list includes `.js .ts`). | Same lifecycle as estate 1; consumer CI blocks a reintroduced silent-exception defect (a caught error that is swallowed rather than surfaced) and passes the clean baseline. |
| 3. Data/dbt project | A small dbt or equivalent SQL transformation project with a handful of models and a defined system of record. | Proves the data-domain path (grain, systems of record, historization) works outside BrotherSBE's own test fixtures. | Adopt and init succeed; a change to a model reaches design coverage including the data-model dossier artifact; consumer CI blocks a reintroduced wrong-grain defect and passes the clean baseline. |
| 4. SQL migration project | A small project whose changes are schema migrations (forward and reverse scripts) against a real or restorable database copy. | Exercises the migration hard gate specifically: forward and reverse run against a restored copy, row counts recorded, rehearsal id present (README.md, "migration" gate). | A clean migration produces a `migration-receipt.json` the gate accepts as PASS; a migration with no reverse script or no row counts reports NO-DATA, never PASS; consumer CI blocks a migration missing rollback evidence. |
| 5. Mixed monorepo | A single repository holding more than one of the above (for example a Python API and a dbt project side by side, with a shared CI config). | Review 12.2 item 7; proves BrotherSBE's tiering and gates apply correctly when a change might touch more than one domain at once, and that the write-scope fence (review, `tools/sbe_fence` behavior) does not get confused by multiple project roots in one tree. | Intake and design correctly scope to the actually-touched subproject; a change touching only the Python side does not demand the dbt side's data-model artifact, and vice versa; consumer CI runs the applicable subset, not the whole matrix, for a change scoped to one subproject. |
| 6. Malicious/poisoned repository fixture | A repository deliberately built to attack BrotherSBE itself: a prompt-injection payload inside a README or comment aimed at an agent reading it, a symlink or FIFO planted where a normal file is expected, and a forged or stale evidence receipt sitting in the tree already. | Review 12.2 item 12; the one estate that is adversarial by design, matching the hostile-repository corpus review 14's Security section requires ("Prompt-injection corpus passes within stated boundary", "Filesystem/path hostile corpus passes"). | BrotherSBE does not follow instructions embedded in repository content as though they came from the operator; the path/filesystem attack does not escape the intended working directory or crash the tool; the pre-planted forged or stale receipt is reported as FAIL or NO-DATA, never PASS, matching the evidence gate's stated behavior (README.md, "approval" and "ran" gate descriptions). |

## Fixture and result manifests

D13-C03's acceptance evidence is "exact fixture/result manifests from unrelated repositories"
(review 21.5). For each of the six estates above, the completed run must produce and retain:

- a manifest naming the exact repository (or fixture) used, its origin, and a statement that
  it was never used in BrotherSBE's own internal test suite;
- the exact commands run, in order, with their exit codes;
- the raw evidence output (gate verdicts, receipts, CI job logs) unedited;
- the expected-outcome column above, marked met or not-met, with the actual observed result
  quoted next to it.

Machine-readable capture fields for these manifests are in `metrics.json` under
`estate_matrix`.

## Release threshold

Review 13's external validation section does not give estate proof a separate numeric
threshold the way it does for the beginner and engineer studies; instead, review 14's binary
no-release gate ties it to D13 directly: no release-blocking control (which includes D13-C03)
may be NO-DATA or WAIVED at release. In practice that means: all six estates above must show a
completed run with the expected outcome met, or the gap must be fixed and the estate rerun,
before D13-C03 is accepted, before D13 can leave its 1.0/5 floor (review 1.2), and before
1.0.0 can be tagged.
