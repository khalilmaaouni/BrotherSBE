# BrotherSBE quickstart: the practical first hour

BrotherSBE is a Claude Code skill: a senior backend and data engineering colleague
for small teams (two to eight) and strong individual contributors. It is the
specialist sibling of BrotherModeUp (github.com/khalilmaaouni/BrotherModeUp). Where
BrotherModeUp is the general chassis, BrotherSBE adds the part that makes a data or
backend engineer trust an agent: four hard gates that turn the four silent-failure
classes into a mechanical PASS or FAIL, plus a linter for the code patterns that
hide an error so a wrong result passes for a right one.

The spine of the whole thing, stated once so the rest makes sense: an agent earns
trust in exact proportion to how mechanically its output can be checked. Every
command below is that rule made concrete.

This page gets you from a clone to two things working end to end: a data engineer
verifying one figure through the numbers gate, and a backend engineer shipping one
change through the ran gate. Then it wires the gates into CI so they block a merge.

Everything here runs against the real tools in this repo. No field, filename, or
subcommand below is invented; each one is read by the code in `tools/`.

---

## The first ten minutes: point it at your own repository

Clone the skill wherever your Claude Code skills live. These docs assume the
default install path; set a shell variable so the commands are copy-pasteable.
Then run it where your work is, not where the skill is.

```bash
SBE="$HOME/.claude/skills/brothersbe"     # wherever you cloned BrotherSBE
cd ~/your-repo
python3 "$SBE/tools/sbe_score.py" .       # the linter, over the code in .
```

The report is split, and the split is the point. The first group is the checks
that opened a file in the directory you are standing in. The second is fed by a
telemetry vault and fence registries you have not installed yet, so its lines
are true and are not about your code:

```
CHECKS THAT OPENED A FILE IN /home/you/your-repo (1 of 12): these verdicts are about the code here.
silent-failure-lints      FAIL     1 hit(s) in 2 file(s) scanned: src/config.py:7 except-then-pass (swallows the error) [severity: gate]

CHECKS FED BY A VAULT OR REGISTRY OUTSIDE /home/you/your-repo (11 of 12, of which 10 have no source on this machine at all): a verdict here is not a statement about the code in this directory.
```

That one FAIL is the whole first run: a file, a line, and the reason. Everything
under the second heading is the tool telling you what it did not read.

Now the four gates, on the same directory:

```bash
python3 "$SBE/tools/sbe_gate.py" .        # all four gates, advisory, exits 0
```

With no receipts present you get four NO-DATA lines. NO-DATA is never a pass: it
means "no evidence either way", which is the honest verdict for a change that
carries no figure, no migration, no money path, and no SQL. Every verdict names
the root it examined, what it read there, and what inside that root contributed
nothing, including any tree the walk pruned:

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  numbers   NO-DATA  no numbers-manifest found; if this change presents no decision figure that is correct, else add one; no numbers-manifest.json read under .; 1 of 1 director(y/ies) directly under . contributed no numbers-manifest.json (src) [severity: gate]
  ran       NO-DATA  no ran-receipt.json; a SQL or pipeline change is not done until its check executed and left a receipt; no ran-receipt.json read under .; 1 of 1 director(y/ies) directly under . contributed no ran-receipt.json (src); 1 pruned director(y/ies) hold file(s) this check reads and were NOT examined, so this verdict does not cover them: ./node_modules (installed node packages (its entries carry their own package.json)) [severity: gate]
```

Read the tail of that last line. The walk skipped `node_modules`, that tree
holds a file this gate reads, and the verdict says so rather than reporting an
absence it did not establish.

## Step two: watch the gates fail on purpose

Before you trust a verdict, watch the gate earn it. The eval suite plants the
exact defects the operating record produced (an overstated multi-year total, an
untested reverse migration, a typed-name approval, a green-on-red check) and
asserts the matching gate catches each one:

```bash
python3 "$SBE/evals/run_evals.py"
```

```
536 evals: 536 passed, 0 regressions.
```

Every case in `evals/run_evals.py` is a real failure class as a fixture. When you change a gate,
this suite is what tells you a gate stopped catching its defect. Run it before you
rely on anything else here.

The four gates and the exact receipt each one reads:

| gate | receipt file (found under the directory you name) | what a PASS proves |
| --- | --- | --- |
| `numbers` | `numbers-manifest.json` | a decision figure is pinned, re-derived by a second query differing beyond formatting and comments, zero drift |
| `migration` | `migration-receipt.json` | forward and reverse both ran against a restore, and recorded row counts match (no row counts recorded is NO-DATA) |
| `approval` | `APPROVAL` file or an `Approved-by:` commit trailer | a money or partner change carries a human approval bound to a verified signature, or a review id the gate does not resolve |
| `ran` | `ran-receipt.json` | a SQL or pipeline check actually executed (nonzero duration, zero exit) |

The gate walks exactly the directory you name (the default is `.`, the
current directory) and never a silently substituted git worktree top, so the
verdict is about the tree you pointed it at. It skips version-control,
dependency and virtualenv directories by directory name (matching `.git` as a
substring of the path had also hidden `.github/` from all four gates). The
skip list is one shared set, `sbe_checks.SKIP_DIRS`, plus two structural
tells: a directory carrying a `pyvenv.cfg` is a virtualenv whatever it was
named, and `site-packages` is installed code. Put a receipt anywhere inside
the directory you name: at the repo root when you run the gate at the repo
root, or beside the model or migration it belongs to. A receipt OUTSIDE that
directory is not found, and the gate reports NO-DATA for it, which does not
block, so name the directory that holds the receipts you mean to check.

---

## Walkthrough A: a data engineer verifies one figure end to end

You produced a headline number, say GMV for a board slide. The rule from the skill:
a headline number shown before its independent second check is not a result, it is
a guess with a decimal point. The numbers gate makes that rule mechanical. A figure
ships only when its `numbers-manifest.json` carries all of:

- `snapshot_id`: a pinned read. A live warehouse drifts under you; the gate fails a
  figure with no snapshot id rather than let an unpinned number look verified.
- `query`: the primary derivation.
- `second_derivation`: a second query that reaches the same number a different way.
  It must be textually different from the first, or it is not independent and the
  gate says so.
- `rerun`: `{"ran": true, "primary": <n>, "secondary": <n>}`. Both derivations
  re-ran; the two results must be equal (zero drift).

### Step 1: write the manifest with the fields the gate reads

Derive GMV two ways. Sum the order totals; then, independently, sum quantity times
price on the order lines. Pin both reads to the same snapshot. Record the manifest:

```bash
mkdir -p ~/sbe-demo && cd ~/sbe-demo
cat > numbers-manifest.json <<'EOF'
{
  "figures": [
    {
      "label": "gmv",
      "snapshot_id": "snap_2026_07",
      "query": "SELECT SUM(amount) FROM orders",
      "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
      "rerun": { "ran": true, "primary": 17570, "secondary": 17570 }
    }
  ]
}
EOF
```

Those are the only keys the gate reads: `figures[].label`, `snapshot_id`, `query`,
`second_derivation`, and `rerun` with `ran`, `primary`, `secondary`. Anything else
in the file is ignored. `primary` and `secondary` hold the numbers your two queries
actually returned; you fill them from the query output, not by hand.

### Step 2: run the gate advisory and read the PASS

```bash
python3 "$SBE/tools/sbe_gate.py" numbers ~/sbe-demo
```

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  numbers   PASS     1 figure(s) each pinned to a snapshot, with a second derivation whose text differs beyond case, whitespace and comments, re-run to zero drift [severity: gate]
```

The figure is pinned, derived two independent ways, and both derivations returned
17570. That is a number you can put on the slide with UNVERIFIED removed.

### Step 3: plant a drift and watch it FAIL

Now break it the way reality breaks it. Suppose your two queries disagree: the sum
of amounts says 17570, but quantity times price says 17998. That gap is a real bug
(a discount applied in one place and not the other, a currency column missed).
Change `secondary` to the number the second query actually returned:

```bash
cd ~/sbe-demo
python3 - <<'EDIT'
import io
p = "numbers-manifest.json"
s = io.open(p).read()
io.open(p, "w").write(s.replace('"secondary": 17570', '"secondary": 17998'))
EDIT
python3 "$SBE/tools/sbe_gate.py" numbers ~/sbe-demo
```

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  numbers   FAIL     gmv: DRIFT primary=17570 secondary=17998 (zero drift required) [severity: gate]
```

The gate names the label, both numbers, and the rule. You do not ship a figure whose
two derivations disagree; you go find why they disagree. The same FAIL fires if you
drop the `snapshot_id`, omit the `second_derivation`, paste the first query in as the
second (identical text is not independent), or forget to set `rerun.ran`. Each of
those is a separate eval case, so each stays caught.

Restore the manifest to the matching-numbers version once the underlying bug is
fixed, and the gate returns to PASS.

---

## Walkthrough B: a backend engineer debugs, then ships one change through the ran gate

You have a failing job. The highest-frequency, cheapest use of BrotherSBE is the
debugging loop, and it is where a backend engineer starts.

### Step 1: the debugging loop

Paste the trace or the failing test into the BrotherSBE session. The loop is:
ranked candidate causes, then verify each against a reproduction before you touch
code. You do not act on the first plausible cause; you reproduce it. The skill's own
rule: after two failed attempts on one approach, revert to last good and
re-diagnose; a third failure stops and presents options. The blast radius here is
near zero and detection is seconds, which is why this is the entry point.

Say the reconciliation between a source table and its rollup is off. You reproduce
it, trace it to a join that dropped null keys, and write the fix plus a
reconciliation query that must return zero mismatched rows.

### Step 2: the change is not done until its check ran

The ran gate exists to catch the most common agent lie: a green result reported but
never executed. A check that took no time did not run. So "done" for a SQL or
pipeline change means a `ran-receipt.json` exists with, per check:

- `name`: what ran (your reconciliation query, your test).
- `exit_code`: the process exit code. It must be present and zero. `null` means the
  gate cannot tell it ran, and fails; nonzero means it ran and failed, and fails.
- `duration_ms`: wall-clock milliseconds. Zero or missing fails, because a check
  that took no time did not execute.

Run your reconciliation, capture its real exit code and duration, and write them:

```bash
cd ~/sbe-demo
# run the real check, then record what it actually did:
cat > ran-receipt.json <<'EOF'
{
  "checks": [
    { "name": "reconcile", "exit_code": 0, "duration_ms": 812 }
  ]
}
EOF
```

The `checks` array is the only key the gate reads; each entry needs `name`,
`exit_code`, and `duration_ms`. You fill `exit_code` and `duration_ms` from the run
itself, not from intent.

### Step 3: attach the receipt and clear the gate

```bash
python3 "$SBE/tools/sbe_gate.py" ran ~/sbe-demo
```

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  ran       PASS     1 recorded check(s), each with a zero exit and a nonzero duration [severity: gate]
```

Now the change is done in the sense the gate means: its check executed and left
proof. Commit the receipt alongside the change, under the directory you hand the
gate. Had your reconciliation exited nonzero, the gate would report
`reconcile: check exited nonzero (1)` and block; had you recorded `duration_ms: 0`,
it would report the check did not run. Either way, "green" that you did not earn
does not pass.

### A note on the silent-failure lints

While you are in backend code, the companion linter in `sbe_score.py` scans your
worktree for the patterns that swallow an error so a wrong result looks like a right
one: bare `except:`, except-then-`pass`, a discarded `subprocess` result with no
`check=True`, a conflict-skipping upsert with no logged skip count, and Swift
`try!`. It is opt-in on a path, so it never scans an unrelated tree:

```bash
python3 "$SBE/tools/sbe_score.py" ~/your/repo    # scans that worktree for silent swallows
```

A genuine, reviewed swallow is legal when a human names why: put a
`# sbe: allow-silent <reason>` comment on the line and the linter skips it. The
exemption is visible in the diff, which is the point.

---

## Wire the gates into CI so they block a merge

Advisory tells a session. Enforcing stops a bad merge. Both modes run the same
checks; `--strict` is the difference: it exits nonzero on any FAIL. You saw it
locally:

```bash
python3 "$SBE/tools/sbe_gate.py" numbers ~/sbe-demo --strict ; echo "exit=$?"
```

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  numbers   FAIL     gmv: DRIFT primary=17570 secondary=17998 (zero drift required) [severity: gate]
STRICT: 1 hard gate(s) failed; exiting nonzero to block the merge.
exit=1
```

Two properties make this safe to turn on in CI:

- NO-DATA does not fail. A pull request that carries no figure, no migration, no
  money path, and no SQL passes without receipts. The gate blocks only a receipt
  that exists and is bad, so it does not force ceremony onto changes that do not
  need it.
- A crash in strict mode blocks. If the gate itself errors under `--strict`, it
  exits nonzero rather than waving work through. A broken gate never silently
  passes.

This repo ships the CI file already, at `.github/workflows/brothersbe-gates.yml`.
Copy it into the repository you want guarded (the tools must be present in that
checkout, so vendor `tools/` into the repo or add a step that clones this skill
first). The workflow, verbatim:

```yaml
# BrotherSBE enforcement: this is what turns the gates from advisory into blocking.
# Cloning the skill gives you the tools; this file wires them into your CI so a
# merge is stopped when a hard gate fails. Copy it into the repo you want guarded.
#
# Hardening, because this file is the control everything else rests on:
# - Actions are pinned to full commit SHAs (the tag each SHA corresponds to is
#   the trailing comment; both verified against the live repositories with
#   `git ls-remote` on 2026-07-27), so a moved tag cannot change what runs here.
# - permissions is read-only: nothing in this workflow needs to write.
# - The gates job runs on Linux and macOS, across a 3.9 floor and a newer 3.x
#   leg. A second job below, gates-windows, runs the same battery on
#   windows-latest pinned to 3.9 only, added 2026-08-05 (founder-approved,
#   lane T7). It skips only the two POSIX `sh` install and upgrade scripts,
#   named where each is skipped; everything else, including the suites that
#   assert POSIX file permission bits, is exercised on Windows for the first
#   time there instead of staying "genuinely untested" (docs/KNOWN-LIMITS.md
#   still describes the pre-2026-08-05 state and is due its own update to
#   match, out of this file's own scope to make).
name: BrotherSBE gates
permissions:
  contents: read
on:
  pull_request:
  push:
    branches: [main]
env:
  # Where your dossiers live. Empty means "search the whole checkout": every
  # directory holding a 00-intake.json OR any of 01 through 07 is found and
  # checked. That is what makes the design checks reach a dossier in
  # design/<project>/ instead of opening only <root>/00-intake.json and reporting
  # nothing while a full dossier sits two directories away, and it is also why
  # deleting the intake file no longer hides a dossier: that FAILs, naming the
  # missing intake. Set it (for example to `design`) once this repository is
  # supposed to carry a dossier: a declared root holding none is then a FAIL, not
  # an absence. Leave it empty in a repository that mixes T0 work with dossier
  # work, because a declared root plus a legitimately dossier-free change FAILs
  # by design. A directory holding dossier-shaped files that are not live design
  # work (a template library, a finished project) carries a .sbe-exempt file
  # whose contents say why, and that reason prints on every run.
  SBE_DOSSIER_ROOT: ''
jobs:
  gates:
    strategy:
      # fail-fast off: when one platform fails, the other must still report in
      # full. The first Linux eval failure in this repository's history was
      # diagnosed blind because fail-fast cancelled the macOS job mid-suite,
      # leaving half the evidence unread.
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
        # The front page promises a 3.9 floor and the runners ship 3.14; the
        # first readable CI logs proved excerpts can drift between the two
        # (unittest id formatting), so BOTH ends are tested: the floor the
        # promise names and the newest an adopter will actually have.
        python: ['3.9', '3.x']
    runs-on: ${{ matrix.os }}
    # Founder decision 2026-07-31 (batched round): the 3.9 floor is the
    # BLOCKING leg because it is the promise on the front page; the newest
    # interpreter is informational, so a 3.x-only failure is a heads-up about
    # the future, never a release blocker.
    continue-on-error: ${{ matrix.python == '3.x' }}
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
        with:
          fetch-depth: 0   # the approval gate reads commit trailers and signatures
      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5
        with:
          python-version: ${{ matrix.python }}
      # The approval gate accepts a signature only if THIS host verified it. A
      # runner with no public keys imported reports "cannot verify" for every
      # signed commit, which is NO-DATA and not an approval. To use the signed
      # trailer path in CI, import the approvers' public keys first:
      #   - run: gpg --import <<< "${{ secrets.SBE_APPROVER_PUBKEYS }}"
      # Or standardise on the Reviewed-in: <review id> trailer, which needs no
      # keyring at all. Doing neither is legal and honest: approvals then report
      # NO-DATA, instead of a gate that quietly degrades into accepting any
      # signature blob because it could not check one.
      # Scoped to the LIVE dossier root (design/, declared by `sbe init`), not
      # the whole checkout. The first real run of this workflow proved why the
      # wide sweep was wrong twice over: the teaching dossier under
      # docs/for-engineers/examples carries an APPROVAL that is DESIGNED to
      # fail (two documents paste that refusal as the lesson), so scanning it
      # turned pedagogy into a red build, and the same sweep let the examples'
      # receipts print PASS lines as if they were this repository's own
      # claims, which is worse than the red. This repository carries no live
      # dossier today, so all four gates read NO-DATA here, printed in full:
      # NO-DATA is never a pass, and never a manufactured failure either.
      - name: Hard gates (numbers, migration, approval, ran) block on failure
        run: python3 tools/sbe_gate.py --strict design
      # A waiver is not a pass. `.sbe-exempt` lets a template library or a finished
      # project stop blocking every unrelated merge, and the exit code cannot tell
      # you one was used, so this step surfaces every WAIVED line as an annotation
      # and in the job summary. A human sees it, or it is not a control. Add
      # --strict-waivers here if you want an exemption to block outright.
      - name: Design checks (dossier completeness) block on failure
        run: |
          set -o pipefail
          python3 tools/sbe_design.py --strict . | tee design-checks.out
      # The pattern is `^  >> `, the prefix sbe_design.py puts on a waived line, and
      # not the word WAIVED. The banner the tool prints on every run ends "WAIVED
      # is not a pass either", so `grep -q 'WAIVED'` was unconditionally true: every
      # clean run told the reviewer that a .sbe-exempt had waived one or more design
      # checks and that nothing opened a file for them, over a run in which every
      # check opened its files. An assurance signal that always fires carries no
      # information, and this one asserted something false, which trains a reviewer
      # to ignore the single control that makes WAIVED visible in CI at all.
      - name: Surface design waivers (a waiver is not a pass)
        if: always()
        run: |
          if grep -qE '^  >> ' design-checks.out; then
            grep -E '^  >> ' design-checks.out | while read -r line; do
              echo "::warning title=BrotherSBE design waiver::$line"
            done
            {
              echo '### BrotherSBE design waivers'
              echo 'A `.sbe-exempt` waived one or more design checks. Nothing opened a file for them.'
              echo '```'
              grep -E '^  >> |^WAIVERS: ' design-checks.out
              echo '```'
            } >> "$GITHUB_STEP_SUMMARY"
          fi
      # Severity is declared per check and printed on every verdict line: --strict
      # blocks on gate severity (the lints), and --strict-soft is the visible
      # opt-in that makes soft-severity (graded) FAILs block too. This workflow
      # passes both, which is this repository's choice, not a default; drop
      # --strict-soft to let graded checks fail without stopping a merge.
      - name: Silent-failure lints and code-graded checks block on failure
        run: python3 tools/sbe_score.py --strict --strict-soft .
      # The gates above are only worth what their tests are worth. These two ran
      # on nobody's merge path until now, which made them documentation rather
      # than a gate: a fixture no merge runs cannot stop anything.
      - name: Regression evals (every gate against the defect it exists to catch)
        run: python3 evals/run_evals.py
      - name: Replay detail on failure (which excerpt blocks differ, and how)
        if: failure()
        run: |
          python3 --version
          python3 evals/replay_book.py || true
          python3 evals/replay_guide05.py || true
      # Two passes: the fixed sweep, then a seeded random composition of the
      # same hollowing operations (--seed). The seeds are fixed so CI is
      # reproducible; a failing scenario prints its seed in its id. A wider
      # search is one more --seed here, not new test code.
      - name: Honesty meta-test (no check may PASS over evidence it never examined)
        run: |
          python3 evals/test_no_data_class.py
          python3 evals/test_no_data_class.py --quiet --seed 1 --seed 2 --seed 3
      - name: Tool tests (redaction, permissions, identity, autosave, plugin surface, CLI)
        run: python3 tools/test_sbe.py
      # Both suites below existed and ran on nobody's merge path, which is the
      # same "documentation rather than a gate" condition the comment above
      # names. The fence hook is an enforcement boundary and the impact fixtures
      # carry the defect that a declared tier can contradict the diff; neither
      # is worth anything if a merge never runs it.
      - name: Fence hook tests (the write boundary)
        run: python3 tools/test_sbe_fence_hook.py
      - name: Impact fixtures (a declared tier cannot contradict the diff silently)
        run: python3 tools/test_sbe_impact.py
      # The suites below are the same "documentation rather than a gate"
      # condition the comment above names: each one existed on disk and ran
      # on nobody's merge path until this step wired it in. Listed in the
      # order tools/test_sbe*.py sorts, so a new suite dropped into tools/
      # is easy to spot missing from this list.
      - name: Adopt and init fixtures (sbe adopt, sbe init)
        run: python3 tools/test_sbe_adopt.py
      - name: Authority hook fixtures (undeclared edits to authority files refused)
        run: python3 tools/test_sbe_authority_hook.py
      - name: Benchmark fixtures (the comparative harness, and its ground-truth leak guard)
        run: python3 benchmarks/test_sbe_bench.py
      - name: Book estate fixtures (the worked example the book's chapters paste)
        run: python3 tools/test_sbe_book.py
      - name: Bypass fixtures (the ways a person or an agent gets past these controls)
        run: python3 tools/test_sbe_bypass.py
      - name: Consumer minting fixtures (the job produces the evidence it demands)
        run: python3 tools/test_sbe_consumer_mint.py
      - name: Converge fixtures (sbe converge)
        run: python3 tools/test_sbe_converge.py
      - name: Decision contract fixtures (every key decision surface names its falsification tier)
        run: python3 tools/test_sbe_decision_contract.py
      - name: Decision package fixtures (sbe explain, sbe lineage)
        run: python3 tools/test_sbe_decisions.py
      - name: Evidence fixtures (a receipt cannot be typed by the same process it verifies)
        run: python3 tools/test_sbe_evidence.py
      - name: Golden scenario (the whole chain, start through acknowledge, real engine)
        run: python3 tools/test_sbe_golden_scenario.py
      - name: Handover fixtures (sbe handover, identity forgeries refused)
        run: python3 tools/test_sbe_handover.py
      - name: Import hygiene fixtures (the six sys.path mounts collapsed into one)
        run: python3 tools/test_sbe_import_hygiene.py
      - name: Instruction surface fixtures (changed authority files outside declared scope)
        run: python3 tools/test_sbe_instruction_surface.py
      - name: Interoperability fixtures (namespacing, no foreign writes, coexistence)
        run: python3 tools/test_sbe_interop.py
      - name: Install script fixtures (dry-run, missing prerequisites)
        run: python3 tools/test_sbe_install.py
      # Founder instruction 2026-08-07, and the human edit L16 reserves to him:
      # the PUBLIC install path becomes a non-skippable release test. It used to
      # rest on a dated sentence in the README saying the two commands had been
      # run by hand once, which meant the first thing every stranger does was
      # the one thing nothing checked.
      - name: Public install path (the two commands the front page promises)
        run: python3 tools/test_sbe_public_install.py
      - name: Map fixtures (sbe map, a deterministic status map, never a filled template)
        run: python3 tools/test_sbe_map.py
      - name: Plan fixtures (sbe plan)
        run: python3 tools/test_sbe_plan.py
      # This is the canned/offline suite: every GitHub API call is routed
      # through a fake fetch, so it needs no network and no token, and it
      # runs on every PR. tools/test_sbe_prverify_live.py is a separate,
      # deliberately unwired script: it needs BOTH SBE_LIVE_GH_REPO and
      # SBE_LIVE_GH_PR plus a token discoverable the way `sbe pr verify`
      # itself discovers one, none of which this workflow provides, and
      # without them it already prints one NO-DATA line and exits 0 (its
      # own docstring). Wiring it here would either skip silently on every
      # normal run or require CI secrets this repository does not carry, so
      # it stays a manual, opt-in script instead.
      - name: PR verify fixtures (sbe pr verify, canned GitHub API, offline)
        run: python3 tools/test_sbe_prverify.py
      - name: Release invariant fixtures (distributable bytes cannot move without VERSION)
        run: python3 tools/test_sbe_release_invariant.py
      - name: Review record fixtures (normalized findings, commit binding, staleness)
        run: python3 tools/test_sbe_review_record.py
      - name: Review route fixtures (deterministic reviewer selection)
        run: python3 tools/test_sbe_review_route.py
      - name: Review skill fixtures (the skill consumes the route)
        run: python3 tools/test_sbe_review_skill_fixtures.py
      - name: Sandbox fixtures (doc-truth for docs/guides/00-sandbox.md)
        run: python3 tools/test_sbe_sandbox.py
      - name: Status fixtures (sbe status)
        run: python3 tools/test_sbe_status.py
      - name: Team status fixtures (sbe status --team)
        run: python3 tools/test_sbe_status_team.py
      - name: Task fixtures (sbe task)
        run: python3 tools/test_sbe_tasks.py
      - name: Team workflow fixtures (eight execution laws over one fixture)
        run: python3 tools/test_sbe_team_workflow.py
      - name: Version bump fixtures (one command moves every declaration site)
        run: python3 tools/test_sbe_version_bump.py
      - name: Work fixtures (sbe work)
        run: python3 tools/test_sbe_work.py
      - name: Work brief fixtures (sbe work brief)
        run: python3 tools/test_sbe_work_brief.py
      # The kill criterion this wave was cut against, verbatim: an install
      # that needs a manual global settings edit. This proves a plain
      # `git archive HEAD` extracts on its own into an empty directory and
      # verifies clean there (scripts/verify-install.sh, bin/sbe doctor),
      # nothing written outside that one directory.
      - name: Install-from-artifact test (a fresh `git archive` install verifies clean)
        run: sh scripts/test-install-artifact.sh
      # scripts/test-install-artifact.sh above already proves the checksums
      # manifest cannot drift from the bytes it describes; it says nothing
      # about whether VERSION moved when those bytes did, which is the
      # narrower gap this step closes. fetch-depth: 0 on the checkout step
      # above fetches full history for every branch and tag, including the
      # origin/main remote-tracking ref this checker diffs against by
      # default, so the base ref resolves here; a checkout that switched to
      # a shallow clone would make this NO-DATA rather than crash, which is
      # this tool's own stated behavior for a ref it cannot resolve, never a
      # false pass.
      - name: Release invariant (distributable bytes cannot move without VERSION moving)
        run: python3 tools/sbe_release_invariant.py --strict
      # Exercises the real upgrade/rollback path once this repository has cut
      # its first tag; until then it prints NO-DATA and exits 0 without
      # claiming an upgrade was tested, which is the honest result here, not
      # a skip and not a pass (docs/KNOWN-LIMITS.md, "The release candidate
      # ships packaging, not a release").
      - name: Upgrade and rollback test (NO-DATA until a previous tag exists, never a false pass)
        run: sh scripts/test-upgrade-rollback.sh

  # BrotherSBE gates (windows leg), added 2026-08-05, founder-approved, lane
  # T7: the same battery the gates job above runs on Linux and macOS,
  # started from that job's full step list, on windows-latest, pinned to the
  # 3.9 floor only (the promise on the front page; not the informational
  # 3.x leg above, so this addition costs one job run per push, not two).
  # continue-on-error is never set here: a red step blocks a merge exactly
  # like the matrix above does.
  #
  # Two steps are skipped, each named where it is skipped: the two `sh`
  # install and upgrade scripts (docs/KNOWN-LIMITS.md, "Windows is
  # untested") invoke the `sh` interpreter directly, which this leg cannot
  # supply cleanly. Everything else, including the suites that assert POSIX
  # file permission bits (chmod, stat mode checks), now runs for real on
  # Windows for the first time and is free to fail honestly if a POSIX
  # assumption inside one of them does not hold there; that is the point of
  # this leg, not a promise that every suite already passes on Windows.
  gates-windows:
    runs-on: windows-latest
    env:
      # Round 2 of this leg's first day proved the need: two Unicode homoglyph
      # evals (a-lisu-spelling-of-tbd-is-not-a-snapshot-pin and
      # a-small-capital-placeholder-is-not-a-pin) read their fixtures through
      # Windows' legacy locale codec and the gate saw mangled bytes instead of
      # the homoglyph it exists to catch. Linux and macOS already run UTF-8
      # locales; declaring UTF-8 mode here equalizes the environment without
      # touching what any gate tests.
      PYTHONUTF8: "1"
    defaults:
      run:
        # Git for Windows ships bash on windows-latest by default (verified
        # against the runner image's own software manifest on 2026-08-05),
        # so this names no new dependency; it is what makes the multi-line
        # steps below (set -o pipefail, grep, while read, || true) behave
        # the same here as they do on Linux and macOS above, where bash is
        # already the implicit default shell for an unspecified step.
        shell: bash
    steps:
      - name: Line endings stay bytes (autocrlf off before any file exists)
        # The tracked manifest hashes exact bytes and .gitattributes rides
        # INSIDE the checkout, so files extracted before it lands in the
        # working tree could still be converted by the runner's default
        # autocrlf: rounds 1 to 3 of this leg watched the same four
        # early-alphabet files (.brothersbe/config.json, the two
        # .claude-plugin manifests, .gitattributes itself) hash stale on
        # first read and identical on re-read (run 31042529271). Turning
        # conversion off before checkout removes the ordering race the
        # in-tree attributes file cannot close by itself.
        run: git config --global core.autocrlf false
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
        with:
          fetch-depth: 0   # the approval gate reads commit trailers and signatures
      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5
        with:
          python-version: '3.9'
      # Windows reality, confirmed against actions/setup-python's own
      # find-python.ts on 2026-08-05: some images place only python.exe on
      # PATH; the current windows-latest image resolves python3 already (its
      # first real run proved the unconditional copy fails as same-file), so
      # this guard is a no-op there and a bridge only where needed. Every step below still calls python3
      # unmodified, identical to the gates job above, so this one step
      # bridges the gap instead of rewriting each of them.
      - name: Ensure python3 resolves (guard for images shipping only python.exe)
        run: |
          if ! command -v python3 >/dev/null 2>&1; then
            py="$(command -v python)"
            cp "$py" "$(dirname "$py")/python3.exe"
          fi
      # The approval gate accepts a signature only if THIS host verified it. A
      # runner with no public keys imported reports "cannot verify" for every
      # signed commit, which is NO-DATA and not an approval. To use the signed
      # trailer path in CI, import the approvers' public keys first:
      #   - run: gpg --import <<< "${{ secrets.SBE_APPROVER_PUBKEYS }}"
      # Or standardise on the Reviewed-in: <review id> trailer, which needs no
      # keyring at all. Doing neither is legal and honest: approvals then report
      # NO-DATA, instead of a gate that quietly degrades into accepting any
      # signature blob because it could not check one.
      # Scoped to the LIVE dossier root (design/, declared by `sbe init`), not
      # the whole checkout. The first real run of this workflow proved why the
      # wide sweep was wrong twice over: the teaching dossier under
      # docs/for-engineers/examples carries an APPROVAL that is DESIGNED to
      # fail (two documents paste that refusal as the lesson), so scanning it
      # turned pedagogy into a red build, and the same sweep let the examples'
      # receipts print PASS lines as if they were this repository's own
      # claims, which is worse than the red. This repository carries no live
      # dossier today, so all four gates read NO-DATA here, printed in full:
      # NO-DATA is never a pass, and never a manufactured failure either.
      - name: Hard gates (numbers, migration, approval, ran) block on failure
        run: python3 tools/sbe_gate.py --strict design
      # A waiver is not a pass. `.sbe-exempt` lets a template library or a finished
      # project stop blocking every unrelated merge, and the exit code cannot tell
      # you one was used, so this step surfaces every WAIVED line as an annotation
      # and in the job summary. A human sees it, or it is not a control. Add
      # --strict-waivers here if you want an exemption to block outright.
      - name: Design checks (dossier completeness) block on failure
        run: |
          set -o pipefail
          python3 tools/sbe_design.py --strict . | tee design-checks.out
      # The pattern is `^  >> `, the prefix sbe_design.py puts on a waived line, and
      # not the word WAIVED. The banner the tool prints on every run ends "WAIVED
      # is not a pass either", so `grep -q 'WAIVED'` was unconditionally true: every
      # clean run told the reviewer that a .sbe-exempt had waived one or more design
      # checks and that nothing opened a file for them, over a run in which every
      # check opened its files. An assurance signal that always fires carries no
      # information, and this one asserted something false, which trains a reviewer
      # to ignore the single control that makes WAIVED visible in CI at all.
      - name: Surface design waivers (a waiver is not a pass)
        if: always()
        run: |
          if grep -qE '^  >> ' design-checks.out; then
            grep -E '^  >> ' design-checks.out | while read -r line; do
              echo "::warning title=BrotherSBE design waiver::$line"
            done
            {
              echo '### BrotherSBE design waivers'
              echo 'A `.sbe-exempt` waived one or more design checks. Nothing opened a file for them.'
              echo '```'
              grep -E '^  >> |^WAIVERS: ' design-checks.out
              echo '```'
            } >> "$GITHUB_STEP_SUMMARY"
          fi
      # Severity is declared per check and printed on every verdict line: --strict
      # blocks on gate severity (the lints), and --strict-soft is the visible
      # opt-in that makes soft-severity (graded) FAILs block too. This workflow
      # passes both, which is this repository's choice, not a default; drop
      # --strict-soft to let graded checks fail without stopping a merge.
      - name: Silent-failure lints and code-graded checks block on failure
        run: python3 tools/sbe_score.py --strict --strict-soft .
      # The gates above are only worth what their tests are worth. These two ran
      # on nobody's merge path until now, which made them documentation rather
      # than a gate: a fixture no merge runs cannot stop anything.
      - name: Regression evals (every gate against the defect it exists to catch)
        run: python3 evals/run_evals.py
      - name: Replay detail on failure (which excerpt blocks differ, and how)
        if: failure()
        run: |
          python3 --version
          python3 evals/replay_book.py || true
          python3 evals/replay_guide05.py || true
      # Two passes: the fixed sweep, then a seeded random composition of the
      # same hollowing operations (--seed). The seeds are fixed so CI is
      # reproducible; a failing scenario prints its seed in its id. A wider
      # search is one more --seed here, not new test code.
      - name: Honesty meta-test (no check may PASS over evidence it never examined)
        run: |
          python3 evals/test_no_data_class.py
          python3 evals/test_no_data_class.py --quiet --seed 1 --seed 2 --seed 3
      - name: Tool tests (redaction, permissions, identity, autosave, plugin surface, CLI)
        run: python3 tools/test_sbe.py
      # Both suites below existed and ran on nobody's merge path, which is the
      # same "documentation rather than a gate" condition the comment above
      # names. The fence hook is an enforcement boundary and the impact fixtures
      # carry the defect that a declared tier can contradict the diff; neither
      # is worth anything if a merge never runs it.
      - name: Fence hook tests (the write boundary)
        run: python3 tools/test_sbe_fence_hook.py
      - name: Impact fixtures (a declared tier cannot contradict the diff silently)
        run: python3 tools/test_sbe_impact.py
      # The suites below are the same "documentation rather than a gate"
      # condition the comment above names: each one existed on disk and ran
      # on nobody's merge path until this step wired it in. Listed in the
      # order tools/test_sbe*.py sorts, so a new suite dropped into tools/
      # is easy to spot missing from this list.
      - name: Adopt and init fixtures (sbe adopt, sbe init)
        run: python3 tools/test_sbe_adopt.py
      - name: Authority hook fixtures (undeclared edits to authority files refused)
        run: python3 tools/test_sbe_authority_hook.py
      - name: Benchmark fixtures (the comparative harness, and its ground-truth leak guard)
        run: python3 benchmarks/test_sbe_bench.py
      - name: Book estate fixtures (the worked example the book's chapters paste)
        run: python3 tools/test_sbe_book.py
      - name: Bypass fixtures (the ways a person or an agent gets past these controls)
        run: python3 tools/test_sbe_bypass.py
      - name: Consumer minting fixtures (the job produces the evidence it demands)
        run: python3 tools/test_sbe_consumer_mint.py
      - name: Converge fixtures (sbe converge)
        run: python3 tools/test_sbe_converge.py
      - name: Decision package fixtures (sbe explain, sbe lineage)
        run: python3 tools/test_sbe_decisions.py
      - name: Evidence fixtures (a receipt cannot be typed by the same process it verifies)
        run: python3 tools/test_sbe_evidence.py
      - name: Golden scenario (the whole chain, start through acknowledge, real engine)
        run: python3 tools/test_sbe_golden_scenario.py
      - name: Handover fixtures (sbe handover, identity forgeries refused)
        run: python3 tools/test_sbe_handover.py
      - name: Instruction surface fixtures (changed authority files outside declared scope)
        run: python3 tools/test_sbe_instruction_surface.py
      - name: Interoperability fixtures (namespacing, no foreign writes, coexistence)
        run: python3 tools/test_sbe_interop.py
      - name: Install script fixtures (dry-run, missing prerequisites)
        run: python3 tools/test_sbe_install.py
      - name: Plan fixtures (sbe plan)
        run: python3 tools/test_sbe_plan.py
      # This is the canned/offline suite: every GitHub API call is routed
      # through a fake fetch, so it needs no network and no token, and it
      # runs on every PR. tools/test_sbe_prverify_live.py is a separate,
      # deliberately unwired script: it needs BOTH SBE_LIVE_GH_REPO and
      # SBE_LIVE_GH_PR plus a token discoverable the way `sbe pr verify`
      # itself discovers one, none of which this workflow provides, and
      # without them it already prints one NO-DATA line and exits 0 (its
      # own docstring). Wiring it here would either skip silently on every
      # normal run or require CI secrets this repository does not carry, so
      # it stays a manual, opt-in script instead.
      - name: PR verify fixtures (sbe pr verify, canned GitHub API, offline)
        run: python3 tools/test_sbe_prverify.py
      - name: Release invariant fixtures (distributable bytes cannot move without VERSION)
        run: python3 tools/test_sbe_release_invariant.py
      - name: Review record fixtures (normalized findings, commit binding, staleness)
        run: python3 tools/test_sbe_review_record.py
      - name: Review route fixtures (deterministic reviewer selection)
        run: python3 tools/test_sbe_review_route.py
      - name: Review skill fixtures (the skill consumes the route)
        run: python3 tools/test_sbe_review_skill_fixtures.py
      - name: Status fixtures (sbe status)
        run: python3 tools/test_sbe_status.py
      - name: Team status fixtures (sbe status --team)
        run: python3 tools/test_sbe_status_team.py
      - name: Task fixtures (sbe task)
        run: python3 tools/test_sbe_tasks.py
      - name: Team workflow fixtures (eight execution laws over one fixture)
        run: python3 tools/test_sbe_team_workflow.py
      - name: Version bump fixtures (one command moves every declaration site)
        run: python3 tools/test_sbe_version_bump.py
      - name: Work fixtures (sbe work)
        run: python3 tools/test_sbe_work.py
      - name: Work brief fixtures (sbe work brief)
        run: python3 tools/test_sbe_work_brief.py
      # EXCLUDED on windows-latest: this step ran `sh scripts/test-install-artifact.sh`, a POSIX `sh` script never exercised on Windows (docs/KNOWN-LIMITS.md, "Windows CI runs, with named gaps").
      # On Linux and macOS, scripts/test-install-artifact.sh above already proves
      # the checksums manifest cannot drift from the bytes it describes; that
      # script is excluded on this Windows leg (see the exclusion comment just
      # above), so this step's own narrower claim, that VERSION moves when
      # distributable bytes do, stands on its own here. fetch-depth: 0 on the
      # checkout step above fetches full history for every branch and tag,
      # including the origin/main remote-tracking ref this checker diffs
      # against by default, so the base ref resolves here; a checkout that
      # switched to a shallow clone would make this NO-DATA rather than
      # crash, which is this tool's own stated behavior for a ref it cannot
      # resolve, never a false pass.
      - name: Release invariant (distributable bytes cannot move without VERSION moving)
        run: python3 tools/sbe_release_invariant.py --strict
      # EXCLUDED on windows-latest: this step ran `sh scripts/test-upgrade-rollback.sh`, a POSIX `sh` script never exercised on Windows (docs/KNOWN-LIMITS.md, "Windows CI runs, with named gaps").
```'
              grep -E '^  >> |^WAIVERS: ' design-checks.out
              echo '```'
            } >> "$GITHUB_STEP_SUMMARY"
          fi
      # Severity is declared per check and printed on every verdict line: --strict
      # blocks on gate severity (the lints), and --strict-soft is the visible
      # opt-in that makes soft-severity (graded) FAILs block too. This workflow
      # passes both, which is this repository's choice, not a default; drop
      # --strict-soft to let graded checks fail without stopping a merge.
      - name: Silent-failure lints and code-graded checks block on failure
        run: python3 tools/sbe_score.py --strict --strict-soft .
      # The gates above are only worth what their tests are worth. These two ran
      # on nobody's merge path until now, which made them documentation rather
      # than a gate: a fixture no merge runs cannot stop anything.
      - name: Regression evals (every gate against the defect it exists to catch)
        run: python3 evals/run_evals.py
      - name: Replay detail on failure (which excerpt blocks differ, and how)
        if: failure()
        run: |
          python3 --version
          python3 evals/replay_book.py || true
          python3 evals/replay_guide05.py || true
      # Two passes: the fixed sweep, then a seeded random composition of the
      # same hollowing operations (--seed). The seeds are fixed so CI is
      # reproducible; a failing scenario prints its seed in its id. A wider
      # search is one more --seed here, not new test code.
      - name: Honesty meta-test (no check may PASS over evidence it never examined)
        run: |
          python3 evals/test_no_data_class.py
          python3 evals/test_no_data_class.py --quiet --seed 1 --seed 2 --seed 3
      - name: Tool tests (redaction, permissions, identity, autosave, plugin surface, CLI)
        run: python3 tools/test_sbe.py
      # Both suites below existed and ran on nobody's merge path, which is the
      # same "documentation rather than a gate" condition the comment above
      # names. The fence hook is an enforcement boundary and the impact fixtures
      # carry the defect that a declared tier can contradict the diff; neither
      # is worth anything if a merge never runs it.
      - name: Fence hook tests (the write boundary)
        run: python3 tools/test_sbe_fence_hook.py
      - name: Impact fixtures (a declared tier cannot contradict the diff silently)
        run: python3 tools/test_sbe_impact.py
      # The suites below are the same "documentation rather than a gate"
      # condition the comment above names: each one existed on disk and ran
      # on nobody's merge path until this step wired it in. Listed in the
      # order tools/test_sbe*.py sorts, so a new suite dropped into tools/
      # is easy to spot missing from this list.
      - name: Adopt and init fixtures (sbe adopt, sbe init)
        run: python3 tools/test_sbe_adopt.py
      - name: Authority hook fixtures (undeclared edits to authority files refused)
        run: python3 tools/test_sbe_authority_hook.py
      - name: Benchmark fixtures (the comparative harness, and its ground-truth leak guard)
        run: python3 benchmarks/test_sbe_bench.py
      - name: Book estate fixtures (the worked example the book's chapters paste)
        run: python3 tools/test_sbe_book.py
      - name: Bypass fixtures (the ways a person or an agent gets past these controls)
        run: python3 tools/test_sbe_bypass.py
      - name: Converge fixtures (sbe converge)
        run: python3 tools/test_sbe_converge.py
      - name: Decision contract fixtures (every key decision surface names its falsification tier)
        run: python3 tools/test_sbe_decision_contract.py
      - name: Decision package fixtures (sbe explain, sbe lineage)
        run: python3 tools/test_sbe_decisions.py
      - name: Evidence fixtures (a receipt cannot be typed by the same process it verifies)
        run: python3 tools/test_sbe_evidence.py
      - name: Golden scenario (the whole chain, start through acknowledge, real engine)
        run: python3 tools/test_sbe_golden_scenario.py
      - name: Handover fixtures (sbe handover, identity forgeries refused)
        run: python3 tools/test_sbe_handover.py
      - name: Import hygiene fixtures (the six sys.path mounts collapsed into one)
        run: python3 tools/test_sbe_import_hygiene.py
      - name: Instruction surface fixtures (changed authority files outside declared scope)
        run: python3 tools/test_sbe_instruction_surface.py
      - name: Interoperability fixtures (namespacing, no foreign writes, coexistence)
        run: python3 tools/test_sbe_interop.py
      - name: Install script fixtures (dry-run, missing prerequisites)
        run: python3 tools/test_sbe_install.py
      # Founder instruction 2026-08-07, and the human edit L16 reserves to him:
      # the PUBLIC install path becomes a non-skippable release test. It used to
      # rest on a dated sentence in the README saying the two commands had been
      # run by hand once, which meant the first thing every stranger does was
      # the one thing nothing checked.
      - name: Public install path (the two commands the front page promises)
        run: python3 tools/test_sbe_public_install.py
      - name: Map fixtures (sbe map, a deterministic status map, never a filled template)
        run: python3 tools/test_sbe_map.py
      - name: Plan fixtures (sbe plan)
        run: python3 tools/test_sbe_plan.py
      # This is the canned/offline suite: every GitHub API call is routed
      # through a fake fetch, so it needs no network and no token, and it
      # runs on every PR. tools/test_sbe_prverify_live.py is a separate,
      # deliberately unwired script: it needs BOTH SBE_LIVE_GH_REPO and
      # SBE_LIVE_GH_PR plus a token discoverable the way `sbe pr verify`
      # itself discovers one, none of which this workflow provides, and
      # without them it already prints one NO-DATA line and exits 0 (its
      # own docstring). Wiring it here would either skip silently on every
      # normal run or require CI secrets this repository does not carry, so
      # it stays a manual, opt-in script instead.
      - name: PR verify fixtures (sbe pr verify, canned GitHub API, offline)
        run: python3 tools/test_sbe_prverify.py
      - name: Release invariant fixtures (distributable bytes cannot move without VERSION)
        run: python3 tools/test_sbe_release_invariant.py
      - name: Review record fixtures (normalized findings, commit binding, staleness)
        run: python3 tools/test_sbe_review_record.py
      - name: Review route fixtures (deterministic reviewer selection)
        run: python3 tools/test_sbe_review_route.py
      - name: Review skill fixtures (the skill consumes the route)
        run: python3 tools/test_sbe_review_skill_fixtures.py
      - name: Sandbox fixtures (doc-truth for docs/guides/00-sandbox.md)
        run: python3 tools/test_sbe_sandbox.py
      - name: Status fixtures (sbe status)
        run: python3 tools/test_sbe_status.py
      - name: Team status fixtures (sbe status --team)
        run: python3 tools/test_sbe_status_team.py
      - name: Task fixtures (sbe task)
        run: python3 tools/test_sbe_tasks.py
      - name: Team workflow fixtures (eight execution laws over one fixture)
        run: python3 tools/test_sbe_team_workflow.py
      - name: Version bump fixtures (one command moves every declaration site)
        run: python3 tools/test_sbe_version_bump.py
      - name: Work fixtures (sbe work)
        run: python3 tools/test_sbe_work.py
      - name: Work brief fixtures (sbe work brief)
        run: python3 tools/test_sbe_work_brief.py
      # The kill criterion this wave was cut against, verbatim: an install
      # that needs a manual global settings edit. This proves a plain
      # `git archive HEAD` extracts on its own into an empty directory and
      # verifies clean there (scripts/verify-install.sh, bin/sbe doctor),
      # nothing written outside that one directory.
      - name: Install-from-artifact test (a fresh `git archive` install verifies clean)
        run: sh scripts/test-install-artifact.sh
      # scripts/test-install-artifact.sh above already proves the checksums
      # manifest cannot drift from the bytes it describes; it says nothing
      # about whether VERSION moved when those bytes did, which is the
      # narrower gap this step closes. fetch-depth: 0 on the checkout step
      # above fetches full history for every branch and tag, including the
      # origin/main remote-tracking ref this checker diffs against by
      # default, so the base ref resolves here; a checkout that switched to
      # a shallow clone would make this NO-DATA rather than crash, which is
      # this tool's own stated behavior for a ref it cannot resolve, never a
      # false pass.
      - name: Release invariant (distributable bytes cannot move without VERSION moving)
        run: python3 tools/sbe_release_invariant.py --strict
      # Exercises the real upgrade/rollback path once this repository has cut
      # its first tag; until then it prints NO-DATA and exits 0 without
      # claiming an upgrade was tested, which is the honest result here, not
      # a skip and not a pass (docs/KNOWN-LIMITS.md, "The release candidate
      # ships packaging, not a release").
      - name: Upgrade and rollback test (NO-DATA until a previous tag exists, never a false pass)
        run: sh scripts/test-upgrade-rollback.sh

  # BrotherSBE gates (windows leg), added 2026-08-05, founder-approved, lane
  # T7: the same battery the gates job above runs on Linux and macOS,
  # started from that job's full step list, on windows-latest, pinned to the
  # 3.9 floor only (the promise on the front page; not the informational
  # 3.x leg above, so this addition costs one job run per push, not two).
  # continue-on-error is never set here: a red step blocks a merge exactly
  # like the matrix above does.
  #
  # Two steps are skipped, each named where it is skipped: the two `sh`
  # install and upgrade scripts (docs/KNOWN-LIMITS.md, "Windows is
  # untested") invoke the `sh` interpreter directly, which this leg cannot
  # supply cleanly. Everything else, including the suites that assert POSIX
  # file permission bits (chmod, stat mode checks), now runs for real on
  # Windows for the first time and is free to fail honestly if a POSIX
  # assumption inside one of them does not hold there; that is the point of
  # this leg, not a promise that every suite already passes on Windows.
  gates-windows:
    runs-on: windows-latest
    env:
      # Round 2 of this leg's first day proved the need: two Unicode homoglyph
      # evals (a-lisu-spelling-of-tbd-is-not-a-snapshot-pin and
      # a-small-capital-placeholder-is-not-a-pin) read their fixtures through
      # Windows' legacy locale codec and the gate saw mangled bytes instead of
      # the homoglyph it exists to catch. Linux and macOS already run UTF-8
      # locales; declaring UTF-8 mode here equalizes the environment without
      # touching what any gate tests.
      PYTHONUTF8: "1"
    defaults:
      run:
        # Git for Windows ships bash on windows-latest by default (verified
        # against the runner image's own software manifest on 2026-08-05),
        # so this names no new dependency; it is what makes the multi-line
        # steps below (set -o pipefail, grep, while read, || true) behave
        # the same here as they do on Linux and macOS above, where bash is
        # already the implicit default shell for an unspecified step.
        shell: bash
    steps:
      - name: Line endings stay bytes (autocrlf off before any file exists)
        # The tracked manifest hashes exact bytes and .gitattributes rides
        # INSIDE the checkout, so files extracted before it lands in the
        # working tree could still be converted by the runner's default
        # autocrlf: rounds 1 to 3 of this leg watched the same four
        # early-alphabet files (.brothersbe/config.json, the two
        # .claude-plugin manifests, .gitattributes itself) hash stale on
        # first read and identical on re-read (run 31042529271). Turning
        # conversion off before checkout removes the ordering race the
        # in-tree attributes file cannot close by itself.
        run: git config --global core.autocrlf false
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
        with:
          fetch-depth: 0   # the approval gate reads commit trailers and signatures
      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5
        with:
          python-version: '3.9'
      # Windows reality, confirmed against actions/setup-python's own
      # find-python.ts on 2026-08-05: some images place only python.exe on
      # PATH; the current windows-latest image resolves python3 already (its
      # first real run proved the unconditional copy fails as same-file), so
      # this guard is a no-op there and a bridge only where needed. Every step below still calls python3
      # unmodified, identical to the gates job above, so this one step
      # bridges the gap instead of rewriting each of them.
      - name: Ensure python3 resolves (guard for images shipping only python.exe)
        run: |
          if ! command -v python3 >/dev/null 2>&1; then
            py="$(command -v python)"
            cp "$py" "$(dirname "$py")/python3.exe"
          fi
      # The approval gate accepts a signature only if THIS host verified it. A
      # runner with no public keys imported reports "cannot verify" for every
      # signed commit, which is NO-DATA and not an approval. To use the signed
      # trailer path in CI, import the approvers' public keys first:
      #   - run: gpg --import <<< "${{ secrets.SBE_APPROVER_PUBKEYS }}"
      # Or standardise on the Reviewed-in: <review id> trailer, which needs no
      # keyring at all. Doing neither is legal and honest: approvals then report
      # NO-DATA, instead of a gate that quietly degrades into accepting any
      # signature blob because it could not check one.
      # Scoped to the LIVE dossier root (design/, declared by `sbe init`), not
      # the whole checkout. The first real run of this workflow proved why the
      # wide sweep was wrong twice over: the teaching dossier under
      # docs/for-engineers/examples carries an APPROVAL that is DESIGNED to
      # fail (two documents paste that refusal as the lesson), so scanning it
      # turned pedagogy into a red build, and the same sweep let the examples'
      # receipts print PASS lines as if they were this repository's own
      # claims, which is worse than the red. This repository carries no live
      # dossier today, so all four gates read NO-DATA here, printed in full:
      # NO-DATA is never a pass, and never a manufactured failure either.
      - name: Hard gates (numbers, migration, approval, ran) block on failure
        run: python3 tools/sbe_gate.py --strict design
      # A waiver is not a pass. `.sbe-exempt` lets a template library or a finished
      # project stop blocking every unrelated merge, and the exit code cannot tell
      # you one was used, so this step surfaces every WAIVED line as an annotation
      # and in the job summary. A human sees it, or it is not a control. Add
      # --strict-waivers here if you want an exemption to block outright.
      - name: Design checks (dossier completeness) block on failure
        run: |
          set -o pipefail
          python3 tools/sbe_design.py --strict . | tee design-checks.out
      # The pattern is `^  >> `, the prefix sbe_design.py puts on a waived line, and
      # not the word WAIVED. The banner the tool prints on every run ends "WAIVED
      # is not a pass either", so `grep -q 'WAIVED'` was unconditionally true: every
      # clean run told the reviewer that a .sbe-exempt had waived one or more design
      # checks and that nothing opened a file for them, over a run in which every
      # check opened its files. An assurance signal that always fires carries no
      # information, and this one asserted something false, which trains a reviewer
      # to ignore the single control that makes WAIVED visible in CI at all.
      - name: Surface design waivers (a waiver is not a pass)
        if: always()
        run: |
          if grep -qE '^  >> ' design-checks.out; then
            grep -E '^  >> ' design-checks.out | while read -r line; do
              echo "::warning title=BrotherSBE design waiver::$line"
            done
            {
              echo '### BrotherSBE design waivers'
              echo 'A `.sbe-exempt` waived one or more design checks. Nothing opened a file for them.'
              echo '```'
              grep -E '^  >> |^WAIVERS: ' design-checks.out
              echo '```'
            } >> "$GITHUB_STEP_SUMMARY"
          fi
      # Severity is declared per check and printed on every verdict line: --strict
      # blocks on gate severity (the lints), and --strict-soft is the visible
      # opt-in that makes soft-severity (graded) FAILs block too. This workflow
      # passes both, which is this repository's choice, not a default; drop
      # --strict-soft to let graded checks fail without stopping a merge.
      - name: Silent-failure lints and code-graded checks block on failure
        run: python3 tools/sbe_score.py --strict --strict-soft .
      # The gates above are only worth what their tests are worth. These two ran
      # on nobody's merge path until now, which made them documentation rather
      # than a gate: a fixture no merge runs cannot stop anything.
      - name: Regression evals (every gate against the defect it exists to catch)
        run: python3 evals/run_evals.py
      - name: Replay detail on failure (which excerpt blocks differ, and how)
        if: failure()
        run: |
          python3 --version
          python3 evals/replay_book.py || true
          python3 evals/replay_guide05.py || true
      # Two passes: the fixed sweep, then a seeded random composition of the
      # same hollowing operations (--seed). The seeds are fixed so CI is
      # reproducible; a failing scenario prints its seed in its id. A wider
      # search is one more --seed here, not new test code.
      - name: Honesty meta-test (no check may PASS over evidence it never examined)
        run: |
          python3 evals/test_no_data_class.py
          python3 evals/test_no_data_class.py --quiet --seed 1 --seed 2 --seed 3
      - name: Tool tests (redaction, permissions, identity, autosave, plugin surface, CLI)
        run: python3 tools/test_sbe.py
      # Both suites below existed and ran on nobody's merge path, which is the
      # same "documentation rather than a gate" condition the comment above
      # names. The fence hook is an enforcement boundary and the impact fixtures
      # carry the defect that a declared tier can contradict the diff; neither
      # is worth anything if a merge never runs it.
      - name: Fence hook tests (the write boundary)
        run: python3 tools/test_sbe_fence_hook.py
      - name: Impact fixtures (a declared tier cannot contradict the diff silently)
        run: python3 tools/test_sbe_impact.py
      # The suites below are the same "documentation rather than a gate"
      # condition the comment above names: each one existed on disk and ran
      # on nobody's merge path until this step wired it in. Listed in the
      # order tools/test_sbe*.py sorts, so a new suite dropped into tools/
      # is easy to spot missing from this list.
      - name: Adopt and init fixtures (sbe adopt, sbe init)
        run: python3 tools/test_sbe_adopt.py
      - name: Authority hook fixtures (undeclared edits to authority files refused)
        run: python3 tools/test_sbe_authority_hook.py
      - name: Benchmark fixtures (the comparative harness, and its ground-truth leak guard)
        run: python3 benchmarks/test_sbe_bench.py
      - name: Book estate fixtures (the worked example the book's chapters paste)
        run: python3 tools/test_sbe_book.py
      - name: Bypass fixtures (the ways a person or an agent gets past these controls)
        run: python3 tools/test_sbe_bypass.py
      - name: Converge fixtures (sbe converge)
        run: python3 tools/test_sbe_converge.py
      - name: Decision package fixtures (sbe explain, sbe lineage)
        run: python3 tools/test_sbe_decisions.py
      - name: Evidence fixtures (a receipt cannot be typed by the same process it verifies)
        run: python3 tools/test_sbe_evidence.py
      - name: Golden scenario (the whole chain, start through acknowledge, real engine)
        run: python3 tools/test_sbe_golden_scenario.py
      - name: Handover fixtures (sbe handover, identity forgeries refused)
        run: python3 tools/test_sbe_handover.py
      - name: Instruction surface fixtures (changed authority files outside declared scope)
        run: python3 tools/test_sbe_instruction_surface.py
      - name: Interoperability fixtures (namespacing, no foreign writes, coexistence)
        run: python3 tools/test_sbe_interop.py
      - name: Install script fixtures (dry-run, missing prerequisites)
        run: python3 tools/test_sbe_install.py
      - name: Plan fixtures (sbe plan)
        run: python3 tools/test_sbe_plan.py
      # This is the canned/offline suite: every GitHub API call is routed
      # through a fake fetch, so it needs no network and no token, and it
      # runs on every PR. tools/test_sbe_prverify_live.py is a separate,
      # deliberately unwired script: it needs BOTH SBE_LIVE_GH_REPO and
      # SBE_LIVE_GH_PR plus a token discoverable the way `sbe pr verify`
      # itself discovers one, none of which this workflow provides, and
      # without them it already prints one NO-DATA line and exits 0 (its
      # own docstring). Wiring it here would either skip silently on every
      # normal run or require CI secrets this repository does not carry, so
      # it stays a manual, opt-in script instead.
      - name: PR verify fixtures (sbe pr verify, canned GitHub API, offline)
        run: python3 tools/test_sbe_prverify.py
      - name: Release invariant fixtures (distributable bytes cannot move without VERSION)
        run: python3 tools/test_sbe_release_invariant.py
      - name: Review record fixtures (normalized findings, commit binding, staleness)
        run: python3 tools/test_sbe_review_record.py
      - name: Review route fixtures (deterministic reviewer selection)
        run: python3 tools/test_sbe_review_route.py
      - name: Review skill fixtures (the skill consumes the route)
        run: python3 tools/test_sbe_review_skill_fixtures.py
      - name: Status fixtures (sbe status)
        run: python3 tools/test_sbe_status.py
      - name: Team status fixtures (sbe status --team)
        run: python3 tools/test_sbe_status_team.py
      - name: Task fixtures (sbe task)
        run: python3 tools/test_sbe_tasks.py
      - name: Team workflow fixtures (eight execution laws over one fixture)
        run: python3 tools/test_sbe_team_workflow.py
      - name: Version bump fixtures (one command moves every declaration site)
        run: python3 tools/test_sbe_version_bump.py
      - name: Work fixtures (sbe work)
        run: python3 tools/test_sbe_work.py
      - name: Work brief fixtures (sbe work brief)
        run: python3 tools/test_sbe_work_brief.py
      # EXCLUDED on windows-latest: this step ran `sh scripts/test-install-artifact.sh`, a POSIX `sh` script never exercised on Windows (docs/KNOWN-LIMITS.md, "Windows CI runs, with named gaps").
      # On Linux and macOS, scripts/test-install-artifact.sh above already proves
      # the checksums manifest cannot drift from the bytes it describes; that
      # script is excluded on this Windows leg (see the exclusion comment just
      # above), so this step's own narrower claim, that VERSION moves when
      # distributable bytes do, stands on its own here. fetch-depth: 0 on the
      # checkout step above fetches full history for every branch and tag,
      # including the origin/main remote-tracking ref this checker diffs
      # against by default, so the base ref resolves here; a checkout that
      # switched to a shallow clone would make this NO-DATA rather than
      # crash, which is this tool's own stated behavior for a ref it cannot
      # resolve, never a false pass.
      - name: Release invariant (distributable bytes cannot move without VERSION moving)
        run: python3 tools/sbe_release_invariant.py --strict
      # EXCLUDED on windows-latest: this step ran `sh scripts/test-upgrade-rollback.sh`, a POSIX `sh` script never exercised on Windows (docs/KNOWN-LIMITS.md, "Windows CI runs, with named gaps").
```'
              grep -E '^  >> |^WAIVERS: ' design-checks.out
              echo '```'
            } >> "$GITHUB_STEP_SUMMARY"
          fi
      # Severity is declared per check and printed on every verdict line: --strict
      # blocks on gate severity (the lints), and --strict-soft is the visible
      # opt-in that makes soft-severity (graded) FAILs block too. This workflow
      # passes both, which is this repository's choice, not a default; drop
      # --strict-soft to let graded checks fail without stopping a merge.
      - name: Silent-failure lints and code-graded checks block on failure
        run: python3 tools/sbe_score.py --strict --strict-soft .
      # The gates above are only worth what their tests are worth. These two ran
      # on nobody's merge path until now, which made them documentation rather
      # than a gate: a fixture no merge runs cannot stop anything.
      - name: Regression evals (every gate against the defect it exists to catch)
        run: python3 evals/run_evals.py
      - name: Replay detail on failure (which excerpt blocks differ, and how)
        if: failure()
        run: |
          python3 --version
          python3 evals/replay_book.py || true
          python3 evals/replay_guide05.py || true
      # Two passes: the fixed sweep, then a seeded random composition of the
      # same hollowing operations (--seed). The seeds are fixed so CI is
      # reproducible; a failing scenario prints its seed in its id. A wider
      # search is one more --seed here, not new test code.
      - name: Honesty meta-test (no check may PASS over evidence it never examined)
        run: |
          python3 evals/test_no_data_class.py
          python3 evals/test_no_data_class.py --quiet --seed 1 --seed 2 --seed 3
      - name: Tool tests (redaction, permissions, identity, autosave, plugin surface, CLI)
        run: python3 tools/test_sbe.py
      # Both suites below existed and ran on nobody's merge path, which is the
      # same "documentation rather than a gate" condition the comment above
      # names. The fence hook is an enforcement boundary and the impact fixtures
      # carry the defect that a declared tier can contradict the diff; neither
      # is worth anything if a merge never runs it.
      - name: Fence hook tests (the write boundary)
        run: python3 tools/test_sbe_fence_hook.py
      - name: Impact fixtures (a declared tier cannot contradict the diff silently)
        run: python3 tools/test_sbe_impact.py
      # The suites below are the same "documentation rather than a gate"
      # condition the comment above names: each one existed on disk and ran
      # on nobody's merge path until this step wired it in. Listed in the
      # order tools/test_sbe*.py sorts, so a new suite dropped into tools/
      # is easy to spot missing from this list.
      - name: Adopt and init fixtures (sbe adopt, sbe init)
        run: python3 tools/test_sbe_adopt.py
      - name: Authority hook fixtures (undeclared edits to authority files refused)
        run: python3 tools/test_sbe_authority_hook.py
      - name: Benchmark fixtures (the comparative harness, and its ground-truth leak guard)
        run: python3 benchmarks/test_sbe_bench.py
      - name: Book estate fixtures (the worked example the book's chapters paste)
        run: python3 tools/test_sbe_book.py
      - name: Bypass fixtures (the ways a person or an agent gets past these controls)
        run: python3 tools/test_sbe_bypass.py
      - name: Converge fixtures (sbe converge)
        run: python3 tools/test_sbe_converge.py
      - name: Decision contract fixtures (every key decision surface names its falsification tier)
        run: python3 tools/test_sbe_decision_contract.py
      - name: Decision package fixtures (sbe explain, sbe lineage)
        run: python3 tools/test_sbe_decisions.py
      - name: Evidence fixtures (a receipt cannot be typed by the same process it verifies)
        run: python3 tools/test_sbe_evidence.py
      - name: Golden scenario (the whole chain, start through acknowledge, real engine)
        run: python3 tools/test_sbe_golden_scenario.py
      - name: Handover fixtures (sbe handover, identity forgeries refused)
        run: python3 tools/test_sbe_handover.py
      - name: Import hygiene fixtures (the six sys.path mounts collapsed into one)
        run: python3 tools/test_sbe_import_hygiene.py
      - name: Instruction surface fixtures (changed authority files outside declared scope)
        run: python3 tools/test_sbe_instruction_surface.py
      - name: Interoperability fixtures (namespacing, no foreign writes, coexistence)
        run: python3 tools/test_sbe_interop.py
      - name: Install script fixtures (dry-run, missing prerequisites)
        run: python3 tools/test_sbe_install.py
      - name: Map fixtures (sbe map, a deterministic status map, never a filled template)
        run: python3 tools/test_sbe_map.py
      - name: Plan fixtures (sbe plan)
        run: python3 tools/test_sbe_plan.py
      # This is the canned/offline suite: every GitHub API call is routed
      # through a fake fetch, so it needs no network and no token, and it
      # runs on every PR. tools/test_sbe_prverify_live.py is a separate,
      # deliberately unwired script: it needs BOTH SBE_LIVE_GH_REPO and
      # SBE_LIVE_GH_PR plus a token discoverable the way `sbe pr verify`
      # itself discovers one, none of which this workflow provides, and
      # without them it already prints one NO-DATA line and exits 0 (its
      # own docstring). Wiring it here would either skip silently on every
      # normal run or require CI secrets this repository does not carry, so
      # it stays a manual, opt-in script instead.
      - name: PR verify fixtures (sbe pr verify, canned GitHub API, offline)
        run: python3 tools/test_sbe_prverify.py
      - name: Release invariant fixtures (distributable bytes cannot move without VERSION)
        run: python3 tools/test_sbe_release_invariant.py
      - name: Review record fixtures (normalized findings, commit binding, staleness)
        run: python3 tools/test_sbe_review_record.py
      - name: Review route fixtures (deterministic reviewer selection)
        run: python3 tools/test_sbe_review_route.py
      - name: Review skill fixtures (the skill consumes the route)
        run: python3 tools/test_sbe_review_skill_fixtures.py
      - name: Sandbox fixtures (doc-truth for docs/guides/00-sandbox.md)
        run: python3 tools/test_sbe_sandbox.py
      - name: Status fixtures (sbe status)
        run: python3 tools/test_sbe_status.py
      - name: Team status fixtures (sbe status --team)
        run: python3 tools/test_sbe_status_team.py
      - name: Task fixtures (sbe task)
        run: python3 tools/test_sbe_tasks.py
      - name: Team workflow fixtures (eight execution laws over one fixture)
        run: python3 tools/test_sbe_team_workflow.py
      - name: Version bump fixtures (one command moves every declaration site)
        run: python3 tools/test_sbe_version_bump.py
      - name: Work fixtures (sbe work)
        run: python3 tools/test_sbe_work.py
      - name: Work brief fixtures (sbe work brief)
        run: python3 tools/test_sbe_work_brief.py
      # The kill criterion this wave was cut against, verbatim: an install
      # that needs a manual global settings edit. This proves a plain
      # `git archive HEAD` extracts on its own into an empty directory and
      # verifies clean there (scripts/verify-install.sh, bin/sbe doctor),
      # nothing written outside that one directory.
      - name: Install-from-artifact test (a fresh `git archive` install verifies clean)
        run: sh scripts/test-install-artifact.sh
      # scripts/test-install-artifact.sh above already proves the checksums
      # manifest cannot drift from the bytes it describes; it says nothing
      # about whether VERSION moved when those bytes did, which is the
      # narrower gap this step closes. fetch-depth: 0 on the checkout step
      # above fetches full history for every branch and tag, including the
      # origin/main remote-tracking ref this checker diffs against by
      # default, so the base ref resolves here; a checkout that switched to
      # a shallow clone would make this NO-DATA rather than crash, which is
      # this tool's own stated behavior for a ref it cannot resolve, never a
      # false pass.
      - name: Release invariant (distributable bytes cannot move without VERSION moving)
        run: python3 tools/sbe_release_invariant.py --strict
      # Exercises the real upgrade/rollback path once this repository has cut
      # its first tag; until then it prints NO-DATA and exits 0 without
      # claiming an upgrade was tested, which is the honest result here, not
      # a skip and not a pass (docs/KNOWN-LIMITS.md, "The release candidate
      # ships packaging, not a release").
      - name: Upgrade and rollback test (NO-DATA until a previous tag exists, never a false pass)
        run: sh scripts/test-upgrade-rollback.sh

  # BrotherSBE gates (windows leg), added 2026-08-05, founder-approved, lane
  # T7: the same battery the gates job above runs on Linux and macOS,
  # started from that job's full step list, on windows-latest, pinned to the
  # 3.9 floor only (the promise on the front page; not the informational
  # 3.x leg above, so this addition costs one job run per push, not two).
  # continue-on-error is never set here: a red step blocks a merge exactly
  # like the matrix above does.
  #
  # Two steps are skipped, each named where it is skipped: the two `sh`
  # install and upgrade scripts (docs/KNOWN-LIMITS.md, "Windows is
  # untested") invoke the `sh` interpreter directly, which this leg cannot
  # supply cleanly. Everything else, including the suites that assert POSIX
  # file permission bits (chmod, stat mode checks), now runs for real on
  # Windows for the first time and is free to fail honestly if a POSIX
  # assumption inside one of them does not hold there; that is the point of
  # this leg, not a promise that every suite already passes on Windows.
  gates-windows:
    runs-on: windows-latest
    env:
      # Round 2 of this leg's first day proved the need: two Unicode homoglyph
      # evals (a-lisu-spelling-of-tbd-is-not-a-snapshot-pin and
      # a-small-capital-placeholder-is-not-a-pin) read their fixtures through
      # Windows' legacy locale codec and the gate saw mangled bytes instead of
      # the homoglyph it exists to catch. Linux and macOS already run UTF-8
      # locales; declaring UTF-8 mode here equalizes the environment without
      # touching what any gate tests.
      PYTHONUTF8: "1"
    defaults:
      run:
        # Git for Windows ships bash on windows-latest by default (verified
        # against the runner image's own software manifest on 2026-08-05),
        # so this names no new dependency; it is what makes the multi-line
        # steps below (set -o pipefail, grep, while read, || true) behave
        # the same here as they do on Linux and macOS above, where bash is
        # already the implicit default shell for an unspecified step.
        shell: bash
    steps:
      - name: Line endings stay bytes (autocrlf off before any file exists)
        # The tracked manifest hashes exact bytes and .gitattributes rides
        # INSIDE the checkout, so files extracted before it lands in the
        # working tree could still be converted by the runner's default
        # autocrlf: rounds 1 to 3 of this leg watched the same four
        # early-alphabet files (.brothersbe/config.json, the two
        # .claude-plugin manifests, .gitattributes itself) hash stale on
        # first read and identical on re-read (run 31042529271). Turning
        # conversion off before checkout removes the ordering race the
        # in-tree attributes file cannot close by itself.
        run: git config --global core.autocrlf false
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
        with:
          fetch-depth: 0   # the approval gate reads commit trailers and signatures
      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5
        with:
          python-version: '3.9'
      # Windows reality, confirmed against actions/setup-python's own
      # find-python.ts on 2026-08-05: some images place only python.exe on
      # PATH; the current windows-latest image resolves python3 already (its
      # first real run proved the unconditional copy fails as same-file), so
      # this guard is a no-op there and a bridge only where needed. Every step below still calls python3
      # unmodified, identical to the gates job above, so this one step
      # bridges the gap instead of rewriting each of them.
      - name: Ensure python3 resolves (guard for images shipping only python.exe)
        run: |
          if ! command -v python3 >/dev/null 2>&1; then
            py="$(command -v python)"
            cp "$py" "$(dirname "$py")/python3.exe"
          fi
      # The approval gate accepts a signature only if THIS host verified it. A
      # runner with no public keys imported reports "cannot verify" for every
      # signed commit, which is NO-DATA and not an approval. To use the signed
      # trailer path in CI, import the approvers' public keys first:
      #   - run: gpg --import <<< "${{ secrets.SBE_APPROVER_PUBKEYS }}"
      # Or standardise on the Reviewed-in: <review id> trailer, which needs no
      # keyring at all. Doing neither is legal and honest: approvals then report
      # NO-DATA, instead of a gate that quietly degrades into accepting any
      # signature blob because it could not check one.
      # Scoped to the LIVE dossier root (design/, declared by `sbe init`), not
      # the whole checkout. The first real run of this workflow proved why the
      # wide sweep was wrong twice over: the teaching dossier under
      # docs/for-engineers/examples carries an APPROVAL that is DESIGNED to
      # fail (two documents paste that refusal as the lesson), so scanning it
      # turned pedagogy into a red build, and the same sweep let the examples'
      # receipts print PASS lines as if they were this repository's own
      # claims, which is worse than the red. This repository carries no live
      # dossier today, so all four gates read NO-DATA here, printed in full:
      # NO-DATA is never a pass, and never a manufactured failure either.
      - name: Hard gates (numbers, migration, approval, ran) block on failure
        run: python3 tools/sbe_gate.py --strict design
      # A waiver is not a pass. `.sbe-exempt` lets a template library or a finished
      # project stop blocking every unrelated merge, and the exit code cannot tell
      # you one was used, so this step surfaces every WAIVED line as an annotation
      # and in the job summary. A human sees it, or it is not a control. Add
      # --strict-waivers here if you want an exemption to block outright.
      - name: Design checks (dossier completeness) block on failure
        run: |
          set -o pipefail
          python3 tools/sbe_design.py --strict . | tee design-checks.out
      # The pattern is `^  >> `, the prefix sbe_design.py puts on a waived line, and
      # not the word WAIVED. The banner the tool prints on every run ends "WAIVED
      # is not a pass either", so `grep -q 'WAIVED'` was unconditionally true: every
      # clean run told the reviewer that a .sbe-exempt had waived one or more design
      # checks and that nothing opened a file for them, over a run in which every
      # check opened its files. An assurance signal that always fires carries no
      # information, and this one asserted something false, which trains a reviewer
      # to ignore the single control that makes WAIVED visible in CI at all.
      - name: Surface design waivers (a waiver is not a pass)
        if: always()
        run: |
          if grep -qE '^  >> ' design-checks.out; then
            grep -E '^  >> ' design-checks.out | while read -r line; do
              echo "::warning title=BrotherSBE design waiver::$line"
            done
            {
              echo '### BrotherSBE design waivers'
              echo 'A `.sbe-exempt` waived one or more design checks. Nothing opened a file for them.'
              echo '```'
              grep -E '^  >> |^WAIVERS: ' design-checks.out
              echo '```'
            } >> "$GITHUB_STEP_SUMMARY"
          fi
      # Severity is declared per check and printed on every verdict line: --strict
      # blocks on gate severity (the lints), and --strict-soft is the visible
      # opt-in that makes soft-severity (graded) FAILs block too. This workflow
      # passes both, which is this repository's choice, not a default; drop
      # --strict-soft to let graded checks fail without stopping a merge.
      - name: Silent-failure lints and code-graded checks block on failure
        run: python3 tools/sbe_score.py --strict --strict-soft .
      # The gates above are only worth what their tests are worth. These two ran
      # on nobody's merge path until now, which made them documentation rather
      # than a gate: a fixture no merge runs cannot stop anything.
      - name: Regression evals (every gate against the defect it exists to catch)
        run: python3 evals/run_evals.py
      - name: Replay detail on failure (which excerpt blocks differ, and how)
        if: failure()
        run: |
          python3 --version
          python3 evals/replay_book.py || true
          python3 evals/replay_guide05.py || true
      # Two passes: the fixed sweep, then a seeded random composition of the
      # same hollowing operations (--seed). The seeds are fixed so CI is
      # reproducible; a failing scenario prints its seed in its id. A wider
      # search is one more --seed here, not new test code.
      - name: Honesty meta-test (no check may PASS over evidence it never examined)
        run: |
          python3 evals/test_no_data_class.py
          python3 evals/test_no_data_class.py --quiet --seed 1 --seed 2 --seed 3
      - name: Tool tests (redaction, permissions, identity, autosave, plugin surface, CLI)
        run: python3 tools/test_sbe.py
      # Both suites below existed and ran on nobody's merge path, which is the
      # same "documentation rather than a gate" condition the comment above
      # names. The fence hook is an enforcement boundary and the impact fixtures
      # carry the defect that a declared tier can contradict the diff; neither
      # is worth anything if a merge never runs it.
      - name: Fence hook tests (the write boundary)
        run: python3 tools/test_sbe_fence_hook.py
      - name: Impact fixtures (a declared tier cannot contradict the diff silently)
        run: python3 tools/test_sbe_impact.py
      # The suites below are the same "documentation rather than a gate"
      # condition the comment above names: each one existed on disk and ran
      # on nobody's merge path until this step wired it in. Listed in the
      # order tools/test_sbe*.py sorts, so a new suite dropped into tools/
      # is easy to spot missing from this list.
      - name: Adopt and init fixtures (sbe adopt, sbe init)
        run: python3 tools/test_sbe_adopt.py
      - name: Authority hook fixtures (undeclared edits to authority files refused)
        run: python3 tools/test_sbe_authority_hook.py
      - name: Benchmark fixtures (the comparative harness, and its ground-truth leak guard)
        run: python3 benchmarks/test_sbe_bench.py
      - name: Book estate fixtures (the worked example the book's chapters paste)
        run: python3 tools/test_sbe_book.py
      - name: Bypass fixtures (the ways a person or an agent gets past these controls)
        run: python3 tools/test_sbe_bypass.py
      - name: Converge fixtures (sbe converge)
        run: python3 tools/test_sbe_converge.py
      - name: Decision package fixtures (sbe explain, sbe lineage)
        run: python3 tools/test_sbe_decisions.py
      - name: Evidence fixtures (a receipt cannot be typed by the same process it verifies)
        run: python3 tools/test_sbe_evidence.py
      - name: Golden scenario (the whole chain, start through acknowledge, real engine)
        run: python3 tools/test_sbe_golden_scenario.py
      - name: Handover fixtures (sbe handover, identity forgeries refused)
        run: python3 tools/test_sbe_handover.py
      - name: Instruction surface fixtures (changed authority files outside declared scope)
        run: python3 tools/test_sbe_instruction_surface.py
      - name: Interoperability fixtures (namespacing, no foreign writes, coexistence)
        run: python3 tools/test_sbe_interop.py
      - name: Install script fixtures (dry-run, missing prerequisites)
        run: python3 tools/test_sbe_install.py
      - name: Plan fixtures (sbe plan)
        run: python3 tools/test_sbe_plan.py
      # This is the canned/offline suite: every GitHub API call is routed
      # through a fake fetch, so it needs no network and no token, and it
      # runs on every PR. tools/test_sbe_prverify_live.py is a separate,
      # deliberately unwired script: it needs BOTH SBE_LIVE_GH_REPO and
      # SBE_LIVE_GH_PR plus a token discoverable the way `sbe pr verify`
      # itself discovers one, none of which this workflow provides, and
      # without them it already prints one NO-DATA line and exits 0 (its
      # own docstring). Wiring it here would either skip silently on every
      # normal run or require CI secrets this repository does not carry, so
      # it stays a manual, opt-in script instead.
      - name: PR verify fixtures (sbe pr verify, canned GitHub API, offline)
        run: python3 tools/test_sbe_prverify.py
      - name: Release invariant fixtures (distributable bytes cannot move without VERSION)
        run: python3 tools/test_sbe_release_invariant.py
      - name: Review record fixtures (normalized findings, commit binding, staleness)
        run: python3 tools/test_sbe_review_record.py
      - name: Review route fixtures (deterministic reviewer selection)
        run: python3 tools/test_sbe_review_route.py
      - name: Review skill fixtures (the skill consumes the route)
        run: python3 tools/test_sbe_review_skill_fixtures.py
      - name: Status fixtures (sbe status)
        run: python3 tools/test_sbe_status.py
      - name: Team status fixtures (sbe status --team)
        run: python3 tools/test_sbe_status_team.py
      - name: Task fixtures (sbe task)
        run: python3 tools/test_sbe_tasks.py
      - name: Team workflow fixtures (eight execution laws over one fixture)
        run: python3 tools/test_sbe_team_workflow.py
      - name: Version bump fixtures (one command moves every declaration site)
        run: python3 tools/test_sbe_version_bump.py
      - name: Work fixtures (sbe work)
        run: python3 tools/test_sbe_work.py
      - name: Work brief fixtures (sbe work brief)
        run: python3 tools/test_sbe_work_brief.py
      # EXCLUDED on windows-latest: this step ran `sh scripts/test-install-artifact.sh`, a POSIX `sh` script never exercised on Windows (docs/KNOWN-LIMITS.md, "Windows CI runs, with named gaps").
      # On Linux and macOS, scripts/test-install-artifact.sh above already proves
      # the checksums manifest cannot drift from the bytes it describes; that
      # script is excluded on this Windows leg (see the exclusion comment just
      # above), so this step's own narrower claim, that VERSION moves when
      # distributable bytes do, stands on its own here. fetch-depth: 0 on the
      # checkout step above fetches full history for every branch and tag,
      # including the origin/main remote-tracking ref this checker diffs
      # against by default, so the base ref resolves here; a checkout that
      # switched to a shallow clone would make this NO-DATA rather than
      # crash, which is this tool's own stated behavior for a ref it cannot
      # resolve, never a false pass.
      - name: Release invariant (distributable bytes cannot move without VERSION moving)
        run: python3 tools/sbe_release_invariant.py --strict
      # EXCLUDED on windows-latest: this step ran `sh scripts/test-upgrade-rollback.sh`, a POSIX `sh` script never exercised on Windows (docs/KNOWN-LIMITS.md, "Windows CI runs, with named gaps").
```

Why the two settings matter:

- `fetch-depth: 0` gives the approval gate the commit it needs. `gate_approval`
  reads the `Approved-by:` trailer on HEAD and its signature status. Note that
  signature verification is awkward to reproduce in CI, so the keyless path is a
  `Reviewed-in: <platform-review-id>` trailer, which points at a recorded platform
  review instead of binding a key. That path reports NO-DATA rather than PASS,
  because nothing resolves the id and the agent writes the commit message; NO-DATA
  neither blocks nor passes, so it does not impede a team that has chosen it. A
  bare typed name fails by design: a name in a text field is not a control.
- The second step runs `sbe_gate.py`'s companion, `sbe_score.py --strict`, which
  blocks on the silent-failure lints and the code-graded checks. This is not
  optional: the silent-failure lints are the fifth non-waivable gate on the merge
  path, refused rather than waived, same as the four in `sbe_gate.py`. Both tools
  take the root as a trailing `.` argument and examine exactly that directory.

Turn on branch protection for the `gates` job and the four failure classes stop
being things a reviewer has to remember. They become a merge that does not happen
until the receipt is there and consistent.

---

## Where to go next

- `references/laws-hard-gates.md` L7 to L10 are the four hard gates, and `SKILL.md` L11
  is the lints CI runs beside them. `references/laws-overrides-and-waivers.md` holds L15,
  the override rule, and L16, the one that makes `--strict` unavailable to a session.
  `SKILL.md` is the always-on core and its routing table names which file holds which law.
- `evals/run_evals.py` is the proof: one planted defect per class, each caught by its
  gate. Read the fixtures to see the exact shape of every receipt.
- `SECURITY.md` documents the network posture: the tools that run inside a session
  make no network call, with two named exceptions (`sbe pr verify` reads the GitHub
  API when you run it, and `install.sh` clones once at install time). They
  write only to the vault you point `BROTHERSBE_VAULT` at (default
  `~/BrotherSBEVault`), and the autosave snapshots your work to a local git ref
  without ever pushing.
- `RUBRIC.md` is the weekly-review scorecard. Its baselines are the author's,
  measured on one machine; re-measure them on your own estate before you trust a
  threshold.

Clean up the demo when you are done: `rm -rf ~/sbe-demo`.
