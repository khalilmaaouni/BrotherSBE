# BrotherSBE: how it works

The mechanical half: the dossier and its completeness rules, the four tools that
compute and check it, the four hard gates, the coordination chassis underneath, and
the loop that changes the law. For the why and the what see
[DESIGN.md](DESIGN.md). To install, see [SETUP.md](SETUP.md). For all of it applied
to one system, read [the worked engagement](guides/05-a-worked-engagement.md).

Every mechanism named here is a real file in this repository. Where a section names
a tool, that tool is under `tools/` and is exercised by `evals/run_evals.py`.

```
SKILL.md              the law: 17 laws in WHEN, INPUTS, RULE, OUTPUT, ENFORCED BY form
PRACTICES.md          the advice, which says it is advice
DIGEST.md             the law's shadow, injected at session start
STATE.template.md     the per-project fence registry format
RUBRIC.md             the frozen review metrics
templates/dossier/    the seven design artifacts
tables/architecture.json   the shape decision table
tools/                intake, design checks, decision tables, gates, score, hooks
memory-template/      the memory an install copies out and then owns
evals/                fixtures with planted defects, and the release gate
```

---

## 1. The dossier

A design engagement produces at most seven files in one directory, usually
`design/<project>/`:

| File | Holds |
|---|---|
| `00-intake.json` | the five answers and the computed tier |
| `01-purpose.md` | problem, users, success criteria, non-goals, blast radius |
| `02-process.md` | actors, steps with triggers and exception paths, handoffs with contracts |
| `03-adr.md` | context, criteria, rejected alternatives, decision, consequences, flip condition |
| `04-technology-map.md` | per component: technology, owner, failure mode, recovery path; source systems; recovery objectives |
| `05-data-model.md` | conceptual, logical, physical; systems of record; cardinalities; the three lenses |
| `06-diagrams.md` | Mermaid, one section per required view |
| `07-verification.md` | every claim, the check that proves it, when it runs |

`templates/dossier/` holds all seven with worked example content. Copy the folder,
run the intake, delete what the tier does not require.

Five completeness rules are mechanical. Four are stated as laws L2 to L5 in
[SKILL.md](../SKILL.md) and the fifth backs L2, and they are exactly what
`tools/sbe_design.py` checks:

1. **artifacts.** Every file the tier requires exists, and the tier itself is
   re-derived from the answers stored beside it rather than believed as written. A
   tier that disagrees with its own answers and carries no override reason fails,
   naming both values. A missing tier, no answers, or no intake file at all, is
   NO-DATA rather than a pass.
2. **adr.** At least two rejected alternatives, plus Criteria, Decision,
   Consequences, and a "What would flip this" section. All five, or it fails.
3. **datamodel.** Every entity names a system of record with a value; every
   relationship carries one of one-to-one, one-to-many, many-to-one, many-to-many as
   a standalone token. A system of record recorded as TBD or explicitly absent fails
   like one that is missing, and "one-to-many-ish" is not a cardinality. No entities
   at all is a failure, not a pass.
4. **diagrams.** At least one diagram node exists, and no node names something
   `05-data-model.md` never defines. A diagram artifact with no diagram in it is a
   defect, not an absence.
5. **placeholder.** No artifact is still the shipped template. Each template carries
   an `SBE-TEMPLATE-UNFILLED` marker, and the check fails while any survives, naming
   the artifacts. Without it, the fastest route to a green run was copying seven
   files describing someone else's system and changing nothing.

## 2. `tools/sbe_intake.py`: five questions, one tier

Asks the five questions, writes `00-intake.json`, prints the tier and the artifact
list. `compute_tier` is a decision table with first match winning:

```python
def compute_tier(a):
    if a.get("touches_sensitive") or not a.get("reversible_under_hour"):
        return "T3"
    if a.get("changes_contract") or a.get("consumers") == "many":
        return "T2"
    if a.get("crosses_boundary") or a.get("consumers") == "some":
        return "T1"
    return "T0"
```

`required_artifacts(tier)` returns the file numbers: T0 none, T1 `01`, T2 `01 02 03
05 06 07`, T3 all seven. `sbe_design.py` imports both functions rather than
duplicating the rule, so the tier logic exists once.

The written file carries `override` and `override_reason` fields. Both are set
together or the design check fails the mismatch, naming the written tier and the
computed one, which is what makes L15 a rule rather than a wish.

## 3. `tools/sbe_design.py`: the completeness checks

One function per check, each returning a verdict and its evidence, collected in a
`CHECKS` dict: `artifacts`, `adr`, `datamodel`, `diagrams`, `placeholder`. Same
contract as the gates: advisory by default, `--strict` exits nonzero so CI can block.

```bash
python3 tools/sbe_design.py .              # all five, advisory
python3 tools/sbe_design.py datamodel .    # one check
python3 tools/sbe_design.py --strict .     # enforcing
```

Where it looks matters as much as what it checks. A directory holding a dossier is
checked directly. Anything else is a search root, walked for directories containing
`00-intake.json`, because the documented layout puts dossiers in `design/<project>/`
while CI runs from the repository root. Set `SBE_DOSSIER_ROOT` when a repository is
supposed to carry a dossier: a declared root holding none is then a FAIL rather than
a report.

On this repository, which carries no dossier at all, the search finds nothing and
says so, and the exit code is 0:

```
BROTHERSBE DESIGN CHECKS  (advisory unless --strict; NO-DATA is never a pass)
  dossier    NO-DATA  no dossier found under .: no directory contains 00-intake.json. If this repository is supposed to carry one, set SBE_DOSSIER_ROOT to where dossiers live and this becomes a FAIL instead of a report
```

Two implementation details are worth knowing before you write a dossier, because
they decide what the checks can see.

**The entity list is parsed from bullets.** `_entities` reads bullet lines in
`05-data-model.md` above the `Relationships` heading, taking the text before the
first colon as the name and the rest as its meta, which must contain the words
"system of record". Bullet lines below the Relationships heading are read as
relationships and must carry a cardinality, so tables and numbered lists are the
right shape for everything after that point.

**The diagram check traces against that same entity list.** A node in
`06-diagrams.md` that is not in the list is an orphan and fails by name. If a
diagram legitimately names a runtime component, declare it in `05-data-model.md`
with a system of record, under its own heading, exactly as
[guide 05](guides/05-a-worked-engagement.md) does. Declaring it anywhere else does
not work: the datamodel check then fails the component for having no system of
record. And when `05-data-model.md` has no entities at
all, the diagram check returns NO-DATA rather than PASS, because an empty known set
would make every invented node look traceable, which is the exact defect the check
exists to catch.

## 4. `tools/sbe_decide.py` and `tables/`

`recommend(table, context)` scores each criterion supplied in the context and
returns one shape:

| Key | Meaning |
|---|---|
| `verdict` | `OK`, or `NO-DATA` when no criterion contributed |
| `recommendation` | top-ranked option, `None` when NO-DATA |
| `alternatives` | up to two next-ranked options, empty when NO-DATA |
| `deciding_criteria` | one line per criterion that contributed |
| `evidence` | how many criteria contributed |
| `unrecognized` | one line per supplied value matching none of a criterion's keys |
| `flip_condition` | the table's flip line, unconditionally |
| `scores` | the raw tally per option |

The suppression is the point: when nothing contributed, the recommendation is
withheld rather than shown, because a ranking over an all-zero tally is a guess
with a table around it. The `unrecognized` list is the other half: a typo in a
value is reported by name so it is distinguishable from an omission.

`tables/architecture.json` ships one table, `shape`, with four criteria
(`deploying_teams`, `consistency`, `ops_maturity`, `failure_isolation`), four
options, per-criterion score maps, and one `flip` line. Criteria are `number` kind
with a low and high bound per option, or `choice` kind with a list of favoured
options per key. Editing a threshold is editing this file, in a reviewed pull
request; the tool holds no numbers of its own.

```bash
python3 tools/sbe_decide.py tables/architecture.json shape
```

## 5. `tools/sbe_gate.py`: the four hard gates

One subcommand per silent-failure class. Each walks the git worktree for its
receipt file, then checks the receipt is internally consistent rather than merely
present.

| Gate | Receipt | Passes only when |
|---|---|---|
| `numbers` | `numbers-manifest.json` | each figure has a `snapshot_id`, a `second_derivation` textually different from `query`, `rerun.ran` true, and `primary` equal to `secondary` |
| `migration` | `migration-receipt.json` | both legs have `ran_against_restore`, the reverse has a `rehearsal_run_id`, and `row_counts.before` equals `row_counts.after_reverse` |
| `approval` | `APPROVAL` file plus a HEAD trailer | a signed commit carries `Approved-by:` (git `%G?` in `G`, `U`, `E`) or the commit carries `Reviewed-in: <id>`. A typed name with neither fails |
| `ran` | `ran-receipt.json` | every check has `exit_code` 0 and a nonzero `duration_ms` |

```bash
python3 tools/sbe_gate.py .             # all four, advisory
python3 tools/sbe_gate.py numbers .     # one class
python3 tools/sbe_gate.py --strict .    # enforcing
```

Four properties are deliberate. A missing receipt is NO-DATA, so a change with
nothing to prove is not taxed. A receipt that exists and records zero items is also
NO-DATA and says which file and why, because an empty manifest is exactly what a run
that never happened produces, and reporting PASS over zero items would print evidence
asserting work nobody did. A receipt that exists and is either unparseable or
internally inconsistent FAILs with the reason named, because the operating record
says pasted receipts get invented and a file that cannot be read is a broken claim,
not an absent one. A crash under `--strict` exits nonzero: a broken gate blocks
rather than waves work through.

## 6. `tools/sbe_score.py`: the code-graded checks

The weekly review's mechanical half. Eleven checks, each printing PASS, FAIL, or
NO-DATA with its evidence inline, so the model judges only the residue:
`ledger-coverage`, `schema-2-uniform`, `cache-economy`, `vault-log-per-active-day`,
`fence-hygiene`, `correction-latency`, `budget-vs-tier`, `prediction-seals`,
`felt-outcome-ratings`, `review-cadence`, and `silent-failure-lints`.

The last one is the linter for the patterns that swallow an error so a wrong result
passes for a right one. The patterns are bare `except`, except-then-`pass`, a
discarded subprocess result without `check=True`, a conflict-skipping upsert with no
logged skip count, and force-try. It is opt-in on a path, and a run that opened no
file reports NO-DATA naming why rather than the word "clean", which would assert the
opposite of what happened; a positional argument that is not a directory is a FAIL,
so a mistyped path cannot read as a clean scan. It scans tracked `.py .sql .swift .rb .js .ts .go` files under
`SBE_LINT_ROOT` or a directory argument. A reviewed exemption carries a visible
`# sbe: allow-silent <reason>` marker on the line, so the swallow is auditable in
the diff.

```bash
python3 tools/sbe_score.py "$(pwd)"
python3 tools/sbe_score.py --strict .   # gate severity, by ratified decision
```

## 7. CI: where advisory becomes blocking

`.github/workflows/brothersbe-gates.yml` runs three steps on every pull request:

```yaml
      - name: Hard gates (numbers, migration, approval, ran) block on failure
        run: python3 tools/sbe_gate.py --strict .
      - name: Design checks (dossier completeness) block on failure
        run: python3 tools/sbe_design.py --strict .
      - name: Silent-failure lints and code-graded checks block on failure
        run: python3 tools/sbe_score.py --strict .
```

The checkout step needs `fetch-depth: 0` because the approval gate reads commit
trailers and signatures. All three tools are standard-library Python with no
dependencies and no network calls.

`--strict` is not overridable by a session instruction. It changes by a human
editing this file in a reviewed change, which is the entire mechanism behind "a
session instruction never waives a hard gate".

## 8. The chassis underneath

The coordination layer is inherited from BrotherModeUp
(github.com/khalilmaaouni/BrotherModeUp), where it has an operating record.
[PARITY.md](../PARITY.md) tracks what is shared verbatim and what was adapted.

**The safety floor.** Before anything is written: the ground is mapped (git status,
current branch, live writers, an environment preflight), the fence is registered,
and STATE.md carries the plan and the intent. The floor is exempt from the learning
loop by construction, because a loop allowed to grade its own safety checks will
eventually learn to skip them.

**Single-writer fences.** Exactly one writer per fenced scope, and the fence line
lands in STATE.md before the agent launches. Each fence carries objective, output
format, tool guidance, boundaries, termination, plus file scope, ids, a lease TTL,
an effort tier, and a runnable done-check. Overlapping scopes queue rather than
share. A fence closes only with an inline evidence block: the command and its last
lines. Two parts of this are checked by `sbe_score.py` over the registries named in
`BROTHERSBE_REGISTRIES`: `fence-hygiene` flags a live fence line in a registry
untouched for more than two days, and `budget-vs-tier` flags a live fence line with
no tier tag. Unset registries report NO-DATA rather than guessing. The rest of the
fence discipline is human review, and SKILL.md law L13 says so in its own text.

**State on disk.** Event-time logging rather than batch-end logging; write-ahead
intent before a risky action; `tools/sbe_autosave.sh` snapshotting the whole
working tree, untracked files included, to a private git ref at PreCompact without
touching the branch, index, or working tree and without pushing anything; resume by
id rather than respawn; durable placement of any deliverable the moment it exists.

**Context hygiene.** Grep before read, line ranges rather than whole files,
subagent return contracts capped near 1,500 tokens, and a re-read of the law and
STATE.md from disk after any compaction. Laws live on disk, not in recollection.

**The decision ladder and effort tiers.** Six rungs, stopping at the first
sufficient one: answer directly, look it up, ask the operator, do it inline,
dispatch one agent behind one fence, dispatch a fleet. Every brief and fence
declares an effort tier, which sets model routing and the token ceiling. Where the
harness cannot enforce a ceiling, "not measured" is a legal report and an invented
number is not.

## 9. The hooks

Three hooks, wired in `~/.claude/settings.json` or a project settings file. Every
hook exits 0 on every path: a broken diary never blocks an engineer's work.

- `tools/sbe_sessionstart.sh` at SessionStart prints `DIGEST.md` into context, plus
  mechanical nags (overdue review, unprocessed corrections) and an offline update
  check that reads git ref files as plain files.
- `tools/sbe_telemetry.py outcomes-append` at SessionEnd appends one line per
  session to the outcomes ledger and scans short operator messages for correction
  candidates. Appends are idempotent: the write is skipped when the last line for
  the session id is byte-identical, and the done-check is firing the hook twice and
  diffing the ledger for zero growth.
- `tools/sbe_autosave.sh precompact` and `tools/sbe_telemetry.py precompact-brief`
  at PreCompact snapshot the tree and write a forward-looking resume brief.

The division is the point: hooks write the ledgers, because a logging duty left to
model memory is a defect. Gate tools exist to block and therefore have two modes,
advisory and `--strict`. Observability tools exist to observe and therefore have
one: exit 0, always.

Everything the hooks write stays on the machine. The vault path is
`BROTHERSBE_VAULT`, and the user-text store ships with redaction, 0600 permissions,
a retention limit, and a purge command from its first line.
[SECURITY.md](../SECURITY.md) carries the claims and the greps that check them.

## 10. `evals/run_evals.py`: the release gate

Each eval is a fixture with a planted defect and an assertion that the matching
check catches it: an overstated total, a second derivation identical to the first,
an untested reverse migration, a typed-name approval, a green-on-red check, a
missing dossier artifact, an ADR with no rejected alternatives, a relationship with
no cardinality, an entity with no system of record, an orphan diagram node, an
empty decision context. The suite exits nonzero on any regression, so a gate that
stops catching its defect stops the release.

```bash
python3 evals/run_evals.py
python3 tools/test_sbe.py
```

## 11. How the law changes

`SKILL.md` is never edited casually. An observed weakness becomes one line in the
pending-amendments note the moment it is observed. Amendments land at the weekly
review (`tools/WEEKLY-REVIEW.md`) at most one consolidation per cycle, each naming
the measured signal it should move. The next review compares strictly and reverts
any amendment whose signal did not move. Rejected amendments keep their reasons and
are not re-proposed without new evidence.

`DIGEST.md` is generated from `SKILL.md` and updated in the same change: a hand
edit to it is a defect by definition, because it is the file injected at session
start and it has to say what the law says.

A practice becomes a law by acquiring a check. It moves from `PRACTICES.md` into
`SKILL.md` in the law form (WHEN, INPUTS, RULE, OUTPUT, ENFORCED BY), with the new
check named on the enforcement line and a fixture in `evals/` proving the check
catches the defect it claims to catch. On a team, that promotion is a reviewed pull
request into the shared repository and `memory-template/LEARNED.md`. No colleague's
tool changes behavior silently.
