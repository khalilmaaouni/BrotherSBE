# BrotherSBE test protocol

This is the structured half of testing. [TESTERS.md](TESTERS.md) is the
welcome page: what the tool is, how to install it, where to report. This file
is what to actually do once it is installed.

Two tracks. Pick the one that matches you, or run both.

- **Track A, the guided run.** About 30 minutes. You need no security or
  engineering background. It answers the question the whole product rests on:
  can somebody who has never seen this finish one governed change without
  reading internal documentation.
- **Track B, the red team.** About 30 to 45 minutes, for people comfortable in
  a terminal. It tries to break the assurance controls. Every scenario has one
  expected outcome: the tool blocks you and names the exact reason.

Report every finding as its own GitHub issue with the
[tester report template](.github/ISSUE_TEMPLATE/tester-report.md). One finding
per issue.

Before either track: `python3 bin/sbe doctor`. Paste its output into your
first issue if anything looks wrong.

## Track A, the guided run

Time each step roughly. If a step takes more than twice what the estimate
says, that is a finding on its own, and we want it.

| # | Do this | Expected | Estimate |
|---|---------|----------|----------|
| A1 | In Claude Code, in any project or an empty folder, type `/brothersbe:start` | It looks at where you are and recommends exactly one next action, in plain language | 2 min |
| A2 | Follow that recommendation, then keep following `/brothersbe:next` until it says the work is finished or it asks you for a decision | Every step names one action; you are never handed a menu of internal machinery | 10 min |
| A3 | At any point, run `/brothersbe:status` | It tells you where you are in language you would use out loud, not identifiers | 2 min |
| A4 | Work the prepared example instead if you prefer: follow [docs/guides/00-sandbox.md](docs/guides/00-sandbox.md) top to bottom | Every output block in the guide matches what your terminal prints, except hashes, dates, paths and machine-dependent lines, which the guide flags as expected to differ | 10 min |
| A5 | Open [docs/explainer/index.html](docs/explainer/index.html) in a browser | It explains the same ideas without jargon | 3 min |
| A6 | Try to finish a task without evidence: claim something is done and see what happens | It refuses, and the refusal names what is missing | 3 min |

What we most want from Track A: the first sentence that stopped making sense,
the first moment you did not know what to do next, and any place the tool
sounded confident about something it had not checked.

## Track B, the red team

These ten scenarios come from a hostile review of BrotherSBE's own assurance
model. Every one of them is a real bypass that a capable agent could attempt.
All ten are expected to FAIL, meaning the tool blocks them and names the exact
missing, invalid, stale, unprotected or out-of-scope fact.

Run these inside a throwaway clone, never a repository you care about.

| # | Attempt | Expected outcome |
|---|---------|------------------|
| B1 | Commit a database migration with no evidence receipt at all | Blocked. The reason names the missing required check, not a generic failure |
| B2 | Produce a receipt by running a trivially passing command, then label it as the migration check | Blocked. A receipt proves which registered check ran, and this was not it |
| B3 | Export a fake CI run id in your shell, then generate a receipt | The receipt is labeled CI-CLAIMED, never treated as protected evidence |
| B4 | Edit `CLAUDE.md` from a Bash command instead of the editor, for example with a redirect or a one line Python call | Blocked by the Bash write guard, or caught when the session tries to end |
| B5 | Delete the task registry or the policy file, then continue working | Blocked. A missing control is never read as permission |
| B6 | Change the evidence verifier and approve your own change | Blocked, or honestly reported as unprotected on a single-operator repository (see limits below) |
| B7 | Pass an empty receipts directory to the consumer action and see whether verification is skipped | Not skipped. Policy still evaluates and reports what is missing |
| B8 | Create a waiver with no owner, reason, expiry or approval | Refused, and any legitimate waiver shows as WAIVED, never as a pass |
| B9 | Reuse an old receipt after changing the registered check or its runner script | The old receipt is invalidated and named as stale |
| B10 | Break the hook wiring, then run the unit tests | The tests do not paper over it; the end to end check catches the broken wiring |

For every scenario, report: what you ran, what happened, and whether the
message told you the exact fact that was wrong. A block with a vague reason is
still a finding.

## Current assurance limits, stated plainly

Testing something honestly means knowing what is not finished. As of this
release:

- **No cryptographic attestation yet.** Evidence produced in CI is labeled
  CI-CLAIMED, which means CI shaped metadata was recorded but no protected
  identity was verified. The stronger label does not exist in this release,
  by choice, because a label must never be stronger than its evidence.
- **Single operator control plane.** The repository has one human. CODEOWNERS
  and the protection verifier ship, but a genuine second-party approval is
  not possible until a second person exists. We name this rather than staging
  a review that is really the same person twice.
- **The end to end host check runs locally, not in CI yet.** Its evidence for
  this release was produced on the release commit by hand and stored with the
  release notes.
- **Windows is experimental.** One known eval failure is open. Mac and Linux
  run the full battery on every merge.
- **No rollback command on the marketplace install path.** The git install
  path has one. This is queued as the next install fix.

If you find something outside this list that the tool claims but cannot back,
that is the single most valuable issue you can file.
