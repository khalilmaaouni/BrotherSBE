# 03. Architecture decision record

## Context

The feature list, the roles, the checks with their severities, the laws with
their enforcement classes and the limits are currently written out by hand in
four separate documentation surfaces, and the copies are free to disagree.
BrotherSBE's own argument is that a claim earns trust in proportion to how
mechanically it can be checked, so a hand-typed feature list inside a document
arguing for derived evidence is the product contradicting itself in public.
Something has to own those enumerations, and the drift has to become visible
to a check rather than to a careful reader.

## Criteria

- **Derivability**: can the enumerated sections be produced from the files that
  already define them, without a second declaration to maintain? Observed on
  this estate: yes for commands (a literal table in `src/brothersbe/cli.py`),
  roles (`agents/*.md` frontmatter), checks and severities (the check registry),
  laws and enforcement classes (`DIGEST.md`), limits (`docs/KNOWN-LIMITS.md`
  headings).
- **Detection latency for drift**: today, unbounded. Required: one CI run.
- **New moving parts**: this repository ships no site generator and no
  JavaScript build. Adding one is a permanent maintenance cost carried by one
  maintainer.
- **Blast radius of a wrong parse**: high. A generated feature list is read as
  authoritative precisely because it claims to be derived.
- **Author freedom**: the prose has to stay hand-written. A book whose prose is
  generated reads like a specification, and the reader we are trying to convince
  stops on page one.

## Options considered

### Rejected: a documentation site generator (Docusaurus, Starlight, MkDocs)

It solves navigation, search and theming, which are real. It fails
derivability and new moving parts together: the enumerated sections would
still be typed by hand into MDX, so the drift this decision exists to remove
survives intact, and the repository acquires a Node or Python toolchain, a
lockfile and a build step that must stay green on Windows, where this project
already spends effort. It buys presentation and pays for it with the one
property that motivated the work.

### Rejected: a single hand-written document with a per-chapter review stamp

The cheapest option, and it is what the existing four surfaces already are. It
scores well on new moving parts and author freedom and fails derivability
outright: nothing computes that the commands table matches the CLI, so
detection latency stays at "whenever a reader happens to notice". This is the
status quo with a date on it, and the status quo is the problem statement.

## Decision

One deterministic Python module, `src/brothersbe/book.py`, exposed as
`sbe book`, following the pattern `src/brothersbe/program.py` and
`src/brothersbe/mapgen.py` already establish in this repository: parse
canonical state, render between explicit generated markers, emit one
self-contained offline HTML, no network and no third-party dependency.

Prose chapters stay hand-written markdown under `docs/fieldbook/chapters/`,
each carrying a `verified-against:` version stamp. Generated sections are
written between markers inside those chapters, and the SHA-256 of every source
read is recorded in `docs/fieldbook/bindings.json`. `sbe book --check`
recomputes those hashes and fails on a mismatch under `--strict`.

## Consequences

The enumerations gain exactly one home and a mechanical drift signal, at the
cost of a parser per bound source, and a parser is a thing that can be wrong.
That risk is met the way this repository meets it elsewhere: an unparseable
source is a FAIL carrying the exception, a source parsing to zero items is
NO-DATA naming why, and neither is ever an empty table the reader would read as
"there are none".

The book gains no search, no client-side navigation beyond anchors, and no
incremental build. A full regenerate is the only mode, which is acceptable
because it is fast and because determinism is worth more here than speed.

Prose staleness is reported, never enforced. A `verified-against` stamp older
than `VERSION` yields NO-DATA, so a release cannot be blocked by prose nobody
has reread, and equally cannot claim the prose was reread.

## What would flip this

If the booklet grows past roughly thirty chapters, or if readers start asking
for full-text search and cross-version diffs, the hand-rolled renderer stops
paying for itself and a site generator becomes the right call. The trigger to
revisit is a concrete reader request for search, not a page count on its own.

If a second consumer ever needs the parsed enumerations (a website, a
directory submission, an MCP resource), the parsers should be lifted out of
`book.py` into their own module before the second consumer is written, not
after.

## Falsification tier

Deterministic check. The parsers are covered by unit tests asserting that each
one recovers the same items an independent grep of the source finds, and the
drift check is covered by a test that mutates a bound source and asserts the
check FAILs naming that source. No mutation calibration and no fresh-context
refute exists for this decision yet, and stating otherwise would be the exact
overclaim the gates exist to prevent.

## Return to developer

The maintainer may decline the drift gate and keep the generator advisory, in
which case the book still cannot be wrong at generation time but can go stale
between regenerations. Nothing here defaults to enforcement without that being
chosen out loud, and the choice is recorded in
`.github/workflows/brothersbe-gates.yml` where a reviewer sees it in the diff.
