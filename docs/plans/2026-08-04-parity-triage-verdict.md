# Parity plan triage verdict (Fable, 2026-08-04 night)

Source: BROTHERSBE_LEADING_PRODUCT_AUTONOMOUS_EXECUTION_PLAN.md (2,631 lines,
44 distinct implementation proposals per the digest in
2026-08-04-parity-plan-digest.md). Khalil's instruction: review with Fable,
execute what survives, full overnight autonomy. Rules applied: the lean plan's
five questions, its removed-architecture register and deferred backlog (both
ratified), tonight's landed work, and the precedence that a ratified founder
decision is reversed only by Khalil awake, never inferred from a document
another model wrote.

## Accepted (join the program)

- PT-1 (digest row 39, LP-0701/0702): remove private cross-layer imports and
  sys.path mutation for internal imports. Collides with nothing. New board row.
- PT-2 (row 42, LP-0705): one command moves every version declaration site
  (VERSION, plugin.json, marketplace.json x2, DIGEST.md) and reminds about
  CHANGELOG and replay_book --write. Proof of need: this session hand-bumped
  four sites three times (rc.4, rc.5, and rc.6 pending). Serves the release
  invariant, never bypasses it. New board row, S.
- PT-3 (row 15, LP-0205 reshaped): deterministic visual map GENERATED from
  sbe status --json / --team --json as a static artifact. This is the exact
  route the ratified GUI decision prescribes. No server, no loopback, nothing
  the AST test forbids. New board row after LT-302.
- Folded into existing rows: benchmark fixtures (row 2) into LT-501 as battery
  extensions only; team-mode CI postcondition (row 34) into LT-103/501
  acceptance; generated status views (row 41) into LT-503's generation step.

## Deferred (deferred-backlog gate: three real changes exposing the gap, plus
Khalil's explicit go after the golden scenario)

Rows 35 (multi-repo workspace, self-admitted second-truth risk), 37
(packaging/console entry), 38 (self-management commands), 40 (tools shims),
43 (wave-8 simulator/digest/capsules), 44 (GitHub one-way export; also an
internal duplicate of the plan's own section 13.7).

## Rejected, each with the register row that kills it

Rows 1, 3, 4 (domain package tree, lifecycle reducer, applicability engine):
"a second aggregate creates dual truth" (lean L208); the applicability defect
was CR-07, landed tonight in the reporting layer. Row 5 (stable identities):
LT-202 extends the landed schema, never rebuilds. Row 6 (second evidence
binding): verify already mints; "no competing evidence completion mechanism"
is the lean plan's own boundary. Rows 7, 14, 26, 32 (review rebuild, review
migration, Review Center, reviewer lanes): CR-09 landed; LT-201/202/203 own
review on the board. Row 9, 31 (operation journal, activity events):
"append-only event stream" removed (lean L209). Rows 10, 28 (dependency
graph service, team state service): registry, fences and sbe work own scope
(lean L217). Rows 11, 12, 13 (result envelope, CLI migration, skills
migration): sbe status --json already IS the structured state; skills consume
it since tonight. Row 29 (WIP/swarm policy): max 3 writers is ratified. Row
36 (installer rebuild): release closure owns installation; run_doctor and 23
install tests landed tonight. Rows 16-25, 27, 33 (server GUI family): blocked
on the no-server promise, see below.

## The one question for Khalil (morning)

The parity plan proposes a local loopback HTTP server (its lines 671, 689-696)
and instructs amending SECURITY.md plus carving an allowlist into the AST
test that enforces "no analytics, no account, no server". Your ratified
2026-08-04 decision kept the promise and prescribed generating the visual map
from the canonical report instead. I am building the generated-artifact route
(PT-3). If you want the server route instead, that is a product and security
decision only you can make awake; nothing tonight forecloses it.

## Also noted

The plan is silent on the five human-only gates and the 1.0.0 tag, and
contains no instruction weakening hard gates or touching the 4 held archive
tags; its own charter forbids deleting tags or historical evidence.
