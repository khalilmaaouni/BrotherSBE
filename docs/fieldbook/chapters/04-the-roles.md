---
slug: the-roles
title: The reviewer roles
part: "2"
verified-against: 1.0.0-rc.28
---

# The reviewer roles

When a change needs a second pair of eyes, BrotherSBE dispatches a reviewer
with a narrow brief rather than asking one general reviewer to think about
everything. The selection is deterministic: `sbe review-route` reads the diff
and picks the roles, so no model decides who reviews what.

Read the **Tools it may use** column carefully, because it is the whole
argument. Every reviewer is read-only: `Read, Grep, Glob, Bash` and nothing
else, so a reviewer cannot edit what it finds. Exactly one role in the table
holds `Edit` and `Write`, and it is `implementation-worker`, which writes code
and reviews nothing.

That separation is structural rather than a matter of instruction. The agent
that writes the work never reviews the work.

<!-- BEGIN GENERATED FIELDBOOK roles -->

| Role | What it is for | What it covers | Tools it may use |
|---|---|---|---|
| `backend-reviewer` | Read-only backend change review | Use when a service, API, endpoint, queue consumer or transactional path changes. Covers contract compatibility, idempotency, concurrency, transaction boundaries, error paths, retries, observability and performance. | [Read, Grep, Glob, Bash] |
| `data-reviewer` | Read-only data and warehouse change review | Use when a data model, SQL transformation, dbt model, pipeline or reported figure changes. Covers grain, joins and fan-out, keys, systems of record, historization, reconciliation, freshness, quality and cost. | [Read, Grep, Glob, Bash] |
| `evidence-auditor` | Read-only audit of evidence provenance | Use when a receipt, a gate verdict, a test result, a rehearsal identifier or an approval is being relied on. Its job is to try to disprove the evidence, not to confirm it. It must never generate the evidence it audits. | [Read, Grep, Glob, Bash] |
| `implementation-worker` | Implementation worker for one sbe work brief | Use when a plan task has already been briefed (`sbe work brief`) and someone needs to write the code, not review it. Reads the brief, edits only inside its declared scope, runs the named verification, and returns a compact result contract. It is not a reviewer, never approves or blocks anyone else's change, and holds no merge, rebase, push or deploy rights of its own. | [Read, Grep, Glob, Edit, Write, Bash] |
| `migration-reviewer` | Read-only database migration review | Use when a schema migration, backfill or destructive data operation is part of a change. Covers forward and reverse evidence, expand and contract compatibility, lock duration, mixed-schema deployment and rollback time. | [Read, Grep, Glob, Bash] |
| `principal-architect` | Read-only architecture review | Use when a system boundary, a service split, a technology choice or a reversibility question is on the table, or when an ADR needs a second opinion before it is committed to. Returns a recommendation, the first and second alternative, and what would flip it. | [Read, Grep, Glob, Bash] |
| `qa-reviewer` | Read-only test coverage and traceability review | Use when a change is about to be called testable or done. Maps requirements and acceptance criteria to executable tests, finds missing negative and non-functional coverage, and validates that the test evidence says what it is claimed to say. | [Read, Grep, Glob, Bash] |
| `security-reviewer` | Read-only security and privacy review | Use when authentication, authorization, partner APIs, money movement, file upload, secrets, dependencies or personal data are touched. Covers threat model impact, authorization coverage, secret exposure, input validation, data classification and audit logging. | [Read, Grep, Glob, Bash] |

<!-- END GENERATED FIELDBOOK roles -->

## Why read-only matters more than it sounds

A reviewer that can edit will fix what it finds, and a finding that gets fixed
in silence is a finding nobody recorded. Worse, an agent that both writes and
reviews has every incentive to review kindly. Splitting the two is the
cheapest control in the whole system.

The same logic runs through `evidence-auditor`: its job is to try to disprove
a receipt, not to confirm it, and it is forbidden from generating the evidence
it audits.

## What a review verdict has to name

A review verdict counts only when it names the falsification that was actually
executed: the command that was re-run, the defect that was reproduced, the
number that was re-derived. Reasoning on its own is NO-DATA, not a finding.

That rule is graded at the weekly review and nothing parses a verdict, so it
is a discipline rather than a control, and it is listed among the honest
limits for exactly that reason.

## Where deterministic beats model

Before any model is asked to judge work, the deterministic check is tried
first: a command, a grep, a diff, a schema match. The record then names which
one answered. A model asked to eyeball something a grep could have settled is
a slower, less reliable grep.
