# Branch closure record

Measured at `origin/main` = `d11975ed8e1e172e7c8502d1bea735d5245c2e0b`, 2026-08-04.

This file exists because deletion is the last consequence of evidence, never the
first cleanup action. Every branch below was classified before anything was
deleted, and every tip was written to an immutable `archive/*` tag first, so no
disposition on this page can lose a commit. If a classification here is later
found wrong, the branch is recreated from its tag with `git branch <name>
archive/<name-with-slashes-replaced-by-dashes>`, and nothing needs recovering
from a reflog.

Classification vocabulary, from the release covenant:

- `MERGED`: every commit unique to the branch is already reachable from `main`.
- `SUPERSEDED`: it has unique commits that are intentionally obsolete.
- `PORT`: it has unique commits with value that must move into a 1.0 work item
  before deletion.
- `BLOCKED`: provenance or intent cannot be established, so deletion is
  prohibited until a human decides.

Method, per branch: `git rev-parse` for the tip, `git merge-base` for the base,
`git rev-list --count` both directions, and `git cherry main <ref>` for
patch-identity, which is the check that matters across a rewritten history
because it compares patches rather than commit hashes. A leading `+` from
`git cherry` means the patch is NOT in `main`; a leading `-` means an equivalent
patch IS in `main` under a different hash.

What this record does NOT prove: that the code on a `PORT` branch works. Two of
the four say in their own commit messages that they are unverified and
unreviewed, and no functional review of them was performed. Provenance
classification and a working-code judgement are different questions, and only
the first was answered here.

## Remote branches

All ten were re-verified as strict ancestors of `origin/main` with `git
merge-base --is-ancestor` immediately before deletion, not only during the
earlier audit. Each corresponds to a merged pull request except
`plugin-conversion`, which is fully reachable from `main` by an earlier merge
that predates the pull-request window inspected.

| Branch | Tip | Ahead | Behind | Unique patches not in main | Disposition | Archive tag |
|---|---|---:|---:|---:|---|---|
| `feature/beginner-finalization` | `f4e2b2b` | 0 | 23 | 0 | MERGED | `archive/feature-beginner-finalization` |
| `feature/dummies-book` | `42eabb7` | 0 | 11 | 0 | MERGED | `archive/feature-dummies-book` |
| `fix/impact-strict-no-data` | `96f5a01` | 0 | 24 | 0 | MERGED | `archive/fix-impact-strict-no-data` |
| `fix/py314-replay-excerpts` | `71841fe` | 0 | 33 | 0 | MERGED | `archive/fix-py314-replay-excerpts` |
| `fix/replay-doctor-python-version` | `d07e16a` | 0 | 29 | 0 | MERGED | `archive/fix-replay-doctor-python-version` |
| `loop0/close` | `c7c38a8` | 0 | 9 | 0 | MERGED | `archive/loop0-close` |
| `loop1/security-truth` | `4a1a5b9` | 0 | 3 | 0 | MERGED | `archive/loop1-security-truth` |
| `loop2/evidence-identity` | `db7296d` | 0 | 1 | 0 | MERGED | `archive/loop2-evidence-identity` |
| `plugin-conversion` | `1c90b25` | 0 | 77 | 0 | MERGED | `archive/plugin-conversion` |
| `release/v1.0.0-rc.2` | `9bc0717` | 0 | 19 | 0 | MERGED | `archive/release-v1.0.0-rc.2` |

Ahead of zero is itself the proof for these ten: a branch with no commit absent
from `main` cannot lose work when it is deleted, and no patch-identity check is
needed to establish that.

## Local-only branches

None of these ever existed on `origin`, so deleting them changes nothing a
collaborator can see. They are recorded because they hold the only copies of
some work, and because a local branch nobody has classified is exactly the state
this covenant exists to end.

| Branch | Tip | Ahead | Unique patches not in main | Disposition | Archive tag |
|---|---|---:|---:|---|---|
| `backup/pre-identity-rewrite-2026-07-28` | `5f332c7` | 139 | 0 of 137 checked | SUPERSEDED | `archive/backup-pre-identity-rewrite-2026-07-28` |
| `port-fence-hook` | `079b5e9` | 134 | 0 of 133 checked | SUPERSEDED | `archive/port-fence-hook` |
| `v2-lazy-core` | `4682c37` | 129 | 0 of 129 checked | SUPERSEDED | `archive/v2-lazy-core` |
| `v2-systems-design` | `5f332c7` | 139 | 0 of 137 checked | SUPERSEDED | `archive/v2-systems-design` |
| `claude/funny-kirch-1a11c1` | `18d67eb` | 1 | 1, content duplicated in main | SUPERSEDED | `archive/claude-funny-kirch-1a11c1` |
| `fix/version-marker-namespace` | `3bb7328` | 1 | 0 | SUPERSEDED | `archive/fix-version-marker-namespace` |
| `claude/happy-kilby-c38f6c` | `edea07e` | 3 | 2 | PORT | `archive/claude-happy-kilby-c38f6c` |
| `worktree-agent-a1563a6925670c1ca` | `136d76a` | 1 | 1 | PORT | `archive/worktree-agent-a1563a6925670c1ca` |
| `worktree-agent-abce7f3251f41442d` | `0536cec` | 1 | 1 | PORT | `archive/worktree-agent-abce7f3251f41442d` |
| `worktree-agent-ae762d20cd87669ff` | `802b1f1` | 1 | 1 | PORT | `archive/worktree-agent-ae762d20cd87669ff` |
| `worktree-agent-a2e2f84b3d27f281f` | `bffbd80` | 1 | 0 relative to the release branch | MERGED into `release/1.0-closeout` | `archive/worktree-agent-a2e2f84b3d27f281f` |

### Why the four large SUPERSEDED branches are safe

`backup/pre-identity-rewrite-2026-07-28`, `port-fence-hook`, `v2-lazy-core` and
`v2-systems-design` share a root commit that is NOT `main`'s root: same message,
same author timestamp, different hash. `git merge-base main <branch>` returns
nothing for all four, so they have no common ancestor with `main` at all. That
is the signature of a full history rewrite correcting authorship, and these are
the pre-rewrite lineage kept as a named backup.

Because `git cherry` compares patch identity rather than hashes, it still works
across unrelated histories, and it marked every non-merge commit on all four as
already present in `main`: 137, 133, 129 and 137 commits checked, zero unique.
A tree diff additionally shows the old lineage is missing roughly 45,600 lines
that `main` now has, which is the shape of an earlier snapshot rather than a
parallel feature line.

Stated honestly: the "intentionally obsolete" half of SUPERSEDED here is
inferred from branch naming, dates and the rewrite signature, not from an
explicit commit message declaring abandonment. The archive tags make that
inference cheap to reverse.

Note that `backup/pre-identity-rewrite-2026-07-28` and `v2-systems-design` point
at the identical commit `5f332c747f2b039d688345188b98bdac2d645f69`.

### The four PORT branches

These carry work that exists nowhere else. The founder decision on 2026-08-04
was to archive them as immutable tags and delete the branches, rather than merge
unreviewed code into a release candidate. The work is not abandoned; it is
parked at a tag and resumable.

- `claude/happy-kilby-c38f6c` (`archive/claude-happy-kilby-c38f6c`) carries a
  real fix: `scripts/verify-install.sh` currently reports Claude Code's own
  per-machine permissions file, `.claude/settings.local.json`, as an EXTRA file,
  which that script describes as "exactly the shape of a planted backdoor". The
  branch adds a targeted exact-path exclusion plus a calibration eval proving the
  exclusion is not a directory-wide hole. Confirmed absent from `main` by grep.
  This is a genuine user-visible false positive and is the strongest candidate
  for a follow-up work item.
- `worktree-agent-a1563a6925670c1ca` (`archive/worktree-agent-a1563a6925670c1ca`)
  carries 355 insertions of in-progress command work across `src/brothersbe/cli.py`,
  `src/brothersbe/decisions.py` and `tools/test_sbe_decisions.py`, self-labelled
  "pre-rebase".
- `worktree-agent-abce7f3251f41442d` (`archive/worktree-agent-abce7f3251f41442d`)
  carries 3,697 insertions of release-control tooling across 16 files, including
  `tools/sbe_release_control.py` and registries. Its own commit message reads
  "WIP paused mid-run by founder request, unverified and unreviewed".
- `worktree-agent-ae762d20cd87669ff` (`archive/worktree-agent-ae762d20cd87669ff`)
  carries 1,259 insertions of release-pipeline tooling, including
  `.github/workflows/release.yml`, `tools/sbe_release_bundle.py` and
  `docs/RELEASE-PIPELINE.md`. Same self-labelled unverified and unreviewed status.

## Deletion safety, checked before anything was deleted

- Open pull requests: zero. `gh pr list --state open` returned `[]`, so no open
  pull request has any of these branches as head or base.
- Orphaned tags: none. `v1.0.0-rc.1` and `v1.0.0-rc.2` were both confirmed
  ancestors of `main`, so no release tag is stranded by any deletion here.
- Worktrees: six branches were attached to worktrees and cannot be deleted while
  attached. They are detached as part of the closure, not force-deleted.
- Recovery: every tip listed above carries an `archive/*` tag created before the
  first deletion.

## Separate finding, not a branch issue

`v1.0.0-rc.2` exists as a LOCAL git tag only. It was never pushed to `origin`,
where only `v1.0.0-rc.1` is present. Anyone told to pin to the `v1.0.0-rc.2` tag
cannot resolve it from the remote. That is a release-integrity gap tracked
outside this file.
