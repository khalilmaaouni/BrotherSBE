# Plan review, BrotherSBE 1.0

Reviewed 2026-08-04 against `main` = `d11975ed8e1e172e7c8502d1bea735d5245c2e0b`,
the exact baseline the direction document names.

Verdict: **PLAN-APPROVED WITH AMENDMENTS**, recorded in section 12. Three
amendments are material and one of them reverses a requirement in the direction
document. Nothing here starts a second master plan; amendments are recorded as
decisions and progress is tracked in one place, `docs/release-1.0/STATUS.md`.

Every statement in the direction document was treated as a hypothesis until it
matched current source. Six of the seventeen blockers did not survive that test
unchanged, which is the point of running it.

## 1. Repository inventory at review time

| Fact | Value | How established |
|---|---|---|
| `main` | `d11975e` | `git rev-parse origin/main` |
| Declared version | `1.0.0-rc.2` | `VERSION`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` |
| Commits from `v1.0.0-rc.2` to `main` | 22 | `git rev-list --count v1.0.0-rc.2..main` |
| Tracked files differing over that range | 80 | `git diff --name-only v1.0.0-rc.2 main` |
| Executable files in that set | 8 | includes `src/brothersbe/evidence.py`, `status.py`, `tools/sbe_gate.py` |
| Remote branches at review | 11 | `git ls-remote --heads origin` |
| Open pull requests | 0 | `gh pr list --state open` |
| Merged pull requests | 9 | `gh pr list --state merged` |
| Submitted reviews across those 9 | 0 | `gh pr view <n> --json reviews` per pull request |
| Python | 3.9.6 | `python3 --version` |

## 2. Branch classification and closure

Recorded in full in `docs/release-1.0/BRANCH-CLOSURE.md`. Summary: all ten
remote branches classified MERGED with zero commits ahead of `main`; twelve
local-only branches classified, of which four are PORT and six SUPERSEDED.

The direction document predicted all ten would close as MERGED and instructed a
rerun before deletion. The prediction held for the remote. It did not hold for
the local set, which the document did not enumerate at all and which contained
the only copies of roughly 5,300 lines of work.

## 3. Product position and promise

Accepted without amendment.

> BrotherSBE is the verified change system for backend and data teams.

> Describe the change. BrotherSBE guides the team from intent to merge, gives one
> next action at a time, and proves every material claim.

This is defensible because it is narrower than every competitor surveyed and
because the assurance engine underneath it is genuinely the strongest part of the
product. It is also currently overclaimed in the opposite direction: the product
does not yet give one reliable next action, which is why the lifecycle blockers
outrank the positioning work.

## 4. Competitor patterns adopted and rejected

Adopted: one canonical install path per audience rather than seven; initialize
the target project rather than the tool's own checkout; a small public lifecycle
with progressive disclosure; deterministic state that the presentation layer
renders rather than reconstructs; explicit update and rollback as tested product
behavior.

Rejected deliberately: a large command and agent surface; a second
implementation language for packaging, since the product is already
standard-library Python and a Node installer would add prerequisites without
removing code; project-management integrations; and any autonomous merge or
deploy.

## 5. Architecture

The dependency direction in the direction document is accepted:
presentation depends on application, which depends on domain, which depends on
ports, which adapters implement.

Amendment: the document's implied rewrite is larger than the defect requires.
The audit established that `sbe status --json` and `sbe status --team --json`
ALREADY emit a sorted structured report carrying a canonical `nextAction` field
and a per-finding `basis` field, and that `src/brothersbe/status.py` already
contains a multi-dossier walker. The four beginner skills simply do not call any
of it: they instruct 21 independent probes and interpret prose at every decision
point.

So the correct first move is not to build a new kernel. It is to make the
presentation layer consume the engine state that exists. That is a change to
skill text and a small number of engine additions, not a new package tree.
Building the tree first would create a second surface to keep in parity while
the drift it was meant to fix continued.

## 6. Canonical schemas

Accepted as specified for the project, state, applicability, operation, decision
and review shapes, with one addition: the review record is implemented as a
dossier artifact numbered in the existing sequence, so it is discovered by the
same readers that already handle `09-convergence.json` and `10-approval.json`,
both of which already implement commit binding and staleness correctly and are
the pattern to copy rather than reinvent.

## 7. Installation and update

Accepted. The packaged Python CLI is the right call and the document's own
reasoning is sound: the product is already standard-library Python, and no
measured evidence supports a second stack.

Amendment, from evidence the document did not have: the installer defect is
worse than described, and part of the test criticism is wrong.

- Worse: `install.sh` is the ONLY path that applies the team profile, and it is
  named by zero user-facing documents. Two advertised profile fields,
  `vaultPathPattern` and `codeGuideDepth`, have no reader anywhere in the
  codebase. The `ci` field never produces the workflow it promises. And the
  defect has already fired for real: `.brothersbe/install-receipt.json` in this
  repository records `installedInto` as the BrotherSBE clone itself.
- Wrong: CR-03 claimed update and rollback are untested. They are.
  `scripts/test-upgrade-rollback.sh` archives the previous tag, then HEAD, then
  the tag again, verifying each. `scripts/test-install-artifact.sh` installs a
  `git archive` into a fresh directory and verifies it. Both run in CI. The
  genuine gaps are plugin activation, hooks firing, paths with spaces, and
  Windows.

## 8. GUI boundary

**This amendment reverses the direction document.**

Part VIII requires a local loopback GUI and Gate 4 blocks release on it. But
`design/final-release-program/01-purpose.md` lines 83 to 89 ratify "a local web
GUI server" as an explicit 1.0 non-goal, on the stated ground that it would make
the published `SECURITY.md` claim of no analytics, no account and no server
false. That claim is not prose: `tools/test_sbe.py` lines 745 to 790 AST-parses
every file under `tools/`, `src/brothersbe/`, `hooks/`, `scripts/` and `bin/sbe`
and fails if any imports `urllib`, `requests`, `socket` or `http`.

Building the GUI therefore breaks a shipped security promise and the passing test
that enforces it.

Founder decision, 2026-08-04: keep the no-server promise. The real defect
underneath the GUI request is one the repository already recorded itself, that
the visual map fills its slots from a state a model derives by hand and can
therefore disagree with what the command line prints. The fix is to generate the
map from the same report, not to add a server. Gate 4 is amended accordingly and
the GUI is deferred past 1.0 with the reason stated in the release notes.

## 9. Team model

Accepted. Objective, ownership, one writer per overlapping path, independent
review, staleness on head change, and handover with acknowledgment.

Amendment: `docs/TEAM-PLAYBOOK.md` described four operational screens in the
present tense that do not exist, while honestly labelling its integration stages
as not built. The screens are a ratified 1.0 cut, not missed work, and the
playbook now says so in its own vocabulary.

## 10. Dependency graph and ownership

Work was decomposed so that no two concurrent writers own overlapping files, and
each brief named its exclusive file list, its constraints, and a done-check the
agent had to run after its last edit and quote. Fences were written before
dispatch, never after.

Model assignment followed the document: the orchestrator owns architecture,
decomposition, adversarial review and the release recommendation; a lower
implementation model owns the lifecycle, installer, adapters and security fixes.
Read-only auditors were dispatched with an explicit instruction to REFUTE each
claim rather than confirm it, which is why six of seventeen blockers came back
PARTIAL or REFUTED instead of a clean sweep of confirmations.

## 11. Acceptance, adversarial cases, and kill criteria

The battery in `release-control/baseline/run-battery.sh` is the acceptance
suite, unchanged in content and order. Adversarial cases are the existing 527
regression evals plus the seeded no-data class sweep.

Kill criteria, any one of which blocks release regardless of schedule: an
assurance eval regresses; a NO-DATA verdict becomes a PASS anywhere; the zero
network property fails; the remote branch inventory contains anything but
`main`; distributable bytes change without a version change.

## 12. Verdict

**PLAN-APPROVED WITH AMENDMENTS.**

Amendments, each carrying its evidence above:

1. The GUI is deferred and Gate 4 is amended, because building it falsifies a
   published security claim and breaks the test enforcing it (section 8).
2. The lifecycle work is a presentation-layer correction over an engine state
   that already exists, not a new kernel (section 5).
3. CR-03 is corrected: update, rollback and artifact installation are tested
   today; the real gaps are narrower and named (section 7).

Not approved and not attempted, because no agent can perform them: the human
usability studies, official marketplace acceptance, Windows verification,
artifact signing, and the second RELEASE decision from an independent human. The
release recommendation is therefore NO-GO for a 1.0.0 tag, and the deliverable of
this program is a release-legal candidate with those five items stated as open,
not disguised as closed.
