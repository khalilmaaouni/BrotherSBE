# Known limits

Every law already states what its machinery does not do, but those statements
live inside the digest and the law text, where the honest half of the product
is the hardest part to read. This page collects them: one heading per limit,
each naming the law it qualifies and the file where the full text lives. Three
laws (L6, L11, L14) live in `SKILL.md` itself; the other sixteen and the six
phases live in the `references/*.md` file its routing table names.
Nothing here is new; a limit stated only on this page and nowhere else would
be a bug in this page.

## The spine is a discipline, not a control

"Design before verification" and "install the check before writing the work"
are [human] lines: no tool computes whether you did. Full text: `SKILL.md`
(The spine), `DIGEST.md`.

## Nothing detects that a change needed an approval (L9)

The gate verifies an approval that was declared. It cannot notice a money-path
change that declared nothing, and nothing resolves a `Reviewed-in:` id, which
is why that path reports NO-DATA rather than an approval. Full text:
`references/laws-hard-gates.md` L9 and `LAWS-REFERENCE.md` (the hard gates).

## This repository's own merged pull requests carry no independent review (L9)

Applied to this repository's own history rather than to a change the gate is
checking, L9 reports NO-DATA, not PASS. Verified on 2026-08-04: all nine
merged pull requests in this repository (numbers 1 through 9) carry zero
submitted reviews, zero review requests, and zero issue comments (`gh pr
list --state merged --json reviews,reviewRequests,comments`, each field
empty on every one of the nine), and `git log origin/main --format='%h|%s|
%(trailers:key=Approved-by,valueonly)'` shows every `Approved-by` trailer on
every merge commit empty. L9 requires an approval naming somebody other than
the author and committer, and self-approval FAILs; nine merged pull requests
with zero reviews is the absence of that evidence, not a weaker form of it.
This page does not imply a review happened out of band, because none did.
The founder has chosen plain disclosure of this gap over turning on branch
protection for this repository. Full text: `references/laws-hard-gates.md`
L9, and the entry directly above.

## Only one tag is published on origin

Verified on 2026-08-04:

```
$ git ls-remote --tags origin | grep -v '\^{}'
dacee900d24d40b351bc117ebbf001406bb09699	refs/tags/v1.0.0-rc.1

$ git ls-remote --tags origin 'refs/tags/v1.0.0-rc.2' | wc -l
0
```

`v1.0.0-rc.1` is the only tag this repository has ever pushed to origin.
`v1.0.0-rc.2` was cut locally (`docs/RELEASE.md`, "What has actually been
executed") but never pushed, and the version this tree carries moves again
with every release. A pinning command that names a specific `vX.Y.Z` fails
at clone time the moment the named tag is not the one actually published,
which is why `docs/ROLLOUT.md` and `docs/RELEASE.md` now have the reader run
`git ls-remote --tags <repository-url>` and substitute the tag they see,
rather than a version typed into this page going stale the next time a
release is cut. Full text: `docs/ROLLOUT.md` (Upgrade and rollback),
`docs/RELEASE.md` (Pinning an install to a release, What has actually been
executed).

## The tier comes from answers about contracts that no checker reads

The intake asks whether the change alters a data model, an API contract, or a
file interface. Those answers are what set the tier, and the tier is what
decides which design artifacts are required. Nothing anywhere in this tool opens
a schema, a contract, an OpenAPI document, a protobuf file or a file format
specification, so nothing can confirm or contradict an answer: `sbe_intake.py`
records what it is told, `compute_tier` applies the rule to that record, and the
design checks then verify the artifacts a tier requires are present and carry
content. A wrong answer produces a lower tier, fewer required artifacts, and a
run whose every verdict is honest about what it read. The check on that answer
is a person.

## The forcing conditions are read by a person (L6)

Stop-on-ambiguity, contradiction, gate collision, and disproven assumption are
[human]: the checkpoint shape is prose the session follows or does not. Full
text: `SKILL.md` L6.

## The fence checks read registries, not the world (L13)

Fence hygiene and budget-vs-tier run only over registries named in
`BROTHERSBE_REGISTRIES`, and only over fence lines containing the word
"agent". Writing the fence, comparing scopes, and resuming after a kill are
human. Full text: `references/laws-parallel-writers.md` L13, `LAWS-REFERENCE.md`.

## The case-fold confirmation trusts one probe of the project's own volume

`tools/sbe_fence_hook.py::paths_overlap` closes the case-insensitive-filesystem
escape (`docs/BYPASS-COVERAGE.md` row 21) by retrying a missed comparison
case-folded and confirming the fold against the filesystem before trusting it,
never on the string match alone. When both spellings already exist, the
confirmation is `os.path.samefile`, which is definitive. When one or both do
not exist yet, there is nothing to `samefile`, so the confirmation instead
probes whether the PROJECT ROOT's own directory entry answers to a case-swapped
spelling, on the reasoning that case (in)sensitivity is a property of the
volume, not of any one file on it. Two edges follow from that reasoning and are
worth stating rather than assuming away: a root whose own directory name
carries no letters to swap (all digits or symbols) cannot be probed, and this
hook's fail-open bias means an inconclusive probe allows the write rather than
denying it; and a project split across two mounts with different case
sensitivity (a fenced file reached through a symlink onto a different volume
than `root`) is answered by `root`'s volume, not the target's. Neither edge is
fixtured, because neither can be constructed without a filesystem this suite
does not control.

## Blast radius revokes nothing (L14)

"No apply rights on production state" is a working rule plus whatever access
control your estate has. Nothing here can revoke a credential your shell
already holds. Full text: `SKILL.md` L14.

## The CI workflow guards nothing until you copy it (L16)

`--strict` blocks only in a repository that wired it. No CODEOWNERS and no
branch protection ships, so nothing makes editing the workflow require a
review; that is your repository's setting. Full text:
`references/laws-overrides-and-waivers.md` L16.

## Most of the close is human (L17)

Only the vault session log has a check, and only where `BROTHERSBE_VAULT`
points at a vault, which the shipped CI does not set: on a stock runner every
ledger check is NO-DATA at exit 0. Open items, the failures index, the
scorecard and the self-score cap are human review. Full text:
`references/laws-closing-and-review.md` L17.

## Telemetry observes, it never decides

The SessionEnd hook writes the ledger and decides nothing; no CI step reads
it. The checks fed by it are named on their own digest lines. Full text:
`DIGEST.md`, `LAWS-REFERENCE.md` (Telemetry).

## The UNVERIFIED label is the agent's to write

No tool applies it. A session that fails to label unverified output is not
caught by a check. Full text: `references/laws-hard-gates.md` L7,
`references/laws-overrides-and-waivers.md` L16, `DIGEST.md`.

## The doc-honesty guard reads proximity, not grammar

The guard that checks shipped prose against what the tools do now reads a
document the way a reader does, joining hard-wrapped lines into the block they
form, so a false sentence no longer escapes by wrapping. What it still cannot
do is decide which word a negator governs: a sentence carrying "no", "not" or
"never" within 24 characters before a claim is read as denying it, so an
assertion that happens to carry one ("there is no doubt the gate walks up to
the repository root") reads as honest. Requiring the negator to sit
immediately before the claim was tried and reverted, because it flags the
honest denials this project actually writes, where the negator is the clause's
subject. Full text: `evals/run_evals.py` (_SCOPE_DENIAL, _reader_blocks).

## Published figures are derived only where a page says so

A block marked `derived-by: <script>` is re-run by an eval on every suite
execution and the page fails when it disagrees with the script. That is the
whole mechanism, and its boundary is the marker: a number typed into ordinary
prose with no marker is checked by nothing here, exactly as it was before. The
eval-count guards and the lint-count guards cover their own numbers
separately. Full text: `evals/run_evals.py`
(every-derived-figure-in-a-shipped-doc-recomputes),
`scripts/derive_refusal_table.py`.

## The hollowing sweep is not a proof

The meta-test hollows each check's own declared worked example, prints its
coverage, skipped cases and exemptions, and claims nothing about inputs no
fixture plants. Full text: `INVARIANTS.md` (what the register does not claim),
`evals/README.md`.

## Never run in anyone else's CI

Every green run this project cites happened in its own repository or on the
estate it was built on. No external adoption, and no second estate, is
claimed anywhere.

## The ledger rewrite guard leaves one instant uncovered

A maintenance rewrite (migrate, dedup) re-measures the live ledger under the
writer lock immediately before its rename and carries any bytes appended
since its read into the rewrite, so an append that took the 15 second
unlocked fallback survives. What remains is the instant between that final
measurement and the rename itself: an append landing exactly there would be
in neither the rewritten file nor the rewrite's read. The window is
microseconds, not the fallback's 15-plus seconds, and it is covered post-hoc
rather than prevented: every unlocked append records itself in
`<ledger>.unlocked-appends`, and a rewrite that finds a record from inside
its own window says so after the rename and points at the per-run byte
backup. Full text: `tools/sbe_telemetry.py` (_rewrite_locked).

## The writer lock needs a filesystem that honors flock

The telemetry writer lock is an advisory `flock` on a sidecar file. On a
filesystem that does not honor it (a network mount is the ordinary case; the
vault is documented as a local directory for this reason), the lock cannot be
taken, and the degradation is the safe one rather than a silent loss: an
append proceeds unlocked so the row is never dropped and records itself in
`<ledger>.unlocked-appends`, and both maintenance rewrites (migrate, dedup)
REFUSE to rewrite and say so, naming the possibility that the platform has no
working lock. Executed by forcing `flock` to return the unsupported error on
this host: the appended row survived, the fallback recorded itself, and both
rewrites left the file byte-identical. What is lost on such a mount is
maintenance, not data: migrate and dedup will never run there until the vault
sits on a filesystem whose locks work. Full text: `tools/sbe_telemetry.py`
(_writer_lock).

## The approval identity proof has a measured refusal remainder (L9)

The approval gate certifies "the approver is not the author" only when the
difference is proven: by an email address differing at positions the host
reads, by name structure, by readable letters, or by code point within one
script. Two names of ONE script compare by code point (two different Ethiopic
or Devanagari letters are different glyphs, not look-alikes of each other),
which accepts near-identical glyph pairs WITHIN a script as a limit, exactly
as it already does for CJK ideographs. What remains refused is the soft
class: same-script name pairs whose every differing letter is one the
confusable tables fold to ASCII, where a certificate resting on the fold's
coverage would rest on a table this project's own history proves incomplete.
Every refused pair passes by recording an email address that differs from the
author's, which the gate accepts as proof of difference; the refusal sentence
names that escape, and the second-to-last column below exercises it rather
than asserting it. That escape is HOST-DEPENDENT, not a blanket "any two
different-looking addresses prove two people": on gmail.com and
googlemail.com, an address that differs from the author's only by a dot in
the local part reaches the SAME mailbox by the host's own aliasing, so the
gate declines to certify it as a second person, and the escape does not
close those pairs. The last column below exercises that case too, rather
than asserting it, and it is why the escape column must never be read on
its own. Full text: `tools/sbe_gate.py` (gate_approval, _canonical_email),
`tools/sbe_checks.py` (the four character kinds).

The figures below are not typed. They are the output of a script you can run,
over pools it publishes, and an eval re-runs that script and fails when this
page disagrees with it. An earlier edition of this section typed its numbers
by hand over pools it did not publish; the code underneath moved, and the page
went on reporting a measurement nobody could reproduce, which is the same
false assurance this project exists to refuse. Regenerate with
`python3 scripts/derive_refusal_table.py`.

<!-- derived-by: scripts/derive_refusal_table.py -->

```text
Recomputed by scripts/derive_refusal_table.py on 2026-07-27.
Pools of 10 real names per script, 45 unordered pairs each, name only,
no email address recorded. "Unproven" means the gate declines to certify
the two are different people and says so; it is never a silent pass.

script        pairs  unproven  percent  still unproven with distinct emails  still unproven with a gmail dot-alias
Amharic          45         0        0                                   0                                      0
Arabic           45         0        0                                   0                                      0
Armenian         45         0        0                                   0                                      0
Georgian         45         0        0                                   0                                      0
Greek            45         9       20                                   0                                      9
Hebrew           45         0        0                                   0                                      0
Hindi            45         0        0                                   0                                      0
Japanese         45         0        0                                   0                                      0
Korean           45         0        0                                   0                                      0
Russian          45        13       29                                   0                                     13
Thai             45         0        0                                   0                                      0
Vietnamese       45         0        0                                   0                                      0

Real names read as placeholders by the vacuity backstop: 0 of 240 names
across 12 scripts, two disjoint pools of 10 per script.
```

## The citation check never opens a page

`citation-inventory` proves that every external URL cited in README.md,
SKILL.md and docs/ has a `docs/CITATIONS.md` entry answering claim,
population, date and limit, and nothing more. It verifies structure and
coverage offline, makes no network call, and cannot prove a page still says
what its entry recorded; its own verdict sentence states that limit.
Re-checking content against the live page is a human job at review time. Full
text: `docs/CITATIONS.md` (preamble), `docs/HOW-IT-WORKS.md` (section 6).

## Windows is untested

The shipped CI runs Linux and macOS. The two `sh` tools and the POSIX file
modes have never been exercised on Windows, and `SECURITY.md` already treats a
POSIX mode there as a courtesy.

## Every threshold was measured on one estate

`tables/`, the RUBRIC baselines, and the lint's own numbers were measured
where this project was built. Re-measure on yours; NO-DATA is a legal score.
Full text: `README.md` (What this is not), `RUBRIC.md`, `INVARIANTS.md`.

## The impact scan proposes a floor, and reads paths more than it reads code

`sbe impact` derives the five intake answers from the git diff and runs them
through the SAME tier table a person's answers go through, so the two can never
drift apart. What it cannot do, stated where the behavior is:

- Two of the five answers are not derivable from a diff. `consumers` is assumed
  `none`, and `crosses_boundary` is inferred only from infrastructure-shaped
  files, so a service call added inside existing code is invisible to it. Both
  assumptions can only LOWER the proposal. The proposed tier is therefore a
  FLOOR: it can say a change is bigger than declared, never smaller.
- A PASS from it means "nothing in the diff contradicts the declared tier". It
  does not mean the declared tier is right.
- Detection is mostly path-shaped, with content patterns only for SQL data
  definition language, destructive operations, and personal-data field names.
  A payment path in a file named nothing like a payment is not detected.
- Content patterns read ADDED lines only, so removing a sensitive line is not
  classified as adding one. The reverse is also true: a deletion that IS the
  risky change (dropping a column in code rather than in a migration) is not
  caught by a content pattern.
- Every changed file no detector covers is reported under `unmeasured`, by name.
  A clean report over an unsupported language is not available from this tool.
- Maturity: INTERNAL-EVAL. It has been exercised on this repository's fixtures
  and on this repository's own diff, and on no other estate.
Full text: `src/brothersbe/impact.py`, `docs/CLI.md`.

## The evidence wrapper binds a run to a commit, and proves less than that sounds

`sbe evidence run` executes the command itself, so the duration, the exit code
and the output digests come from a run rather than from a keyboard, and
`sbe evidence verify` refuses a receipt whose commit or covered files have
moved. What that does NOT establish, stated where the behavior is:

- The `runId` seal is TAMPER EVIDENCE, not a signature. It catches a plausible
  receipt typed to satisfy the schema. It does not stop anybody who has read
  `src/brothersbe/evidence.py`, because the input is the receipt itself and
  there is no key. A locally generated receipt is therefore never more than
  LOCAL-ADVISORY, and `show` says so on every receipt rather than leaving it to
  the reader to remember.
- `PROTECTED-CI` is only as trustworthy as the environment that set
  `SBE_CI_RUN_ID`. Nothing here can tell a run id minted by a CI system from one
  an agent exported into its own shell. The label states where the value came
  from; it does not authenticate it. What makes it worth having is that a
  protected CI configuration is a thing a human controls and an agent in a
  worktree usually does not.
- Nothing checks that the command was the RIGHT command. `sbe evidence run --
  true` produces a flawless receipt for a run that tested nothing. The receipt
  records the argv it ran (redaction aside, see below) so a reader can see
  that; deciding whether that argv is the work the gate wanted is a person's
  job, and no field here does it.
- `argv` is recorded as text, on purpose, because a receipt whose command was
  paraphrased proves nothing about what happened. Before it is written, every
  token is checked against `SECRET_PATTERNS`, the same list
  `tools/sbe_telemetry.py` already uses to redact an operator's own messages
  (imported from there, not a second list kept here). A match becomes a named
  marker, `[REDACTED:<shape>]`, and the receipt's `argvRedactions` field says
  how many were found, so a reader never has to guess whether argv is verbatim.
  This is a NARROWING, not a fix: the pattern list is finite by nature, so a
  credential typed in a shape none of these patterns recognize (a bespoke
  internal token format, a password with no recognizable prefix) still reaches
  the receipt whole, and the digests-only policy that covers stdout and stderr
  does not cover argv either way. Pass secrets through the environment or a
  file, never as an argument, when the shape is anything you are not certain
  the pattern list would catch. Fixtures pin both halves: a planted
  pattern-matching secret comes out as the marker
  (`tools/test_sbe_evidence.py::test_a_secret_shaped_argv_token_is_redacted_not_recorded_verbatim`),
  and this residual limit stays a decision rather than a surprise.
- The digests prove the same bytes came back. They carry none of them, so a
  receipt cannot be used to audit what a command printed, only to detect that it
  printed something different.
- Coverage is what the caller named, or the diff between base and head. A change
  to a file the receipt does not cover is invisible to `verify`, and a receipt
  covering no file at all is NO-DATA rather than a pass, naming why. A diff
  cannot tell code under test from another evidence receipt that happened to
  land in the same range; see "Evidence covering evidence" below for the
  narrower limit that leaves open.
- The staleness check is deliberately strict in one direction: a covered file
  written after the run ended FAILs even when its bytes are unchanged, so a
  checkout or a formatter that rewrites a file identically invalidates the
  receipt. Regenerating is cheap; a receipt that speaks for a file it did not
  see is not.
- `verify` compares against the CURRENT head of the working directory it is
  given. A receipt made on a branch tip and verified at a merge commit FAILs,
  correctly and inconveniently: it is evidence for the commit it was made
  against and for no other.
- Writing a receipt INTO the repository it covers makes that tree dirty, so the
  next receipt generated there is advisory. Keep receipts outside the tree, or
  ignore them, or accept NO-DATA.
- Maturity: INTERNAL-EVAL. Exercised by 27 fixtures in
  `tools/test_sbe_evidence.py` that build real git repositories and run real
  commands, on this repository and on no other estate.
Full text: `src/brothersbe/evidence.py`, `docs/CLI.md`.

## Evidence covering evidence (T6)

A receipt's `coveredFiles`, when computed from a diff rather than an explicit
`--covers` list, is every file that changed in `base..head`, and that diff
cannot distinguish "the code this run tested" from "another evidence receipt
that happened to land in the same range". A receipt regenerated at a fixed
`--out` path is the ordinary shape of a CI re-run (the design, gate and score
checks all write to well-known paths on every push), not an edit to any code
under test. Reproduced: generate `design.json` with `--covers app.py`, commit
it; generate `gate.json` with the default diff-based coverage, which then
names `design.json` alongside `app.py` purely because of where it landed;
regenerate `design.json` in place. Before this fix, `gate.json` FAILed with
"covered file .sbe/evidence/design.json now hashes to ...: the code changed
after the evidence was made", for a check that never claimed to test
`design.json` and whose own covered code (`app.py`) never moved: the evidence
store poisoning itself.

The fix is scoped to interpretation, not to what a receipt records:
`evidence.verify` gained an `exclude_dirs` parameter (default: none, so every
existing caller keeps today's behavior unchanged) naming path prefixes whose
`coveredFiles` entries are still recorded and shown in the note, but never
hashed, timed, or allowed to fail or pass a verdict. `status.py`'s
`_scan_evidence`, the one place this repository reads every receipt in the
store to build BROKEN CLAIMS and COMPLETED EVIDENCE, passes the evidence
store itself. A receipt whose ENTIRE coverage sits under an excluded path
reads NO-DATA, never a silent PASS built on nothing.

What this does NOT close, stated where the behavior is:
- The exclusion is per-caller, not global. `src/brothersbe/decisions.py` and
  `src/brothersbe/work.py` also call `evidence.verify` (for a decision
  package's judged receipts and a task's close postcondition) and neither
  passes `exclude_dirs`; the same accidental coupling can still reach them
  through the identical diff-based mechanism. Closing every caller was out of
  this stage's scope, named here rather than silently left open.
- This does not touch `generate()`: a receipt's own `coveredFiles` field
  still lists an evidence-store path when the diff found one, faithfully, as
  a record of what the diff actually contained. Only what that record is
  allowed to PROVE changed.
- This does not touch the commit-binding check (`headCommit` must equal the
  current HEAD). A receipt that is itself committed to the repository is, by
  construction, generated before the commit that adds it exists, so its
  recorded `headCommit` can never equal that commit's own SHA; the very next
  commit of any kind, evidence or not, makes it stale under the rule two
  entries above ("`verify` compares against the CURRENT head..."). That is
  the pre-existing, already-tested behavior
  (`tools/test_sbe_status.py::TestBrokenClaims::test_a_stale_receipt_is_named_under_broken_claims_and_exits_1`),
  and this fix leaves it exactly as it was: a receipt that is committed and
  then followed by any further commit is still named under BROKEN CLAIMS for
  that separate, unrelated reason.
- The exclusion is a path-prefix match against `coveredFiles` entries as
  RECORDED (POSIX-style, relative to the repository root). A receipt covering
  an absolute path, or a path spelled with backslashes, is not matched and
  not excluded; this repository's own receipts never record either shape.
Full text: `src/brothersbe/evidence.py` (`_check_covered`, `verify`),
`src/brothersbe/status.py` (`_scan_evidence`),
`tools/test_sbe_status.py::TestEvidenceStoreSelfPoisoning`.

## The privacy controls are defaults and patterns, not guarantees

Capture is off by default per category, an organization switch can force it all
off, and the autosave reads file CONTENT before any git object is created. What
none of that does, stated where somebody deciding whether to install this can
read it:

- A file name exclusion has never prevented secret capture and this page will
  not say otherwise. A credential lives in a normally named source file at
  least as often as in a file called `.env`, and this project shipped a comment
  claiming the name patterns meant "credentials never enter the autosave ref".
  They never did. The content scan is what addresses that class, and it is
  pattern matching over the shapes it knows: a secret in a shape it does not
  know still enters the snapshot.
- A local git ref is not a private one. `refs/brothersbe/autosave/<id>` never
  leaves the machine by any action of this tool, and that is a statement about
  this tool only: a backup, a mirror, a sync client or anything else that copies
  `.git` carries the snapshot with it, including whatever a snapshot preserved
  before the content scan existed. Snapshots taken by an earlier version are
  still in your object database; `git reflog <ref>` lists them.
- Excluding a file loses work. An excluded file is left out of the snapshot
  entirely, so an unsaved edit to it is preserved nowhere. The scan is
  deliberately conservative, so it will sometimes exclude a file holding no
  secret at all. Both cases are named with their reason in
  `99-System/telemetry/autosave-exclusions.log`, which is the only reason this
  trade is visible rather than silent.
- Three of the scan's reject reasons are limits, not detections: a file past
  the size limit, a binary file, and a path git could not print literally were
  never scanned at all. They are excluded and recorded on exactly that basis,
  because a file the scanner could not read must not be treated as clean.
- The scan reads every candidate file on every snapshot, and the tick mode
  snapshots every N tool calls. On a very large worktree that cost is real and
  nothing here caps it. Past `BROTHERSBE_AUTOSAVE_MAX_EXCLUSIONS` (200) the
  snapshot is refused outright rather than truncated, because a `git add` whose
  argument list is too long produces an empty tree that would then be committed
  as though it were the work.
- Content already committed is not the autosave's doing and not its to withhold.
  The snapshot index is seeded from HEAD so tracked work is never dropped, so a
  secret that is already in a commit rides along in the snapshot tree. The
  control here is about what a snapshot ADDS to the object database.
- The organization telemetry override is a policy control on a cooperating
  machine. Root can put the file where an ordinary user cannot write it, and a
  user who runs a patched copy of the script is past it regardless. It fails
  closed on an unreadable or unrecognized policy, which is the strongest thing
  it can honestly do.
- Redaction is unchanged and still best effort. What changed is that nothing is
  read out of a transcript until a switch says so, which means the redactor is
  no longer the only thing between a session and a file on disk.
- `data-show` and `data-purge` see one vault. Copies made by a backup, a mirror
  or an export you took yourself are outside their reach, and `data-export`
  deliberately creates one such copy.
- The resume brief flip (founder, 2026-07-29) traded a standing placeholder
  for silence. `transcript` off used to still write a file naming the switch,
  so a resumed session read something even with capture off. Off now means no
  file at all: the switch is named once, on stderr, at the moment the
  `precompact-brief` hook declines to write. A resumed session's SessionStart
  hook has nothing on disk to relay, because there is nothing on disk, so
  anyone who was not watching that stderr line never sees it; SECURITY.md and
  `data-show` are where they find out afterward.
Full text: `tools/sbe_telemetry.py` (the capture policy block),
`tools/sbe_autosave.sh` (the content scan block), `SECURITY.md`,
`docs/THREAT_MODEL.md`.

## A green bypass suite covers the scenarios it covers

An external review listed 35 ways a person or an agent could get past these
controls. `docs/BYPASS-COVERAGE.md` is the table: one row per scenario, each row
COVERED (with the fixture named), UNREACHABLE HERE (with the missing thing
named: a GitHub token, branch protection, a warehouse, a real second estate) or
UNCOVERED (with what covering it would take). As this file is written, 18 rows
are COVERED, 6 are UNREACHABLE HERE and 11 are UNCOVERED.

So: a green `python3 tools/test_sbe_bypass.py` means the COVERED scenarios were
tested. It is not a statement about the other 17, and it is not a claim that the
list of 35 is the whole space of bypasses. Some fixtures in that file pin a
bypass that WORKS, and carry `_is_a_limit` in their names for exactly that
reason; a limit fixture is a tripwire on this documentation, not coverage.

Two holes found while writing that table were fixed in a later wave, both in
`src/brothersbe/evidence.py`. `sbe evidence verify` used to open the receipt
path with no access check, so a FIFO where a receipt was expected hung the
command forever with no verdict in either mode; it now runs the same
`evidence_problem` access check the hard gates use before opening, and refuses
a FIFO, socket, device or unreadable file by name in bounded time instead
(`tools/test_sbe_evidence.py::TestAccessAndTimeout`). The evidence wrapper's
`subprocess.run` used to carry no timeout at all, so a command that hung, hung
the wrapper; `sbe evidence run` now takes an optional `--timeout SECONDS` that
kills the child and writes no receipt rather than one that could later verify
PASS. It has NO DEFAULT, on purpose: a silent one would kill a legitimate
long-running test suite, which is the exact false-positive shape this
project's own kill criteria warn against, so a command run with no `--timeout`
can still hang the wrapper forever, precisely as before. One more limit,
measured rather than assumed (a `sh -c "sleep 60 & sleep 60"` run under
`timeout=2` returned in 2.00 seconds and left both sleeps alive): expiry kills
the CHILD, not its descendants, because nothing here kills a process group. The
refusal comes back at the bound, and a grandchild the command spawned may keep
running, detached, after the wrapper has already said no. Both were row 35 of
the table, now COVERED with that residual stated on the row itself.

Full text: `docs/BYPASS-COVERAGE.md`, `tools/test_sbe_bypass.py`,
`docs/CLI.md` ("sbe evidence").

## The task registry only governs writers who register

`sbe task close` detects an out-of-scope write after the fact by reading the
diff, which is exactly why it survives Bash. But the postcondition runs at
close, and only a task that was OPENED can be closed: an actor who never runs
`sbe task open` never meets it, and reviewer separation orders roles inside
the registry only. In front of that actor stands only the fence hook, which
is advisory and fails open with a stated reason. Full text: `docs/CLI.md`
("sbe task"), `docs/HOW-IT-WORKS.md` (the two-layer scope model).

## The registry file itself has no lock

`.sbe/tasks.json` is rewritten atomically (write temp, rename), so it is never
half-written, but two simultaneous `sbe task open` calls are last-write-wins
and one of the two records can vanish. Concurrent writers of the REGISTRY
itself are out of scope by design: no service, no daemon, no lock. `sbe task
check` is the recovery tool, because it re-runs the overlap scan over whatever
the file now holds.

## The registry exempts its own file from the postcondition

Opening a task writes `.sbe/tasks.json`, so that one path, by exact name, is
excluded from the changed-path comparison at close; otherwise no single-writer
flow could ever close clean, which is this control's own kill criterion. The
exemption is one exact path, not the `.sbe/` directory: receipts under
`.sbe/evidence` still count, which is what the reviewer-receipt refusal reads.

## Task expiry is informational, and nothing writes "abandoned" yet

`expiry` is a date a human reads in `sbe task list`; nothing deletes or closes
a task on a clock, so a stale open task keeps refusing overlapping opens until
somebody closes it (with `--force` and a recorded who and why, if its work is
gone). "abandoned" is a legal status value in the schema and no command in
this wave writes it.

## The fence view is one-directional

`sbe task fence` renders markdown FROM the JSON registry for humans reading a
STATE.md style file. Nothing reads markdown fences back into the registry, so
a hand-edited fence line and the registry can disagree, and the registry is
the one the postcondition reads.
## The adoption kit proposes, and verifies only what a filesystem can answer

`sbe adopt` detects a repository's stack and proposes a policy file and a CODEOWNERS example;
`sbe init` installs BrotherSBE's own local footprint. What neither does, stated where the
behavior is:

- `sbe adopt`'s report names three protections that live on GitHub's code review platform, not
  on a filesystem: branch protection, required status checks, and whether review from a code
  owner is REQUIRED. None of the three can ever read PRESENT here. They report
  UNVERIFIABLE-HERE unconditionally, naming what checking them for real would take (a GitHub
  token with repo scope, plus admin rights on the repository), because this tool holds no
  GitHub credentials and asks for none. This is the kill criterion the plugin conversion plan
  states for this wave, made into a fixture:
  `tools/test_sbe_adopt.py::TestAdoptionReportNeverClaimsPresent`.
- A CODEOWNERS file merely existing in the tree IS a fact this tool can read, and it is reported
  separately, under `localFacts`, so it is never folded into a claim about whether GitHub
  actually requires that review. The file existing and GitHub requiring it are two different
  facts, one local and one not, and only one of them is checkable from a clone.
- The repository policy `sbe adopt` proposes (`.brothersbe/policy.json`) is NOT wave 3's
  eventual policy file and JSON schema, which had not shipped as this wave was written. It is a
  smaller, provisional shape built from what stack detection can already see, and the file says
  so on its own `note` field. Replacing it once wave 3 ships its schema is expected, not a
  regression.
- Stack detection walks the tree pruning conventional vendor and build directories by name
  (`.git`, `node_modules`, `vendor`, `venv`, `.venv`, `dist`, `build`, `__pycache__`, `.tox`,
  `.mypy_cache`, `.pytest_cache`, `target`), never by content. A project keeping first-party
  source inside a directory with one of those names is under-detected, and a very large
  unconventionally-named vendor directory is walked in full, which costs real time on a large
  repository with nothing here to cap it.
- Detection of a contract, migration or dbt-shaped path reuses the SAME path patterns
  `sbe impact` runs against a diff (`brothersbe.impact.DETECTORS`), applied here to a full tree
  walk instead. The same limits `sbe impact` already states about those patterns being
  path-shaped rather than content-read apply here too: a migrations directory named something
  this project's patterns do not recognize is not detected.
- The CODEOWNERS example this proposes carries the placeholder `@REPLACE-ME` on every line.
  Neither `sbe adopt` nor anything else in this project has repository membership to read a
  real username or team from, and a placeholder left in place protects nothing: GitHub will not
  resolve it to an owner. `docs/ADOPTION.md` says so before the checklist of what to click.
- `sbe init --with-consumer-ci` copies this INSTALLATION's own shipped
  `.github/workflows/consumer-check.yml` and `.github/actions/sbe-consumer/action.yml`. When
  those files cannot be read from the installation running the command, the copy is skipped and
  named under a warning rather than writing a partial or empty file in their place.
- Both `sbe adopt` and `sbe init` propose deterministic content (no timestamp, no run id) so a
  second `--apply` can recognize nothing changed. The one exception is `sbe init`'s own install
  receipt, which legitimately carries an install timestamp; it is written or refreshed only when
  something else was actually written this run, and left untouched on a no-op run, which is what
  keeps "running it twice changes nothing" true even though the receipt itself is not
  deterministic content.
- Maturity: INTERNAL-EVAL. Exercised by `tools/test_sbe_adopt.py` against real temporary git
  repositories built by the test itself, and against this repository's own diff, and on no other
  estate.
Full text: `src/brothersbe/adopt.py`, `src/brothersbe/initcmd.py`, `docs/ADOPTION.md`,
`docs/CLI.md`.

## The release candidate ships packaging, not a release

Wave 10 adds `.claude-plugin/marketplace.json` (so `claude plugin marketplace
add` has something to read), an install-artifact test, and an
upgrade-rollback test. None of that is a release. Four things stay blocked,
named here in this tool's own voice rather than left for a reader to infer
from what is absent:

- **Signed release.** No tag this project produces is signed. A signed
  release is blocked on a key the founder holds, not on anything this code
  could compute for itself, and nothing here claims otherwise. `git tag -a`
  (`docs/RELEASE.md`, `docs/ROLLOUT.md`) makes an annotated tag, which
  records who ran the command and when; it is not a signature, and this file
  does not call it one.
- **Branch protection.** Unchanged from the limit already stated above under
  "The adoption kit proposes, and verifies only what a filesystem can
  answer": branch protection, required status checks, and required code-owner
  review are GitHub platform settings, never `PRESENT` from a local read,
  always `UNVERIFIABLE-HERE`. Shipping a marketplace manifest changes nothing
  about that; there is still no GitHub token anywhere in this project.
- **`gh auth`.** Nothing in this wave runs `gh auth login`, stores a GitHub
  token, or automates a GitHub-side action on anyone's behalf. Every
  GitHub-side step `docs/ROLLOUT.md` and `PUBLISH-CHECKLIST.md` describe
  (opening a repository, protecting a branch, pushing a tag) is a human
  authorizing it in the GUI.
- **Real-estate maturity claims.** The install-artifact test and the
  upgrade-rollback test are exercised against THIS repository's own git
  history (`tools/test_sbe.py`'s new `TestMarketplaceManifest` class checks
  the manifest shape and re-runs the installed CLI's own validator; the two
  shell scripts are calibrated by breaking each fixture and watching it go
  red, then restoring it and watching it go green, against this
  repository and a disposable clone of it). None of that is evidence from a
  second, independent estate. Maturity: INTERNAL-EVAL, same word this file
  uses everywhere else, meaning the same thing everywhere else: proven here,
  claimed nowhere beyond here.

The upgrade-rollback script carries one limit of its own, stated where the
behavior is rather than only here: as of this wave, this repository has cut
no tag (`docs/RELEASE.md`), so `scripts/test-upgrade-rollback.sh` finds no
previous release to upgrade FROM and reports NO-DATA rather than PASSED,
every time it runs, until the first tag exists. A NO-DATA verdict here is not
a weaker pass; it is the honest absence of the one fixture the script needs,
named as exactly that.

Full text: `docs/ROLLOUT.md`, `scripts/test-install-artifact.sh`,
`scripts/test-upgrade-rollback.sh`, `tools/test_sbe.py`
(`TestMarketplaceManifest`).

## A gate exemption cannot tell a real reason from a well-formed fake one

`tools/sbe_gate.py` now reads `.sbe-exempt` too, close to how `tools/sbe_design.py`
already does: a directory holding a gate artifact that is not live work (a
finished project's old receipts, a teaching example) names which of the four
hard gates it waives and why, and the report prints WAIVED with that reason on
every run instead of PASS, FAIL or NO-DATA. The mechanical part is real: a file
naming no gates, a file naming a gate and a blank or whitespace-only reason,
and `gates: *` are each refused as their own FAIL, by name, and the artifact
underneath is still checked rather than silently dropped. One check design's
own exemption has that this one does not: `tools/sbe_design.py::parse_exemption`
holds its reason to a minimum word and character count so a one-token reason
cannot pass; this channel checks only that a reason is present, not how short
it is, so `reason: x` waives a gate here where design would refuse it. What is
not mechanical either way, stated as plainly as design's own docstring states
it: no test here can tell a real reason from a well-formed fake one.
`reason: this is a finished project kept for history` waives a gate whether or
not that sentence is true; a blank-reason check only proves a reason was
written, never that it is accurate or long enough to say anything. The control
this buys is narrower than "the waiver is justified": it is "the waiver is
visible, names the gate it covers, and is not a blank switch", which is what
the WAIVED line, the per-gate waiver count, and `--strict-waivers` are for. A
waiver's only expiry is a human deleting the file or narrowing what it names;
nothing here reads a date, an owner, or an approver out of `.sbe-exempt`, the
same limit `tools/sbe_design.py`'s own exemption already carries and this
channel inherits rather than closes.

Full text: `tools/sbe_gate.py` (`parse_exemption`, `find`), `tools/sbe_design.py`
(`parse_exemption`), `evals/run_evals.py` (the `gx1`-`gx4` fixtures).

## A dossier's binding only resolves a commit held as a loose object

`00-intake.json` may carry an OPTIONAL `binding` block: the head commit a
dossier was written against, plus a sha256 per artifact it covers
(`docs/BYPASS-COVERAGE.md` row 23). Left out, nothing changes: no commit is
read, no digest is checked, and the design checks behave exactly as they did
before this block existed. Recorded, `tools/sbe_design.py::_binding_problem`
checks it by reading git's own on-disk files directly (`HEAD`, a ref, a loose
object's path) rather than by running git as a subprocess, which is also why
`tools/test_sbe_bypass.py::test_the_design_checks_never_read_a_commit_which_is_a_limit`
still passes unchanged: it pins the absence of a `subprocess` import and of a
`git log`/`rev-parse` call, and this stays true of a file that resolves a
commit by reading `.git` itself.

The gap that reading `.git` by hand carries and a real git binary would not:
confirming a bound commit id names a real object is checked only against
LOOSE objects under `.git/objects`; a commit folded into a pack by
housekeeping (`git gc`) is invisible to this check. HEAD itself, and any
commit still close enough to it that nothing has packed it, resolve
correctly, which covers the ordinary case a dossier's own author hits: bind
right after committing, and the bound commit is the loosest object there is.
A binding naming a commit from far enough back in history to have been
packed reads NO-DATA here rather than a confirmed FAIL or PASS, the same
"cannot resolve, so cannot vouch either way" answer this project already
gives a snapshot id or a rehearsal id it cannot look up. Row 23 stays
UNCOVERED for exactly this reason: an optional control only a dossier's own
author opts into is not a covered bypass, and this project does not round a
partial, honestly-limited check up to COVERED.

Full text: `docs/BYPASS-COVERAGE.md` row 23, `tools/sbe_design.py`
(`_binding_problem`, `_git_dir`, `_resolve_head`, `_object_exists`),
`tools/test_sbe.py` (`TestDossierBindingScenario23`).

Two more edges the fixtures pin: a bound artifact that no longer exists or cannot be read FAILs quoting the path (never a silent skip), and a bound path that resolves outside the repository FAILs as a broken claim even when the outside file exists and its digest is true, because a design artifact lives in the tree it binds.

## Two honest narrowings from the baseline repair (2026-07-30)

The book's replay check masks one declared-volatile substring, the live
merge-base diff line, in chapter 03's status block; every other byte of every
excerpt is still compared literally, and the calibration in
`tools/test_sbe_book.py::TestDeclaredVolatileLine` proves the mask cannot
widen silently. The private-name scan applies a stands-alone rule to exactly
one vendored minified file; a name planted standalone in that file is still
caught, and a letter-flanked substring of a generated identifier is not. Both
narrowings exist because the alternative was a control that cried wolf, and a
control that cries wolf gets ignored, which is worse than a narrow one.

## sbe plan derives structures, not intent

There is no LLM anywhere in `tools/sbe_plan.py`'s derivation or validation:
every task, citation and verdict comes from parsing a dossier and applying
the rules the spec names, never from reading intent prose beyond those
structures. That has a direct consequence at the point where a dossier's own
decision names no paths: the plan it derives has a first task that owns
nothing, the ownership check FAILs that task by id, and the remedy is a
better dossier, not a guess, because nothing here can infer ownership the
dossier never stated. Freshness is checked the same mechanical way: recorded
dossier digests are compared against the dossier files on disk, so a dossier
edited after planning in a way that changes its digest is caught and named,
but an edit that happens to keep the file's bytes identical is invisible to
this check, because a digest cannot see past its own bytes. Full text:
`docs/specs/2026-07-30-sbe-plan-derivation.md` (What this deliberately does
not do), `tools/sbe_plan.py`, `tools/test_sbe_plan.py`.

## sbe work isolates, it does not merge

`sbe work` gives a task its own branch and its own git worktree, and closes it
only on a postcondition plus a bound receipt, but nothing in this module ever
merges, rebases onto the default branch, pushes, or touches a production
system; that boundary is a source level fixture, not a policy note
(`TestNoMergeLaw::test_work_module_never_constructs_a_merge_rebase_or_push_argv`).
Landing a task's branch onto the default branch, deploying it, and applying
anything to production state stay human decisions this tool never automates,
the same [human] line the rest of this page already draws around merge,
deploy, and apply.

`check`'s scope comparison reads the diff between the worktree's current
state and the task's recorded base, the same postcondition machinery
`sbe task close` already runs. A change made and then reverted inside the
worktree, before `check` or `finish` ever run, therefore leaves no diff to
read: it is invisible to scope checking precisely because scope checking
only ever sees the diff, never a history of edits. This is the same shape of
limit stated above for the task registry's own postcondition, applied here
to a worktree instead of a shared tree.

Worktree isolation is a filesystem convenience, `git worktree add` giving one
task its own directory and branch, not a sandbox. Nothing here restricts
network access, process execution, environment variables, or reads and
writes outside the worktree's own path: an agent working inside a task's
worktree can still read or write anywhere its own OS permissions allow. The
worktree keeps two writers from colliding on the same files; it does not
confine what either writer's code can do while it runs.

Full text: `docs/specs/2026-07-30-sbe-work-lifecycle.md`,
`src/brothersbe/work.py`, `tools/test_sbe_work.py`.

## pr verify reads GitHub, it does not police it

There is no GitHub token on the reference machine, so `sbe pr verify`'s live
path is opt-in, not the default: without GITHUB_TOKEN, GH_TOKEN, or a working
`gh auth token`, every control that needs the network reports NO-DATA with a
remedy, never PASS, and the exit is nonzero
(`test_no_token_no_gh_is_no_data_everywhere_with_remedy_and_nonzero_exit`).
Branch protection and required checks are read from the GitHub API on that
call or reported UNVERIFIABLE; this tool never infers protection state from
local git config, hooks, or history, because a local guess is not the same
fact as what GitHub currently enforces. Approval state is re-fetched from the
API on every run and never cached across runs or within one, so the verdict
always reflects the request that just went out, not a stale copy. Because of
that, a force-push landing between the first fetch and the last one in the
same run is UNVERIFIABLE rather than a guess in either direction, naming both
shas the check saw, and the remedy is the same command again
(`test_a_force_pushed_head_between_first_and_last_fetch_is_unverifiable`).

Full text: `docs/specs/2026-07-30-sbe-pr-verify.md`,
`src/brothersbe/prverify.py`, `tools/test_sbe_prverify.py`.


## converge compares structures, not intent

`sbe converge` reads names, shapes, and receipts, nothing subtler. Contracts
are diffed only when the changed file parses as JSON OpenAPI at both commits;
YAML has no standard-library parser here, so a YAML contract is named
unmeasured and blocks a clean CONTRACTS verdict rather than passing unread.
The DATA dimension scans changed migrations for DROP TABLE and DROP COLUMN
statements against the names the data model documents, and nothing subtler:
a rename, a type change, or a semantic contradiction is beyond this scan.
ARCHITECTURE compares declared component names against new top-level
directories and everything deeper (technology choices, dependencies,
infrastructure, recovery) is NO-DATA by design: intent is not readable from
a diff. Scope compares path names against plan ownership and dossier-named
paths; it does not read file contents, and a changed file that is neither
source-shaped nor detector-matched is named unmeasured rather than counted
clean or flagged as unplanned noise. A FINAL PASS therefore means "nothing
this tool can read contradicts the dossier", and its own output names every
dimension that had nothing to read.


## status --team reads the estate, it does not phone anyone

Approval facts in the team view are only as fresh as the saved report; the
view never calls GitHub, so a review dismissed a minute ago still reads PASS
until `sbe pr verify` runs again, and the staleness line it CAN compute (a
report bound to a commit that is no longer head) is labeled derived. An
unreadable source is a visible unavailable finding, never a silent gap. One
repository per invocation: cross-repository estates are out of scope. And a
structural fact this view had to design around rather than fix: plan task
ids are per-change (every derived plan starts at T01) while the task
registry is one global table, so records are attributed to changes
best-effort by id, conflicts are computed globally over all open records so
no collision can hide, and two changes cannot hold an open task with the
same id at the same time. A team-profile designRoots entry that resolves
outside the repository is refused by name and never walked; discovery stays
inside the tree it was asked about.


## What the first external round taught converge and plan (2026-07-31)

Receipt matching is shlex-canonical on both sides now, and detector kinds
honor content patterns, both learned from foreign estates the hard way
(docs/EXTERNAL-PROOF-2026-07-31.md). Two limits stay: converge SCOPE matches
ownership by file path only, so a later range touching the same files for an
unrelated reason still reads in scope (the deeper diff-content comparison is
future work), and sbe plan does not re-check the tier's required-artifact
list because sbe design owns that gate; run design before plan and CI runs
both. sbe adopt still proposes this repository's own layout to foreign
trees; the existence-filtered proposal is designed and lands with its suite
rewrite, not before.


## The zero-network scan now walks the whole tree, not only tools/

`TestAuditableSurface.test_the_zero_network_property_holds_by_ast` in
`tools/test_sbe.py` used to parse only `tools/*.py` and `tools/*.sh`. It now
parses `src/brothersbe/*.py`, `hooks/**/*.py`, `scripts/**/*.py`, `bin/sbe`,
and `install.sh` too, the same surface `SECURITY.md`'s own suggested audit
grep names (`grep -rnE "urllib|requests|socket|http|curl|wget|subprocess"
tools/ src/ hooks/ scripts/ bin/`). One exact path is allow-listed rather
than a directory, so no sibling module can hide behind it:
`src/brothersbe/prverify.py`, `sbe pr verify`'s own documented GitHub API
client (see "pr verify reads GitHub, it does not police it" above). The
shell side of the same test now also flags `nc`, not only `curl` and
`wget`. `install.sh`'s own documented `git` network calls (`git ls-remote`
at line 98, `git clone` or `git pull --ff-only` at lines 106 to 110) are not
what this scan bans; the property under test is the absence of a direct
`urllib`, `requests`, `socket` or `http` import and the absence of a
`curl`, `wget` or `nc` invocation, not the absence of `git` as a local
subprocess call, which the test's own docstring already names as one of the
three benign shapes a hit is allowed to be.

Full text: `SECURITY.md`, `docs/THREAT_MODEL.md`,
`tools/test_sbe.py::TestAuditableSurface`.


## Every suite that existed now runs in CI, except one, and that is a choice

`.github/workflows/brothersbe-gates.yml` used to run a handful of suites by
name while thirteen others sat in `tools/` passing locally on nobody's
merge. It now runs all of them on both OS legs: `test_sbe_adopt.py`,
`test_sbe_book.py`, `test_sbe_bypass.py`, `test_sbe_converge.py`,
`test_sbe_decisions.py`, `test_sbe_evidence.py`, `test_sbe_install.py`,
`test_sbe_plan.py`, `test_sbe_prverify.py`, `test_sbe_status.py`,
`test_sbe_status_team.py`, `test_sbe_tasks.py`, and `test_sbe_work.py`,
alongside the suites already wired before this pass. Every
`tools/test_sbe_*.py` file now appears in the workflow exactly once, with
one deliberate exception: `test_sbe_prverify_live.py` stays unwired. It is
not the same suite as `test_sbe_prverify.py` (that one is canned and
offline, every GitHub API call routed through a fake fetch, and it is the
one that runs in CI); the live script needs both `SBE_LIVE_GH_REPO` and
`SBE_LIVE_GH_PR` set, plus a token discoverable the same way `sbe pr
verify` itself discovers one, none of which this workflow provides. Without
those, the live script already prints one NO-DATA line and exits 0 by its
own docstring, so wiring it in would either skip silently on every normal
run or force this repository to carry a GitHub token as a CI secret for a
script most runs would never exercise. The workflow carries a comment
stating this reasoning next to the `test_sbe_prverify.py` step it sits
beside. No strictness flag changed to get here; the diff is purely
additive.

Full text: `.github/workflows/brothersbe-gates.yml`.

## A hard-gate receipt with no headCommit still passes unbound

`tools/sbe_gate.py`'s `gate_numbers`, `gate_migration` and `gate_ran` now read
an optional `headCommit` field, the same field name and comparison
`src/brothersbe/evidence.py`'s own `sbe evidence` receipt store already
carries (`_check_commit`). When the field is present and names a commit that
is not the directory's current `git rev-parse HEAD`, the receipt is stale
evidence for the change that is actually checked out and the gate FAILs
rather than PASSing over it: a `numbers-manifest.json`,
`migration-receipt.json` or `ran-receipt.json` copied forward from an earlier
commit no longer clears the gate at a later one. Calibrated, in
`evals/run_evals.py`'s
`a-stale-headcommit-ran-receipt-no-longer-passes`,
`a-stale-headcommit-numbers-manifest-no-longer-passes` and
`a-stale-headcommit-migration-receipt-no-longer-passes`, each of which pins a
receipt sound in every other field to an old commit, moves HEAD on with a
second, unrelated commit, and asserts FAIL; with `_commit_problem` in
`tools/sbe_gate.py` neutralized to always return `None`, the same three cases
read `want=FAIL got=PASS REGRESSION`, and a fourth
(`a-non-string-headcommit-is-caught`) regresses the same way, confirming the
check is what makes each one red.

What this does NOT do, stated because a control that oversells itself is
worse than none: a receipt that records no `headCommit` at all is not judged
by this check either way, and still PASSes exactly as it did before this
field existed. This gate cannot tell "a receipt written before this field
existed" apart from "an operator who chose not to record one", and every
worked receipt this repository ships today is the first kind: the shipped
example receipts under `docs/for-engineers/examples/`, the worked receipts
`docs/guides/05-a-worked-engagement.md` writes and `evals/replay_guide05.py`
replays verbatim, and every eval case in `evals/run_evals.py` written before
this change all carry no `headCommit` field, and none of those quoted PASS
lines are files this change is scoped to rewrite. Closing that second gap
(making an unbound receipt something other than a silent PASS once a
directory has real git history to bind against) needs those shipped receipts
and worked-engagement blocks updated together with the code in one pass, so
the doc-quote guards that replay them do not go stale on landing; that pass
is future work, named here rather than left implicit. The mismatch case this
change closes is the one actually reproduced and asked for: a passing receipt
copied forward from a commit that is no longer HEAD.

A second, smaller side effect of the same change: adding new fixture-backed
eval cases moved `evals/run_evals.py`'s own case count, and a handful of
shipped docs outside this change's scope (`README.md`, `docs/SETUP.md`,
`docs/guides/01-quickstart.md`, `docs/guides/04-teams-and-evolution.md`)
quote that exact count the way `CHECKSUMS.sha256` quotes tracked file hashes.
Regenerating those counts is the same kind of whole-tree pass as regenerating
`CHECKSUMS.sha256`, and is left to it rather than forced through a file this
change was not scoped to touch.

Full text: `tools/sbe_gate.py` (`_current_head`, `_commit_problem`,
`gate_numbers`, `gate_migration`, `gate_ran`), `src/brothersbe/evidence.py`
(`_check_commit`), `evals/run_evals.py` (the commit-binding cases).

## check-update follows a linked worktree, not a broken one

`tools/sbe_telemetry.py::_resolve_git_dirs` follows a linked worktree's
`.git` file (`gitdir: <path>`) to the per-worktree directory git created for
it, then reads that directory's own `commondir` file to find the COMMON
directory where refs/heads and refs/remotes actually live (a linked
worktree does not duplicate them). This covers every worktree `git
worktree add` produces and every one `git worktree prune` has not yet torn
down: the case reproduced and fixed. It does not cover a worktree whose
per-worktree directory survives but whose `commondir` file is itself
missing, unreadable, or points at a directory that no longer exists, the
shape of a hand-edited or partially corrupted `.git/worktrees/<name>`
rather than anything an ordinary `git worktree` command leaves behind. In
that narrower case the helper falls back to treating the per-worktree
directory as the refs source, refs/heads is normally empty there, the
branch ref fails to resolve, and `cmd_check_update` exits at its existing
`if not local: return` exactly as before this change, silently. That is a
narrower silence than the one this change closes (a per-worktree directory
that is itself intact but missing its link to the common dir, not any
linked worktree git actually creates), and is named here rather than
guarded against speculatively for a shape not reproduced. Full text:
`tools/sbe_telemetry.py` (`_resolve_git_dirs`, `cmd_check_update`),
`tools/test_sbe.py` (`TestCheckUpdateFindsAWorktreeGitdir`).

## The authority-file guard cannot always tell a worker from a human (LT-402)

`tools/sbe_authority_hook.py` refuses an UNDECLARED write to an authority-bearing
file (CLAUDE.md, `.claude/**`, `.mcp.json`, `.claude-plugin/**`, `hooks/**`,
`agents/*.md`, `skills/*/SKILL.md`, `CODEOWNERS`, `.github/workflows/**`) only
when it can also tell it is running inside a dispatched worker's session, not a
human editing interactively. Refusing every undeclared authority-file edit
unconditionally would block the ordinary case this project runs in every day: a
human, in an interactive session, with no task registry in play at all, editing
CLAUDE.md by hand.

`_worker_context` answers the question with exactly two signals, either
sufficient on its own: at least one task is OPEN in `.sbe/tasks.json` right now
(regardless of whether it covers the file in question), or the working
directory's own `.git` entry is a FILE rather than a directory, the shape `git
worktree add` leaves behind for a linked worktree and the shape this project's
own dispatch model uses to isolate a worker (`sbe task open --worktree`).

Both are heuristics, not proof, and here is exactly where they fail. A worker
that shares the primary tree (no `--worktree` was used to open its task) and
whose own task has already been closed, or that never ran `sbe task open` at
all, is indistinguishable from an interactive human by either signal. In that
shape, an undeclared authority-file edit is ALLOWED, not refused: the hook
prints a note naming the file and saying no worker context was detected
(`tools/test_sbe_authority_hook.py::TestWorkerContextSignal::test_no_registry_and_no_linked_worktree_allows_the_undeclared_edit`
is the fixture that proves the allow, on purpose, in that shape), but nothing
stops the edit. Closing this gap needs a signal Claude Code's PreToolUse
payload does not currently carry: nothing in `tool_name`, `tool_input`,
`session_id`, `cwd`, or `project_dir` distinguishes a dispatched subagent
invocation from the operator's own primary session. Until such a signal
exists, this is a real, named remainder, not an oversight.

## The authority guard's case-fold confirmation covers named segments, not a powerset

`tools/sbe_authority_hook.py::confirmed_surface` closes the same
case-insensitive-filesystem hazard `tools/sbe_fence_hook.py::paths_overlap`
closes for fence scopes (see "The case-fold confirmation trusts one probe of
the project's own volume", above), reusing its confirmation function
(`_same_entry_case_insensitive`) rather than re-deriving it. But the CANDIDATE
spelling it confirms against is built from a fixed, named table of segments
(`_known_segments`: the literal tuples `tools/sbe_instruction_surface.py`'s
`_matched_surface` is itself built from, plus `CLAUDE.md`, `agents`, `skills`,
`SKILL.md`, `.github`, `workflows`), not an exhaustive case powerset of an
arbitrary path. A case-folded hazard in a path segment none of the nine
detected authority families ever names is out of scope by the same logic
`_matched_surface` itself uses to decide what counts as authority-bearing at
all, and is not a gap this file closes or claims to.

## Per-task worktree evidence under team status and converge (LT-501; both engine gaps fixed in rc.11, one true boundary remains)

The LT-501 golden scenario (`tools/test_sbe_golden_scenario.py`) runs the
whole team lifecycle for real: `sbe work start` opens a dedicated branch and
linked worktree per task, never merges, rebases onto, or pushes to the
repository root's own branch (the no-merge law, checked mechanically by the
same suite). Driving that real chain surfaced two engine gaps in rc.10,
recorded here at the time with red fixtures built to flip. Both were fixed
in rc.11 and the fixtures flipped exactly as designed.

First, fixed in rc.11: `sbe status --team`'s evidence scan
(`status._scan_evidence`) used to compare every receipt's `headCommit`
against the repository ROOT's own checked-out HEAD, so a finished task's
own receipt, generated on the task's own never-merged branch, always read
as a severity-1 broken claim. The scan now resolves a receipt CLAIMED BY A
TASK RECORD, meaning the record's `evidenceId` equals the receipt's
`runId`, against that record's declared worktree when the directory still
exists, and the resolution is disclosed on the entry itself (`verifiedIn`,
`task`, and the finding sentence naming the declared worktree). What
remains true, and is a boundary rather than a defect: a claimed receipt
whose worktree has been removed, an unclaimed receipt, and an unreadable
registry all still verify against root exactly as before, so linkage that
cannot be read never upgrades a verdict. Proven by
`tools/test_sbe_golden_scenario.py::TestTeamModeCIPostcondition`, which
asserts zero severity-1 findings after real task work while the legitimate
NO-DATA blockers (missing approval, missing convergence) stay named
exactly, and separately asserts the plain status JSON names the worktree
resolution, so a scan that silently dropped the receipt cannot pass either
assertion. Calibrated by suppressing the resolution in a scratch copy: the
suite goes red.

Second, fixed in rc.11: `sbe converge`'s VERIFICATION dimension
(`src/brothersbe/converge.py`, the block computing `missing_cover`) used to
compare a bare path string from a plan task's `owns` against
`receipt["coveredFiles"]`, which `sbe evidence run` always writes as a list
of `{path, sha256, note}` objects, so the membership test could never match
and a writer task's OWN receipt was misreported as not covering its own
owned path. The block now extracts `path` from each entry (tolerating a
legacy bare-string entry) before the membership test. Proven by
`tools/test_sbe_golden_scenario.py::TestFullChain`, which asserts the
sealed-receipt PASS finding for T02's own receipt and the absence of the
old does-not-cover text against it. Calibrated by reverting the extraction
in a scratch copy: the suite goes red.

What remains a real limit, unchanged and inherent: `sbe converge` assesses
one explicit `--head`, so receipts for the OTHER tasks, bound to their own
never-merged branch heads, still read as wrong-head stale evidence for the
assessed head until integration happens outside `sbe` (the no-merge law
says `sbe` itself never performs it). The golden scenario asserts
VERIFICATION still FAILs for exactly that reason and FINAL stays FAIL by
the documented rule.


## Plugin interoperability rests on platform behavior this repository cannot drive in a test (LT-502)

`docs/INTEROPERABILITY.md` names seven interoperability guarantees and labels
each one PROVEN BY TEST or DOCUMENTED CONTRACT, never implied. Four of the
seven carry a documented-contract half that no fixture here can turn into a
mechanical check, because the missing half is Claude Code's own runtime, not
this repository's code: whether the harness actually prefixes every skill
with `brothersbe:` at resolution time, whether it correctly merges two
installed plugins' `SessionStart` and `PreToolUse` hooks rather than only
running one, and whether a person who lacks a companion plugin actually
reaches `docs/CLI.md` are all platform or human behavior this repository has
no way to observe from inside a unit test. The one place a human action
substitutes for code, the manual `~/.claude/settings.json` paste
`docs/SETUP.md` step 3 and `docs/HOOKS.md` document for a standalone
(non-plugin) install, is proven only on the code side (nothing in the
install path names the file at all); that a person follows the documented
paste correctly is not something a test can watch.

`sbe doctor` (`src/brothersbe/cli.py::_doctor_checks`) gained no
interoperability row: it is a fixed, hand-written list of tuples, not a
discoverable check registry, and editing it sits outside LT-502's file
boundary (documentation and tests only) and would reopen review on the
doctor command for a change this task was not scoped to make. The contract
is documented instead, in `docs/INTEROPERABILITY.md`'s own "Doctor: branch
taken" section.

Full text: `docs/INTEROPERABILITY.md`, `tools/test_sbe_interop.py`.
