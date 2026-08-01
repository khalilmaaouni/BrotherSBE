# 05. Data model

These are the records the program depends on. Four of the seven exist on main
today. ReviewRecord does not exist at all, and OperationResult exists six times
in six shapes; those two absences are the reason Loops 3 and 4 exist.

Every entity names the system that owns it. An entity with no owning system named
is a defect, and so is a relationship with no cardinality.

## Conceptual: entities and meanings

- ProjectState: where one change stands right now, computed rather than stored, carrying stage, next action, blockers and evidence freshness. System of record: src/brothersbe/status.py.
- OperationResult: what one command returned, as a versioned envelope rather than six unrelated JSON shapes. System of record: src/brothersbe/cli.py, which is where the six existing JSON outputs are dispatched from.
- ReviewRecord: what a review found, whether it approved, and the exact commit it judged. Nothing durable holds this today, which is confirmed defect six of the plan review; system of record: the review record store that Loop 3 adds under the .sbe directory, written and read through src/brothersbe/converge.py.
- DecisionPackage: one decision somebody has to carry, with its inputs, its verdict and the evidence behind it. System of record: src/brothersbe/decisions.py.
- EvidenceReceipt: proof that a named check actually ran, bound to the commit it ran against, carrying the check kind Loop 2 adds as a recorded field. System of record: src/brothersbe/evidence.py, storing under the .sbe/evidence directory named at src/brothersbe/tasks.py line 72.
- WorkItem: one unit of program work with its write scope, its budget cap and its dependencies. System of record: program/work-items/, seven YAML files today, reconciled against program/PROGRAM.yaml.
- Event: one recorded thing that happened, appended under a file lock so a concurrent write cannot lose a line. System of record: tools/sbe_telemetry.py and its outcomes ledger.

## Relationships

- ProjectState to EvidenceReceipt: one-to-many, optional. One project state cites many receipts; a receipt is cited by the state of exactly one project. A state with zero receipts is honest and reports NO-DATA rather than a pass.
- ProjectState to ReviewRecord: one-to-many, optional. A project accumulates review records over time, and the state reads the most recent one; a record belongs to exactly one project. Zero records means the project has never been reviewed, which is not the same as having been reviewed and passed.
- ProjectState to WorkItem: one-to-many, optional. A project state covers many work items; each work item belongs to exactly one project.
- WorkItem to EvidenceReceipt: one-to-many, optional. Each work item earns its own receipts; each receipt is earned by at most one work item, and a receipt earned outside any work item is still valid evidence for the project.
- WorkItem to WorkItem: many-to-many, optional. Dependencies between work items form a graph, not a tree, which is why the plan check validates the graph rather than a list.
- ReviewRecord to DecisionPackage: one-to-many, optional. A review that finds something writes a decision package per finding somebody has to carry; each package traces back to exactly one review.
- EvidenceReceipt to DecisionPackage: many-to-many, optional. One package can cite several receipts and one receipt can support several packages.
- OperationResult to ProjectState: many-to-one, mandatory. Many command results describe the same project state; every result names exactly one project state it was computed from.
- DecisionPackage to Event: one-to-many, optional. Writing, waiving or closing a package appends events; each event belongs to exactly one package.
- EvidenceReceipt to Event: one-to-one, optional. Running the wrapper appends at most one event for the receipt it wrote.

## Attribute roles

| Attribute | Entity | Role |
|---|---|---|
| project_root | ProjectState | identifier |
| stage | ProjectState | status |
| next_action | ProjectState | descriptor |
| computed_at | ProjectState | temporal |
| envelope_version | OperationResult | descriptor |
| verdict | OperationResult | status |
| review_id | ReviewRecord | identifier |
| reviewed_commit | ReviewRecord | foreign key |
| approved | ReviewRecord | status |
| finding_count | ReviewRecord | measure |
| decision_id | DecisionPackage | identifier |
| receipt_id | EvidenceReceipt | identifier |
| check_kind | EvidenceReceipt | descriptor |
| bound_commit | EvidenceReceipt | foreign key |
| earned_at | EvidenceReceipt | temporal |
| item_id | WorkItem | identifier |
| token_cap | WorkItem | measure |
| depends_on | WorkItem | foreign key |
| event_id | Event | identifier |
| occurred_at | Event | temporal |

## Historization

ProjectState is never stored, only computed, so it has no history of its own by
design; its history is the history of the receipts and review records it reads.
That is deliberate: a stored stage is a stage that can be edited, and the whole
product exists to stop a verdict from being typed.

EvidenceReceipt, DecisionPackage, ReviewRecord and Event are append only. A
receipt is never rewritten, which is the founder gate on Loop 2: the schema
version bump is forward only and existing receipts are left exactly as they were
written. A review record goes stale when new commits land rather than being
updated in place, so the record of what was reviewed stays true even after the
code moves past it.

WorkItem keeps its status transitions rather than only its current status, so the
program ledger can be reconciled against what actually happened rather than
against the last thing somebody typed.

## Source systems and failover

| Entity | Source | Refresh contract | If the source is unavailable |
|---|---|---|---|
| ProjectState | Computed on demand from the repository | Recomputed every call, never cached | With no git metadata, the state reports NO-DATA with a stated reason rather than guessing a stage |
| OperationResult | Produced by the command that ran | Per invocation | A command that cannot produce a result returns a failure the caller can see, never an empty success |
| ReviewRecord | Written at the end of a review | Written once, then read until new commits make it stale | Absent means never reviewed, and that is reported as NO-DATA, never as approved |
| DecisionPackage | Written when a FAIL or a WAIVED line is printed | Written at the moment the decision is made | A package that cannot be written blocks the run rather than being skipped quietly |
| EvidenceReceipt | Written by the evidence wrapper | Written per check run, bound to the commit | A receipt whose bound commit is not the current head is stale and clears nothing |
| WorkItem | Committed YAML files under program/work-items/ | Edited by hand, reconciled against the ledger | A missing file is a missing work item, and the ledger reconciliation says so |
| Event | Appended under a file lock | Per event | A failed append is reported; the ledger never silently loses a line |

## The three lenses

1. Can this load reliably and recover after failure? The concurrency work in Loop
   2 is exactly this question asked of DecisionPackage and WorkItem, and its
   answer is a multi-process stress test rather than an opinion.
2. Can the real questions be answered without heroic joins? The question a user
   actually asks is "what do I do next", and today it needs a join across
   ProjectState, EvidenceReceipt and a ReviewRecord that does not exist. Loop 3
   makes that one call.
3. Is history preserved and is a stale answer distinguishable from a fresh one?
   Every record that carries a verdict binds to a commit, so freshness is a
   property of the data rather than a convention.

## Physical

EvidenceReceipt, DecisionPackage and ReviewRecord are JSON files in the
repository tree, not rows in a database, because the product must run with no
service of its own. The consequence is named in 04-technology-map.md: committed
receipts are self-poisoning today, because each committed receipt becomes a
covered file of the next diff. Loop 2 either excludes the store from the
covered-file diff or moves the receipts out of the committed tree, and that
choice is a founder gate rather than a writer's call, because it changes where a
user's evidence lives.

The migration path for the receipt schema is forward only. New receipts carry the
check kind field; old receipts do not and are read as unclassified, which clears
no obligation. The reverse path is to stop writing the field, which leaves every
already-written receipt readable by the old code. No migration rewrites a receipt
that exists.
