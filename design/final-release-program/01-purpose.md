# 01. Purpose brief

## Problem

BrotherSBE has a strong assurance engine and no single, honest path through it.
A review of the release plan dated 2026-08-01 confirmed ten defects against the
code line by line, and five of them are the same shape: the product knows more
than it can say in one place.

The evidence classifier decides which obligation a receipt satisfies by matching
substrings of the recorded command line (src/brothersbe/status.py, the
`_receipt_kinds` function at line 107), so a receipt recording a command that
runs no check at all can clear the design, gate and score obligations. The
security promise is written more absolutely than the code supports: SECURITY.md
line 11 says the product makes no network calls while src/brothersbe/prverify.py
line 120 calls the GitHub API. Concurrent writes to the decision store can lose
records, and the store's own docstring at src/brothersbe/decisions.py lines 1154
to 1157 admits it. There is no one lifecycle: the guided skills in skills/ and
the status surface in src/brothersbe/status.py each work out the stage on their
own and can give contradictory next actions on the same repository. A review's
findings and approval persist nowhere the status surface can read them.

None of that is a missing feature. It is the same product telling a user two
different things, and a tool that says two things cannot be trusted to say one.

## Users

Four people, and today each of them pays for the same gap.

The beginner wants to finish one small project without reading the internal
architecture. Today the next action depends on which surface they happen to ask,
so they learn to ask twice and trust neither answer.

The engineer wants evidence they can defend in a review. Today they can hand
assemble something that passes, because the classifier reads a command line as a
string rather than a declared kind, so the strongest control in the product has a
door in it.

The expert wants to extend the tool without breaking its guarantees. Today the
lifecycle rules are spread across the skills and the status code, so a change in
one place silently disagrees with the other.

The team lead wants to see where several changes stand at once. Today
`sbe status` and `sbe status --team` resolve the same repository to different
projects, because src/brothersbe/status.py carries two locators
(`_design_roots` at line 478 and `_team_changes` at line 509) that read different
layouts.

## Success criteria

Observable conditions, each of which someone can check.

1. Every surface that tells a user what to do next computes that answer from one
   place, and on a fixed set of test repositories the command line and the
   guided skills give the same answer every time.
2. A receipt says which kind of check it ran as a recorded field, and a command
   that ran no check clears no obligation. The bypass that works today is kept as
   a test fixture that must stay red under the old behaviour and green under the
   new one.
3. Every sentence in SECURITY.md and docs/THREAT_MODEL.md is true of the code on
   main, with the two network paths (`sbe pr verify` and install.sh) named rather
   than denied.
4. Every test suite in tools/ runs in the merge gate. Today three of them do:
   `ls tools/test_*.py` in this worktree returns 17 files, and
   .github/workflows/brothersbe-gates.yml names three of them, at lines 143, 150
   and 152. The plan review counted 18 suites against an earlier commit;
   reconciling that count is part of Loop 1's own work.
5. Concurrent writes to the decision store and the task registry lose nothing
   under a multi-process stress test.
6. A review's findings, its approval, and the commit it judged are recorded
   somewhere the status surface and the convergence check both read, and go
   stale when new commits land.
7. Install, update, rollback and uninstall each run successfully from a clean
   machine on the two platforms the project claims to support.
8. At least five unrelated beginners and five unrelated engineers complete the
   agreed validation scenarios, which is the floor the ratified covenant in
   program/MASTER-PLAN.md section 2 already sets.

## Non-goals

These are cut from 1.0 deliberately, and each cut has a reason.

- **A local web GUI server.** It contradicts the non-goal list in
  program/MASTER-PLAN.md and it would make the published "no server" security
  claim false, along with the drift test that checks it. The visual surface for
  1.0 is the existing offline map template in skills/help/map-template.html plus
  the explainer under docs/explainer.
- **A team dashboard.** The team operating model already ratified this week
  chose one-way exporters into the boards teams already use. Building a
  dashboard would contradict a decision that is days old.
- **Host adapters beyond Claude Code.** The master plan puts cross-host adapters
  in wave 4. The public docs scope the product to Claude Code today and that is
  honest, so 1.0 keeps that scope.
- **Three-team pilots.** The ratified validation floor is five beginners and five
  engineers. Team pilots move to 1.1 rather than inflating the 1.0 gate.
- **Hosted anything, receipt history rewrites, and new gates without an escaped
  defect to justify them.**

## The release covenant

BrotherSBE 1.0 ships only when every sentence the product says about itself is
true of the code on main, when one lifecycle computes the next action and every
surface renders that same answer, when evidence is earned by a wrapper rather
than hand assembled and a receipt names the kind of check it ran, when a review's
findings and approval are durable and go stale on new commits, when install,
update, rollback and uninstall have each been executed successfully from a clean
machine on both supported platforms, when at least five unrelated beginners and
five unrelated engineers have completed the agreed validation scenarios, and when
no critical or high severity release finding remains open. A calendar date, a
feature count, a test count or a marketplace submission does not waive any of
that, and the founder publishes the tag.

## What breaks if this is wrong

If the program ships without closing these defects, the product's worst failure
is not a crash. It is a green verdict over evidence nobody earned. A user shows a
passing gate to a reviewer, the reviewer trusts it, and the thing the gate exists
to catch goes to production anyway. That is worse than having no gate, because a
gate that is wrong is believed.

The second blast radius is the security claim. A published sentence saying the
product makes no network calls, next to code that calls the GitHub API, is the
kind of finding that ends a tool's credibility in one screenshot even though
docs/KNOWN-LIMITS.md already tells the truth.

The third is quieter. If the lifecycle stays split between the guided skills and
the status code, every future change has to be made twice and will eventually be
made once, and the two halves drift apart again.
