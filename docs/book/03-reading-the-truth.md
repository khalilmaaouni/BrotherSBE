# Reading the truth

## What sbe status is, and what it deliberately is not

**sbe status** answers one question: where does a change stand, right now.
It does not compute a new verdict of its own. It reads state that other
commands already recorded, evidence receipts, the task registry, an intake
file, a disposition, the diff itself, and reports what it finds, blocker
first. If the underlying checks were never run, status says so. It will not
run them itself, because a summary tool that quietly becomes a second gate
runner is a summary tool nobody can trust to only summarize.

That design choice is why a business analyst or project manager can read
this command's output and trust it as far as it goes: it is not opinion,
and it is not a fresh judgment made on the spot. It is a plain readback of
what has already been recorded, with the honest gaps left visible instead of
smoothed over.

## The six things it always prints

Every run prints the same five sections, in the same order, plus one closing
line:

1. **BROKEN CLAIMS**: a piece of recorded evidence that does not hold up,
   a receipt that cannot be read, or a check that failed. Blocks.
2. **MERGE BLOCKERS**: whatever this repository's own rules name as blocking
   right now. Blocks.
3. **ACTIVE CONFLICTS**: two open pieces of work claiming the same scope at
   the same time. Blocks.
4. **MISSING EVIDENCE**: a check this change's tier requires, that nobody
   has run yet. Blocks.
5. **COMPLETED EVIDENCE**: what was checked, and came back clean. This
   section never blocks. It is read only, the record of what already
   passed.
6. **NEXT ACTION**: one line, computed from the first section above that
   carries an item, or a line saying nothing blocking was found.

Sections one through four decide the exit code. Section five never does,
by design: a long list of completed evidence says something was checked, it
does not excuse anything that was not.

Inside each section, watch for one distinction. A line that opens with
"NO-DATA" means nothing was there to inspect at all, no receipts, no
registry, nothing recorded. A line that opens with "clean" means something
was inspected, and it came back with nothing to report. Those are not the
same claim, and the scope text after either word says exactly what was, or
was not, looked at.

## A real run, on this repository

The block below is not typed from memory. It is the literal output of the
command shown, re-executed by the book's own build check every time this
page is verified. It runs against a small repository the block itself
builds, carrying copies of this repository's three real design dossiers.
Why not against the live repository directly? Because a printed page cannot
freeze a living branch: the moment real work is in flight, the diff-derived
sections change, and this page would be lying in one direction or the
other. The build check proved that twice before this sentence was written.
The demo repository holds the dossiers still so the reading below stays
true; your own run of `bin/sbe status .` on a moving repository will differ
in exactly the ways this chapter teaches you to read.

```bash
rm -rf /tmp/sbe-book-ch03
git init -q /tmp/sbe-book-ch03
git -C /tmp/sbe-book-ch03 -c user.name=reader -c user.email=reader@example.com commit -q --allow-empty -m "a starting point"
cp -r design /tmp/sbe-book-ch03/design
bin/sbe status /tmp/sbe-book-ch03
```

```
sbe status: /tmp/sbe-book-ch03

BROKEN CLAIMS:
  NO-DATA. scope: no evidence store found at /tmp/sbe-book-ch03/.sbe/evidence; disposition absent

MERGE BLOCKERS:
  clean. scope: dossier field-book intake /tmp/sbe-book-ch03/design/field-book/00-intake.json (tier T2); dossier final-release-program intake /tmp/sbe-book-ch03/design/final-release-program/00-intake.json (tier T3); dossier lifecycle-blockers intake /tmp/sbe-book-ch03/design/lifecycle-blockers/00-intake.json (tier T2); dossier release-blockers intake /tmp/sbe-book-ch03/design/release-blockers/00-intake.json (tier T3); dossier team-operating-model intake /tmp/sbe-book-ch03/design/team-operating-model/00-intake.json (tier T3); no task registry found at /tmp/sbe-book-ch03/.sbe/tasks.json; git diff f77787c72b60..HEAD over 0 changed file(s)

ACTIVE CONFLICTS:
  NO-DATA. scope: no task registry found at /tmp/sbe-book-ch03/.sbe/tasks.json

MISSING EVIDENCE:
  - dossier field-book: no evidence receipt declares a design completeness check run, and declared tier T2 owes one
  - dossier field-book: no evidence receipt declares a hard gate run, and declared tier T2 owes one
  - dossier field-book: no evidence receipt declares a scored surface run, and declared tier T2 owes one
  - dossier final-release-program: no evidence receipt declares a design completeness check run, and declared tier T3 owes one
  - dossier final-release-program: no evidence receipt declares a hard gate run, and declared tier T3 owes one
  - dossier final-release-program: no evidence receipt declares a scored surface run, and declared tier T3 owes one
  - dossier lifecycle-blockers: no evidence receipt declares a design completeness check run, and declared tier T2 owes one
  - dossier lifecycle-blockers: no evidence receipt declares a hard gate run, and declared tier T2 owes one
  - dossier lifecycle-blockers: no evidence receipt declares a scored surface run, and declared tier T2 owes one
  - dossier release-blockers: no evidence receipt declares a design completeness check run, and declared tier T3 owes one
  - dossier release-blockers: no evidence receipt declares a hard gate run, and declared tier T3 owes one
  - dossier release-blockers: no evidence receipt declares a scored surface run, and declared tier T3 owes one
  - dossier team-operating-model: no evidence receipt declares a design completeness check run, and declared tier T3 owes one
  - dossier team-operating-model: no evidence receipt declares a hard gate run, and declared tier T3 owes one
  - dossier team-operating-model: no evidence receipt declares a scored surface run, and declared tier T3 owes one

COMPLETED EVIDENCE:
  NO-DATA. scope: no evidence store found at /tmp/sbe-book-ch03/.sbe/evidence

NEXT ACTION: run `bin/sbe design --strict <dossier>` through `sbe evidence run --kind design` to record it (MISSING EVIDENCE) scope: intake absent; disposition absent; evidence store absent; task registry absent; dossiers discovered: field-book, final-release-program, lifecycle-blockers, release-blockers, team-operating-model; diff git diff f77787c72b60..HEAD over 0 changed file(s)

sbe status: exit 1. at least one of BROKEN CLAIMS, MERGE BLOCKERS, ACTIVE CONFLICTS or MISSING EVIDENCE carries an item above.
```

One line in that output is live by design: `git diff <sha>..HEAD over N
changed file(s)` names the commit your repository is actually at, so the sha
and the count on your machine will differ from the ones printed here, and
they move again after every commit. The book's own replay check knows this:
it treats exactly that substring as declared volatile and compares every
other byte of the block literally, because freezing a live reading onto a
printed page would be the kind of quiet lie this product exists to catch.

## Reading this specific report

Three different verdict shapes sit in one report, and telling them apart is
the whole lesson. BROKEN CLAIMS, ACTIVE CONFLICTS, and COMPLETED EVIDENCE
read NO-DATA: nothing was recorded for them to examine, no evidence store,
no task registry. MERGE BLOCKERS reads "clean": it HAD something to inspect,
the actual git diff and the three declared intakes, and found nothing the
rules treat as blocking. And MISSING EVIDENCE carries nine concrete items:
three dossiers each declared a tier, each tier owes a design check, a hard
gate run, and a scored surface run, and no receipt anywhere says any of the
nine happened. Declared obligations with no evidence are findings, not
silence.

So this report exits 1, and the closing line says exactly why. Notice what
the exit code did NOT come from: not from anything broken, not from any
conflict, only from promises the intakes made that nothing has kept yet. A
reader who skims to "clean" under MERGE BLOCKERS and calls this change
ready has made the exact mistake this whole book exists to stop: a clean
section is a claim about one seam, never about the work.

## When to escalate

The rule is mechanical, not a judgment call: escalate whenever BROKEN
CLAIMS, MERGE BLOCKERS, ACTIVE CONFLICTS, or MISSING EVIDENCE carries even
one item. Each of those is an exit 1 by construction, and each item names a
concrete file, claim, or scope conflict, not a vague concern. That is
precisely what makes it something to hand to a person rather than resolve by
re-reading the report harder: the tool has already done the reading, and
what is left is a decision only a human can make.

COMPLETED EVIDENCE never needs escalation on its own. It is the section that
tells you what is already settled.

One case deserves a second look even when nothing blocks: a report that is
NO-DATA almost everywhere, the way the demo repository's is above outside
its declared intakes. That is not a blocker by the tool's own rule, but it
is worth asking, out loud, whether the repository is expected to have an
evidence store and a task registry by this point in its work, and if so,
why it does not yet.

## Diagram: how the sections resolve into one action

```mermaid
flowchart TD
  Status["sbe status ."] --> BC[BROKEN CLAIMS]
  Status --> MB[MERGE BLOCKERS]
  Status --> AC[ACTIVE CONFLICTS]
  Status --> ME[MISSING EVIDENCE]
  Status --> CE[COMPLETED EVIDENCE]
  BC -->|one item here blocks| NA[NEXT ACTION]
  MB -->|one item here blocks| NA
  AC -->|one item here blocks| NA
  ME -->|one item here blocks| NA
  CE -->|informational only, never blocks| NA
  NA --> Exit["exit code: 1 if any of the first four carried an item, else 0"]
```
