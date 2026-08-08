---
slug: personas
title: Three ways in
part: "5"
verified-against: 1.0.0-rc.28
---

# Three ways in

Same tool, three genuinely different experiences depending on who you are.

## The individual contributor, working alone

**Day one.** Install it, run `/brothersbe:start`, and take the one action it
gives you. Do not read the laws. Do not learn the command list. Most of your
changes will come back T0 and owe nothing, which is the point.

**Week one.** The first time a change comes back T2, write the six artifacts.
It will feel slow. What you are buying is the thing you normally reconstruct
from memory at review time.

**Month one.** You will notice you reach for `sbe status` before standup and
`sbe verify` before you open a pull request. The team learning loop collapses
to local learning on a solo install, and everything else still works.

**What you get that you did not have.** A written record of what you rejected
and why, and a mechanical answer to "is this actually done".

## The small team, two to eight people

This is the shape the project was designed for, and the difference is the
learning loop.

**Day one.** One person adopts it on one repository and runs `sbe adopt`, which
is a dry run by default. Nothing changes until somebody passes `--apply`.

**Week one.** Wire the checks into CI under `--strict`. Agree one thing out
loud: a FAIL blocks, a NO-DATA does not, and nobody edits the workflow to make
red go away. That last agreement is the whole control, because a session
instruction can never waive a hard gate. `--strict` moves only by a human
editing the workflow file, visible in the diff.

**Month one.** Lessons start landing. A lesson becomes a shared rule only
through a reviewed pull request into the shared lessons file, so no colleague's
tool starts behaving differently overnight without anyone noticing. This is
slower than automatic learning and it is deliberate.

**What you get that you did not have.** Design decisions that survive
handover, reviewers picked deterministically from the diff rather than by
whoever is free, and one shared definition of done.

## The platform or engineering lead, deciding for others

You are not evaluating the ergonomics. You are evaluating whether the claims
are real.

**Read in this order.** The honest limits chapter first. Then the checks and
gates chapter, specifically the severity column and the empty-state column.
Then this book's own provenance block, which names the files every generated
table was derived from.

**The three questions worth asking.**

1. *What happens when a check does not run?* NO-DATA, named, and it never
   decides an exit code. Verify it: the empty state is declared at construction
   and `PASS` is refused there.
2. *What is enforced versus stated?* Every law ends in `[checked: tool]` or
   `[human]`. The spine itself is `[human]`.
3. *Who can turn it off?* `--strict` changes only by a human editing the CI
   workflow. A session instruction cannot waive a hard gate.

**What you should not expect.** No CODEOWNERS and no branch protection ships
with it, and the workflow guards nothing until you copy it into your own
repository. The approval gate cannot notice a change that declared no
approval. Both are your job, and the project says so rather than letting you
assume otherwise.

**The adoption shape that works.** One repository, one lane of work, CI in
advisory mode for two weeks, then `--strict`. Do not roll it across an estate
before one team has an opinion.
