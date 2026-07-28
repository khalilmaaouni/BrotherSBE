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
names that escape, and the last column below exercises it rather than
asserting it. Full text: `tools/sbe_gate.py` (gate_approval),
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

script        pairs  unproven  percent  still unproven with distinct emails
Amharic          45         0        0                                   0
Arabic           45         0        0                                   0
Armenian         45         0        0                                   0
Georgian         45         0        0                                   0
Greek            45         9       20                                   0
Hebrew           45         0        0                                   0
Hindi            45         0        0                                   0
Japanese         45         0        0                                   0
Korean           45         0        0                                   0
Russian          45        13       29                                   0
Thai             45         0        0                                   0
Vietnamese       45         0        0                                   0

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
  records the exact argv so a reader can see that; deciding whether that argv is
  the work the gate wanted is a person's job, and no field here does it.
- `argv` is recorded verbatim, on purpose, because a receipt whose command was
  paraphrased proves nothing about what happened. So a credential passed ON the
  command line IS persisted in the receipt, and the digests-only policy that
  covers stdout and stderr does not cover it. Pass secrets through the
  environment or a file, never as an argument. A fixture pins this so it stays a
  decision rather than a surprise.
- The digests prove the same bytes came back. They carry none of them, so a
  receipt cannot be used to audit what a command printed, only to detect that it
  printed something different.
- Coverage is what the caller named, or the diff between base and head. A change
  to a file the receipt does not cover is invisible to `verify`, and a receipt
  covering no file at all is NO-DATA rather than a pass, naming why.
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
Full text: `tools/sbe_telemetry.py` (the capture policy block),
`tools/sbe_autosave.sh` (the content scan block), `SECURITY.md`,
`docs/THREAT_MODEL.md`.

## A green bypass suite covers the scenarios it covers

An external review listed 35 ways a person or an agent could get past these
controls. `docs/BYPASS-COVERAGE.md` is the table: one row per scenario, each row
COVERED (with the fixture named), UNREACHABLE HERE (with the missing thing
named: a GitHub token, branch protection, a warehouse, a real second estate) or
UNCOVERED (with what covering it would take). As this file is written, 16 rows
are COVERED, 6 are UNREACHABLE HERE and 13 are UNCOVERED.

So: a green `python3 tools/test_sbe_bypass.py` means the COVERED scenarios were
tested. It is not a statement about the other 19, and it is not a claim that the
list of 35 is the whole space of bypasses. Some fixtures in that file pin a
bypass that WORKS, and carry `_is_a_limit` in their names for exactly that
reason; a limit fixture is a tripwire on this documentation, not coverage.

Two holes found while writing that table are recorded here rather than fixed,
because fixing them changes code that was outside the wave that found them.
`sbe evidence verify` opens the receipt path without the access check the hard
gates use, so a FIFO where a receipt is expected hangs the command forever and
prints no verdict in either mode. And the evidence wrapper runs the operator's
command with no timeout, so a command that hangs hangs the wrapper. Both are row
35 of the table.

Full text: `docs/BYPASS-COVERAGE.md`, `tools/test_sbe_bypass.py`.
