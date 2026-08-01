# 02. Process map

The program runs as seven loops. Each loop closes with a green battery, a review
whose job is to refute the loop's own claims, and a report to the founder. Loops
marked with a founder gate do not start their next stage until the founder
answers. One writer holds the tree at a time.

## Actors

- **The founder.** Ratifies scope, answers the founder gates, recruits the human
  validators, and publishes the tag. The final click is always his.
- **The design stage.** Writes the contracts and this dossier before any writer
  starts. Owns 03-adr.md, 05-data-model.md and 07-verification.md.
- **The writer stage.** Implements one loop's work items inside a fence, serially,
  through the isolated work path in src/brothersbe/work.py.
- **The review stage.** Reads the finished loop and tries to disprove its exit
  gate rather than confirm it.
- **The gate battery.** The mechanical half: tools/sbe_design.py,
  tools/sbe_gate.py, tools/sbe_score.py and the suites under tools/, run by
  .github/workflows/brothersbe-gates.yml.
- **The human validators.** Five beginners and five engineers who run the
  benchmark project in Loop 6.

## Steps

| # | Step | Actor | Trigger | Exit gate | Exception path |
|---|---|---|---|---|---|
| 0 | Converge the tree | The founder and the design stage | The plan review is approved with changes | main carries every in-flight branch, the full battery is green on main, one release candidate tag sits on main's ancestry, and no fence is live | A concurrent session holds the tree: wait it out, never write across it |
| 1 | Security truth reset | The writer stage | Loop 0 exit gate met | A deliberately planted network import under src/ fails the merge gate, every test suite in tools/ appears in the workflow, and the security documents quote only claims that are true of main | A planted-import fixture that passes means the scan does not cover the path it claims: widen the scan, do not weaken the fixture |
| 2 | Concurrency and evidence identity | The writer stage | Loop 1 exit gate met and the founder has approved the receipt schema | The concurrency stress test loses no record, the bypass fixtures are red under the old behaviour and green under the new one, and no legacy evidence file clears an obligation without the wrapper | A schema change that would rewrite existing receipts stops the loop: the bump is forward only |
| 3 | One lifecycle | The design stage, then the writer stage | Loop 2 exit gate met and the founder has approved the lifecycle schema | A convergence suite in which every fixture, by repeatedly following the printed next action, reaches done or an explicit human decision, with no fixture oscillating, and the guided skills and the command line agreeing on every fixture | A second incompatible schema version proposed before the first ships stops the loop and returns it to contracts |
| 4 | Product surfaces, no server | The writer stage | Loop 3 exit gate met | Parity fixtures proving the command line text, the versioned result envelope and the map template render the same canonical state for the same fixture | A surface that cannot render the canonical state is descoped, never given its own copy of the lifecycle rules |
| 5 | Distribution honesty | The writer stage and the founder | Loop 4 exit gate met | Install, update, rollback and uninstall pass from clean environments on both supported platforms, the release checklist is green, and hosted continuous integration is green on the candidate commit | If the Linux leg turns out to fail for a structural reason, Linux is dropped from the 1.0 support claim with the founder's sign off, rather than the gate being weakened |
| 6 | Validation, candidate, release | The human validators, then the review stage, then the founder | Loop 5 exit gate met | Five beginners and five engineers complete the scenarios, the remediation sprint closes every critical and high finding, and a fresh review of the exact immutable candidate commit writes RELEASE or NO-GO with evidence | A NO-GO is a result, not a failure: it names what must change and the program returns to the loop that owns it |

## Loop 0 is done

Loop 0 closed on main at commit f7191de, the merge of pull request 6 carrying the
book branch, confirmed by `git log --oneline -1 f7191de` in this worktree.

Two platform defects were fixed on the way in, both visible in this worktree's
git log:

- **A locale-dependent sort in a book listing.** Commit f7f8d14, "Pin the vault
  listing's sort locale so two machines print the same book page". Two machines
  with different locales printed the same page in a different order, so the book
  output was not reproducible.
- **A path only macOS has, in one chapter.** Commit 42eabb7, "Stop chapter 13
  from typing a path only a Mac has". On Linux that chapter did nothing at all,
  and nothing said so.

Closing those two produced the first fully green run of the gate battery
including both Linux legs. The workflow matrix at
.github/workflows/brothersbe-gates.yml lines 44 to 49 runs ubuntu-latest and
macos-latest against Python 3.9 and 3.x, with the 3.9 leg blocking and the 3.x
leg informational. The run identifier for that first all-green result is
30689408725; that number comes from the Loop 0 close brief that commissioned this
dossier, not from a file in this repository, and it has not been confirmed
against the hosting service from here.

## Handoffs

| From | To | What is handed over | Contract |
|---|---|---|---|
| The design stage | The writer stage | An approved dossier and the schemas the loop depends on | No writer starts a loop whose contracts are not approved; a schema question raised mid loop stops the writers rather than being decided in the code |
| The writer stage | The gate battery | A candidate commit and the receipts earned for it | Every receipt is produced by the evidence wrapper, bound to the commit it was earned on, and no receipt is hand written |
| The gate battery | The review stage | A verdict set, with absence reported as NO-DATA rather than as a pass | A NO-DATA is never read as a pass, and a waiver is never read as a pass either |
| The review stage | The founder | A report naming what was proved, what was refuted, and what remains unverified | Anything not verified is listed by name; silence is not permitted to stand for success |
| The founder | The next loop | An answer to each founder gate, or an instruction to re-plan | A loop that reaches 75 percent of its budget cap without a passing acceptance test stops for re-planning rather than pressing on |
