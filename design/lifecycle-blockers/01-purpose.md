# 01. Purpose brief

## Problem

Five blockers remain open against `docs/release-1.0/STATUS.md` after the plan
review of 2026-08-04, and all five are the same shape: the engine already
computes a truthful answer and the surface a user actually reads does not
consume it. `docs/release-1.0/FABLE-PLAN-REVIEW.md` section 5 states the
correction plainly: "the correct first move is not to build a new kernel. It
is to make the presentation layer consume the engine state that exists."
This dossier designs that correction for the five blockers still marked
`open` in the STATUS.md table:

- **CR-07, "absence confused with non-applicability."** Verdict: CONFIRMED,
  reproduced. Reproduced live on this repository: `sbe status . --json` and
  four hard gates over `design/final-release-program` report NO-DATA on all
  four, and the process exits 0 (`tools/sbe_gate.py:1567` starts `fails=0`,
  `:1615-1616` only a FAIL increments it, `:1630-1633` a strict exit is
  nonzero only when `fails` is nonzero). `skills/next/SKILL.md` rung 5
  (`:31-33`) reads "anything not green" as "run `/brothersbe:verify`" with no
  branch for a legitimate NO-DATA, so a tier that owes nothing loops forever
  between rung 5 and a verify command that mints nothing.
- **CR-08, "verification does not complete proof atomically."** Verdict:
  CONFIRMED, reproduced. `_cmd_verify` (`src/brothersbe/cli.py:343`) runs
  three delegates and writes a decision package
  (`cli.py:363` to `.sbe/decisions`, `decisions.py:117`), never a receipt.
  Receipts exist only through `sbe evidence run --out <path>`
  (`evidence.py:940` marks `--out` required, write at `:1013-1014`), a
  separate command with no default path. `sbe status` looks for
  `<root>/.sbe/evidence` (`status.py:344`, `tasks.py:97`) and, finding
  nothing a default `sbe verify` run wrote, reports every obligation under
  MISSING EVIDENCE. A tool that passes a gate and leaves no evidence a
  reviewer can point to is not proof; it is a claim.
- **CR-06, "status cannot locate the documented layout."** Verdict: PARTIAL,
  `--team` finds dossiers that single-project mode does not. Reproduced
  live: `sbe status . --json` on this repository returns `storesInspected`
  all null, `nextAction` "nothing blocking here", exit 0, while
  `sbe status --team --json` on the identical tree returns the changes
  `final-release-program` and `team-operating-model` with four findings.
  `build_report` searches four flat paths at the repository root
  (`status.py:342-345`); the module's own docstring (`:28-33`) names the
  limit: "a dossier nested under `design/<change>/` is not discovered by
  this wave." The team walker that already solves this
  (`_design_roots` at `status.py:552-580`, `_team_changes` at `:583-596`)
  sits unused by the single-project path.
- **CR-10, "beginner experience is prompt-driven."** Verdict: PARTIAL, engine
  state already exists and is ignored. The beginner skills carry 21
  independent probes across `start`, `next`, `status` and `help`
  (cr0610 scout inventory) that interpret rendered prose instead of the
  `nextAction`, `notes` and `scope.storesInspected` fields `sbe status --json`
  already emits (`status.py:465-479`, serialized at `cli.py:767-769`). No
  skill anywhere passes `--json` (`grep -rn -- "--json" skills/ agents/`
  returns nothing). `skills/next/SKILL.md:26-27` names a summary section
  that does not exist in the rendered output at all.
- **CR-03, "install tests prove syntax, not installation."** Verdict:
  PARTIAL, narrowed. `docs/release-1.0/FABLE-PLAN-REVIEW.md` section 7
  corrects the original claim: update and rollback are already tested by
  `scripts/test-upgrade-rollback.sh` and `scripts/test-install-artifact.sh`,
  both wired into CI. What remains open is narrower and named: plugin
  activation, hooks firing from an installed layout, paths containing
  spaces on the installer's own side (`SCRIPT_DIR`, `$HOME`, `clone_dest`),
  and one concrete defect, that `install.sh`'s `run_doctor` (`:255-266`)
  runs from `cd "$SCRIPT_DIR"` (`:108`) and so grades the BrotherSBE clone
  rather than the target it just initialized.

None of these five is a missing feature. Each is the same product telling a
user two different things, or telling them nothing when it has an answer
sitting in memory, which is the defect class this whole release program
exists to close (`design/final-release-program/01-purpose.md`, "the same
product telling a user two different things").

## Users

The same four people the final-release-program dossier names, and each pays
for a narrower slice of the same gap here.

The beginner runs `/brothersbe:next` on a small project and, if that
project's tier legitimately owes no evidence yet, is told to run
`/brothersbe:verify` (CR-07's loop), which runs the gates again, changes
nothing, and returns the beginner to the same rung. The loop is skill text,
not engine behavior: `tools/sbe_gate.py:1615-1633` never counts NO-DATA
against the exit code, so the engine already knows the four gates are not a
failure. The skill does not ask it.

The engineer runs `sbe verify` expecting the pass they see to be backed by
something a reviewer can open. It is backed by a decision package that
records a verdict, never by a receipt that records what ran, so `sbe status`
on the same tree reports every obligation MISSING even though verify just
printed PASS three times.

The team lead runs `sbe status` on a repository laid out exactly the way the
project's own docs describe, a change under `design/<name>/`, and is told
"nothing blocking here" over a tree that `sbe status --team` reads
correctly. Two commands, same repository, two different truths.

The expert extending the beginner skills inherits 21 probes that re-derive
answers the engine already computed, so a change to `status.py`'s next-action
logic can silently stop matching what the skills print, and nothing catches
the drift because the skills never call the field that would have caught it.

## Success criteria

Observable conditions, each checkable against this repository.

1. `sbe status . --json` on this repository's own dossiers (or an equivalent
   fixture with a nested `design/<change>/` layout) reports the same
   dossiers `sbe status --team --json` already finds, either directly or by
   naming them in `scope.storesInspected` and delegating to the team
   machinery, per the flip condition in Decision 1 of `03-adr.md`.
2. A default `sbe verify` run on a clean tree mints a receipt for each of the
   three delegate checks it runs, bound to the commit it ran against, and
   `sbe status`'s MISSING EVIDENCE section on that same tree is empty for
   every obligation the tier requires.
3. Rung 5 of `skills/next/SKILL.md` has a NO-DATA branch: four gates
   NO-DATA plus an empty `missingEvidence` for the declared tier proceeds to
   a later rung, never loops back into `/brothersbe:verify`.
4. `skills/next`, `skills/verify`, `skills/status` and `skills/start` read
   `nextAction`, `notes` and `scope.storesInspected` from `sbe status --json`
   (and `sbe doctor --json` where the current probes duplicate it) instead
   of re-deriving the same answers from rendered prose, and the parity
   between the guided skills and the command line (the property
   `docs/release-1.0/STATUS.md` already asks for under CR-10) becomes
   testable rather than assumed.
5. `install.sh`'s doctor step grades the target it just initialized, not its
   own checkout, and an installed-layout test replays the PreToolUse fence
   hook contract from the actual `hooks/hooks.json` a real install ships,
   not only from the checkout.

## Non-goals

Cut from this dossier deliberately, each with a reason, mirroring the scope
discipline `design/final-release-program/01-purpose.md` already sets for the
program this dossier is a part of.

- **A new lifecycle package.** `docs/release-1.0/FABLE-PLAN-REVIEW.md`
  section 5 is explicit that this is a presentation-layer correction over an
  engine state that already exists, "not a new kernel." No new module tree
  is created by any of the four decisions in `03-adr.md`.
- **A new verdict word.** The vocabulary PASS, FAIL, NO-DATA is closed
  (`tools/sbe_checks.py:1695` converts a fourth word to FAIL); applicability
  for CR-07 lives in the reporting and exit layer, never as a new verdict.
- **A wrapper command that re-renders gate output for skills.** `sbe status
  --json` already carries `nextAction` and `basis`; a second presentation
  surface would be one more thing to keep in parity with the one that
  already exists, which is the exact defect this dossier closes.
- **An opt-in flag for CR-08's fix.** The defect is the default path; making
  receipt minting opt-in leaves CR-08 reproduced for every user who does not
  know the flag exists.
- **A full `install.sh` redesign.** CR-03's fix is bounded to the run_doctor
  target-grading defect, one mechanical hook-firing test, and space-in-path
  coverage for the installer's own variables; the two branches of
  `install.sh` (marketplace-direct and clone fallback) are unchanged.

## What breaks if this is wrong

If CR-07 stays open, the beginner loop the whole product exists to serve
sends a user with nothing left to do back into a command that changes
nothing, and the honest answer, "you are done for this tier," never
surfaces. A tool that cannot say "nothing is wrong" is a tool nobody
finishes using.

If CR-08 stays open, `sbe verify` prints PASS and `sbe status` prints
MISSING EVIDENCE about the same run, on the same commit, in the same
minute. A reviewer who trusts the first sentence and a reviewer who trusts
the second reach opposite conclusions about the same change, and the
product's whole claim, that its verdicts can be defended, breaks on its own
default path.

If CR-06 stays open, the layout the project's own documentation describes,
a dossier under `design/<name>/`, is invisible to the one command most
users run first. The team walker already proves the fix is not a research
question; it is an unused answer.

If CR-10 stays open, every future change to the next-action logic in
`status.py` has to be re-implemented by hand in four skill files that read
prose instead of the field the engine already sorted, and the two halves
drift apart again, which is precisely the failure mode `03-adr.md` of
`design/final-release-program` names as the reason a single lifecycle
matters at all.

If CR-03 stays open, "install: PASS, sbe doctor agrees" (`install.sh:261`)
keeps meaning "the BrotherSBE clone is healthy," never "the thing I just
installed is healthy," and the one sentence a fresh install prints to prove
itself stays false about what it graded.
