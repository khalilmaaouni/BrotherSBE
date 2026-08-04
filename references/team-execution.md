# Team execution

LOAD WHEN: `/brothersbe:work` is resolving ready tasks, dispatching an implementation-worker
against a worktree, or a human is taking over a task another writer has claimed.

(The compact reference `skills/work/SKILL.md` points at. That file carries the full operational
steps with their exact commands; this file carries the four things worth checking against
independently of the skill's own prose: the flow compressed to six stages, the parallelism
conditions, the one-writer law as it applies here, the takeover protocol, and the shape a
worker's report must carry.)

## The six-stage flow

1. **State.** `sbe status --json`: `nextAction`, `scope.storesInspected`. No intake and no
   dossiers anywhere means no plan exists; nothing is invented past that point.
2. **Resolve.** The active dossier and its `08-plan.json`, one only; more than one dossier
   carrying ready or running work is named and asked about, never guessed. `sbe work brief`'s
   own plan-validation rule is the validation report; nothing re-derives it by hand.
3. **Ready.** Severity 8 findings from `sbe status --team --json` for the active dossier: a
   task's dependencies are all closed clean and it carries no registry record yet.
4. **Overlap and select.** Two `owns` sets overlap by the same rule `sbe task open` already
   enforces (see below). Disjoint, dependency-closed, independently verifiable candidates may run
   together, up to three; one is the default and the safe choice.
5. **Brief, start, dispatch.** `sbe work brief --out .sbe/briefs/<id>.json`, then
   `sbe work start <id>`, then one `implementation-worker` dispatch per task, into the worktree
   `work start` opened, given the brief's file path, never its contents pasted inline.
6. **Verify and close.** `sbe work check <id>` reads the actual diff and the actual evidence
   store; only a CLOSABLE verdict is followed by `sbe work finish <id>`. A worker's own report is
   ingested as the compact contract only, never trusted as proof by itself.

## Parallelism conditions

Raise the run from one task to two or three only when ALL of the following hold for the entire
selected set, not merely for the newest addition to it:

- scopes are pairwise disjoint (step 4's overlap rule, checked between every pair, not just
  consecutive ones)
- every dependency for every selected task is already closed clean
- each task is independently verifiable by its own `verificationCommands`, with no shared
  generated manifest another selected task also writes
- running them together saves material time over running them one after another

Any one condition failing drops the run back to one task, or to running the overlapping pair
sequentially instead of together. Three is the ceiling regardless of how many tasks are ready.

## The one-writer law, as this skill applies it

A claim overlaps another claim when they name the same path, when one is a directory or glob
prefix that would swallow the other, or when a case-folded filesystem probe confirms the two
spellings name one entry. This is not a rule invented for this skill: it is `paths_overlap` in
`tools/sbe_fence_hook.py`, the same function `sbe task open` already runs against every other
open task before it will claim a path. This skill's overlap check in step 4 of the flow is a
read of the plan ahead of dispatch, using the identical rule, so a collision is caught before a
worker is ever started rather than only at the close `sbe task open` would have refused anyway.

Dispatching a worker never asks the Agent tool for its own worktree-isolation behavior. `sbe work
start` already created the one worktree a task is fenced to, recorded on the registry; a second
worktree created independently of that record would be exactly the undeclared, uncompared claim
this law exists to catch, the same failure mode `docs/book/16-working-as-one-team.md` names for
a shared "staging" folder nobody declared.

## The takeover protocol

On an explicit "I will take over `<task-id>`":

1. Stop, or wait for, any worker currently dispatched against that task id.
2. Read the registry record: its `worktree` and its branch.
3. Run `git -C <worktree> status --short` and show what is uncommitted. Nothing is deleted,
   reset, or reverted to get there.
4. State plainly that only the human writes the claimed scope from this point.
5. Record the change as a fence note stated to the operator: which task, which worktree, which
   branch, and that the human now holds it.

No registry field is written to make step 5 true. `RECORD_FIELDS` in `src/brothersbe/tasks.py`
carries an `agent` field, but the only commands that touch it are `sbe task open` (sets it once,
at creation) and `sbe task close` (never touches it). Nothing re-expresses an ownership transfer
on an OPEN record without ending the record, and ending it would close the fence rather than
hand it over, which is not what a takeover means. So this skill adds no owner-transition command
to `tasks.py`: the registry's `agent` field keeps naming whoever `sbe work start` opened the
record as, exactly the shape chapter sixteen already documents for a human handoff (the outgoing
owner stays the tool's recorded owner until the incoming owner explicitly resumes, and the
mismatch between "who the registry names" and "who is actually typing" is the fence note's job
to carry, not the registry's). Acceptance: one owner true at any moment (the fence note, read
alongside the registry record, always answers it); resuming an agent on a taken-over task
requires an explicit instruction, never an automatic re-dispatch; no dirty work is ever deleted
to hand a task over.

## The worker response contract

`agents/implementation-worker.md` returns exactly nine fields, every run: Result (done, blocked,
or refused, one sentence why), Task, Commit (baseline confirmed against, and produced), Files
changed (all inside `scope`), Acceptance criteria (each marked met or not met), Verification run
(the exact command and its result), Evidence receipt (the path, or "not required"), Open concern
(or "none"), Recommended next action. This skill reads exactly those nine fields and nothing
else from the worker's own words; the actual proof is `sbe work check`'s independent read of the
diff and the evidence store in step 6, run regardless of what Result says.
