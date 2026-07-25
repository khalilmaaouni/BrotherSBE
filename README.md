# BrotherSBE

BrotherSBE is a Claude Code skill that acts as a senior backend and data engineering colleague. It designs systems in the order the work actually runs: purpose, process, architecture, data, expression, then verification. It produces a design dossier, decides architecture from decision tables with named criteria, and holds the result to checks that run.

Identity, five words, each a law in [SKILL.md](SKILL.md): **realistic, SOTA, best practices driven, proven, trustable.**

It is the domain specialist sibling of [BrotherModeUp](https://github.com/khalilmaaouni/BrotherModeUp), the general orchestrator. BrotherSBE is standalone: clone it and it works with nothing else installed. See [PARITY.md](PARITY.md) for what the two share and where they diverge.

**Start here:** [a worked engagement](docs/guides/05-a-worked-engagement.md), one system designed end to end with the real commands and the real output.

## Who it is for

- **Small teams first (two to eight people).** Lessons become law only through a reviewed pull request into `memory-template/LEARNED.md`, so no colleague's tool changes behavior silently.
- **Strong individual contributors second.** On a solo install the team loop collapses to local learning and everything still works.

The operator is a working backend, infrastructure, or data engineer. BrotherSBE speaks to them as a peer: it shows the diff, names the command, uses the jargon, and explains on request rather than by default.

## The spine

Two rules carry the design.

**Design comes before verification.** The expensive mistakes are made while deciding what to build, how the process runs, what shape the system takes, and how the data is modeled. Checking the result at the end catches none of them.

**An agent earns trust in exact proportion to how mechanically its output can be checked.** Not by fluency, not by model quality. Every law in [SKILL.md](SKILL.md) names the thing that enforces it; a rule that cannot name one is advice and lives in [PRACTICES.md](PRACTICES.md), which says so.

## The dossier

A design engagement produces at most seven files in one directory. Templates with worked content are in [`templates/dossier/`](templates/dossier/).

| File | Holds | Checked by |
|---|---|---|
| `00-intake.json` | the five intake answers and the computed tier | `sbe_intake.py` writes it |
| `01-purpose.md` | problem, users, success criteria, non-goals, blast radius | artifacts |
| `02-process.md` | actors, steps with triggers and exception paths, handoffs with contracts | artifacts |
| `03-adr.md` | criteria, two rejected alternatives, decision, consequences, flip condition | adr |
| `04-technology-map.md` | per component: technology, owner, failure mode, recovery path | artifacts |
| `05-data-model.md` | conceptual, logical, physical; systems of record; cardinalities | datamodel |
| `06-diagrams.md` | Mermaid views, every node traceable to the dossier | diagrams |
| `07-verification.md` | every claim, the check that proves it, when it runs | artifacts |

**How much of it you write is computed, not chosen.** Five objective questions produce a tier, first match wins: T3 (money, partner data, personal data, production state, or not reversible in an hour) requires all seven; T2 (a contract change, or many consumers) requires six; T1 (one boundary crossed) requires the purpose brief; T0 requires nothing at all. T0 is the common case.

```bash
python3 tools/sbe_intake.py            # five questions, writes 00-intake.json
python3 tools/sbe_design.py .          # artifacts, adr, datamodel, diagrams
python3 tools/sbe_decide.py tables/architecture.json shape
```

Architecture shape is scored against named criteria in [`tables/architecture.json`](tables/architecture.json): independently deploying teams, consistency requirement, operational maturity, failure isolation. Every run returns a recommendation, up to two alternatives, the criteria that separated them, and what would flip the decision. A run where no criterion contributed returns NO-DATA with the recommendation suppressed, because a recommendation backed by zero evidence is a guess with a table around it.

## The last mile: four hard gates

Verification comes last, and only four failure classes get structural gates. Each fails silently: a wrong result looks exactly like a right one, and detection latency runs from minutes to never.

- **numbers**: every figure that could reach a decision ships with an independently scripted second derivation, re-run to zero drift against a pinned snapshot.
- **migration**: forward and reverse both ran against a restored copy, the reverse carries a resolvable rehearsal run id, and row counts before and after match.
- **approval**: money and partner paths need a named human approval bound to an identity the agent cannot forge (a signed `Approved-by:` commit trailer or a recorded `Reviewed-in:` review id). A typed name fails.
- **ran**: no SQL or pipeline change is done until its reconciliation query or test executed and left a receipt with a zero exit code and a nonzero duration. A check that took no time did not run.

The gates live in [`tools/sbe_gate.py`](tools/sbe_gate.py). They run advisory in a session (print the verdict, exit 0) and enforcing in CI (`--strict`, exit nonzero, stop the merge). Output that has not cleared its gate carries the label UNVERIFIED next to the item. Absent evidence is NO-DATA, never PASS, so a change with nothing to prove is not taxed.

A companion linter in [`tools/sbe_score.py`](tools/sbe_score.py) catches the code patterns that swallow an error so a wrong result passes for a right one (bare except, except-then-pass, discarded subprocess result, conflict-skipping upsert, force-try). A reviewed exemption carries a visible `# sbe: allow-silent <reason>` marker, so the swallow is auditable in the diff.

### What a gate actually reads

Each gate walks the git worktree for a receipt file and checks it is internally consistent, not merely present (the operating record proves pasted receipts get invented).

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

**migration** looks for `migration-receipt.json`:

```json
{"forward": {"ran_against_restore": true},
 "reverse": {"ran_against_restore": true, "rehearsal_run_id": "job_8842"},
 "row_counts": {"before": 100, "after_reverse": 100}}
```

**approval** looks for an `APPROVAL` file (declaring the change touches a money or partner path) plus an `Approved-by:` trailer or `Reviewed-in:` id on HEAD. The trailer passes only when the commit signature verifies (`git log` `%G?` in `G`, `U`, or `E`); an unsigned typed name FAILs.

**ran** looks for `ran-receipt.json`:

```json
{"checks": [{"name": "reconcile", "exit_code": 0, "duration_ms": 812}]}
```

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

**4. Wire the checks into CI.** This is what turns them from advisory into blocking. Copy [`.github/workflows/brothersbe-gates.yml`](.github/workflows/brothersbe-gates.yml) into the repo you want guarded, or add the three lines to an existing job:

```yaml
      - name: Hard gates (numbers, migration, approval, ran) block on failure
        run: python3 tools/sbe_gate.py --strict .
      - name: Design checks (dossier completeness) block on failure
        run: python3 tools/sbe_design.py --strict .
      - name: Silent-failure lints and code-graded checks block on failure
        run: python3 tools/sbe_score.py --strict .
```

The approval gate reads commit trailers and signatures, so the checkout step needs `fetch-depth: 0`. All three tools are standard-library Python, no dependencies to install.

Invoke the skill with `/brothersbe` at the start of any backend, infrastructure, or data engineering task.

## A 60-second first run

Run the eval bed. Each case is a real failure class turned into a fixture with a planted defect, plus an assertion that the matching check CATCHES it. This is the mechanism behind the "proven" claim: the checks are tested against the defect classes the operating record produced, not asserted.

```bash
python3 evals/run_evals.py
```

Expected tail:

```
  small-team-strong-consistency-is-not-microservices want=modular monolith got=modular monolith ok
  many-teams-high-isolation-is-services  want=services got=services ok
  recommendation-always-names-a-flip-condition want=yes      got=yes      ok
  low-team-count-high-isolation-is-event-driven want=event-driven got=event-driven ok
  empty-context-is-no-data               want=NO-DATA  got=NO-DATA  ok
  non-numeric-number-criterion-is-unrecognized want=unrecognized got=unrecognized ok

37 evals: 37 passed, 0 regressions.
```

The bed exits nonzero if any check stops catching its defect, so it doubles as a release gate for the skill itself. To watch one check on a real change:

```bash
python3 tools/sbe_design.py .           # the four design checks, advisory
python3 tools/sbe_gate.py numbers .     # one hard gate
python3 tools/sbe_gate.py --strict .    # enforcing: exits nonzero on any FAIL
```

## What this is not

- **Not autonomous.** No agent holds apply rights on production state (databases, IaC apply, deploy, partner endpoints). It drafts; a human applies. Credentials are never typed, stored, or logged.
- **Not an oracle.** Confidence is stated at the claim (verified by command, verified by inspection, likely, assumed), every number carries its source, and where the record shows agents do not help it stands down instead of guessing.
- **Not a checkbox.** Cloning the skill gives you the tools. It does not enforce anything until you wire `--strict` into CI, and that CI wiring is real setup, not a toggle. Advisory mode tells a session; only CI stops a merge.
- **Not a set of numbers you inherit.** Every threshold in `tables/` and every baseline in [RUBRIC.md](RUBRIC.md) was measured on one estate. Re-measure on your own before treating one as yours. NO-DATA is a legal score and never a pass.

## Learn more

- [docs/guides/05-a-worked-engagement.md](docs/guides/05-a-worked-engagement.md): one system designed end to end, real commands, real output. The best place to start.
- [docs/DESIGN.md](docs/DESIGN.md): the why and what, in the real order.
- [docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md): the mechanical half, tool by tool.
- [docs/SETUP.md](docs/SETUP.md) to install, and the rest of [docs/guides/](docs/guides/) for the gates, the doctrines, and teams.
- [SKILL.md](SKILL.md) is the law itself; [SECURITY.md](SECURITY.md) is the data and network posture (no network calls, no analytics, no account, no server).

## License

MIT. See [LICENSE](LICENSE).

Created by Khalil Maaouni.
