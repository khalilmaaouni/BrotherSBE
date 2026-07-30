# sbe work: isolated implementation, no autonomous merge rights

Status: spec of record for Loop 2 of the First-Rank Essentials program
(Release A, capability 2). Builds on docs/specs/2026-07-30-sbe-plan-derivation.md
and the existing task registry (src/brothersbe/tasks.py). The fixtures in
tools/test_sbe_work.py and the implementation in src/brothersbe/work.py both
read from here.

## Commands

    bin/sbe work start  <task-id> --plan <dossier>/08-plan.json [--worktree-dir <dir>] [--agent <name>] [--cwd <repo>]
    bin/sbe work check  <task-id> [--cwd <repo>]
    bin/sbe work finish <task-id> [--force] [--cwd <repo>]
    bin/sbe work remove <task-id> [--override-dirty <reason>] [--cwd <repo>]

## The single source of task state is the existing registry

.sbe/tasks.json, exactly as src/brothersbe/tasks.py defines it. sbe work never
invents a second state file: a plan task is complete when a registry record
with its id is closed clean. 08-plan.json is never mutated by work; it stays
byte-stable so plan determinism holds.

## start

1. Validate the plan file with the sbe plan validation checks; any FAIL
   refuses start, quoting the failing check.
2. Resolve the task id in the plan; unknown id is usage error.
3. Dependencies: every dependsOn id must be closed clean in the registry.
   An open or absent dependency refuses start naming it. A dependency closed
   FORCED does not count as clean and refuses start naming the forced close.
4. Collisions: an existing branch sbe/<change-id>/<task-id>, an existing
   worktree directory, or an open registry record with this id refuses start
   naming the collision. change-id is the dossier directory basename.
5. Create branch sbe/<change-id>/<task-id> at the plan baseCommit when set
   and resolvable, else at HEAD (stated out loud as unpinned).
   Create a dedicated git worktree at <worktree-dir>/<repo-name>-sbe-<task-id>
   (default worktree-dir: the repository's parent directory).
6. Open the registry record through the existing tasks machinery with fields
   read mechanically from the plan: owns, readOnly, baseCommit, first
   verification command, role, id. The record's worktree field is the created
   worktree path.
7. Print, from the plan: acceptance criteria, every verification command,
   dossier sources. The engineer starts with the contract in front of them.

## check (read-only, never mutates)

Report: branch and worktree (and whether both still exist), owner and role,
changed files against the task scope (the registry postcondition machinery),
scope violations by name, dependency state per dependsOn id, verification
evidence present or missing (evidence receipts bound to the task, via the
existing evidence store when configured), and one final line: CLOSABLE or
NOT CLOSABLE with the reasons. Exit 0 when closable, 1 when not.

## finish

1. Run the registry postcondition for the task in its worktree; any
   out-of-scope write refuses closure naming the paths.
2. Verification: the task's verification command must have a receipt in the
   evidence store bound to the worktree's current commit; absent receipt
   refuses closure as NO-DATA prose naming the command (an agent SAYING it
   ran is not evidence).
3. All checks pass: close the registry record clean. The plan task is now
   complete by the single-source rule.
4. --force closes anyway but the record carries status forced, check and
   status surfaces print FORCED loudly, and a forced close never satisfies a
   dependency (see start rule 3).

## remove

Deletes the worktree for a CLOSED task; the branch is left in place and says so, because branch deletion is not one of this module's allowed git mutations (worktree add and remove, branch creation), and deleting history is the human's call. A dirty worktree
(uncommitted changes) refuses removal unless --override-dirty with a nonempty
reason is given; the override is recorded on the registry record
(overrideDirty: reason) so the human decision is permanent, visible history.
An open task's worktree is never removed.

## Hard boundaries (each one a fixture)

- One writer task, one branch, one worktree. No sharing.
- No merge, no rebase onto the default branch, no push, no deploy, ever.
- Reviewer-role tasks stay read-only: start refuses a worktree for a
  reviewer task with owned paths (the plan validator already FAILs that
  shape; work refuses it independently rather than trusting its input).
- Nothing closes clean on an agent statement alone: closure needs the
  postcondition AND the receipt.

## Essential fixtures (tools/test_sbe_work.py)

branch and worktree collisions; incomplete and forced dependencies refused;
an out-of-scope file created in the worktree via plain shell caught at
finish; finish without a receipt refused as NO-DATA; a reviewer task
attempting to own paths refused; dirty removal refused then allowed with a
recorded override; forced close visible in check output and not counted as a
clean dependency; registry integration end to end (plan, start, edit in
scope, receipt, finish, remove).
