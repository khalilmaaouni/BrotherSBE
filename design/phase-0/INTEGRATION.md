# Phase 0 integration checklist

Owned by the orchestrator. Every line is a check the orchestrator RE-RUNS itself;
a lane's own green line is a claim, not evidence. Written 2026-08-06 while the
lanes were still writing, so the checks were fixed before their results were
known.

## Before folding anything in

1. `git -C <lane worktree> status --short` shows ONLY the two fenced files.
   Anything else is a boundary violation: reject the lane back, do not patch it.
2. `git -C <lane worktree> log --oneline -1` still reads b54a543. A worker that
   committed broke the rule that workers never commit.
3. Read the full diff of both lanes as a hostile reviewer, not as the person who
   wants them to pass.

## Real-data parsing, the known integration risk for lane A

The lane's tests were written against the ledger as it stood at b54a543. The
ledger changed under it (nine new items, a milestones block, a plan_waves block),
which is exactly the collision the orchestrator predicted in BR-1000's risk list.
Verify each of these against the MERGED tree, not the lane's worktree:

4. A test asserting an exact item COUNT against the live ledger now fails. That is
   the lane's defect to fix (assert shape, not counts) or the orchestrator's to
   reject back with the gap named. Never delete the assertion to get green.
5. `BR-0201.yaml` contains a multi-line plain scalar inside a list item
   (continuation lines under `risks:`). Confirm it parses into one joined string
   and not into a truncated first line or a parse error.
6. Shipped items carry an `acceptance_notes` key that the spec never listed.
   Confirm an unknown key does NOT raise a parse error, because refusing unknown
   keys would refuse the repository's own real data.
7. `status: not started` (space) and `status: not_started` (underscore) both exist
   in shipped items, as do `partially done` and `in_progress`. Confirm all four
   normalize to one value each and that an unrecognized status still raises a
   named parse error.
8. Confirm every one of the sixteen work items loads: seven shipped plus nine new.

## The honesty properties, checked by hand

9. Feed the reporter an item with `status: in_progress`, no `percent_complete`,
   and no `acceptance_met`. It must report "not measured" and contribute NOTHING
   to any aggregate. If a fifty appears anywhere, that is the defect the spec
   forbids by name.
10. Confirm an aggregate states its coverage ("N of M items measured").
11. Delete `program/OWED.json` in a scratch copy and run the dispatch gate's
    loop-open. It must REFUSE as NO-DATA. If it passes, the control is inverted
    and the lane is BLOCKED.
12. Hand the dispatch gate a brief missing four required fields. It must name all
    four in one run, not the first one only.
13. Hand it `model_tier: claude-opus-5`. It must refuse and explain that routing
    is by capability profile.

## Wiring the orchestrator owns

14. `src/brothersbe/cli.py`: register `program` with `status` and `check`
    subcommands, mirroring how `_cmd_status` and `_cmd_map` are registered. The
    lanes were forbidden from touching this file.
15. `evals/run_evals.py`: add the STATUS.md drift case, so a stale committed
    artifact fails the release gate. Adding a case moves baked counts.
16. THE COUNTS LAW: run the evals and copy the number they print into any
    document that states it. Never predict a count.

## The battery, run after the last edit, quoted in the commit

```
python3 tools/test_sbe_program.py
python3 tools/test_sbe_dispatch.py
python3 tools/test_sbe.py
python3 evals/run_evals.py
python3 tools/sbe_score.py --strict --strict-soft
python3 -m py_compile src/brothersbe/program.py tools/sbe_dispatch.py
```

17. Dash scan over every new and edited file: zero matches.
18. Secret scan over the staged diff before any commit.
19. Explicit-path staging only, then `git status` confirms exactly the intended
    set (founder rule 5a897729).
20. Regenerate `program/STATUS.md`, then run `sbe program check` and confirm it
    exits 0 on a fresh render and 1 on a stale one.
