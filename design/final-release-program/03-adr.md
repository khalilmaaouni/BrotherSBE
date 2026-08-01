# 03. Architecture decision record

## Context

The plan review of 2026-08-01 confirmed that the product has no single lifecycle:
the guided skills under skills/ and the status surface in
src/brothersbe/status.py each work out the stage independently and can print
contradictory next actions for the same repository. The external proposal
document that triggered the review answers this by introducing a new package,
src/brothersbe/core/, and moving the lifecycle into it. The founder's ratified
master plan already records a different layout in program/MASTER-PLAN.md section
6.2, and the code on main matches neither exactly: src/brothersbe/ today is a flat
set of twelve modules (cli.py, status.py, evidence.py, decisions.py, converge.py,
tasks.py, work.py, impact.py, prverify.py, adopt.py, initcmd.py and the package
initializer), measured with `wc -l src/brothersbe/*.py` in this worktree. One
layout has to be recorded as the decision, because silently shipping a second one
makes the ratified architecture a dead letter.

## Criteria

The criteria that decide this, each with the value observed on this repository
today.

- **Blast radius of the change.** Number of call sites that would move if the
  package layout changed: every import in src/brothersbe/cli.py, which is 968
  lines and is the single entry point for all 25 subcommands listed by
  `bin/sbe --help`. Observed value: high.
- **Test coverage available to catch a regression during the move.**
  `ls tools/test_*.py` returns 17 files in this worktree, and three of them run
  in the merge gate today (test_sbe.py, test_sbe_fence_hook.py,
  test_sbe_impact.py, read from .github/workflows/brothersbe-gates.yml lines 143,
  150 and 152). Observed value: low, and it stays low until Loop 1 wires the
  rest.
- **Distance between the proposal and the ratified plan.** The proposed layout in
  program/MASTER-PLAN.md section 6.2 has five sub-packages (domain, application,
  ports, adapters, presentation) plus infrastructure, and four of the eight
  adapter directories it names are for hosts that 1.0 explicitly does not ship.
  Observed value: large, and most of it serves post-1.0 scope.
- **Whether the defect actually requires the move.** The seven confirmed defects
  that Loops 1 to 3 close are behavioural: a substring classifier, an unlocked
  identifier allocator, two disagreeing locators, two disagreeing tier readers,
  an absent review record, an unenforced test set, an untrue security sentence.
  Observed value: none of the seven names a package boundary as its cause.
- **Reversibility.** A behavioural fix inside the current modules can be reverted
  by reverting its commit. A package move touches every import at once and is
  reverted only by another move. Observed value: the fix is cheap to reverse, the
  move is not.

## Options considered

### Rejected: adopt the proposed core package layout

The external proposal introduces src/brothersbe/core/ and moves the lifecycle
rules into it. The intent is right: one canonical place for the rules, which is
also what the ratified plan's own architectural rule says. The problem is the
order of operations. Doing it now moves every import in a 968 line command
surface at the exact moment when only three of the 17 test suites run in the
merge gate, so the regression net that would catch a bad move is not yet in
place. The move also creates a third layout on the table, since it matches
neither the code on main nor program/MASTER-PLAN.md section 6.2, and a third
layout is how a ratified architecture quietly becomes advisory.

There is a second cost that matters more than it looks. A package move produces
an enormous, mechanical diff. Every review of the loops that follow would have to
read the lifecycle change through that diff, and the lifecycle change is the one
piece of genuine design work in the whole program. Hiding it inside a rename is
the opposite of what this program is for.

This alternative becomes the right one once the test net is complete and the
lifecycle behaviour has settled. It is deferred, not refuted.

### Rejected: full rewrite behind a new lifecycle engine

The other end of the range: leave the current modules where they are, write a new
lifecycle engine beside them, and cut every surface over to it in one release.
This is genuinely attractive on paper, because the current disagreement between
the guided skills and the status code is a symptom of rules living in two places,
and a fresh engine could hold them in one from the start.

It loses on evidence continuity. The product's value is that its verdicts can be
defended, and every verdict rests on receipts, decision packages and gate
artifacts written by the code that exists. A new engine has to reproduce the
semantics of the evidence store in src/brothersbe/evidence.py, the decision store
in src/brothersbe/decisions.py at 2106 lines, and the four hard gates in
tools/sbe_gate.py, and until it does, nothing written by the old code can be
trusted by the new. That is a migration of the one asset the program cannot
afford to break, undertaken while the security truth reset and the concurrency
fixes are still in flight.

It also loses on the budget. The plan review put the amended program at 2.05
million to 3.6 million tokens across all seven loops. A rewrite of the engine
alone would consume that, and the founder would be paying for a second
implementation of behaviour that is already correct in most places.

## Decision

Extend the layout that exists. The lifecycle work of Loop 3 lands inside
src/brothersbe/ as it stands today: one project locator function, one tier
reader, one next action evaluator, and one durable review record, each added to
the modules that already own the neighbouring behaviour. No new package is
created for 1.0, and program/MASTER-PLAN.md section 6.2 is amended to record that
its structure is the post-1.0 target rather than the 1.0 shape, so the plan and
the code agree.

## Consequences

The lifecycle rules move into code in one place, which is the actual fix, and the
diff that carries them is small enough to review as design rather than as a
rename. The seven confirmed defects can each be closed and reverted
independently.

The cost is honest and worth naming. src/brothersbe/ stays flat, and a flat
package with twelve modules and a 968 line command surface is not the shape
anybody would choose from scratch. status.py is already 854 lines and Loop 3 adds
to it. The program accepts a known structural debt in exchange for a reviewable
change during the period when the regression net is thinnest, and it records that
debt here rather than pretending the layout is good.

A second consequence: the ratified plan has to be amended in the same change, not
left standing while the code goes elsewhere. An architecture document that
describes a layout nobody built is the same class of defect as a security
document that describes behaviour nobody implemented, which is the defect this
program exists to close.

## What would flip this

Two conditions, each observable, each tied to one of the rejected alternatives.

The proposed core package layout becomes the right decision when both of these
hold: every test suite in tools/ runs in the merge gate (the Loop 1 exit gate,
verifiable by comparing `ls tools/test_*.py` against the step list in
.github/workflows/brothersbe-gates.yml), and the Loop 3 convergence suite is
green, meaning the lifecycle behaviour has stopped changing. At that point the
regression net exists, the design work is finished and reviewed, and the move is
a mechanical change reviewable on its own. That is a post-1.0 change by
construction, since the Loop 3 gate is a 1.0 gate.

The rewrite becomes the right decision only on a much harder signal: if the Loop
3 convergence suite cannot be made green inside its budget cap because fixtures
oscillate, that is evidence the lifecycle cannot be expressed in the current
modules, and the program should stop and re-plan with the founder rather than
keep patching. The kill criterion is already written into the program: a second
incompatible schema version proposed before the first ships stops Loop 3 and
returns it to contracts.
