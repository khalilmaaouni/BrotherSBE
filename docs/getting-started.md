# Getting Started

This guide is the shortest path from installation to a real BrotherSBE engineering change.

Use a real repository and a real task.

## About the `sbe` command

The guided `/brothersbe:` commands need nothing beyond the plugin install.

The `sbe` CLI ships at `bin/sbe` inside the plugin. On most installs the plugin's `bin` directory is reachable; if `sbe` is not on your PATH, either run it by full path from the plugin cache, or clone the repository and use `bin/sbe`. Examples below write `sbe`; substitute your form.

```bash
sbe doctor
```

confirms the wiring either way.

## 1. Install

```bash
claude plugin marketplace add khalilmaaouni/BrotherSBE
claude plugin install brothersbe@brothersbe
```

Restart Claude Code if required after installation.

## 2. Open your repository

```bash
cd your-project
claude
```

## 3. Start

Inside Claude Code:

```text
/brothersbe:start
```

Use this command whenever you start or resume BrotherSBE work.

It returns one recommended next action rather than forcing you to memorise the command set.

## 4. Create the change directory

For this example:

```bash
mkdir -p design/order-reconciliation
sbe intake design/order-reconciliation
```

Answer the five risk questions.

BrotherSBE writes:

```text
design/order-reconciliation/00-intake.json
```

### Verify

Check that the intake file exists and that the tier matches the change you described.

If the risk answers are wrong, fix the answers before continuing. The tool cannot know that a human answered them incorrectly. Later, `sbe impact` reconciles the declared tier against what the diff actually touched, but that runs after code exists.

## 5. Design

Inside Claude Code:

```text
/brothersbe:design
```

For a higher-risk change, expect the design to cover some or all of:

```text
01-purpose.md
02-process.md
03-adr.md
04-technology-map.md
05-data-model.md
06-diagrams.md
07-verification.md
```

Then run the mechanical design check:

```bash
sbe design design/order-reconciliation
```

### Verify

Resolve every `FAIL`.

A design check verifies structure and required fields. It does not prove that the engineering judgement inside the document is correct. A one-sentence purpose brief passes the shape check; whether it says anything is on you.

For data work, manually confirm at minimum:

```text
grain
keys
system of record
relationship cardinality
downstream consumers
reconciliation approach
```

For backend work, manually confirm at minimum:

```text
contract
consumers
failure path
retry behaviour
compatibility
rollback
```

## 6. Implement

Inside Claude Code:

```text
/brothersbe:work
```

Use this after the design and plan are ready.

A BrotherSBE work brief gives a worker:

```text
scope
allowed paths
paths it must not touch
dependencies
acceptance criteria
verification command
stop conditions
```

### Verify

The implementation worker stays inside its declared scope and runs the verification command named in its brief.

The worker does not own merge or deployment.

## 7. Review

Inside Claude Code:

```text
/brothersbe:review
```

Or inspect routing directly:

```bash
sbe review-route --base origin/main
```

BrotherSBE routes specialist review from the diff. No model chooses the reviewer; the changed paths do.

Examples include:

```text
data-reviewer
backend-reviewer
migration-reviewer
security-reviewer
qa-reviewer
principal-architect
```

### Verify

Reviewers return findings. They are read-only and cannot edit the implementation they are reviewing.

Every important finding ends in either:

```text
code changed
```

or:

```text
decision recorded
```

## 8. Verify with evidence

Inside Claude Code:

```text
/brothersbe:verify
```

For an executable project check, register it once in `.sbe/checks.yml`, then run it through the evidence wrapper by id:

```bash
sbe evidence run --check reconcile-orders --out .sbe/evidence/reconcile-orders.json
```

The executable, its arguments, its working directory and the paths it covers all come from the registry entry. Nothing on the command line replaces them; that is what makes the receipt worth something.

An unregistered command can still mint advisory evidence:

```bash
sbe evidence run --out .sbe/evidence/adhoc.json -- ./scripts/reconcile_orders.sh
```

but a free-form run satisfies no required policy check.

### Read the verdict correctly

```text
PASS
```

The configured evidence exists and passed.

```text
FAIL
```

The check failed or the evidence is broken.

```text
NO-DATA
```

There is not enough evidence to make the claim.

`NO-DATA` is not a pass.

## 9. Check status

Inside Claude Code:

```text
/brothersbe:status
```

Or:

```bash
sbe status
```

Before merge, inspect:

```text
blockers
missing evidence
design consistency
review findings
verification results
unmeasured areas
stale evidence
```

Do not reduce the result to "CI is green."

Ask:

```text
What did we actually prove?
```

## 10. Human merge

BrotherSBE does not make the final merge decision.

The final decision stays with the humans and branch protection rules already used by the team.

## Your first useful test

Try BrotherSBE on one real change:

```text
Snowflake model
ELT pipeline
migration
backfill
reconciliation
backend API
partner integration
technical QA issue
```

After the change, answer:

```text
What did it catch?
What did it miss?
What felt unnecessary?
Which command was unclear?
Which evidence was useful?
Where would you still not trust it?
```

Next: **[Workflow Map](workflow-map.md)**
