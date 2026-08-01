# 04. Technology map

Every component below is declared here so the diagrams in 06-diagrams.md trace to
something a reader can find. Owner is a role from 02-process.md, not a person.

## The three planes

| Plane | Technology | Owner role | Failure mode | Recovery path |
|---|---|---|---|---|
| TruthPlane | Git, the program ledger, the task registry, the evidence store | Driver | A receipt is claimed that no command earned | The gate reads it as NO-DATA and refuses the pass; the claim is re-run or withdrawn |
| KnowledgePlane | A git-synced Obsidian vault plus published read-only mirrors | Driver | Two people edit the same note out of sync and union merge keeps both versions | Fence discipline (one writer per note) plus git history; the note is repaired by its owner, never by merge tooling |
| CoordinationPlane | Jira, Confluence, Asana, Microsoft Teams, GitHub Projects v2 | Platform or team lead | A board goes stale because an exporter failed | The exporter alerts and retries; the board carries a last-exported stamp so a reader can see the staleness rather than trust it |

## Integration and engine components

| Component | Technology | Owner role | Failure mode | Recovery path |
|---|---|---|---|---|
| ProgramLedger | YAML work items under program/, append-only event stream | Platform or team lead | A work item is edited without review | Ledger changes ride pull requests under the same merge controls as code |
| TaskRegistry | The shipped claim registry with its write fence | Driver | Two drivers claim overlapping scopes | The fence refuses the second claim at write time, not afterwards |
| EvidenceStore | Receipts written by commands that actually ran | Driver | A hand-typed receipt is submitted | Receipts bind to a commit and a command; an unbound receipt does not verify |
| DesignCheck | tools/sbe_design.py over the dossier directory | Driver | An artifact is present but empty or off-topic | The check FAILs and names the artifact; the plan does not proceed |
| StatusPage | Generated status output, the source for the health screen | Platform or team lead | The page is generated from a stale ledger read | Every figure prints its definition and the date it was checked |
| TeamVault | Obsidian vault synced by git, union-merge on markdown | Driver | Vault becomes the only home for a fact that belongs in git | One fact one home, enforced by review; code and secrets never enter the vault |
| VaultMirror | The published read-only copy of selected vault notes | Platform or team lead | The mirror drifts from the vault | The mirror is regenerated from the vault, never hand-edited; the vault is the upstream |
| ConfluencePublisher | Confluence Cloud REST v2 page create plus the content restrictions API | Platform or team lead | A human hand-edits a generated page and the next publish overwrites them | Update restriction is set to the publishing identity so humans can read but not edit (https://developer.atlassian.com/cloud/confluence/rest/v1/api-group-content-restrictions/) |
| JiraEvidenceField | A URL-typed custom field created with one POST to the field API | Platform or team lead | The field is missing on a project's screen and the link silently does not appear | Field creation is a one-time governance step with a named owner; absence is checked, not assumed (https://support.atlassian.com/jira/kb/jira-software-rest-api-essential-parameters-for-custom-field-creation/) |
| JiraExporter | Thin one-way tool reading the event stream, writing via bulk issue create or the Development Information API | Platform or team lead | Rate limits or a partial batch leave issues half-created | Export is idempotent per event id; the Development Information API is designed for outbound-only pushes with no inbound ports (https://developer.atlassian.com/cloud/jira/software/integrate-jsw-cloud-with-onpremises-tools/) |
| AsanaExporter | Thin one-way tool: create task, then update to the approval subtype | Platform or team lead | A task is created but the conversion to an approval fails, leaving an ordinary task | The conversion is retried; approval is a resource_subtype on a task, so nothing else has to be undone (https://forum.asana.com/t/mark-task-as-approval-via-api/798803) |
| TeamsNotifier | The Workflows app webhook, notify only, never the legacy connector | Platform or team lead | Legacy connectors are retired in the 2026-05-18 to 2026-05-22 window and a connector-based notifier stops delivering | Build on the Workflows trigger from the start; message payload stays under the 28 KB limit and the send rate under 4 per second (https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook) |
| TeamsBot | A real Teams bot using Adaptive Card Universal Actions | Platform or team lead | Tenant app policy blocks the bot for a subset of users and it is silently inert | Tenant app governance is a named rollout step with an owner, verified per user group before launch (https://learn.microsoft.com/en-us/microsoftteams/teams-app-permission-policies) |
| ProjectsBoard | GitHub Projects v2 with fields stage, owner, approver, budget, evidence link | Platform or team lead | Built-in workflows cannot express the rollup the board needs | Real automation runs in Actions against the Projects v2 GraphQL API (https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects) |
| RuleSuiteReader | Scheduled read of the rule suites API, filtered on result | Platform or team lead | Bypasses go unseen because the general audit log has no bypass event | Read rule suites, whose result is pass, fail or bypass with the actor named, and store the pulls durably (https://docs.github.com/en/rest/orgs/rule-suites) |
| MergeQueue | GitHub merge queue on the default branch | Platform or team lead | Status checks never fire because workflows lack the merge_group trigger | Add the merge_group event to the workflows; third-party CI watches the queue's readonly branches (https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue) |
| AttestationSigner | Artifact attestations signing build provenance through GitHub-run Sigstore | Platform or team lead | An artifact ships with no provenance and nobody notices | Verification is a release step; an unverifiable artifact blocks the release rather than the merge (https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds) |

## Source systems

| System | What it masters | Interface | Availability expectation | Failover |
|---|---|---|---|---|
| GitHubEnterprise | Code, pull requests, approvals, rulesets, releases | Git plus REST and GraphQL | The one hard dependency; nothing merges without it | None by design. Truth has one home and an outage stops merging, not deciding |
| JiraCloud | Issue tracking and, where used, change approval workflow | REST v2 and v3, Development Information API | Business hours plus the export window | Export retries; the ledger is unaffected and the board catches up |
| ConfluenceCloud | The governed published record the organization reads | REST v2 page API plus content restrictions | Business hours | Publishing retries; the generated status is regenerable from the ledger at any time |
| AsanaWorkspace | Task and approval tracking for teams that use it | REST 1.0 | Business hours | Export retries; approval subtype conversion is idempotent |
| TeamsTenant | Notifications now, actionable approvals later | Workflows webhook now, bot with Universal Actions later | Business hours | A dropped notification is a dropped notification. Nothing depends on it for correctness |

## Role components

The diagrams name these, so they are declared here rather than left as prose.

| Role | Held by | Never does | Failure mode | Recovery path |
|---|---|---|---|---|
| Driver | One human or one Claude session | Nothing is off limits; this is the writing role | Two drivers on one file | The claim fence refuses the second writer |
| Facilitator | A rotating human | Touches content, ever | Facilitator starts solving the problem and stops keeping the rhythm | Rotation; the role is re-stated at the start of each session |
| NamedApprover | Exactly one accountable human per change | Approves their own change | Approver is a team rather than a person | The dossier names a person; the platform refuses self-approval on the most recent push |
| ReviewWave | Seven read-only reviewer agents plus the human the change class demands | Writes | Findings pile up unrefuted | Each finding is refuted or accepted explicitly before convergence |
| Scribe | Hooks and telemetry | Requires a human to transcribe | A session ends with no record because a hook did not fire | The absence reads as NO-DATA on the health screen rather than as a clean session |
| IncidentCommander | One human during incident mode | Also acts as the only writer | Commander and operations collapse into one overloaded person | Split the roles the moment a second person is available |

## Recovery posture

Nothing in the coordination plane is on the critical path. An exporter outage
degrades visibility and never correctness, which is the whole point of the
one-way stance in 03-adr.md. The truth plane's recovery objective is git's:
the repository is the backup, and every receipt binds to a commit that can be
re-derived. The knowledge plane's recovery is git history plus the fence
discipline, which is weaker than a database transaction and is documented as such
in 05-data-model.md rather than overstated here.
