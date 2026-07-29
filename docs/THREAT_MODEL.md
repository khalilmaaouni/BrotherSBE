# Threat model

This page is written the way the rest of this project reports a verdict: what an
attacker gets, what mechanism here stops it, and, in the same breath, where
nothing here does. A threat model whose every row ends in "mitigated" is a
marketing page, so most rows below end somewhere less comfortable.

Scope. BrotherSBE is a skill, a set of standard-library tools, and a CI workflow
you copy into your own repository. It governs how a Claude Code session behaves
and what evidence a change carries. It is not a sandbox, not an access-control
system, and not a secrets manager, and it holds no key material of its own. Its
whole enforcement surface is: checks that read files and exit non-zero, a
workflow that runs them, and a checksum manifest. Everything below is bounded by
that.

One assumption stated once so it does not have to be repeated in fifteen rows:
an actor who can run arbitrary code on the machine, or who can edit this
repository's own tools and land it, is past every mechanism here. These controls
are for accident, drift, and an actor working inside the process, not for one
who owns the host.

## 1. A malicious or careless agent

Gets: a change that looks reviewed and is not. Invented figures, a schema
migration with no rollback, a "done" with no run behind it, a receipt typed to
satisfy a schema.

Stopped by: the four gates in `tools/sbe_gate.py` plus the silent-failure lints
in `tools/sbe_score.py`, run under `--strict` in
`.github/workflows/brothersbe-gates.yml`, which a `.sbe-exempt` cannot waive.
`sbe evidence run` executes the command itself and records the exit code, so a
duration or a result cannot be typed. `sbe impact` derives the tier from the
diff and can only raise a declared one.

Nothing stops: an agent that writes plausible prose about work it did not do, in
a place no check reads. The gates read named artifacts, and an agent that never
creates the artifact is caught only when a person asks for it. Nothing here
detects that a change NEEDED an approval or a receipt in the first place.

## 2. A malicious or careless developer

Gets: the same as row 1, plus the ability to edit the checks.

Stopped by: nothing in this repository, structurally. The checks are files in
the tree, and a developer with write access can change them. What survives is
that the change is visible: it appears in the diff, in the workflow file, and in
the checksum manifest.

Nothing stops: a developer who edits a check and its fixture in the same commit.
That is a code review problem, and this project's answer is that the check is
small enough to read, not that it is protected.

## 3. A compromised plugin release

Gets: code execution in every session that installs it, with the file access
that session has.

Stopped by: `CHECKSUMS.sha256` plus `scripts/verify-install.sh`, which verifies
both directions (every manifest file matches on disk, and every file on disk
appears in the manifest, so a planted extra file fails rather than riding
along). The tools are standard-library only, so there is no dependency chain to
compromise and no install-time script.

Nothing stops: a manifest that was tampered with in the same channel as the
code. A PASS proves the tree matches the manifest, not that the manifest is
authentic. Commits are unsigned, so there is no signature to check either. Take
the manifest from the release you trust, and pin a commit hash you recorded
yourself.

## 4. Tampered policy

Gets: gates that are configured to pass. A tier table edited downward, a
threshold relaxed, an exemption file that waives a check, an organization
telemetry policy quietly deleted.

Stopped by: severity and waiver rules that are themselves mechanical. A
`.sbe-exempt` reports WAIVED and never PASS, and it cannot waive the
silent-failure lints. An exemption with no reason, or a reason of "tbd", waives
nothing, because every reason goes through the same `answered()` test as every
receipt field. The telemetry policy file fails closed: unreadable, or carrying a
directive this version does not recognize, means capture is off, not on.

Nothing stops: an edit to the policy that is intended and wrong. Nothing here
knows what your tier table SHOULD say. And the telemetry policy is a policy
control on a cooperating machine: root can put the file at
`/etc/brothersbe/telemetry-policy.conf` where an ordinary user cannot edit it,
but a user who can run a patched copy of the script is past it.

## 5. Tampered evidence

Gets: a receipt that certifies a run nobody performed, or one that certifies an
older, greener version of the code.

Stopped by: `sbe evidence verify`, which refuses a broken `runId` seal, a head
commit that has moved, and a covered file that changed, vanished or was written
after the run ended. `sbe evidence show` prints the trust level on every
receipt, so LOCAL-ADVISORY is never something a reader has to remember.

Nothing stops: anybody who has read `src/brothersbe/evidence.py`. The seal is
tamper evidence, not a signature: the input is the receipt itself and there is
no key. `PROTECTED-CI` is only as trustworthy as whatever set `SBE_CI_RUN_ID`.
And nothing checks that the command was the RIGHT command: a receipt for `true`
is a flawless receipt for a run that tested nothing.

## 6. A fake approval

Gets: a money-path or partner-path change that reads as reviewed by a second
person.

Stopped by: `gate_approval` in `tools/sbe_gate.py`, which requires the approver
to be provably not the author, refuses to certify a difference it cannot prove,
and names every APPROVAL file it read.

Nothing stops: an author who records a colleague's name and email address
without telling them. The gate proves two identifiers differ; it does not
authenticate either one. A `Reviewed-in:` id resolves against nothing here, so
that path reports NO-DATA rather than an approval.

## 7. A direct push that bypasses the gates

Gets: an unreviewed change on the default branch.

Stopped by: nothing that ships here. `--strict` blocks only where a workflow
runs it, and a direct push to a branch with no protection runs no workflow at
all before the code is in.

Nothing stops: this one is entirely your repository's settings. Branch
protection, required status checks and CODEOWNERS are not shipped and cannot be
shipped by a skill. `docs/KNOWN-LIMITS.md` states the same thing about L16.

## 8. A disabled hook

Gets: a session with no autosave, no telemetry, and no fence lint, looking
exactly like a session where those ran and found nothing.

Stopped by: partial and honest reporting rather than prevention. Checks report
NO-DATA naming the file they could not read, never PASS. The startup nag says
when the telemetry heartbeat has been silent for 48 hours. `fence-lint` treats a
registry it could not read as occupied rather than free.

Nothing stops: removing a hook from your settings. Hooks are opt-in
configuration, disabling them is a supported action, and the capture switches
added for privacy make an inert default installation normal rather than
suspicious. On this axis, absence of telemetry is not evidence of tampering.

## 9. Workflow deletion

Gets: every gate silently gone, with a green tree.

Stopped by: nothing mechanical here. The deletion is visible in the diff and in
`CHECKSUMS.sha256` for the shipped copy of the workflow, and that is all.

Nothing stops: deleting `.github/workflows/brothersbe-gates.yml` in your own
repository. Requiring a review to change the workflow is a repository setting
this project cannot make for you, and says so.

## 10. Secret capture in telemetry or autosave

Gets: a credential, a customer name or an unreleased design persisted where
nobody expected it: a JSONL file in the vault, or a permanent git object in a
private ref.

Stopped by: capture is off by default, per category
(`BROTHERSBE_TELEMETRY_METRICS`, `BROTHERSBE_TELEMETRY_TRANSCRIPT`,
`BROTHERSBE_TELEMETRY_CORRECTIONS`), with an organization override that no local
switch can reverse. Nothing is read out of a transcript until a category that
needs it is on. `data-show`, `data-export` and `data-purge` make what is stored
visible, portable and removable. The autosave reads every candidate file's
CONTENT before `git add` runs, so a rejected file never becomes a git object,
and every rejection is recorded with its reason.

Nothing stops: a secret in a shape these patterns do not know. Both the
redactor and the autosave scan are pattern matching, stated as such everywhere
they are described. A local git ref is not a private one: a backup, a mirror or
a sync client can carry the snapshot off the machine, and nothing here can see
that happen.

## 11. Prompt injection from repository content

Gets: instructions in a README, a comment, a test fixture or a data file, read
by the agent as though the operator had typed them.

Stopped by: two narrow things. `atomic_append_text` flattens every line break in
an intent record, so injected text cannot forge a second timestamped record that
a later reader quotes as the operator's own words. `one_line()` neutralizes the
control class in report output. Beyond that, the hard gates constrain what an
injected instruction can achieve without evidence: it cannot manufacture an
approval or a receipt.

Nothing stops: the model believing repository text. There is no content
sanitizer here, no allowlist of trusted files, and nothing that separates
instruction from data inside a session. This is the largest unmitigated row on
this page, and it is a property of the harness rather than of this skill.

## 12. Path traversal and symlink attacks

Gets: a check reading or writing outside the tree it was pointed at, or a tool
following a link into a file it should not have opened.

Stopped by: `evidence_problem()` runs an access test before opening evidence, so
a FIFO cannot hang a scorer and an unreadable file cannot read as an absent one.
The lint skips its own source by file identity (inode), not by path spelling, so
a hardlink or a case-different spelling cannot make it scan itself or skip
somebody else's file. The autosave leaves symlinks alone: git stores the target
string, not the linked content. Recovery checks out into a NEW worktree at a
temporary directory created owner-only, never over your live tree.

Nothing stops: a path you hand a tool yourself. These tools open what they are
told to open, and a directory argument that is not a directory FAILs by name
rather than reading as a clean scan, which is the closest thing here to a
traversal control.

## 13. Monorepo scope confusion

Gets: a report that covers one package while claiming to cover the repository,
which is how unsaved work in a sibling package reads as work that was never
done.

Stopped by: the autosave snapshots the whole checkout, always, and refuses
rather than guessing when it cannot resolve or enter the directory git names as
the top of that checkout. This was a real
shipped bug: the hook's cwd is wherever the session sat, and `git add` from
there staged one subdirectory while the ref named the whole worktree. Receipt
coverage is what the caller named or what the diff shows, and a receipt covering
no file is NO-DATA rather than a pass.

Nothing stops: a gate pointed at one package by a person who believes it covers
all of them. Every verdict line names the root it read, which makes the mistake
visible in the output, not impossible.

## 14. An external integration compromise

Gets: whatever that integration could already do. A compromised MCP server, an
editor extension or a CI action runs with the session's own access.

Stopped by: nothing here, and the honest note is that this project adds no
integration to compromise. It makes no network call, has no account, no server,
no analytics and no telemetry endpoint, and the property is drift-tested: a test
parses every tool and fails if any imports `urllib`, `requests`, `socket` or
`http`, or if a shell tool invokes `curl` or `wget`.

Nothing stops: everything else in your session. This project does not change
what Claude Code itself transmits to Anthropic or to your cloud provider; see
`SECURITY.md` (Scope note) and choose your plan accordingly.

## 15. A compromised CI runner

Gets: the ability to report a green gate over a red tree, and the secrets in
that job.

Stopped by: nothing here. The gates run ON the runner, so a compromised runner
is a compromised verdict. `PROTECTED-CI` on a receipt records that
`SBE_CI_RUN_ID` was set by the environment; it does not authenticate it, and
nothing here can tell a run id minted by a CI system from one an agent exported
into its own shell.

Nothing stops: a runner that lies. What makes the label worth having at all is
that a protected CI configuration is a thing a human controls and an agent in a
worktree usually does not. That is a difference in reach, not a proof.

## What this page is not

It is not a claim that the mitigated rows are solved. Every mechanism named
above is a check that reads files and exits non-zero, and every one of them was
measured on the estate this project was built on, never in anyone else's CI. The
rows that end in "nothing stops" are the honest majority of this document and
are meant to be read first.
