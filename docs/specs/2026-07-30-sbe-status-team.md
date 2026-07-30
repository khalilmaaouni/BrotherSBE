# sbe status --team: one blocker-first view across every active change

Status: spec of record for Loop 5 of the First-Rank Essentials program
(Release C, capability 5). Extends the existing src/brothersbe/status.py; the
fixtures in tools/test_sbe_status_team.py and the implementation read from
here. The single-change sbe status behavior is untouched.

## Commands

    bin/sbe status --team [--cwd <repo>]
    bin/sbe status --team --json

## Discovery (never assumes one dossier at the root)

From the repository root: every directory under design/ (and any directory
configured in .sbe/team-profile.json under a "designRoots" list, when
present) containing a 00-intake.json is an active change. For each change:
the dossier artifacts, 08-plan.json, 09-convergence.json, the shared
.sbe/tasks.json registry (records matched to changes by their plan task ids),
worktrees named by open records, receipts in .sbe/evidence, an approval
report when one was saved (10-approval.json, written by sbe pr verify --json
redirected by the user; absence is normal), and forced closures and dirty
overrides from the registry records.

## Display order (deterministic, most severe first)

1. Broken claims (a receipt that fails evidence.verify)
2. Merge blockers (the existing single-change machinery, per change)
3. Scope conflicts (open tasks whose owned paths overlap across changes,
   and any postcondition violation in an open task's worktree)
4. Stale evidence (receipts bound to a commit that is no longer the change's
   head; convergence report bound to a superseded head)
5. Missing approvals (an approval report absent or its FINAL not PASS,
   stated as observed; no report is NO-DATA prose, never an accusation)
6. Convergence failures (09-convergence.json FINAL FAIL or REVIEW-REQUIRED)
7. Active tasks (open records: id, agent, worktree, scope clean or not)
8. Ready tasks (plan tasks whose dependencies are closed clean and which
   have no open record)
9. Completed changes (every plan task closed clean)
10. Next action, one line per change, derived from the highest-severity
    finding above (the remedy sentence, not a scolding)

A change with nothing at severities 1 to 6 prints its active and ready tasks
and its next action. FORCED closures print FORCED wherever the record
appears, at every severity.

## JSON contract (each finding, machine-first)

    {
      "change": "<dossier dir name>",
      "severity": 1..10,
      "verdict": "PASS" | "FAIL" | "NO-DATA" | "REVIEW-REQUIRED",
      "evidence": "<file, receipt id, task id, or command that grounds it>",
      "commit": "<sha the finding binds to, or null>",
      "owner": "<agent name or null>",
      "nextAction": "<one line>",
      "basis": "observed" | "derived" | "unavailable"
    }

basis is the honesty field: observed means read from a file or command this
run; derived means computed from observed values; unavailable means the
source could not be read, and unavailable findings keep their severity slot
visible rather than vanishing (a section that cannot be read is not a clean
section). GitHub is never called by status: approval facts come only from a
saved report, and their staleness against the current head is derived and
labeled as derived. Exit 0 only when no finding has severity 1 to 6.

## Essential fixtures (tools/test_sbe_status_team.py)

multiple dossiers with independent states listed together; two changes whose
open tasks own overlapping paths surfacing as a scope conflict naming both;
a stale approval report (head moved) at severity 4/5 with basis derived; a
forced closure printing FORCED; a change with a plan and no convergence
report showing NO-DATA at severity 6, not PASS; a missing plan showing next
action "run sbe plan"; deterministic ordering (same tree, byte-identical
output, no timestamps in the human view); unavailable registry (unreadable
tasks.json) reported as unavailable, exit nonzero; --json findings carrying
every contract field for every finding.
