# BrotherSBE

BrotherSBE is a Claude Code skill that acts as a senior backend and data engineering colleague: it owns outcomes (correct systems, sound numbers, kept promises) instead of waiting for instructions. Every figure it hands you arrives with its check already run, and where the record shows agents do not help it says "no published evidence" rather than bluff.

Identity, five words, each a law in [SKILL.md](SKILL.md): **realistic, SOTA, best practices driven, proven, trustable.**

It is the domain specialist sibling of [BrotherModeUp](https://github.com/khalilmaaouni/BrotherModeUp), the general orchestrator. BrotherSBE is standalone: clone it and it works with nothing else installed. See [PARITY.md](PARITY.md) for what the two share and where they diverge.

## Who it is for

- **Small teams first (two to eight people).** The learning loop is built for a team: lessons become law only through a reviewed pull request into `memory-template/LEARNED.md`, so no colleague's tool changes behavior silently.
- **Strong individual contributors second.** On a solo install the team loop collapses to local learning and everything still works.

The operator is a working backend, infrastructure, or data engineer. BrotherSBE speaks to them as a peer: it shows the diff, names the command, uses the jargon, and explains on request rather than by default.

## The spine

One idea sits under every law: **an agent earns trust in exact proportion to how mechanically its output can be checked.** Not by fluency, not by model quality. Each hard gate below is that rule applied to one silent-failure class, where a wrong result looks exactly like a right one and detection latency runs from minutes to never.

## The four hard gates

Run advisory in a session (prints the verdict, exits 0) and enforcing in CI (`--strict`, exits nonzero and stops the merge). Output that has not cleared its gate carries the label UNVERIFIED next to the item. Absent evidence is NO-DATA, never PASS.

- **numbers**: every figure that could reach a decision ships with an independently scripted second derivation, re-run to zero drift against a pinned snapshot.
- **migration**: forward and reverse both ran against a restored copy, the reverse carries a resolvable rehearsal run id, and row counts before and after match.
- **approval**: money and partner paths need a named human approval bound to an identity the agent cannot forge (a signed `Approved-by:` commit trailer or a recorded `Reviewed-in:` review id). A typed name fails.
- **ran**: no SQL or pipeline change is done until its reconciliation query or test executed and left a receipt with a zero exit code and a nonzero duration. A check that took no time did not run.

The gate lives in [`tools/sbe_gate.py`](tools/sbe_gate.py). A companion linter in [`tools/sbe_score.py`](tools/sbe_score.py) is gate severity by ratified decision: it catches the code patterns that swallow an error so a wrong result passes for a right one (bare except, except-then-pass, discarded subprocess result, conflict-skipping upsert, force-try). A genuine reviewed exemption carries a visible `# sbe: allow-silent <reason>` marker, so the swallow is auditable in the diff.

### What a gate actually reads

Each gate walks the git worktree for a receipt file and checks it is internally consistent, not merely present (the operating record proves pasted receipts get invented). Drop these next to your change and the gate reads them.

**numbers** looks for `numbers-manifest.json`. A figure passes only with a `snapshot_id`, a `second_derivation` textually different from `query`, `rerun.ran` true, and matching `primary`/`secondary`:

```json
{"figures": [{
  "label": "gmv",
  "snapshot_id": "snap_2026_07",
  "query": "SELECT SUM(amount) FROM orders",
  "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
  "rerun": {"ran": true, "primary": 17570, "secondary": 17570}
}]}
```

A missing `snapshot_id`, a `second_derivation` identical to `query`, or `primary != secondary` each FAILs with the reason named.

**migration** looks for `migration-receipt.json`. Both legs must run against a restore, the reverse needs a resolvable id (free text is not a receipt), and the row counts must match:

```json
{"forward": {"ran_against_restore": true},
 "reverse": {"ran_against_restore": true, "rehearsal_run_id": "job_8842"},
 "row_counts": {"before": 100, "after_reverse": 100}}
```

**approval** looks for an `APPROVAL` file (declaring the change touches a money or partner path) plus an `Approved-by:` trailer or `Reviewed-in:` id on HEAD. The trailer passes only when the commit signature verifies (`git log` `%G?` in `G`, `U`, or `E`); an unsigned typed name FAILs.

**ran** looks for `ran-receipt.json`. Every listed check needs an `exit_code` of 0 and a nonzero `duration_ms`:

```json
{"checks": [{"name": "reconcile", "exit_code": 0, "duration_ms": 812}]}
```

An exit code of 1, a missing exit code, or a zero duration each FAILs.

## Install in minutes

**1. Clone into your skills directory.**

```bash
git clone https://github.com/khalilmaaouni/BrotherSBE ~/.claude/skills/brothersbe
```

**2. Point the vault at durable storage.** All telemetry, session logs, and resume briefs live here. Nothing leaves the machine.

```bash
export BROTHERSBE_VAULT="$HOME/BrotherSBEVault"   # put this in your shell profile
```

**3. Wire the hooks** into `~/.claude/settings.json` (or a project `.claude/settings.json`). The harness fires these, not the model, which is the point: the "save before you die" rule cannot be executed by the actor that is dying.

```json
{
  "hooks": {
    "SessionStart": [
      {"hooks": [{"type": "command",
        "command": "sh ~/.claude/skills/brothersbe/tools/sbe_sessionstart.sh"}]}
    ],
    "SessionEnd": [
      {"hooks": [{"type": "command",
        "command": "python3 ~/.claude/skills/brothersbe/tools/sbe_telemetry.py outcomes-append"}]}
    ],
    "PreCompact": [
      {"hooks": [
        {"type": "command",
         "command": "sh ~/.claude/skills/brothersbe/tools/sbe_autosave.sh precompact"},
        {"type": "command",
         "command": "python3 ~/.claude/skills/brothersbe/tools/sbe_telemetry.py precompact-brief"}
      ]}
    ]
  }
}
```

What each does: **SessionStart** injects the active-laws digest plus mechanical nags and any update warning. **SessionEnd** appends one idempotent telemetry line and scans your short messages for correction candidates (secret-redacted, owner-only). **PreCompact** snapshots the whole worktree (including untracked files) to a private git ref `refs/brothersbe/autosave` and writes a forward-looking resume brief, so a token-death is recoverable. Every hook exits 0 and never blocks a session. Details and opt-outs are in [SECURITY.md](SECURITY.md).

**4. Wire the gates into CI.** This is what turns the gates from advisory into blocking. Copy [`.github/workflows/brothersbe-gates.yml`](.github/workflows/brothersbe-gates.yml) into the repo you want guarded, or add the two lines to an existing job:

```yaml
      - name: Hard gates (numbers, migration, approval, ran) block on failure
        run: python3 tools/sbe_gate.py --strict .
      - name: Silent-failure lints and code-graded checks block on failure
        run: python3 tools/sbe_score.py --strict .
```

The approval gate reads commit trailers and signatures, so the checkout step needs `fetch-depth: 0`. Both tools are standard-library Python, no dependencies to install.

Invoke the skill with `/brothersbe` at the start of any backend, infrastructure, or data engineering task.

## A 60-second first run

Run the eval bed. Each case is a real failure class turned into a fixture with a planted defect, plus an assertion that the matching gate CATCHES it. This is the mechanism behind the "proven" claim: the gates are tested against the exact defect classes the operating record produced, not asserted.

```bash
python3 evals/run_evals.py
```

Expected tail:

```
  overstated-total-caught                want=FAIL     got=FAIL     ok
  sound-number-passes                    want=PASS     got=PASS     ok
  non-independent-derivation-caught      want=FAIL     got=FAIL     ok
  ...
  green-on-red-caught                    want=FAIL     got=FAIL     ok

13 evals: 13 passed, 0 regressions.
```

The bed exits nonzero if any gate stops catching its defect, so it doubles as a release gate for the skill itself. To watch a single gate on a real change, drop the matching receipt in your worktree and run it advisory:

```bash
python3 tools/sbe_gate.py numbers .     # one class
python3 tools/sbe_gate.py .             # all four, advisory
python3 tools/sbe_gate.py --strict .    # enforcing: exits nonzero on any FAIL
```

## What this is not

- **Not autonomous.** The blast-radius rule holds: no agent holds apply rights on production state (databases, IaC apply, deploy, partner endpoints). It drafts; a human applies. Credentials are never typed, stored, or logged.
- **Not an oracle.** Confidence is stated at the claim (verified by command, verified by inspection, likely, assumed), every number carries its source, and where the record shows agents do not help it stands down instead of guessing.
- **Not a checkbox for the gates.** Cloning the skill gives you the tools. It does not enforce anything until you wire `--strict` into CI, and that CI wiring is real setup, not a toggle. Advisory mode tells a session; only CI stops a merge.
- **Not a set of numbers you inherit.** Every baseline in [RUBRIC.md](RUBRIC.md) is the author's, measured on one machine. Re-measure on your own estate before treating a threshold as yours. NO-DATA is a legal score and never a pass.

## Learn more

The full rationale is the whitepaper, split into three documents in the shape of the sibling repo: [docs/DESIGN.md](docs/DESIGN.md) for the why and what (philosophy, doctrines, benchmarks), [docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md) for the mechanical half (the chassis, the four gates, the file-by-file architecture), and [docs/SETUP.md](docs/SETUP.md) to install. Worked, copy-pasteable guides are in [docs/guides/](docs/guides/). Start with [SKILL.md](SKILL.md) for the law itself and [SECURITY.md](SECURITY.md) for the data and network posture (no network calls, no analytics, no account, no server).

## License

MIT. See [LICENSE](LICENSE).

Created by Khalil Maaouni.
