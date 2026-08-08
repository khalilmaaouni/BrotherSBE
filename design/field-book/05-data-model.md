# 05. Data model

The subject is the booklet itself: what a chapter is, what a generated section
is bound to, and what a stamp claims. Every entity below is a file or a record
in this repository, so the system of record is always a path.

## Conceptual: entities and meanings

- **Book**: the whole artifact, one per repository; system of record:
  `docs/fieldbook/`.
- **Part**: a numbered division of the Book (the two-page brief, why this
  exists, what it is made of, how it differs, end to end, personas and
  scenarios, adopting on a team, the honest limits); system of record: the
  ordering declared in `docs/fieldbook/parts.json`.
- **Chapter**: one markdown file of author prose, belonging to exactly one
  Part; system of record: `docs/fieldbook/chapters/*.md`.
- **GeneratedSection**: a block of rendered content inside a Chapter, delimited
  by BEGIN and END markers, produced by one renderer; system of record: the
  markers inside the Chapter file, with the renderer named in the BEGIN marker.
- **SourceBinding**: the record that a GeneratedSection was rendered from a
  named file at a named SHA-256; system of record:
  `docs/fieldbook/bindings.json`.
- **BoundSource**: a file in this repository that a renderer parses; system of
  record: the file itself (`src/brothersbe/cli.py`, `agents/*.md`,
  `src/brothersbe/checks.py`, `tools/sbe_checks.py`, `DIGEST.md`,
  `docs/KNOWN-LIMITS.md`, `VERSION`).
- **Stamp**: a Chapter's `verified-against` version, claiming when a human last
  read that prose; system of record: the Chapter's front matter.
- **DriftVerdict**: the outcome of one `sbe book --check` run over one
  GeneratedSection or one Chapter, one of PASS, FAIL or NO-DATA; system of
  record: the check's stdout, and its exit code under `--strict`.

## Relationships

- Book to Part: one-to-many, mandatory. A Book has at least one Part; a Part
  belongs to exactly one Book.
- Part to Chapter: one-to-many, mandatory. A Part has at least one Chapter; a
  Chapter belongs to exactly one Part.
- Chapter to GeneratedSection: one-to-many, optional. A Chapter may hold zero
  GeneratedSections and is then pure prose; a GeneratedSection belongs to
  exactly one Chapter.
- GeneratedSection to SourceBinding: one-to-many, mandatory. A GeneratedSection
  records at least one SourceBinding, because a section bound to nothing is the
  hand-typed list this design exists to remove.
- SourceBinding to BoundSource: many-to-one, mandatory. Many sections may bind
  the same file; every binding names exactly one file.
- Chapter to Stamp: one-to-one, mandatory. Every Chapter carries exactly one
  Stamp.
- GeneratedSection to DriftVerdict: one-to-one per run. Chapter to
  DriftVerdict: one-to-one per run.

## Attribute roles

| Attribute | Entity | Role |
|---|---|---|
| slug | Chapter | identifier |
| part_number | Part | identifier |
| title | Chapter | descriptor |
| verified_against | Stamp | status |
| renderer | GeneratedSection | identifier |
| path | BoundSource | identifier |
| sha256 | SourceBinding | descriptor |
| recorded_at | SourceBinding | temporal |
| item_count | GeneratedSection | measure |
| verdict | DriftVerdict | status |
| reason | DriftVerdict | descriptor |

## Historization

Change over time is preserved by git and nowhere else, deliberately. A
SourceBinding is overwritten on every regenerate rather than appended, because
the question the check asks is "does the current book match the current
sources", and a history of past hashes answers a question nobody has. The
history that matters, which section changed and when, is the diff of
`bindings.json`, which is committed.

Stamps are not historized either: a Chapter carries the last version a human
verified it against, not every version. The audit trail for who moved a stamp
is the commit that moved it.

## Source systems and failover

| Entity | Source | Refresh contract | If the source is unavailable |
|---|---|---|---|
| Chapter | `docs/fieldbook/chapters/*.md` | On author edit | Generation FAILs naming the missing file; it never renders a Book with a silently absent Chapter |
| BoundSource (commands) | `src/brothersbe/cli.py` | On every regenerate | FAIL carrying the parse exception |
| BoundSource (roles) | `agents/*.md` | On every regenerate | Zero files found renders NO-DATA naming the empty directory, never an empty roles table |
| BoundSource (checks) | `src/brothersbe/checks.py`, `tools/sbe_checks.py` | On every regenerate | FAIL carrying the parse exception |
| BoundSource (laws) | `DIGEST.md` | On every regenerate | FAIL if absent; NO-DATA if present and no law line parses |
| BoundSource (limits) | `docs/KNOWN-LIMITS.md` | On every regenerate | NO-DATA naming the file if it holds no limit heading |
| SourceBinding | `docs/fieldbook/bindings.json` | Written by every regenerate | A missing or unparseable bindings file makes the check NO-DATA naming why, never PASS |

## The three lenses

1. **Engineer**: regeneration is idempotent and offline, so it can run in CI on
   every platform this project supports without a network or a lockfile.
2. **Analyst**: every enumerated row in the Book answers "where did this come
   from" with a path and a hash, so a disputed claim is settled by reading a
   file rather than by asking the maintainer.
3. **Scientist**: no leakage concern applies, and the only derived quantity is
   a content hash, which is reproducible by anyone with the repository.

## Physical

`bindings.json` is a single JSON object keyed by `"<chapter-slug>#<renderer>"`,
each value holding `sources` (a list of `{path, sha256}`), `recorded_at` and
`item_count`. It is written with sorted keys and a trailing newline so its diff
is readable and its bytes are deterministic.

Chapters are UTF-8 markdown with a YAML front matter block carrying `slug`,
`title`, `part` and `verified-against`. Generated blocks are delimited by
`<!-- BEGIN GENERATED FIELDBOOK <renderer> -->` and
`<!-- END GENERATED FIELDBOOK <renderer> -->`, matching the marker convention
`program/STATUS.md` already uses.

The migration path is additive: new files only, no existing file changes shape,
and the reverse is `git rm -r docs/fieldbook src/brothersbe/book.py` plus
removing the `book` row from the CLI command table, which is why the intake
answered that this is reversible in under an hour.
