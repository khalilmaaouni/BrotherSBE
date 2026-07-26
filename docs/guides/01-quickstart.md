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

## The first ten minutes: prove the gates catch what they claim

Clone the skill wherever your Claude Code skills live. These docs assume the
default install path; set a shell variable so the commands are copy-pasteable.

```bash
SBE="$HOME/.claude/skills/brothersbe"     # wherever you cloned BrotherSBE
python3 "$SBE/tools/sbe_gate.py"          # runs all four gates, advisory, exits 0
```

With no receipts present you get four NO-DATA lines. NO-DATA is never a pass: it
means "no evidence either way", which is the honest verdict for a change that
carries no figure, no migration, no money path, and no SQL. The header states the
contract every time:

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  numbers   NO-DATA  no numbers-manifest found; if this change presents no decision figure that is correct, else add one
```

Before you trust the gates, watch them fail on purpose. The eval suite plants the
exact defects the operating record produced (an overstated multi-year total, an
untested reverse migration, a typed-name approval, a green-on-red check) and
asserts the matching gate catches each one:

```bash
python3 "$SBE/evals/run_evals.py"
```

```
303 evals: 303 passed, 0 regressions.
```

Every case in `evals/run_evals.py` is a real failure class as a fixture. When you change a gate,
this suite is what tells you a gate stopped catching its defect. Run it before you
rely on anything else here.

The four gates and the exact receipt each one reads:

| gate | receipt file (found anywhere in the worktree) | what a PASS proves |
| --- | --- | --- |
| `numbers` | `numbers-manifest.json` | a decision figure is pinned, re-derived by a second query differing beyond formatting and comments, zero drift |
| `migration` | `migration-receipt.json` | forward and reverse both ran against a restore, and recorded row counts match (no row counts recorded is NO-DATA) |
| `approval` | `APPROVAL` file or an `Approved-by:` commit trailer | a money or partner change carries a human approval bound to a verified signature, or a review id the gate does not resolve |
| `ran` | `ran-receipt.json` | a SQL or pipeline check actually executed (nonzero duration, zero exit) |

The gate resolves its root to your git worktree top and walks the tree for these
filenames, skipping version-control, dependency and virtualenv directories by
directory name (matching `.git` as a substring of the path had also hidden
`.github/` from all four gates). The skip list is one shared set,
`sbe_checks.SKIP_DIRS`, plus two structural tells: a directory carrying a
`pyvenv.cfg` is a virtualenv whatever it was named, and `site-packages` is
installed code. Put a receipt at the repo root, or beside the model or
migration it belongs to; both are found.

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
  numbers   PASS     1 figure(s) each pinned to a snapshot, with a second derivation whose text differs beyond case, whitespace and comments, re-run to zero drift
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
sed -i '' 's/"secondary": 17570/"secondary": 17998/' numbers-manifest.json
python3 "$SBE/tools/sbe_gate.py" numbers ~/sbe-demo
```

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  numbers   FAIL     gmv: DRIFT primary=17570 secondary=17998 (zero drift required)
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
  ran       PASS     1 recorded check(s), each with a zero exit and a nonzero duration
```

Now the change is done in the sense the gate means: its check executed and left
proof. Commit the receipt alongside the change so the gate can find it in the
worktree. Had your reconciliation exited nonzero, the gate would report
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
  numbers   FAIL     gmv: DRIFT primary=17570 secondary=17998 (zero drift required)
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
name: BrotherSBE gates
on: [pull_request]
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
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # the approval gate reads commit trailers and signatures
      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      # The approval gate accepts a signature only if THIS host verified it. A
      # runner with no public keys imported reports "cannot verify" for every
      # signed commit, which is NO-DATA and not an approval. To use the signed
      # trailer path in CI, import the approvers' public keys first:
      #   - run: gpg --import <<< "${{ secrets.SBE_APPROVER_PUBKEYS }}"
      # Or standardise on the Reviewed-in: <review id> trailer, which needs no
      # keyring at all. Doing neither is legal and honest: approvals then report
      # NO-DATA, instead of a gate that quietly degrades into accepting any
      # signature blob because it could not check one.
      - name: Hard gates (numbers, migration, approval, ran) block on failure
        run: python3 tools/sbe_gate.py --strict .
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
      - name: Silent-failure lints and code-graded checks block on failure
        run: python3 tools/sbe_score.py --strict .
      # The gates above are only worth what their tests are worth. These two ran
      # on nobody's merge path until now, which made them documentation rather
      # than a gate: a fixture no merge runs cannot stop anything.
      - name: Regression evals (every gate against the defect it exists to catch)
        run: python3 evals/run_evals.py
      - name: Honesty meta-test (no check may PASS over evidence it never examined)
        run: python3 evals/test_no_data_class.py
      - name: Tool tests (redaction, permissions, identity, autosave)
        run: python3 tools/test_sbe.py
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
  take the root as a trailing `.` argument and resolve it to the git worktree top.

Turn on branch protection for the `gates` job and the four failure classes stop
being things a reviewer has to remember. They become a merge that does not happen
until the receipt is there and consistent.

---

## Where to go next

- `SKILL.md` L7 to L10 are the four hard gates, L11 the lints CI runs beside them,
  L15 the override rule and L16 the one that makes `--strict` unavailable to a session.
- `evals/run_evals.py` is the proof: one planted defect per class, each caught by its
  gate. Read the fixtures to see the exact shape of every receipt.
- `SECURITY.md` documents the zero-network posture: the tools make no network call,
  write only to the vault you point `BROTHERSBE_VAULT` at (default
  `~/BrotherSBEVault`), and the autosave snapshots your work to a local git ref
  without ever pushing.
- `RUBRIC.md` is the weekly-review scorecard. Its baselines are the author's,
  measured on one machine; re-measure them on your own estate before you trust a
  threshold.

Clean up the demo when you are done: `rm -rf ~/sbe-demo`.
