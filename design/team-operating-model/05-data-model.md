# 05. Data model

Conceptual first (what these things mean and who owns them), then logical (how
they are keyed and related). Physical storage is deliberately thin, because this
round adds no engine code: the shapes below already exist as files in the
repository or as objects in a vendor, and the model's job is to say which is
which.

## Conceptual entities and their meanings

Every entity names the system that owns it. Where an entity is mirrored into a
vendor, the vendor copy is a derived read and is never the owner.

- **WorkItem**: one unit of work with an owner, a reviewer, acceptance criteria
  and a status; system of record: the ProgramLedger.
- **Claim**: an exclusive right to write a declared scope of files for a bounded
  period, held by exactly one driver; system of record: the TaskRegistry.
- **Receipt**: the durable output of a command that actually ran, bound to the
  commit it was earned against; system of record: the EvidenceStore.
- **Approval**: one accountable human saying yes to one change at one commit,
  optionally with an attached condition; system of record: the GitHubEnterprise
  pull request.
- **HandoverPackage**: the written half of a handover (done, in flight, not
  started, open questions) plus the record that it was acknowledged; system of
  record: the TeamVault.
- **Mirror**: a derived read-only copy of ledger state published into a
  coordination surface, carrying the time it was exported; system of record: the
  exporter that produced it, recorded as an event in the ProgramLedger.

## Relationships

| From | To | Cardinality | Rule |
|---|---|---|---|
| WorkItem | Claim | one-to-many, optional | A work item may be claimed many times over its life, but never twice at once |
| Claim | Receipt | one-to-many, optional | Receipts are earned inside a claim; a claim that closes with none is honest and reads as NO-DATA |
| WorkItem | Receipt | one-to-many, mandatory at completion | A work item cannot reach done with zero receipts; absence is never a pass |
| WorkItem | Approval | one-to-one, mandatory at merge | Exactly one named approver per change. Not zero, and not a team standing in for a person |
| Approval | Receipt | one-to-many, optional | An approver may attach conditions whose satisfaction is itself evidenced |
| WorkItem | Mirror | one-to-many, optional | The same work item may be mirrored into Jira, Asana, Confluence and a board at once |
| Mirror | WorkItem | many-to-one, mandatory | Every mirror names exactly one upstream work item. A mirror with no upstream is orphaned and is deleted, not reconciled |
| Claim | HandoverPackage | one-to-one, optional | A claim that outlives its session produces a handover package |
| HandoverPackage | Approval | one-to-many, optional | Open questions in a handover may each be waiting on a different approver |

## Attribute roles

| Attribute | Entity | Role |
|---|---|---|
| id | WorkItem | identifier |
| owner | WorkItem | role reference |
| reviewer | WorkItem | role reference |
| status | WorkItem | status |
| scope | Claim | declared write set |
| holder | Claim | role reference |
| opened_at | Claim | temporal |
| command | Receipt | provenance |
| commit_sha | Receipt | foreign key to the commit |
| verdict | Receipt | status |
| approver | Approval | identifier of a person |
| head_sha | Approval | foreign key to the commit approved |
| condition | Approval | optional text of a conditional yes |
| acknowledged_by | HandoverPackage | identifier of a person |
| acknowledged_at | HandoverPackage | temporal |
| target_system | Mirror | foreign key to a source system |
| exported_at | Mirror | temporal |

## Lifecycle states of a work item

These are the nine steps of 02-process.md, named as states so the rhythm diagram
in 06-diagrams.md traces to them.

- Intake: sized into a tier by the five questions
- DecisionTable: the small, scheduled, terminal decision meeting for T2 and above
- Dossier: the design written and the approver named in it
- Build: pulled from the ready queue under a claim
- Prove: receipts earned by running commands
- ReviewWave: the read-only reviewers plus the human the change class demands
- Converge: the change reconciled against the approved dossier
- Merge: under the platform's own controls, with a named approval bound to the head commit
- Ship: on the release train, with the artifact attested
- Learn: the lesson written into law through a reviewed pull request

An Approval carries its own smaller lifecycle: proposed, then approved or
conditionally approved or rejected, and it is void once the diff changes.

## Historization

Receipts and Approvals are append-only. A correction arrives as a new record, not
as an edit, so a claim made last month can be re-derived exactly as it stood. This
is the same argument Nygard makes for ADRs, that small append-only records survive
where living documents rot
(https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions), applied
to evidence rather than to decisions.

WorkItem is mutable in place, because it is the current state of a thing, and its
history lives in git. Mirror is disposable by design: it is regenerated from the
ledger and carries no state of its own worth preserving. HandoverPackage is
append-only for a specific reason: an acknowledgment that could be edited after
the fact is not evidence that a handover completed.

## Ownership and the direction of authority

| Entity | Owner | Written by | Mirrored into | Can the mirror write back |
|---|---|---|---|---|
| WorkItem | ProgramLedger | A reviewed pull request | JiraCloud, AsanaWorkspace, ProjectsBoard | No |
| Claim | TaskRegistry | The claim command, one writer at a time | Nothing | No |
| Receipt | EvidenceStore | A command that ran | ConfluenceCloud as part of the published status | No |
| Approval | GitHubEnterprise | A human reviewer in the pull request | TeamsTenant as a notification, later as a bot card | No, and this is the load-bearing row |
| HandoverPackage | TeamVault | The outgoing driver | VaultMirror | No |
| Mirror | The exporter | The exporter | Not applicable | Not applicable |

The last column is the ADR restated as data. If any cell in it ever reads yes, the
evidence law has been given up, whatever the rest of the design says.

## Honest limits of this model

- The vault has no per-note access control, no audit log and no single sign-on
  (https://obsidian.md/help/sync/collaborate), so HandoverPackage carries no
  access classification and material needing one belongs elsewhere. Stated here
  rather than solved.
- Union merge on markdown keeps both sides of a same-line edit rather than
  raising a conflict
  (https://forum.obsidian.md/t/team-colaboration/69608), so the model's guarantee
  for vault-resident entities is "additive edits survive", not "conflicts are
  detected". The fence discipline is what closes that gap, and it is a human
  control, not a mechanical one.
- Confluence page metadata is not queryable through the REST API
  (https://confluence.atlassian.com/doc/page-properties-macro-184550024.html), so
  a Mirror published there cannot be read back for reconciliation. Mirrors are
  therefore verified by re-export, not by comparison.
