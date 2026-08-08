---
slug: architecture-decisions
title: Scenario, an architecture decision
part: "5"
verified-against: 1.0.0-rc.28
---

# Scenario, an architecture decision

Splitting a service. Choosing between a queue and a stream. Deciding whether
one warehouse or two. These are the decisions that are cheapest to make and
most expensive to unmake, and they are usually made in a meeting nobody
recorded.

## The failure this addresses

Not that teams choose badly. That they choose without recording what they
rejected, so the decision gets re-litigated every six months by whoever is
newest, and nobody can tell whether the conditions that justified it still
hold.

## The decision table, and what it is honestly worth

```bash
printf '5\neventual\nhigh\nhigh\n' | python3 tools/sbe_decide.py tables/architecture.json shape
```

Four named criteria for architecture shape: independently deploying teams,
consistency requirement, operational maturity, failure isolation. You provide
the observed value for each on your estate. It returns a recommendation, up to
two alternatives, the criteria that separated them, and what would flip it.

Three things this does and does not do, stated plainly.

**It does** force the criteria to be named and valued before a conclusion
exists, which is the actual discipline.

**It does not** know your organisation. A criterion value you enter wrongly
produces a confident wrong answer.

**One table ships.** Architecture shape. Every other decision this project
mentions is honest human review until its table lands, and that is stated
rather than implied. A run where no criterion contributed returns NO-DATA with
the recommendation suppressed.

## The ADR, and the two parts everybody skips

The check demands two genuinely distinct rejected alternatives, criteria, a
decision, consequences and a flip condition.

**Two distinct rejected alternatives.** Not one strawman. Each has to carry its
own text saying why it lost. The check enforces that the text exists and is
distinct; whether it actually explains the loss rather than restating the
option's name is human review, and the tool says so on every run.

**The flip condition.** The observable condition that means revisit. Without
it, an ADR is a tombstone: it records what was decided and gives the next
person no way to know whether it still applies.

```markdown
## What would flip this
If a second team comes to need independent deployment of the pricing path, or
if the consistency requirement moves from eventual to strict for order totals,
revisit toward a split. Neither is true today: one team deploys this, and
Finance reconciles daily rather than continuously.
```

That paragraph is worth more than the rest of the document combined.

## The falsification tier

An ADR states what actually backs its recommendation, in order of strength:

1. A deterministic check ran.
2. A mutation calibration exists.
3. A fresh-context agent tried to refute it.

If nothing but reasoning backs it, that is **NO-DATA**, named as such, and not
dressed up as one of the three. Most architecture decisions in most companies
are NO-DATA and would be healthier for saying so.

## Getting a second opinion that is worth having

```bash
sbe review-route --base main
```

`principal-architect` is read-only and returns a recommendation, the first and
second alternative, and what would flip it. The instruction that makes it
useful is that a reviewer is asked to **refute**, not to confirm. A finding
that survives a genuine attempt to kill it is worth something. A finding that
survives "does this look right" is worth nothing.

Give different reviewers different lenses rather than three copies of the same
check: correctness, security, and does it actually reproduce.

## Return to developer

Every decision package carries an explicit option to decline the
recommendation and keep control, stated out loud so that silence is never
mistaken for acceptance. The tool recommends. It does not decide, and it never
pretends the absence of an objection was a choice.

## Week one and month one

**Week one.** Take the last architecture decision your team made and write it
up as an ADR, retrospectively, including the flip condition. It takes an hour
and it will surface at least one disagreement you did not know you had.

**Month one.** Every boundary change carries one. New joiners stop asking why
and start asking whether the flip condition has been met, which is a much
better question.
