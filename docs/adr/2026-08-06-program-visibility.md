# ADR: program progress becomes a generated product feature

- **Date:** 2026-08-06
- **Status:** accepted
- **Tier:** T2 (a contract change, several consumers)
- **Decider:** Fable, under the founder's directive of 2026-08-06 that progress
  visibility become a core feature of the product rather than a session habit
- **Context commit:** b54a543

## Context

`sbe status` answers "where does THIS CHANGE stand" from recorded state, and
`sbe map` renders one change's dossier as an offline page. Nothing answers "where
does the PROGRAM stand": what is finished, what is in flight, what is still to do,
what is blocked and by what, which risks are live and what mitigates them, and how
spend compares to budget.

The program ledger already exists at `program/PROGRAM.yaml` and
`program/work-items/*.yaml`, with a rich schema (status, owner, dependencies,
acceptance criteria, budgets, evidence, risks, alerts, and a `spec` pointer). A
grep across `tools/`, `src/` and `evals/` on 2026-08-06 found NO code that reads
either path. The ledger is therefore hand-maintained data with no reader, no
generated view, and no drift test: precisely the shape this repository gates
against everywhere else.

The founder's requirement adds one more consumer: a gantt whose advancement is
always current, as a key reporting artifact.

## Decision

Add `src/brothersbe/program.py`, a new module that reads the program ledger and
only the program ledger, and generates `program/STATUS.md` between explicit
markers, including a mermaid gantt, the finished, in-flight, to-do and blocked
lists, risks with their mitigations, a documentation index, and budget against
recorded spend. Expose it as `sbe program status` with `--json`, `--write`, and a
`sbe program check` that exits nonzero when the committed artifact has drifted
from a fresh render.

Progress is computed from declared percentages or from acceptance criteria
actually met, and is otherwise reported as "not measured". A status word never
becomes a percentage, and aggregates always state their coverage.

## Criteria used to decide

1. Truthfulness: the view must be impossible to drift from its source without a
   check failing.
2. No second store: the product already has too many places where truth could
   live, and the plan forbids adding one.
3. No new verdicts: the module must not become a second gate runner or compute
   judgements over source code.
4. Beginner legibility: persona P1 must be able to read the output without
   knowing the machinery.
5. Cost of change: it must not require rewriting the two shipped status surfaces.

## Alternatives rejected

**Alternative 1: extend `src/brothersbe/mapgen.py`.** Rejected on criteria 3 and
5. `mapgen` is documented as building strictly from `build_team_report`, the task
registry, and dossier artifact PRESENCE, all of which are CHANGE-scoped sources.
Teaching it a program-scoped ledger would give one module two unrelated source
sets and two unrelated audiences, and its own docstring argues at length against
exactly that kind of slot-filling expansion. The change-level page and the
program-level report answer different questions for different people.

**Alternative 2: keep `program/STATUS.md` hand-written, and add a linter that
checks it mentions every work item.** Rejected on criterion 1. A linter over prose
can confirm that an id appears; it cannot confirm that the sentence next to the id
is true. This is the same failure class as a receipt that claims success without
the check re-running, which this repository refuses everywhere else. It would also
leave the founder's gantt requirement to human diligence, which is what failed.

## Consequences

- One new module and one new test suite, which move the repository's baked lint
  counts. The counts law applies: run the evals and copy what they print.
- The ledger's YAML must be parsed with a strict, documented stdlib subset parser,
  because PyYAML is not available under the stdlib-only constraint. Anything
  outside that subset is a named parse error, never a guess. This is a real cost
  and a real risk, accepted because adding a dependency is the larger one.
- `program/STATUS.md` becomes a generated artifact. Human prose outside the
  markers survives regeneration; anything inside them is overwritten.
- A doc-truth eval must fail when STATUS.md drifts, or the artifact rots like the
  hand-maintained one it replaces.
- The ledger becomes load-bearing: an item with a wrong status now produces a
  wrong public report, so ledger updates join the landing ritual.

## What would flip this decision

If a second program-scoped consumer appears that needs the same data in a
different shape (for example the Loop D workspace rendering program progress as a
web view), and the two renderers begin duplicating logic, then the parsing and
report-building move into a shared module with the renderers as thin adapters,
exactly as the master plan's canonical-core-and-thin-adapters direction states.
The trigger is the second renderer, not the anticipation of one.
