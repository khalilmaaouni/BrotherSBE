# BR-1009 design note: sbe watchdog

Binding for the implementation, whoever writes it (this session or a
successor adopting the fence). Ratified policy: docs/PRINCIPLES.md section 7.
Acceptance contract: program/work-items/BR-1009.yaml, 12 rows. Mirror:
tools/sbe_dispatch.py, the newest sibling, including its say() discipline and
its exit codes (0 clean, 1 finding, 2 usage).

## The one-sentence spec

A read-only command that answers the fixed question list (A boundaries, B
worker commits, C stall, D main-tree hygiene, E dashes, F spend vs declared
budget, G state vs owed register consistency, H the blocker audit) from what
is recorded on disk, silent on clean, one JSON finding plus a one-line human
summary on failure, with its mode (in flight, idle) auto-detected from the
fence registry rather than told to it.

## Sources, and only these

1. STATE.md fence blocks: a fence is OPEN when a "### Fence:" heading is not
   followed by a LANDED/closed/transferred marker in its block. Parse
   structurally (heading plus its bullet block), never by keyword-in-prose,
   which is how the session prompt's grep produced two false hits on the
   policy's own wording.
2. program/OWED.json, already schema-fixed, read exactly as sbe_dispatch reads
   it (share the loader if importable without a new coupling; else mirror its
   refusals verbatim: absent file is NO-DATA, JSON null cannot forge the
   sentinel).
3. The worktrees a fence names: git status via subprocess with checked
   results (the lint runs on this tool too).
4. Declared budget lines in the fence block ("budget NNNk declared").
5. NOTHING else. No network, no engine state files in v1: an engine run
   always coexists with an open fence under the fence-then-dispatch law, so
   fences alone decide the mode honestly. Recorded as a KNOWN LIMIT in the
   tool docstring: a workflow run outside any fence is invisible to v1, and
   that condition is itself a fence-law violation the audit cannot see.

## Verdict semantics, the non-negotiables

- Absent STATE.md, or STATE.md with zero fence blocks ever recorded, is
  NO-DATA (exit 1 with the NO-DATA sentence), never "clean": mirrors the
  dispatch gate's owed-file rule, and it gets its own calibrated test.
- A worktree a fence names that does not exist on disk: finding (stalled or
  prematurely pruned lane), not a crash, not a skip.
- Question H heuristic, v1 scope stated honestly: flag lines in the LAST 60
  STATE.md lines matching waiting/pending/awaiting/"when work resumes" that
  are not inside a LANDED block and not on the founder-only list (tag, human
  gates, credentials, decision window, another estate's channel, telemetry
  line). H findings are alarm class. The heuristic is textual and will
  under-catch; that limit is printed in the finding's evidence line, never
  hidden.
- Read-only proven, not promised: the suite snapshots the tree (file list
  plus mtimes plus hashes of STATE.md and OWED.json), runs the tool, asserts
  byte-identical. Calibrated by making the tool write one byte and watching
  the test fail.
- Cadence lives in tools/watchdog-config.json (shipped defaults 20 and 60);
  the tool only REPORTS the configured cadence; scheduling stays with the
  session cron or CI. Arming-by-default lands with the SessionStart hook at
  integration, wired by the orchestrator, opt-out recorded in the config
  file as {"armed": false, "opt_out_reason": "..."} and REPORTED whenever
  the tool runs with it set.

## CLI

  sbe_watchdog.py audit [--root PATH] [--json]     the full question list
  sbe_watchdog.py mode  [--root PATH]              prints in-flight or idle plus why

Exit: 0 clean (silent unless --json), 1 any finding or NO-DATA, 2 usage.

## Done-checks (the fence's check line)

  python3 tools/test_sbe_watchdog.py                     OK, every load-bearing
                                                        test calibrated
  python3 evals/test_no_data_class.py                    0 failures (this tool
                                                        registers its checks)
  the workflow-copied battery                            green before any push
