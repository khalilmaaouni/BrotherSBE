# Known limits

Every law already states what its machinery does not do, but those statements
live inside the digest and the law text, where the honest half of the product
is the hardest part to read. This page collects them: one heading per limit,
each naming the law it qualifies and the file where the full text lives.
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
`SKILL.md` L9 and `LAWS-REFERENCE.md` (the hard gates).

## The forcing conditions are read by a person (L6)

Stop-on-ambiguity, contradiction, gate collision, and disproven assumption are
[human]: the checkpoint shape is prose the session follows or does not. Full
text: `SKILL.md` L6.

## The fence checks read registries, not the world (L13)

Fence hygiene and budget-vs-tier run only over registries named in
`BROTHERSBE_REGISTRIES`, and only over fence lines containing the word
"agent". Writing the fence, comparing scopes, and resuming after a kill are
human. Full text: `SKILL.md` L13, `LAWS-REFERENCE.md`.

## Blast radius revokes nothing (L14)

"No apply rights on production state" is a working rule plus whatever access
control your estate has. Nothing here can revoke a credential your shell
already holds. Full text: `SKILL.md` L14.

## The CI workflow guards nothing until you copy it (L16)

`--strict` blocks only in a repository that wired it. No CODEOWNERS and no
branch protection ships, so nothing makes editing the workflow require a
review; that is your repository's setting. Full text: `SKILL.md` L16.

## Most of the close is human (L17)

Only the vault session log has a check, and only where `BROTHERSBE_VAULT`
points at a vault, which the shipped CI does not set: on a stock runner every
ledger check is NO-DATA at exit 0. Open items, the failures index, the
scorecard and the self-score cap are human review. Full text: `SKILL.md` L17.

## Telemetry observes, it never decides

The SessionEnd hook writes the ledger and decides nothing; no CI step reads
it. The checks fed by it are named on their own digest lines. Full text:
`DIGEST.md`, `LAWS-REFERENCE.md` (Telemetry).

## The UNVERIFIED label is the agent's to write

No tool applies it. A session that fails to label unverified output is not
caught by a check. Full text: `SKILL.md` L7 and L16, `DIGEST.md`.

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
