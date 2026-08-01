# 03. Architecture decision record

## Context

An enterprise team already runs its coordination on Jira, Confluence, Asana,
Microsoft Teams and GitHub. BrotherSBE's whole value is that a claim without a
receipt is not a pass, and that law only holds while git remains the single source
of truth. The two facts are in tension: the organization looks at the boards, and
the truth lives in the repository.

Something has to define the direction of authority between them, once, before any
exporter is written. Every later integration inherits that decision, and an
integration built on the wrong direction cannot be corrected by writing it more
carefully.

The relevant vendor facts are settled and are not in dispute here. Jira, Asana and
Confluence all expose write APIs an external system can drive. Jira Automation and
Confluence Automation both expose incoming webhook triggers that let an external
system start a flow inside the vendor
(https://support.atlassian.com/cloud-automation/docs/configure-the-incoming-webhook-trigger-in-atlassian-automation/).
Jira Automation's "Send web request" action is the outbound half, able to POST
anywhere. Asana's webhooks can be filtered narrowly, down to a specific field on a
specific resource subtype
(https://developers.asana.com/docs/webhooks). The capability to build two-way sync
is fully present. The question is whether to use it.

## Criteria

The decision is judged on five things, in this order.

1. **Survival of the evidence law.** After the integration exists, is it still
   true that nothing changes without a commit, a receipt, and an approver?
2. **Auditability.** Can an auditor point at one system and get a complete,
   attributable record of who decided what and when?
3. **Failure blast radius.** When the integration breaks, what is the worst thing
   that happens?
4. **Network and governance posture.** Does it require inbound ports, a public
   receiver, or a tenant-admin grant before anything works at all?
5. **Cost to build and to keep running.** Two engineers can maintain it, or they
   cannot.

## Options considered

### Rejected: two-way live sync with the boards

Let the boards write back. A Jira transition moves the ledger; an Asana approval
resolves the approval gate; a Teams button closes a work item. The vendor
machinery for this exists and is documented, so this is not rejected as
impossible.

It loses on criterion one, immediately and permanently. The moment a board can
change ledger state, a status can move with no commit behind it, and every
downstream claim built on that ledger becomes unfalsifiable. The receipt stops
being the thing that decides, and the tool has spent its only real property to buy
convenience.

It loses on criterion two as well. With two writers there is no single record: an
auditor asking "who changed this" gets an answer that depends on which system they
ask, and reconciling the two is a research project rather than a query.

It loses on criterion three in a way that is easy to underrate. A one-way exporter
that fails leaves a stale board and a correct repository, which is annoying. A
two-way sync that fails leaves two divergent truths, and there is no rule that
says which one wins. Conflict resolution then has to be designed, staffed, and
audited, which is a larger system than the one being integrated.

It also loses on criterion four for a large fraction of real deployments: inbound
sync needs a public receiver the vendor can reach, which many regulated networks
will not permit. Atlassian ships the Development Information API specifically for
tools behind the firewall pushing outbound with no inbound ports opened
(https://developer.atlassian.com/cloud/jira/software/integrate-jsw-cloud-with-onpremises-tools/),
which is a strong signal about which direction is the supported one.

### Rejected: build the whole model inside a single vendor suite

Pick one vendor and live there. Put the dossier in Confluence, the work items in
Jira, the approvals in Jira Service Management's change workflow, the discussion
in Teams, and treat the repository as an implementation detail. This is the option
an enterprise architect proposes first, and it is not unreasonable: the controls
exist, the auditors know them, and there is no integration to build.

It loses on criterion one, differently but just as completely. A wiki page is not
a receipt. The evidence law depends on artifacts that diff, review, and replay,
and on checks that can run against them and fail. Confluence's own Page Properties
metadata is not exposed as queryable data through the REST API
(https://confluence.atlassian.com/doc/page-properties-macro-184550024.html), so a
design recorded there cannot be mechanically checked for completeness at all. A
design that cannot be checked is a design that goes stale, which is precisely the
weakness Google's own design-doc practice admits to and the ADR format was
invented to fix (https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

It loses on criterion five over any horizon longer than the first quarter. It
binds the operating model to one vendor's roadmap and pricing, and the evidence
base contains a concrete example of what that costs: the Microsoft 365 connector
that a naive Teams integration would have been built on is being retired, with the
final rollout window 2026-05-18 to 2026-05-22
(https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/what-are-webhooks-and-connectors).
A model that lives inside a vendor surface dies when the surface does.

It loses on criterion three because the blast radius becomes the vendor's
availability. When the suite is down, the team cannot design, decide, or record,
rather than merely being unable to broadcast.

## Decision

We adopt the one-way broadcast ledger.

Git plus the ProgramLedger, the TaskRegistry and the EvidenceStore hold the truth.
Every coordination surface (Jira, Confluence, Asana, Microsoft Teams, GitHub
Projects) is fed FROM that truth by exporters that hold read access to the ledger
and write access only to the vendor. The ledger broadcasts; it never obeys.

Inbound change happens through exactly one channel: a pull request, reviewed and
approved under the platform's own merge controls. No webhook, no bot, no board
automation holds any credential that can write to the repository. Where an
approval genuinely has to happen in a vendor surface, the vendor enforces it in
its own workflow and the exporter drives the ordinary transition; there is no
separate approvals API to build, because Jira's approval gate simply makes the
transition unavailable until approvals resolve
(https://support.atlassian.com/jira-service-management-cloud/docs/designate-your-approvers/).

The knowledge plane sits alongside, not in between: the team vault is async
working memory, and what the organization reads is a published read-only mirror,
not the vault itself.

## Consequences

The good ones first, then the ones that will actually be complained about.

- The evidence law survives contact with enterprise tooling. Every state change
  still has a commit, a receipt, and an approver behind it, and that sentence
  stays true no matter how many boards are connected.
- The audit trail is single-system and maps onto controls an auditor already
  knows, rather than a parallel compliance vocabulary nobody has seen.
- Exporters are small and independently failable. Each one reads an append-only
  stream and writes to one vendor, so a broken exporter is a stale board and
  nothing worse. None of them can block a merge.
- No inbound ports, no public receiver, no tenant-wide write grant into the
  repository. This is the posture Atlassian's own on-premises bridge assumes.

And the costs, stated plainly:

- **The boards lag.** A board reflects the ledger as of the last export, not as of
  now. Anyone reading a board is reading a mirror, and the mirror says so.
- **People will ask to close a ticket from the ticket.** The answer is no, and it
  will be unpopular. Closing happens by merging.
- **Approval buttons in Microsoft Teams require a real bot.** An incoming webhook
  cannot render a working button; the Workflows-based replacement states outright
  that button rendering is not supported
  (https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook),
  and only a bot using Adaptive Card Universal Actions can do it
  (https://learn.microsoft.com/en-us/microsoftteams/platform/task-modules-and-cards/cards/universal-actions-for-adaptive-cards/overview).
  So notify-now and approve-later are two different integrations with two
  different governance stories, and stage 3 carries a tenant app-governance step.
- **Duplicate state exists.** The same work item is a ledger row and a Jira issue.
  That is accepted deliberately: one of them is derived, always the same one, and
  the derivation is one way, which is what makes the duplication safe.
- **Someone has to own the exporters.** Three ledger rows exist for them
  (BR-0520, BR-0521, BR-0522) precisely so that ownership is a work item and not
  an assumption.

## What would flip this

Three conditions, any one of which reopens the decision.

1. A vendor ships a mechanism by which an inbound change can be made to produce a
   real commit with a real approver and a real receipt, without the repository
   trusting the vendor. Concretely: the inbound path opens a pull request rather
   than mutating state. If that exists and is auditable, the two-way rejection is
   worth re-examining, because the objection was never to the direction as such,
   it was to unfalsifiable state.
2. The organization mandates that a specific control (a change advisory board
   approval, most likely) is legally the system of record and cannot be derived.
   In that case the boundary moves: that one control moves into the vendor as the
   authoritative record and the ledger mirrors it inward as evidence, which is the
   exact inversion this ADR rejects and would need its own superseding record
   naming its scope.
3. Exporter maintenance exceeds what the platform team can carry, and the drift
   between ledger and board becomes routine rather than exceptional. At that
   point the honest move is fewer integrations, not two-way sync, and this record
   would be superseded by one that says which boards stop being fed.

Per the ADR discipline, this record is not edited when the decision changes. It is
superseded by a new numbered record that references it.
