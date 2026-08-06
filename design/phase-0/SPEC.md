# Phase 0 specification: program visibility and the dispatch gate

Binding spec for the Phase 0 writer lanes. Authored by Fable 2026-08-06 after the
founder approved program/MASTER-PLAN-2026-08-06.md and then extended Phase 0 with
program reporting as a product feature, a watchdog, and the encoding of the
operating principles. Implementers point at this file; they do not restate it.

Python 3.9, standard library only. No network. No subprocess in the reporting
module. Zero em or en dashes anywhere. Every claim a module prints must come from
recorded state, never from a fresh judgement the module invented.

---

## Lane A: `src/brothersbe/program.py`, the program reporter

### Why it exists (persona need)

Persona 1, the non-engineer founder, cannot answer "where does the whole program
stand" today. `sbe status` answers that for ONE change; `sbe map` renders ONE
change's dossier. Nothing reads the program ledger, so the program's own progress
lives in hand-maintained markdown that drifts the moment anyone forgets to edit
it. This module makes program progress a generated artifact with a drift test,
the same treatment every other truth in this repository gets.

### The kill criterion, adopted verbatim in spirit from `status.py`

If a truthful program summary cannot be produced without running the suites,
starting a subprocess, or computing a NEW verdict over source code, the module
stops and says so rather than doing any of those. It reads state other commands
and humans already recorded. It never invents a number.

### The sources, and only these

1. `program/PROGRAM.yaml`: the program record (objective, version target, token
   budget, milestones, waves, release gates).
2. `program/work-items/*.yaml`: one file per work item.
3. Nothing else. Not git, not the evidence store, not the task registry. A future
   item may add those; this one must not, because each added source is another
   thing that can be silently absent and read as clean.

### The work-item schema this module reads

Existing fields, all already present in shipped items and all optional except
`id`, `title`, `status`:

```
id, title, why, owner, reviewer, status, wave, depends_on[], spec,
acceptance[], estimated_days, token_budget, tokens_used, started_at,
completed_at, evidence[], risks[], alerts[]
```

Three additions this lane introduces, each backward compatible:

- `risks[]` accepts EITHER a plain string (every shipped item today) OR a mapping
  with keys `risk` (required), `mitigation` (optional), `severity` (optional, one
  of high, medium, low). A plain string is read as a risk with no recorded
  mitigation, and the report says "no mitigation recorded" rather than inventing
  one. A mapping missing `risk` is a PARSE ERROR named by file and index, never
  skipped silently.
- `blocked_by[]`: optional list of free-text blocker statements, distinct from
  `depends_on` (which names other work items).
- `percent_complete`: optional integer 0 to 100.

### How progress is computed, and where it refuses to guess

This is the load-bearing honesty rule of the lane. Progress comes from exactly
one of three sources, in this order, and the source is always named in the output:

1. `percent_complete` when explicitly recorded: reported as `declared`.
2. Otherwise, when `acceptance[]` is non-empty AND the item records
   `acceptance_met[]` (a list of indices or exact strings from `acceptance`):
   `met / total` as a percentage, reported as `derived from acceptance`.
3. Otherwise: NOT MEASURED. The report prints the status word and the string
   `not measured`, and the item contributes to no percentage aggregate.

A status word alone NEVER becomes a percentage. `in_progress` does not mean 50
percent, and any code that makes it mean 50 percent is a defect this spec
forbids by name. Aggregates (a wave's or the program's overall progress) are
computed over measured items only, and every aggregate states how many items it
covered out of how many exist, for example `4 of 9 items measured`.

Status vocabulary accepted (case and separator insensitive; `partially done`,
`partially_done` and `PARTIALLY DONE` are one value): `not_started`, `ready`,
`in_progress`, `partially_done`, `blocked`, `done`, `deferred`, `cancelled`. An
unrecognized status is a PARSE ERROR naming the file and the value, never coerced
to a neighbour.

### The public API

```python
def load_program(root):        # -> ProgramData, or raises ProgramParseError
def build_program_report(root) # -> dict, the JSON envelope below
def render_status_md(report)   # -> str, the generated block only
def render_gantt(report)       # -> str, a fenced mermaid gantt block
```

`build_program_report` returns a plain dict (JSON serializable, deterministic key
order, no timestamps that change between runs on unchanged input) with at least:

```
schemaVersion, program{...}, milestones[], waves[], items[],
summary{counts by status, measured_count, total_count, aggregate_percent or null},
risks[], blockers[], docs[], budget{declared, used_recorded, not_recorded_count},
parseErrors[]
```

`parseErrors` is a first-class field, never an exception that hides the rest: one
malformed item must not make the other eight invisible. An item that fails to
parse appears in `parseErrors` with its path and reason AND is excluded from every
aggregate, and the summary states how many items were excluded.

### The generated artifact: `program/STATUS.md`

Written only between these exact markers, so human prose outside them survives
regeneration untouched (mirror `bm_store.py`'s generated-view convention, which
this repository already uses in STATE.md):

```
<!-- BEGIN GENERATED PROGRAM STATUS -->
<!-- END GENERATED PROGRAM STATUS -->
```

Section order inside the block, all required, each rendering `none recorded` when
empty rather than being omitted (an omitted section reads as "nothing to say",
which is a different claim from "nothing was recorded"):

1. Headline: program name, version target, one line on overall position, and the
   measured-coverage sentence (`N of M items measured`).
2. The gantt, as a fenced mermaid block (below).
3. Finished: every `done` item, id, title, completion date when recorded.
4. In flight: every `in_progress`, `partially_done`, `ready` item with owner and
   progress source.
5. Still to do: every `not_started` item, with what it waits on.
6. Blocked: items whose `depends_on` names an item that is not `done`, plus every
   `blocked_by` entry. Each blocker names the item that blocks it.
7. Risks and mitigations: a table of risk, severity when recorded, mitigation or
   the literal `no mitigation recorded`.
8. Documentation: every distinct `spec` path across items, plus PROGRAM.yaml's
   own `plan` pointer, marked as existing or MISSING by a filesystem check (the
   one filesystem read this module performs beyond loading the ledger).
9. Budget: declared totals, recorded usage, and how many items record no usage.
10. Parse errors, when any: file, reason. Never silent.

### The gantt

A fenced ` ```mermaid ` gantt block, deterministic for identical input. Rules:

- One `section` per wave or milestone as recorded in PROGRAM.yaml.
- Tags carry state, never a fabricated percentage: `done` items get the `done`
  tag, `in_progress` and `partially_done` get `active`, blocked items get `crit`,
  everything else renders untagged.
- Dependencies drive ordering with `after <id>` when `depends_on` has exactly one
  entry that exists in the ledger. With multiple dependencies, use `after` with
  all of them (mermaid accepts a space-separated list). With an unknown
  dependency, the item is placed without `after` and the unknown dependency is
  reported in `parseErrors`.
- Item ids in the gantt are the work-item ids, so a reader can trace any bar back
  to its file.
- Durations come from `estimated_days` when recorded, else `1d`, and the block
  carries a one-line comment stating that bars show sequence and recorded
  estimates, never calendar promises.

### The CLI surface

The orchestrator wires `cli.py`; this lane does NOT edit `cli.py`. The lane
provides the functions the wiring calls, and its test proves them directly. The
intended surface, for the lane's docstrings to match:

```
sbe program status            human-readable summary to stdout
sbe program status --json     the envelope
sbe program status --write    regenerate program/STATUS.md between the markers
sbe program check             exit 1 when STATUS.md differs from a fresh render
```

### Done-check for lane A

```
python3 tools/test_sbe_program.py
```
must print OK, and the suite must include, at minimum, calibrated tests for: a
plain-string risk read without inventing a mitigation; a mapping risk with a
mitigation; an unknown status raising a parse error naming the file; an item
without percent or acceptance_met reported as `not measured` and excluded from
the aggregate; an aggregate stating its coverage; a malformed item surfacing in
parseErrors while its siblings still render; regeneration of STATUS.md leaving
prose outside the markers byte-identical; and two consecutive renders of
unchanged input producing byte-identical output.

Every test must be CALIBRATED: temporarily break the behaviour, confirm the test
fails, restore it. State in the return which tests were calibrated and how.

---

## Lane B: `tools/sbe_dispatch.py`, the dispatch gate

### Why it exists (persona need)

Persona 3, the agent orchestrator, has no mechanical protection against the
failure that cost this program 11,017k output tokens in one day: agents launched
without a declared model tier, budget, file list, or done-check, and new work
opened while owed work sat unfinished. A rule in a prompt is not a control. This
is the control.

### What it checks

Two independent subcommands, each usable in CI and by a hook.

**`sbe_dispatch.py brief --file PATH`** (or `--json -` reading stdin) validates a
dispatch brief. A brief is a JSON object. REQUIRED fields, each refused by name
when missing, empty, or whitespace only:

- `objective`: what the agent must achieve.
- `model_tier`: one of `fast_worker`, `builder`, `navigator`, `reviewer`,
  `researcher`, `vision_worker`. An unrecognized tier is refused naming the
  allowed set. A tier is a CAPABILITY PROFILE, never a model version string:
  a value that looks like a model name (contains `claude`, `gpt`, `opus`,
  `sonnet`, `haiku`, `gemini`) is refused with the reason that routing is by
  profile, not by version.
- `token_budget`: a positive integer.
- `files[]`: non-empty list of paths the agent may write. Each entry must be a
  relative path (an absolute path is refused, because a fence outside the
  repository is not a fence).
- `done_check`: a runnable command string.
- `tier`: one of `T1`, `T2`, `T3`, matching the effort scaling law.

Then the SCALING CHECK, which is the part that closes the 11M-token failure. Read
optional `agent_count` (default 1) and refuse when it exceeds the tier's ceiling:
T1 allows 1, T2 allows 4, T3 has no ceiling but requires a `tier_reason` field
explaining why full-audit scale is warranted. The ceilings and their source are
named in the refusal text.

Exit codes: 0 when the brief passes, 1 when it is refused, 2 on usage error.
Output names EVERY problem found, never only the first: an agent fixing one
missing field at a time is an agent making four round trips.

**`sbe_dispatch.py loop-open --state PATH --owed PATH`** refuses opening new work
when either condition holds:

- The owed-items file records any item whose state is not `closed` and which is
  not explicitly deferred by the founder (`deferred_by_founder: true` plus a
  `deferral_reason`). The refusal names each blocking item.
- The declared budget for the loop is already exhausted, computed from the state
  file's recorded spend against its declared cap.

The owed-items file is `program/OWED.json`, shape:

```json
{"schemaVersion": 1,
 "items": [{"id": "...", "title": "...", "state": "open|closed",
            "deferred_by_founder": false, "deferral_reason": null,
            "closes_in": "..."}]}
```

A MISSING owed file is NO-DATA and refuses the loop open with that reason stated,
because "the file that would list unfinished work is absent" is not evidence that
no unfinished work exists. That is the single most important behaviour in this
lane, and it must have its own calibrated test.

### Done-check for lane B

```
python3 tools/test_sbe_dispatch.py
```
must print OK, with calibrated tests for at minimum: every required field missing
in turn and refused by name; a model version string in `model_tier` refused; an
absolute path in `files` refused; T2 with 5 agents refused and with 4 accepted;
T3 without `tier_reason` refused; a passing brief exiting 0; a missing owed file
refusing loop-open as NO-DATA; an open owed item blocking; a founder-deferred item
with a reason not blocking; multiple problems all reported in one run.

---

## Rules binding both lanes

1. Mirror the closest sibling in this repository for structure, naming, imports,
   and error handling: `src/brothersbe/status.py` for lane A, `tools/sbe_gate.py`
   or `tools/sbe_intake.py` for lane B. State in your return which file you
   mirrored.
2. No bare `except`, no `except: pass`, no discarded subprocess result: this
   repository lints for exactly those and the lint runs on test code too.
3. Compile after every edit: `python3 -m py_compile <file>`.
4. Do not touch: `CHECKSUMS.sha256`, `VERSION`, `.claude-plugin/`,
   `evals/run_evals.py`, `CHANGELOG.md`, `src/brothersbe/cli.py`, or any file
   outside your fence. The orchestrator wires the CLI and the evals at
   integration, because those files move baked counts and are single-writer.
5. Never weaken a test to make it pass. A failing done-check is reported as a
   failing done-check.
6. Return format is JSON, under 1,500 tokens, with keys: `lane`, `filesWritten`,
   `doneCheckCommand`, `doneCheckLastLines`, `testsCalibrated`, `mirroredFile`,
   `residualReds`, `openQuestions`. `residualReds` enumerates by exact name any
   check that is red after your work, measured against a pristine base, never a
   category label like "integration class".
7. FRESHNESS ASSERTION, run first and quoted back before any other work:
   `git -C <your worktree> log --oneline -1` and `git -C <your worktree> status --short`.
