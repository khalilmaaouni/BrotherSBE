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

### If you would rather rehearse first

This guide uses a real repository and a real task on purpose, because that is where BrotherSBE either earns its place or does not. Two lighter on-ramps exist if you want one:

- [The sandbox](guides/00-sandbox.md) walks a disposable dossier end to end, so you can see the whole loop without touching work that matters.
- [A worked engagement](guides/05-a-worked-engagement.md) reads one system designed from purpose to verification, with the real commands and their real output, before you run anything yourself.

Your first *team* test should still be a real change. Rehearsal is for learning the shape of the loop, not for deciding whether it helps.

## 4. Create the change directory

For this example:

```bash
mkdir -p design/order-reconciliation
sbe intake design/order-reconciliation
```

Answer the five risk questions. A real run, on a change that touches money and has many consumers:

```text
Does this change a data model, an API contract, or a file interface others depend on? (y/n) y
Does it cross a service, system, or team boundary? (y/n) y
Is it reversible in under an hour? (y/n) n
Does it touch money, partner data, personal data, or production state? (y/n) y
How many downstream consumers break if it is wrong? (none/some/many) many

tier T3 (artifacts required: 01, 02, 03, 04, 05, 06, 07) written to design/order-reconciliation/00-intake.json
```

Your answers will differ, and so will your tier. That is the point: the tier is computed from what you answered, not chosen by whoever is in a hurry. Most changes come back T0 and owe nothing.

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

Run before you have written anything, this is what a real failing check looks like:

```text
BROTHERSBE DESIGN CHECKS  (advisory unless --strict; NO-DATA is never a pass; WAIVED is not a pass either)
  artifacts  FAIL     tier T3 requires 01, 02, 03, 04, 05, 06, 07; missing: 01-purpose.md,
                      02-process.md, 03-adr.md, 04-technology-map.md, 05-data-model.md,
                      06-diagrams.md, 07-verification.md [severity: gate]
  adr        NO-DATA  no 03-adr.md in this dossier [severity: gate]
  datamodel  NO-DATA  no 05-data-model.md in this dossier [severity: gate]
```

Read the two verdicts apart, because they mean different things. `FAIL` says a required artifact is missing and names every one. `NO-DATA` says the check had nothing to read, which is not a pass and not a failure. Once the artifacts exist, those NO-DATA lines become real verdicts about their content.

### Verify

Resolve every `FAIL`.

**If this fails and you cannot see why:** the message names what it counted and what it expected. Fix the file it names and re-run. A check that reports NO-DATA is telling you it found nothing to examine, so the fix is usually a missing file rather than a wrong one.

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

but a free-form run satisfies no required policy check, and it tells you so rather than letting you assume otherwise. A real free-form run:

```text
sbe evidence run: FREE FORM run: no registered check, so this receipt is advisory
and satisfies no required policy check
sbe evidence run: receipt written to ev.json. Trust LOCAL-ADVISORY. Command exited 0
in 0.456s. Declared check kind(s): none, so this receipt clears no design, gate or
score obligation. stdout and stderr are recorded as digests only.
```

That paragraph is the receipt telling you exactly how much it is worth. Register the check and run it by id, and the same command earns a receipt that clears an obligation.

**If this reports NO-DATA:** confirm the check is registered in `.sbe/checks.yml` under the id you passed, and re-run by id. NO-DATA on evidence almost always means the registry entry is missing, not that the command failed.

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

## When a step does not work

Work down this ladder; each rung is cheaper than the one below it.

1. **Read the verdict line.** Every check names what it examined and what it expected. Most failures are answered there.
2. **`sbe doctor`** for anything that looks like wiring rather than content: a command not found, a path it cannot reach, a tool version it cannot read.
3. **`/brothersbe:help`** inside Claude Code when the workflow itself is unclear rather than one command.
4. **[Known limits](KNOWN-LIMITS.md)** when a check passed and you do not believe it, or failed and you think it should not have. Every gap the checks cannot cover is written down there, by name.
5. **Open an issue** on the repository with the verdict line and what you expected.

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
