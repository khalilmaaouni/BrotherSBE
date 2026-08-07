# The comparative benchmark harness

Four tool estates, four scenarios, seven measures, and one condition that makes
the whole thing honest.

**THE EVALUATION IS UNRUN.** No person has run any row. Every measure in
[RESULTS.md](RESULTS.md) reads NO-DATA and every provenance cell reads UNRUN.
That is a stated fact, not a status update: nothing here is pending, in
progress, or estimated. Any release document quoting this harness says the
evaluation is unrun, and says it in those words.

## What is being compared

| | |
| --- | --- |
| Estates | vanilla Claude Code, feature-dev, Superpowers, BrotherSBE |
| Scenarios | a migration, an API contract change, a data pipeline change, an incident |
| Measures | defects found, defects missed, wall clock, tokens, operator corrections, false blocks, reviewer findings |

Sixteen rows. The estates, scenarios and measures are declared once, in
[scenarios.json](scenarios.json), because a grid whose shape lives in prose
drifts the first time somebody adds a column.

## The condition, and it is not optional

**Defects are planted in advance, with known file and line, in a fixture
repository this harness creates.** They are not planted in a real repository,
and they are not identified after the fact by reading what a tool happened to
say.

Without that, `defects missed` is unmeasurable BY CONSTRUCTION. You can always
count what a tool reported. You cannot count what it failed to report unless
somebody wrote down beforehand what was there. A benchmark that skips this step
is a tool grading its own homework in four columns, and the founder named that
failure mode before this directory existed.

So: [defects.json](defects.json) declares nine defects, each with an id, a
class, a file, a line, a line window and the exact source text at that line.
[fixture_repo.py](fixture_repo.py) builds the tree those lines refer to.
Nothing in the built tree names a defect, carries a marker comment, or contains
the word FIXME: an estate that could grep for the answer is not being measured.

Neither does any document the OPERATOR is handed. Matching is by file and line
window and never by wording, so an example finding that happened to sit on a
planted location would score as FOUND for whoever pasted it, and that estate
would never have been measured on that defect either. Every markdown file in
this directory is scanned for planted file-plus-line pairs by
[test_sbe_bench.py](test_sbe_bench.py). That scan reads each document whole and
depends on no code fence, so dropping the `json` tag off a block hides nothing
from it. Three forms count as naming a location: a `file` key within 200
characters of a `line` key with no brace between them (which is a findings
entry, in a fenced block under any tag or inline in a sentence), the
`path:line` form, and a path written on one line within 60 characters of the
words `line 9`, in either order. The planted set is read out of
[defects.json](defects.json), expanded over each defect's declared line window,
and is never hardcoded in the test. Every JSON example block is additionally
parsed, and one that will not parse fails the same test rather than being
skipped past.

Findings are recorded relative to the fixture root: the scorer compares paths
literally and strips no prefix, so an absolute path matches nothing and is
reported as unmatched rather than quietly repaired.

## What each part does

| File | What it is |
| --- | --- |
| [defects.json](defects.json) | The ground truth. Nine planted defects, file and line, declared in advance |
| [fixture_repo.py](fixture_repo.py) | Builds the fixture repository. Refuses to build into a non-empty directory or into this checkout |
| [scenarios.json](scenarios.json) | The grid: four estates, four scenarios, seven measures, and which defects each scenario owns |
| [scenarios/](scenarios/) | Four operator runbooks, literal enough for somebody who has never seen this repository |
| [score_run.py](score_run.py) | Computes every measure from one run's own artifacts. Reports NO-DATA for anything it could not compute |
| [report.py](report.py) | Renders the grid. Refuses to render a COMPARISON where the PROVENANCE column is empty |
| [runs/](runs/) | Where run artifacts go. Ships empty of runs |
| [RESULTS.md](RESULTS.md) | The rendered report. Currently UNRUN |
| [test_sbe_bench.py](test_sbe_bench.py) | The harness's own fixtures |

## Running it

```
python3 benchmarks/fixture_repo.py --out ~/bench-S1-brothersbe
```

Then follow the runbook for the scenario, capture the artifacts it names, and:

```
python3 benchmarks/score_run.py --run benchmarks/runs/<dir> --out benchmarks/runs/<dir>/<id>.scored.json
python3 benchmarks/report.py --scored benchmarks/runs --out benchmarks/RESULTS.md
```

The comparison mode is the one that refuses:

```
python3 benchmarks/report.py --scored benchmarks/runs --mode comparison
```

## The three honesty properties, and where they are proven

`python3 benchmarks/test_sbe_bench.py` proves all three, and each was
calibrated by re-injecting the defect it guards and watching the assertion turn
red before it was restored.

1. **A planted defect a run misses is counted as missed.** Not silently
   dropped, not rounded away because the run reported something else nearby.
2. **A measure that cannot be computed reports NO-DATA, never zero.** Zero is
   the claim that nothing happened. Absence is not that claim.
3. **A report with an empty provenance column refuses to render as a
   comparison.** It writes nothing and exits nonzero. There is no flag that
   turns it off.

## What this harness does NOT do

- It does not run the estates. A human operator does, one session at a time,
  and puts their name in the provenance column.
- It does not judge whether a block was justified. A named person does, per
  block, in `blocks.json`. One unjudged block makes the whole false-block
  measure read NO-DATA.
- It does not read the wording of a finding. Matching is by file and line
  within a declared window, because wording is judgment and a benchmark that
  scores judgment produces numbers that move when the reader changes.
- It does not measure anything about a real repository. The fixture is
  deliberately small, and results from it are results about it.
