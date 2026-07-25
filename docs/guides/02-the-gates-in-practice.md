# The four hard gates in practice

This is the deepest technical doc in the set. It shows how each of the four hard
gates in `tools/sbe_gate.py` executes: the exact JSON receipt it reads, a worked
PASS and a worked FAIL with the real output line, what stops a receipt from being
faked, the infrastructure the gate genuinely needs, and how to override it without
lying to yourself.

Everything below was run against the shipped `tools/sbe_gate.py`. The output lines
are copied from real runs, not paraphrased.

## Why four, and why mechanical

Four failure classes share one property: a wrong result looks exactly like a right
one, and the time it takes to notice runs from minutes to never. A total that
overstates its own components. A migration with a reverse nobody ran. A partner
payout signed off by a name typed into a text field. A reconciliation query the
agent reported green without executing. For these, "the agent said it checked" is
worth nothing. The gate is worth something because it reads a receipt and re-derives
the claim.

The spine of BrotherSBE: an agent earns trust in exact proportion to how mechanically
its output can be checked. These four gates are that rule with teeth.

### Two modes, one truth

```
python3 tools/sbe_gate.py <class> <dir>            # advisory: prints the verdict, exits 0
python3 tools/sbe_gate.py <class> <dir> --strict   # enforcing: exits nonzero on any FAIL
```

`<class>` is one of `numbers`, `migration`, `approval`, `ran`. Omit it to run all
four. `<dir>` defaults to the current git worktree; the gate resolves it to the git
toplevel and walks the tree for receipt files, skipping `.git`. Advisory mode tells
a session. `--strict` on the CI path stops a merge. The checks are identical; only
the exit code differs.

Every gate returns one of three verdicts. PASS means the receipt is present and
internally consistent. FAIL means a receipt is present but a check inside it did not
hold. NO-DATA means no receipt was found, which is never a pass: absent evidence is
reported as absent, and in `--strict` a FAIL blocks while a NO-DATA does not (a
change that presents no decision figure legitimately has no numbers receipt).

Output that has not cleared its gate carries the label UNVERIFIED next to the item
itself, not in a footnote.

---

## Gate 1: numbers

Every figure that could reach a decision ships with a `numbers-manifest.json`. The
gate reads `sbe_gate.py numbers` and checks each figure for four things: a pinned
snapshot id, an independently scripted second derivation, that the second derivation
actually re-ran, and zero drift between the two derivations.

### The receipt shape (from `gate_numbers`)

```json
{
  "figures": [
    {
      "label": "gmv_q3",
      "snapshot_id": "snap_2026_07_24",
      "query": "SELECT SUM(amount) FROM orders WHERE ts < '2026-07-01'",
      "second_derivation": "SELECT SUM(qty*unit_price) FROM order_lines WHERE order_ts < '2026-07-01'",
      "rerun": {"ran": true, "primary": 4185320, "secondary": 4185320}
    }
  ]
}
```

The fields the gate actually reads: `figures[]`, and per figure `label`,
`snapshot_id`, `query`, `second_derivation`, and `rerun` with `rerun.ran`,
`rerun.primary`, `rerun.secondary`. Nothing else in the object is consulted; a field
the gate does not read is decoration.

### Worked PASS

The figure above (`gmv_q3`) is pinned to `snap_2026_07_24`, its second derivation
sums a different table by a different path, and both derivations re-ran to the same
number.

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  numbers   PASS     1 figure(s) each with a pinned, independently re-derived, zero-drift check
```

### Worked FAIL

This is the exact failure class the gate was built for: a filed model that overstated
a five year total against its own year-by-year components. The primary query and the
second derivation disagree.

```json
{
  "figures": [
    {
      "label": "five_year_total",
      "snapshot_id": "snap_2026_07_24",
      "query": "SELECT SUM(y) FROM plan",
      "second_derivation": "SELECT y1+y2+y3+y4+y5 FROM plan_wide",
      "rerun": {"ran": true, "primary": 1938, "secondary": 432}
    }
  ]
}
```

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  numbers   FAIL     five_year_total: DRIFT primary=1938 secondary=432 (zero drift required)
```

The gate names the label and prints both numbers. A human reading that line knows in
one glance which figure is wrong and by how much.

### What makes the receipt hard to fake

Presence is necessary but not sufficient. A pasted receipt can be stale, truncated,
or invented, so the gate checks internal consistency:

- **Independent second derivation.** `gate_numbers` compares `query.strip()` against
  `second_derivation.strip()`. If they are textually identical, the figure FAILs with
  "second derivation is textually identical to the first (not independent)." Copying
  the first query into the second field does not clear the gate; a genuinely different
  path (a different table, a different aggregation) is the only thing that does.
- **Pinned snapshot.** A figure without `snapshot_id` FAILs with "no snapshot_id (a
  live warehouse drifts; pin the read)." The reason is in the message: two reads of a
  live warehouse taken seconds apart can differ for reasons that have nothing to do
  with the code, so a pinned snapshot is the only way zero drift proves agreement
  rather than luck.
- **Actually re-ran.** `rerun.ran` must be true, or the figure FAILs with "second
  derivation not marked as re-run." A second query that was written but never executed
  is a plan, not a check.
- **Zero drift.** When both `rerun.primary` and `rerun.secondary` are present and
  differ, the figure FAILs with the DRIFT line above.

### The honest limit

A live warehouse drifts, and the gate depends on that being handled, not hidden. If
you point the two derivations at the live warehouse and rows land between the two
reads, the numbers disagree and the gate FAILs a figure that is actually fine: a false
positive. The fix is not to loosen the gate; it is to record a `snapshot_id` and run
both derivations against that pinned snapshot. The gate makes the pin mandatory
precisely so this false positive cannot be waved away. The infrastructure cost is
real: you need a way to pin a snapshot (a time-travel read, a materialized copy, a
`AS OF` clause on a warehouse that supports it). That cost is priced here, not hidden.

---

## Gate 2: migration

A forward and a reverse migration, both run against a restored copy, the reverse
carrying a resolvable rehearsal run id, with row counts before and after the reverse
that match. The gate reads `migration-receipt.json`.

### The receipt shape (from `gate_migration`)

```json
{
  "forward": {"ran_against_restore": true},
  "reverse": {"ran_against_restore": true, "rehearsal_run_id": "job_8842"},
  "row_counts": {"before": 204118, "after_reverse": 204118}
}
```

The fields the gate reads: `forward.ran_against_restore`,
`reverse.ran_against_restore`, `reverse.rehearsal_run_id`, and `row_counts.before`
with `row_counts.after_reverse`.

### Worked PASS

Both legs ran against a restore, the reverse carries `job_8842`, and the row count
came back to where it started.

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  migration PASS     forward and reverse both ran against a restore with matching row counts and a resolvable rehearsal id
```

### Worked FAIL

Here the reverse claims it ran against a restore but carries no run id. Free text is
not a receipt.

```json
{
  "forward": {"ran_against_restore": true},
  "reverse": {"ran_against_restore": true},
  "row_counts": {"before": 204118, "after_reverse": 204118}
}
```

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  migration FAIL     reverse: no resolvable rehearsal_run_id (free text is not a receipt)
```

Two other FAIL paths exist and are worth knowing: a leg with
`ran_against_restore: false` FAILs with "forward: not run against a restored copy" or
the reverse equivalent, and a reverse that dropped rows FAILs with "reverse did not
restore row count: before=204118 after=61" when `before` and `after_reverse` differ.

### What makes the receipt hard to fake

- **Resolvable rehearsal id.** `reverse.rehearsal_run_id` must be present. The word
  resolvable is load-bearing: the id is meant to point at a rehearsal run someone can
  look up (a CI job number, a pipeline run id), not a sentence a model typed. The gate
  enforces presence; the review enforces that it resolves.
- **Ran against a restore.** Both legs must set `ran_against_restore: true`. A
  migration tested against an empty scratch schema proves nothing about production; the
  flag records that the rehearsal happened against a restored copy of real data.
- **Row-count identity.** `before` must equal `after_reverse`. A reverse that leaves
  the table with fewer rows than it started with is a lossy reverse, and the gate
  catches it by arithmetic, not by trust.

### The honest limit

CI cannot cheaply stand up a production-shaped restore on every pull request. A full
restore of a large warehouse is minutes to hours and real money. So the receipt records
that a rehearsal ran against a restore; it does not itself perform the restore inside
the gate. That means the restore is a genuine infrastructure prerequisite you provide
out of band: a staging environment loaded from a recent production backup, or a
restore job the migration rehearsal targets. The gate verifies the receipt of that
rehearsal, not the rehearsal itself. This is priced here plainly: no restore
environment, no honest migration receipt. The gate does not pretend the restore is
free, and it does not let you skip it by writing `true` into a field, because the
`rehearsal_run_id` has to point at a run that happened.

---

## Gate 3: approval

A change on a money or partner-facing path carries a named human approval bound to an
identity the agent cannot forge: a signed commit trailer, or a recorded platform review
id. A bare typed name FAILs. The gate reads an `APPROVAL` file and the HEAD commit
trailers.

### What the gate reads (from `gate_approval`)

- An `APPROVAL` file anywhere in the tree, whose presence declares that this change
  touches a money or partner path.
- The HEAD commit body, for an `Approved-by:` trailer and a `Reviewed-in:` trailer.
- The commit signature state via `git log -1 --format=%B%n---%n%G?`, where `%G?`
  returns `G` (good signature), `U` (good, unknown validity), `E` (cannot check), `N`
  (no signature), and similar.

The binding rule: an `Approved-by:` trailer counts only when the signature state is
`G`, `U`, or `E` (a signature exists and was attached to the commit). A `Reviewed-in:`
trailer counts as a platform review id on its own.

### Worked FAIL

A partner billing change with an `APPROVAL` file and an `Approved-by: A. Reviewer`
trailer, but the commit is unsigned. A name in a text field is not a control.

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  approval  FAIL     approval is a typed name with no signature or review id; a name in a text field is not a control (add a signed Approved-by trailer or a Reviewed-in review id)
```

### Worked PASS

Amend the same commit to carry a platform review id instead:

```
Reviewed-in: gh_pr_1421
```

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  approval  PASS     approval bound to platform review gh_pr_1421
```

A signed commit with `Approved-by:` passes the same way, printing "signed commit
carries Approved-by: <name>".

### Worked NO-DATA

A change that touches no money or partner path has no `APPROVAL` file and no
`Approved-by:` trailer. That is correct, and the gate says so without failing:

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  approval  NO-DATA  no APPROVAL file and no Approved-by trailer; if this change touches no money or partner path that is correct
```

### What makes the receipt hard to fake

The whole point of this gate is that the agent cannot mint the approval. A typed name
is exactly what an agent can produce, so a typed name alone FAILs. What clears the gate
is a binding to an identity the agent does not hold: a cryptographic commit signature
(the private key is the human's), or a platform review id that points at a review that
happened in a system the agent cannot post to on the human's behalf. This is the blast
radius rule made concrete: no agent holds sign-off on money or partner paths; it drafts
the change and a human binds their identity to it.

### The honest limit

The gate verifies that a signature or a review id is present and, for signatures, that
the commit is signed. It does not itself confirm the review was substantive, or that
the `Reviewed-in:` id points at a real approval rather than a closed-without-merge
review. That last mile is a human review responsibility. The gate raises the floor from
"a name in a field" to "an identity the agent could not forge"; the ceiling stays with
the reviewer.

---

## Gate 4: ran

No SQL or pipeline change is done until its reconciliation query or test executed and
left a `ran-receipt.json` with a zero exit code and a nonzero duration. A check that
took no time did not run. The gate reads `sbe_gate.py ran`.

### The receipt shape (from `gate_ran`)

```json
{
  "checks": [
    {"name": "row_parity", "exit_code": 0, "duration_ms": 812}
  ]
}
```

The fields the gate reads per check: `name`, `exit_code`, `duration_ms`.

### Worked PASS

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  ran       PASS     1 recorded check(s), each with a zero exit and a nonzero duration
```

### Worked FAIL

The green-on-red case: the agent claimed the reconciliation passed, but the recorded
check exited nonzero.

```json
{
  "checks": [
    {"name": "row_parity", "exit_code": 1, "duration_ms": 400}
  ]
}
```

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)
  ran       FAIL     row_parity: check exited nonzero (1)
```

The other FAIL path is a check with no `exit_code` at all, which FAILs with "row_parity:
no exit code recorded (was it actually run?)", and a check with `duration_ms` of zero or
missing, which FAILs with "zero or missing duration (a check that took no time did not
run)."

### What makes the receipt hard to fake

- **Nonzero duration.** A check that reports `duration_ms: 0` did not run; a real
  reconciliation against real data takes measurable time. The zero-duration FAIL is the
  cheapest tell that a receipt was written by hand rather than emitted by an execution.
- **Recorded exit code.** `exit_code` must be present and zero. A missing exit code
  FAILs, so "I ran it and it was fine" without a captured code does not clear the gate.
- **The exit code is the truth, not the prose.** A nonzero code FAILs regardless of any
  claim the agent made in text. This is the gate that exists to catch a green build the
  agent reported but did not run.

### The honest limit

The gate trusts that the `ran-receipt.json` was written by the harness that ran the
check, not typed afterward. The internal-consistency checks (nonzero duration, real exit
code) make a hand-forged receipt harder, but the strongest form is to have your test
runner or pipeline step emit the receipt itself, so the numbers come from the execution
and not from a keyboard. The gate raises the cost of faking; wiring the receipt to the
runner removes the opportunity.

---

## Overriding a gate correctly

Reality produces exceptions, so overrides exist. They are constrained so an override can
never quietly become the norm:

- **Named and logged.** An override is named (who, why) and written to the overrides
  ledger, then surfaced at the weekly review. It is never silent.
- **Never on the `--strict` CI path.** Impatience cannot override a strict gate. The
  only way a `--strict` gate stops failing is a human editing the gate config in a
  reviewed change. This is deliberate: the session can note an exception, but the merge
  block belongs to CI, and CI answers only to a reviewed edit.
- **A session instruction never waives a hard gate.** If a prompt says skip the numbers
  gate, the gate still runs and the output still carries UNVERIFIED with the reason. A
  rule stated in a prompt is not a control; a control is a check that runs.

Concretely, an advisory FAIL in a session is a signal you can act on with an override
noted in the ledger. A `--strict` FAIL in CI is a wall: you fix the receipt, or a human
changes the gate in a PR someone reviews. `--strict` on a FAIL exits nonzero and prints
the block reason:

```
STRICT: 1 hard gate(s) failed; exiting nonzero to block the merge.
```

---

## The silent-failure lints

Alongside the four hard gates, `tools/sbe_score.py` runs `silent-failure-lints`, which
scans source for the code patterns that hide an error so a wrong result looks like a right
one. By ratified decision these are gate severity: in `--strict` a lint hit exits nonzero,
the same as a hard-gate FAIL, which is why L7 to L11 rather than L7 to L10 are the laws a
session may never waive.

The check is opt-in on a path: it scans the directory you pass, or `SBE_LINT_ROOT`. Pass
neither and it reports NO-DATA naming why, because a run that opened no file has found
nothing and cannot be called clean. A positional argument that is not a directory is a
FAIL, so a mistyped path cannot read as a clean scan.

### The five patterns

From `LINT_PATTERNS` in `sbe_score.py`:

1. **Bare `except:`** catches everything, including the errors you needed to see. Flagged
   as "bare except (catches everything, hides the real error)".
2. **`except <Type>:` then `pass`** swallows the error with nothing logged. Flagged as
   "except-then-pass (swallows the error)".
3. **Conflict-skipping upsert** (an `.execute(...)` with `ON CONFLICT ... DO NOTHING`)
   drops rows with no count of what it skipped. Flagged as "conflict-skipping upsert
   without a logged skip count".
4. **Discarded subprocess result without `check=True`.** A statement-leading
   `subprocess.run/call/Popen(...)` whose exit code is neither checked nor assigned
   swallows a failure. Flagged as "discarded subprocess result without check=True (exit
   code is swallowed)". An assigned result (`out = subprocess.run(...)`) can be inspected,
   so it is not flagged.
5. **Swift `try!`** discards the error and traps at runtime. Flagged as "force-try (Swift
   try! discards the error)".

The lint is opt-in and scoped: it scans a directory you pass as an argument or set via
`SBE_LINT_ROOT`, and never an unrelated tree. It walks source files (`.py`, `.sql`,
`.swift`, `.rb`, `.js`, `.ts`, `.go`), skipping `.git`, `node_modules`, `__pycache__`,
`.venv`, and `venv`. Each hit names its file and line.

### The visible allow-marker

A swallow is sometimes correct: a hook must never crash a session, so a boundary handler
that turns a failure into absent data rather than a false pass is legitimate. The lint
allows it only when a human named why, on the same line, in a form that shows up in the
diff:

```python
except Exception:  # sbe: allow-silent a hook must never crash a session; the miss is visible as absent telemetry
    pass
```

A line carrying `# sbe: allow-silent <reason>` is exempt. This is the override philosophy
applied to lints: the exemption is visible and auditable, not a config flag someone flips
once and forgets. The reason travels with the code.

### How BrotherSBE passes its own lints

The tool holds itself to the rule it enforces. Running the lint over the shipped tools:

```
$ python3 tools/sbe_score.py tools/     # one of eleven check lines; the rest are omitted here
silent-failure-lints      PASS     6 file(s) scanned under tools/, clean
```

Two mechanisms make that honest rather than lucky:

- **The linter skips its own file.** `sbe_score.py` defines the patterns as string
  literals, so a naive scan would match itself. It excludes `os.path.basename(__file__)`
  for exactly that reason, and the exclusion is documented in the function.
- **Every genuine swallow carries a marker.** The boundary handlers that must not crash a
  session are exempted in the open. `sbe_gate.py:170` marks the receipt-read handler; five
  handlers in `sbe_telemetry.py` (lines 283, 719, 772, 917, 945) mark the non-blocking hook
  boundaries, each with a reason ending in the same guarantee: the miss surfaces as absent
  data, never as a false pass. The test harness (`test_sbe.py`) marks its two fire-and-forget
  hook invocations, noting the snapshot ref it creates is asserted immediately below.

Nothing is hidden by turning off the check. The lint runs against the tool's own source,
finds the swallows, and passes only because each one is named. That is the same standard
the four gates hold your work to, applied to the gates themselves.

---

## One page to keep

| Gate | Receipt file | Key fields the gate reads | The fake it stops |
| --- | --- | --- | --- |
| numbers | `numbers-manifest.json` | `snapshot_id`, `query` vs `second_derivation`, `rerun.ran`, `rerun.primary`/`secondary` | a total that disagrees with its own components |
| migration | `migration-receipt.json` | `forward`/`reverse.ran_against_restore`, `reverse.rehearsal_run_id`, `row_counts.before`/`after_reverse` | a reverse nobody rehearsed against a restore |
| approval | `APPROVAL` + commit trailers | `Approved-by:` with a signature (`%G?` in G/U/E), or `Reviewed-in:` | a typed name standing in for a control |
| ran | `ran-receipt.json` | `checks[].exit_code`, `checks[].duration_ms` | a green the agent reported but did not run |

Advisory in a session, `--strict` in CI. NO-DATA is never a pass. Output that has not
cleared its gate is labeled UNVERIFIED next to the item. The gates are regression-tested:
`python3 evals/run_evals.py` runs every case in the suite, each a real failure class as a
fixture, and a release is blocked if any of them stops being caught.

Maintained by Khalil Maaouni, Founder. BrotherSBE is the specialist sibling of
BrotherModeUp (github.com/khalilmaaouni/BrotherModeUp).
