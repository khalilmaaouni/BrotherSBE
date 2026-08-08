---
slug: the-brief
title: The two-page brief
part: "0"
verified-against: 1.0.0-rc.28
---

# The two-page brief

Read this and nothing else, and you will know what BrotherSBE is, what it
actually enforces, and whether it is worth your afternoon. Everything after
this is depth you can reach for when you need it.

## What it is

BrotherSBE is a Claude Code plugin that behaves like a senior backend and data
engineering colleague. You tell it the outcome you want in plain language. It
decides the method, works in the order the engineering actually runs, and
refuses to call anything done until a check has run and left a receipt.

It is not a prompt pack and it is not a linter. It is a design method with
machinery attached, and the machinery is the part that matters.

## The problem it was built against

Most engineering mistakes that hurt are made early, while somebody is deciding
what to build, how the process runs, what shape the system takes and how the
data is modelled. Reviewing the result at the end catches almost none of them,
because by then the expensive decisions are already load-bearing.

The second problem is newer. An agent that writes confidently is not an agent
that is right, and fluency is not evidence. A tool that says "done" has told
you nothing unless something ran.

## The two rules the whole thing rests on

**Design comes before verification.** Six phases, in order, each gating the
next: purpose, process, architecture, data, expression, verification.
Verification is last. It is never the theme.

**An agent earns trust in exact proportion to how mechanically its output can
be checked.** Not by how well it writes. Every rule in this project names the
thing that enforces it, and a rule that cannot name one is labelled advice and
filed as advice.

## How much ceremony you owe is computed, not chosen

Five objective questions produce a tier, and the first match wins.

| Tier | Trigger | What you owe |
|---|---|---|
| T3 | Money, partner data, personal data, production state, or not reversible within an hour | All seven design artifacts |
| T2 | A contract change, or many downstream consumers | Six artifacts |
| T1 | One boundary crossed, or some consumers | The purpose brief |
| T0 | None of the above | Nothing at all |

T0 is the common case, and it is meant to be. A tool that taxes every change
equally gets switched off within a week.

## What is actually mechanical

Four hard gates block a merge in CI, and they exist because each of these
failures is silent: a wrong result looks exactly like a right one.

- **numbers**: every figure that could reach a decision ships with a second
  derivation whose text genuinely differs, re-run to zero drift against a
  pinned snapshot.
- **migration**: forward and reverse both ran against a restored copy, with a
  rehearsal id and matching row counts.
- **approval**: a host-verified signed `Approved-by` trailer naming somebody
  other than the author. Self-approval fails. A typed name fails.
- **ran**: no SQL or pipeline change is done until its reconciliation query or
  test executed with exit zero and a nonzero duration. A check that took no
  time did not run.

Alongside them, a linter catches the code patterns that swallow an error so a
wrong result passes for a right one, and the design checks refuse a dossier
that is missing an artifact, an alternative, a cardinality or a traceable
diagram node.

## The one idea worth taking even if you adopt nothing

**Absent evidence is NO-DATA, and NO-DATA is never a pass.**

Three states, not two. A receipt that does not exist is NO-DATA. A receipt
that exists and records nothing is NO-DATA and says so. A receipt that exists
and cannot be parsed is a FAIL, because a broken claim is not an absent one.
A check that crashes is a FAIL carrying the exception, never a line that
quietly disappears from the report.

Most tooling collapses those three into "green", and that is where wrong
results get through.

## Where to start

```bash
claude plugin marketplace add khalilmaaouni/BrotherSBE
claude plugin install brothersbe@brothersbe
```

Then, in Claude Code, one command:

```
/brothersbe:start
```

It looks at where you are, a fresh project or one already in flight, and hands
you exactly one next action. You never pick a tier and you never memorise a
command list.

## What it does not do

Stated here rather than discovered later.

- It does not detect that a change *needed* an approval. It verifies an
  approval that was declared.
- It does not prove two derivations of a number are genuinely independent. It
  proves their text differs, which is a floor, not a proof.
- It does not resolve a rehearsal id against your job system. That id is a
  pointer for a human to follow.
- It does not judge whether a stated reason is a *good* one. It checks that a
  reviewable reason exists.
- It does not run your production changes. It drafts the exact command and its
  rollback for a human to run.
- It does not measure the spine. "Design before verification" is a discipline,
  and no tool computes whether you followed it.

Every threshold this project ships was measured on one estate. Measure them on
yours.
