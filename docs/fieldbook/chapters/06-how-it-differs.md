---
slug: how-it-differs
title: How it differs from other Claude plugins
part: "3"
verified-against: 1.0.0-rc.28
---

# How it differs from other Claude plugins

The honest framing first: most of what is in this space is good, and most of it
is solving a different problem. The question is not which is better. It is
which layer you are missing.

## The four things that get compared

**A skill pack or prompt library.** A collection of instructions that make the
model behave more like a senior engineer: checklists, review rubrics, language
conventions. These are genuinely useful and they are cheap to adopt.

**A linter or CI gate.** Deterministic, blocking, trustworthy, and blind to
everything upstream of the diff. It cannot tell you that the grain of the
table is wrong.

**A general agent orchestrator.** Fans work out across subagents, manages
parallelism, coordinates writers. It is about throughput and coordination
rather than about correctness in one domain.

**BrotherSBE.** A design method for backend and data work, with the checks
attached to it, in the order the engineering runs.

## The comparison

| | Skill pack | Linter or CI gate | Agent orchestrator | BrotherSBE |
|---|---|---|---|---|
| Covers the phase where expensive mistakes are made | No, it reviews output | No, it reads the diff | Partly, it coordinates | Yes, six phases before verification |
| Effort is computed rather than chosen | No | Fixed for everything | No | Yes, five questions produce a tier |
| Distinguishes absent evidence from passing evidence | No | Rarely, absent usually reads green | No | Yes, NO-DATA is a first-class verdict and never a pass |
| Every rule names what enforces it | No | Implicitly, the rule is the code | No | Yes, and rules with no enforcer are filed as advice |
| Blocks a merge on real evidence | No | Yes, on lint findings | No | Yes, four hard gates on receipts |
| Domain judgement for warehouse and service work | Sometimes | No | No | Yes, decision tables plus specialist reviewers |
| States its own limits mechanically | No | No | No | Yes, and one is that this repository's own PRs carry no independent review |
| Works with nothing else installed | Yes | Yes | Varies | Yes, standalone |

## The three claims that are actually load-bearing

Anyone can say "we enforce quality". These are the three that are hard to
copy, because they are structural rather than a matter of writing better
prompts.

**Absent evidence is a verdict.** A missing receipt is NO-DATA, and NO-DATA
never passes and never blocks. It is stated in the report. Most tools have two
states and quietly sort "did not run" into the good one. This one is enforced
at construction: a check is refused registration if it declares `PASS` as its
empty state, and a meta-test enumerates the registries rather than a written
list.

**Every rule names its enforcer, and rules that cannot are demoted.** Each law
ends with `[checked: some_tool.py]` or `[human]`. That is not a documentation
convention; it changes what you are allowed to believe. Rules with no enforcer
live in a separate file that says so.

**The size of the ceremony is computed.** Five objective questions, first match
wins, and a re-derivation compares the declared tier against the diff. A tool
that lets the person in a hurry decide how much rigour applies is a tool that
applies none on the day it matters.

## Where it sits next to the general orchestrator

BrotherSBE is the domain specialist sibling of BrotherModeUp, the general
orchestrator. They share a spine and diverge on scope: one knows backend and
data engineering deeply, the other coordinates any kind of work. BrotherSBE is
standalone. Clone it and it works with nothing else installed.

If you already run a skill pack you like, keep it. This is the layer
underneath it, the one that decides what gets built and refuses to call it
done without a receipt.
