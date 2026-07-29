---
name: review
description: Use when reviewing a diff, a pull request, or a colleague's change against the design it claims to implement. Compares the implementation with the dossier and the intake, runs the lints, and returns severity-split findings where a Critical blocks the merge. Invoke as /brothersbe:review.
---

# Review

Read `${CLAUDE_PLUGIN_ROOT}/SKILL.md`, then
`${CLAUDE_PLUGIN_ROOT}/references/laws-closing-and-review.md` (L17 to L19).

## What a review is pointed at

Aim matters more than effort here: an independent code review has found a Critical that six
adversarial rounds missed, because it was pointed at the contract rather than at execution
edges. So review in this order:

1. The **contract**: does the change do what the purpose brief and the ADR said it would, and
   does it break anything downstream that depends on the old shape.
2. The **design fidelity**: where the implementation and the dossier disagree, one of them is
   wrong. Name which.
3. The **execution edges**: concurrency, idempotency, transaction boundaries, error paths,
   retries, partial failure, duplicate delivery.
4. The **evidence**: was the figure checked, was the migration rehearsed forward and back, was
   the approval real, did the command actually run.

## Mechanical passes to run before writing the review

```
python3 "${CLAUDE_PLUGIN_ROOT}/tools/sbe_score.py" --strict --strict-soft <dir>
python3 "${CLAUDE_PLUGIN_ROOT}/tools/sbe_gate.py"  <dir>
```

The silent-failure lints inside the score run catch bare excepts, except-then-pass, discarded
subprocess results, conflict-skipping upserts and force-tries. A line carrying
`# sbe: allow-silent <reason>` is exempt and the reason is read, so an exemption is visible in
the diff rather than an off switch.

## Specialized reviewers

For a change with real surface area, dispatch the read-only agents that ship with this plugin
rather than doing every lens yourself: `backend-reviewer`, `data-reviewer`, `qa-reviewer`,
`security-reviewer`, `migration-reviewer`, `principal-architect`, and `evidence-auditor`. They
are read-only on purpose. The evidence auditor in particular must never generate the evidence
it audits.

## Output shape

Severity-split, each finding naming a file and a line, each with the failure it produces
rather than an adjective. Critical blocks the merge. A review that found nothing says so and
names what it examined, because an unexamined area and a clean area are not the same result.
