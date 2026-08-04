# Release 1.0 status

The single program surface. `docs/release-1.0/FABLE-PLAN-REVIEW.md` holds the
approved plan and its amendments; this file holds where the work stands. No
second roadmap is created. Amendments are recorded as decisions in the plan
review, never as a new plan.

Last updated 2026-08-04, against `main` = `d11975e`.

Supersedes for release-1.0 purposes: `program/MASTER-PLAN.md` and the loop
programs. Those remain readable history and are not deleted; they are no longer
the authority on scope, sequence or release gates.

## Release recommendation

**NO-GO for a `1.0.0` tag.** Five gates cannot be closed by any agent and remain
open. This is not a schedule judgement; it is the five items in "Open, requires a
human" below. The deliverable of this program is a release-legal candidate with
those items stated plainly, not a tag.

## Repository topology

| Requirement | State |
|---|---|
| One public repository | met |
| `main` the only long-lived remote branch | met, `git ls-remote --heads origin` returns `main` alone |
| Zero open pull requests | met |
| Every deleted branch has a closure entry | met, `docs/release-1.0/BRANCH-CLOSURE.md` |
| No unique commit lost | met, 21 `archive/*` tags created before any deletion |

## Blockers

Seventeen were tested against source. Six did not survive as stated, which is
recorded rather than smoothed over.

| Id | Claim | Verdict after audit | State |
|---|---|---|---|
| CR-01 | installer initializes the wrong repository | CONFIRMED | closed |
| CR-02 | team profile not applied | CONFIRMED | closed |
| CR-03 | install tests prove syntax not installation | PARTIAL, update and rollback ARE tested | narrowed, open |
| CR-04 | version can lag distributed bytes | CONFIRMED | closed |
| CR-05 | competing installation truths | CONFIRMED, seven paths not four | closed |
| CR-06 | status cannot locate the documented layout | PARTIAL, `--team` finds them, single-project does not | open |
| CR-07 | absence confused with non-applicability | CONFIRMED, reproduced | open |
| CR-08 | verification does not complete proof atomically | CONFIRMED, reproduced | open |
| CR-09 | review has no durable completion state | PARTIAL | closed |
| CR-10 | beginner experience is prompt-driven | PARTIAL, engine state already exists and is ignored | open |
| CR-11 | the GUI is documentation, not an application | PARTIAL, a GUI is a ratified 1.0 non-goal | amended, deferred |
| CR-12 | release checklist is stale | CONFIRMED | closed |
| CR-13 | no independent reviews | CONFIRMED, 0 of 9 | disclosed |
| CR-14 | startup consumes too much context | CONFIRMED | closed |
| CR-15 | team tooling described more fully than it exists | PARTIAL | closed |
| CR-16 | repository topology not release-clean | PARTIAL, a stale inventory existed | closed |
| CR-17 | the battery destroys its own evidence | new, found during this program | closed |

CR-17 was not in the direction document. It was found by running the battery and
noticing that the run made the checksum manifest stale, which meant the release
suite could not be run and be green at the same time on any machine.

## Open, requires a human, cannot be closed by an agent

These are the reason the recommendation is NO-GO. None is a scheduling problem.

1. **Human usability studies.** At least five people unfamiliar with BrotherSBE
   and five engineers, against the thresholds in the direction document Part
   XIII. Kits exist at `release-control/validation-kits/`.
2. **Official Claude marketplace acceptance.** Requires submission and a decision
   by Anthropic. The one-click install claim is blocked on it.
3. **Windows verification.** No Windows machine was available. Windows behavior,
   native paths, PowerShell and the absence of `fcntl` are unverified.
4. **Signed artifacts.** Requires the maintainer's signing identity.
5. **The second RELEASE decision.** The direction document requires a fresh
   review and an independent human to both issue RELEASE. Only one of those two
   exists, and it is not independent of the work.

## Known gap disclosed rather than fixed

All nine merged pull requests carry zero submitted reviews, zero review requests
and zero `Approved-by` trailers. The project's own law L9 requires an approval
naming somebody other than the author and committer, so L9 reports NO-DATA on
this repository's own history rather than PASS. The founder decision on
2026-08-04 was to disclose this plainly rather than enable branch protection,
which as a single-maintainer repository would block every merge until a second
reviewer exists. Recorded in `docs/KNOWN-LIMITS.md`.

## Work parked at tags, not abandoned

Four local branches held the only copies of roughly 5,300 lines. They are
archived as immutable tags and deleted as branches. The strongest candidate for
a follow-up work item is the `.claude/settings.local.json` false positive in
`scripts/verify-install.sh`, which currently reports Claude Code's own
permissions file as, in that script's own words, "exactly the shape of a planted
backdoor". Details in `docs/release-1.0/BRANCH-CLOSURE.md`.

Those tags exist only on the machine that made them. The commits were never on
the remote, so preserving them off-machine is a separate decision the founder has
not yet been asked to make.
