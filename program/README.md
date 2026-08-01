# Program ledger

This directory is the single source of truth for the BrotherSBE public release
program: what is being built, in what order, under what budgets, and against
which release gates.

## What lives here

- `MASTER-PLAN.md`: the delivery blueprint, copied verbatim. It is the source
  of intent for every wave, budget, and gate recorded here. Its own punctuation
  survives as quoted source material; new prose written for this repository
  stays free of em and en dashes.
- `PROGRAM.yaml`: the release objective, version target (1.0.0), product
  owner, the seven waves with their work item ranges and token budgets, and
  the eight release gate categories.
- `work-items/`: one YAML file per work item, each with owner, reviewer,
  reason, acceptance criteria, status, and evidence. `BR-0000.yaml` records
  the guided layer slice that created this ledger, so the ledger starts
  truthful rather than aspirational. Work items on file so far (status
  taken from each file, see the file for evidence):
  - `BR-0000`: guided layer vertical slice (start, next, status, help,
    README opening, program ledger). Status: done.
  - `BR-0201`: guided project navigator, Claude slice. Status: partially
    done; see the file for what shipped and what has not.
  - `BR-0301`: install path, marketplace primary. Status: partially done;
    see the file for what shipped and what has not.
  - `BR-0310`: beginner explainer page. Status: done.
  - `BR-0520`: Jira and Confluence one-way exporters. Status: not started, designed.
  - `BR-0521`: Asana exporter. Status: not started, designed.
  - `BR-0522`: Teams notifications now, actionable bot later. Status: not started, designed.

## What updates it

People and reviewed changes. A work item file is edited when its status,
evidence, or budget use changes, and every change lands through a normal
reviewed commit. Nothing here is generated yet.

## What is not built yet

The plan's section 9 also describes generated `STATUS.md` and `DECISIONS.md`
files, an `events.jsonl` stream, and event driven alerts (budget thresholds,
blockers, gate failures). Those are later waves (BR-0501 and BR-0502 in wave 5)
and do not exist in this repository today. Do not expect a generated status
report from this directory until that wave ships.

## Release posture

The master plan is a delivery blueprint, not a release announcement. No public
release is authorized until every condition in its no-release covenant
(section 2) and every release gate (section 11) passes. A documented no-go is
a valid program outcome.
