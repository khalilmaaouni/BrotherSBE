---
slug: checks-and-gates
title: The checks and the gates
part: "2"
verified-against: 1.0.0-rc.28
---

# The checks and the gates

## The four hard gates

Four failure classes get a structural gate, and they were chosen on one
criterion: each fails **silently**. A wrong result looks exactly like a right
one, and detection latency runs from minutes to never.

| Gate | What it demands | What it cannot do |
|---|---|---|
| numbers | A real snapshot id, a second derivation whose text genuinely differs and still computes, a claimed re-run, and zero drift between the real numbers | It cannot prove the two derivations are independent. Renaming an alias passes, and nothing reads which tables they touch |
| migration | Forward and reverse both ran against a restored copy, a rehearsal id as a string, and whole matching row counts | Nothing resolves the rehearsal id against a job system. It is a pointer for a human to follow |
| approval | A host-verified signed `Approved-by` trailer naming somebody other than the author and committer | Nothing detects that a change *needed* an approval. A `Reviewed-in` id is NO-DATA, because the agent writes commit messages |
| ran | Each recorded check names what ran, exited zero, and took a nonzero duration | It does not understand what the command does. A registered check pointed at a script that prints nothing is a false registry |

That right-hand column is not a disclaimer bolted on afterwards. It is the
product. A control whose limits are hidden is a control you will over-trust at
exactly the wrong moment.

## Every registered check

Generated from the registries themselves, using the same discovery rule the
project's own honesty meta-test applies, so a check registered next year
appears here on the day it is registered rather than on the day somebody
remembers to update a list.

<!-- BEGIN GENERATED FIELDBOOK checks -->

| Check | Declared in | Severity | Verdict when its evidence is absent |
|---|---|---|---|
| `acceptance` | tools/sbe_plan.py | gate | NO-DATA |
| `adr` | tools/sbe_design.py | gate | FAIL |
| `approval` | tools/sbe_gate.py | gate | FAIL |
| `artifacts` | tools/sbe_design.py | gate | NO-DATA |
| `budget-vs-tier` | tools/sbe_score.py | soft | NO-DATA |
| `cache-economy` | tools/sbe_score.py | soft | NO-DATA |
| `calculation` | tools/sbe_plan.py | gate | NO-DATA |
| `citation-inventory` | tools/sbe_score.py | gate | NO-DATA |
| `citations` | tools/sbe_plan.py | gate | NO-DATA |
| `compatibility` | tools/sbe_plan.py | gate | NO-DATA |
| `correction-latency` | tools/sbe_score.py | soft | NO-DATA |
| `datamodel` | tools/sbe_design.py | gate | FAIL |
| `diagrams` | tools/sbe_design.py | gate | FAIL |
| `felt-outcome-ratings` | tools/sbe_score.py | soft | NO-DATA |
| `fence-hygiene` | tools/sbe_score.py | soft | NO-DATA |
| `freshness` | tools/sbe_plan.py | gate | NO-DATA |
| `graph` | tools/sbe_plan.py | gate | NO-DATA |
| `instruction-surface` | tools/sbe_instruction_surface.py | gate | NO-DATA |
| `ledger-coverage` | tools/sbe_score.py | soft | NO-DATA |
| `migration` | tools/sbe_gate.py | gate | NO-DATA |
| `migration` | tools/sbe_plan.py | gate | NO-DATA |
| `nonempty` | tools/sbe_plan.py | gate | FAIL |
| `numbers` | tools/sbe_gate.py | gate | NO-DATA |
| `ownership` | tools/sbe_plan.py | gate | NO-DATA |
| `placeholder` | tools/sbe_design.py | gate | FAIL |
| `prediction-seals` | tools/sbe_score.py | soft | NO-DATA |
| `ran` | tools/sbe_gate.py | gate | NO-DATA |
| `release-invariant` | tools/sbe_release_invariant.py | gate | NO-DATA |
| `review-cadence` | tools/sbe_score.py | soft | NO-DATA |
| `schema-2-uniform` | tools/sbe_score.py | soft | NO-DATA |
| `silent-failure-lints` | tools/sbe_score.py | gate | NO-DATA |
| `vault-log-per-active-day` | tools/sbe_score.py | soft | NO-DATA |

<!-- END GENERATED FIELDBOOK checks -->

## Reading that table

**Severity** is declared at write time in each check's constructor and prints
on every verdict line. `gate` means a FAIL blocks a `--strict` run. `soft`
means a FAIL is graded and blocks only under the opt-in `--strict-soft`. A
check declaring neither is refused registration outright. Severity changes the
exit code and nothing else: it never changes what a check examines.

**Verdict when its evidence is absent** is the empty state, and `PASS` is
refused there at construction. This is the mechanism behind "NO-DATA is never
a pass": it is enforced when the check is written, not hoped for when it runs.

## The silent-failure linter

Alongside the gates, a linter hunts the code patterns that swallow an error so
a wrong result passes for a right one: bare except, except-then-pass, a
discarded subprocess result, a conflict-skipping upsert read as SQL, and
force-try. It reads `.py .sql .swift .rb .js .ts .go`.

An exemption is visible in the diff and its reason is read:

```python
value = risky()  # sbe: allow-silent the caller re-raises with the row id attached
```

A bare marker waives nothing. A marker carrying a refused token like `tbd`
waives nothing, and the hit says why. Surviving exemptions are counted and
named rather than quietly subtracted.

A run that opened no file is NO-DATA naming why, never "clean", and so is a
scan where every finding in every file was waived. Those two are the same
sentence a careless tool would print as success.

## One writer per file

Concurrency is handled by a fence, not by hope. You fence a path, then
dispatch, in a registry, tier-tagged, and you close the fence with an inline
evidence block. Two agents never edit the same file at the same time.

What is mechanical here is narrower than it sounds, and the project says so:
fence hygiene and budget-versus-tier are checked only over registries named in
an environment variable, and only for fence lines containing the word "agent".
The rest is human discipline.
