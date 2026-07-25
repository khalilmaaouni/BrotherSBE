# Parity with BrotherModeUp

BrotherSBE is a standalone skill: clone it, and it works with nothing else installed. It is the domain specialist sibling of BrotherModeUp (github.com/khalilmaaouni/BrotherModeUp), the general orchestrator. This file names what the two intentionally share, so a fix to a shared mechanism gets ported by hand rather than drifting.

## Shared mechanics (ported, kept in sync by hand)

| Mechanism | Where | Note |
|---|---|---|
| Session-start digest injection | tools/sbe_sessionstart.sh, DIGEST.md | Same hook shape; the digest content is BrotherSBE's own laws. |
| Autosave before compaction | tools/sbe_autosave.sh | Same behavior: snapshots the worktree to a private ref, never pushes. |
| Idempotent hook-written telemetry | tools/sbe_telemetry.py | Same append-dedup discipline that fixed the sibling's duplicate-flush bug. |
| Code-graded weekly review | tools/sbe_score.py, tools/WEEKLY-REVIEW.md | Shared check set (ledger coverage, fence hygiene, correction latency, review cadence, budget tags) plus BrotherSBE's silent-failure lints. |
| Five-field fence contract | STATE.template.md | Same objective, output, tool-guidance, boundaries, termination shape. |
| Corrections privacy regime | SECURITY.md, purge-corrections | Same redaction, 0600, retention, purge. |
| Honesty conventions | throughout | NO-DATA is never a pass; not-measured over fiction; bad news first. |

## Where BrotherSBE deliberately diverges

- Operator register: engineer peer-to-peer, not a non-engineer principal. The sibling's narration law is replaced (SKILL.md, "The spine").
- Alignment metric: review outcomes and the deploy and incident record, not a felt-outcome rating (RUBRIC.md metric 4). An engineer verifies alignment directly, so an impression-based feed would let charm outrank correctness.
- The four hard gates and the eval bed (tools/sbe_gate.py, evals/): BrotherSBE-only. This is the specialization.
- Team learning through reviewed pull requests into LEARNED.md (SKILL.md, "What is not law"): the sibling assumed a single operator.

## Porting rule

When a shared mechanism is fixed in either repo, port it to the other in the same week and note it here. The two repos evolve at their own pace; only the rows above are contractually shared.
