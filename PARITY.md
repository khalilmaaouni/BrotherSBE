# Parity with BrotherModeUp

BrotherSBE is a standalone skill: clone it, and it works with nothing else installed. It is the domain specialist sibling of BrotherModeUp (github.com/khalilmaaouni/BrotherModeUp), the general orchestrator. This file names what the two intentionally share, so a fix to a shared mechanism gets ported by hand rather than drifting.

## Shared mechanics (ported, kept in sync by hand)

| Mechanism | Where | Note |
|---|---|---|
| Session-start digest injection | tools/sbe_sessionstart.sh, DIGEST.md | Same hook shape; the digest content is BrotherSBE's own laws. |
| Autosave before compaction | tools/sbe_autosave.sh | Same behavior: snapshots the worktree to a private ref, never pushes. The IMPLEMENTATIONS have diverged on purpose and this row says so rather than leaving "same behavior" to imply otherwise: the sibling rewrote its autosave in Python because Windows is ratified scope there and a shell script does not run on Windows, while BrotherSBE stays POSIX shell and scopes Windows out (README.md, "A POSIX shell for the two `sh` tools. Linux and macOS are what CI runs; Windows is untested"). Behavior is shared; the platform set is not. |
| Idempotent hook-written telemetry | tools/sbe_telemetry.py | Same append-dedup discipline that fixed the sibling's duplicate-flush bug. |
| Code-graded weekly review | tools/sbe_score.py, tools/WEEKLY-REVIEW.md | Shared check set (ledger coverage, fence hygiene, correction latency, review cadence, budget tags) plus BrotherSBE's silent-failure lints. |
| Five-field fence contract | STATE.template.md | Same objective, output, tool-guidance, boundaries, termination shape. |
| Corrections privacy regime | SECURITY.md, purge-corrections | Same redaction, 0600, retention, purge. |
| Honesty conventions | throughout | NO-DATA is never a pass; not-measured over fiction; bad news first. |

## Where BrotherSBE deliberately diverges

- Operator register: engineer peer-to-peer, not a non-engineer principal. The sibling's narration law is replaced (SKILL.md, "The spine").
- Alignment metric: primarily review outcomes and the deploy and incident record, not a felt-outcome rating outranking or substituting for them (RUBRIC.md metric 4). Felt ratings are still collected and scored (`tools/sbe_score.py`'s felt-outcome-ratings check, gathered per `tools/WEEKLY-REVIEW.md`), but an engineer verifies alignment directly, so an impression-based feed is never allowed to let charm outrank correctness.
- The four hard gates and the eval bed (tools/sbe_gate.py, evals/): BrotherSBE-only. This is the specialization.
- Team learning through reviewed pull requests into LEARNED.md (SKILL.md, "What is not law"): the sibling assumed a single operator.
- Multi-thread orchestration (the sibling's `tools/bm_store.py` and `tools/bm_threads.py`): BrotherSBE has no equivalent and is not getting one. It is invoked as a single session per task, so it keeps no persistent thread registry and no sqlite store (`grep -rl sqlite3 tools/` returns nothing here). The sibling's thread-identity race fix and its sqlite handle-leak fix therefore do not apply, and a reader who goes looking for them here is looking for the fixes to a subsystem this repo does not have. Named so their absence reads as a decision rather than as a missed port.
- The lazy core (SKILL.md's routing table and `references/`): ported from the sibling, with one divergence. The sibling's core keeps a summarized safety floor; BrotherSBE's keeps three whole laws (L6, L11, L14) verbatim, on the rule that a law stays always-on when its trigger is a condition the work can already be inside without having noticed. MANIFEST-extraction.md records the split and its character reconciliation.

## Porting rule

When a shared mechanism is fixed in either repo, port it to the other in the same week and note it here. The two repos evolve at their own pace; only the rows above are contractually shared.
