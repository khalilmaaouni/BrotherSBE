---
slug: the-commands
title: The commands
part: "2"
verified-against: 1.0.0-rc.28
---

# The commands

Both tables below are generated. Nobody typed them, and if the command surface
moves without this book being regenerated, `sbe book --check` fails in CI and
names the file that moved. That is the only reason you should believe them.

## The guided surface, which is where you start

You do not need any of the command-line surface to use BrotherSBE. These are
the slash commands inside Claude Code, and one of them is enough on day one.

<!-- BEGIN GENERATED FIELDBOOK guided-commands -->

| Command | When to reach for it |
|---|---|
| `/brothersbe:adopt` | Use when installing BrotherSBE into a repository that has not used it before, or when checking whether an existing installation is actually wired up |
| `/brothersbe:design` | Use when the shape of a system is being decided or reviewed: a purpose brief, a process map, an architecture decision record, a technology map, a conceptual to logical to physical data model, diagrams as code, or a verification plan |
| `/brothersbe:handover` | Use when someone wants to hand this change's ownership to another named human, or when a receiver wants to inspect and accept or reject a handover already prepared for them |
| `/brothersbe:help` | Use when someone asks what BrotherSBE is, how it works, or which command or skill to use |
| `/brothersbe:kickoff` | Use at the start of any backend, infrastructure, or data engineering task, before designing or writing anything |
| `/brothersbe:learn` | Use when a lesson from an incident, a repeated correction, a review finding or a measured outcome should become a shared rule, or when a session wants to propose an amendment to the laws |
| `/brothersbe:next` | Use when someone asks what to do next in a BrotherSBE project |
| `/brothersbe:review` | Use when reviewing a diff, a pull request, or a colleague's change against the design it claims to implement |
| `/brothersbe:start` | Use as the single entry point when someone wants to begin or resume work with BrotherSBE and does not know, or does not care, which command comes next |
| `/brothersbe:status` | Use when someone wants to know where a BrotherSBE project stands |
| `/brothersbe:verify` | Use when work is about to be called done, a figure that could reach a decision has been produced, a schema migration is part of the change, the change touches money or a partner path, or a verification plan is being written |
| `/brothersbe:work` | Use when someone wants BrotherSBE to execute ready plan tasks with implementation workers, not just recommend or design them |

<!-- END GENERATED FIELDBOOK guided-commands -->

If you remember one, remember `/brothersbe:start`. It reads the ground, works
out whether you are resuming or beginning, and hands back exactly one
recommended next action. Not a menu. One action, why it is the one, what
happens automatically, what decision stays yours, and how success will be
checked.

## The command line, for when you want the machinery directly

Everything the guided surface does is reachable as a subcommand, and CI uses
these directly.

<!-- BEGIN GENERATED FIELDBOOK cli-commands -->

| Command | What it does |
|---|---|
| `sbe adopt` | inspect a repository for installation readiness, dry run by default |
| `sbe book` | the field book: regenerate the explainer whose command, role, check and limit tables are derived from canonical state; `--check` fails when a bound source moved without a regenerate |
| `sbe converge` | does the code between two commits still match the approved dossier: scope, contracts, data, architecture, verification |
| `sbe decide` | run a decision table (delegates to sbe_decide.py) |
| `sbe design` | the design completeness check (delegates to sbe_design.py) |
| `sbe doctor` | check this installation and the environment it will run in |
| `sbe evidence` | run a command and write the receipt it earned, verify one, or show one |
| `sbe exceptions` | list exceptions, their owners and their expiry |
| `sbe explain` | print the decision package for a decision id, or for a gate or check name, regenerating one from the shipped registry when no run has written it |
| `sbe fences` | print the live fences the write hook would enforce |
| `sbe gate` | one hard gate by name, or all of them over a directory |
| `sbe handover` | explicit human handover: prepare, show, acknowledge, reject; ownership stays with the outgoing owner until a named human receiver acknowledges |
| `sbe impact` | read the git diff and reconcile it with the declared intake tier |
| `sbe init` | install BrotherSBE's local footprint into a repository, dry run by default |
| `sbe inspect-change` | alias of impact, the name the finalization brief uses |
| `sbe instruction-surface` | did a changed CLAUDE.md, .claude/**, .mcp.json, .claude-plugin/**, hooks/**, agent or skill definition, CODEOWNERS or CI workflow stay inside declared, reviewed scope (delegates to sbe_instruction_surface.py) |
| `sbe intake` | score the five intake questions into a tier |
| `sbe lineage` | walk the chain for one artifact oldest to newest: binding, receipts, decisions, notes and commits, with an evidence pointer on every hop |
| `sbe map` | a deterministic, offline HTML status page built from canonical state only: sbe map --out FILE |
| `sbe plan` | derive the task plan from a dossier and validate it (delegates to sbe_plan.py) |
| `sbe policy` | evaluate .sbe/policy.yml against a diff: which checks, tiers and approvals this change is REQUIRED to carry, and whether they are there |
| `sbe pr` | pull-request surfaces: pr verify <number> --repo owner/name checks live GitHub approval evidence, bound to the head commit |
| `sbe program` | program-wide status from the ledger: gantt, finished, in flight, blocked, risks with mitigations, docs, budget; `check` fails when STATUS.md drifted |
| `sbe protections` | is the repository itself protecting the control plane: protections verify --repository owner/name --branch main reads CODEOWNERS locally and the branch ruleset through gh api |
| `sbe review` | run the scored surface including soft findings, plus the gates |
| `sbe review-route` | deterministic reviewer selection from a diff: no model chooses, at most two specialists, zero is a legal result, never claims a clean review |
| `sbe scope` | did the changes that survived stay inside declared scope: scope verify --base REF [--head REF] [--strict] is the CI backstop for the Bash and Stop write boundary, scope report says what the Stop hook would decide right now (delegates to sbe_session_reconcile.py) |
| `sbe score` | the scored surface (delegates to sbe_score.py) |
| `sbe status` | blocker-first summary of where a change stands, read from recorded state |
| `sbe task` | the write-scope registry: open, list, fence, check, and close with the diff-against-declaration postcondition |
| `sbe verify` | run the design check and the hard gates over a directory |
| `sbe version` | print the version, or move every version declaration site at once (version bump <new>) |
| `sbe work` | isolated implementation for one plan task: start, check, finish, remove, and never a merge |

<!-- END GENERATED FIELDBOOK cli-commands -->

## The four you will actually use

Out of that whole list, a working engineer touches four:

```bash
sbe status          # where does this change stand, blockers first
sbe verify .        # the design check and the hard gates over a directory
sbe review          # the scored surface, including soft findings
sbe evidence run --check <id> -- <command>   # run a check and mint its receipt
```

`sbe status` leads with what is broken, not with what passed. `sbe verify` is
advisory locally and enforcing in CI. `sbe evidence run` is the one that
matters most in practice: it runs a *registered* check, resolved from the
registry rather than from whatever you typed beside it, and records the
receipt. There is no argument on that path that changes what runs, which is
the point. A receipt that could be minted for `true` proves nothing.
