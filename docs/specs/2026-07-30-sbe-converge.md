# sbe converge: does the code still match the approved design

Status: spec of record for Loop 4 of the First-Rank Essentials program
(Release B, capability 4). The fixtures in tools/test_sbe_converge.py and the
implementation in src/brothersbe/converge.py both read from here.

## Command

    bin/sbe converge <dossier-dir> --base <sha> --head <sha> [--json] [--cwd <repo>]

Both shas are required and must resolve; convergence over a guessed range is
not a comparison, it is a hope. The verdict set is the impact verdict set:
PASS, FAIL, REVIEW-REQUIRED, NO-DATA. Exit 0 only for PASS.

Output: one verdict line per dimension (SCOPE, CONTRACTS, DATA, ARCHITECTURE,
VERIFICATION), then FINAL: FAIL beats REVIEW-REQUIRED; NO-DATA is the final
verdict only when EVERY dimension was NO-DATA (nothing was comparable at
all); otherwise a PASS stands and lists its NO-DATA dimensions by name as
not examined, because a range with no contract change must not be blocked
for the silence of a dimension that had nothing to read. A report is written to <dossier-dir>/09-convergence.json bound to
repository identity, base, and head; every finding names its evidence source
(file, symbol, operation, receipt id, commit) because a hard verdict without
a citable fact is an opinion, and opinions are advisory here by law.

## SCOPE (deterministic)

Changed paths over base..head (the impact module's diff machinery) compared
against: the plan's union of owned paths (08-plan.json when present) plus the
paths the dossier itself names (the same backticked-path rule sbe plan uses).
- changed and planned: listed as in scope
- changed, unplanned, but matching no detector: REVIEW-REQUIRED, "unplanned
  but potentially legitimate", each file named
- unmeasured file types (no detector covers them): named as unmeasured,
  never silently counted as clean
- no plan and no dossier-named paths: NO-DATA (nothing to converge against)

## CONTRACTS (deterministic where the format is parseable)

For changed contract-shaped files (the impact detectors decide what is
contract-shaped): when the file parses as JSON OpenAPI at BOTH base and head
(git show at each sha), diff the operation set (method plus path):
- an operation REMOVED or an existing operation's schema changed, with no
  mention of that operation or path in any dossier artifact or plan task:
  FAIL, a direct contradiction (the status example in the essentials program
  is exactly this: an unplanned DELETE operation)
- an operation ADDED undocumented: REVIEW-REQUIRED
- a contract file that does not parse as JSON at either sha: unmeasured by
  name (YAML has no stdlib parser; this project does not guess), and the
  dimension cannot claim PASS while any changed contract file is unmeasured;
  it says REVIEW-REQUIRED naming the unread file.
- no changed contract-shaped files: NO-DATA prose ("no contract change to
  examine"), which is not a pass and not a failure.

## DATA (deterministic, narrow on purpose)

For changed migration-shaped files (impact detectors): scan head-side content
for DROP TABLE <name> and DROP COLUMN <name> statements (case-insensitive,
word-boundary). A dropped name that is still a documented entity or attribute
in 05-data-model.md at head: FAIL, migration/data-model contradiction, naming
the entity and both files. A migration change with no 05-data-model.md in the
dossier at all: FAIL (the dossier is claiming a data change needs no data
model, which the tier rules already refuse). No migration-shaped changes:
NO-DATA prose.

## ARCHITECTURE (honestly limited)

Declared components come from 06-diagrams.md (the sbe_design parsing
helpers). If declared components exist, any NEW top-level source directory
appearing in the changed paths (a directory not present at base) that
matches no declared component name is REVIEW-REQUIRED naming it. Everything
deeper (technology choices, dependencies, infrastructure, recovery) is
NO-DATA with the limit stated: this comparison reads names, not intent.
docs/KNOWN-LIMITS.md carries this limit verbatim.

## VERIFICATION (deterministic, the sharpest teeth)

For every plan task with verificationCommands: a receipt must exist in the
evidence store (.sbe/evidence, the existing evidence module) that
- loads and carries a seal matching its own run facts (the receipt is read
  directly rather than through evidence.verify, because verify binds to the
  CURRENT head of the tree and converge assesses an explicit --head that may
  lawfully differ),
- binds to the assessed head sha exactly,
- covers every file its task owns, whenever the task owns any (a receipt
  recording other files is evidence about the wrong files and FAILs naming
  the uncovered paths),
- recorded exit 0.
A missing receipt is FAIL naming the command. A receipt bound to another
commit is FAIL naming both shas (stale evidence). No plan or no tasks with
commands: NO-DATA prose. An LLM statement, a chat log, or a human assertion
is not a receipt and never substitutes.

## Amendment flow, and the absence of force

There is no flag that turns divergence into PASS, and none may be added. A
legitimate deviation is legalized only by amending the dossier (which moves
its digests), regenerating the plan (sbe plan --write; freshness would FAIL
otherwise), regenerating the evidence against the new head, and re-running
converge. The fixture for this is a full round trip: diverge, FAIL, amend,
regenerate, PASS, with every intermediate verdict asserted.

## Essential fixtures (tools/test_sbe_converge.py)

unplanned file REVIEW-REQUIRED by name; undocumented removed OpenAPI
operation FAIL and undocumented added operation REVIEW-REQUIRED; DROP of a
documented entity FAIL naming it; missing receipt FAIL; receipt bound to the
wrong commit FAIL naming both shas; unparseable contract file reported
unmeasured and never PASS; the valid amendment round trip; determinism (two
runs, identical report bytes apart from nothing: the report carries no
timestamps for exactly this reason); both shas required (usage error
otherwise); no force flag (argparse refuses one); the FINAL rule (FAIL beats
REVIEW-REQUIRED, NO-DATA only when every dimension was silent, PASS naming
its silences) pinned by the scenarios above.
