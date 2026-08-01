# BrotherSBE Public Release Master Plan

**Status:** Delivery blueprint - no public release authorized  
**Baseline reviewed:** `dacee900d24d40b351bc117ebbf001406bb09699`  
**Plan date:** 2026-07-31  
**Product owner:** Khalil Maaouni  
**Primary objective:** Turn BrotherSBE's strong assurance engine into the simplest, most guided, most maintainable engineering product in its category.

---

## 1. Executive direction

BrotherSBE already has a differentiated backend and data-engineering assurance core. The remaining problem is not a lack of gates, agents, checks, or technical depth. The problem is that the product exposes too much of its internal machinery and expects the user to understand it before it helps them.

The next program must therefore focus on five outcomes, in this order:

1. **One obvious starting point and continuous handholding.**
2. **One-click installation, automatic setup, health reporting, update, and rollback.**
3. **One maintainable host-neutral architecture instead of separate implementations per model or IDE.**
4. **A complete, visible lifecycle from idea to finished and reviewed change.**
5. **A release process that makes contradictions, broken installation, unclear next steps, and unsupported hosts release blockers.**

The product promise becomes:

> Install once. Describe what you want to build. BrotherSBE shows the next action, explains why it matters, performs everything it can safely perform, asks only for decisions that require a person, and stays with the project until it is ready to finish.

### Delivery estimate

Assuming two experienced engineers, a part-time product/UX lead, and the founder available for decisions:

- **Engineering and product work:** 12 weeks
- **External usability validation and remediation:** 2 to 4 weeks
- **Total to a defensible stable release:** **14 to 16 weeks**
- If work begins on Monday, August 3, 2026, the earliest defensible stable release window is **November 9 to November 23, 2026**, only if every release gate in this document passes.
- Anthropic directory review is external and cannot be time-guaranteed. Submission must happen early enough to run in parallel with product validation.

For one maintainer working sequentially, the same program is approximately **26 to 32 weeks**.

### Token budget

- **Planned agent budget:** approximately **6.2 million input and output tokens**
- **Hard program ceiling:** **7,410,000 tokens** (the sum of the per-item caps in section 10)
- CI logs, test fixture output, and deterministic generated files are excluded from this estimate.
- Every task has its own token cap. Reaching 75 percent without an acceptance criterion passing triggers a scope review. Reaching 100 percent stops the task until it is split or re-planned.

These are planning estimates, not a release promise. The release is evidence-gated, not date-gated.

---

## 2. The no-release covenant

BrotherSBE will not be publicly released or described as stable until all of the following are true:

- Installation is one click in Claude's official plugin directory, with a one-command fallback for other hosts.
- Installation requires no manual editing of shell profiles, JSON settings, hook definitions, or copied workflow files for the normal path.
- A new user always sees one recommended next action.
- A beginner can complete a first project without reading the internal architecture documentation.
- User-facing skills and documentation contain no known contradiction with the implementation.
- The product no longer teaches manual evidence creation where wrapper-generated evidence exists.
- A stable signed release, checksums, provenance, upgrade, rollback, and uninstall paths have been executed successfully.
- Tier 1 host adapters pass the same lifecycle contract suite.
- At least five unrelated beginners and five unrelated engineers complete the agreed validation scenarios.
- No critical or high-severity release finding remains open.

A calendar date, feature count, test count, or marketplace submission is not sufficient to waive these conditions.

---

## 3. Key personas and the three most-needed features

### Persona A: Beginner builder

This user may be a founder, product manager, analyst, junior developer, or non-specialist. They know what outcome they want but do not know which BrotherSBE command, skill, artifact, gate, or engineering phase to use.

Their questions are:

- Where do I start?
- What should I do now?
- What does this warning mean?
- What will happen if I continue?
- Is the project finished?

### Persona B: Individual engineer

This user wants better design and verification without losing velocity. They do not want to manually coordinate dossiers, receipts, worktrees, checks, and reviewers.

Their questions are:

- Can BrotherSBE detect what matters automatically?
- Can it run the right workflow without ceremony for small changes?
- Can I trust the evidence and resume later?
- Can it work in my preferred CLI or IDE?

### Persona C: Team lead, reviewer, or platform owner

This user wants clear ownership, progress, risks, exceptions, and release readiness across several changes and people.

Their questions are:

- Who owns this work and why?
- What is blocked?
- Which claims are proven, waived, stale, or unavailable?
- Is the team ready to merge or release?
- Are we spending excessive time or tokens on the wrong work?

### The three priority features

These three features cover the highest-value needs across the personas and the strongest competitor advantages without bloating the product.

#### Feature 1: Guided Project Navigator

One lifecycle controller with four primary actions:

```text
/brothersbe:start
/brothersbe:next
/brothersbe:status
/brothersbe:help
```

The user describes the desired outcome in natural language. BrotherSBE determines the current stage, recommends exactly one next action, explains why, and routes internally to the existing specialist capabilities.

This replaces the expectation that a beginner chooses among kickoff, design, plan, work, evidence, verify, review, converge, PR verification, and status.

#### Feature 2: One-click install and self-managing distribution

The primary Claude path is installation from Claude's official plugin directory. The product configures itself, performs a health check, reports readiness, and teaches the first action.

Other supported hosts use one signed installer command or their native extension mechanism. Update, rollback, uninstall, and state migration are part of the same product, not separate runbooks.

#### Feature 3: Shared progress, ownership, and portable execution

A host-neutral project state records:

- Objective
- Stage
- Next action
- Owner and reviewer
- Reason for the task
- Dependencies
- Token budget and actual use
- Evidence
- Risks and alerts
- Host and model used
- Completion and release status

Claude, Codex, Gemini, Qwen, Kimi, OpenCode, and IDE integrations all operate on this same state rather than maintaining separate workflows.

---

## 4. Experience principles

### 4.1 One entry point

The normal user never needs to remember the internal command inventory. `/brothersbe:start` starts or resumes the project.

### 4.2 One next action

Every user-facing response contains:

1. **Where you are**
2. **What is complete**
3. **What needs attention**
4. **The single recommended next action**
5. **Why it is recommended**
6. **What BrotherSBE will do automatically**
7. **What decision or permission is required from the user**
8. **Expected effort and token budget**
9. **How success will be verified**

Never show a flat list of commands as the primary answer.

### 4.3 Progressive disclosure

BrotherSBE has three presentation modes over the same engine:

- **Guided:** Plain language, one action at a time, technical details collapsed.
- **Standard:** Concise engineering terminology with evidence links.
- **Expert:** Raw commands, artifacts, verdicts, source locations, and full evidence.

A user's assurance level never changes with presentation mode. Only the amount of explanation changes.

### 4.4 Safe autonomy

BrotherSBE automatically performs local, reversible, and read-only actions. It asks before meaningful mutations. It never obtains production apply, merge, release, or destructive rights by default.

### 4.5 No dead ends

Every error and refusal includes:

- What happened
- Why it matters
- The safest recovery action
- An automatic repair option when possible
- A manual command only as an advanced fallback

### 4.6 Teach through use

Handholding is strongest during the first three successful projects:

- **Project 1:** Full explanations and examples.
- **Project 2:** Explanations remain available, but repeated concepts are shortened.
- **Project 3:** Standard mode is suggested after successful completion.
- Users can return to Guided mode at any time.

BrotherSBE recommends capabilities contextually. It shows one required capability and no more than two optional recommendations, each with a reason, permissions, expected outcome, and installation status.

---

## 5. The orchestrated lifecycle loops

The product is one state machine with seven loops. Each loop has an entry condition, automation, a human decision boundary, an output, and a completion condition.

```text
INSTALL -> UNDERSTAND -> DESIGN -> PLAN -> BUILD -> PROVE -> FINISH -> LEARN
                  ^                                      |
                  +----------- AMEND AND RE-RUN ----------+
```

### Loop 0: Install and become ready

**Entry:** The user clicks Install or runs the universal installer.  
**Goal:** Reach a verified, usable state without manual configuration.

#### Automated sequence

```text
DETECTING HOST
DOWNLOADING SIGNED PACKAGE
VERIFYING SIGNATURE AND CHECKSUM
CONFIGURING NATIVE INTEGRATION
CREATING LOCAL STATE
CHECKING GIT AND RUNTIME
REGISTERING COMMANDS AND HOOKS
RUNNING HEALTH CHECK
READY
```

#### User-facing result

```text
BrotherSBE is ready

Host: Claude Code
Version: 1.0.0
Project support: Ready
Updates: Stable channel, automatic
Local data: Off by default

Start here: /brothersbe:start
```

Partial readiness is never presented as complete:

```text
BrotherSBE needs one fix

Python 3.9 or newer was not found.
BrotherSBE can install its isolated runtime without changing your system Python.

[Fix automatically] [Show details]
```

#### Completion criteria

- Native command or skill is registered.
- The package signature and checksums pass.
- Required runtime is available.
- State directory is writable.
- No manual global settings edit is required.
- The first project action is displayed.

---

### Loop 1: Understand the project and the user's outcome

**Entry:** `/brothersbe:start` in a new or existing repository.  
**Goal:** Establish an accurate objective and project profile with minimal questioning.

#### Automated actions

- Detect repository, languages, build tools, tests, CI, contracts, schemas, migrations, infrastructure, and likely risk areas.
- Read project-native instructions such as `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, repository contribution guides, and existing BrotherSBE state.
- Identify whether the user is starting new work or resuming an active project.
- Infer the likely work profile and minimum assurance tier.
- Ask only questions whose answers materially change the plan.

#### Guided interaction

```text
What are you trying to accomplish?

You can describe the result in normal language. For example:
- Add customer export to the API
- Fix the revenue mismatch
- Design a new ordering service
- Review this pull request before release
```

After the answer:

```text
I understand the goal

Outcome: Add a customer export endpoint
Users: Operations analysts
Main risk: Personal data may leave the service
Detected stack: Python, FastAPI, PostgreSQL, GitHub Actions
Assurance level: High

Recommended next action: Confirm what customer fields may be exported.
Why: This decision changes both the API contract and privacy boundary.
Estimated effort: 5 minutes, up to 15k tokens.
```

#### Completion criteria

- Objective, users, success condition, and non-goals are recorded.
- Detected facts are separated from assumptions.
- Risk tier has a machine-derived floor and a human-confirmed final value.
- One next action is available.

---

### Loop 2: Design and plan the work

**Entry:** Objective and project profile are complete.  
**Goal:** Produce only the design material the change actually requires and transform it into executable work.

#### Automated actions

- Select the minimum necessary dossier artifacts.
- Reuse repository information instead of asking the user to repeat it.
- Generate architecture alternatives only where a decision exists.
- Produce a task graph with dependencies, owners, verification commands, and token budgets.
- Estimate elapsed engineering time and agent-token cost.
- Detect tasks that can safely run in parallel.

#### Plan presentation

```text
Project plan

1. Confirm export fields                 Human decision       5 min
2. Update API contract                   BrotherSBE + engineer 45 min
3. Add authorization and audit logging   Engineer              90 min
4. Implement export generation           Engineer              2 h
5. Prove privacy and compatibility        BrotherSBE            45 min
6. Review and prepare the pull request    BrotherSBE + reviewer 30 min

Estimated elapsed time: 1 to 2 working days
Planned model budget: 180k tokens
Parallel work: Tasks 2 and 3 may start after task 1

Recommended next action: Confirm the export fields.
```

#### Completion criteria

- Every task cites the requirement or design decision that created it.
- Every task has one owner and one reviewer role.
- Every task has acceptance criteria and a verification method.
- No task exceeds 200k tokens without being split.
- Dependencies are acyclic and executable.

---

### Loop 3: Build with continuous guidance

**Entry:** A validated plan has at least one ready task.  
**Goal:** Complete tasks safely without making the user coordinate worktrees, receipts, scopes, or specialist agents manually.

#### Automated actions

- Select the highest-priority ready task.
- Create isolation only when parallel work or risk requires it.
- Reserve the task's declared scope.
- Recommend the best available host/model for the work, but respect the user's chosen host.
- Run the repository's own checks during implementation.
- Persist progress and resume state at meaningful milestones.
- Stop after two failed attempts on one approach and re-plan rather than consuming tokens indefinitely.

#### Progress card

```text
Building: Add authorization and audit logging

Owner: Backend implementation
Why this exists: Customer exports contain personal data
Progress: 3 of 5 acceptance checks complete
Token budget: 61k of 90k used
Current action: Add an audit event for successful and denied exports
Next proof: Run authorization and audit tests

No action is needed from you.
```

Alerts appear only when action is useful:

```text
Decision needed

Two implementation approaches have failed for the same reason: the current audit
library cannot record streaming failures after the response starts.

Recommendation: Generate the export before opening the response stream.
Tradeoff: Higher temporary disk usage, simpler and auditable failure handling.

[Use recommendation] [Compare alternatives]
```

#### Completion criteria

- Declared scope matches actual changes.
- Acceptance criteria are met.
- Required checks have executed.
- Evidence is bound to the current commit.
- Task status and token use are recorded.

---

### Loop 4: Prove, review, and converge

**Entry:** Implementation tasks are complete.  
**Goal:** Determine whether the implementation is correct, supported by evidence, and still matches the approved design.

#### Automated actions

- Run only the relevant gates.
- Generate evidence through wrappers; never ask the user to type durations, exit codes, row counts, or successful results manually.
- Run specialist reviews according to detected risk.
- Compare implementation with objective, contracts, data model, architecture, and verification plan.
- Deduplicate findings.
- Convert findings into tasks rather than leaving them as prose.

#### Guided result

```text
Review result: Not ready yet

1 blocker
- The rollback migration has not been rehearsed against a restored copy.

2 improvements
- Add a timeout to the export job.
- Document the maximum supported export size.

Recommended next action: Rehearse the rollback migration.
BrotherSBE will create the rehearsal command and record its evidence.
Estimated effort: 20 minutes, up to 25k tokens.
```

A detailed technical appendix remains available but is not the primary UI.

#### Completion criteria

- No blocking finding remains.
- Required approvals are current and independently attributable.
- Evidence is current for the assessed commit.
- Convergence passes or the design has been explicitly amended and re-approved.

---

### Loop 5: Finish and prepare release

**Entry:** Review and convergence pass.  
**Goal:** Make completion obvious and create the artifacts needed for a human-controlled merge or release.

#### Automated actions

- Produce a concise change summary.
- Produce test and evidence summary.
- Identify rollout, rollback, monitoring, and ownership.
- Generate or update the pull-request description.
- Verify required checks and approvals when the host supports it.
- Mark the project complete only when the recorded state supports completion.

#### Completion card

```text
Ready for human review

Outcome: Customer export endpoint is implemented
Scope: 7 files changed
Evidence: 18 checks passed, 0 stale, 0 waived
Review: Security and backend review complete
Rollback: Tested against restored data
Remaining human action: Approve and merge pull request #184

BrotherSBE will not merge or deploy automatically.
```

#### Completion criteria

- The user understands what changed and what remains human-controlled.
- Release and rollback instructions are present.
- Project state is closed without force.
- Final summary is portable across hosts.

---

### Loop 6: Learn, update, and improve without hidden behavior changes

**Entry:** Project closes, an incident occurs, or a repeated correction is observed.  
**Goal:** Improve the product and team process without silently changing behavior.

#### Automated actions

- Propose lessons with evidence and recurrence count.
- Track usability friction, false blockers, repeated questions, token overruns, and adapter failures.
- Suggest one improvement at a time.
- Require review before a proposal changes shared laws or defaults.
- Apply versioned state migrations during product updates.

#### Completion criteria

- Lessons are proposals until reviewed.
- Product updates are signed and reversible.
- Existing projects migrate or roll back cleanly.
- No adapter receives a behavior change that the canonical core did not define.

---

## 6. Target architecture

### 6.1 Architectural rule

**One canonical core, many thin adapters.**

Claude, Codex, Gemini, Qwen, Kimi, OpenCode, and IDEs must not contain independent versions of BrotherSBE's lifecycle or assurance rules.

### 6.2 Proposed structure

```text
src/brothersbe/
  domain/
    lifecycle.py          # stages, transitions, invariants
    work_item.py          # ownership, budgets, dependencies, status
    assurance.py          # verdict and evidence semantics
    policy.py             # policy and exception models

  application/
    install.py
    start.py
    next_action.py
    project_status.py
    plan_project.py
    execute_task.py
    prove_change.py
    finish_project.py
    update_product.py

  ports/
    filesystem.py
    git.py
    process.py
    host.py
    network.py
    clock.py
    secrets.py
    telemetry.py

  adapters/
    cli/
    claude/
    codex/
    gemini/
    qwen/
    kimi/
    opencode/
    ide/

  presentation/
    view_model.py
    guided.py
    standard.py
    expert.py
    json_renderer.py

  infrastructure/
    local_filesystem.py
    local_git.py
    github_readonly.py
    package_manager.py
    updater.py

  schemas/
    lifecycle-state.schema.json
    work-item.schema.json
    result-envelope.schema.json
    policy.schema.json
    exception.schema.json
```

### 6.3 Preserve the proven engine

The current gates, checks, evidence, plan, work, convergence, and PR verification should not be rewritten as part of the first UX wave.

They should be wrapped behind stable application interfaces. Rewrite only when:

- A verified defect requires it.
- Duplication prevents a stable contract.
- The module cannot be tested through the new interface.
- The change reduces total code and behavior remains covered.

### 6.4 One result contract

All user-facing operations return a versioned result envelope:

```json
{
  "schemaVersion": "1.0",
  "operation": "next",
  "status": "ACTION_REQUIRED",
  "stage": "DESIGN",
  "summary": "Confirm which customer fields may be exported.",
  "why": "The answer changes the API and privacy boundary.",
  "recommendedAction": {
    "id": "confirm-export-fields",
    "actor": "human",
    "estimatedMinutes": 5,
    "tokenBudget": 15000
  },
  "completed": [],
  "blockers": [],
  "evidence": [],
  "technicalDetails": {}
}
```

The CLI, Claude skill, IDE panel, and other hosts render the same envelope differently. They do not recompute the result.

### 6.5 One state contract

The project stores a small, versioned `.brothersbe/project.json` containing pointers and summaries, not copied terminal output. Large evidence remains in dedicated stores.

State writes must be:

- Atomic
- Lock-safe across processes
- Versioned
- Migratable
- Recoverable
- Explicit about unavailable data

### 6.6 Eliminate documentation duplication

The following must be generated from canonical registries or templates:

- Command reference
- Skill routing table
- Lifecycle stages
- Exit codes
- Result vocabulary
- Install status vocabulary
- CI snippets
- Compatibility matrix
- Version references

A copied full workflow inside several guides is prohibited. Guides link to or embed a generated, tested excerpt.

### 6.7 Maintainability targets

- Adding a host adapter must not change domain or assurance code.
- A normal new adapter should require no more than 500 lines of host-specific code and two engineering days after the SDK is stable.
- Changing one lifecycle transition should require edits in one canonical module, its tests, and generated documentation - not multiple hand-maintained guides.
- Public modules have typed interfaces and contract tests.
- Every persisted schema has forward migration and rollback coverage.
- Every network-capable module is explicitly allowlisted and documented.

---

## 7. Distribution, installation, update, and rollback

### 7.1 Claude Code: primary installation

The stable path is:

```text
Claude -> Plugins -> Discover -> BrotherSBE -> Install
```

The command-line equivalent remains available:

```text
/plugin install brothersbe@claude-plugins-official
```

The package includes its own skills, commands, agents, hooks, schemas, and executable payload. A normal user never clones the repository or edits settings.

### 7.2 Other hosts: universal installation

Provide signed native packages and one command per operating system:

```text
macOS/Linux: curl -fsSL https://brothersbe.dev/install | sh
Windows:     irm https://brothersbe.dev/install.ps1 | iex
```

Also publish through appropriate package managers when stable:

- Homebrew
- npm or standalone binary channel
- Winget or Scoop
- GitHub Releases

The installer must verify the downloaded artifact before execution and must support pinned versions.

### 7.3 First-run self-configuration

The installer or first-run bootstrapper:

- Detects supported hosts.
- Installs the canonical core once.
- Installs or generates selected host adapters.
- Registers native commands and instructions.
- Creates local state with secure permissions.
- Runs `doctor` automatically.
- Displays a final status report.
- Offers automatic repair for supported problems.

### 7.4 Updates

Two channels:

- **Stable:** Default, signed, compatibility-tested.
- **Preview:** Explicit opt-in, reversible.

Update behavior:

1. Download to a staging location.
2. Verify signature, checksum, and provenance.
3. Run migration dry-run.
4. Validate installed adapters.
5. Activate atomically.
6. Run health checks.
7. Roll back automatically on failure.
8. Show what changed in plain language.

### 7.5 Uninstall

Uninstall removes program files and host registrations, then asks separately whether to retain project state and evidence. It never silently deletes user work.

### 7.6 Installation acceptance criteria

- 90 percent of beginner test users complete installation without external documentation.
- Median click-to-ready time is under five minutes on supported systems.
- No manual settings file edit is required.
- Completion status is explicit: READY, PARTIAL, or BLOCKED.
- Re-running installation is idempotent.
- Upgrade and rollback preserve existing project state.
- Uninstall leaves no active hooks or broken host references.

---

## 8. Cross-model, CLI, and IDE support

### 8.1 Product rule

BrotherSBE integrates with **hosts**, not directly with every model API in version 1. The host selects and authenticates the model. BrotherSBE supplies lifecycle, state, tools, instructions, and assurance.

This prevents separate model clients, authentication implementations, and duplicated orchestration logic.

### 8.2 Capability negotiation

Each adapter reports capabilities such as:

- Native skills
- Custom commands
- Hooks
- Subagents
- Structured JSON output
- MCP support
- ACP support
- Session resume
- IDE panel support
- Permission controls
- Background task support

BrotherSBE enables only supported features and displays a degradation report when a host lacks one.

### 8.3 Tier 1 hosts required for stable release

| Host | Integration target | Stable requirement |
|---|---|---|
| Claude Code | Official plugin with skills, commands, agents, hooks | Full guided lifecycle and one-click directory install |
| OpenAI Codex CLI and IDE | Native instructions, command bridge, state and result protocol | Start, next, status, execute, prove, finish |
| Google Gemini CLI | Native extension/skills/commands and context adapter | Same lifecycle contract |
| Alibaba Qwen Code | Native command and skills adapter, headless support | Same lifecycle contract |
| Moonshot Kimi Code | Native command/skills or ACP adapter | Same lifecycle contract |
| OpenCode | Provider-neutral command or plugin adapter | Same lifecycle contract |

### 8.4 Tier 2 IDE surfaces

- VS Code
- Cursor and other compatible VS Code forks
- JetBrains IDEs
- Zed

The first release may use the host's terminal/agent integration plus a lightweight status panel. It must not create independent assurance logic inside the extension.

### 8.5 Tier 3 compatibility certification

- TRAE
- Tongyi Lingma
- Other Chinese coding environments
- Future ACP, MCP, and AGENTS-compatible hosts

Where no stable extension interface exists, provide:

- Canonical `AGENTS.md` generation
- CLI bridge
- MCP or ACP integration where supported
- Compatibility report naming unavailable capabilities

### 8.6 Model coverage through supported hosts

The architecture should work with the main model families selected by those hosts, including:

- Anthropic Claude
- OpenAI GPT and Codex models
- Google Gemini
- Alibaba Qwen Coder
- Moonshot Kimi
- DeepSeek and other OpenAI-compatible models through provider-neutral hosts
- Additional local or hosted models through OpenCode-compatible providers

No model receives a weaker assurance definition. If a model or host cannot support a required control, BrotherSBE reports the control as unavailable rather than pretending parity.

### 8.7 Adapter contract suite

Every Tier 1 adapter must pass the same scenarios:

1. Install and health check.
2. Start a new project.
3. Resume an existing project.
4. Determine one next action.
5. Execute a safe task.
6. Refuse a production mutation.
7. Produce commit-bound evidence.
8. Surface a blocking failure.
9. Finish with a portable summary.
10. Update and roll back without state loss.

---

## 9. Attribution, tracking, status, insights, and alerts

### 9.1 Single source of truth

Create:

```text
program/
  PROGRAM.yaml
  work-items/
    BR-0001.yaml
    BR-0002.yaml
  events.jsonl
  STATUS.md              # generated
  DECISIONS.md           # generated index of reviewed decisions
```

`PROGRAM.yaml` records the release objective, version, owners, total budget, target window, and release gates.

Each work item records:

```yaml
id: BR-0203
title: Implement sbe next
why: Beginners cannot identify the next lifecycle action.
owner: product-engineer
reviewer: architecture-owner
status: in_progress
wave: guided-experience
depends_on: [BR-0101, BR-0102]
acceptance:
  - returns exactly one recommended action
  - explains why the action is next
  - works in guided, standard, and expert modes
estimated_days: 4
token_budget: 180000
tokens_used: 0
started_at: null
completed_at: null
evidence: []
risks: []
alerts: []
```

### 9.2 Attribution

Every task, commit, pull request, decision, exception, and generated release note carries:

- Work-item ID
- Human owner
- Agent or host used
- Reviewer
- Reason for the work
- Acceptance criteria
- Evidence
- Token budget and actual usage

An AI agent may implement a task. It may not become the accountable human owner or approve its own work.

### 9.3 Status reporting

`STATUS.md` and `/brothersbe:status` present:

- Overall release readiness
- Completed, active, ready, blocked, and deferred work
- Current critical path
- Token budget versus actual use
- Rework count
- Open contradictions
- Adapter compatibility
- Usability results
- External review status
- Recommended management action

### 9.4 Event-driven alerts

Alerts appear only on meaningful state changes:

- Critical or high release finding created
- Task blocked longer than one working day
- Token usage reaches 75 percent of budget
- Task reaches two failed implementation approaches
- Dependency or owner changes
- CI or adapter contract becomes red
- Documentation contradicts executable behavior
- Migration or rollback cannot complete
- Beginner completion rate falls below the release threshold
- Marketplace submission requires action

### 9.5 Insight cadence

- **Per task:** Completion summary with actual time, tokens, evidence, and follow-up.
- **Per wave:** Retrospective of rework, defects, usability friction, and budget variance.
- **At session start:** Show only changes since the user's last interaction.
- **Weekly during the program:** Generated executive summary, not a manually written report.

Telemetry remains local and opt-in. Program tracking uses repository state and does not require collection of user conversations.

---

## 10. Delivery roadmap, ownership, time, and token budgets

### Recommended team

| Role | Responsibility |
|---|---|
| Product owner / founder | Product decisions, scope, release authority, marketplace submission |
| Architecture owner | Core contracts, maintainability, security boundaries, adapter design |
| Product engineer | Guided UX, lifecycle controller, renderers, onboarding |
| Platform/release engineer | Packaging, installers, updates, signing, compatibility CI |
| UX test lead | Beginner scenarios, observation, friction tracking, acceptance evidence |
| Independent reviewer | Security, release readiness, contradiction review |

One person may hold multiple implementation roles, but product owner, implementer, and final independent reviewer should not collapse into one unchecked actor.

### Wave 0 - Truth reset and feature freeze

**Schedule:** Week 1  
**Purpose:** Remove release-blocking contradictions before building on top of them.

| ID | Task | Owner role | Days | Token cap | Depends on |
|---|---|---:|---:|---:|---|
| BR-0001 | Freeze non-critical feature additions and capture exact baseline | Architecture owner | 1 | 40k | - |
| BR-0002 | Correct network/security promises and add whole-codebase network allowlist tests | Security reviewer + engineer | 2 | 90k | BR-0001 |
| BR-0003 | Fix repository-name validation and adversarial tests | Engineer | 1 | 50k | BR-0001 |
| BR-0004 | Synchronize all user-facing skills with impact, evidence, plan, work, and convergence | Product engineer | 2 | 100k | BR-0001 |
| BR-0005 | Replace manual receipt guidance with wrapper-generated evidence | Product engineer | 1 | 50k | BR-0004 |
| BR-0006 | Make decision-package allocation process-safe | Architecture owner | 2 | 100k | BR-0001 |

**Wave budget:** 430k tokens  
**Exit:** No known critical contradiction remains; current engine is frozen behind tests.

### Wave 1 - Canonical lifecycle and maintainable contracts

**Schedule:** Weeks 2 to 3  
**Purpose:** Define the stable foundation before adding new surfaces.

| ID | Task | Owner role | Days | Token cap | Depends on |
|---|---|---:|---:|---:|---|
| BR-0101 | Define lifecycle state machine and transition invariants | Architecture owner | 3 | 140k | Wave 0 |
| BR-0102 | Define result envelope and guided view model | Product engineer | 3 | 130k | BR-0101 |
| BR-0103 | Define work-item, attribution, budget, and event schemas | Architecture owner | 2 | 90k | BR-0101 |
| BR-0104 | Implement atomic state store, locks, migration, and rollback | Platform engineer | 4 | 180k | BR-0101, BR-0103 |
| BR-0105 | Wrap current engine behind application interfaces without rewriting gates | Architecture owner | 5 | 220k | BR-0102, BR-0104 |
| BR-0106 | Generate command, lifecycle, and verdict documentation from registries | Product engineer | 3 | 130k | BR-0102 |

**Wave budget:** 890k tokens  
**Exit:** One canonical state and result protocol; existing capabilities available through stable interfaces.

### Wave 2 - Guided experience and onboarding

**Schedule:** Weeks 3 to 5  
**Purpose:** Make the product usable without learning its internal command inventory.

| ID | Task | Owner role | Days | Token cap | Depends on |
|---|---|---:|---:|---:|---|
| BR-0201 | Implement `sbe start` and project resume detection | Product engineer | 4 | 180k | BR-0105 |
| BR-0202 | Implement deterministic `sbe next` | Product engineer | 4 | 180k | BR-0201 |
| BR-0203 | Redesign `sbe status` around stage, blocker, next action, and ownership | Product engineer | 3 | 130k | BR-0102, BR-0103 |
| BR-0204 | Implement `sbe explain` with plain-language and technical layers | Product engineer | 2 | 90k | BR-0102 |
| BR-0205 | Implement Guided, Standard, and Expert renderers | Product engineer | 4 | 180k | BR-0102 |
| BR-0206 | Implement first-three-project onboarding progression | UX lead + product engineer | 4 | 180k | BR-0201, BR-0202 |
| BR-0207 | Implement contextual capability and skill recommendations | Product engineer | 3 | 120k | BR-0202 |
| BR-0208 | Add no-dead-end error and recovery contract | Architecture owner | 3 | 120k | BR-0102 |

**Wave budget:** 1.18M tokens  
**Exit:** A beginner can start, resume, understand status, and receive one next action.

### Wave 3 - Installation, packaging, update, and rollback

**Schedule:** Weeks 5 to 7  
**Purpose:** Remove clone-and-configure installation completely from the normal path.

| ID | Task | Owner role | Days | Token cap | Depends on |
|---|---|---:|---:|---:|---|
| BR-0301 | Produce reproducible signed release artifacts | Platform engineer | 4 | 180k | Wave 1 |
| BR-0302 | Implement host detector and universal installer | Platform engineer | 4 | 180k | BR-0301 |
| BR-0303 | Implement installation progress and final health report | Product engineer | 3 | 120k | BR-0302, BR-0205 |
| BR-0304 | Implement idempotent repair and uninstall | Platform engineer | 3 | 130k | BR-0302 |
| BR-0305 | Implement stable/preview update channels and automatic rollback | Platform engineer | 5 | 220k | BR-0104, BR-0301 |
| BR-0306 | Build Windows, macOS, and Linux install matrix | Platform engineer | 4 | 180k | BR-0302, BR-0305 |
| BR-0307 | Package Claude plugin for official directory and submit early | Product owner + platform engineer | 3 | 120k | BR-0301, BR-0303 |

**Wave budget:** 1.13M tokens  
**Exit:** One-click Claude installation and one-command universal installation both end in a visible readiness report.

### Wave 4 - Cross-host adapters

**Schedule:** Weeks 7 to 9  
**Purpose:** Support major global and Chinese coding environments without duplicating the product.

| ID | Task | Owner role | Days | Token cap | Depends on |
|---|---|---:|---:|---:|---|
| BR-0401 | Implement adapter SDK and capability negotiation | Architecture owner | 4 | 180k | Wave 1 |
| BR-0402 | Complete Claude Code adapter over canonical lifecycle | Product engineer | 2 | 80k | BR-0401, Wave 2 |
| BR-0403 | Implement Codex CLI and IDE adapter | Adapter engineer | 3 | 120k | BR-0401 |
| BR-0404 | Implement Gemini CLI adapter | Adapter engineer | 3 | 120k | BR-0401 |
| BR-0405 | Implement Qwen Code adapter | Adapter engineer | 3 | 120k | BR-0401 |
| BR-0406 | Implement Kimi Code adapter | Adapter engineer | 3 | 120k | BR-0401 |
| BR-0407 | Implement OpenCode adapter | Adapter engineer | 3 | 120k | BR-0401 |
| BR-0408 | Provide VS Code/Cursor, JetBrains, and Zed integration layer | IDE engineer | 5 | 220k | BR-0401, BR-0403 to BR-0407 |
| BR-0409 | Certify TRAE, Tongyi Lingma, ACP/MCP, and AGENTS-based fallback paths | Adapter engineer | 3 | 120k | BR-0401 |

**Wave budget:** 1.20M tokens  
**Exit:** Every Tier 1 host passes the same ten-scenario adapter contract suite.

### Wave 5 - Team control, governance, and release engineering

**Schedule:** Weeks 9 to 11  
**Purpose:** Make ownership, risk, updates, and release readiness visible and governable.

| ID | Task | Owner role | Days | Token cap | Depends on |
|---|---|---:|---:|---:|---|
| BR-0501 | Implement program/work-item ledger and generated status | Platform engineer | 4 | 180k | BR-0103 |
| BR-0502 | Implement event-driven alerts and token-budget controls | Platform engineer | 3 | 130k | BR-0501 |
| BR-0503 | Implement PR and release summary generated from project state | Product engineer | 3 | 120k | Wave 2, BR-0501 |
| BR-0504 | Implement structured policies and owned, approved, expiring exceptions | Architecture owner | 5 | 230k | BR-0103 |
| BR-0505 | Implement contradiction checker across code, skills, docs, and security claims | Architecture owner | 5 | 220k | BR-0106 |
| BR-0506 | Add SBOM, provenance, signed tag, checksums, and release verification | Release engineer | 4 | 180k | BR-0301 |
| BR-0507 | Add upgrade, rollback, state-migration, and adapter compatibility CI | Release engineer | 4 | 180k | BR-0305, Wave 4 |

**Wave budget:** 1.24M tokens  
**Exit:** Release readiness is computable, attributable, and auditable.

### Wave 6 - Human validation and release candidate

**Schedule:** Weeks 12 to 16  
**Purpose:** Prove that the product is actually simple and reliable for people outside the project.

| ID | Task | Owner role | Days | Token cap | Depends on |
|---|---|---:|---:|---:|---|
| BR-0601 | Run five beginner install-and-first-project studies | UX lead | 5 | 180k | Waves 2 to 4 |
| BR-0602 | Run five engineer/team complete-lifecycle pilots | UX lead + reviewer | 5 | 200k | Waves 2 to 5 |
| BR-0603 | Run objective benchmark against Superpowers and two other leaders | Independent reviewer | 4 | 150k | Waves 2 to 5 |
| BR-0604 | Repair usability, contradiction, and compatibility findings | Delivery team | 8 | 500k | BR-0601 to BR-0603 |
| BR-0605 | Run security and release-readiness review | Independent reviewer | 4 | 160k | BR-0604 |
| BR-0606 | Cut release candidate, test clean install/update/rollback/uninstall | Release engineer | 3 | 120k | BR-0605 |
| BR-0607 | Publish only after every release gate passes | Product owner | 1 | 30k | BR-0606, directory acceptance |

**Wave budget:** 1.34M tokens  
**Exit:** Stable release or a documented no-go with the failed gate named.

### Total

The task caps above intentionally contain contingency. Their sum is exactly **7,410,000 tokens**, the program's hard ceiling, recomputed from the per-item caps rather than typed by hand. Planned use should remain around **6.2 million tokens** through reuse, deterministic generation, and early task splitting.

---

## 11. Release gates

### 11.1 Truth and security

- Zero known critical or high contradiction.
- Security documentation matches all network-capable code.
- All network imports are allowlisted and tested.
- No token, credential, or raw command output leaks into shared artifacts.
- Production mutation refusal remains effective across hosts.

### 11.2 Installation

- Claude directory installation is one click.
- Universal install is one command.
- No normal-path manual configuration.
- READY/PARTIAL/BLOCKED status is displayed.
- Repair, update, rollback, and uninstall are tested.
- Signed artifacts and provenance verify.

### 11.3 Beginner experience

- At least 4 of 5 beginner users install without assistance.
- At least 4 of 5 complete the first project scenario without external documentation.
- Median time from installation to first meaningful next action is under ten minutes.
- Every observed screen leaves the user able to answer, "What should I do next?"
- No beginner is required to understand dossiers, receipts, worktrees, or exit codes to proceed.

### 11.4 Engineering experience

- T0/T1 work remains lightweight.
- Engineers can opt into technical detail without losing guided state.
- Evidence is wrapper-generated and commit-bound.
- Two failed approaches trigger re-planning.
- Resume works after interruption or host change.

### 11.5 Team experience

- Every active task has an owner, reviewer, reason, budget, and status.
- Status identifies the critical path and blockers.
- Exceptions have owner, approver, expiry, scope, risk, and compensating control.
- PR and release summaries are generated from evidence, not memory.

### 11.6 Cross-host support

- All Tier 1 adapters pass the same lifecycle contract suite.
- A project started in one host can resume in another without loss of state.
- Unsupported capabilities appear as unavailable, never as passed.
- The canonical core contains no host-specific lifecycle forks.

### 11.7 Maintainability

- Command, lifecycle, verdict, and compatibility documentation is generated.
- No full CI workflow is copied manually into multiple guides.
- State schema migrations and rollback pass.
- A new adapter can be added without modifying core assurance behavior.
- The stable release branch is green on supported operating systems and Python versions.

### 11.8 Public readiness

- Signed stable tag exists and is immutable.
- Changelog, release notes, SBOM, checksums, provenance, migration, and rollback instructions ship together.
- Five beginner and five engineering validations are published with limitations.
- Marketplace listing and first-run experience use the same current product language.
- No unresolved blocker is waived solely to meet a release date.

---

## 12. Rules that minimize rework and token waste

1. **Freeze the engine before redesigning its presentation.** Fix critical defects, then wrap current behavior.
2. **Define contracts before adapters.** State, result, lifecycle, and capability contracts precede host work.
3. **Build vertical slices.** Each wave must produce a usable end-to-end improvement, not disconnected infrastructure.
4. **One work item, one reason.** Do not mix refactoring, UX, and new behavior in one task.
5. **No task above 200k tokens.** Split by independently testable acceptance criteria.
6. **Stop after two failed approaches.** Record what failed, return to the last verified state, and re-plan.
7. **Generated documentation only where code defines the truth.** Do not maintain repeated copies manually.
8. **Contract-test adapters.** Never validate a host through prose alone.
9. **No premature extension.** Do not build dashboards, hosted services, additional agents, or direct model clients before the release gates require them.
10. **Use deterministic tools for deterministic work.** Schema generation, docs, compatibility matrices, and status reports should not consume model tokens after their templates are defined.
11. **Review budget at 75 percent.** A task that has not passed one acceptance criterion by then is incorrectly scoped.
12. **Release gates cannot be forced.** A no-go is a valid program outcome.

---

## 13. What will not be built before stable release

To preserve focus, version 1 will not add:

- Autonomous merge or production deployment
- A hosted BrotherSBE control plane
- A separate web dashboard
- Direct API integrations for every model provider
- More reviewer agents without user evidence showing a missing review role
- More hard gates without a real escaped-defect class
- Additional dossier files
- A second state store
- Separate lifecycle logic per host
- Hidden behavior changes learned from telemetry

---

## 14. Final definition of done

BrotherSBE is finished for stable public release when a new user can:

1. Find it in Claude's plugin directory.
2. Click Install.
3. See a successful installation status.
4. Run `/brothersbe:start`.
5. Describe a project in normal language.
6. Follow one clear recommended action at a time.
7. Receive automated help through design, plan, implementation, evidence, review, and finish.
8. Understand every blocker and how to recover.
9. Resume the same project from another supported host.
10. Finish with a trustworthy summary, evidence, ownership, and a clear human-controlled merge or release action.

The internal sophistication may remain deep. The user experience must feel simple.

> The strongest product is not the one that exposes the most machinery. It is the one that uses the right machinery at the right time while the user always understands what happens next.

---

## 15. Current ecosystem references

The integration targets and distribution assumptions in this plan were checked on 2026-07-31 against current official sources:

- [Claude Code official plugin directory](https://github.com/anthropics/claude-plugins-official)
- [Claude plugin browser](https://claude.com/plugins)
- [OpenAI Codex](https://openai.com/codex/)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli)
- [Qwen Code](https://github.com/QwenLM/qwen-code)
- [Kimi Code](https://github.com/MoonshotAI/kimi-code)
- [OpenCode](https://opencode.ai/docs)

Interfaces and marketplace requirements can change. Adapter discovery tests and release checks, rather than these links, are the final source of compatibility truth.
