# sbe plan: dossier to task graph, deterministically

Status: spec of record for Loop 1 of the First-Rank Essentials program.
Source program: the founder-supplied essentials plan (Release A, capability 1).
This spec is the single answer to "what exactly does sbe plan derive, and what
does it refuse": the fixtures in tools/test_sbe_plan.py and the implementation
in tools/sbe_plan.py both read from here, and a disagreement between them is a
defect in one of the three, never a negotiation.

## Command

    bin/sbe plan <dossier-dir> [--write] [--json] [--strict] [--cwd <repo>]

Default (no --write): validate design/<change>/08-plan.json against the dossier
and the rules below. Absent plan file: NO-DATA naming the --write remedy.
--write: derive the plan from the dossier, write 08-plan.json, then validate
what was written with the same rules. Empty derivation writes NOTHING.

Exit codes follow src/brothersbe/cli.py convention (0 ok, 1 control failed,
2 usage), with one deliberate exception: an EMPTY plan (NO-DATA) exits 1 even
without --strict, because the essentials law says an empty plan must never
return success.

## Output file: design/<change>/08-plan.json

    {
      "schemaVersion": "1.0",
      "dossier": "<relative dossier dir>",
      "baseCommit": "<40-char sha from intake binding.head, or null>",
      "dossierDigests": {"<artifact>.md": "<sha256>", ...},
      "tasks": [
        {
          "id": "T01",
          "title": "...",
          "role": "writer" | "reviewer",
          "dependsOn": ["T.."],
          "owns": ["path", ...],
          "readOnly": ["<dossier-dir>/**"],
          "acceptance": ["..."],
          "verificationCommands": ["..."],
          "requiredEvidence": ["command-receipt"] | [],
          "requiredReviewers": ["backend" | "data" | "migration" | "evidence", ...],
          "dossierSources": ["03-adr.md#decision", "07-verification.md#row-2", ...]
        }
      ]
    }

Deterministic: same dossier bytes, same plan bytes (sort keys, fixed ID order,
no timestamps, no absolute paths).

## Derivation rules (--write)

Sources are the dossier's own structures and nothing else. A backticked token
inside an artifact counts as a repo path when it contains a slash or ends in a
known code extension and is not a command (no embedded whitespace). A
backticked token in the check column of 07-verification.md counts as a
command when it contains whitespace.

1. 03-adr.md, section "## Decision", non-empty: one writer task, T01,
   title and first acceptance criterion from the first sentence of the
   decision (quoting the dossier, never inventing), owns = the paths named in
   Decision plus Consequences, dossierSources 03-adr.md#decision.
2. 05-data-model.md, section "## Physical", non-empty AND naming at least one
   path: a migration triplet citing 05-data-model.md#physical:
   forward (writer, owns = the physical paths), reverse (writer, dependsOn
   forward), reconciliation (writer, dependsOn forward and reverse); all three
   own the physical paths, which is legal because dependency-ordered overlap
   is a handoff, and each writer task must own at least one path. The
   reverse and reconciliation tasks take their acceptance from the
   07-verification rows whose claim mentions reverse/rollback or
   reconcile/reconciliation. If no such row exists for either, the derivation
   FAILs: a migration whose dossier never states how it is undone or
   reconciled is a missing requirement, not a gap to invent an answer for.
3. Every row of the 07-verification.md table (columns: claim, check, when):
   one task per row, in row order, role reviewer, owns empty,
   acceptance = the claim cell, verificationCommands = the command-shaped
   backticked tokens in the check cell, dossierSources
   07-verification.md#row-N (N = 1-based data-row index).
   A row whose check cell holds no command still becomes a task (acceptance
   without commands is legal for non-executable criteria), and the human
   output counts these rows out loud as unexecutable.
4. Compatibility: when intake answers.changes_contract is true, at least one
   derived task's acceptance or title must mention compatibility, contract,
   or consumer (case-insensitive). If the dossier supports none, derivation
   FAILs naming the gap: an API change whose dossier never claims
   compatibility is a missing requirement. The planner never invents the task.
5. Decision-bearing calculation: a 07 row whose claim cell contains a digit
   is decision-bearing. Each such row needs independent derivation: either a
   second row citing the same claim, or two or more commands in its own check
   cell. Derivation FAILs naming the row otherwise.
6. Reviewers required per task, deterministically: any task whose owned or
   commanded paths mention a migration-shaped path (the detectors in
   src/brothersbe/impact.py are the reference) adds "migration";
   05-data-model-sourced tasks add "data"; everything adds "evidence";
   T01 adds "backend". Reviewer tasks own nothing, always.
7. requiredEvidence: ["command-receipt"] exactly when verificationCommands is
   non-empty, else [].
8. Overlap serialization: two writer tasks whose owns overlap get a
   dependsOn edge from the later ID to the earlier, so no two parallel tasks
   share a path by construction.
9. baseCommit: intake binding.head when present, else null, and null is
   stated as unmeasured in the human output, never silently.
10. dossierDigests: sha256 of every dossier artifact file read during
    derivation, so staleness is detectable later.

Nothing derivable at all (no decision, no physical, no verification rows):
NO-DATA, nothing written, exit 1.

## Validation rules (always run, both modes)

Each is a Check in a module-level PLAN_CHECKS registry in tools/sbe_plan.py
(sbe_checks.Check, severity gate, empty_expect NO-DATA), so the honesty
meta-test counts and exercises them. Verdicts: PASS, FAIL, NO-DATA only.

- citations: every task cites at least one dossierSource, every cited file
  exists in the dossier, and every cited #section resolves (a heading slug for
  .md sections, row-N within the 07 table's row count). A task citing nothing
  or citing a source that does not resolve is FAIL by task id: that is the
  planner-inventing-work case.
- ownership: every writer task owns at least one path; reviewer tasks own
  nothing; no two tasks not ordered by the dependency graph share an owned
  path (overlap between dependency-ordered tasks is legal, that is a
  handoff).
- acceptance: every task carries at least one acceptance criterion.
- graph: dependsOn ids resolve and the graph is acyclic. A cycle is FAIL
  naming the cycle.
- compatibility, migration, calculation: rules 4, 5 (validation-side, the
  calculation rule reads only tasks citing 07-verification.md#row-N anchors,
  so a filename digit can never read as decision-bearing), and the rule-2 FAIL
  condition above, re-checked against the plan as written (a hand-edited plan
  that deleted the reverse task FAILs here).
- freshness: recorded dossierDigests match the dossier files on disk (a
  dossier edited after planning is a stale plan, FAIL naming the files);
  recorded baseCommit matches intake binding.head when binding exists (FAIL
  on mismatch), and freshness reaches PASS only when the binding corroborates
  it; a digests-only match is NO-DATA prose, because a hollowed binding must
  not leave a PASS standing.
- nonempty: a plan with zero tasks is FAIL (it should have been NO-DATA and
  never written).

## Registry integration (the completion gate)

Every plan task maps onto sbe task open without reinterpretation:
owns -> --owns, readOnly -> --read-only (the flags as cmd_open actually spells them), baseCommit -> --base,
verificationCommands first entry -> --verify, role -> --role, id -> --id.
The fixture proving the gate: derive a plan, open its first task through
bin/sbe task open with fields read mechanically from the JSON, and the
registry postcondition machinery accepts it.

## What this deliberately does not do (documented limits)

No LLM anywhere: derivation and validation are parsing and rules. It cannot
read intent prose beyond the structures above, so a dossier written without
paths in its decision yields a plan whose T01 owns nothing, which the
ownership check then FAILs: the remedy is a better dossier, not a guess. Row
targets: docs/KNOWN-LIMITS.md gains this paragraph verbatim when the loop
lands.
