---
slug: end-to-end
title: One change, end to end
part: "4"
verified-against: 1.0.0-rc.28
---

# One change, end to end

A single change followed from the first sentence to the merge, with the real
commands. The example is deliberately ordinary: a nightly aggregate that
feeds a number somebody reports.

## Step 0. Say what you want, in your own words

```
/brothersbe:start
```

You answer one question: what outcome do you want. Not a tier, not a command.

> "Finance says the daily revenue figure in the dashboard disagrees with the
> ledger. I need the aggregate to be reproducible and the difference
> explained."

## Step 1. The intake sizes it for you

```bash
mkdir -p design/revenue-aggregate
python3 tools/sbe_intake.py design/revenue-aggregate
```

Five questions. This one touches money, so the first match is T3 and all seven
artifacts are owed. Nobody negotiated that; it fell out of a yes.

```
tier T3 (artifacts required: 01, 02, 03, 04, 05, 06, 07)
```

If you disagree, you may override, and the override wants three fields that
agree plus a written reason. Awkward on purpose.

## Step 2. Purpose, before anything else

`01-purpose.md`: the problem stated without a solution in it, who is affected
and what they do today, what observable condition means it worked, what this
explicitly does not do, and what breaks if it is wrong.

The non-goals section earns its place immediately. "This does not change how
revenue is recognised" is the sentence that stops the change turning into a
three-month accounting project.

## Step 3. Process, including the exception path

`02-process.md`: actors, steps with their triggers, and what happens when each
step fails. The exception path is the half people skip, and it is where the
silent row-dropping lives.

## Step 4. Architecture, decided from criteria

```bash
printf '3\neventual\nmedium\nhigh\n' | python3 tools/sbe_decide.py tables/architecture.json shape
```

You get a recommendation, up to two alternatives, the criteria that separated
them, and what would flip it. `03-adr.md` records two genuinely distinct
rejected options with the reason each lost, plus the flip condition. A decision
record without a flip condition is a tombstone.

## Step 5. Data, where this class of bug actually lives

`05-data-model.md`: every entity names its system of record, every relationship
carries a cardinality, and the grain of the aggregate is stated in words before
anybody writes SQL.

Nine times out of ten the disagreement with the ledger is here: a join that
fans out, or two systems both believing they own the same entity.

## Step 6. Draw it

`06-diagrams.md`: fenced diagrams whose every node traces to a declared entity
or component. The check enforces the tracing, and it is worth more than it
sounds. A node naming something no artifact declared means two artifacts have
already drifted apart, on day one, before any code exists.

## Step 7. Say how each claim will be proven, before writing the work

`07-verification.md`: one row per claim, the check that proves it, and when it
runs. This is the phase that carries the spine's real instruction: install the
check before writing the work. The check written afterwards is written by
somebody who already believes the work is right.

## Step 8. Now write it, then prove it

```bash
python3 tools/sbe_design.py .                 # five design checks
sbe evidence run --check daily-reconciliation -- <the registered command>
sbe verify design/revenue-aggregate           # the design check plus the hard gates
```

The numbers gate wants a pinned snapshot id, a second derivation whose text
genuinely differs from the first, and zero drift between the two real numbers.
Note what it does not want: your assurance.

Note also what it cannot do, which the gate says on every run. It checks that
the two derivations differ in text. It does not read which tables they touch,
so two queries against the same broken view agree perfectly and pass. That is
a floor, and knowing it is a floor is the difference between a control and a
comfort.

## Step 9. Ask where you stand

```bash
sbe status
```

Blockers first. Broken claims, merge blockers, active conflicts, missing
evidence, then one next action. When nothing is blocking, it says so and then
immediately lists what it did **not** inspect, so "clean" is never mistaken for
"everything was checked".

## Step 10. Merge

CI runs the same checks under `--strict`. FAIL blocks. NO-DATA does not, and it
is printed. What has not cleared a gate carries the label UNVERIFIED next to
the item.

## What you have afterwards

A directory that answers, six months later, why the grain is what it is, what
was rejected, what would make you revisit it, and which check proves the number.
That is the artifact that survives the person who wrote it.
