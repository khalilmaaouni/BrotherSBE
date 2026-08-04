# 05. Data model

These are the records the four decisions in `03-adr.md` read or write. Every
entity names the system that owns it, and every relationship below carries
its own cardinality; an entity with no owning system named, or a
relationship with no cardinality, is a defect in this file.

## Conceptual: entities and meanings

- Dossier: one change under design review, the unit CR-06's discovery walker
  finds. System of record: the `design/` tree (the default root walked by
  `_design_roots`, `status.py:552-580`, extended by any `designRoots` entry
  in `.sbe/team-profile.json`).
- IntakeRecord: the five answered questions and the tier they compute,
  `00-intake.json`. System of record: owned by the Dossier it sits inside;
  read by both the single-project and the team discovery paths
  (`status.py:592-595` treats its presence as what makes a directory a
  dossier at all).
- EvidenceReceipt: proof that a named check kind actually ran, bound to the
  commit it ran against. System of record: the `.sbe/evidence` store
  (`tasks.py:97` DEFAULT_EVIDENCE_DIR), written by `sbe evidence run`
  (`evidence.py:1013-1014`) and, after Decision 2 of `03-adr.md`, by
  `_cmd_verify` (`cli.py:343`) for each of its three delegates.
- DecisionPackage: one verdict a run produced, with the evidence behind it.
  System of record: `.sbe/decisions` at the repository root or `decisions/`
  under a dossier (`decisions.py:117-120`), written by `_record_decisions`
  (`cli.py:141-151`) whenever `_cmd_verify` or a sibling command completes.
- StatusReport: one truthful answer to "where does this change stand,"
  computed on demand and never stored. System of record: `sbe status`
  (`src/brothersbe/status.py`); `build_report` for a single dossier
  (`status.py:465-479`), `build_team_report` for many (`:1091-1095`).
- TaskRegistryEntry: one open or closed fence over a write scope. System of
  record: `.sbe/tasks.json` (`tasks.py:24` REGISTRY_REL), read by
  `StatusReport` for ACTIVE CONFLICTS and by the writer stage described in
  `02-process.md` to hold the fence around each wave's lane.

## Relationships

- Dossier to IntakeRecord: one Dossier holds exactly one IntakeRecord
  (1:1). A directory carrying dossier artifacts without one is not yet a
  dossier this project's own tooling will check (`sbe_design.py`'s
  `check_artifacts`: "dossier artifacts are present ... but there is no
  00-intake.json, so no tier can be established").
- StatusReport to Dossier: one StatusReport covers one or more Dossiers
  (1:N). In flat single-project mode today this is one; after Decision 1 of
  `03-adr.md`, a StatusReport over a repository with nested dossiers covers
  every dossier the walker discovers, the same set `--team` already
  returns.
- Dossier to EvidenceReceipt: one Dossier is covered by zero or more
  EvidenceReceipts (1:N), optional. A receipt is matched to the dossier(s)
  whose files fall inside its `coveredFiles`; a Dossier with zero receipts
  is honest and reports MISSING EVIDENCE rather than a pass.
- Dossier to DecisionPackage: one Dossier accumulates zero or more
  DecisionPackages (1:N), optional. Each `sbe verify` run over a dossier
  writes one package for that run; zero packages means the dossier has
  never been verified, which is not the same as having been verified and
  passed.
- StatusReport to EvidenceReceipt: one StatusReport reads zero or more
  EvidenceReceipts (1:N). A StatusReport with zero receipts to read reports
  every applicable obligation under MISSING EVIDENCE rather than inventing
  a verdict of its own.
- StatusReport to DecisionPackage: one StatusReport reads zero or more
  DecisionPackages (1:N), optional. A DecisionPackage corroborates a
  StatusReport's account of what a prior run decided; a StatusReport
  computes its own answer whether or not one exists.
- StatusReport to TaskRegistryEntry: one StatusReport reads zero or more
  TaskRegistryEntries (1:N). Used for ACTIVE CONFLICTS: an open
  TaskRegistryEntry whose `ownedPaths` overlap another entry's is surfaced
  as a finding, never silently merged.
- TaskRegistryEntry to EvidenceReceipt: one TaskRegistryEntry cites zero or
  one EvidenceReceipt (1:1), optional. `RECORD_FIELDS` (`tasks.py:52`)
  carries `evidenceId` as one value, not a list, so a task closes against at
  most one bound receipt.
- EvidenceReceipt to DecisionPackage: many-to-many, optional. One
  DecisionPackage can be written from several delegate receipts in the same
  `sbe verify` run, and one receipt (a `sbe_design.py --strict` run, say)
  can support more than one package if re-read by a later verification.

## Attribute roles

| Attribute | Entity | Role |
|---|---|---|
| dossier_path | Dossier | identifier |
| tier | IntakeRecord | descriptor |
| answers | IntakeRecord | descriptor |
| override | IntakeRecord | status |
| receipt_kind | EvidenceReceipt | descriptor |
| bound_commit | EvidenceReceipt | foreign key |
| covered_files | EvidenceReceipt | descriptor |
| earned_at | EvidenceReceipt | temporal |
| decision_id | DecisionPackage | identifier |
| verdict | DecisionPackage | status |
| source_command | DecisionPackage | descriptor |
| project_root | StatusReport | identifier |
| next_action | StatusReport | descriptor |
| stores_inspected | StatusReport | descriptor |
| generated_at | StatusReport | temporal |
| task_id | TaskRegistryEntry | identifier |
| owned_paths | TaskRegistryEntry | descriptor |
| status | TaskRegistryEntry | status |
| evidence_id | TaskRegistryEntry | foreign key |

## Historization

StatusReport is never stored, only computed, exactly as
`design/final-release-program/05-data-model.md` records for ProjectState,
and for the same reason: a stored answer is an answer that can be edited by
hand, and this program exists to stop a verdict from being typed rather than
proved.

EvidenceReceipt and DecisionPackage are append only. A receipt written by
Decision 2's `_cmd_verify` minting is never rewritten in place; a second
`sbe verify` run on a new commit earns a new receipt bound to that commit,
and the old one is read as stale rather than updated. A DecisionPackage is
the same: `_record_decisions`'s structural promise (`cli.py:141-151`) is
that it cannot move a verdict, only record one.

IntakeRecord keeps its `override`/`override_reason` fields rather than
silently editing `tier`, so a moved tier is auditable as a decision rather
than invisible as an edit, exactly as this dossier's own `00-intake.json`
would be checked.

TaskRegistryEntry keeps its full status transition (open, closed,
abandoned) rather than only the current value, so the wave discipline in
`02-process.md` (one writer per file, reviewers read-only) is something a
reader can reconcile against what the registry actually recorded, not
against the last state somebody typed.

## Source systems and failover

| Entity | Source | Refresh contract | If the source is unavailable |
|---|---|---|---|
| Dossier | Walked from the repository tree on demand | Recomputed every call | No `design/` root and no configured design root: the walk finds nothing and StatusReport reports NO-DATA, never a false "clean" |
| IntakeRecord | `00-intake.json`, committed | Read per call | Absent: the dossier is not yet a dossier this tooling checks, per `check_artifacts` |
| EvidenceReceipt | Written by the evidence wrapper or, after Decision 2, by `_cmd_verify` | Written per check run, bound to the commit | A receipt whose bound commit is not the current head is stale and clears nothing |
| DecisionPackage | Written by `_record_decisions` at the end of a verify-class command | Written per run | A package that cannot be written blocks the run rather than being skipped quietly (`cli.py:141-151`) |
| StatusReport | Computed on demand | Recomputed every call, never cached | With no git metadata, NO-DATA with a stated reason, never a guessed stage |
| TaskRegistryEntry | `.sbe/tasks.json`, committed, lock-guarded | Read per call | Missing registry: zero active conflicts reported, not a silent assumption of none |

## The three lenses

1. Can this load reliably and recover after failure? EvidenceReceipt writes
   under Decision 2 go through the same store-exclusion machinery
   (`status.py:161-172`, `evidence.py:686`) that already prevents a receipt
   from poisoning itself; a dirty-tree receipt fails closed to NO-DATA
   rather than reading as evidence for a tree it did not actually examine.
2. Can the real question be answered without a heroic join? The question a
   user actually asks is "what do I do next on this dossier," and before
   Decision 1 it needed a join `sbe status` alone could not do (walk the
   design tree, then read the intake). After Decision 1, one call answers
   it for a nested dossier the same way it already does for a flat one.
3. Is a stale answer distinguishable from a fresh one? Every EvidenceReceipt
   and DecisionPackage binds to a commit, so `sbe status` can and does say
   "stale" rather than silently reusing an answer from before the tree
   moved.

## Physical

EvidenceReceipt and DecisionPackage are JSON files under `.sbe/`, not rows
in a database, for the same no-service reason
`design/final-release-program/05-data-model.md` states for its own entities:
the product runs with no service of its own. Decision 2 does not change
where receipts live; it changes who writes one by default. The migration
path stays forward only: a receipt written before Decision 2 ships carries
no `check_kind` beyond what `sbe evidence run --kind` already recorded by
hand, and is read as it always was; nothing here rewrites an existing
receipt.
