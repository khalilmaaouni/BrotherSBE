# S1, migration

Run this once per estate: vanilla Claude Code, feature-dev, Superpowers, BrotherSBE.
Four runs, four run directories, one operator name on each.

You do not need to have seen this repository before. Every command below is
literal. If a step does not do what it says, stop and record that as a finding
rather than improvising, because an improvised step makes the four columns
incomparable.

## What is planted

Two defects, both declared in advance in `benchmarks/defects.json` with their
file and line. Do not read that file before the run: you are the operator, and
an operator who knows the answers cannot judge whether the estate found them.
Read it afterwards.

## Step 1, build the fixture

```
python3 benchmarks/fixture_repo.py --out ~/bench-S1-<estate>
```

The directory must not exist yet, or must be empty, and must be outside this
repository. The builder refuses otherwise. Nothing in the built tree names a
defect.

## Step 2, open the estate

Start a fresh session for the estate you are running, with `~/bench-S1-<estate>`
as the working directory. The four setups are declared in
`benchmarks/scenarios.json` under `estates`. Do not carry a session over from a
previous scenario.

## Step 3, give it the task

Paste this text and nothing else. It is identical for all four estates.

```text
This repository has a pending migration in db/migrations/ that splits customers.customer_name into given_name and family_name. Review the change and tell me whether it is safe to run against a production database that already holds customer rows. If it is not safe, say exactly which file and which line is the problem.
```

## Step 4, when to stop

Stop at the estate's own first complete answer: the moment it stops asking you
for anything and states a conclusion. Do not prompt again, do not hint, do not
correct. If you do have to intervene, that is a correction and it gets logged in
step 5.

Start your clock when you press enter on step 3. Stop it at the estate's
conclusion.

## Step 5, capture the artifacts

Create `benchmarks/runs/S1-<estate>-<yyyymmdd>/` and write these files. Anything
you cannot fill in, LEAVE OUT: a missing file scores NO-DATA, and an invented
number scores a lie.

`run.json`

```json
{"run_id": "S1-brothersbe-20260807", "scenario": "S1-migration",
 "estate": "brothersbe", "provenance": "your full name"}
```

`findings.json`, one entry per file-and-line the estate actually named. Copy
what it said; do not translate a vague answer into a precise one. Paths are
relative to the fixture root you built in step 1, with forward slashes: if the
estate printed an absolute path, strip the fixture root yourself, because the
scorer compares paths literally and strips nothing for you.

The two values below are PLACEHOLDERS. Nothing in this runbook names a real
planted location, and `benchmarks/test_sbe_bench.py` fails if anything ever
does: an operator who could paste the example and score a hit would be
measuring the example rather than the estate.

```json
{"findings": [{"file": "<repo-relative path the estate named>", "line": 0,
               "note": "verbatim quote of what it said"}]}
```

`timing.json`, `tokens.json`, `corrections.json`, `blocks.json`, `reviewer.json`
follow the shapes in `benchmarks/runs/README.md`.

## Step 6, score it

```
python3 benchmarks/score_run.py --run benchmarks/runs/S1-<estate>-<yyyymmdd> \
  --out benchmarks/runs/S1-<estate>-<yyyymmdd>/S1-<estate>.scored.json
```

## Step 7, re-render the report

```
python3 benchmarks/report.py --scored benchmarks/runs --out benchmarks/RESULTS.md
```
