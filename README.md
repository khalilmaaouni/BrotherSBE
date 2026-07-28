# BrotherSBE

BrotherSBE is a Claude Code skill that acts as a senior backend and data engineering colleague. It designs systems in the order the work actually runs: purpose, process, architecture, data, expression, then verification. It produces a design dossier, decides architecture from decision tables with named criteria, and holds the result to checks that run.

Identity, five words, each a law in [SKILL.md](SKILL.md) and the [`references/`](references/) files its routing table names: **realistic, SOTA, best practices driven, proven, trustable.**

It is the domain specialist sibling of [BrotherModeUp](https://github.com/khalilmaaouni/BrotherModeUp), the general orchestrator. BrotherSBE is standalone: clone it and it works with nothing else installed. See [PARITY.md](PARITY.md) for what the two share and where they diverge.

**Start here:** [a worked engagement](docs/guides/05-a-worked-engagement.md), one system designed end to end with the real commands and the real output.

## Who it is for

- **Small teams first (two to eight people).** Lessons become law only through a reviewed pull request into `memory-template/LEARNED.md`, so no colleague's tool changes behavior silently.
- **Strong individual contributors second.** On a solo install the team loop collapses to local learning and everything still works.

The operator is a working backend, infrastructure, or data engineer. BrotherSBE speaks to them as a peer: it shows the diff, names the command, uses the jargon, and explains on request rather than by default.

## The spine

Two rules carry the design.

**Design comes before verification.** The expensive mistakes are made while deciding what to build, how the process runs, what shape the system takes, and how the data is modeled. Checking the result at the end catches none of them.

**An agent earns trust in exact proportion to how mechanically its output can be checked.** Not by fluency, not by model quality. Every law names the thing that enforces it; the laws live in [SKILL.md](SKILL.md), which keeps the three that fire on no announced trigger, and in the [`references/`](references/) file its routing table sends each of the other sixteen to; a rule that cannot name one is advice and lives in [PRACTICES.md](PRACTICES.md), which says so.

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

**How much of it you write is computed, not chosen.** Five objective questions produce a tier, first match wins: T3 (money, partner data, personal data, production state, or not reversible in an hour) requires all seven; T2 (a contract change, or many consumers) requires six; T1 (one boundary crossed, or some consumers) requires the purpose brief; T0 requires nothing at all. T0 is the common case.

```bash
mkdir -p design/my-project                      # the intake refuses a directory that does not exist
python3 tools/sbe_intake.py design/my-project   # five questions, writes its 00-intake.json there
python3 tools/sbe_design.py .          # artifacts, adr, datamodel, diagrams, placeholder
python3 tools/sbe_decide.py tables/architecture.json shape   # asks for each criterion on stdin
```

`sbe_decide.py` reads its criteria interactively, so pipe the answers when you run it from a script, a CI job or an agent, where a prompt nobody answers is a hang: `printf '5\neventual\nhigh\nhigh\n' | python3 tools/sbe_decide.py tables/architecture.json shape`.

When you are done with the demo dossier, remove it: `rm -rf design/my-project`. The paths above are relative to this clone, so the demo files land INSIDE the installation, and `scripts/verify-install.sh` will (correctly) report any file you created here as EXTRA until you delete it. Real dossiers belong in your own project's repository, not in this clone.

Architecture shape is scored against named criteria in [`tables/architecture.json`](tables/architecture.json): independently deploying teams, consistency requirement, operational maturity, failure isolation. Every run returns a recommendation, up to two alternatives, the criteria that separated them, and what would flip the decision. A run where no criterion contributed returns NO-DATA with the recommendation suppressed, because a recommendation backed by zero evidence is a guess with a table around it.

## The last mile: four hard gates

Verification comes last, and only four failure classes get structural gates. Each fails silently: a wrong result looks exactly like a right one, and detection latency runs from minutes to never.

- **numbers**: every figure that could reach a decision ships with a second derivation whose text differs from the first by more than case, whitespace and comments, re-run to zero drift against a pinned snapshot. Text difference is the floor the tool can check, not proof that the two derivations are independent: renaming an alias passes, and nothing reads which tables they touch.
- **migration**: forward and reverse both ran against a restored copy, the reverse records a rehearsal run id as a string, and row counts before and after match. A receipt with no row counts is NO-DATA, not a pass: the gate says what it compared instead of asserting a comparison it never made. Stated plainly, because the difference matters: nothing resolves the rehearsal id against a job system, so it is a pointer for a human to follow.
- **approval**: a declared approval must be bound to more than a name typed into a text field. Two paths, and they are not equally strong. A signed `Approved-by:` commit trailer THIS HOST VERIFIED proves a key holder signed it, and an agent without the private key cannot produce it. A recorded `Reviewed-in:` review id proves only that a non-vacuous id sits in the commit message: nothing resolves it, there is no shape check on it, the agent writes commit messages, so an agent can write one. Its verdict is therefore NO-DATA, the same verdict a signature this host could not verify gets and for the same reason, and the evidence line says so on every run. If you need that path to be a control, add a CI step that resolves the id against your review platform. A typed name fails, a `Reviewed-in:` id that is a hyphen fails, and CI needs the signers' public keys for the one path that PASSes. The gate checks the binding of an approval that was declared; nothing detects that a change needed one, so the declaration itself is human review.
- **ran**: no SQL or pipeline change is done until its reconciliation query or test executed and left a receipt with a zero exit code and a nonzero duration. A check that took no time did not run.

The gates live in [`tools/sbe_gate.py`](tools/sbe_gate.py). They run advisory in a session (print the verdict, exit 0) and enforcing in CI (`--strict`, exit nonzero, stop the merge). Output that has not cleared its gate is presented with the label UNVERIFIED next to the item; that label is the agent's to write, per the law, and no tool applies it. Absent evidence is NO-DATA, never PASS, so a change with nothing to prove is not taxed. A receipt that exists and records nothing is also NO-DATA and says so; a receipt that exists and cannot be parsed, including valid JSON of the wrong shape, is a FAIL, because a broken claim is not an absent one. A check that crashes is reported as a FAIL carrying the exception, never as a missing line: a gate that disappears from the report is worse than one that fails. None of that rests on anyone remembering it. Every check is registered with a declaration of what it reads and what its empty state is, `PASS` is refused as an empty state at construction, and [`evals/test_no_data_class.py`](evals/test_no_data_class.py) enumerates those registries rather than a written list, so a check added later is covered the moment it is registered.

A companion linter in [`tools/sbe_score.py`](tools/sbe_score.py) catches the code patterns that swallow an error so a wrong result passes for a right one (bare except, except-then-pass, discarded subprocess result, conflict-skipping upsert, force-try) across `.py .sql .swift .rb .js .ts .go`. The upsert pattern reads the SQL wherever it is written and in whatever host language, so it fires on a `.sql` file, and it stops at the statement's semicolon so a legitimate `ON CONFLICT ... DO UPDATE` beside it is not swept in; it used to require a Python `.execute(` on the same line, which meant the one lint aimed at warehouse work could not fire on a warehouse file. A reviewed exemption carries a visible `# sbe: allow-silent <reason>` marker, so the swallow is auditable in the diff, and the reason is READ: a bare marker, or one carrying a refused token like `tbd`, waives nothing and the hit says why. The evidence names the first five hits or waived lines and then how many it did not name, names any file holding nothing to examine, names the linter's own source as skipped (by path, so a file of yours called `sbe_score.py` is still scanned), and carries the count of files that held no match at all. A run that opened no file is NO-DATA naming why, never "clean", and so is a scan whose every finding in every file was waived.

### What a gate actually reads

Each gate walks the directory it was named (the default is the current directory, never a silently substituted git worktree top) for a receipt file and checks it is internally consistent, not merely present (the operating record proves pasted receipts get invented).

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

**approval** looks for an `APPROVAL` file (declaring the change touches a money or partner path) or an `Approved-by:` trailer or `Reviewed-in:` id on HEAD. The trailer PASSes only when this host verified the commit signature against a key it TRUSTS (`git log` `%G?` = `G`, and `G` alone; `U` is a valid signature whose key matched no trusted principal, which is exactly what a self-generated SSH key produces, so it reports NO-DATA); an unsigned typed name FAILs, and a `Reviewed-in:` id reports NO-DATA because nothing resolves it.

**ran** looks for `ran-receipt.json`:

```json
{"checks": [{"name": "reconcile", "exit_code": 0, "duration_ms": 812}]}
```

## Install in minutes

What a first run on an unmodified repository tells you, and what it does not. It tells you one thing about your code immediately: the linter scans the tree you point it at and names every place an error is swallowed, with the file, the line and the pattern. Everything else starts empty on purpose. The four gates read receipts that a change has to produce, so on a repository that has never written one they report NO-DATA on all four, which means "no evidence either way" and never "checked and fine". The design checks read a dossier directory that does not exist yet. The graded checks read a telemetry vault and fence registries you have not installed, so their verdicts are about files outside your repository, and the report prints them under a heading that says exactly that. Nothing here infers quality from a repository's shape: a green first run is a report about what was read, and on a fresh install that is the linter and nothing else.

### As a plugin (recommended for teams)

BrotherSBE ships as a Claude Code plugin: one versioned thing to install, upgrade and roll back, with the hooks wired in the package instead of hand-copied into your settings file. Clone it anywhere, then check the package before you trust it:

```bash
git clone https://github.com/khalilmaaouni/BrotherSBE
claude plugin validate BrotherSBE
```

```
Validating plugin manifest: /path/to/BrotherSBE/.claude-plugin/plugin.json

✔ Validation passed
```

That gives you six namespaced skills (`/brothersbe:kickoff`, `:design`, `:verify`, `:review`, `:learn`, `:adopt`), seven read-only reviewer agents, and the four hooks resolving their own paths. Steps 2 and 3 below are then unnecessary: the vault export is still worth setting, but no hook goes into your `settings.json`. Moving from an older clone-style install is one page: [docs/MIGRATION.md](docs/MIGRATION.md). Distribution through an internal marketplace pinned to a signed release is not built yet, and is not claimed here.

Either way you install it, there is one command line over the nine script paths:

```bash
bin/sbe doctor
```

```
python           PASS     3.9.6 (floor is 3.9)
tools            PASS     all present in /path/to/BrotherSBE/tools
plugin-manifest  PASS     manifest 1.0.0-rc.1, VERSION 1.0.0-rc.1
git              PASS     working directory is inside a git tree
vault            NO-DATA  BROTHERSBE_VAULT is unset, so telemetry, session logs and resume briefs have nowhere durable to go
private-names    NO-DATA  no private-name list, so the publish leak check scans nothing

sbe 1.0.0-rc.1, evidence schema 1.0. 6 check(s): 4 PASS, 0 FAIL, 2 NO-DATA.
```

That block is a real run on a fresh install (no vault exported, no private-name list configured), with only the absolute installation path replaced by `/path/to/BrotherSBE`. The two NO-DATA lines are the point: an unanswered environment question is reported as unanswered, never folded into the passes.

`sbe` is a facade, not a rewrite: every built subcommand delegates to the tool in `tools/` that already carries the behavior and the tests, and the old invocations shown throughout this README still work and are not deprecated. Commands, exit codes, and the six subcommands that are present and deliberately refuse: [docs/CLI.md](docs/CLI.md).

### As a cloned skill (the original way, still supported)

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

What each does: **SessionStart** injects the active-laws digest plus mechanical nags and any update warning. **SessionEnd** appends one idempotent telemetry line and scans your short messages for correction candidates (secret-redacted, owner-only). **PreCompact** snapshots the whole worktree (including untracked files) to a private per-worktree git ref under `refs/brothersbe/autosave/` and writes a forward-looking resume brief, so a token-death is recoverable. Every hook exits 0 and never blocks a session. Details and opt-outs are in [SECURITY.md](SECURITY.md).

**4. Wire the checks into CI.** This is what turns them from advisory into blocking. Copy [`.github/workflows/brothersbe-gates.yml`](.github/workflows/brothersbe-gates.yml) into the repo you want guarded, or add its steps to an existing job:

```yaml
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
        run: python3 tools/sbe_score.py --strict --strict-soft .
      # The gates above are only worth what their tests are worth. These two ran
      # on nobody's merge path until now, which made them documentation rather
      # than a gate: a fixture no merge runs cannot stop anything.
      - name: Regression evals (every gate against the defect it exists to catch)
        run: python3 evals/run_evals.py
      - name: Honesty meta-test (no check may PASS over evidence it never examined)
        run: |
          python3 evals/test_no_data_class.py
          python3 evals/test_no_data_class.py --quiet --seed 1 --seed 2 --seed 3
      - name: Tool tests (redaction, permissions, identity, autosave, plugin surface, CLI)
        run: python3 tools/test_sbe.py
      - name: Fence hook tests (the write boundary)
        run: python3 tools/test_sbe_fence_hook.py
      - name: Impact fixtures (a declared tier cannot contradict the diff silently)
        run: python3 tools/test_sbe_impact.py
```

The last three matter as much as the first three. The gates are worth what their tests are worth, and a fixture no merge runs is documentation rather than a gate.

The approval gate reads commit trailers and signatures, so the checkout step needs `fetch-depth: 0`. Everything here is standard-library Python, no dependencies to install.

Invoke the skill with `/brothersbe` at the start of any backend, infrastructure, or data engineering task.

## Status: read this before trusting anything above

The same disclosure the checks demand of evidence, applied to the project itself.

- **Measured:** the eval counts, the meta-test scenario count, the lint numbers and the defect-reinjection record ([INVARIANTS.md](INVARIANTS.md)) are recomputed by the suites that print them; a doc quoting a stale one fails an eval.
- **Run on one estate only:** every threshold in `tables/`, every baseline in [RUBRIC.md](RUBRIC.md), and the hooks in daily use. They are defaults where you are, not measurements of your estate.
- **Never executed anywhere else:** this project's CI workflow has run in its own repository and in nobody else's; no external adoption is claimed. Windows is untested, and the shipped CI covers Linux and macOS only. The release tag and push steps in [docs/RELEASE.md](docs/RELEASE.md) have never been executed.

The full list, one heading per limit, is [docs/KNOWN-LIMITS.md](docs/KNOWN-LIMITS.md).

## Requirements

- Python 3, standard library only. There is no `pip install`, no lockfile, and no dependency to audit beyond the tree itself.
- git (the autosave, the approval gate, and the manifest all read it).
- Claude Code with hooks, for the session wiring above. The checkers run fine without it: every tool is a plain script you can run by hand.
- A POSIX shell for the two `sh` tools. Linux and macOS are what CI runs; Windows is untested.

## Uninstall

Removal is three deletions, and this section names what each leaves behind so nothing lingers silently:

1. Remove the hook entries from `~/.claude/settings.json` (and any project `.claude/settings.json` you added them to).
2. Delete the clone: `rm -rf ~/.claude/skills/brothersbe`.
3. Decide about your data, which uninstalling does NOT delete: the vault at `$BROTHERSBE_VAULT` (your session logs and telemetry, yours to keep or delete), the `export BROTHERSBE_VAULT` line in your shell profile, and the autosave snapshots under `refs/brothersbe/` in any repository where the hook fired (list them with `git for-each-ref refs/brothersbe/`, delete with `git update-ref -d <ref>`).

## A 60-second first run

Run the eval bed. Each case is a real failure class turned into a fixture with a planted defect, plus an assertion that the matching check CATCHES it. This is the mechanism behind the "proven" claim: the checks are tested against the defect classes the operating record produced, not asserted.

```bash
python3 evals/run_evals.py
```

Eight of its lines and the closing count, each verbatim (the suite grows, so these are picked
lines rather than the tail): the dossier lines are the honest path, which a gate is only worth
having if it clears, and the two consistency lines are the docs checking their own numbers:

```
  cache-counters-that-are-not-counts-are-caught want=FAIL     got=FAIL     ok
  a-complete-t0-dossier-blocks-nothing   want=clear    got=clear    ok
  a-complete-t1-dossier-blocks-nothing   want=clear    got=clear    ok
  a-complete-t2-dossier-blocks-nothing   want=clear    got=clear    ok
  a-complete-t3-dossier-blocks-nothing   want=clear    got=clear    ok
  a-change-with-no-numbers-and-no-migration-blocks-nothing want=clear    got=clear    ok
  no-shipped-doc-prints-an-eval-count-the-suite-does-not-produce want=consistent got=consistent ok
  no-shipped-doc-prints-a-meta-test-count-the-meta-test-does-not-produce want=consistent got=consistent ok

509 evals: 509 passed, 0 regressions.
```

The bed exits nonzero if any check stops catching its defect, so it doubles as a release gate for the skill itself.

Then run the honesty meta-test, which is the one that keeps the rest honest. It carries no list of
checks and no list of registries: it DISCOVERS every registry of checks in `tools/`, and refuses to
run if it finds one it was not taught to invoke. For each check it takes the worked example that
check declares and hollows it out, one leaf, one subtree and one whole receipt at a time, in empty
strings, whitespace and nulls, and requires that none of it produces a PASS. A check added later is
covered without anyone remembering, and so is a field added to an existing one.

```bash
python3 evals/test_no_data_class.py
```

Its last line, verbatim:

```
21 checks discovered from 3 registries in 7 module(s), 1920 scenarios run, 2 waived by declared exemption, 0 failure(s).
```

To watch one check on a real change:

```bash
python3 tools/sbe_design.py .           # the five design checks, advisory
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
- [docs/for-engineers/](docs/for-engineers/): onboarding for backend, data, infrastructure and ETL engineers who have never seen this tool. Start at [00-READ-ME-FIRST.md](docs/for-engineers/00-READ-ME-FIRST.md); four complete worked dossiers are in [docs/for-engineers/examples/](docs/for-engineers/examples/).
- [docs/SETUP.md](docs/SETUP.md) to install, and the rest of [docs/guides/](docs/guides/) for the gates, the doctrines, and teams.
- [SKILL.md](SKILL.md) plus the [`references/`](references/) files its routing table names are the law itself; [SECURITY.md](SECURITY.md) is the data and network posture (no network calls, no analytics, no account, no server).

## License

MIT. See [LICENSE](LICENSE).

Created by Khalil Maaouni.
