# 03. Architecture decision record

## Context

`docs/release-1.0/STATUS.md` carries five blockers still marked `open` after
the plan review of 2026-08-04: CR-07 (a NO-DATA verification result is read
by the skills as "keep verifying"), CR-08 (`sbe verify` mints no receipt, so
its PASS leaves `sbe status` reporting MISSING EVIDENCE about the same run),
CR-06 (single-project `sbe status` cannot find a dossier laid out the way the
project's own docs describe it), CR-10 (the beginner skills interpret
rendered prose instead of the engine's own JSON), and CR-03 (the install
tests prove syntax, not that a fresh install actually works).
`docs/release-1.0/FABLE-PLAN-REVIEW.md` section 5 already settled the shape
of the fix for the first four: "the correct first move is not to build a new
kernel. It is to make the presentation layer consume the engine state that
exists." This ADR records four decisions that carry that correction into the
five modules that own the affected surfaces, plus one bounded install.sh fix
for CR-03. Each decision below is settled; the alternatives are recorded for
the record, not reopened.

## Criteria

The criteria that decided each of the four choices below, observed against
this repository rather than assumed.

- **Whether a mechanism already exists.** CR-06's team walker
  (`_design_roots` at `status.py:552-580`, `_team_changes` at `:583-596`)
  already discovers nested dossiers; CR-10's skills already have
  `nextAction`, `notes` and `scope.storesInspected` to read
  (`status.py:465-479`). A fix that builds a second mechanism beside one
  that already works is the exact drift this program exists to close.
- **Whether the closed verdict vocabulary stays closed.** PASS, FAIL,
  NO-DATA is the whole vocabulary; `sbe_checks.py:1695` converts a fourth
  word to FAIL and `evals/test_no_data_class.py:1529` reads a fourth word as
  no verdict at all. No decision below introduces a new verdict word.
  Applicability for CR-07 lives in the reporting and exit layer
  (`sbe_gate.py:1615-1633`), never as a change to what a gate is allowed to
  return.
- **Whether an existing written contract stays true.** `sbe_gate.py:1496`
  promises "writes: nothing"; CR-08's fix must keep that promise, so minting
  lives in `_cmd_verify`, never inside a gate.
- **Whether the fix is reversible in under an hour.** Every decision below
  is a behavioral change inside modules that already exist, reverted by
  reverting its commit; none moves a package boundary, which is the same
  reversibility argument `design/final-release-program/03-adr.md` makes for
  keeping `src/brothersbe/` flat.
- **Blast radius against the defect actually named.** CR-03's fix is scoped
  to the one line that grades the wrong directory
  (`install.sh:108` cd, `run_doctor` at `:255-266`) plus test coverage; it
  does not touch the marketplace-direct and clone-fallback branches'
  install logic itself.

## Options considered

### CR-06: single-project status gains dossier discovery

#### Rejected: teach status to read .brothersbe/config.json dossierRoot

`.brothersbe/config.json` already declares a `dossierRoot` field (read today
only by `initcmd.py:164-200` and `adopt.py:223`), and teaching `status.py` to
read it looks like the direct fix. It is rejected because it adds a SECOND
discovery convention beside one that already exists and already works: the
team walker's `_design_roots` already reads `.sbe/team-profile.json`'s
`designRoots` list and extends the default `["design"]` root with it
(`status.py:560-579`). A config file the team walker does not read and a
team-profile field the single-project path does not read would leave two
independent ideas of "where dossiers live" in the same codebase, which is
the CR-06 defect reproduced one layer down rather than closed.

#### Rejected: leave single-project mode flat-only and document --team as the answer

The narrowest possible change: document that a nested dossier needs
`--team`, and single-project mode stays flat-only by design. Rejected
because it leaves CR-06 open by definition: a solo user working the
documented layout, a change under `design/<name>/`, still runs the plain
`sbe status` command first (it is the one named in every quickstart) and
still sees "nothing blocking here" over a dossier that demonstrably exists.
That is the reproduced defect, not a narrower version of it.

### CR-08: sbe verify mints receipts for the delegates it already runs

#### Rejected: teach status to stop expecting receipts from verify

`sbe status` could simply stop looking for receipts and read the decision
package `_cmd_verify` already writes instead. Rejected because it weakens
the evidence law rather than satisfying it: `sbe status` would then report
proof for a command that produced none, which is the same class of false
sentence CR-08 exists to close, moved from the verify side of the contract
to the status side.

#### Rejected: an opt-in sbe verify --mint flag

Add `--mint` and leave the default `sbe verify` behavior unchanged.
Rejected because CR-08's defect is precisely the DEFAULT path: an opt-in
flag leaves every user who does not already know the flag exists exactly
where CR-08 found them, with a passing verify and an empty evidence store.

### CR-07 and CR-10: skills consume the engine's own JSON

#### Rejected: teach sbe_gate.py the intake tier so gates self-silence

Have each gate read the dossier's tier and return something other than
NO-DATA when the tier owes it nothing. Rejected on two grounds: the closed
verdict vocabulary (`sbe_checks.py:1695` turns any fourth word into FAIL,
and the honesty sweep that guards every check registry would have to be
re-taught for every gate that grew this branch) and ownership: applicability
is a question about what a reader should DO with a NO-DATA, which is a
reporting-layer question, not a question the gate that produced the verdict
is positioned to answer about itself.

#### Rejected: a new wrapper command that re-renders gate output for skills

A dedicated command that runs the gates and re-shapes their output for
skill consumption specifically. Rejected because `sbe status --json`
already carries `nextAction` and a per-finding `basis`
(`status.py:465-479`); a second presentation surface is one more place to
keep in parity with the one that already exists, and keeping two surfaces
in parity is the exact failure mode this whole dossier is closing.

### CR-03: verification additions, not an install.sh redesign

#### Rejected: a full install.sh redesign separating SCRIPT_DIR from TARGET end to end

Rework how `install.sh` resolves its own directory against the target
directory across both branches (marketplace-direct at `:174-177` and the
clone fallback at `:178-190`). Rejected as disproportionate: `docs/release-1.0/FABLE-PLAN-REVIEW.md`
section 7 already narrows CR-03 to four named gaps (plugin activation, hooks
firing, spaces in paths, install proof), and only the fourth actually
requires touching `install.sh`'s behavior. Redesigning both branches to fix
one target-grading defect would move code the existing dry-run tests do not
yet cover, widening risk against a fix that a single `cd` correction and a
targeted test can close.

#### Rejected: add the test coverage without fixing run_doctor's cd

Write the hook-firing test, the space-in-`SCRIPT_DIR` fixture, and an
install-proof test, and leave `run_doctor`'s `cd "$SCRIPT_DIR"`
(`install.sh:108`, `run_doctor` at `:255-266`) exactly as it is. Rejected
because it closes the gap on paper while leaving it open in fact: the new
tests would pass and "install: PASS, sbe doctor agrees" (`install.sh:261`)
would keep grading the BrotherSBE clone rather than `$TARGET`, which is the
same false-sentence defect the plan review named in section 7 and the exact
class of finding this whole program exists to close.

## Decision

Four decisions, one per blocker or blocker pair, each extending a module
that already owns the neighboring behavior. No new package is created.

### CR-06

`build_report` in `src/brothersbe/status.py` gains dossier discovery through
the SAME `_design_roots`/`_team_changes` walker the team report already
uses (`status.py:552-596`). When the flat single-dossier layout is absent at
root AND dossiers exist under the design roots, the report covers the
discovered dossiers (per-dossier sections, or delegation to the team
walker's per-change machinery), and `scope.storesInspected` names what was
searched. When the flat layout exists, behavior is unchanged.

### CR-08

`_cmd_verify` in `src/brothersbe/cli.py` mints evidence receipts for the
three delegates it already runs (design, gate, score kinds, the same kind
names `status.py:93-103` sources from `evidence.CHECK_KIND_NAMES`) by
routing each delegate through the evidence module into the store status
already reads (`.sbe/evidence`, `tasks.py:97`). The store scan exclusion
machinery (`status.py:161-172`, `evidence.py:686`) is used so receipts
cannot poison each other; receipts made on a dirty tree stay NO-DATA with
the dirty state named, which is the honest law, not a bug; the minting
bookkeeping copies the structural cannot-move-a-verdict shape of
`_record_decisions` (`cli.py:141-151`); `tools/sbe_gate.py` keeps its
"writes: nothing" promise, so minting lives in the verify command, never in
the gate; the closed verdict vocabulary is untouched.

### CR-07 and CR-10

`skills/next`, `skills/verify`, `skills/status` and `skills/start` replace
their prose-interpretation probes with consumption of `sbe status --json`
(`nextAction`, `notes`, `scope.storesInspected`), `sbe doctor --json`, and
`sbe status --team --json` where multi-dossier. Rung 5 of `skills/next`
gains the NO-DATA branch: four gates NO-DATA plus `missingEvidence` empty
for the declared tier means proceed to later rungs, never loop into
`/brothersbe:verify` (the loop is skill text, not engine behavior:
`sbe_gate.py:1615-1633` never counts NO-DATA).

### CR-03

Tests gain: (a) an installed-layout hook-firing test that parses the
installed `hooks.json`, substitutes `CLAUDE_PLUGIN_ROOT`, and replays the
PreToolUse fence hook contract per the copyable harness at
`test_sbe_fence_hook.py:572-601`; (b) an install-proof test asserting the
doctor step grades the TARGET, which first requires `install.sh`'s
`run_doctor` (`install.sh:255-266`, `cd` at `:108`) to stop grading the
BrotherSBE clone; (c) space-in-`SCRIPT_DIR` coverage. All network-fenced by
stubbing `git` and `claude` on `PATH`, using the two env levers the cr03
scout names, `SBE_INSTALL_REQUIRE` and `HOME`. This is the one decision
that touches `install.sh` behavior; its risk is bounded by the existing
dry-run tests.

## Consequences

Four decisions, four costs, each named rather than hidden.

### CR-06

`sbe status` and `sbe status --team` converge on the same set of discovered
dossiers for the same repository, which is the property `01-purpose.md`'s
success criterion 1 asks for. The cost: `status.py` is already 854 lines
(per `design/final-release-program/03-adr.md`'s own measurement) and this
adds to it rather than extracting a shared discovery module, matching that
same dossier's accepted debt of keeping `src/brothersbe/` flat for 1.0.

### CR-08

A default `sbe verify` run leaves a receipt trail a reviewer can open, and
`sbe status`'s MISSING EVIDENCE section stops lying about a run that just
happened. The cost, named rather than hidden: a receipt earned on a dirty
tree is still NO-DATA, so a user who runs `sbe verify` mid-edit gets a
receipt that clears nothing, which is correct and will read as surprising
the first time it happens.

### CR-07 and CR-10

The guided skills stop re-deriving answers the engine already computed, so
a future change to `status.py`'s next-action logic is read by the skills
automatically instead of requiring four files to be updated by hand in
parallel, which is the exact drift `01-purpose.md` names as the third blast
radius if this dossier is wrong. The cost: skill files grow by the size of
the JSON-consumption logic they add, which is why the flip condition below
names the CR-14 startup budget as the thing that could force a retreat.

### CR-03

`install.sh` grades what it just installed, so its own printed proof
becomes true. The cost is one behavioral change to a script every real
install runs, bounded by the existing dry-run test suite and by keeping
both the marketplace-direct and clone-fallback branches otherwise
untouched.

## What would flip this

Four conditions, one per decision, each observable and each already named
as this decision's own kill switch.

**CR-06.** If the walker-backed report breaks the deterministic-output test
or the empty-repo NO-DATA tests in ways that cannot be fixed additively,
fall back to the rejected alternative of documenting `--team` as the answer,
plus an explicit pointer finding naming the dossiers seen, so a user is at
least told where to look.

**CR-08.** If receipt self-exclusion cannot be spelled so that
`evals/test_no_data_class.py` and the receipt-covering tests
(`test_sbe_status.py:251`, `:301`) stay green, retreat to decision packages
as the only verify output and teach status to read decision packages as
evidence pointers, with the retreat recorded in this ADR rather than
silently shipped as a smaller fix than decided here.

**CR-07 and CR-10.** If the CR-14 startup budget or a skill-size audit
refuses the added skill text, split consumption into a shared reference
file loaded on demand, the same pattern `skills/verify/SKILL.md` already
uses for `references/laws-hard-gates.md`, rather than inlining the JSON
contract into all four skills.

**CR-03.** If fixing `run_doctor`'s target resolution cannot be done
without touching the clone-fallback branch's live git clone
(`install.sh:186`) in a way that risks the network side effect the cr03
scout flags, retreat to leaving `run_doctor` as documentation-only and add
a separate `sbe doctor` invocation against `$TARGET` as its own proof step,
with the retreat recorded here rather than folded silently into a smaller
fix.
