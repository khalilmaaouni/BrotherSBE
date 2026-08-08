# BrotherSBE

**Design before code. Evidence before done.**

BrotherSBE is an engineering workflow for AI-assisted backend, data engineering, infrastructure, and technical QA work.

It helps teams use Claude Code for real engineering while keeping architecture decisions, verification, review, and merge control explicit.

BrotherSBE does not replace your engineers, QA, or CI/CD. It gives them a structured workflow and evidence they can inspect.

## Start engineering

Install BrotherSBE:

```bash
claude plugin marketplace add khalilmaaouni/BrotherSBE
claude plugin install brothersbe@brothersbe
```

Open Claude Code inside your project and run:

```text
/brothersbe:start
```

That is the main entry point.

BrotherSBE inspects the repository, understands whether you are starting or resuming work, and recommends the next action.

**[Run your first real change ->](docs/getting-started.md)**

**[See the complete workflow ->](docs/workflow-map.md)**

## Find your situation

| You are | Start here |
| --- | --- |
| New to BrotherSBE | [Getting Started](docs/getting-started.md), one real change from install to verification |
| Adding it to an existing repository | Run `/brothersbe:adopt`, which is a dry run by default, then [Adoption](docs/ADOPTION.md) |
| Upgrading an existing install | `claude plugin update brothersbe`, restart to apply, then [CHANGELOG.md](CHANGELOG.md) and [Migration](docs/MIGRATION.md) |
| Wiring it into CI | [CI/CD](docs/ci-cd.md), then [CI-ORDER.md](docs/CI-ORDER.md) for the exact step order |
| Just looking around first | [A worked engagement](docs/guides/05-a-worked-engagement.md), one system designed end to end with real output |

## The engineering loop

```text
START
  |
INTAKE
  |
DESIGN
  |
IMPLEMENT
  |
REVIEW
  |
VERIFY
  |
STATUS
  |
HUMAN MERGE
```

The amount of process scales with risk. A small change should stay small. A change affecting money, production, data models, contracts, migrations, or multiple consumers should carry more design and evidence.

## Why BrotherSBE?

AI can generate implementation faster than most teams can verify it.

BrotherSBE focuses on the parts that become harder as AI output increases:

- **Design before implementation**: purpose, architecture, contracts, data grain, systems of record, and verification are made explicit first.
- **Scoped implementation**: human and AI workers get clear ownership, paths, dependencies, acceptance criteria, and verification commands.
- **Specialist review**: data, backend, migration, security, architecture, and QA review are routed from the actual change, not chosen by a model.
- **Evidence before done**: important claims are backed by checks that actually ran, recorded as receipts.
- **Three evidence states**: `PASS`, `FAIL`, and `NO-DATA`. Missing evidence is never silently treated as success.
- **Human control**: BrotherSBE does not merge, approve, or deploy.

## Where it helps

### Snowflake and ELT

Make data engineering assumptions explicit before SQL is generated: grain, keys, system of record, cardinality, incremental logic, backfill and migration strategy, reconciliation, downstream consumers, verification.

For important numbers, use a pinned warehouse state and a genuinely different second derivation rather than validating a query by running the same logic twice.

**[Snowflake and ELT guide ->](docs/snowflake-elt.md)**

### Technical QA

```text
Requirement
  |
Acceptance criteria
  |
Executable check
  |
Execution
  |
Evidence
```

Technical QA challenges negative paths, retries, timeouts, duplicates, partial failures, schema drift, recovery, and whether the test actually proves the requirement.

**[Technical QA guide ->](docs/technical-qa.md)**

### CI/CD

Start with BrotherSBE in advisory mode. Learn what it catches and what it misses.

Only move selected checks into strict mode after the team trusts them.

Your branch protection, repository permissions, and CI/CD remain the enforcement layer.

**[CI/CD guide ->](docs/ci-cd.md)**

## Documentation

- **[Getting Started](docs/getting-started.md)**: install BrotherSBE and run one real change from start to verification.
- **[Workflow Map](docs/workflow-map.md)**: command order, purpose, output, and verification point for each stage.
- **[Command Reference](docs/commands.md)**: quick reference for guided commands and CLI commands. The full CLI surface is in [docs/CLI.md](docs/CLI.md).
- **[Snowflake and ELT](docs/snowflake-elt.md)**: practical data engineering workflow and validation examples.
- **[Technical QA](docs/technical-qa.md)**: requirement-to-evidence workflow for QA and validation.
- **[CI/CD](docs/ci-cd.md)**: advisory rollout, evidence, and strict enforcement. The exact CI step order is in [docs/CI-ORDER.md](docs/CI-ORDER.md).
- **[A worked engagement](docs/guides/05-a-worked-engagement.md)**: one system designed end to end, with the real commands and the real output.
- **[The sandbox](docs/guides/00-sandbox.md)**: rehearse the loop on a disposable dossier before touching real work.
- **[The booklet](docs/fieldbook/BrotherSBE-Booklet.html)**: the full story for a team deciding whether to adopt: outcomes, personas, the team operating model, and the trust mechanics.
- **[The engineering reference](docs/ENGINEERING-REFERENCE.md)**: the complete documentation of the method, the gates, the laws, and every install path. Nothing was cut when this README was shortened; it all lives there.

## First team test

Do not start with a toy project.

Pick one real change such as:

- Snowflake transformation
- ELT pipeline change
- data reconciliation problem
- migration or backfill
- backend API change
- partner integration
- CI/CD change
- technical QA problem

Run it through the workflow and tell us:

What was useful? What was confusing? What was too heavy? What did BrotherSBE miss? Where would you still not trust it?

## Status

BrotherSBE is an early engineering system, tested on itself.

The controls and commands are covered by the test suites in this repository and run in CI on Linux and Windows. Platform-specific patterns such as Snowflake integration still need real-world validation against actual engineering estates.

Every limit the checks cannot cover is written down in [docs/KNOWN-LIMITS.md](docs/KNOWN-LIMITS.md). The goal is not to claim more than the evidence supports.

**Design before code. Evidence before done.**
