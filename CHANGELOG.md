# Changelog

Newest first. Each entry names the behavior that changed and the check or test
that proves it, because a changelog line nothing can verify is a press release.
What this file does NOT record: internal working notes and measurements from
the estates this project was built on, which stay untracked by the publish
checklist's own rules.

## Unreleased

- The book grew its persona spine: Part IV, one deep dive each for the
  backend engineer, the data engineer, and the platform lead, and Part V,
  working as one team, the vault opened in Obsidian for real, and the
  mastery ladder. Six new chapters, roughly twenty two thousand words,
  every terminal excerpt re-executed by the replay harness (142 blocks,
  0 differ) and the two blocks the day's other changes made stale patched
  from live runs, never by hand. The cover and the explainer route each
  persona to their chapter.

- The team operating model is designed end to end and recorded the tool's
  own way: a full dossier at design/team-operating-model (real intake, a
  deliberate recorded raise to T3, strict design check green on all five
  gates), the human-facing docs/TEAM-PLAYBOOK.md, three integration work
  items (Jira and Confluence, Asana, Teams) designed against research from
  opened vendor pages with every unverifiable limit named, and the team
  vault pattern shipped in memory-template/TEAM-VAULT.md. Zero engine code
  changed; the stance is one way: the ledger broadcasts, it never obeys.

## 1.0.0-rc.2 (2026-08-01)

Everything below accumulated in one pre-release stretch. `v1.0.0-rc.1`
(commit `dacee900`, 2026-07-31) was cut partway through this list and is
superseded by this release before any general announcement.

- The explainer grew from a leaflet into a field guide, and help learned to
  draw a map. `docs/explainer/index.html` is now twelve sections behind a
  table of contents: a ninety second story, the whole journey end to end
  with real excerpts lifted from the replay-tested book and labeled as real,
  loop advice, an honest good-at and not-good-at table, six use cases, three
  follow-along tutorials on the book's estate, and a co-writing section for
  developers; its self-containment guard is unchanged and still bites. The
  help skill gained a build-the-map flow with a shipped template
  (`skills/help/map-template.html`, eleven slots, honest absent-sentences,
  held by `TestHelpMapTemplate`); filling it writes an offline
  `brothersbe-map.html` into the user's project. The README names the
  session-start version-change announcement beside the update command, and
  `program/DIRECTORY-SUBMISSION.md` records the verified truth about
  listing: the official directory is curated with no application process,
  the community marketplace takes submissions through a web form, packet
  prepared for the product owner's click.

- Install docs now teach only the paths that were run, not the paths that
  seemed plausible. README, `docs/SETUP.md`, `docs/ROLLOUT.md`, and
  `docs/RELEASE.md` name the marketplace add plus install pair as the
  primary path, because that pair was executed end to end in an isolated
  config directory on 2026-08-01 (marketplace add exit 0, install exit 0,
  plugin listed 1.0.0-rc.1 enabled, content verified at main head 71f4d3f
  with all ten skills), and `scripts/test-install-artifact.sh` passed for
  that same commit. Stale tag claims in `docs/ROLLOUT.md` and
  `docs/RELEASE.md` are corrected: `v1.0.0-rc.1` lags main by 9 commits and
  a fresh tag is a decision for the product owner, not a fact to assert.
  Two guided skills are fixed to match what they actually do: `adopt` now
  runs its own command instead of describing one, and `next` explains its
  recommendation in plain words before the command. A new beginner
  explainer page ships at `docs/explainer/index.html`, a single
  self-contained file held by a new guard, `TestExplainerSelfContained`,
  that proves it carries no external reference and no em or en dash. The
  program ledger gains three work items (`BR-0201`, `BR-0301`, `BR-0310`)
  alongside `BR-0000`, each recording what shipped this train and what is
  still open by name. Held by `python3 tools/test_sbe_book.py` and a dash
  scan over every file this entry touches.

- `sbe impact --strict` no longer fails a run over pure absence. A NO-DATA
  verdict whose derived answers are all at their lowest values (a docs, data or
  test-only diff no detector covers, or an empty diff) now exits 0 under
  `--strict`, with a stderr sentence saying so; a NO-DATA carrying detector
  hits that propose a tier above T0 with no intake to reconcile them against,
  and a diff that could not be read at all, both still exit 1. Before this,
  every docs-or-data pull request through the consumer workflow went red:
  `bin/sbe impact . --json --strict` exited 1 with verdict NO-DATA and every
  derived answer at its lowest value, which graded absence, and this project's
  law is that NO-DATA never decides an exit code. The strict semantics are now
  documented in full in `docs/CLI.md`'s impact section (they were not written
  down anywhere before), and the consumer workflow's comment states them where
  the flag is set, so the change is visible in the workflow diff a human
  reviews, per L16. Held by `TestStrictOverAbsence` in
  `tools/test_sbe_impact.py`, four fixtures, calibrated by reinjecting the old
  exit rule: exactly the two absence fixtures went red, the two
  evidence-still-blocks fixtures stayed green, and the fixed file was restored
  with a matching SHA256 before and after.

- A decision can now be read back on demand and traced end to end. `sbe explain
  <id|gate|check>` prints a recorded decision package, or, when no run has
  written one, regenerates a package from the shipped registry with the verdict
  section marked NO-DATA, because no run has been made; a package bound to a
  different commit is never overwritten, the new one allocates the next id and
  names the one it supersedes, so packages stay append-only. `sbe lineage
  <artifact>` walks the task binding, evidence receipts, decision packages,
  notes and git commits oldest to newest with an evidence pointer on every hop;
  an absent store, including the notes store that ships in Loop 4, renders one
  named NO-DATA hop rather than a silently shorter chain, and a receipt that
  fails verification stays visible as a broken-receipt hop. Four calibrated
  evals feed each new control its defect: a WAIVED trigger packaged as PASS, a
  line outside the verdict grammar copied into a package, a package rewritten
  under an older commit, and a lineage hop carrying no evidence pointer. The
  command table in `docs/CLI.md` gains both rows, and every shipped doc that
  prints the eval count now prints the live 521, recomputed from a run rather
  than typed. Loop 2, tasks 5 to 8 of 8. Held by `TestExplain`, `TestLineage`,
  the four eval cases above, and the doc-count eval
  `no-shipped-doc-prints-an-eval-count-the-suite-does-not-produce`.

- The product now opens with a guided layer instead of a command inventory.
  Four new skills route a person who does not know the machinery into the
  machinery that exists: `/brothersbe:start` detects prior state and resumes it
  or asks for the outcome in plain language, `/brothersbe:next` walks a fixed
  priority ladder and returns exactly one recommended action with its reason,
  `/brothersbe:status` reframes the status command as a plain answer with one
  next action, and `/brothersbe:help` explains the product before it lists it.
  No engine file changed: the skills wrap commands that already ship, per the
  master plan's rule to wrap the proven engine rather than rewrite it. The
  README's first screen now answers what this is, why a beginner should care,
  and the one first move, with the full engineering reference intact below a
  named divider. The public release program itself is tracked in `program/`
  (the founder's master plan verbatim, PROGRAM.yaml, and work items), with the
  unbuilt parts of its section 9 named as unbuilt in program/README.md. Held by
  the existing frontmatter, citation-drift, and YAML tests over `skills/`, the
  eval battery, and the manifest check.

- The other two decisions worth recording now record themselves: a tier raised
  or disposed by `sbe impact`, and a forced task close. Both go through helpers
  that return nothing and are invoked as bare statements, so neither can move an
  exit code, and both catch every exception class and say so rather than
  escaping. Two honesty rules are enforced where they are easy to get wrong: a
  raise whose disagreements are all disposed is recorded WAIVED, never the PASS
  the impact report prints, because copying PASS onto a suppressed control is
  exactly the defect these packages exist to catch; and a forced record that
  CLAIMS a PASS, or carries no verdict at all, is recorded NO-DATA with the
  claim named rather than believed. Under `--json` the package still gets
  written and its sentence goes to stderr, so machine-readable stdout stays
  parseable. Loop 2, task 4 of 8. Held by `TestOtherTriggers`, calibrated by
  eight deliberate breaks with none uncaught. Two of the book's terminal blocks
  print those commands and are regenerated from live runs in the same change

- A failing or waived gate now writes its own decision package, without the
  writing ever being able to change what the gate decided. `sbe verify`, `gate`
  and `score` tee their delegate's output, parse only lines matching the shipped
  verdict grammar, and record one package per FAIL and per WAIVED. A PASS is
  never packaged. A line outside the grammar is COUNTED and never copied, so an
  unrecognized line cannot smuggle its text into a shared artifact.
  The no-effect-on-exit-code property is structural rather than promised:
  `_record_decisions` returns nothing, so no caller has a value to fold in; every
  caller returns the delegated tool's own code, computed before the call; and
  every exception class is caught there, printed with its class named, and
  stopped. A fixture proves it by making the write fail while the gate FAILs, and
  the exit code stays 1. `--no-decisions` suppresses the write and SAYS it did,
  because a silent suppression is indistinguishable from a tool that never ran.
  Loop 2, task 3 of 8. Held by `TestGateTriggers`, calibrated by six breaks with
  none uncaught

- A decision package now carries the code that decided, not just the verdict it
  reached. `deciding_code` returns the check's own function, excerpted at the
  source span it names, resolved through the shipped check registries rather
  than from memory; `logic_flowchart` draws the check's parts from what the
  registry DECLARES it reads, and every verdict the registry gives no example
  for becomes a NO-DATA node rather than a confident arrow. An unknown check
  gets NO-DATA and never an invented span, and a name that two registries
  declare (`migration`, from both `sbe_gate.py` and `sbe_plan.py`) is reported
  as ambiguous with every declaration named, rather than resolved quietly to
  whichever was found first. Neither helper starts a subprocess. Loop 2, task 2
  of 8. Held by `TestDecidingCode`, calibrated by nine deliberate breaks each
  traced to the single test that caught it

- One `.sbe-exempt` format, two scanners, and each used to refuse a file addressed only
  to the other, so this repository could not pass its own whole-root gate scan with both
  shipped exemption files well-formed: `sbe_gate.py --strict .` FAILed the
  templates/dossier exemption (a `checks:` file with no `gates:` line) as "records a
  reason but names no gates", and `sbe_design.py --strict .` FAILed the new teaching
  waiver the same way in mirror. The rule now, in both parsers: an exemption naming ONLY
  the other registry's field is addressed to that scanner, which honors it and PRINTS it
  as a WAIVED line, and this scanner skips it, so every exemption file stays visible in
  exactly one shipped report; a file naming NEITHER field is still refused by both,
  because that shape is an off switch, not an exemption. Alongside this,
  docs/for-engineers/examples/infra-topology gains a `gates: approval` waiver stating
  that its APPROVAL is DESIGNED to fail as pedagogy (the CI note in
  docs/guides/01-quickstart.md records the scoping decision this mirrors), so a
  whole-checkout scan now reads the teaching refusal as WAIVED with the reason printed,
  never as this repository failing its own controls and never as a PASS; the example's
  numbers, migration and ran fixtures stay unwaived and judged. The publish checklist's
  self-consistency line (`sbe_gate.py --strict .` exits 0) is true for the first time
  since the estates wave tightened the exempt gate. Proof: `TestExemptionAddressing` in
  `tools/test_sbe.py`, four fixtures, calibrated red against the parsers with the
  addressed-elsewhere branches removed (a design refusal where exit 0 was asserted, a
  gate refusal where an approval FAIL was asserted, exit 1 at the repo root) before the
  fix was restored, the restore verified against the pre-recorded `git hash-object` of
  both tools.

- `sbe score` reports on the directory you asked about, not the one you happen
  to be standing in. The split that opens the report groups checks by whether
  they opened a file inside the directory being reported on, and that directory
  was read from the WORKING directory. Running the tool from its own checkout
  against another tree therefore inverted the entire report: `citation-inventory`,
  reading THIS repository's own docs, was filed under "these verdicts are about
  the code here", while `silent-failure-lints`, which had just read the caller's
  tree, was filed under "a verdict here is not a statement about the code in this
  directory". The one line the reader came for sat beneath the heading that
  disowned it, which is the exact failure the split was added to prevent. The
  anchor is now SBE_LINT_ROOT, then the positional directory, then the working
  directory, matching `_resolved_sources`. Found while scanning three outside
  repositories. Held by `TestReportIsAboutTheScannedTree`, calibrated by
  restoring the working-directory anchor and watching both of its tests go red

- Help means help on EVERY `sbe` subcommand, closing external-proof open item 8: the
  whole-surface sweep of the defect class fixed on the three telemetry data commands in
  the entry further down ("make help mean help on the data commands"). Two mechanisms
  produced the same wrong answer, exit 2 for an explicit `-h`/`--help`, on all 23
  subcommands: the top-level parser built every child with add_help=False while
  argparse's REMAINDER drops a LEADING flag, so `sbe intake -h` was refused by a parser
  with no help to give and never reached the tool that had one; and the package modules
  behind `evidence`, `task`, `work` and `pr` caught argparse's SystemExit(0) for help
  and folded it into exit_usage, so `sbe evidence run -h` printed the RIGHT usage and
  still exited 2. Run standalone, three tools were worse than a wrong exit code:
  `sbe_design.py -h` and `sbe_score.py -h` stripped flags wholesale and ran a REAL scan
  (the `data-export --help` shape again), `sbe_fence_hook.py -h` fell into hook mode and
  sat reading stdin, and `sbe_decide.py -h` was read as a table named '-h'. Now the
  passthrough commands (design, gate, score, intake, decide, fences, plan, evidence,
  task, work, pr) are dispatched by hand in `src/brothersbe/cli.py` before argparse sees
  their argv, every other child parser answers `-h` itself, each owning surface prints
  its own usage and exits 0 before touching anything, and a flag a surface does not know
  is refused with usage and exit 2, never silently dropped (`sbe_intake.py`'s refusal
  was exit 1, now 2, matching the CLI's documented table). The bare hook invocation of
  `sbe_fence_hook.py` is untouched and still fails open, and its usage prints on stderr
  because stdout is that tool's decision channel. Proof: `TestHelpMeansHelpOnEveryCommand`
  in `tools/test_sbe.py` (every command in cli.COMMANDS, both help spellings, plus the
  scanning tools examining nothing on -h and the whole-surface bad-flag refusal) and a
  `TestHelpMeansHelp` class in each owning suite: `test_sbe_evidence.py`,
  `test_sbe_tasks.py`, `test_sbe_work.py`, `test_sbe_prverify.py`, `test_sbe_plan.py`,
  `test_sbe_fence_hook.py`, 17 fixtures in all. Calibrated red in three rounds by
  reinjecting add_help=False plus the argparse-first dispatch, the SystemExit fold in
  each module, and each tool's missing help branch: every help fixture failed (a
  returncode of 2, or a real scan where usage was asserted) before the fix was restored,
  each restore verified byte-identical against the pre-recorded `git hash-object` of the
  fixed file rather than by `git checkout`.

- `sbe adopt` no longer proposes ghost paths. The proposal used to carry
  protectedPaths and CODEOWNERS entries hardcoded to this repository's own
  layout (the plugin manifest, `hooks/`, `src/brothersbe/`, the release
  files), none of which exist in a foreign clone, so a consumer applied
  protection rules over paths that protect nothing while looking like they
  do; the first external-proof run named this as its one deliberately
  deferred repair. Now each layout path is proposed only if it exists under
  the target root, a category that loses paths has every missing one named
  under the policy's `_notProposed` block (and in a CODEOWNERS comment, and
  as NOT-PROPOSED lines in both output modes) instead of vanishing, and the
  two paths the kit itself creates (`.brothersbe/` by `sbe adopt --apply`,
  `design/` by `sbe init --apply`) stay proposed unconditionally, because
  existence-checking a path your own first apply creates makes the second
  apply disagree with the first. Proof: `tools/test_sbe_adopt.py`
  `TestGhostPathsNeverProposed` (eight fixtures) plus
  `TestAdoptOnThisRepository` (nothing real is dropped where every path
  exists), each counted green only after being shown red against the
  defect it names: eight against the restored fixed-proposal behavior, and
  the second-apply fixture against a filter that existence-checks the
  self-created paths too.

- External proof round one: three public estates (a FastAPI application, a dbt
  project, an infrastructure deployment) ran the whole assurance path with
  attack rounds, and four defects they surfaced are fixed with calibrated
  tests in the same train: receipt matching is shlex-canonical in converge
  AND work, so a quoted verification command finally binds its own receipt;
  detector kinds honor content patterns, so a SELECT-only model is no longer
  ordered to produce a data model; a markdown-escaped pipe survives the
  07-verification table; and the migration triplet fires only on
  migration-shaped paths. docs/EXTERNAL-PROOF-2026-07-31.md carries the whole
  account: what the tools caught on foreign trees, what broke, what stays
  open by name, and what this round does not prove.

- The update notifier's state file is namespaced to this tool. PARITY.md names
  the notifier as a mechanism this skill shares with BrotherModeUp, and both kept
  "which commit did the operator last see" under the SAME basename in
  `<vault>/99-System/telemetry`. The vault path is the operator's own choice and
  nothing reserves it, so pointing both tools at one vault is a supported setup:
  under the shared name each overwrote the other's stamp every session, and both
  then reported a version change on every following start, forever, reading the
  sibling's commit hash as their own drift. The mechanism meant to catch a real
  change became a permanent false alarm. Observed on a real machine 2026-07-31,
  the day both vaults were pointed at one directory. Held by `TestVersionMark`,
  whose sibling comparison reads BrotherModeUp's real source when it is installed
  and reports NO-DATA rather than passing when it is not, and calibrated by
  restoring the shared name and watching both of its tests go red

- The silent-failure lint no longer reads English as Swift. Every pattern now
  carries an explicit language scope, and `try!` is scoped to `.swift`, where it
  is syntax; unscoped, it matched the ordinary word in prose, so a pure-Python
  file whose docstring reads "Give it a try!" was reported as a discarded error
  at GATE severity, which under `--strict` blocks a merge. Found by running this
  lint against a real outside tree (pallets/click, whose
  examples/colors/colors.py carries exactly that sentence), which is also the
  first time this project's headline check has been exercised on code it did not
  write. Held by
  `TestLintSelfSkipThroughSymlink::test_a_language_scoped_pattern_never_fires_on_another_language`,
  calibrated in both directions by reinjecting the unscoped pattern and watching
  exactly that test go red, then restoring it: the prose file must come back
  clean AND a real Swift force-try must still FAIL, so deleting the rule cannot
  pass the test

- The five first-rank commands were audited against their own specs and the
  nine confirmed defects fixed, each with the test that now holds the fix.
  `sbe pr verify` validates `--repo` against an anchored `owner/name` shape
  before token discovery and before any fetch, so a hostile value never
  reaches URL composition (`REPO_SHAPE_RE`, `valid_repo_shape`); it reads
  REQUIRED CHECKS and CODEOWNERS from the one authoritative source, the base
  branch's protection endpoint, instead of inferring CODEOWNERS from the
  presence of a file and REQUIRED CHECKS from an unfiltered check-run scan,
  and the scan survives only as prose labeled ADVISORY inside the detail line;
  an unreadable reviews endpoint is now carried as an explicit unavailability
  so "no satisfying approval" and "could not check" stop collapsing into one
  verdict. `sbe converge` splits SCOPE's leftovers in two: a changed file that
  no impact detector recognizes and whose extension is outside the tracked
  source-text set is reported as `unmeasured`, a category distinct from
  `unplanned`, and it is named in the PASS detail rather than absorbed into
  it. `sbe status --team` refuses a `designRoots` entry that resolves outside
  the repository root, by its literal spelling and as a visible severity-3
  FAIL rather than a silent skip; it computes each open task's postcondition
  against its declared ownership through the same `tasks.postcondition` that
  `sbe task close` refuses against, so a merge blocker this run can see for
  itself is reported at severity 2 with `basis: observed`; and it fills the
  two empty severity slots, ready-to-start tasks (8) and a fully closed plan
  (9), both `derived` and both suppressed when the registry was unreadable, so
  neither is ever guessed from data the run could not read. Held by
  `tools/test_sbe_prverify.py`, `tools/test_sbe_converge.py`,
  `tools/test_sbe_status_team.py`, `tools/test_sbe_work.py` and
  `tools/test_sbe_plan.py`, all passing, with the eval bed at 517 passed, 0
  regressions

- `sbe status --team` reads every active change under `design/` (plus any
  `designRoots` a team profile adds) into one blocker-first report over ten
  severities, broken claims first, next actions last, with zero network by
  construction: approval facts come only from a saved `10-approval.json`, and
  staleness against the current head is computed and labeled `derived`, never
  presented as observed
  (`TestEvidenceAndConvergence::test_a_stale_approval_report_is_derived_not_observed`,
  calibrated by disabling exactly that control and watching exactly that test
  go red, restored hash-verified). Every finding carries the honesty field
  `basis` (observed, derived, unavailable), and an unreadable task registry
  keeps its severity slot visible as `unavailable` with a nonzero exit
  instead of vanishing
  (`TestJsonContractAndExit::test_an_unreadable_registry_is_an_unavailable_finding_and_a_nonzero_exit`).
  Scope conflicts are computed pairwise over ALL open registry records rather
  than per change, because plan task ids are per-change (every derived plan
  starts at T01) while the registry is one global fence table; the fixture
  that forced this design names two agents holding the same path from two
  changes
  (`TestConflictsAndForced::test_overlapping_open_tasks_across_changes_is_a_scope_conflict_naming_both`).
  A plan with no convergence report is NO-DATA at the convergence severity
  and blocks, because unexamined is not PASS; a change with no plan is a
  starting state whose next action names `sbe plan`, not an error. The human
  view is deterministic, no timestamps. Proof: `tools/test_sbe_status_team.py`,
  11 tests, `OK`.

- `sbe converge` (`src/brothersbe/converge.py`) answers whether the code between
  two pinned commits still matches the approved dossier, in five dimensions,
  every hard verdict grounded in a citable fact and never in a judgment: an
  unplanned changed file is REVIEW-REQUIRED by name
  (`TestScope::test_an_unplanned_changed_file_is_review_required_by_name`); a
  removed OpenAPI operation no dossier artifact or plan task mentions is a
  direct contradiction and FAILs naming the operation, while an undocumented
  added one is REVIEW-REQUIRED
  (`TestContracts`); a changed migration that drops a column the data model
  still documents FAILs naming the attribute and both files
  (`TestData::test_dropping_a_documented_attribute_is_fail_naming_it`); a plan
  verification command with no receipt bound to the assessed head FAILs
  naming the command, and a receipt bound to another commit FAILs naming both
  shas (`TestVerification`, the head-binding control calibrated by disabling
  it and watching exactly that test go red, restored hash-verified). There is
  no force flag and argparse refuses one
  (`TestUsage::test_there_is_no_force_flag`); the only path from divergence
  to PASS is the amendment round trip the suite walks end to end: diverge,
  FAIL, amend the dossier, regenerate the plan and the receipt, PASS
  (`TestAmendment`). The report at `09-convergence.json` carries no
  timestamps, so two runs are byte-identical, and a FINAL PASS lists every
  NO-DATA dimension by name as not examined. Proof: `tools/test_sbe_converge.py`,
  12 tests, `OK`.

- `sbe pr verify` (`src/brothersbe/prverify.py`) binds a PASS/FAIL verdict to
  a pull request's live head commit on GitHub: PR existence, approval bound
  to the current head sha, no self-approval, no dismissed or bot-only
  approval, no changes-requested left standing, CODEOWNERS coverage, and
  required checks on the head sha. Every control that cannot be checked
  reports UNVERIFIABLE, a taxonomy that exists only at this report level
  (a 401 or 403 with a token present, a race between fetch and force-push
  naming both shas) and never a stand-in for PASS
  (`test_403_with_a_token_present_is_unverifiable_never_pass`,
  `test_a_force_pushed_head_between_first_and_last_fetch_is_unverifiable`).
  Missing GitHub credentials on this machine are NO-DATA, never PASS: with no
  GITHUB_TOKEN, no GH_TOKEN, and no `gh auth token`, every network-dependent
  control reports NO-DATA with a one-line remedy and the process exits
  nonzero (`test_no_token_no_gh_is_no_data_everywhere_with_remedy_and_nonzero_exit`).
  The token, when one is found, is held in memory only: it is never printed,
  never written to a report or receipt, and the canary fixtures plant a
  distinctive token value and grep every line of output to prove it never
  surfaces, in a full canned run and in a no-token CLI run
  (`test_the_canary_token_never_appears_in_a_full_canned_run`,
  `test_the_canary_token_never_appears_in_a_no_token_cli_run`). The GitHub
  client is read-only by construction: a source level fixture inspects every
  constructed request and fails if any method but GET appears anywhere
  (`test_every_request_construction_is_get_no_mutating_method_anywhere`).
  Proof: `tools/test_sbe_prverify.py`.

- `sbe work` (`src/brothersbe/work.py`) gives a plan task an isolated
  lifecycle: `start` validates the plan with the landed `sbe plan` checks,
  refuses an incomplete or force closed dependency by naming it, refuses
  every branch, worktree, or open registry collision by name, then opens a
  dedicated git branch and worktree and a registry record through the
  existing `sbe task` machinery. `check` reports scope, dependency, and
  verification state without mutating anything. `finish` closes a task only
  when the registry postcondition is clean AND a verification receipt bound
  to the worktree's current commit exists in the evidence store; an agent
  saying it ran the command is not evidence, so an absent receipt refuses
  closure as NO-DATA prose naming the command
  (`TestFinishRefusals::test_finish_refuses_as_no_data_when_the_verification_receipt_is_absent`).
  One writer owns one branch and one worktree, never shared. A forced close
  (`finish --force`) is visible and loud in `check` and in the record, and it
  never satisfies a dependent task
  (`TestForceFinish::test_finish_force_closes_marks_forced_visible_in_check_and_never_satisfies_a_dependent`).
  There is no merge, no rebase onto the default branch, no push, and no
  deploy code path anywhere in this module, held by a source level fixture
  that greps the file for those verbs
  (`TestNoMergeLaw::test_work_module_never_constructs_a_merge_rebase_or_push_argv`).
  `remove` deletes a CLOSED task's worktree and leaves the branch in place, because branch deletion is not one of this module's allowed git mutations, and a dirty worktree
  refuses removal until a human gives `--override-dirty` with a nonempty
  reason, recorded permanently on the registry record
  (`TestRemove::test_remove_with_override_dirty_succeeds_and_records_the_reason`).
  Proof: `tools/test_sbe_work.py`.

- `sbe plan` (`tools/sbe_plan.py`) derives a task plan mechanically from a dossier: no LLM
  anywhere in derivation, only parsing and the rules the spec names. An empty
  dossier never yields a success verdict (`TestEmptyDossier`), a task citing a
  dossier source that does not resolve is FAIL by task id because that is the
  planner-inventing-work case (`TestPlannerNeverInvents`), and a migration
  task written without its stated reversal task FAILs
  (`TestMigrationWithoutRow`). Ownership, citations, acceptance criteria, the
  dependency graph, and freshness against recorded dossier digests are each
  checked and each FAILs by naming the offending id or file
  (`TestValidationFailures`, `TestCompatibilityGap`). A derived plan's first
  task also opens through `bin/sbe task open` with fields read mechanically
  from the JSON, proving the registry accepts it without reinterpretation
  (`TestRegistryIntegration`). Proof: `tools/test_sbe_plan.py`, 14 tests, `OK`.

- The book's replay harness (`evals/replay_book.py`) now declares exactly one
  substring volatile: the live merge-base diff line the status and impact
  tools print (`git diff <sha>..HEAD over N changed file(s)`), whose sha and
  count move with every commit and push, which is how the published pages
  went stale within hours of `5be26b2` landing. Chapter 03 says so in prose
  beside the block; chapter 05 stops using a live range at all and pins
  `--base 47422a88df57 --head f924538`, which is deterministic on any clone.
  Proof: `tools/test_sbe_book.py::TestDeclaredVolatileLine`, calibrated both
  ways (a volatile-only difference passes, any other difference still fails,
  and a pinned range is never masked).
- The private-name scan (`tools/test_sbe.py::TestNoPrivateNameShips`) counts
  a hit inside vendored minified code (`docs/book/assets/mermaid.min.js`,
  the only file on that list) only when the name stands alone rather than
  flanked by letters or digits: a short name is a near-certain substring of
  SOME generated identifier in two megabytes of minified JavaScript, and the
  first false positive (the name inside mermaid's own motion-blur
  identifier) turned the whole baseline red. Every file this project authors
  keeps the plain substring rule. Proof: three new calibration fixtures with
  a synthetic name, including one pinning the vendored list to exactly one
  file so widening it is a decision rather than a drive-by.

- `00-intake.json` may now carry an OPTIONAL `binding` block (row 23 of
  `docs/BYPASS-COVERAGE.md`, a stale dossier reused for a new change): a head
  commit plus a sha256 per artifact the dossier covers. Absent, nothing
  changes, and the absence is what keeps the row UNCOVERED rather than
  COVERED. Present, `tools/sbe_design.py::_binding_problem` verifies it before
  letting `check_artifacts` reach its own PASS: a HEAD that moved since
  binding FAILs naming both commits and says "re-bind deliberately"; an
  artifact whose digest moved FAILs naming the file; a binding naming a
  commit this tool cannot resolve is NO-DATA, never a pass. Resolution reads
  git's own on-disk files directly (`HEAD`, a ref, a loose object's path)
  rather than shelling out to git, so
  `tools/test_sbe_bypass.py::test_the_design_checks_never_read_a_commit_which_is_a_limit`
  is unaffected: it pins the absence of a `subprocess` import and of a
  `git log`/`rev-parse` call, both still true. Proof: `tools/test_sbe.py`'s
  new `TestDossierBindingScenario23`, five fixtures (bound-and-current
  passes; HEAD-moved fails by name; artifact-digest-drift fails naming the
  file; absent binding is unchanged behavior; an unresolvable bound commit is
  NO-DATA), each calibrated red against a one-line break and restored to the
  pre-recorded `git hash-object` of the fixed file before being counted
  green. `docs/KNOWN-LIMITS.md` states the one gap this resolution carries: a
  bound commit old enough to have been folded into a pack by housekeeping
  reads NO-DATA rather than a confirmed verdict, because confirming existence
  is checked only against loose objects.

- `tools/sbe_gate.py` now honors `.sbe-exempt`, which it had zero support for until now
  (the CI workflow comment promised it; a grep of the file found nothing). Mirrors
  `tools/sbe_design.py::parse_exemption`'s semantics: a `gates: <names>` field naming
  which of the four hard gates a directory waives, a required `reason:` field, `gates: *`
  refused BY NAME because a wildcard is not the name of a gate, and a blank or
  whitespace-only reason refused as its own FAIL naming the file rather than a quiet
  waiver. An artifact found IN OR UNDER an exempt directory reports WAIVED, quoting the
  reason, never PASS and never silently skipped; the summary counts waived artifacts per
  gate. Exit stays 0 under `--strict`
  alone (a waiver is a visible decision, not a violation); the new `--strict-waivers`
  flag, matching `sbe_design.py`'s own flag of the same name and wording, makes any
  WAIVED artifact block a `--strict` run. Proof: `evals/run_evals.py`'s new
  `an-exempted-approval-reads-waived-with-the-reason-and-strict-exits-clear`,
  `strict-waivers-blocks-an-exempted-approval-that-strict-alone-does-not`,
  `a-blank-sbe-exempt-reason-fails-by-name-and-the-artifact-is-still-checked`, and
  `a-pass-is-impossible-for-an-exempted-artifact`, each calibrated red against a
  one-line break in the new code and restored to the pre-recorded `git hash-object`
  of the fixed file before being counted green.

- The resume brief is now opt-in, matching the `metrics` and `corrections` default wave 6 already
  set. It was the one capture path still writing a file by default: `BROTHERSBE_TELEMETRY_TRANSCRIPT`
  off (the default) wrote the brief anyway, with a `[REDACTED]` placeholder in place of every
  transcript-derived section and a line naming the switch that would fill them in. Flip decision
  (founder, 2026-07-29): off now means no file at all, and the `precompact-brief` code path that
  would have written it names the switch once on stderr instead, the same "who kept this off and
  why" sentence the other two categories already print, so an absent file is never mistaken for a
  quiet session. The opt-in path (`BROTHERSBE_TELEMETRY_TRANSCRIPT=1`) is unchanged: it still reads
  the transcript tail and still redacts before writing. `SECURITY.md` and `docs/KNOWN-LIMITS.md` are
  updated to the new default and its own limit: the stderr line only reaches whoever is watching the
  hook at the moment of compaction, and a resumed session's `compact-hint` reader has nothing on disk
  to relay, unlike the old placeholder file. Proof: `tools/test_sbe.py`'s `TestResumeBrief`, rewritten
  from the test that asserted a file existed by default (its docstring states the old meaning and this
  decision) into `test_default_writes_no_brief_and_names_the_switch_on_stderr`, plus the new
  `test_opt_in_writes_the_brief_and_still_redacts` fixture for the opt-in path; three fixtures in
  `TestCaptureDefaultsAndAutosaveContentScan` (`test_a_default_installation_captures_no_transcript_text_and_no_correction`,
  `test_each_switch_turns_on_exactly_one_category`, `test_the_organization_override_forces_every_category_off`)
  updated to the same default. Calibrated red against the pre-flip code (4 fixtures failed, each on a
  now-missing-file assertion) before the fix restored it, the restore verified byte-identical to the
  pre-recorded `git hash-object` of the fixed file rather than by `git checkout`.

- `sbe evidence run` no longer writes `argv` fully verbatim: every token is now checked against
  `SECRET_PATTERNS`, imported from `tools/sbe_telemetry.py` rather than reinvented, and a match
  is replaced by a named marker, `[REDACTED:<shape>]`, before the receipt is written. The
  command that RUNS still receives the untouched, unredacted argv; only the recorded copy is
  masked. The receipt gains `argvRedactions`, the count, so a reader can tell whether argv is
  verbatim (`0`) or not without diffing it by hand, and `argvRedactions` sits in `SEALED_FIELDS`
  beside `argv` so a redacted receipt seals and verifies exactly like any other. This narrows
  the argv limit; it does not close it, because the pattern list is finite by nature and a
  secret in a shape it does not know still reaches the receipt whole, which stays a stated limit
  in `docs/KNOWN-LIMITS.md`. Proof: `tools/test_sbe_evidence.py`'s
  `test_a_secret_shaped_argv_token_is_redacted_not_recorded_verbatim` (a planted `sk-`-shaped
  token lands in the receipt as the marker, never the secret; this replaces the retired
  `test_argv_is_recorded_verbatim_which_is_a_limit_not_a_leak_to_ignore`, which pinned the
  opposite on purpose as a stated limit),
  `test_a_receipt_with_redactions_still_verifies_pass_on_an_untouched_tree` (a redacted receipt
  still verifies PASS), `test_zero_redactions_keeps_argv_byte_identical_to_what_ran`, and
  `TestRedactArgv` for the function directly.

- `sbe init` now also ensures `.gitignore` carries its own install-receipt line,
  `.brothersbe/install-receipt.json`, under a one-line comment, because a fresh clone that ran
  `sbe init --apply` could track a receipt naming this machine's absolute install path with
  nothing in the way. Appended, not owned: existing `.gitignore` content is left untouched, the
  mutation compares identical (present means untouched) exactly like every other proposal,
  dry-run shows it as a proposed diff like every other mutation, and the install receipt's
  `writtenPaths` and uninstall instructions never include `.gitignore`, because `sbe init` does
  not delete a file it only appended a line to. Proof: `tools/test_sbe_adopt.py`'s
  `TestInitGitignoreLine`, calibrated red (three fixtures failed) against the mutation removed
  from `plan()`, before the fix restored it.

- `sbe doctor` gains an `identity` check: it reads this repository's `git config user.email` and
  `user.name` and reports a `WARNING`, quoting the value found, for a fixture identity, an
  `@example.com` email or the literal name `ci`. That shape of identity authored a run of real
  public commits before anyone noticed it; the check exists to catch the same class earlier, and
  it never blocks a run by itself: `WARNING` moves neither the exit code nor the `FAIL` count,
  matching `NO-DATA` and `PASS`, the same never-a-hard-failure rule `doctor` already applies
  everywhere else. Proof: `tools/test_sbe.py`'s `TestDoctorIdentityCheck`, calibrated red (both
  leak fixtures failed) against the `WARNING` branch disabled, before the fix restored it.

- `tools/sbe_score.py`'s silent-failure lint named a self-skipped file by
  name but never counted it: a directory where the walk reached its own
  source under thirteen of its fourteen names (a hardlink or a case/symlink
  alias reaches the same inode more than once) printed "1 file(s) scanned
  under X, clean" with the thirteen listed and no number attached, because
  the "clean in what was opened, which is not the same as a clean tree"
  withdrawal only checked the KIND-skip count, never the self-skip one. Both
  are counted now, and either withdraws the bare "clean". Proof:
  `tools/test_sbe.py`'s
  `test_a_directory_mostly_self_skipped_names_the_count_and_withdraws_clean`,
  planted with thirteen hardlinks of the scorer's own file, calibrated red
  against the prior sentence before the fix restored it.

- `tools/sbe_autosave.sh` already exits 0 on an unwritable vault (an earlier
  fix closed that), but the REASON did not: `log_line` and `excl_record`
  tried to write their explanation into the same vault directory that had
  just failed to write, so a skipped precompact or tick left no trace
  anywhere, not in `autosave.log`, not in `autosave-exclusions.log`, not on
  stderr (kept clean on purpose). Both now fall back to a file beside the
  repository's own git metadata (`.git/brothersbe-autosave-fallback.log`),
  which does not depend on the vault at all, when the primary write fails.
  Proof: `tools/test_sbe.py`'s
  `test_an_unwritable_vault_still_lands_the_reason_in_a_fallback_log`, which
  chmods a vault telemetry directory read-only and asserts the reason lands
  in the fallback log instead of nowhere, with a writable-vault control
  asserting no fallback file is written when none is needed.

- docs/CLI.md gains a section documenting the telemetry data commands (`data-show`,
  `data-export`, `data-purge`): where they live (`tools/sbe_telemetry.py`, not `sbe`, because
  the facade fronts assurance commands run routinely on somebody else's schedule and these
  three read or delete what BrotherSBE captured about the operator's own sessions, a privacy
  surface a person runs deliberately, by name, on purpose), what each shows or deletes, the
  vault location (`BROTHERSBE_VAULT`, default `~/BrotherSBEVault`), and real output quoted
  from a run against this repository's own vault. Docs-only; the three commands themselves
  are unchanged.

- The first real run of the CI gates found the hard-gates step grading the
  teaching dossier under docs/for-engineers/examples: its deliberately failing
  APPROVAL broke the build, and its receipts printed PASS lines as if they
  were this repository's claims. The step now scopes to the live dossier root
  (design/, declared by this repository's own `sbe init`), where all four
  gates honestly read NO-DATA today. The consumer workflow's strict flag now
  applies on pull requests only: a push to main has no proposed change, and
  grading its empty self-diff under --strict manufactured a failure out of
  absence. The install receipt is gitignored because it records this
  machine's absolute path.

- PRACTICES.md gains the loop close-out interview: open loops are put to their
  decision owner as per-loop question sets, each question carrying a
  recommendation, its pros, and its cons, triaged gating-first and run through
  the harness's native question surface by default rather than as prose. Advice,
  not a control, and it says so.

- `sbe status`: one truthful, blocker-first answer to "where does this change stand",
  read from state other commands already recorded rather than computed fresh. It never
  runs the suites itself and never becomes a second gate runner: nothing in it starts a
  subprocess, and every design/gate/score FAIL it names comes from an EXISTING evidence
  receipt someone already generated with `sbe evidence run`, never from status invoking a
  check on its own. Six sections, blocker-first: BROKEN CLAIMS (a receipt failing `sbe
  evidence verify`, or a disposition bound to a commit that is not HEAD), MERGE BLOCKERS
  (an intake tier disagreeing with the diff-derived tier with no disposition, an unreadable
  intake, a task closed `--force`d, or a verified receipt recording a nonzero exit code),
  ACTIVE CONFLICTS (overlapping open tasks, read by calling `tasks.load_registry`,
  `tasks.open_tasks` and `tasks.claims_overlap` directly, the same functions `sbe task
  check` runs, so there is no second copy of wave 5's overlap rule), MISSING EVIDENCE (a
  design/gate/score kind no verified receipt names, for a tier above T0, each naming the
  command that would fill it), COMPLETED EVIDENCE (a clean, zero-exit receipt with its
  trust label), and NEXT ACTION (the first nonempty section's remedy, or "nothing blocking
  here that this tool can see", plus the scope sentence naming exactly which stores were
  read). An absent store is NO-DATA with a reason, never clean, and every positive or empty
  line in text mode names the scope it inspected. Exit 0 means sections 1-4 are empty, not
  that everything was inspected, and the closing line says so. Proof:
  `tools/test_sbe_status.py`, 17 fixtures over 10 classes, each calibrated by planting the
  break, watching the section go red, then restoring the clean state and watching it clear:
  a stale receipt, a tier disagreement without and then with a disposition, an injected
  registry overlap and its non-overlapping counterpart, a forced close, missing evidence
  for a T2 tier against a T0 tier's clean bill, a clean receipt and a failing one, all three
  NEXT ACTION arrangements, `--json` carrying every section and the scope object, and a
  guard that greps rendered output (not source) for a scope phrase on every empty-section
  line. Limits stated beside the behavior in `docs/CLI.md`, including the flat,
  single-dossier convention this wave reads (`00-intake.json`, `disposition.json` and
  `.sbe/` at the inspected path itself, not discovered under a nested `design/<change>/`
  dossier) and the argv-substring heuristic used to recognize a design/gate/score receipt.
  Maturity: INTERNAL-EVAL.
- Release-candidate packaging: `.claude-plugin/marketplace.json` names the
  plugin, the repository, and the version, in the shape `claude plugin
  marketplace add` and `claude plugin validate` (installed CLI 2.1.207)
  accept; `tools/test_sbe.py`'s new `TestMarketplaceManifest` class pins its
  version against `VERSION` and `.claude-plugin/plugin.json` (a four-way pin,
  extending the pin `TestPluginSurface` already held) and re-runs the
  installed CLI's own validator as a subprocess, skipping honestly (not
  passing) when `claude` is not on PATH. `scripts/test-install-artifact.sh`
  proves a plain `git archive HEAD` extracts into an empty directory and
  verifies clean there (`scripts/verify-install.sh`, `bin/sbe doctor`),
  nothing written outside that directory, the kill criterion this wave was
  cut against. `scripts/test-upgrade-rollback.sh` proves the same for a
  previous-tag-to-HEAD-to-rollback cycle when a previous tag exists, and
  reports NO-DATA honestly (exit 0, no claim of a tested upgrade) today,
  because this repository has cut no tag yet; both scripts were calibrated
  by breaking each fixture in a disposable clone of this repository and
  watching it go red, then restoring it and watching it go green, on both
  branches of the upgrade-rollback script. Both new steps are wired into
  `.github/workflows/brothersbe-gates.yml`. `docs/ROLLOUT.md` is new: a
  staged rollout for an adopting organization (shadow mode, then a
  founder-gated move to enforced, then the adoption kit), a support and
  ownership model with no invented SLA, the upgrade and rollback procedure,
  and the blocked list verbatim (signed release, branch protection, `gh
  auth`, real-estate maturity claims). `docs/KNOWN-LIMITS.md` gets a matching
  section naming the same four blocks in this project's own voice. No
  control was weakened; the pre-existing suite counts only rose (`sbe`: 47 to
  49). Maturity: INTERNAL-EVAL, proven against this repository and a
  disposable clone of it, and no other estate, exactly as `docs/ROLLOUT.md`
  states plainly rather than implies.
- `sbe task`: a write-scope registry with a diff postcondition that survives
  Bash. The fence hook fails open and cannot govern shell writes because shell
  cannot be parsed reliably; `sbe task open` now records who owns what in
  `.sbe/tasks.json` (one file, atomic rewrite, no lock, concurrent registry
  writers a stated limit), and `sbe task close` reads the union of
  `git diff --name-only <base>...HEAD` and `git status --porcelain` and
  refuses to close a task whose tree changed outside its declaration, naming
  every violation by path; uncommitted edits count, a rename counts both
  sides, and an unresolvable base is NO-DATA, never a pass. `open` refuses an
  owned path overlapping another open task's, using the fence hook's own
  `paths_overlap` imported rather than re-typed (a fixture fails if that
  import is ever replaced by a local copy); `check` re-runs the scan so a
  collision injected into the JSON by hand is caught; `fence` renders the
  markdown fence view one way, JSON to markdown; `--force` records who and
  why and marks the close FORCED, never clean; and a reviewer task can
  neither open owning the evidence store nor close over a touched receipt,
  even forced. Proof: `tools/test_sbe_tasks.py`, 15 fixtures, every one
  calibrated by breaking the control and watching it go red. Limits beside
  the behavior in `docs/CLI.md`, `docs/KNOWN-LIMITS.md` and
  `docs/HOW-IT-WORKS.md` (the two-layer scope model). Maturity:
  INTERNAL-EVAL.
- `sbe adopt` and `sbe init` are built, closing the refusal `cli.py` used to print for `adopt`
  ("the adoption doctor cannot yet tell a protected repository from an unprotected one, and a
  readiness report that omits that is worse than none"). `sbe adopt` detects a repository's
  stack by walking the tree (languages, a migrations directory, dbt models, API contract files,
  existing CI workflows), reusing the SAME path patterns `sbe impact` already carries
  (`brothersbe.impact.DETECTORS`) rather than a second copy of them, and proposes a provisional
  `.brothersbe/policy.json` (wave 3's own policy file and JSON schema had not shipped when this
  was written; the file's own `note` field says so) plus a `.github/CODEOWNERS` generated from
  that same policy, protecting the manifest, hooks, this repository's own policy and config,
  where the evidence schema is declared, product and consumer CI, and release files. THE KILL
  CRITERION THIS WAVE WAS BUILT AROUND: the adoption report never claims a GitHub-side
  protection (branch protection, required status checks, review from a code owner being
  REQUIRED) is PRESENT, because nothing here holds a GitHub token or asks for one; all three
  report UNVERIFIABLE-HERE unconditionally, naming what checking them for real would take, and
  `tools/test_sbe_adopt.py::TestAdoptionReportNeverClaimsPresent` pins exactly that. A
  CODEOWNERS file merely existing in the tree is reported separately, under `localFacts`, so it
  is never read as proof GitHub actually requires that review. Both proposals are deterministic
  (no timestamp, no run id), which is what lets a second `--apply` recognize nothing changed and
  write nothing; an existing file that differs is never overwritten without `--force`.
  `sbe init` installs BrotherSBE's own local footprint (`.brothersbe/config.json`, a
  `design/.gitkeep` dossier marker, and, only with `--with-consumer-ci`, a copy of this
  installation's own consumer CI workflow and composite action), refuses outside a git
  repository naming the reason, and writes or refreshes an install receipt
  (`.brothersbe/install-receipt.json`) naming every path it has written and the exact `rm -f`
  uninstall line for each, only when something was actually written that run; a no-op run leaves
  the receipt, timestamp included, untouched. `.github/workflows/brothersbe-gates.yml` gained
  the missing `push` (to `main`) trigger beside `pull_request`, and a new
  `.github/workflows/consumer-check.yml` plus `.github/actions/sbe-consumer/action.yml` give a
  client repository something to copy or call that runs ONLY `sbe impact`, `sbe evidence
  verify` (when receipts exist), `sbe status` (wave 8; guarded by a file-exists check and
  skipped honestly until that wave lands), and the design checks in strict mode when a dossier
  is declared, and never BrotherSBE's own test files; both new workflow files carry the same
  honest header the product workflow already does, that a workflow file guards nothing on its
  own until branch protection requires it (`docs/KNOWN-LIMITS.md` L16). Eleven fixtures across
  17 test methods in `tools/test_sbe_adopt.py` build real temporary git repositories and run the
  real command: dry-run writes nothing (proved by hashing the whole tree, not by checking the
  paths this module happens to propose today), apply-then-reapply is a no-op, an existing file
  is never overwritten without `--force`, the kill criterion itself, stack detection shifting
  the proposed policy for a planted dbt project and a planted migrations directory, the init
  receipt and its uninstall instructions, `sbe init` refusing outside a git repository, and the
  two shipped workflow files' triggers and scope, read as text and grepped the same
  line-oriented way `evals/run_evals.py` already reads `brothersbe-gates.yml` (this project
  ships no YAML parser). Calibrated by neutralizing each control in turn and confirming the
  matching fixture goes red before trusting the green: the dry-run guard, apply idempotence, the
  force guard, the kill criterion itself, each stack-detection shift, the receipt's uninstall
  match, the git-repository refusal, and both workflow-file assertions, eight breaks, eight red.
  One pre-existing test could not be updated in this change and is a known, expected regression
  rather than a silently accepted one: `tools/test_sbe.py::TestCliSurface::
  test_an_unbuilt_command_refuses_loudly_and_names_its_wave` hardcodes `adopt` in its list of
  commands still expected to refuse and exit 3; building `adopt` this wave makes that one line
  false, and the one-line fix (removing `"adopt"` from that list) touches a file this wave was
  not allowed to edit. Limits in full in `docs/KNOWN-LIMITS.md`; maturity INTERNAL-EVAL.
- The two defects the bypass-coverage table recorded rather than fixed are
  closed, and the table and `docs/KNOWN-LIMITS.md` are updated to match.
  `sbe evidence verify` used to open a receipt path with no access check, so a
  FIFO where a receipt was expected hung the command forever with no verdict
  in either mode; it now runs the same `sbe_checks.evidence_problem` access
  check the hard gates use before opening, and refuses a FIFO, socket, device
  or unreadable file by name in bounded time instead, in both text and
  `--json` mode (`tools/test_sbe_evidence.py::TestAccessAndTimeout`, two
  fixtures). `sbe evidence run` gained an optional `--timeout SECONDS`: past
  it, the child is killed and no receipt is written, so nothing can later
  verify PASS for a run whose exit code was never observed. There is
  deliberately no default, because a silent one would kill a legitimate
  long-running suite, the exact false-positive shape this project's own kill
  criteria warn against, so a command run with no `--timeout` can still hang
  the wrapper as before; that residual is stated on row 35 of
  `docs/BYPASS-COVERAGE.md` rather than left implicit. Separately,
  `tools/sbe_fence_hook.py::paths_overlap` closed the case-insensitive-
  filesystem escape (row 21): a fence written for `docs/SETUP.md` used to let
  a second writer land on `docs/setup.md` because the comparison was
  case-sensitive on a filesystem that is not. A missed comparison is now
  retried case-folded and the fold is confirmed against the filesystem
  (`os.path.samefile` when both spellings exist, a volume-level probe when
  one does not) before it is trusted, so two honestly different files named
  `a.md` and `A.md` on a case-sensitive filesystem still do not conflict.
  `tools/test_sbe_bypass.py::test_a_case_variant_of_a_fenced_path_is_refused`
  moved from a LIMIT fixture to a COVERAGE fixture, and
  `tools/test_sbe_fence_hook.py::TestCaseFoldConfirmation` pins the
  confirmation itself. Bypass-coverage totals move from 16 COVERED / 6
  UNREACHABLE HERE / 13 UNCOVERED to 18 / 6 / 11.
- The 35 bypasses an external review listed are now answered one by one, in
  `docs/BYPASS-COVERAGE.md`, and the answer for each is exactly one of three:
  COVERED with the fixture named, UNREACHABLE HERE with the missing thing named
  (a GitHub token, branch protection, a warehouse, a real second estate), or
  UNCOVERED with what covering it would take. Sixteen are COVERED, twelve of
  them by suites that already existed and four by the new
  `tools/test_sbe_bypass.py`: an invented review id is a pointer and never an
  approval, an approval stops counting at the next commit, an exemption naming a
  wildcard waives nothing, and a monorepo package carrying no receipt is named
  in its neighbour's PASS line. Six are UNREACHABLE HERE and thirteen are
  UNCOVERED, and the table says so rather than quietly dropping them, because
  the honesty of that count is the deliverable and the fixture count is not.
  Fixtures that pin a bypass WORKING carry `_is_a_limit` in their names (an
  alias-only second derivation passes, a rehearsal against an empty database
  passes on zero equals zero, a case variant escapes a fence on a
  case-insensitive filesystem), so each hole is a decision somebody made rather
  than a surprise somebody finds. Every fixture was calibrated by breaking the
  control it targets and watching it go red: 21 breaks, 21 red. Two holes found
  in the writing are recorded in `docs/KNOWN-LIMITS.md` and not fixed here,
  because fixing them changes code this wave was not allowed to touch:
  `sbe evidence verify` hangs forever on a FIFO receipt (no access check before
  the open), and the evidence wrapper runs the operator's command with no
  timeout.
- Two privacy defects an external review found are closed, and both were
  defaults rather than bugs. FIRST: this tool parsed the session transcript and
  stored excerpts of the operator's own messages by default, with best-effort
  redaction standing between a customer name, a partner term or an unreleased
  design and a file on disk. Best effort is the right engineering for a redactor
  and the wrong basis for a default. Capture is now OFF unless switched on, per
  category and independently: `BROTHERSBE_TELEMETRY_METRICS` for the per-session
  row in `outcomes.jsonl`, `BROTHERSBE_TELEMETRY_TRANSCRIPT` for the transcript
  text in the resume brief, `BROTHERSBE_TELEMETRY_CORRECTIONS` for the excerpts
  in `corrections.jsonl`. The invariant, and the fixture that holds it: a
  default installation captures no transcript text and no correction excerpt,
  and nothing is read out of a transcript until a category that needs it is on.
  `metrics` is opt-in too, because its row carries the working directory
  basename and a basename can be a client's name. An organization override
  (`BROTHERSBE_TELEMETRY_DISABLE`, or `capture = off` in
  `/etc/brothersbe/telemetry-policy.conf`) forces all three off and no local
  switch reverses it; a policy file that cannot be read, or that carries a
  directive this version does not recognize, FAILS CLOSED and names the file and
  the line. Three new subcommands make the stored data visible, portable and
  removable from one shared inventory: `data-show`, `data-export` and
  `data-purge`, the last re-checking the filesystem after each removal and
  reporting anything that survived rather than reporting success from its own
  intention. Every field that can be stored is now published field by field in
  `SECURITY.md`. SECOND: the autosave excluded secret-shaped file NAMES, and a
  secret in a normally named source file (`src/config.py` holding an API key)
  matched no pattern and became a permanent git object; the documentation said
  the name patterns meant "credentials never enter the autosave ref", which was
  never true. Every candidate file's CONTENT is now read BEFORE `git add` runs,
  which is the moment a blob would be created, so a rejected file never becomes
  a git object at all. Files past `BROTHERSBE_AUTOSAVE_MAX_BYTES` (1 MiB) and
  binary files are excluded as UNSCANNED rather than assumed clean, as is a path
  git cannot print literally. Every exclusion is recorded in
  `99-System/telemetry/autosave-exclusions.log` with its reason, as a path and a
  reason only, and `recover` points at that record because what a snapshot does
  NOT hold matters at recovery time. In a repository declared production
  (`BROTHERSBE_REPO_CLASS=production` or a `.brothersbe-production` file)
  autosave is opt-in and snapshots nothing until `BROTHERSBE_AUTOSAVE_PRODUCTION`
  is set. Seven fixtures in `tools/test_sbe.py`
  (`TestCaptureDefaultsAndAutosaveContentScan`) run the real tools in temporary
  vaults and real git repositories, and the secret-in-a-source-file fixture
  asserts that no git OBJECT for that content exists anywhere, not merely that
  the tree omits it. Calibrated by breaking each control in turn and confirming
  the matching fixtures fail: capture default (2 fixtures), organization
  override (1), content scan (2), exclusion record (1), production opt-in (1),
  purge removal (1). `docs/THREAT_MODEL.md` is new and covers fifteen threats,
  including the ones nothing here stops: a direct push, a deleted workflow, a
  compromised CI runner, and prompt injection from repository content. What
  these controls do NOT stop is in `docs/KNOWN-LIMITS.md`, including the two
  sentences that matter most: a path exclusion never prevented secret capture,
  and a local git ref can still be carried off the machine by a backup or a
  mirror.
- `sbe evidence` closes the hole under every gate in this project: a receipt
  could be typed by hand by the same agent whose work it verified, so a
  fabricated duration, exit code, row count or rerun id satisfied the schema and
  a gate could PASS on a run nobody's command ever performed, and nothing bound
  a receipt to a commit either, so one written against older code still passed
  after that code changed. The invariant now: a receipt only counts as evidence
  for the commit it was generated against, by a wrapper that ran the command
  itself. `sbe evidence run --out r.json -- <command...>` EXECUTES the command
  through subprocess and records what it observed (repository identity, base and
  head commit, the exact argv, start and end in ISO 8601 UTC, duration, exit
  code, python and sbe versions, platform, tree dirtiness, and the covered files
  with their content digests); there is no flag that accepts a duration or an
  exit code, and the wrapper's own exit code is the command's, so a failing
  command cannot be laundered into a passing evidence step. `sbe evidence
  verify` FAILs on an unknown schema version, a vacuous required field (through
  the same `answered()` every other receipt field goes through), a broken
  `runId` seal, a head commit that has moved, or a covered file that changed,
  vanished or was written after the run ended; it returns NO-DATA rather than
  PASS for a receipt generated on a dirty tree or covering no file, because
  advisory is not a pass; and every verdict line names what it inspected.
  `sbe evidence show` prints the trust level unconditionally: PROTECTED-CI only
  when `SBE_CI_RUN_ID` was set by the environment AND the tree was clean,
  LOCAL-ADVISORY otherwise, since a CI job over uncommitted edits is a local run
  wearing a badge. stdout and stderr are recorded as SHA256 digests and byte
  counts, never as text, because a receipt is the one artifact everybody is
  encouraged to share and a command that prints a token would otherwise persist
  it there forever. The `runId` seal is stated as tamper evidence rather than a
  signature, in the module, in `docs/CLI.md` and in `docs/KNOWN-LIMITS.md`: it
  catches a receipt nobody's command produced and it does not stop somebody who
  read the source, which is exactly why a local receipt is never more than
  advisory. Twenty-seven fixtures in `tools/test_sbe_evidence.py` build real git
  repositories and run real commands: the defect (three hand-authored and
  doctored receipts), the sound case, a stale commit, a stale file, a deleted
  covered file, a dirty tree, malformed and unknown-schema receipts, vacuous
  required fields, and the assertion that a secret printed by the command
  reaches the receipt only as a digest. Calibrated by neutralizing each of the
  four controls in turn and confirming the matching fixtures fail (commit
  binding 1, seal 2, dirty-tree NO-DATA 2, covered-file staleness 2) before
  trusting the green. One limit the fixtures found and now pin: `argv` is
  recorded verbatim, so a credential passed on the command line IS persisted.
  Limits in full in `docs/KNOWN-LIMITS.md`; maturity INTERNAL-EVAL.
- `sbe impact` closes the oldest hole in this project: the tier was computed
  from five answers and nothing ever read the code, so a change rewriting an API
  contract could be classified T0 by answering "no" five times, and every gate
  downstream then agreed the change owed no evidence. The scan derives those
  same five answers from the git diff and runs them through
  `sbe_intake.compute_tier`, the SAME table a person's answers go through: one
  rule, one place, two inputs, so a derived tier and a declared tier cannot drift
  apart. It may raise a declared tier and may never lower one. A disagreement is
  resolved only by a disposition naming the detector, the decision, the reason,
  the author and the head commit it was decided against; a disposition from
  another commit resolves nothing and one with no reason is an off switch rather
  than a decision. The proposed tier is a FLOOR, not a ceiling: `consumers`
  cannot be read from a diff and is assumed at its lowest value, and every
  changed file no detector covers is listed by name under `unmeasured` rather
  than folded into a clean result. Verdicts are PASS, REVIEW-REQUIRED, FAIL and
  NO-DATA, and `--strict` makes NO-DATA block for protected CI. Twenty-two
  detectors ship (OpenAPI, AsyncAPI, protobuf, Avro, GraphQL, event schemas,
  migrations, SQL data definition language, dbt models, ORM models, destructive
  operations, payment paths, partner paths, personal data paths and field names,
  authorization paths, production configuration, secret material,
  infrastructure, CI pipelines, queue configuration). Sixteen fixtures in
  `tools/test_sbe_impact.py` build real git repositories and run the real
  command: the defect, the sound case, hollow and malformed intakes, an
  unsupported language reported as unmeasured, four bypass attempts (deleting
  the intake, a stale disposition, an unreasoned disposition, a deletion
  misread as an addition), and the invariant that a declared tier is never
  lowered. Calibrated by neutralizing the control and confirming five of the
  sixteen fail before trusting the green. Limits stated beside the behavior in
  `docs/KNOWN-LIMITS.md`; maturity INTERNAL-EVAL.
- Two suites that existed and ran on nobody's merge path now run in CI: the
  fence hook tests and the impact fixtures. The workflow's own comment already
  said it: a fixture no merge runs cannot stop anything.

- One command line, `bin/sbe`, over the nine script paths, plus an importable
  `src/brothersbe/` package. It is a facade and says so: every built subcommand
  delegates to the tool in `tools/` that already carries the behavior and the
  tests, and returns that tool's exit code. Nothing in `tools/` changed, and the
  old invocations are NOT deprecated in this change: deprecating commands that
  509 evals and a dozen pasted doc examples point at is its own change with its
  own risk, and it is not being smuggled into a packaging wave. No install step
  either, because zero dependencies is a promise on the front page and
  `pip install` would retract it for anyone in a CI image with no package index.
  Six subcommands the finalization brief calls for (`inspect-change`, `plan`,
  `evidence`, `policy`, `exceptions`, `adopt`) are PRESENT and REFUSE: each names
  what is missing, names the wave that builds it, and exits 3 rather than
  printing an empty result. Exit codes are fixed at 0 no control failed, 1 a
  control failed, 2 usage, 3 not built, and `verify` and `review` close with a
  line saying that exit 0 is not a pass, because a run where every check reported
  NO-DATA also exits 0 and an exit code cannot tell those apart. Documented in
  `docs/CLI.md`. Six new tests in `tools/test_sbe.py` pin the surface: the
  launcher reports the one version in `VERSION`, no command is advertised without
  a runner or implemented without a help line, an unbuilt command exits 3 and
  names its wave, the four exit codes a CI job would branch on hold, `verify`
  cannot exit 0 over an empty directory without saying no control passed, and the
  package imports with nothing installed. Two of them were calibrated by
  injecting the defect (an unbuilt command made to succeed, and a command
  advertised with nothing behind it) and confirming they fail before trusting the
  green.

- BrotherSBE is now a Claude Code plugin, and nothing was moved to make that
  true. `.claude-plugin/plugin.json` declares it, `skills/` holds six thin
  namespaced skills (`kickoff`, `design`, `verify`, `review`, `learn`, `adopt`)
  that route into the existing law rather than restating it, `agents/` holds
  seven read-only reviewer agents, and `hooks/hooks.json` ships the four hooks
  with self-resolving `${CLAUDE_PLUGIN_ROOT}` paths so no engineer hand-edits a
  shared settings file. `SKILL.md`, `references/`, `tools/`, `tables/`,
  `templates/` and every law citation stay exactly where they were: the
  conversion was constrained to add a surface, never to move the law. Proven by
  `claude plugin validate .` (passes) and by five new tests in
  `tools/test_sbe.py` that pin the manifest to the `VERSION` file, require the
  frontmatter each skill and agent loader reads, forbid a write tool in an agent
  documented as read-only, and resolve every `${CLAUDE_PLUGIN_ROOT}` path cited
  by a skill, an agent or a hook. The frontmatter test exists because
  `claude plugin validate` caught a defect this suite's first version accepted:
  an unquoted colon in a description makes the YAML parse fail, and the skill
  then loads with empty metadata in silence. That test was calibrated by
  re-injecting the defect and watching it fail. Rationale, the three rejected
  alternatives and the flip condition: `docs/adr/2026-07-28-plugin-conversion.md`.
  What the conversion does NOT fix is unchanged and still listed in
  `docs/KNOWN-LIMITS.md`: evidence can still be hand-authored, the tier is still
  computed from answers rather than from the diff, approvals are still not
  resolved against a review platform, and the write fence still fails open and
  does not gate Bash.

- An onboarding set for engineers who have never seen this tool ships at
  `docs/for-engineers/`: eight pages (install and first run, one per role for
  backend, data, infrastructure and ETL, the limits page, and the adoption page)
  plus four complete worked dossiers under `docs/for-engineers/examples/`, one
  per role, each carrying the receipts its change would owe. Every block of tool
  output on every page was executed against this tree rather than carried
  forward, and the four dossiers pass all five design checks at their shipped
  path. The eight pages are in `SHIPPED_DOCS`, so the guards that recompute eval
  counts, meta-test counts and pasted lint lines read them too; the ETL page's
  three lint lines are recomputed by
  `no-shipped-doc-prints-a-silent-failure-lint-line-the-scorer-does-not-produce`
  from a fixture rather than exempted from it.

- Every citation that credited `SKILL.md` with a law the lazy-core split moved
  out of it now names the reference file that declares the law. Fifteen
  (file, law) pairs across six documents were dangling: `docs/KNOWN-LIMITS.md`,
  `docs/guides/01-quickstart.md`, `docs/guides/03-work-doctrines.md`,
  `docs/HOW-IT-WORKS.md`, `RUBRIC.md` and `MANIFEST-extraction.md`'s own worked
  example. Nine further pointers that describe `SKILL.md` as the whole law, and
  carry no law number for a check to read, were widened by hand. Proven by
  `every-law-citation-names-a-file-that-holds-that-law`, which globs
  `references/` for the law-text files and requires the file being credited to
  declare the law with its own heading, and which fails on a planted wrong
  pointer rather than on a remembered list of known-bad citations.

The first named version. Before this line the only name for an install was a
commit hash, which `tools/sbe_telemetry.py check-update` compares but no human
can read a promise into.

- Every verdict names the root it examined and the targets it read, and names
  or counts the directories inside that root that contributed nothing. Two
  defects were the same absence: pointed at an EMPTY directory with
  `SBE_DOSSIER_ROOT` set elsewhere, the design tool printed five PASS lines
  byte for byte identical to the run against a complete dossier, and a parent
  holding three change directories, the middle one carrying no receipt at all,
  printed one gate PASS over the pool while that directory alone printed
  NO-DATA. Closed once in `sbe_checks.scope_note`, which both walkers
  (`sbe_gate.find` and `sbe_design.find_dossiers`) call, so a gate added later
  inherits it; the design tool also prints a scope line and prints the dossier
  heading unconditionally, and a configured root that replaces a directory
  named on the command line is disclosed next to the root it replaced. The
  approval refusal names which APPROVAL file it quoted and how many it read.
  No verdict changed. Proven by
  `a-change-directory-with-no-receipt-is-named-in-the-verdict-that-pools-it`
  (executed on the numbers, migration and ran gates, not asserted from their
  source shape), `the-approval-verdict-names-which-approval-file-it-read` and
  `an-empty-directory-cannot-print-the-report-of-a-dossier-somewhere-else` in
  `evals/run_evals.py`.
- The scorer's report is split by what it opened. Checks that opened a file in
  the directory being examined print first, under a heading that says so;
  checks fed by a telemetry vault or fence registries outside that directory
  print under a second heading that says a verdict there is not a statement
  about the code here, and counts how many of those sources are not on the
  machine at all. Measured against a foreign repository, the single line in the
  whole first run that was true about the reader's own code printed eleventh,
  underneath ten NO-DATA lines about a vault path that does not exist for them
  and one PASS about the installed skill's own tree. Severity ordering alone
  did not fix that. No verdict changed, and nothing is aggregated, scored or
  graded. The quickstart's first ten minutes now runs against the reader's own
  repository first, with the real output including the pruning disclosure, and
  the eval bed is step two; the README states what a first run on an unmodified
  repository does and does not tell you; `docs/KNOWN-LIMITS.md` states that the
  intake's contract question sets the tier and that no checker reads a contract.
- The approval identity proof examines something before it certifies. A
  bracketed or parenthesized approver is read as the reader reads it rather
  than parsed to an empty set, a character whose glyph carries no ink
  separates or disappears but never welds two names into one, a comparison
  with no emails and no names on either side certifies nothing, a proven
  email difference is itself the proof, two names of one script compare by
  code point, and the approver who amends and signs is the approver (the
  signature's matched principal is the ground). Proven by the `c15i` approval
  cases in `evals/run_evals.py`; the measured refusal remainder per script is
  disclosed in `docs/KNOWN-LIMITS.md`.
- Ledger rewrites measure the live file before the rename, never after their
  own output: the bytes are read once under the writer lock, anything appended
  since is carried into the replacement verbatim, and a file that shrinks or
  keeps growing is never renamed over. Dedup rewrites through the same
  primitive with a per-run backup name, the lock sidecar can fail without
  dropping the row it exists to protect, short writes complete, and a
  line-delimited record stays one line. Proven by
  TestTelemetryWriterSerialization in `tools/test_sbe.py`.
- The autosave tick treats its counter as untrusted input and its lock as
  leakable: a counter that cannot be written is a named skip with a log line
  (never a silent off), non-numeric and empty counters are named resets, the
  lock is released by a trap on every exit path, and a stale lock is broken
  only when it predates the whole wait, with the presumption named in the log.
  Proven by TestAutosaveCoversTheWorktree in `tools/test_sbe.py`.
- An ADR's rejected count states only what the document establishes: the
  winner is identified per option rather than per document, a Decision
  sentence that names one listed option in ordinary English identifies it
  without quotation marks, a chosen marker that resolves to no listed option
  establishes nothing about the others, and "Flip condition" (this project's
  own name for the section in four shipped pages) is an accepted heading.
  Proven by `an-unquoted-decision-sentence-naming-one-listed-option-is-the-winner`,
  `a-chosen-marker-resolving-to-no-listed-option-establishes-nothing` and
  `the-projects-own-name-for-the-flip-section-is-accepted`.
- The doc-honesty guard classifies a sentence instead of remembering a
  phrasing: the scanned set is every markdown page the manifest ships (42
  pages, where a curated tuple of 18 was read before, so SECURITY.md,
  CHANGELOG.md and the shipped templates were never opened), and a
  claim that the receipt lookup is wider than the directory the caller named
  is recognized by its meaning, with a denial of that same mechanism read as
  the denial it is. A run that derives no page reports that, rather than
  reporting the pages consistent. Proven by
  `a-phrasing-of-the-removed-re-root-nobody-has-written-yet-is-caught`.
- Autosave recovery checks the snapshot out into a NEW detached worktree and
  never writes into the live working tree; the in-place restore path is gone,
  not warned about. Proven by TestAutosaveRecover in `tools/test_sbe.py`.
- The injected digest fits the cap its own SessionStart hook comment names,
  with the long qualifications moved to `LAWS-REFERENCE.md`. Proven by
  TestDigestCap in `tools/test_sbe.py`, which reads the cap out of the hook
  comment rather than hardcoding a second number.
- Every check declares its severity (gate or soft) at write time, prints it on
  every verdict line, and the exit-code mapping is explicit: `--strict` blocks
  on gate FAILs, `--strict-soft` opts graded FAILs into blocking. Proven by
  TestStrictMode in `tools/test_sbe.py` and the severity evals in
  `evals/run_evals.py`.
- `INVARIANTS.md` states the numbered promises with their asserting tests and
  the defect-reinjection record. Proven by the eval cases it names, verified
  present on the date it states.
- Release discipline ships: `VERSION`, this changelog, `CHECKSUMS.sha256` with
  `scripts/checksums.sh` and `scripts/verify-install.sh` (both directions,
  planted extra files fail), and the cut runbook in `docs/RELEASE.md`. Proven
  by the verify-install eval in `evals/run_evals.py`.
- Evidence rendering neutralizes the whole control-character class (categories
  Cc and Cf, plus stray surrogates), not only line breaks, so a receipt field
  cannot forge verdict lines by moving the terminal cursor. Proven by
  `a-receipt-field-cannot-move-the-cursor-in-the-rendered-report` in
  `evals/run_evals.py` and TestOneLineNeutralizesTheControlClass in
  `tools/test_sbe.py`.
- Placeholder detection folds SHAPES (bracketing, a trailing owner, dotted
  initialisms, combining marks and confusables) to a fixpoint, so `[TBD]`,
  `<TODO>`, `TODO(dana)` and `t.b.d.` record no answer, and a container where a
  snapshot id belongs pins nothing. Proven by `a-dressed-up-placeholder-...`,
  `a-bracketed-placeholder-is-not-a-pin` and `a-container-snapshot-id-pins-nothing`.
- The approval gate certifies the NEGATIVE "the approver is not the author"
  only when the difference is proven: proven means no one-for-one look-alike
  substitution this host can read maps one identity onto the other (they
  differ in structure, at a plain-ASCII position, or across a wide or
  right-to-left letterform). A word mixing script families is refused as a
  disguise shape; an identity that is letter-for-letter
  substitution-compatible with the author (a Lisu, Cherokee or Coptic
  spelling of the author's name) is NO-DATA naming the ambiguity, never a
  certificate; a value carrying a reordering bidi control (U+202E and
  family) is refused by code point; and an honest name that merely carries a
  letter no fold reduces (Þóra, Kjær, Bæk, sœur) is certified by its
  readable letters instead of being refused for its unreadable one. Proven by
  `a-confusable-outside-the-curated-table-is-refused-not-passed`,
  `a-multi-script-forgery-is-refused-whatever-scripts-it-uses`,
  `a-partially-mapped-single-script-word-is-refused-not-passed`,
  `a-lisu-spelling-of-the-author-cannot-certify-a-second-person`,
  `a-bidi-override-cannot-render-an-approver-as-the-author`,
  `an-icelandic-name-with-thorn-passes-cleanly`,
  `a-danish-name-with-ae-passes-cleanly`,
  `a-lisu-spelling-of-tbd-is-not-a-snapshot-pin` and
  `a-wholly-single-script-approver-still-passes` (the printed case ids, so the
  citation greps straight out of the suite's own output).
- The gate examines the directory it was named and never a silently
  substituted git top level, so an empty named directory is NO-DATA for that
  directory. Proven by
  `the-gate-examines-the-directory-it-was-named-not-the-git-toplevel`.
- Every diagram and entity grammar starts at any letter (Unicode word
  properties), a diagram line the parser cannot read is confessed and refuses
  the "all traceable" verdict, create/destroy participants keep their alias,
  and `A & B --> C & D` reads every member. Proven by the ten design evals from
  `a-japanese-data-model-is-a-data-model` through
  `a-line-the-parser-cannot-read-refuses-all-traceable` (the printed case ids, so the
  citation greps straight out of the suite's own output).
- The two-alternatives floor counts only rejections that are ESTABLISHED: an
  option whose own text or governing heading carries a rejection verdict, or,
  once the decision is identified among the listed options (a chosen marker
  in any authoring form, a chosen table row, or the Decision's quoted
  choice), the remaining listed options. When no option carries a verdict
  and the Decision paraphrases instead of quoting, the winner may be any of
  them, and the verdict is NO-DATA naming the ambiguity rather than a count
  the check cannot defend; a bullet marking itself chosen is the decision in
  every form, not only in a table. Colon-terminated and bold section leads
  (`Criteria:`, `**Criteria**`, `Entities:`) are read as the headings they
  declare, in the ADR and the data model both. Proven by
  `a-faithful-madr-with-one-rejection-fails-the-floor`,
  `a-madr-with-two-real-rejections-passes-with-an-honest-count`,
  `an-in-bullet-chosen-marker-cannot-inflate-the-rejected-count`,
  `unmarked-options-with-an-unnamed-winner-are-nodata-not-a-count` and
  `a-colon-led-hurried-adr-is-read-as-its-sections`.
- Every report line prints through one flattening choke point (`say()`), so no
  interpolated value of any kind can move the cursor or open a second verdict
  line, and the source lint that enforces it derives its file set from the
  tool walk rather than a filename list: a tool added later is linted on
  arrival, the reviewed exceptions are named with reasons and reconciled on
  every run, and `sbe_decide.py` (whose Recommendation and Alternatives lines
  a table's option name could forge) is inside it. Proven by
  `a-receipt-field-cannot-move-the-cursor-in-the-rendered-report` and the
  report-print lint in `evals/test_no_data_class.py`, whose dead-exemption
  reconciliation is itself a failure path.
- `verify-install.sh` names UNWALKABLE directories and discloses that it
  verifies content, not modes; a shipped doc sentence asserting tool behavior
  is falsified against the source by the doc-behavior guard, whose liveness
  predicates read the MECHANISM (comment-stripped source for the removed
  re-root; the raw marker text for the waiver marker, which is itself
  comment-shaped) and never prose, and one dead claim family is a failure by
  itself. Proven by `no-shipped-doc-widens-the-receipt-lookup-past-what-the-gate-does`.
- Autosave snapshots cover the worktree the ref names (never the hook's cwd
  subtree), the skip-and-save decisions are logged, the tick counter and
  runaway warning serialize on a lock so the printed count is the measured
  one, every superseded snapshot stays reachable through the ref's reflog,
  the per-worktree id is git's own hash of the path (CRC-32 collided across
  ordinary paths), and recover's empty-ref sentence describes the whole
  namespace with legacy-id fallbacks. Proven by TestAutosaveCoversTheWorktree
  in `tools/test_sbe.py`.
- Telemetry writers serialize on an exclusive lock with per-process temp
  paths, and the migrate loss guard recounts the real post-rename file under
  that lock, so a live session's appended row survives a concurrent migrate
  and a maintenance collision cannot report a migration that reached no file.
  Proven by TestTelemetryWriterSerialization in `tools/test_sbe.py`, which
  runs the writers concurrently for real.
- The diagrams FAIL names what it examined (declared entities, components,
  states and systems of record) instead of asserting a whole-dossier absence,
  and a system of record an entity names is a traceable declaration. Proven
  by `a-system-of-record-named-in-the-data-model-traces-a-diagram-node`.
- Guide 01's planted-drift demonstration is replayed from the guide's own
  fenced steps by the suite, and the intake's printed override teaching names
  all three edits while the mismatch FAIL names the completing edit. Proven
  by `guide-01s-drift-demonstration-replays-from-its-own-steps` and the
  override evals in `evals/run_evals.py`.
- An exemption key resolves against the fixture leaf or heading it names, the
  access and legacy axes are non-exemptible by construction, and a waiver that
  excuses no PASS is a meta-test failure. Proven by the `gd_exempt*` guards and
  the dead-waiver guard in `evals/run_evals.py`.
- `verify-install.sh` enumerates every directory entry regardless of type, so a
  symlinked planted module is named rather than invisible, and an eval gates
  `CHECKSUMS.sha256` against the tracked tree so a stale manifest is a red
  suite. Proven by `a-symlinked-planted-module-fails-the-install-check` and
  `the-tracked-manifest-matches-the-tree-it-ships-with`.

- `tools/sbe_telemetry.py`'s `data-show`, `data-export` and `data-purge` had no help path: their
  argv scanning only ever matched the flags each already knew, so `data-export --help` fell through
  unconsumed and ran a real export, and a mistyped flag such as `--catgory` on `data-purge` was
  silently ignored rather than refused, which would have purged every category instead of the one
  named. `-h`/`--help` anywhere in a data command's argv now prints that command's usage (what it
  reads, what it writes, its flags) and exits 0 before anything under the vault is touched; any
  other unrecognized flag is refused with usage and a nonzero exit instead of running past it.
  Proof: `tools/test_sbe.py`'s `test_help_on_each_data_command_prints_usage_and_never_creates_the_vault`,
  `test_help_on_a_populated_vault_reports_and_changes_nothing_in_it` and
  `test_an_unrecognized_flag_refuses_nonzero_instead_of_running_live`, each hashing the vault
  directory's listing before and after rather than trusting the command's own claim. Calibrated red
  against the pre-fix dispatch (all three fixtures failed, one on a real `data-show` run appearing
  where usage was expected, one on a vault the command was only asked to describe getting created,
  one on a returncode of 0 for a rejected flag) before the fix restored it, the restore verified
  byte-identical to the pre-recorded `git hash-object` of the fixed file rather than by `git checkout`.

- `tools/sbe_gate.py::_canonical_email` folded case and a `+tag` for every
  approval-identity comparison but never a gmail dot, so an Approved-by trailer
  of `dana.author@gmail.com` against an author of `danaauthor@gmail.com`, ONE
  real gmail mailbox, fell through the self-approval check unmatched and
  reached the approval gate's strongest sentence: PASS, "proven different." The
  fix folds the local part's dots too, but ONLY for `gmail.com` and
  `googlemail.com`, because dot-insensitivity is a property of those hosts'
  own mail routing, not of email addressing in general; folding it everywhere
  would merge genuinely distinct mailboxes on a host where the dot is
  significant and turn a real second approver into a false self-approval
  refusal. A same-mailbox pair now FAILs by name, and the sentence quotes
  both recorded addresses and says they reach one mailbox under that host's
  own aliasing, not two identities; a genuinely different dotted pair on a
  non-gmail host still reaches PASS, "proven different," unchanged. Proof:
  `evals/run_evals.py`'s `a-gmail-dot-alias-is-not-proven-different` (reads
  the FAIL sentence itself, not just the verdict), the control
  `a-different-dotted-pair-on-a-non-gmail-host-stays-proven-different`, and
  `gmail-plus-tag-and-case-fold-still-collapse-with-the-dot-fold` (the new
  fold stacked with the two it sits beside on the same address), each
  calibrated red against the dot fold commented out and restored to the
  pre-recorded `git hash-object` of the fixed file before being counted
  green. `scripts/derive_refusal_table.py` now also re-runs every unproven
  pair with a gmail dot-alias standing in for the refusal sentence's own
  remedy ("record an email address that differs from the author's"), and
  publishes how many of those the gate still correctly declines, so the
  published table's escape column can no longer be read as "any two
  different-looking addresses close the remainder." `docs/KNOWN-LIMITS.md`
  states the host-dependence and carries that script's fresh output.

- `tools/sbe_checks.py::could_render_same` and `::name_sets_could_collide`
  were safe only because their two callers (the approval check in
  `tools/sbe_gate.py`, reused by `scripts/derive_refusal_table.py`) always
  hand them text already run through `fold()`, which composes via NFKC
  before either function compares a single character. Called on raw text,
  a composed-versus-decomposed spelling of the SAME rendered identity read
  as "proven different": a decomposed Hangul jamo run counts more
  characters than its precomposed syllable and trips the length check that
  earns a certifying PASS its proof, and a precomposed accented letter
  missing from the curated confusable and Latin-name tables (Greek
  omega-with-tonos, outside both) reads as an unreadable letter that
  differs by code point from its own NFD form once the mark-stripping step
  has reduced that form to bare omega, a genuine proof of difference for
  one letter compared against itself. Both functions now run `plain_text`
  (fold()'s own NFKC-composition-and-invisible-strip step, the one
  normalizer this module has, never a second one) over their arguments at
  entry, idempotent for the two callers that already pre-normalize, so
  neither caller's behavior moves. Proof: `tools/test_sbe.py`'s new
  `TestRenderSameNormalizesRawText`, four fixtures (a raw NFC/NFD accent
  pair and a raw Hangul syllable/jamo pair, each through both functions
  directly) plus a control (two genuinely different Hangul syllables, one
  passed as raw jamo, still prove different), each calibrated red against
  the two `plain_text` calls removed and restored to the pre-recorded
  `git hash-object` of the fixed file before being counted green. The
  existing `sig`-class evals exercising both call sites
  (`a-homoglyph-does-not-make-a-second-person`,
  `a-confusable-outside-the-curated-table-is-refused-not-passed`,
  `a-same-script-lookalike-letter-is-refused-not-passed`,
  `a-bidi-override-cannot-render-an-approver-as-the-author`,
  `a-blank-rendering-joiner-does-not-weld-a-second-person`,
  `a-confusable-email-is-the-authors-own-mailbox`, and the gmail-dot-alias
  cases above) were re-run and are unchanged.
