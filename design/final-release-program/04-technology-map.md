# 04. Technology map

Every component below exists on main today. Nothing here is planned work; the
loops in 02-process.md change these parts, they do not introduce new ones. Line
numbers were read in this worktree with `wc -l src/brothersbe/*.py tools/sbe_gate.py`.

## Components

| Component | Where it lives | Owner | Failure mode | Recovery path |
|---|---|---|---|---|
| ProjectLocator | src/brothersbe/status.py, `_design_roots` at line 478 and `_team_changes` at line 509 | Loop 3, design stage writes the contract | Two functions resolve the same repository to different projects, so `sbe status` and `sbe status --team` disagree about which change is being discussed | Loop 3 replaces both with one function that handles the flat layout, the nested design layout, worktrees, and a broken state with recovery guidance |
| LifecycleEvaluator | src/brothersbe/status.py, 854 lines | Loop 3, design stage writes the contract | The stage and the next action are worked out here and again, independently, inside the guided skills, so the two can print contradictory next actions for one repository | Loop 3 makes this the only evaluator and has every surface render its answer |
| EvidenceWrapper | src/brothersbe/evidence.py, 826 lines | Loop 2, writer stage | A receipt records the command line it ran but not the kind of check it was, so the consumer has to guess from a substring | Loop 2 adds a recorded check-kind field; the old bypass is kept as a fixture that must stay red under the old behaviour |
| ReceiptClassifier | src/brothersbe/status.py, `_receipt_kinds` at line 107 | Loop 2, writer stage | Matches substrings of the recorded command line, so a command that runs no check at all can clear the design, gate and score obligations | Loop 2 makes it read the recorded field and stop reading the command line |
| HardGates | tools/sbe_gate.py, 1559 lines, gates numbers, migration, approval and ran | Loop 2, writer stage | Its own evidence files carry no commit binding, so a stale or hand-copied file passes a gate that is supposed to prove a fresh run | Loop 2 commit-binds them, or routes them through EvidenceWrapper so they inherit the binding that already exists there |
| DesignChecks | tools/sbe_design.py, checks artifacts, adr, datamodel, diagrams and placeholder | Loop 3, design stage | Reads the intake tier with its own reader, which can disagree with the reader in the status surface about the same 00-intake.json, in the opposite direction | Loop 3 gives both one shared tier reader |
| DecisionStore | src/brothersbe/decisions.py, 2106 lines | Loop 2, writer stage | Allocates sequential numeric identifiers by scanning the store with no lock; the module docstring at lines 1154 to 1157 states that a second concurrent write lands on top of the first | Loop 2 adds the file lock pattern already used by Telemetry, proved by a multi-process stress test |
| TaskRegistry | src/brothersbe/tasks.py, 621 lines; evidence directory default `.sbe/evidence` at line 72 | Loop 2, writer stage | Last write wins on concurrent registry writes, by its own admission | Same lock pattern, same stress test |
| ConvergenceCheck | src/brothersbe/converge.py, 544 lines | Loop 3, design stage | Cannot require a current review, because no durable review record exists for it to read | Loop 3 adds the record and makes this check require it, along with fresh evidence, no open tasks and no expired waivers |
| CommandSurface | bin/sbe and src/brothersbe/cli.py, 968 lines, 25 subcommands | Loop 4, writer stage | Six separate JSON outputs with no shared envelope, so a consumer parses six shapes | Loop 4 unifies them behind one versioned result envelope |
| GuidedSkills | skills/, ten skill directories: adopt, design, help, kickoff, learn, next, review, start, status, verify | Loop 3, then Loop 4 | Each skill re-derives the stage ladder in prose, so a change to the lifecycle has to be made in code and again in ten skill files | Loop 3 moves the ladder into code and leaves the skills rendering the computed answer |
| MapTemplate | skills/help/map-template.html, the offline eleven-slot visual surface | Loop 4, writer stage | Renders a state it derives itself, so it can drift from what the command line prints | Loop 4 makes it render the canonical state, proved by parity fixtures |
| PullRequestVerifier | src/brothersbe/prverify.py, 692 lines; the GitHub call is at line 120 | Loop 1, writer stage | It performs a network call, which SECURITY.md line 11 denies; docs/KNOWN-LIMITS.md already states the truth, so the documents contradict each other | Loop 1 scopes the security claim to name this path and install.sh as the two exceptions, and adds a named allowlist entry so the zero-network scan can cover src/ without failing on it |
| GatesWorkflow | .github/workflows/brothersbe-gates.yml | Loop 1, writer stage | Names three of the 17 files `ls tools/test_*.py` returns, at lines 143, 150 and 152, so 14 documented protections never execute on any merge | Loop 1 wires the remaining suites into the workflow |
| Telemetry | tools/sbe_telemetry.py, the outcomes ledger and its file lock | Loop 2 reuses its lock pattern | A ledger append that raced would lose a line, which is why the lock exists here first | Already solved here; the fix in Loop 2 is to reuse it rather than reinvent it |

## Source systems

| System | What it masters | Interface | Availability expectation | Failover |
|---|---|---|---|---|
| ProgramLedger | The program's waves, budgets and status; program/PROGRAM.yaml, with program/MASTER-PLAN.md as its stated source of truth for scope | A file in the repository | Always available; it is a committed file | If it disagrees with the master plan, the master plan wins and the ledger is corrected in the same change |
| WorkItemStore | The individual work items; program/work-items/, seven YAML files today | Files in the repository | Always available | An item missing from the ledger is a ledger defect, not a licence to work without one |
| EvidenceStore | The receipts, under `.sbe/evidence` | Written by EvidenceWrapper, read by ReceiptClassifier and HardGates | Always available | Receipts committed in the tree are self-poisoning today: each committed receipt becomes a covered file of the next diff, which lands earlier receipts in the broken-claims list. Loop 2 either excludes the store from the covered-file diff or moves the receipts out of the committed tree |
| GitHistory | Commits, tags and branches; the identity every receipt and review record binds to | The git command line | Always available locally | A machine with no git gets an honest absence rather than a crash; src/brothersbe/status.py already renders that as NO-DATA with a reason |
| HostedRunner | The merge gate result; GitHub Actions running GatesWorkflow across ubuntu-latest and macos-latest, Python 3.9 and 3.x | Network, outside the product | Not guaranteed; the service is external | A red or unavailable hosted run blocks the release rather than being waived. The 3.9 leg blocks; the 3.x leg is informational by founder decision recorded in the workflow comments at lines 51 to 55 |

## Failure modes this map does not fix

Two are named here because they belong to no single component. First, the
security documentation and the code are separate artifacts with no mechanical
link, so a true sentence today can become false tomorrow without anything
noticing; Loop 1's planted-import fixture is the control that closes it. Second,
14 of the 17 test suites are prose protections rather than enforced ones until
Loop 1 wires them, and until then any claim resting on them is a claim nothing
recomputes.

## Recovery posture

The program's recovery target is a working tree, not a running service. If a loop
goes wrong, recovery means returning main to its last green commit and re-running
the battery, which is minutes rather than hours, and the state that must survive
is the evidence: receipts, decision packages and, after Loop 3, review records.

The drill that proves it is the upgrade and rollback harness already wired into
GatesWorkflow at line 165. It has only ever taken its NO-DATA branch, because no
release tag has ever been on main's ancestry, and Loop 0 fixed that precondition.
Loop 5 is the first time that harness runs its real path, and until it does, the
rollback claim is unproven and is recorded as such rather than assumed.
