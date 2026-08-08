---
slug: the-shape-of-an-engagement
title: The shape of an engagement
part: "1"
verified-against: 1.0.0-rc.28
---

# The shape of an engagement

## Six phases, in order, each gating the next

| Phase | The question it answers | What it leaves behind |
|---|---|---|
| Purpose | What is broken, for whom, and what would count as fixed | `01-purpose.md` |
| Process | Who does what, in what order, and what happens on the exception path | `02-process.md` |
| Architecture | What shape the system takes, and what was rejected | `03-adr.md`, and at T3 `04-technology-map.md` |
| Data | What the entities are, who owns each one, and at what grain | `05-data-model.md` |
| Expression | How the whole thing is drawn so a reader can hold it | `06-diagrams.md` |
| Verification | Every claim, the check that proves it, and when it runs | `07-verification.md` |

At most eight files land in one directory: the seven above plus the
`00-intake.json` the intake writes beside them. Which of them you owe is
computed by the tier, not chosen by whoever is in a hurry.

## The intake, in five questions

```bash
mkdir -p design/my-change
python3 tools/sbe_intake.py design/my-change
```

Five questions, all objective, no judgement calls:

1. Does this change a data model, an API contract, or a file interface others
   depend on?
2. Does it cross a service, system, or team boundary?
3. Is it reversible in under an hour?
4. Does it touch money, partner data, personal data, or production state?
5. How many downstream consumers break if it is wrong?

First match wins. Sensitive or slow to reverse is T3. A contract change or many
consumers is T2. One boundary or some consumers is T1. Otherwise T0.

You may override the tier, and overriding is deliberately awkward: three
fields have to agree, and a reason of at least three words has to be written
down. A half-declared override fails and names the fields that disagree.
Whether the reason is a *good* one is human review, and the tool says so
rather than pretending otherwise.

## What the design checks actually read

```bash
python3 tools/sbe_design.py .
```

Five checks, all blocking under `--strict`:

- **artifacts**: every artifact the tier requires exists, carries content of
  its own, and shares subject matter with the rest of the dossier.
- **adr**: two genuinely distinct rejected alternatives, plus criteria, a
  decision, consequences and a flip condition. A decision record without a
  flip condition is a tombstone.
- **datamodel**: every entity names its owning system, and every relationship
  carries a cardinality. Where nothing declares entities, the verdict is
  NO-DATA rather than PASS.
- **diagrams**: every node in a fenced diagram traces to a declared entity, a
  declared component or a declared lifecycle state. A node that traces to
  nothing is a sign two artifacts have drifted apart.
- **placeholder**: no artifact is still the shipped template.

That fourth one earns its keep. Writing this very book, the diagrams check
caught a sequence diagram naming an actor that no artifact had declared. It
was a real gap, found by a tool, in about a second.

## Architecture decided from a table, not a mood

```bash
printf '5\neventual\nhigh\nhigh\n' | python3 tools/sbe_decide.py tables/architecture.json shape
```

Architecture shape is scored against named criteria: independently deploying
teams, consistency requirement, operational maturity, failure isolation. Every
run returns a recommendation, up to two alternatives, the criteria that
separated them, and what would flip the decision.

A run where no criterion contributed returns NO-DATA with the recommendation
suppressed, because a recommendation backed by zero evidence is a guess with a
table around it.

One table ships today. The rest are honest human review until theirs land, and
that is stated rather than implied.

## The last mile

Verification runs advisory in a session and enforcing in CI. Locally it prints
its verdict and exits zero, so it informs you without standing in your way.
Under `--strict` in CI it exits nonzero and stops the merge.

Anything that has not cleared its gate is presented with the label UNVERIFIED
next to the item, not in a footnote. That label is written by the agent under
the law, and no tool applies it, which is exactly the kind of thing this book
tells you rather than lets you assume.
