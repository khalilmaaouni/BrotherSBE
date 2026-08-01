# 07. Verification plan

Every claim this design makes, and the check that would prove it. A row whose
check does not exist yet says so, and names the work item that builds it, rather
than being written as though it already ran.

## Claims about the design itself, checkable today

| Claim this design makes | The check that proves it | When it runs |
|---|---|---|
| This dossier is complete for the tier it declares | `python3 tools/sbe_design.py design/team-operating-model` reports no FAIL | Every change to the dossier |
| The tier raise is a recorded override, not a silent edit | The same check re-derives the tier from the answers and prints the declared override with its reason; a move with any of the three fields missing FAILs | Every change to the dossier |
| Every diagram node names something this dossier declares | The diagrams check traces each node to an entity, a component, a lifecycle state, or a system of record | Every change to the dossier |
| Every relationship in the data model carries a cardinality | The data model check reads each relationship line and FAILs one that carries none | Every change to the dossier |
| The ADR rejects at least two named alternatives and says why each lost | The ADR check counts rejected alternatives and applies a reviewability floor to each reason | Every change to the dossier |
| No artifact is the shipped template with the marker deleted | The placeholder check plus the artifact content floor | Every change to the dossier |
| Nothing written here carries an em dash or an en dash | A dash scan over every file in this change | Before every commit |
| The three exporter work items exist in the ledger with the field shape the ledger uses | The repository's own YAML rules test | Every change to the ledger |

## Claims about the exporters, checkable when they are built

These are contract tests, and they are the acceptance criteria of BR-0520,
BR-0521 and BR-0522. None of them exist yet. That is the honest state, and the
work items carry them rather than this document claiming them.

| Claim | The check that would prove it | Owned by |
|---|---|---|
| An exporter can read the ledger and cannot write it | A test that runs the exporter with a read-only credential and asserts success, plus a test asserting the exporter holds no repository write token | BR-0520, BR-0521, BR-0522 |
| Exporting the same event twice produces one issue, task or card | An idempotency test replaying a fixed event stream twice and diffing the target state | BR-0520, BR-0521 |
| A failed export never blocks a merge | A test that fails the exporter deliberately and asserts the merge path is unaffected | BR-0520, BR-0521, BR-0522 |
| A published Confluence page is readable but not hand-editable | A test asserting the update restriction is set to the publishing identity after publish (https://developer.atlassian.com/cloud/confluence/rest/v1/api-group-content-restrictions/) | BR-0520 |
| Evidence links land on the right Jira issue | A test asserting the URL-typed custom field is populated on an issue created from a known event | BR-0520 |
| An Asana task becomes an approval | A test asserting resource_subtype is approval after the update call, since setting approval_status alone does not convert a task (https://forum.asana.com/t/mark-task-as-approval-via-api/798803) | BR-0521 |
| The Teams notifier uses the Workflows webhook and not a retired connector | A test asserting the configured endpoint is a Workflows trigger URL, plus a payload size assertion under the 28 KB limit | BR-0522 |
| The Teams bot's buttons actually work for the intended approvers | A tenant test asserting an Action.Execute invoke reaches the bot and returns an updated card, run per user group because app policy can block it silently (https://learn.microsoft.com/en-us/microsoftteams/teams-app-permission-policies) | BR-0522 |

## Claims about the merge and release controls

| Claim | The check that proves it | Notes on what it does not prove |
|---|---|---|
| An author cannot approve their own most recent push | The platform's own setting, verified by attempting it | Proves the control is on, not that reviews are good |
| An approval does not survive a material change to the diff | Stale-review dismissal, verified by pushing after approval and observing the dismissal | Proves invalidation, not that the re-review was thorough |
| The right owners are asked for review | CODEOWNERS routing | OR semantics only. Multiple owners on one line means any one of them satisfies it, never all of them (https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners) |
| Gated paths need a minimum number of approvals from a named team | The required-reviewer ruleset rule, GA 2026-02 (https://github.blog/changelog/2026-02-17-required-reviewer-rule-is-now-generally-available/) | This is the only mechanism that gives a count. CODEOWNERS never does, and the design does not claim it does |
| The control file cannot be quietly weakened | CODEOWNERS owns itself, or is owned by repository admins | Proves review is required, not that the reviewer read it |
| Every bypass is countable and attributable | A scheduled read of the rule suites API filtered on result, stored durably (https://docs.github.com/en/rest/orgs/rule-suites) | The general audit log has no bypass event, so a check reading only the audit log would report a false zero |
| A new ruleset does not break the org on the day it lands | Evaluate mode first, then Active after the dry-run window | Proves what would have blocked, not that the rule is right |
| Every released artifact has provenance | `gh attestation verify` in the release path | SLSA Build Level 3 as the platform states it (https://github.blog/enterprise-software/devsecops/enhance-build-security-and-reach-slsa-level-3-with-github-artifact-attestations/) |

## Claims about the human rhythm, and how they are actually observed

These are the weakest rows in the plan and are labeled as such. A process claim
has no unit test. What follows is the signal that would falsify it, which is not
the same as proof.

| Claim | The signal that would falsify it | Honest limit |
|---|---|---|
| The facilitator never touches content | The facilitator appears as an author or committer on a change during a session they facilitated | Observable from git, but a facilitator who dictates rather than types is invisible to it |
| Allocation is by pull, not by push | Items move to a driver before that driver's work-in-progress falls below the limit | Requires the board to record when an item was pulled, which is a field on the board and not a fact in git |
| A work-in-progress breach triggers swarming, not reassignment | The breached column stays breached for more than one working day | Directional only. The term swarming is vendor vocabulary rather than canonical Kanban, and the research says so (r6, open items) |
| Every handover is acknowledged | A handover package with no acknowledgment record, still open after its deadline | Mechanically checkable in the vault, but only records what people wrote down |
| Lessons become law only through a reviewed change | The learned file changes outside a pull request | Fully mechanical, and the strongest row in this table |

## Adoption signals

Whether the model is being used, as opposed to being documented. These are read
as prompts for a retrospective, never as a performance measure, which is what both
DORA's own guidance and SPACE explicitly ask for
(https://dora.dev/guides/dora-metrics/ and
https://www.microsoft.com/en-us/research/publication/the-space-of-developer-productivity-theres-more-to-it-than-you-think/).

| Signal | What it suggests when it moves the wrong way |
|---|---|
| Share of merged changes carrying at least one receipt | Receipts are being skipped, which means the evidence law is decorative |
| Share of work items whose approver is a named person | The named-approver rule has degraded into "the team approved it" |
| Count of NO-DATA verdicts read and acted on | If this goes to zero, either everything is proved or nobody is looking. Check which |
| Bypass count per month, with actor | A rising count is not automatically bad. A count nobody reads is |
| Median age of an open handover item past its deadline | Handover is being written and not acknowledged |
| Number of screens showing a figure with no printed definition and checked date | Any number above zero is a defect |

Delivery metrics are reported with their definitions and the date each was checked
printed beside them, and without tier labels. The elite tier stopped appearing in
DORA's own clustering after the 2022 report, per Google Cloud's own page
(https://cloud.google.com/blog/products/devops-sre/using-the-four-keys-to-measure-your-devops-performance),
so a screen that prints one is repeating folklore.
