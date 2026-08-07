# Post rc.16 remeasure, executed 2026-08-06 evening (OWED-2 closed)

Measured against main at 25723a6, version 1.0.0-rc.18, by session 6e125dab.
Method per the standing recipe: the full workflow-copied battery on a DETACHED
worktree the session never edited, plus three scripted journeys re-run live by
independent agents, each journey then hostilely re-executed by a separate
refuter on a fresh checkout. Binary credit. Falsification tiers as in the
rc.15 round: [ran] means the command ran and its output is quoted.

## The battery, clean baseline

Run in a detached worktree at 25723a6 (log preserved at
BrotherSBE-delivery/baseline-battery-clean-rc18-25723a6.log): every step of
.github/workflows/brothersbe-gates.yml in order, exit 0 overall. [ran]

- 530 evals: 530 passed, 0 regressions.
- sbe_score strict, strict-soft: 12 checks, 9 PASS, 0 FAIL, 3 NO-DATA.
- Every tools/test_sbe*.py suite green, install-artifact and upgrade-rollback
  green.

Honesty note, recorded not hidden: the FIRST baseline attempt ran inside the
live checkout while this session wrote tester files there, and
test_sbe_install failed on exactly that contamination. That run was killed
and discarded; the numbers above come from the clean detached rerun. The
lesson (batteries only ever run in a worktree the session never edits) is in
STATE.md.

## The journeys, refuter-adjusted

**Journey 3, staff engineer: all four rc.15 frictions are FIXED.** [ran,
refuter CONFIRMED] Blocker 1 (status and lineage disagreeing about the same
receipt): identical verdicts now. Blocker 2 (plain status and the map naming
different next actions): both now emit resolve-missing-approval. Major 3
(design check dropping the tier override in its FAIL branch): the label
prints. Major 4 (status ignoring the override): status reads the overridden
tier. The refuter corrected two evidence details in the journey agent's
report (an exit code and a JSON field path) without overturning any verdict.

**Journey 2, team lead: 7 of 7 rows PASS, including the two new rows this
remeasure was ordered to score** (plain team view shows completion; shows
acknowledged ownership after handover). [ran, refuter ADJUSTED on evidence
quality only] Two NEW Minor frictions found by the refuter: writing an
evidence receipt inside the task worktree makes work finish fail confusingly
(placement trap), and sbe status --team rejects --cwd while the tools/
entry points accept it (CLI drift).

**Journey 1, beginner sandbox: completed end to end.** [ran, refuter
ADJUSTED] One claimed FAIL was OVERTURNED: the guide at rc.18 no longer
makes the hash-pinning promise the row quoted; it documents the divergence.
Remaining real findings:
- FAIL (Beginner): the "isolated" sandbox review pulls the machine's real
  vault and private-name registry into its output. Queued as a repair item.
- FAIL (Install): docs/KNOWN-LIMITS.md claims no tag was ever cut while two
  real tags exist and the rollback script passes against them. This is
  OWED-6 and its fix ships in the rc.20 train.
- FAIL (Install): no rollback verb on the recommended marketplace path.
  Loop C scope, dropped from the noon release gate by founder decision and
  named in the release limits.

## What this round did not measure

The GUI dimension (server deliberately unbuilt, unchanged), and the
maintainability row movement (no dedicated pass this round; next scheduled
remeasure covers it). Neither is claimed.
