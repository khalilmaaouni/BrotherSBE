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
| `version` | the version and the evidence schema version |

Six more are **present and refuse**: `inspect-change`, `plan`, `evidence`, `policy`,
`exceptions` and `adopt`. Each names what is missing and which wave builds it, and exits 3.
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

## Python floor

3.9, which is the system Python on the machine that maintains this, so it is the floor that is
actually exercised rather than the one that sounds modern. `doctor` checks it and FAILs below
it.
