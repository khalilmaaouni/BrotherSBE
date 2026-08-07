# Run artifacts

One directory per run, named `<scenario>-<estate>-<yyyymmdd>`. Sixteen of them
when the evaluation is complete: four scenarios by four estates.

This directory ships EMPTY of runs. That is the honest state, and
`benchmarks/RESULTS.md` says so in the word UNRUN rather than the word pending.

## The rule that governs every file below

If you cannot fill a file in honestly, leave it out. A missing file makes its
measure read NO-DATA, which is a stated absence. A file holding a number you
reconstructed from memory makes the measure read like evidence, and it is not.
NO-DATA never passes anything and never blocks anything, so leaving it out costs
you nothing except the number you did not actually have.

## run.json, required

The only file that carries PROVENANCE. A run whose `provenance` is missing or
empty scores fine and then makes `benchmarks/report.py --mode comparison` refuse
to render, naming that row.

```json
{
  "run_id": "S1-brothersbe-20260807",
  "scenario": "S1-migration",
  "estate": "brothersbe",
  "provenance": "Full name of the person who sat through this run"
}
```

`scenario` must be one of the ids in `benchmarks/scenarios.json`. A scenario id
that is not declared there makes `defects_found` and `defects_missed` read
NO-DATA, because there is no declared defect set to score against.

## findings.json

Every file-and-line the estate actually named, quoted rather than paraphrased.
Paths are relative to the fixture root, with forward slashes; the scorer
compares them literally and strips no prefix for you.

Every path and line below is a PLACEHOLDER. No shape in this file names a real
planted location, and `benchmarks/test_sbe_bench.py` fails if one ever does:
this file is the one the runbooks send you to for artifact shapes, so an
example that happened to sit on a planted line would score itself.

```json
{"findings": [
  {"file": "<repo-relative path the estate named>", "line": 0,
   "note": "verbatim quote"},
  {"file": "<a second path, one entry per file-and-line>", "line": 0,
   "note": "verbatim quote"}
]}
```

An EMPTY list is data, not an absence: it says the estate reported nothing, and
every planted defect for that scenario counts as missed. Omitting the file
entirely says something different, that nobody recorded what it reported, and
both defect measures read NO-DATA.

A finding with no line number cannot be matched to a planted defect and is
carried into the scored record as unmatched, with the reason. Scoring never
reads the wording.

## timing.json

```json
{"started_at": "2026-08-07T09:14:00+09:00", "ended_at": "2026-08-07T09:41:30+09:00"}
```

## tokens.json

Both halves or neither: half a total is not a total, and reports NO-DATA.

```json
{"input": 184213, "output": 9042}
```

## corrections.json

One entry per time you had to intervene, redirect, or restate the task.

```json
{"corrections": [{"at": "2026-08-07T09:22:00+09:00",
                  "what": "had to say the migration directory is db/migrations"}]}
```

## blocks.json

One entry per time the estate refused to proceed. `justified` is a judgment a
named person makes, per block, after the run.

```json
{"blocks": [{"at": "2026-08-07T09:30:00+09:00",
             "what": "refused to call the migration ready with no rehearsal evidence",
             "justified": true,
             "judged_by": "Full name"}]}
```

One block with no boolean `justified` makes `false_blocks` read NO-DATA for the
whole run. Counting an unjudged block as justified would flatter the estate that
raised it; counting it as false would flatter the other three.

## reviewer.json

Findings a human reviewer raised against whatever the estate produced.

```json
{"findings": [{"file": "<repo-relative path the reviewer named>", "line": 0,
               "what": "the reviewer's own words"}]}
```

## Scoring and rendering

```
python3 benchmarks/score_run.py --run benchmarks/runs/<dir> --out benchmarks/runs/<dir>/<run-id>.scored.json
python3 benchmarks/report.py --scored benchmarks/runs --out benchmarks/RESULTS.md
```

`report.py` finds every `*.scored.json` under this directory. A scored file it
cannot parse is named in the report, never dropped from the grid in silence.
