# Handover: BrotherSBE 1.0 release closure

> HISTORICAL SNAPSHOT, marked 2026-08-05 at 1.0.0-rc.11. This file describes the
> repository as it stood on 2026-08-04 and is kept unedited as history. Its claims
> (including "Nothing is on GitHub") were true then and are not live state. The
> repository has been on GitHub since this snapshot was written: origin/main
> carries every merged release candidate through the current one, while
> published version tags and releases stop at v1.0.0-rc.1; the 17 archive/*
> tags are published under the recorded founder tag decision (17 pushed, 4
> held), and version tagging past rc.1 stays founder gated. Live state comes
> from `sbe status` and `git log`, never from this file.

Written 2026-08-04 at the end of the session that ran the closure program.
Audience: a fresh session, on a different machine, under a different account,
with no access to the conversation that produced this.

Verdict up front, so nothing below reads as a success report: **NO-GO for a
1.0.0 tag.** Five release gates cannot be closed by any agent, several checks
are failing right now, and the final merge is blocked. Sections 4 and 5 are the
honest parts. Read section 0 first; it is the only urgent one.

---

## 0. STOP. Nothing is on GitHub.

Every result described here exists ONLY on the machine that produced it,
`~/Documents/BrotherSBE` on Khalil's Mac.

Verified 2026-08-04:

```
git rev-parse main                                   d11975ed8e1e172e7c8502d1bea735d5245c2e0b
git rev-parse origin/main                            d11975ed8e1e172e7c8502d1bea735d5245c2e0b
git ls-remote --tags origin | grep -c archive        0
git tag --list 'archive/*' | wc -l                   21
```

`main` and `origin/main` are the same commit, so **none of the closure work has
been pushed**. It sits on the local branch `release/1.0-closeout` at `a558fce`,
three commits ahead of `main`. The 21 `archive/*` tags are the only surviving
copy of roughly 5,300 lines of otherwise-deleted work, and they exist locally
and nowhere else.

Starting a new session on a different PC before this is pushed does not continue
this work. It starts from `d11975e`, and everything below is gone.

**Do this on the original machine first:**

```bash
cd ~/Documents/BrotherSBE
git checkout main
git merge --no-ff release/1.0-closeout -m "Merge release 1.0 closeout"
git push origin main
git push origin --tags
```

The push is founder-gated and goes through GitHub Desktop under the standing
rule. The tags matter as much as the commits; without `--tags` the archived work
is still stranded.

One caveat, because pushing tags is publication and not only backup: four of
those tags carry work whose own commit messages say it is unverified and
unreviewed. Pushing makes that code public. That is a decision, not an automatic
consequence of taking a backup. If publishing is unwanted, copy the repository
directory to external storage instead.

---

## 1. What this session was asked to do

Finalize and release BrotherSBE per `BROTHERSBE_FINAL_RELEASE_DIRECTION.md` (in
`~/Downloads`), with a swarm of agents, full autonomy, ending with one `main`
branch.

That document describes a six to eight week program budgeted at 2.7 million
tokens. Parts of it cannot be executed by any agent: human usability studies with
real strangers, official Claude marketplace acceptance, Windows verification,
artifact signing, and a second RELEASE decision from an independent human. Those
were declared unreachable at the start rather than quietly skipped, and they are
why the recommendation is NO-GO.

---

## 2. What changed, and the command behind each claim

Every item was re-verified by the orchestrator after the agent's last edit,
rather than accepted from the agent's report. That distinction found two real
defects; see section 5.

### Repository topology, the headline ask

| Fact | Before | After | Proof command |
|---|---|---|---|
| Remote branches | 11 | 1 (`main`) | `gh api repos/khalilmaaouni/BrotherSBE/branches` |
| Open pull requests | 0 | 0 | `gh pr list --state open` |
| Worktrees attached | 6 | 1 | `git worktree list` |
| Branch tips archived | 0 | 21 | `git tag --list 'archive/*'` |

All ten remote branches were re-verified as strict ancestors of `origin/main`
with `git merge-base --is-ancestor` immediately before deletion, not merely
during the earlier audit. Every tip was tagged before the first delete.

Local branches were NOT deleted, because the merge into `main` is blocked. Nineteen
branches remain, all archived.

### Blockers

Seventeen were tested against source. Six did not survive the test as stated.
Ten were closed. Full table in `docs/release-1.0/STATUS.md`.

- **CR-01** the installer initialized the BrotherSBE clone, not the user's
  project. `install.sh` now captures the invoking directory before any `cd`,
  accepts `--target`, and refuses the distribution directory unless
  `--developer-self-test` is passed. Refusal exits 1; `--target` handles a path
  containing a space; dry-run writes nothing.
- **CR-02** the advertised team profile was never read. One reader now applies
  five supported fields and rejects unsupported fields BY NAME. Confirmed by
  installing into a scratch repository with a non-default `dossierRoot`.
- **CR-05** seven competing install paths reduced to three. `install.sh` was
  documented for the first time; it had zero mentions in any user-facing file
  despite being the only path that applies the team profile.
- **CR-09** `sbe review` persisted nothing. Now writes a commit-bound
  `11-review.json` with staleness computed at read time and self-review
  detection, mirroring the existing approval and convergence readers.
- **CR-12** `PUBLISH-CHECKLIST.md` claimed the repository was unpublished.
- **CR-13** disclosed rather than fixed; see section 5.
- **CR-14** startup context cut from 9,107 to 2,444 bytes, with all 24 law lines
  moved verbatim to `references/laws-full-digest.md` and a test pinning the
  ceiling.
- **CR-15** four team screens marked "designed, not built" in the playbook's own
  vocabulary.
- **CR-16** branch inventory now generated by `scripts/branch-inventory.sh`.
- **CR-17** found by us, not in the direction document; see section 5.

### Documents produced

`docs/release-1.0/FABLE-PLAN-REVIEW.md` (PLAN-APPROVED with three amendments,
one reversing the direction document on the GUI), `BRANCH-CLOSURE.md` (evidence
for all 22 branches plus a recovery record of full SHAs), and `STATUS.md` (the
single program surface). Version bumped to `1.0.0-rc.3` across all four
declaration sites.

---

## 3. What worked as method, and is worth repeating

**Auditors instructed to REFUTE, not confirm.** Every blocker was handed to a
read-only agent told its job was to disprove the claim. Six of seventeen came
back PARTIAL or REFUTED. Had they been told to confirm, this session would have
built a GUI that breaks a shipped security promise and rewritten a lifecycle
kernel that already exists.

**The orchestrator re-ran every done-check.** Agents reported honestly, but two
real defects survived their own tests and were caught only by independent
re-verification.

**One writer per file, fences before dispatch.** Six agents wrote concurrently
across roughly forty files with zero merge conflicts, because each brief named an
exclusive file list and every agent refused to touch anything outside it.

---

## 4. What is broken right now

### Blocked, needs a human

`git merge --no-ff release/1.0-closeout` into `main` was refused by the
permission classifier three times. This is the last step to local main-only. It
was not routed around.

### Failing checks at `a558fce`

1. **Three eval regressions.** The workflow gained a step, "Release invariant
   (distributable bytes cannot move without VERSION moving)", so it ships 26
   steps. Three documents still show 25: `README.md`, `docs/HOW-IT-WORKS.md`,
   `docs/guides/01-quickstart.md`. The quickstart also carries a fence labelled
   "verbatim" that no longer matches the workflow byte for byte. The checks
   catching this are correct. Fix the documents, never the check.
2. **`SECURITY.md` line-count drift.** It states `tools/` holds 22,330 lines; it
   holds 25,870. That is 16% against its own 15% threshold, so
   `test_the_stated_line_count_tracks_the_tree` FAILS. One-line fix, but recount
   after the document fixes above, not before.
3. **`CHECKSUMS.sha256` needs regenerating** after both, via
   `scripts/checksums.sh CHECKSUMS.sha256`.
4. **`cache-economy` FAILs** in the score lints. Not a code defect: it reads
   session telemetry from the Kay Vault outside the repository and fails on one
   session at 86% warm-read against a 90% floor. On a machine without that vault
   it reports NO-DATA and passes. Worth flagging as a gate-design problem in its
   own right, since a release gate should not depend on the maintainer's personal
   session cache statistics.

### Not attempted

CR-03, CR-06, CR-07, CR-08 and CR-10 remain open. Two were reproduced live and
are real:

- **CR-07**: running the gates on this repository's own dossiers returns NO-DATA
  on all four hard gates with exit 0, while `skills/next/SKILL.md` rung 5 says
  "anything not green means recommend verify". A T0 change loops on verification
  forever.
- **CR-08**: `sbe verify .` exits 0, then `sbe status .` immediately reports "no
  evidence store found". Verify never mints the receipts status expects.

---

## 5. Our mistakes, and what they cost

**Trusting a subagent's green report.** The installer agent reported all
done-checks passing. Independent re-verification found that a profile naming
`dossierRoot: blueprints` produced a config claiming `blueprints` while still
creating `design/.gitkeep` and a receipt naming `design/.gitkeep`. A
self-contradicting install, and the same class of defect CR-02 was about: a field
accepted and not honored. Cost one round trip.

**Adding a CI step without updating what mirrors it.** Broke three documentation
checks plus a verbatim fence. Cost a full battery run. In this repository the
workflow has four mirrors; grep for them before touching it.

**Regenerating the checksum manifest before the tree stopped moving.** Done
twice, wasted both times, because agents were still writing. Manifest
regeneration is the last action before commit, never mid-flight.

**Running the battery before committing.** Steps 22 and 23 archive HEAD, not the
working tree, so they measured the old commit and reported 49 extra files. Two
failures that were pure measurement artifact.

**Not asking about tag publication up front.** "Archive as tags, then delete" was
answered as a preservation question. Whether those tags should be PUSHED, which
makes 5,300 lines of self-declared unreviewed code public, was never put to the
founder. Still open, and now urgent because the tags are single-copy.

**Inherited, not ours, but real.** `install.sh`'s plugin fallback performed a
live network `git clone` into `~/.claude/skills/brothersbe` during an agent's
end-to-end test. That directory now exists on the original machine and did not
before. Harmless, but it means `install.sh` has a network side effect on a path
outside the repository that no test declares.

---

## 6. What to do better

- **Batch every irreversible-consequence question before starting.** Three were
  asked and answered well. The fourth, about pushing archive tags, surfaced too
  late.
- **Commit at every green.** Roughly 3,000 insertions sat uncommitted for hours.
  Nothing was lost, but one agent reported files transiently vanishing from the
  shared working tree, and recovery was luck rather than design.
- **Give long-running concurrent agents isolated worktrees.** One writer per file
  prevented conflicts, but all six shared one tree, so any `git add -A` or stash
  by any process affected all of them.
- **Do not let a check that reads outside the repository block a release.**
  `cache-economy` gates release on personal telemetry. That is a category error
  in gate design, not a failing repository.

---

## 7. What to do next, in order

Assume a fresh session on a new machine, after section 0 is genuinely done.

**Step 1, orient.** Read `docs/release-1.0/STATUS.md`, then
`FABLE-PLAN-REVIEW.md`, then this file. Do NOT treat the direction document as
current truth; the plan review records three places where it is wrong about the
repository.

**Step 2, get green.** Fix the three documentation CI blocks and the verbatim
fence, recount `SECURITY.md`, regenerate `CHECKSUMS.sha256`, then run
`sh release-control/baseline/run-battery.sh`. Expect `cache-economy` to pass on a
machine without the Kay Vault. Nothing else should fail. Bounded and mechanical;
one implementation-tier agent is enough.

**Step 3, finish the topology.** Merge `release/1.0-closeout` into `main`, delete
the 19 local branches (all archived), confirm `git branch -a` shows `main` alone.

**Step 4, the lifecycle blockers.** CR-07, CR-08, CR-06, CR-10, CR-03, in that
order. The plan review argues with evidence that this is a presentation-layer
correction, not the kernel rewrite the direction document implies:
`sbe status --json` ALREADY emits a canonical report carrying a `nextAction`
field and a per-finding `basis` field, and `status.py` already contains a
multi-dossier walker. The four beginner skills simply do not call any of it; they
instruct 21 independent probes and interpret prose at every decision point. Start
by making the skills consume `--json`. Do not build a new package tree first.

**Step 5, the GUI decision is already made.** Keep the no-server promise, defer
the GUI, and close the drift by generating the visual map from the same report
the command line prints. Not started.

**Never do:** build an HTTP server without first rewriting the `SECURITY.md`
claim of "no analytics, no account, and no server" AND the AST test at
`tools/test_sbe.py` lines 745 to 790 that enforces it. That test fails if any
file under `tools/`, `src/brothersbe/`, `hooks/`, `scripts/` or `bin/sbe`
imports `urllib`, `requests`, `socket` or `http`.

---

## 8. Standing facts a new session will not otherwise know

- Python on the original machine is 3.9.6. Code stays standard library only.
- The em dash and en dash ban is absolute and mechanically enforced over shipped
  prose.
- `evals/replay_book.py` and `evals/replay_guide05.py` re-execute fenced blocks
  from shipped markdown and compare byte for byte. Editing a code fence in the
  book or guides breaks CI unless the output genuinely matches.
- `docs/book/BrotherSBE-for-Dummies.html` is an untracked build output. Do not
  hand-edit it.
- The frozen Loop 0 battery evidence under `release-control/baseline/battery/` is
  immutable. `run-battery.sh` refuses to write there without `--rewrite-baseline`.
- Absence of evidence is NO-DATA, never a pass and never a block. This is the
  project's central law and every new check must express it.
- `v1.0.0-rc.2` exists as a LOCAL tag only. Origin carries only `v1.0.0-rc.1`.
  Any instruction naming an unpublished tag fails at clone time. The docs were
  fixed; the tag is still unpushed.
- All nine merged pull requests carry zero reviews and zero `Approved-by`
  trailers, so the project's own law L9 reports NO-DATA on its own history. This
  is disclosed in `docs/KNOWN-LIMITS.md` by founder decision, not fixed.

---

## 9. The five gates no agent can close

Human usability studies, official marketplace acceptance, Windows verification,
artifact signing, and the second RELEASE decision from an independent human.

The deliverable of this program is a release-legal candidate with those five
stated as open, not disguised as closed. Do not let a future session quietly
convert any of them into a PASS.

---

*Not run through the humanizer skill: the session hit its context limit while
writing this, and delivering the untouched draft is the documented fallback.*
