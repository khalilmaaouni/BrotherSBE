# 01. Purpose brief

## Problem

BrotherSBE proves one person's work. The intake sizes a change, the dossier
records the design, the gates refuse a claim with no receipt behind it, and the
task registry keeps one writer per file. All of that holds inside a single
repository worked by a single driver.

A team breaks none of those laws and still cannot use them, because the work does
not arrive in the repository. It arrives on a board. A Jira issue, an Asana task,
a Microsoft Teams thread, a Confluence page: those are where an enterprise says
what is being built, who approved it, and whether it shipped. Today a driver who
wants the evidence law has to retype the state of the ledger into the board by
hand, twice a day, and a driver who wants the board has to abandon the evidence
law. Neither happens for long. The board wins, because the board is where the
organization looks, and the receipts stop being written.

The second half of the problem is the handover. A session ends, a context window
fills, an engineer goes on leave, and the state of the work lives in one person's
head plus a chat scrollback nobody will read. The repository knows what was
committed. It does not know what was in flight, where it stopped, or who now owns
the open question.

So: the coordination surfaces exist and are not going away, the truth has to stay
in git, and there is currently no designed relationship between the two.

## Users

Four personas plus the organization that employs them. The four are the ones the
product already writes for (docs/specs/2026-08-01-dummies-book-personas.md names
them as beginner builder, backend engineer, data engineer, and platform or team
lead).

- **The beginner builder.** Wants one obvious next move and no vocabulary to
  learn. Needs the board to tell them what to pull and the tool to tell them what
  it owes. Fails if the operating model adds a second place to look.
- **The backend engineer.** Wants to write code and merge it. Needs the review
  wave, the approval, and the merge controls to be the ones already configured in
  GitHub, not a parallel process. Fails if evidence collection is a second job.
- **The data engineer.** Owns numbers other people bet money on. Needs the
  reconciliation receipt and the lineage walk to survive contact with a change
  advisory board that speaks only Jira. Fails if the auditable record and the
  working record are different documents.
- **The platform or team lead.** Owns how many repositories adopt anything, and
  answers to whoever signs the audit. Needs bypasses visible, approvals
  attributable, and one screen per question. Fails if the answer to "who
  approved this" is a chat message.
- **The enterprise itself.** A Forbes-500-scale organization with existing
  tooling, existing controls, and an auditor. It does not adopt a tool that asks
  it to replace Jira. It adopts a tool that feeds Jira and produces a trail its
  auditor already recognizes.

## Success criteria

1. A work item can be sized, designed, built, proved, reviewed, approved, merged
   and shipped without any human retyping state between the ledger and a board.
2. Every screen the organization looks at names the mechanical source of every
   number on it, and prints a definition and a checked date beside the number.
3. Every merge control the design relies on is one of the four mechanisms a
   SOX-familiar auditor already knows (ownership routing, no self-approval on the
   most recent push, stale-review dismissal, and protection of the control file
   itself, r5), plus the required-reviewer ruleset rule for per-path minimum
   approval counts (GA 2026-02,
   https://github.blog/changelog/2026-02-17-required-reviewer-rule-is-now-generally-available/).
4. No inbound path exists by which a board, a webhook, or a bot can change the
   repository. Every inbound change is a pull request.
5. A handover hands over: a written package plus an explicit acknowledgment, with
   a named owner and a deadline on every open item, and a successor who can
   continue without asking the predecessor anything.
6. Bypasses are countable. Because GitHub's general audit log carries no
   dedicated ruleset-bypass event, the compliance screen reads the rule suites
   API, whose result field is pass, fail, or bypass with the actor named
   (https://docs.github.com/en/rest/orgs/rule-suites).

## Non-goals

- This does not replace Jira, Asana, Confluence, Microsoft Teams, or GitHub
  Projects. It feeds them.
- This does not make the shared vault an enterprise knowledge base. The vault has
  no single sign-on, no audit log, and no per-role access control
  (https://obsidian.md/help/sync/collaborate and the gap list at
  https://ravoid.com/blog/obsidian-vs-confluence-knowledge-stack-decision/), and
  the design says so out loud rather than designing around it.
- This does not ship engine code in this round. It writes the dossier, the human
  playbook, the ledger rows for the exporters, and the vault pattern.
- This does not build a two-way sync. Rejected explicitly in 03-adr.md.
- This does not define an approval API of its own. Jira enforces approvals inside
  its own workflow, so an external system drives the ordinary issue transition
  and Jira refuses it until the approval resolves
  (https://support.atlassian.com/jira-service-management-cloud/docs/designate-your-approvers/).

## Blast radius: what breaks if this is wrong

The dangerous failure is not that the integration breaks. It is that the
integration works and lies.

- **If the broadcast direction inverts**, a board becomes able to mutate the
  repository, and the evidence law dies quietly: a status changes with no commit,
  no receipt, and no approver. Every downstream claim built on that ledger is then
  unfalsifiable. This is why the one-way stance is an ADR and not a preference.
- **If a screen shows a number with no mechanical source**, the organization
  starts making decisions on a figure nobody can reproduce, and the tool has
  become the thing it was built to replace.
- **If bypasses are invisible**, the compliance screen reads green while the
  controls are off. This is a live risk rather than a theoretical one, because the
  bypass event is genuinely absent from the general audit log and only the rule
  suites surface carries it.
- **If the handover is written but never acknowledged**, work is dropped in the
  gap between two people who each believed the other had it. Every high-reliability
  source in the evidence base converges on the two-part shape for exactly this
  reason (r6 findings 1 and 2).
- **If the vault's limits are soft-pedalled**, someone puts material in it that
  needed access control it does not have. That is a disclosure incident caused by
  a documentation choice.

The cheap failure is adoption: if the model reads as ceremony, teams route around
it and the receipts stop. The design treats that as the default outcome to be
argued against, which is why the coordination layer is fed automatically and the
human layer is a pull system rather than an assignment system.
