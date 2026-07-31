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
| `task` | the write-scope registry: open, list, fence, check, and close with the diff-against-declaration postcondition |
| `adopt` | inspect a repository for installation readiness, dry run by default |
| `status` | blocker-first summary of where a change stands, read from recorded state; `--team` reads every change under `design/` into one ten-severity view with a `basis` honesty field per finding |
| `init` | install BrotherSBE's local footprint into a repository, dry run by default |
| `version` | the version and the evidence schema version |
| `plan` | derive `08-plan.json` from a dossier mechanically and validate it; an empty plan never exits 0 (delegates to `tools/sbe_plan.py`) |
| `work` | isolated lifecycle for one plan task: `start` (branch, worktree, fenced registry record), `check`, `finish` (postcondition AND a head-bound receipt, never an agent statement), `remove` |
| `pr` | `pr verify <number> --repo owner/name`: live GitHub approval evidence bound to the head sha; no credentials is NO-DATA with a remedy, never PASS |
| `converge` | does base..head still match the approved dossier: scope, contracts, data, architecture, verification; no force flag exists |
| `explain` | print the decision package for a decision id, or for a gate or check name; with no recorded run it regenerates one from the shipped registry and marks the verdict NO-DATA, and it never overwrites a package bound to another commit |
| `lineage` | walk the chain for one artifact oldest to newest: binding, receipts, decisions, notes and commits, an evidence pointer on every hop; an absent store is a named NO-DATA hop, never a shorter chain |

Two more are **present and refuse**: `policy` and `exceptions`.
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

Help means help, on every subcommand: `-h`/`--help` prints the owning surface's usage and
exits 0 before anything is read, scanned or written. For the passthrough commands (design,
gate, score, intake, decide, fences, plan, evidence, task, work, pr) the whole argv,
including `-h`, goes to the tool or module that owns the parsing, so the usage you see is
that surface's own; for everything else the CLI answers directly. A flag a surface does not
know is refused with usage and exit 2, never silently ignored: a typo must not run as if
nothing were wrong. The one deliberate exception is `tools/sbe_fence_hook.py`'s bare hook
invocation, which stays fail-open by law; its explicit `-h` still exits 0, with usage on
stderr because that tool's stdout is the hook decision channel.

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

## `sbe doctor`, and what WARNING means

Every check returns one of four results, never folded together: `PASS`, `FAIL`, `NO-DATA` (an
environment question nobody could answer, never counted as a pass), and `WARNING` (something
worth a person's attention that is not, by itself, grounds to block a run). Only `FAIL` moves
the exit code; a `WARNING` is doctor observing, not doctor failing.

The `identity` check reads this repository's `git config user.email` and `user.name` and flags
a fixture identity, an `@example.com` email or the literal name `ci`, as a `WARNING`, quoting
the value it found. That shape of identity authoring real commits is a leak that goes
unnoticed until someone reads the log by hand: a CI or scratch git config left active in a real
checkout is exactly how it happens. `doctor` surfaces it rather than passing silently over it,
and rather than hard-failing an otherwise-healthy environment over a question this command can
only observe, not adjudicate.

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

`run` **executes the command**, over the real, unredacted argv it was given. There is no flag
that accepts a duration, an exit code or an output digest; those come from the run or the
receipt does not exist. It records repository identity, base and head commit, argv, start and
end in ISO 8601 UTC, duration, exit code, python and `sbe` versions, the platform, whether the
tree was dirty, and the files the receipt covers with their content digests. Its own exit code
is the command's, so a failing command cannot be laundered into a passing evidence step by the
fact that a receipt got written about it.

**The recorded argv is redacted, not raw.** Before the receipt is written, every argv token is
checked against the same `SECRET_PATTERNS` `tools/sbe_telemetry.py` already uses to redact an
operator's own messages (imported, not a second list). A match becomes a named marker,
`[REDACTED:<shape>]` (`[REDACTED:api-key]`, `[REDACTED:aws-key-id]`, and so on), and the receipt
records `argvRedactions`, the count, so a reader can tell at a glance whether argv is verbatim
(`0`) or not. The command that RAN is untouched; only the copy written to the receipt is
masked. This narrows the old limit, it does not close it: the pattern list is finite, so a
secret in a shape none of these patterns know still reaches the receipt whole. Full statement:
`docs/KNOWN-LIMITS.md`.

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

## `sbe task`, and the postcondition that survives Bash

```bash
bin/sbe task open --id wave5 --agent alpha --role writer \
  --base $(git rev-parse HEAD) --verify "python3 tools/test_sbe_tasks.py" \
  --owns src/brothersbe/tasks.py --owns tools/test_sbe_tasks.py
bin/sbe task list
bin/sbe task close wave5
```

The write fence is a PreToolUse hook that fails open and cannot govern Bash, because shell
cannot be parsed reliably. `sbe task` is the after-the-fact layer: `open` records who owns
what in `.sbe/tasks.json` (one file, atomic rewrite, no service), and `close` computes what
actually changed, the union of `git diff --name-only <base>...HEAD` and `git status
--porcelain`, inside the task's `--worktree` if one was declared, else the shared tree, and
compares it against the declaration. Uncommitted edits count, and a rename counts both sides.
The shell is never parsed; the diff is simply read.

- Every changed path outside the owned paths is a **violation, listed by name**: verdict FAIL,
  exit nonzero, the task stays open. Changed paths inside ownership print as the evidence of
  scope kept. A declared `--read-only` path that changed is a violation too, flagged as such:
  read-only means read.
- A base commit that no longer resolves is **NO-DATA with the reason, never a pass**.
- `close --force` requires `--who` and `--why`, records that disposition in the record, and
  marks the close **FORCED**, never silently clean.
- `open` refuses (exit 2, reason on stderr, colliding task named) when the id is already open,
  or when any owned path overlaps an owned path of another open task. Overlap is the fence
  hook's own `paths_overlap`, imported rather than re-typed, including its confirmed
  case-folding on case-insensitive filesystems; a test fails if that import is ever replaced
  by a local copy.
- `check` re-runs the overlap scan across all open tasks, so a collision injected into the
  JSON by hand is caught the same way `open` would have caught it.
- `fence` renders the markdown fence view from the registry, one direction only, JSON to
  markdown, printed for a human to paste into a STATE.md style registry. Nothing reads
  markdown fences back into the registry, and the hand-written fence flow keeps working
  untouched.
- Reviewer separation: a `--role reviewer` task cannot open owning any path under the evidence
  store (default `.sbe/evidence`, `--evidence-dir` to override), and a reviewer whose diff
  touches a receipt FAILs at close **even under `--force`**; force may not waive that class.
  This separates roles inside the registry; it cannot stop an actor who never registers.

The registry file itself (`.sbe/tasks.json`) is exempted by exact name from the comparison,
because `open` writes it and counting it would make an ordinary single-writer flow unable to
close clean, which is this control's own kill criterion. `expiry` is informational: nothing
deletes a task on a clock. Concurrent writers of the registry file are out of scope (atomic
rename, last write wins, no lock). Limits in full: `docs/KNOWN-LIMITS.md`. Maturity:
**INTERNAL-EVAL**, exercised on this repository's fixtures and on no other estate.

## `sbe adopt`, and the line it will never cross

```bash
bin/sbe adopt .                 # dry run (the default): every proposal as a unified diff, writes nothing
bin/sbe adopt . --apply         # writes what was proposed; never overwrites an existing file
bin/sbe adopt . --apply --force # overwrites an existing file that differs from the proposal
```

Detects the stack by walking the tree (languages by extension, a migrations directory, dbt
models, API contract files, existing CI workflows), reusing the SAME path patterns `sbe impact`
already carries (`brothersbe.impact.DETECTORS`), so a pattern that means "this is an OpenAPI
document" to one tool means the same thing to the other. From that it proposes a provisional
`.brothersbe/policy.json` (wave 3's own repository policy schema has not shipped; this is a
smaller shape built from what `sbe adopt` can detect, and the file says so) and a
`.github/CODEOWNERS` generated from that same policy, protecting the manifest, the hooks, this
repository's own policy and config, where the evidence schema is declared, product and consumer
CI, and release files. Both proposals are **deterministic**, which is what makes a second
`--apply` a no-op: nothing about them changes between two runs over an unchanged tree.

The adoption report also names three protections that live on GitHub, not on a filesystem:
branch protection, required status checks, and whether review from a code owner is *required*.
**None of the three can ever read `PRESENT` from this command.** They report `UNVERIFIABLE-HERE`
unconditionally, naming what checking them for real would take (a GitHub token with repo scope,
plus admin rights), because this tool holds no credentials and asks for none. A CODEOWNERS file
merely *existing* in the tree is a separate, locally-checkable fact under `localFacts`, never
folded into a claim about GitHub's settings. `tools/test_sbe_adopt.py`'s kill-criterion fixture
pins exactly this: a report that ever claims one of the three PRESENT from a local read is worse
than the refusal this command used to print instead of a result.

Full checklist of what only a human with admin rights can turn on: `docs/ADOPTION.md`. Limits in
full: `docs/KNOWN-LIMITS.md`. Maturity: **INTERNAL-EVAL**.

## `sbe status`, and the rule that keeps it from becoming a second gate runner

```bash
bin/sbe status .                 # blocker-first summary of the current repository
bin/sbe status . --base main     # diff-derived sections read against a stated base
bin/sbe status . --json          # the same six sections, machine-readable
```

One truthful, blocker-first answer to "where does this change stand", read from state
other commands already recorded. It **never runs the suites itself**: nothing in this
command starts a subprocess, and nothing in it computes a new verdict over source code.
It reads `sbe evidence` receipts, the `sbe task` registry, an intake file, a disposition
file, and the diff (the same way `sbe impact` already reads it, by calling that module
rather than re-deriving the git plumbing). If a truthful summary could not be produced
without running the suites or becoming a second `sbe verify`, this command would refuse
rather than run them; it does not need to, because every finding below is something
recorded state already answers.

Six sections, blocker-first, and **every positive or empty line names what it inspected**:

1. **BROKEN CLAIMS**: an evidence receipt under `.sbe/evidence/` that fails `sbe evidence
   verify` (stale, wrong commit, malformed), and a disposition bound to a commit that is
   not the current HEAD.
2. **MERGE BLOCKERS**: an intake tier disagreeing with the diff-derived tier `sbe impact`
   proposes, with no disposition recorded; an intake that cannot be read; a task closed
   `--force`d; and a receipt that verifies as trustworthy but recorded a nonzero exit
   code, meaning a check actually ran and failed and evidence of that failure already
   exists.
3. **ACTIVE CONFLICTS**: open tasks in `.sbe/tasks.json` with overlapping owned paths,
   read by calling `tasks.load_registry`, `tasks.open_tasks` and `tasks.claims_overlap`
   directly, the same functions `sbe task check` itself runs; there is no second copy of
   the overlap rule here.
4. **MISSING EVIDENCE**: for a declared tier above T0, a design/gate/score kind no
   verified receipt's `argv` names, each naming the command that would fill it.
5. **COMPLETED EVIDENCE**: receipts that verify clean with a zero exit code, printed with
   their trust label (`LOCAL-ADVISORY` or `PROTECTED-CI`) every time.
6. **NEXT ACTION**: one line, derived mechanically from the first nonempty section above,
   plus the scope sentence naming exactly which stores this run read.

Where it looks, and this is a stated limit, not a silent one: `<path>/00-intake.json`,
`<path>/disposition.json`, `<path>/.sbe/evidence/` (recursively), `<path>/.sbe/tasks.json`.
These are flat, single-dossier conventions, the same ones `tools/test_sbe_impact.py`'s own
fixtures write to; a dossier nested under `design/<change>/` is not discovered by this
wave, and every section reads NO-DATA rather than guessing at a path it was never told.

A design/gate/score FAIL is recognized only from a receipt whose `sbe evidence verify`
verdict is PASS (sealed, current, every covered file intact): its `argv` is read for the
substring `design`, `gate` or `score` (`verify` counts as all three, `review` counts as
gate and score), and a nonzero recorded `exitCode` on such a receipt is the MERGE BLOCKER.
A receipt whose command names none of the three still counts by its exit code but clears
no MISSING EVIDENCE entry for a kind it does not name.

Exit codes: `0` when BROKEN CLAIMS, MERGE BLOCKERS, ACTIVE CONFLICTS and MISSING EVIDENCE
are all empty, `1` when any of them carries an item, `2` usage. Exit 0 is never printed as
a claim that everything was inspected; the closing line and every empty section's NO-DATA
line say what was not. Limits in full, beside the behavior, live in this section rather
than `docs/KNOWN-LIMITS.md`, which this wave did not touch. Maturity: **INTERNAL-EVAL**.

## `sbe init`, and the idempotence it is built on

```bash
bin/sbe init .                        # dry run (the default): every mutation as a diff, writes nothing
bin/sbe init . --apply                # writes: config, dossier directory, install receipt
bin/sbe init . --apply --with-consumer-ci  # also copies the consumer CI workflow and action, only when asked
```

Writes `.brothersbe/config.json` (the schema version, tool version, and the dossier root,
`design/`), a `design/.gitkeep` marker so the dossier directory is trackable before it holds
anything, and, only with `--with-consumer-ci`, a copy of this installation's own
`.github/workflows/consumer-check.yml` and `.github/actions/sbe-consumer/action.yml`. Refuses
outside a git repository, naming the reason: there is nowhere for the config, the dossier
directory or the receipt to be versioned.

It also ensures `.gitignore` carries one line, `.brothersbe/install-receipt.json`, under a
one-line comment explaining why: the receipt records this machine's absolute install path, a
local, personal fact with no business being tracked. That mutation is **appended, never owned**:
`sbe init` reads whatever is already in `.gitignore` and adds the comment and the line only
when they are missing, leaving every other line in the file untouched. Present means untouched,
the same idempotence rule as everything else here, and dry-run shows it as a proposed diff like
every other mutation.

Every proposal is deterministic content, compared byte for byte against what is already on disk,
which is what makes **running it twice under `--apply` change nothing the second time**: the
second run finds every proposal already matches and writes nothing, and the install receipt
(the one file that legitimately carries a timestamp) is left untouched rather than rewritten,
because nothing happened this run for it to describe. When something IS written, `sbe init`
writes or refreshes `.brothersbe/install-receipt.json`: the schema and tool version, when it
ran, every path it has ever written (across this call and any prior one), and exact uninstall
instructions, `rm -f <path>` for each, printed at the end and saved into the same receipt.
`.gitignore` is the one exception to that written set: it is written like any other proposal
when its line is missing, but it is never listed in `writtenPaths` or the uninstall
instructions, because `sbe init` only appended a line to a file it does not own, and an
uninstall instruction of `rm -f .gitignore` would delete every other line a real project keeps
in that file.

Limits in full: `docs/KNOWN-LIMITS.md`. Maturity: **INTERNAL-EVAL**.

## `tools/sbe_telemetry.py` data commands: `data-show`, `data-export`, `data-purge`

```bash
python3 tools/sbe_telemetry.py data-show
python3 tools/sbe_telemetry.py data-export [--out PATH]
python3 tools/sbe_telemetry.py data-purge [--category NAME] [--yes]
```

These three are not on `sbe`, and they are not going to be. `sbe` is the facade in front of the
assurance tools in the table above (`design`, `gate`, `score`, `intake`, `decide`, `verify`, `review`,
`impact`, `status`, and the rest): commands a CI job or a reviewer runs routinely, over a directory,
on somebody else's schedule. `data-show`, `data-export` and `data-purge` read and delete what
BrotherSBE has captured about the operator's own sessions, ratings, and messages. That is a privacy
surface, not an assurance surface, and folding it into a menu a script tabs through would make
"delete what was captured about me" one habitual keystroke away instead of something a person runs
deliberately, by name, on purpose. They live only on `tools/sbe_telemetry.py`, invoked directly, the
same way `intent`, `rate` and `purge-corrections` already do.

All three read the SAME inventory. The tool's own comment states the invariant: "a file that
`data-show` lists is a file `data-export` copies and `data-purge` removes," built from this module's
path constants plus a glob of the telemetry directory, so a per-project file cannot be listed by one
of the three and missed by the other two.

**Where the vault is:** `BROTHERSBE_VAULT`, default `~/BrotherSBEVault`. The telemetry directory
these three commands read and write is `<vault>/99-System/telemetry`.

### `data-show`

Read-only, never writes. Prints the capture policy in force for each category (`corrections`,
`metrics`, `transcript`, gated respectively by `BROTHERSBE_TELEMETRY_CORRECTIONS`,
`BROTHERSBE_TELEMETRY_METRICS`, `BROTHERSBE_TELEMETRY_TRANSCRIPT`, every category off by default),
then every file the tool can write: category, path, record count, byte size, file mode, and what it
holds, or "absent, so nothing is stored at this path" for one that does not exist. `-h`/`--help`
anywhere in its argv prints usage and exits 0 instead of running; any other flag is refused
nonzero rather than ignored. Real
output against this repository's own vault, paths abbreviated below, capture off:

```
BROTHERSBE STORED DATA (vault ~/BrotherSBEVault)
  policy: corrections capture is off: BROTHERSBE_TELEMETRY_CORRECTIONS is not set, and every category is off by default
  policy: metrics capture is off: BROTHERSBE_TELEMETRY_METRICS is not set, and every category is off by default
  policy: transcript capture is off: BROTHERSBE_TELEMETRY_TRANSCRIPT is not set, and every category is off by default
  [metrics] .../telemetry/outcomes.jsonl: absent, so nothing is stored at this path
  [metrics] .../telemetry/ratings.jsonl: absent, so nothing is stored at this path
  [metrics] .../telemetry/reviews.jsonl: absent, so nothing is stored at this path
  [corrections] .../telemetry/corrections.jsonl: absent, so nothing is stored at this path
  [housekeeping] .../telemetry/installed-skill-version-brothersbe: 1 record(s), 41 bytes, mode 644 -- the git sha of the installed skill at the last check
  [autosave] .../telemetry/autosave.log: 5 record(s), 1408 bytes, mode 644 -- one line per autosave snapshot, skip or lock event
  [autosave] .../telemetry/autosave-exclusions.log: 5 record(s), 487 bytes, mode 600 -- paths the autosave content scan kept out of a snapshot, and why (paths and reasons only, never the matched content)
read 3 file(s), 4 path(s) absent, 0 that could not be measured, under .../telemetry.
This lists this vault only. A backup, a mirror or a sync client may hold copies of any of it, and nothing here can see those.
```

### `data-export`

Writes ONE owner-only JSON bundle, file mode 600, named `brothersbe-telemetry-export.json` in the
current directory by default, `--out PATH` to name another location. The bundle carries the actual
file CONTENT for every path in the same inventory `data-show` lists, not just the counts, so it
"holds the stored data itself" in the tool's own words, and it says so on every run: "treat as
sensitive; redaction was applied at capture time and is best effort." This is how a person gets their
own captured data out of the vault to read somewhere else, not a routine export a script should
schedule. `-h`/`--help` anywhere in its argv prints usage (what it reads, what it writes, its
flags) and exits 0 without writing a bundle; any other unrecognized flag is refused with usage and
a nonzero exit rather than ignored, so a typo can no longer run a real export.

### `data-purge`

Deletes what is stored. Same dry-run shape as `sbe adopt` and `sbe init`: prints the inventory that
currently exists on disk and stops there unless `--yes` is also given. With `--yes`, it deletes each
file, then RE-CHECKS the filesystem afterward and reports removed / failed / still-present counts,
because, in the tool's own words, "a purge that reports success from its own intention has proven
nothing." `--category NAME` narrows the purge to one category.

Categories are not a fixed enum. They are read from whatever `data-show`'s own inventory currently
finds on disk, so an unrecognized name is refused with the live list, not a hardcoded one. Real
output against this repository's own vault, where only `autosave`, `corrections`, `housekeeping` and
`metrics` currently have a matching file to glob:

```
data-purge: no category named 'nope'; categories are autosave, corrections, housekeeping, metrics
```

A file that fails to remove, or that still exists after `os.remove` reported success, is named on its
own line rather than folded into a clean exit. `-h`/`--help` anywhere in its argv prints usage and
exits 0 without deleting anything; any other unrecognized flag, including a typo of `--category`, is
refused with usage and a nonzero exit rather than run as if the flag had never been given.

### The one law that governs all three, and everything else on this tool

`tools/sbe_telemetry.py` never blocks work: every hook and automatic path exits 0, and an unhandled
exception is caught and printed rather than propagated ("sbe_telemetry: swallowed error (never
blocks)"). The one deliberate exception is the three data-* commands above: a bad flag on one of
them refuses with usage and a nonzero exit instead of running past it, because a mistyped flag on a
command that reads or deletes the vault must not run as if nothing were wrong. Numbers are parsed
or absent; the tool never invents one.

Two commands remain **present and refuse**: `policy` and `exceptions`.
