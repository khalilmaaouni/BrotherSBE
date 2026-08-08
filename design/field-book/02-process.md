# 02. Process

## Actors

| Actor | Role in this process |
|---|---|
| Author | A human writing or revising a prose chapter under `docs/fieldbook/chapters/` |
| Generator | `src/brothersbe/book.py`, invoked as `sbe book`, reads sources and emits the artifact |
| Drift check | `sbe book --check`, the same module in verify mode, run in a session and in CI |
| CI | `.github/workflows/brothersbe-gates.yml`, which runs the drift check under `--strict` |
| Reader | A team engineer opening the published artifact, with or without a terminal |

## Steps

### 1. A source of truth changes

**Trigger:** any commit touching a bound source: `src/brothersbe/cli.py`
(the command table), `agents/*.md` (the roles), `src/brothersbe/checks.py`
and `tools/sbe_checks.py` (the check registry and severities), `DIGEST.md`
(the laws and their enforcement classes), `docs/KNOWN-LIMITS.md` (the limits),
`VERSION`.

**Exception path:** a commit touching none of them leaves the book untouched
and the drift check reports NO-DATA for the generated sections rather than
PASS, naming that no bound source was read.

### 2. The generator runs

**Trigger:** `sbe book`, run by the author or at loop close.

The generator parses each bound source into its section model, renders the
generated sections between explicit markers, records for each section the
SHA-256 of the source bytes it read, and writes both the chapter markdown and
the single-file HTML.

**Exception path:** a source that cannot be parsed is a FAIL carrying the
exception, never a silently empty section. A source that parses to zero items
renders as NO-DATA with the reason named, never as an empty table read as
"there are none".

### 3. The drift check runs

**Trigger:** every session start (advisory), and every CI run (`--strict`).

For each generated section it recomputes the source hash and compares it to
the recorded one. For each prose chapter it compares the `verified-against`
stamp to `VERSION`.

**Exception path:** a mismatch on a generated section is a FAIL naming the
section, the source file and the two hashes. A stale prose stamp is NO-DATA
naming the chapter and both versions, because nobody can compute whether prose
went wrong, only that a human has not looked since.

### 4. The author repairs

**Trigger:** a FAIL or a NO-DATA from step 3.

A generated-section FAIL is repaired by running `sbe book`. A stale prose
stamp is repaired by a human reading the chapter and moving its stamp, and the
check refuses a stamp moved in a commit that changed nothing else in the
chapter only insofar as the diff makes that visible to a reviewer; nothing
computes intent here, and this line is a discipline.

### 5. The artifact is published

**Trigger:** loop close.

The HTML in `docs/fieldbook/` is the committed source of truth. The published
artifact is a copy of it. Republishing is idempotent: identical input produces
byte-identical output, so a publish with no source change is a no-op.

## Handoffs and contracts

| From | To | Contract |
|---|---|---|
| Bound source | Generator | The generator declares, per section, the exact file and the parse it performs. A source whose shape changes fails loudly rather than yielding a plausible partial parse. |
| Generator | Chapter markdown | Generated content lives strictly between `<!-- BEGIN GENERATED ... -->` and `<!-- END GENERATED ... -->`, matching the marker convention `program/STATUS.md` already uses. Text outside the markers is the author's and is never rewritten. |
| Generator | Drift check | The recorded hash manifest is written to `docs/fieldbook/bindings.json`, and the check reads only that file plus the sources. Neither reads the HTML. |
| Drift check | CI | Exit nonzero under `--strict` on any FAIL. NO-DATA never decides the exit code, consistent with every other check in this repository. |
| HTML artifact | Reader | Self-contained: no external stylesheet, script, font or image request. It opens from a file path with no network. |
