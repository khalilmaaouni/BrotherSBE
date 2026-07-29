# The `sbe` command line

One entry point instead of nine script paths.

```
bin/sbe doctor
```

No install step. `bin/sbe` puts `src/` on the path itself and calls the package, because this
project's promise is that a clone works with nothing else installed, and requiring
`pip install` to reach the command line would quietly retract that for anyone on a locked-down
machine or in a CI image with no package index. Put `bin/` on your PATH or call it by path.

## What it is, and what it is not

It is a **facade**. Every built subcommand delegates to the tool in `tools/` that already
carries the behavior, the evals and the unit tests, and it hands back that tool's exit code.
Nothing was reimplemented to build this surface, and nothing in `tools/` changed. The old
invocations still work exactly as documented everywhere else in this repository, and they are
not deprecated: deprecating a command that 509 evals and a dozen pasted doc examples point at
is a separate change with its own risk, and it is not being smuggled into a packaging wave.

## Commands

| Command | Does |
|---|---|
| `doctor` | checks this installation and the environment it will run in |
| `verify` | design completeness check, then the hard gates, then the scored surface |
| `review` | the scored surface including soft findings, plus the hard gates |
| `design` | delegates to `tools/sbe_design.py` |
| `gate` | delegates to `tools/sbe_gate.py` (a gate name, or a directory for all of them) |
| `score` | delegates to `tools/sbe_score.py` |
| `intake` | delegates to `tools/sbe_intake.py` |
| `decide` | delegates to `tools/sbe_decide.py` |
| `fences` | prints the live fences the write hook would enforce |
| `impact` | reads the git diff and reconciles it with the declared intake tier |
| `inspect-change` | alias of `impact`, the name the finalization brief uses |
| `evidence` | generate a receipt by running the command, verify it, or show its trust level |
| `version` | the version and the evidence schema version |

Four more are **present and refuse**: `plan`, `policy`, `exceptions` and `adopt`.
Each names what is missing and which wave builds it, and exits 3.
They are listed rather than hidden so nobody has to guess whether they exist, and they refuse
rather than printing an empty result, because a command that succeeds at nothing is the exact
failure this project exists to stop.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | the command ran and no control FAILED |
| 1 | a control FAILED, or the underlying tool exited nonzero |
| 2 | usage error: unknown command, missing argument, bad path |
| 3 | the command exists and is not built yet |

Read 0 precisely. It means nothing failed. It does **not** mean something passed: a run where
every check reported NO-DATA also exits 0, because nothing failed and nothing was examined
either. `verify` and `review` print a closing line saying so, since an exit code cannot.

## Machine-readable output

`doctor --json` emits the tool version and the evidence schema version alongside its checks,
so a consumer can tell which contract it is reading:

```json
{
  "tool": "sbe",
  "toolVersion": "1.0.0-rc.1",
  "schemaVersion": "1.0",
  "command": "doctor",
  "result": "PASS",
  "checks": [{"name": "python", "result": "PASS", "detail": "3.9.6 (floor is 3.9)"}]
}
```

JSON output on the other commands arrives with the evidence work, not before: emitting a JSON
envelope around a verdict whose provenance is not yet bound to a commit would dress an
advisory result as a machine-readable authoritative one.

## `sbe impact`, and the one rule that makes it safe

```bash
bin/sbe impact . --base main --intake design/my-change/00-intake.json
```

It converts detector hits into the same five intake answers a person gives, and hands them to
the intake's own `compute_tier`. One rule, one table, two inputs, so a tier derived from code
and a tier declared by a human cannot drift apart.

- It may **raise** a declared tier. It may **never lower** one.
- Disagreements are resolved by a **disposition**, not by an argument: a record naming the
  detector, the decision, the reason, who decided, and the head commit it was decided against.
  A disposition written against a different commit resolves nothing, and a disposition with no
  reason is an off switch rather than a decision.
- The proposed tier is a **floor**. `consumers` cannot be read from a diff and is assumed at
  its lowest value; every file no detector covers is listed under `unmeasured` by name.
- `--strict` makes NO-DATA block too, which is what protected CI wants and what a local run
  usually does not.

Verdicts: `PASS` (nothing in the diff contradicts the declared tier), `REVIEW-REQUIRED` (the
diff shows more than was declared, with no current disposition), `FAIL` (the intake is
malformed or unreadable), `NO-DATA` (no diff, or no intake to compare against).

Limits, in full, beside the behavior: `docs/KNOWN-LIMITS.md`. Maturity: **INTERNAL-EVAL**, run
on this repository's fixtures and its own diff, and on no other estate.

## Python floor

3.9, which is the system Python on the machine that maintains this, so it is the floor that is
actually exercised rather than the one that sounds modern. `doctor` checks it and FAILs below
it.

## `sbe evidence`, and the rule that makes a receipt mean something

```bash
bin/sbe evidence run --out evidence/tests.json -- pytest -q
bin/sbe evidence verify evidence/tests.json
bin/sbe evidence show evidence/tests.json
```

The invariant, in one sentence: **a receipt only counts as evidence for the commit it was
generated against, by a wrapper that ran the command itself.**

Before this, every receipt the gates read could be typed by hand by the same agent whose work
it verified. A fabricated duration, exit code, row count or rerun id satisfied the schema, so a
gate could PASS on a run nobody's command ever performed, and nothing bound a receipt to a
commit either, so one written against older code still passed after that code changed.

`run` **executes the command**. There is no flag that accepts a duration, an exit code or an
output digest; those come from the run or the receipt does not exist. It records repository
identity, base and head commit, the exact argv, start and end in ISO 8601 UTC, duration, exit
code, python and `sbe` versions, the platform, whether the tree was dirty, and the files the
receipt covers with their content digests. Its own exit code is the command's, so a failing
command cannot be laundered into a passing evidence step by the fact that a receipt got
written about it.

`--covers <path>` is repeatable and names the files this run is evidence for. Without it, the
files changed between base and head are used. `verify` re-hashes those files, which is how it
tells you the code moved after the evidence was made.

`--timeout SECONDS` bounds the command. Past it, the child is killed and no receipt is written:
no exit code was ever observed, so there is nothing honest to seal, and `sbe evidence run` exits
non-zero with the timeout named on stderr instead. **There is no default.** A silent timeout
would kill a legitimate long-running test suite and hand back nothing to show for it, which is
the exact false-positive pattern this project's own kill criteria warn against, so a run with no
`--timeout` can hang exactly as far as the command itself hangs. Pass it explicitly when the
command is untrusted or has hung before.

`verify` refuses a receipt path it cannot safely open **before** it opens it: a FIFO, a socket, a
device, or a file with no read permission is named and refused in bounded time, in both text and
`--json` mode, rather than read directly, which used to block the command forever on a FIFO with
no verdict printed at all.

**stdout and stderr are recorded as SHA256 digests and byte counts, never as text.** A receipt
gets committed, pasted into a pull request and handed to whoever asks for evidence, and a
command that prints a token would otherwise persist it in the one artifact everybody is
encouraged to share.

`verify` verdicts:

| Verdict | When |
|---|---|
| `PASS` | the seal matches, the head commit is current, every covered file still holds the bytes recorded, and the tree was clean at generation time |
| `FAIL` | the receipt path could not be safely opened (a FIFO, socket, device or unreadable file), the receipt does not parse, its schema version is unknown, a required field records nothing, the seal does not match, the head commit has moved, or a covered file changed or vanished |
| `NO-DATA` | the receipt is sound but was generated on a dirty tree, or covers no file at all. Advisory is NO-DATA here, never a pass |

`--strict` makes NO-DATA block too. Every verdict line names what it inspected, because a
verdict that does not say what it read is not trustworthy output.

`show` prints the receipt and names its **trust level** every time: `PROTECTED-CI` when
`SBE_CI_RUN_ID` was set by the environment AND the tree was clean, `LOCAL-ADVISORY` otherwise.
A CI job over uncommitted edits is a local run wearing a badge, and it is labelled as one.

The `runId` seal is **tamper evidence, not a signature**: it catches a plausible receipt nobody
produced, and it does not stop somebody who read `src/brothersbe/evidence.py`. That is why a
local receipt is never more than advisory. Limits in full: `docs/KNOWN-LIMITS.md`. Maturity:
**INTERNAL-EVAL**.

Four commands remain **present and refuse**: `plan`, `policy`, `exceptions` and `adopt`.
