# 02. Process map

The rhythm is nine steps. It is the same rhythm a solo driver already runs; what
changes at team scale is that some steps gain a second person and every step
gains a broadcast.

## Actors

Human and machine, named once so the steps below can refer to them without
re-explaining.

- **Driver.** The one writer per file, human or Claude session. The only role that
  touches content. Holds a claim in the TaskRegistry for the duration.
- **Facilitator.** Keeps rhythm, timeboxes, work-in-progress limits and
  psychological safety. Touches no content, ever. Rotating human at team scale.
  The role is lifted from mob programming, where the facilitator's job is
  explicitly not technical (https://cucumber.io/blog/bdd/five-roles-in-a-healthy-mob/).
- **Named Approver.** Exactly one accountable approver per change, named in the
  dossier before implementation starts. The pattern comes from Squarespace's RFC
  process, where naming approvers is what makes the decision right unambiguous
  (https://engineering.squarespace.com/blog/2019/the-power-of-yes-if).
- **Review wave.** The seven read-only reviewer agents, plus whichever human
  reviewer the change class demands.
- **Scribe.** Mechanical. Session records and telemetry are hook-written. Humans
  never transcribe.
- **Incident mode.** When production is on fire the roles split the way Google SRE
  splits them: one state-holder (incident commander), one comms voice, one
  planner, and the operations group as the only writer
  (https://sre.google/sre-book/managing-incidents/).
- **Machine actors.** The ProgramLedger, the TaskRegistry, the EvidenceStore, the
  DesignCheck, the exporters, and the boards. All declared in 04-technology-map.md.

## Steps

| # | Step | Actor | Trigger | Exception path |
|---|---|---|---|---|
| 1 | Intake sizes the change into a tier | Driver | A board item is pulled, or `sbe start` is run | An answer outside the accepted vocabulary is refused by name, not guessed; nothing is written. Tiers argue UP only: a raise is recorded as an override with all three fields set, a lowering is refused |
| 2 | Decision table for T2 and above | Named Approver, Driver, Facilitator, one domain expert | The tier computes T2 or higher | No decision in the room: the item returns to intake with the open question named and owned. There is no open-invite design meeting to escalate to |
| 3 | Dossier written, sized by tier, approver named in it | Driver | The decision is made | A missing or empty artifact FAILs the DesignCheck and blocks the plan; a dossier that shares no subject with itself FAILs as filler |
| 4 | Build, pulled from the ready queue | Driver | The driver's work-in-progress is below the limit | Limit breached: the team swarms the blockage before anyone pulls new work. No manager reassigns anything (r6 finding 5) |
| 5 | Prove: receipts written by running commands | Driver | A task claims to be finished | A command that did not run leaves NO-DATA. NO-DATA is read honestly and is never a pass. A hand-typed receipt is a defect, not a shortcut |
| 6 | Review wave, then convergence against the approved dossier | Review wave, Driver | The change is proposed | A finding survives refutation: the change returns to build. Convergence drift against the dossier is a FAIL, not a note |
| 7 | Merge under the four SOX-familiar mechanisms | Named Approver, MergeQueue | Convergence is clean | Self-approval on the most recent push is refused by the platform. A new push dismisses stale approvals. A bypass is permitted, recorded, and appears on the compliance screen with the actor named |
| 8 | Ship on the release train, artifacts attested | MergeQueue, ReleaseTrain, AttestationSigner | The train cutoff | Work that misses the cutoff rides the next train and does not block this one. A failed attestation blocks the release, not the merge |
| 9 | Learn: lessons become law through a reviewed pull request | Driver, Named Approver | A failure or a finding worth keeping | A lesson written only into a chat thread or only into the vault is not law. Law lives in the reviewed file, and nothing else spreads between installs |

Steps 1 through 9 are also the lifecycle states declared in 05-data-model.md, so
the rhythm diagram in 06-diagrams.md traces to them.

## Handoffs and their contracts

A handoff is a contract, not a notification. Each row below names what crosses
and what the receiver is entitled to assume.

| From | To | What is handed over | Contract |
|---|---|---|---|
| Board (Jira or Asana) | Driver | A work item reference and its acceptance criteria | The board's item is an input, never an instruction to the repository. Nothing on the board can change a file |
| Driver | Named Approver | The dossier with the approver named in it | Implementation does not start before the approver says yes. A conditional yes ("yes, if X") is recorded with its condition and unblocks the driver immediately (r5 finding 2) |
| TaskRegistry | Driver | An exclusive claim over a declared write scope | One writer per file, for the life of the claim. A write outside the declared scope is refused by the fence, not reported afterwards |
| Driver | EvidenceStore | A receipt earned by a command that ran | A receipt names the command, its output, and the commit it is bound to. Absence is NO-DATA and never a pass |
| Driver | Review wave | The change plus its receipts | Reviewers are read-only. A reviewer proposes; only the driver writes |
| Named Approver | MergeQueue | An approval bound to the head commit | An approval is void once the diff it approved changes. The platform enforces this, not the process |
| ProgramLedger | Exporters | An append-only event stream | Exporters read. They never write back into the ledger, and they hold no credential that could |
| Exporters | Boards | Issues, tasks, cards, pages, notifications | One way. A failed export is retried or alerted; it never blocks a merge, because a broadcast failure is not a truth failure |
| Outgoing driver | Incoming driver | The handover package | Two parts, below. Not complete until acknowledged |

## The two-part handover law

Every high-reliability handover source in the evidence base converges on the same
shape, and none of them accept half of it (r6 findings 1 and 2). The law here is
therefore stated as two parts, and a handover missing either part is not a
handover.

**Part one, the written artifact.** Four sections, no exceptions: what is DONE
with the evidence that proves it; what is IN FLIGHT with the exact stopping point;
what is NOT STARTED; and the open questions. Every open item carries a named owner
and a deadline. A bare status with no owner and no "by when" is incomplete by the
industrial shift-handover standard the research summarizes
(https://toolkitx.com/blogsdetails.aspx?title=Shift-handover%3A-a-practical-guide-to-doing-it-right-in-PTW),
and Google's incident document holds the same line with explicit exit criteria and
a TODO list carrying bug numbers (https://sre.google/sre-book/incident-document/).

**Part two, the explicit acknowledgment.** A verbal or chat exchange that ends in
the receiver confirming ownership. Google SRE's command handoff is the canonical
form: the outgoing commander says "You're now the incident commander, okay?" and
does not disconnect until the incoming commander confirms
(https://sre.google/sre-book/managing-incidents/). The industrial standard states
the reason plainly: the log captures the facts, the meeting adds nuance and
intent, and dropping either half loses one of them.

The exception path matters more than the rule. If no acknowledgment arrives, the
outgoing owner still owns the work. Ownership does not transfer by writing a
document and walking away. In practice that means the outgoing driver keeps the
claim open in the TaskRegistry until the acknowledgment lands, so the mechanical
state and the human state agree.

The same shape closes every session, not only a shift change. The template ships
in the team vault (memory-template/TEAM-VAULT.md), so the handover package and the
session log are one artifact rather than two competing records.
