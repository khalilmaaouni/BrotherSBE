# 02. Process map

Three waves, run in the order the dependency actually forces: wave 2 reads the
engine fields wave 1 makes truthful, so wave 2 cannot start before wave 1's exit
gate is met. Wave 3 shares no file with either and runs whenever a writer is
free. One writer holds a file at a time; a second writer never edits a file the
first has open.

## Actors

- **The founder.** Ratifies this dossier, answers any founder gate a wave's
  exit criteria raises, and is the one who moves `docs/release-1.0/STATUS.md`
  from `open` to `closed` for each of the five blockers.
- **The design stage.** Wrote this dossier before any writer starts; owns
  `03-adr.md`, `05-data-model.md` and `07-verification.md`, and is the only
  actor allowed to change a decision recorded there mid-wave.
- **The writer stage.** Implements one wave's work items serially, inside a
  fence, through the isolated work path in `src/brothersbe/work.py`, exactly
  as the final-release-program dossier's writer stage does.
- **The review stage.** Reads a finished wave and tries to disprove its exit
  gate, never to confirm it, mirroring `design/final-release-program/02-process.md`'s
  own instruction to the review stage.
- **CI required checks.** `tools/sbe_design.py --strict`, `tools/sbe_gate.py
  --strict`, `tools/sbe_score.py --strict --strict-waivers`, `evals/run_evals.py`,
  plus the suite each wave names below, all run on every merge, per
  `.github/workflows/brothersbe-gates.yml`.

## Waves

| # | Wave | Lane(s) | Files touched (exclusive per lane) | Exit gate |
|---|---|---|---|---|
| 1 | Engine semantics | **Status lane** (CR-06): `src/brothersbe/status.py` only. **Verify lane** (CR-08): `src/brothersbe/cli.py`, `src/brothersbe/evidence.py` only. | Disjoint files, dispatched to isolated worktrees so neither writer's uncommitted diff is visible to the other. | `python3 tools/test_sbe_status.py` and `python3 tools/test_sbe.py` pass; `python3 evals/test_no_data_class.py` still reports empty-dir NO-DATA for every gate; single-project `sbe status . --json` on a fixture with a nested dossier reports the dossiers the team walker finds (Decision 1); a default `sbe verify` run on a clean fixture mints three kind-tagged receipts and `sbe status`'s MISSING EVIDENCE for that fixture is empty (Decision 2) |
| 2 | Skills lane | CR-07 and CR-10, one decision: `skills/next/SKILL.md`, `skills/verify/SKILL.md`, `skills/status/SKILL.md`, `skills/start/SKILL.md`. | Cannot start until wave 1's exit gate is met on the branch this wave forks from: the skills read `nextAction`, `notes` and `scope.storesInspected`, and those fields are not truthful about a nested dossier or a default verify run until wave 1 lands. | A parity fixture set (added to `python3 tools/test_sbe_status.py` or a sibling) asserts each guided skill's answer equals `sbe status --json`'s `nextAction` for the same fixture; rung 5 of `skills/next/SKILL.md` takes the NO-DATA branch and does not recommend `/brothersbe:verify` on a fixture where four gates are legitimately NO-DATA and `missingEvidence` is empty for the declared tier |
| 3 | Install proof | CR-03: `install.sh`, `tools/test_sbe_install.py`, a new installed-layout hook-firing test beside `tools/test_sbe_fence_hook.py`. | Shares no file with wave 1 or wave 2; can be dispatched whenever a writer is free, including concurrently with wave 1. | `python3 tools/test_sbe_install.py` passes, including a fixture asserting `run_doctor` grades `$TARGET`; a new test parses installed `hooks/hooks.json`, substitutes `CLAUDE_PLUGIN_ROOT`, and replays the PreToolUse fence contract per the harness at `tools/test_sbe_fence_hook.py:572-601`; a space-in-`SCRIPT_DIR` fixture passes with `git` and `claude` stubbed on `PATH` |

Wave 1's two lanes are dispatched together because they are independent (no
shared file, no shared runtime state: CR-06 is a read path over dossiers, CR-08
is a write path into the evidence store) and because both are prerequisites for
wave 2. Running them serially would only lengthen the critical path to wave 2
with no isolation benefit gained.

## Handoffs

| From | To | What is handed over | Contract |
|---|---|---|---|
| The design stage | Wave 1 writers | This dossier, with `03-adr.md` Decisions 1 and 2 approved | Neither writer starts until both decisions are approved; a decision question raised mid-wave stops that lane rather than being decided in the code |
| Wave 1 writers | Wave 2 writer | A merged commit on which `sbe status --json` reports nested dossiers and a default `sbe verify` mints receipts | Wave 2 does not fork until this is true on the branch it forks from; forking earlier means the skills would be written against fields that are still lying |
| Wave 1 and 2 writers | CI required checks | A candidate commit and the receipts earned for it | Every receipt is produced by the evidence wrapper (Decision 2), bound to the commit it was earned on; no receipt is hand written into a fixture |
| CI required checks | The review stage | A verdict set, with absence reported as NO-DATA rather than as a pass, exactly as `design/final-release-program/02-process.md` already requires of the gate battery | A NO-DATA is never read as a pass |
| The review stage | The founder | A report naming what was proved, refuted, and what remains unverified, per wave | Anything not verified is listed by name |
| The founder | `docs/release-1.0/STATUS.md` | The state change from `open` to `closed` for the blocker(s) a wave closes | The STATUS.md table is the one place the state lives; this dossier does not duplicate it |

## Reviewers are read-only

No reviewer of any wave holds write access to the files that wave's writer
owns. A reviewer's job, per `design/final-release-program/02-process.md`'s own
actor table, is to read the finished wave and try to refute its exit gate; a
reviewer who can also edit the file under review is the exact defect that
principle exists to prevent, and the comment directly above
`DEFAULT_EVIDENCE_DIR` in `src/brothersbe/tasks.py:93-96` ("a reviewer may not
own any path under this, and a reviewer whose diff touches it cannot close
even with --force") is the mechanism already in the codebase that enforces
the equivalent rule for evidence review.
