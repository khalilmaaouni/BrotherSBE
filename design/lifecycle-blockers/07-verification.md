# 07. Verification plan

Every command below was run in this worktree before it was written down, at
commit `9888225` (the merge of pull request 10 onto `main`). A claim with no
check is a hope, and a check nobody ran is worse than a hope, because it
reads like evidence.

## The two live reproductions this dossier exists to close

Both run against this repository AS IT STANDS, before any of the four
decisions in `03-adr.md` land.

**CR-06/CR-07, `sbe status . --json`:**

```
python3 bin/sbe status . --json
```

Confirmed output includes `"storesInspected": {"disposition": null,
"evidenceDir": null, "intake": null, "taskRegistry": null}`, `"nextAction":
"nothing blocking here that this tool can see..."`, exit 0, on a repository
that carries two full dossiers under `design/`. `sbe status --team --json`
on the identical tree finds both.

**CR-07, four NO-DATA gates exiting clean:**

```
python3 tools/sbe_gate.py design/final-release-program --strict
```

Confirmed output: all four gates (`numbers`, `migration`, `approval`,
`ran`) report NO-DATA, and the process exits 0 despite `--strict`, because
`tools/sbe_gate.py:1615-1616` only increments `fails` on a FAIL and
`:1630-1633` only exits nonzero when `fails` is nonzero. This is the
condition `skills/next/SKILL.md` rung 5 (`:31-33`) cannot currently
distinguish from a real failure.

## The battery every wave runs

Copied from the merge gate's own required checks, the same discipline
`design/final-release-program/07-verification.md` uses.

| Command | What it proves | Confirmed this run |
|---|---|---|
| `python3 tools/sbe_design.py --strict .` | Every dossier in the tree, including this one, carries the artifacts its tier requires | Run against `design/lifecycle-blockers` as this dossier's own done-check |
| `python3 tools/sbe_gate.py --strict design` | The four hard gates over every dossier under `design/` | NO-DATA on all four for both existing dossiers today, exit 0 |
| `python3 evals/run_evals.py` | Every check is run against the defect it exists to catch | Includes the tier-computation evals (`tier-feature-when-contract-changes want=T2 got=T2 ok`, confirming this dossier's own tier) |

## Per decision

| Decision | The claim it makes | The check that proves it | Baseline confirmed this run |
|---|---|---|---|
| 1 (CR-06) | Single-project `sbe status` finds a dossier nested under `design/<name>/`, the same set `--team` finds | `python3 tools/test_sbe_status.py`; a new fixture asserting `build_report` on a nested-only repository names the dossiers in `scope.storesInspected` and does not report "nothing blocking here" over a tree that demonstrably has a blocker | `python3 tools/test_sbe_status.py`: 28 tests, OK |
| 2 (CR-08) | A default `sbe verify` mints one kind-tagged receipt per delegate, bound to the commit, and `sbe status`'s MISSING EVIDENCE is empty for a tier that owes evidence on a clean tree | `python3 tools/test_sbe_evidence.py`, extended with a fixture asserting `sbe verify` on a clean fixture leaves three receipts in `.sbe/evidence`; the receipt-covering tests at `test_sbe_status.py:251` and `:301`; `python3 evals/test_no_data_class.py` must keep reporting empty-dir NO-DATA for every check, unchanged | `python3 tools/test_sbe_evidence.py`: 57 tests, OK. `python3 evals/test_no_data_class.py`: 31 checks discovered from 5 registries in 28 modules, 3758 scenarios run, 2 waived by declared exemption, 0 failures |
| 3 (CR-07, CR-10) | The guided skills' recommended action matches `sbe status --json`'s `nextAction` for the same fixture, and rung 5 of `skills/next` does not recommend `/brothersbe:verify` when four gates are legitimately NO-DATA and `missingEvidence` is empty for the declared tier | A parity fixture set added beside `python3 tools/test_sbe_status.py`, one fixture per rung of the priority ladder in `skills/next/SKILL.md`, plus the specific NO-DATA-does-not-loop fixture | `python3 tools/test_sbe_status.py`: 28 tests, OK (the baseline the parity fixtures are added to) |
| 4 (CR-03) | `install.sh`'s doctor step grades `$TARGET`, not the BrotherSBE clone; an installed `hooks/hooks.json` actually fires the fence hook contract; a path with a space in `SCRIPT_DIR` resolves correctly | `python3 tools/test_sbe_install.py`, extended with the run_doctor-grades-target fixture; a new installed-layout hook-firing test built on the harness at `tools/test_sbe_fence_hook.py:572-601`, both network-fenced by stubbing `git` and `claude` on `PATH` per the cr03 scout's two env levers, `SBE_INSTALL_REQUIRE` and `HOME` | `python3 tools/test_sbe_install.py`: 19 tests, OK |

## What is expected to move, and what is not allowed to

The `evals/run_evals.py` and `evals/test_no_data_class.py` scenario counts
are expected to grow: each new fixture named in the per-decision table above
adds scenarios to whichever registry it belongs to (today: 31 checks, 3758
scenarios, 0 failures for `test_no_data_class.py`). A count going up is
evidence the new coverage landed; a count going DOWN on the same registries
is itself a finding, not routine drift, because it means a check stopped
being discovered.

Three things are honesty constraints, not test counts, and none of them may
move regardless of how the four decisions are implemented:

- **A NO-DATA never becomes a PASS.** Decision 3's fix teaches skills to
  read a NO-DATA correctly, never to relabel it. `evals/test_no_data_class.py`
  already asserts empty-dir NO-DATA for every gate and check it discovers;
  that assertion is unchanged by any of the four decisions, and a change
  that makes it pass by weakening it rather than by the skill reading it
  correctly is not this fix.
- **A dirty-tree receipt stays NO-DATA.** Decision 2's minting must not
  make a receipt earned mid-edit read as evidence for a tree it did not
  examine; `test_sbe_evidence.py:286` and `status.py:199-202` already assert
  this for hand-written receipts, and the same assertion applies to
  minted ones.
- **`tools/sbe_gate.py`'s "writes: nothing" promise stays true.** Decision
  2 puts minting in `_cmd_verify`, never in a gate; a test asserting
  `sbe_gate.py` alone (no `_cmd_verify` wrapper) leaves `.sbe/evidence`
  untouched is part of the same battery this table already runs.

## Verifying this dossier itself

```
python3 tools/sbe_design.py --strict design/lifecycle-blockers
```

The tier is re-derived by `tools/sbe_intake.py` from the five answers in
`00-intake.json` on every run, not trusted as typed:

```
python3 -c "import sys; sys.path.insert(0,'tools'); import sbe_intake; print(sbe_intake.compute_tier({'changes_contract': True, 'crosses_boundary': True, 'reversible_under_hour': True, 'touches_sensitive': False, 'consumers': 'many'}))"
```

Confirmed to print `T2` in this worktree, which is why this dossier owes
01, 02, 03, 05, 06 and 07 and not 04 (`tools/sbe_intake.py`'s `REQUIRED`
table: T2 owes `["01", "02", "03", "05", "06", "07"]`).

## What no command here can prove

Two things, named so this table is not mistaken for full coverage.

First, whether a rejected alternative's stated reason in `03-adr.md` is a
real reason or a restatement of its name is human review; the design
checker measures that the text exists and carries a reviewable length, not
that it reasons correctly.

Second, whether the parity fixtures added for Decision 3 actually cover
every rung a real user hits, versus only the rungs this dossier's authors
thought to fixture, is bounded by the fixture set's own honesty: a rung
with no fixture is a rung this table does not verify, and any such gap
belongs in the wave 2 review report named in `02-process.md`'s handoff
table, not silently assumed closed.
