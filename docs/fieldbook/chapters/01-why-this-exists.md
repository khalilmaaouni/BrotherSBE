---
slug: why-this-exists
title: Why this exists
part: "1"
verified-against: 1.0.0-rc.28
---

# Why this exists

## The failure this was built against

Think about the last incident on your team that actually cost something. A
pipeline that silently dropped rows for three weeks. A figure in a board deck
that nobody could reproduce. A migration whose rollback had never been run.
An endpoint that was fine until two consumers depended on it in ways nobody
had written down.

None of those are typing mistakes. They are decisions, made early, by somebody
reasonable, without the one thing that would have caught them: a check
installed before the work rather than after it.

Code review does not catch them either. By the time a diff exists, the grain
of the table has been chosen, the boundary has been drawn, and the reviewer is
reading an implementation of a decision they were not part of.

## What changed when agents arrived

An engineering agent produces plausible work quickly, and plausible is exactly
the failure mode that hurts here. A wrong number is formatted like a right
one. A migration that was never rehearsed is described in the same confident
sentence as one that was. The bottleneck stopped being how fast work gets
written and became how fast you can tell whether it is true.

That is the whole reason this project's second rule exists. An agent earns
trust in exact proportion to how mechanically its output can be checked. Not
by model size, not by how well it explains itself, and not by how sure it
sounds.

## Why verification last, not first

It looks backwards on a slide. Verification is the last of the six phases, and
it is deliberate.

If you lead with verification, you get a project that is very good at proving
the wrong thing. Tests that pin the current behaviour of a data model nobody
should have chosen. A CI pipeline that gates a boundary that should not exist.
The order matters because each phase constrains the next: what the thing is
for, then how the work runs, then what shape it takes, then how the data is
modelled, then how it is expressed, then how any of it is proven.

The corollary, and this is the part that changes how you work day to day:
**install the check before writing the work.** Not after. The check written
afterwards is written by someone who already believes the work is right.

## Three states, not two

The single most useful idea in this project fits in a sentence.

**Absent evidence is NO-DATA, and NO-DATA is never a pass.**

Most tooling has two states. Something passed, or something failed. Everything
that did not run collapses into the first one, because a report with no red in
it reads as green. That collapse is where wrong results live.

So there are three:

- **PASS**: a check read real evidence and the evidence held.
- **NO-DATA**: nothing was there to read, or what was there recorded nothing.
  This is stated, named, and it never decides an exit code. A change with
  nothing to prove is not taxed.
- **FAIL**: evidence exists and contradicts the claim, or exists and cannot be
  parsed. A broken claim is not an absent one.

A check that crashes is a FAIL carrying its exception, never a missing line,
because a gate that disappears from a report is worse than one that fails
loudly.

None of that rests on anyone remembering it. Every check is registered with a
declaration of what it reads and what its empty state is, `PASS` is refused as
an empty state at construction time, and a meta-test enumerates the registries
rather than a written list, so a check added next year is covered on the day
it is registered.

## Realistic, not maximal

There is a version of this idea that fails. It gates everything, it demands
seven artifacts for a two-line change, and the team turns it off in a
fortnight.

That is why the tier is computed from five objective questions rather than
picked, why T0 is the common case and owes nothing, why NO-DATA never blocks,
and why every limit is written down as a limit instead of being quietly hoped
past. A control you disabled protects nothing.
