# 07. Verification plan

Every command named below was confirmed to exist in this worktree before it was
written down, either by running it with `--help` or by reading it out of
.github/workflows/brothersbe-gates.yml. A claim with no check is a hope, and a
check that names a command nobody can run is worse than a hope, because it reads
like evidence.

## The battery every loop runs

These four run at the close of every loop, not only at the end of the program.
All four are copied verbatim from the merge gate, at
.github/workflows/brothersbe-gates.yml lines 83, 92, 122 and 127.

| Command | What it proves |
|---|---|
| `python3 tools/sbe_design.py --strict .` | Every dossier in the tree carries the artifacts its tier requires, its decision record names at least two rejected alternatives and a flip condition, its data model names an owning system per entity and a cardinality per relationship, and its diagram nodes all trace |
| `python3 tools/sbe_gate.py --strict design` | The four hard gates (numbers, migration, approval, ran) over the dossiers |
| `python3 tools/sbe_score.py --strict --strict-soft .` | The scored surface, including the silent-failure lints, with soft findings blocking too |
| `python3 evals/run_evals.py` | Every gate is run against the defect it exists to catch, so a gate that stopped catching its own defect fails here |

## Per loop

| Loop | The claim it makes | The check that proves it | When it runs |
|---|---|---|---|
| 0 | The tree is converged: main carries every in-flight branch and the battery is green on it | `git log --oneline -1 f7191de` confirms the merge is on main, and the four battery commands above run clean on that commit. Done: closed at f7191de | Closed 2026-08-01 |
| 1 | The product makes no network call except the two it names | An added fixture that plants a network import under src/ and asserts the scan fails. It must be red before the scan is widened and green after | Every merge, inside `python3 tools/sbe_score.py --strict --strict-soft .` |
| 1 | Every test suite in tools/ runs on merge | A check comparing the output of `ls tools/test_*.py` against the run steps in .github/workflows/brothersbe-gates.yml; it must report no file left out. Baseline today: 17 files, 3 named | Every merge |
| 1 | The security documents quote only true claims | `python3 evals/run_evals.py`, whose doc-honesty evals already test documentation against the code and are the existing home for this class of check | Every merge |
| 2 | Concurrent writes lose nothing | A multi-process stress test added beside `python3 tools/test_sbe_decisions.py` and `python3 tools/test_sbe_tasks.py`, asserting that N concurrent writes produce N distinct durable records | Every merge, once Loop 1 has wired those two suites |
| 2 | A command that ran no check clears no obligation | The bypass fixtures in `python3 tools/test_sbe_bypass.py`, which must be red under the old classifier and green under the new one. Both directions are asserted, because a fixture that only passes after the fix proves nothing about what it caught | Every merge |
| 2 | A hand-copied gate evidence file no longer passes | `python3 tools/test_sbe_evidence.py` extended with a receipt whose bound commit is not the current head, asserted to clear nothing; and `bin/sbe evidence verify` on that receipt, asserted to report it stale | Every merge |
| 3 | One locator, one tier reader, one next-action evaluator | Fixture repositories in `python3 tools/test_sbe_status.py` and `python3 tools/test_sbe_status_team.py` where `bin/sbe status` and `bin/sbe status --team` must resolve the same repository to the same project | Every merge |
| 3 | Following the printed next action always terminates | A convergence suite: for each fixture, repeatedly take the next action `bin/sbe status --json` prints, and assert the fixture reaches done or an explicit human decision, and never revisits a state it has already been in | Every merge |
| 3 | A review record is durable and goes stale | `bin/sbe converge --base <base> --head <head> <dossier>` must report NO-DATA when no review record exists, PASS when a current one does, and FAIL when the record names an older commit than the head | Every merge, plus by hand at every loop close |
| 3 | The guided skills and the command line agree | A parity fixture set asserting that the answer rendered by each skill under skills/ equals the answer `bin/sbe status --json` computes, for every fixture | Every merge |
| 4 | Six JSON shapes became one envelope | Parity fixtures asserting that the text output, the JSON envelope and the rendering in skills/help/map-template.html describe the same canonical state for the same fixture repository | Every merge |
| 5 | Install, update, rollback and uninstall work from clean | `sh scripts/test-install-artifact.sh` and `sh scripts/test-upgrade-rollback.sh`, both already wired at .github/workflows/brothersbe-gates.yml lines 159 and 166. The rollback script has only ever taken its NO-DATA branch, so Loop 5 is the first run of its real path and that run is the evidence | Every merge, and by hand on a clean machine per platform before the release |
| 5 | The installation is healthy on a fresh machine | `bin/sbe doctor` on each clean machine, and `bin/sbe adopt` on a repository that has never seen the product | Once per supported platform, per release candidate |
| 5 | The release candidate is a real, reachable release | `bin/sbe pr verify <number> --repo owner/name` against the live pull request, and the release checklist in PUBLISH-CHECKLIST.md walked item by item | Once per release candidate |
| 6 | Beginners and engineers can finish | Five beginners and five engineers each complete the benchmark project, with the observation sheet recording where they stopped, what they asked, and what they read. Human evidence, not a command | Once, before the release decision |
| 6 | Nothing regressed on the candidate commit | The four battery commands, plus every suite in tools/, run on the exact immutable candidate commit, and a fresh review that attempts to refute lifecycle convergence, evidence freshness, install persistence, rollback and the security claims | Once, on the candidate commit |

## Verifying this dossier itself

The program is designed through the product it is releasing, so this dossier is
checked by the same tool a user's dossier would be:

```
python3 tools/sbe_design.py design/final-release-program --strict
```

The tier was computed by `tools/sbe_intake.py`, not typed. The checker re-derives
it from the five recorded answers on every run and fails if the stored tier and
the computed one disagree, which means the tier in 00-intake.json cannot be
lowered by editing it.

## What no command here can prove

Three things, stated so nobody mistakes the table above for full coverage.

First, whether a rejected alternative's stated reason is a real reason or a
restatement of its name is human review; the checker measures that the text
exists, not that it reasons.

Second, the hosted run identifier recorded in 02-process.md for the first
all-green result came from the Loop 0 close brief rather than from a file in this
repository, and nothing here has confirmed it against the hosting service.

Third, the benchmark trials in Loop 6 produce human observation, not machine
evidence. That is the intended shape of that gate, and it is the one gate in the
program that a passing command cannot substitute for.
