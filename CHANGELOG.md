# Changelog

Newest first. Each entry names the behavior that changed and the check or test
that proves it, because a changelog line nothing can verify is a press release.
What this file does NOT record: internal working notes and measurements from
the estates this project was built on, which stay untracked by the publish
checklist's own rules.

## 1.0.0-rc.1 (unreleased)

- An onboarding set for engineers who have never seen this tool ships at
  `docs/for-engineers/`: eight pages (install and first run, one per role for
  backend, data, infrastructure and ETL, the limits page, and the adoption page)
  plus four complete worked dossiers under `docs/for-engineers/examples/`, one
  per role, each carrying the receipts its change would owe. Every block of tool
  output on every page was executed against this tree rather than carried
  forward, and the four dossiers pass all five design checks at their shipped
  path. The eight pages are in `SHIPPED_DOCS`, so the guards that recompute eval
  counts, meta-test counts and pasted lint lines read them too; the ETL page's
  three lint lines are recomputed by
  `no-shipped-doc-prints-a-silent-failure-lint-line-the-scorer-does-not-produce`
  from a fixture rather than exempted from it.

- Every citation that credited `SKILL.md` with a law the lazy-core split moved
  out of it now names the reference file that declares the law. Fifteen
  (file, law) pairs across six documents were dangling: `docs/KNOWN-LIMITS.md`,
  `docs/guides/01-quickstart.md`, `docs/guides/03-work-doctrines.md`,
  `docs/HOW-IT-WORKS.md`, `RUBRIC.md` and `MANIFEST-extraction.md`'s own worked
  example. Nine further pointers that describe `SKILL.md` as the whole law, and
  carry no law number for a check to read, were widened by hand. Proven by
  `every-law-citation-names-a-file-that-holds-that-law`, which globs
  `references/` for the law-text files and requires the file being credited to
  declare the law with its own heading, and which fails on a planted wrong
  pointer rather than on a remembered list of known-bad citations.

The first named version. Before this line the only name for an install was a
commit hash, which `tools/sbe_telemetry.py check-update` compares but no human
can read a promise into.

- Every verdict names the root it examined and the targets it read, and names
  or counts the directories inside that root that contributed nothing. Two
  defects were the same absence: pointed at an EMPTY directory with
  `SBE_DOSSIER_ROOT` set elsewhere, the design tool printed five PASS lines
  byte for byte identical to the run against a complete dossier, and a parent
  holding three change directories, the middle one carrying no receipt at all,
  printed one gate PASS over the pool while that directory alone printed
  NO-DATA. Closed once in `sbe_checks.scope_note`, which both walkers
  (`sbe_gate.find` and `sbe_design.find_dossiers`) call, so a gate added later
  inherits it; the design tool also prints a scope line and prints the dossier
  heading unconditionally, and a configured root that replaces a directory
  named on the command line is disclosed next to the root it replaced. The
  approval refusal names which APPROVAL file it quoted and how many it read.
  No verdict changed. Proven by
  `a-change-directory-with-no-receipt-is-named-in-the-verdict-that-pools-it`
  (executed on the numbers, migration and ran gates, not asserted from their
  source shape), `the-approval-verdict-names-which-approval-file-it-read` and
  `an-empty-directory-cannot-print-the-report-of-a-dossier-somewhere-else` in
  `evals/run_evals.py`.
- The scorer's report is split by what it opened. Checks that opened a file in
  the directory being examined print first, under a heading that says so;
  checks fed by a telemetry vault or fence registries outside that directory
  print under a second heading that says a verdict there is not a statement
  about the code here, and counts how many of those sources are not on the
  machine at all. Measured against a foreign repository, the single line in the
  whole first run that was true about the reader's own code printed eleventh,
  underneath ten NO-DATA lines about a vault path that does not exist for them
  and one PASS about the installed skill's own tree. Severity ordering alone
  did not fix that. No verdict changed, and nothing is aggregated, scored or
  graded. The quickstart's first ten minutes now runs against the reader's own
  repository first, with the real output including the pruning disclosure, and
  the eval bed is step two; the README states what a first run on an unmodified
  repository does and does not tell you; `docs/KNOWN-LIMITS.md` states that the
  intake's contract question sets the tier and that no checker reads a contract.
- The approval identity proof examines something before it certifies. A
  bracketed or parenthesized approver is read as the reader reads it rather
  than parsed to an empty set, a character whose glyph carries no ink
  separates or disappears but never welds two names into one, a comparison
  with no emails and no names on either side certifies nothing, a proven
  email difference is itself the proof, two names of one script compare by
  code point, and the approver who amends and signs is the approver (the
  signature's matched principal is the ground). Proven by the `c15i` approval
  cases in `evals/run_evals.py`; the measured refusal remainder per script is
  disclosed in `docs/KNOWN-LIMITS.md`.
- Ledger rewrites measure the live file before the rename, never after their
  own output: the bytes are read once under the writer lock, anything appended
  since is carried into the replacement verbatim, and a file that shrinks or
  keeps growing is never renamed over. Dedup rewrites through the same
  primitive with a per-run backup name, the lock sidecar can fail without
  dropping the row it exists to protect, short writes complete, and a
  line-delimited record stays one line. Proven by
  TestTelemetryWriterSerialization in `tools/test_sbe.py`.
- The autosave tick treats its counter as untrusted input and its lock as
  leakable: a counter that cannot be written is a named skip with a log line
  (never a silent off), non-numeric and empty counters are named resets, the
  lock is released by a trap on every exit path, and a stale lock is broken
  only when it predates the whole wait, with the presumption named in the log.
  Proven by TestAutosaveCoversTheWorktree in `tools/test_sbe.py`.
- An ADR's rejected count states only what the document establishes: the
  winner is identified per option rather than per document, a Decision
  sentence that names one listed option in ordinary English identifies it
  without quotation marks, a chosen marker that resolves to no listed option
  establishes nothing about the others, and "Flip condition" (this project's
  own name for the section in four shipped pages) is an accepted heading.
  Proven by `an-unquoted-decision-sentence-naming-one-listed-option-is-the-winner`,
  `a-chosen-marker-resolving-to-no-listed-option-establishes-nothing` and
  `the-projects-own-name-for-the-flip-section-is-accepted`.
- The doc-honesty guard classifies a sentence instead of remembering a
  phrasing: the scanned set is every markdown page the manifest ships (42
  pages, where a curated tuple of 18 was read before, so SECURITY.md,
  CHANGELOG.md and the shipped templates were never opened), and a
  claim that the receipt lookup is wider than the directory the caller named
  is recognized by its meaning, with a denial of that same mechanism read as
  the denial it is. A run that derives no page reports that, rather than
  reporting the pages consistent. Proven by
  `a-phrasing-of-the-removed-re-root-nobody-has-written-yet-is-caught`.
- Autosave recovery checks the snapshot out into a NEW detached worktree and
  never writes into the live working tree; the in-place restore path is gone,
  not warned about. Proven by TestAutosaveRecover in `tools/test_sbe.py`.
- The injected digest fits the cap its own SessionStart hook comment names,
  with the long qualifications moved to `LAWS-REFERENCE.md`. Proven by
  TestDigestCap in `tools/test_sbe.py`, which reads the cap out of the hook
  comment rather than hardcoding a second number.
- Every check declares its severity (gate or soft) at write time, prints it on
  every verdict line, and the exit-code mapping is explicit: `--strict` blocks
  on gate FAILs, `--strict-soft` opts graded FAILs into blocking. Proven by
  TestStrictMode in `tools/test_sbe.py` and the severity evals in
  `evals/run_evals.py`.
- `INVARIANTS.md` states the numbered promises with their asserting tests and
  the defect-reinjection record. Proven by the eval cases it names, verified
  present on the date it states.
- Release discipline ships: `VERSION`, this changelog, `CHECKSUMS.sha256` with
  `scripts/checksums.sh` and `scripts/verify-install.sh` (both directions,
  planted extra files fail), and the cut runbook in `docs/RELEASE.md`. Proven
  by the verify-install eval in `evals/run_evals.py`.
- Evidence rendering neutralizes the whole control-character class (categories
  Cc and Cf, plus stray surrogates), not only line breaks, so a receipt field
  cannot forge verdict lines by moving the terminal cursor. Proven by
  `a-receipt-field-cannot-move-the-cursor-in-the-rendered-report` in
  `evals/run_evals.py` and TestOneLineNeutralizesTheControlClass in
  `tools/test_sbe.py`.
- Placeholder detection folds SHAPES (bracketing, a trailing owner, dotted
  initialisms, combining marks and confusables) to a fixpoint, so `[TBD]`,
  `<TODO>`, `TODO(dana)` and `t.b.d.` record no answer, and a container where a
  snapshot id belongs pins nothing. Proven by `a-dressed-up-placeholder-...`,
  `a-bracketed-placeholder-is-not-a-pin` and `a-container-snapshot-id-pins-nothing`.
- The approval gate certifies the NEGATIVE "the approver is not the author"
  only when the difference is proven: proven means no one-for-one look-alike
  substitution this host can read maps one identity onto the other (they
  differ in structure, at a plain-ASCII position, or across a wide or
  right-to-left letterform). A word mixing script families is refused as a
  disguise shape; an identity that is letter-for-letter
  substitution-compatible with the author (a Lisu, Cherokee or Coptic
  spelling of the author's name) is NO-DATA naming the ambiguity, never a
  certificate; a value carrying a reordering bidi control (U+202E and
  family) is refused by code point; and an honest name that merely carries a
  letter no fold reduces (Þóra, Kjær, Bæk, sœur) is certified by its
  readable letters instead of being refused for its unreadable one. Proven by
  `a-confusable-outside-the-curated-table-is-refused-not-passed`,
  `a-multi-script-forgery-is-refused-whatever-scripts-it-uses`,
  `a-partially-mapped-single-script-word-is-refused-not-passed`,
  `a-lisu-spelling-of-the-author-cannot-certify-a-second-person`,
  `a-bidi-override-cannot-render-an-approver-as-the-author`,
  `an-icelandic-name-with-thorn-passes-cleanly`,
  `a-danish-name-with-ae-passes-cleanly`,
  `a-lisu-spelling-of-tbd-is-not-a-snapshot-pin` and
  `a-wholly-single-script-approver-still-passes` (the printed case ids, so the
  citation greps straight out of the suite's own output).
- The gate examines the directory it was named and never a silently
  substituted git top level, so an empty named directory is NO-DATA for that
  directory. Proven by
  `the-gate-examines-the-directory-it-was-named-not-the-git-toplevel`.
- Every diagram and entity grammar starts at any letter (Unicode word
  properties), a diagram line the parser cannot read is confessed and refuses
  the "all traceable" verdict, create/destroy participants keep their alias,
  and `A & B --> C & D` reads every member. Proven by the ten design evals from
  `a-japanese-data-model-is-a-data-model` through
  `a-line-the-parser-cannot-read-refuses-all-traceable` (the printed case ids, so the
  citation greps straight out of the suite's own output).
- The two-alternatives floor counts only rejections that are ESTABLISHED: an
  option whose own text or governing heading carries a rejection verdict, or,
  once the decision is identified among the listed options (a chosen marker
  in any authoring form, a chosen table row, or the Decision's quoted
  choice), the remaining listed options. When no option carries a verdict
  and the Decision paraphrases instead of quoting, the winner may be any of
  them, and the verdict is NO-DATA naming the ambiguity rather than a count
  the check cannot defend; a bullet marking itself chosen is the decision in
  every form, not only in a table. Colon-terminated and bold section leads
  (`Criteria:`, `**Criteria**`, `Entities:`) are read as the headings they
  declare, in the ADR and the data model both. Proven by
  `a-faithful-madr-with-one-rejection-fails-the-floor`,
  `a-madr-with-two-real-rejections-passes-with-an-honest-count`,
  `an-in-bullet-chosen-marker-cannot-inflate-the-rejected-count`,
  `unmarked-options-with-an-unnamed-winner-are-nodata-not-a-count` and
  `a-colon-led-hurried-adr-is-read-as-its-sections`.
- Every report line prints through one flattening choke point (`say()`), so no
  interpolated value of any kind can move the cursor or open a second verdict
  line, and the source lint that enforces it derives its file set from the
  tool walk rather than a filename list: a tool added later is linted on
  arrival, the reviewed exceptions are named with reasons and reconciled on
  every run, and `sbe_decide.py` (whose Recommendation and Alternatives lines
  a table's option name could forge) is inside it. Proven by
  `a-receipt-field-cannot-move-the-cursor-in-the-rendered-report` and the
  report-print lint in `evals/test_no_data_class.py`, whose dead-exemption
  reconciliation is itself a failure path.
- `verify-install.sh` names UNWALKABLE directories and discloses that it
  verifies content, not modes; a shipped doc sentence asserting tool behavior
  is falsified against the source by the doc-behavior guard, whose liveness
  predicates read the MECHANISM (comment-stripped source for the removed
  re-root; the raw marker text for the waiver marker, which is itself
  comment-shaped) and never prose, and one dead claim family is a failure by
  itself. Proven by `no-shipped-doc-widens-the-receipt-lookup-past-what-the-gate-does`.
- Autosave snapshots cover the worktree the ref names (never the hook's cwd
  subtree), the skip-and-save decisions are logged, the tick counter and
  runaway warning serialize on a lock so the printed count is the measured
  one, every superseded snapshot stays reachable through the ref's reflog,
  the per-worktree id is git's own hash of the path (CRC-32 collided across
  ordinary paths), and recover's empty-ref sentence describes the whole
  namespace with legacy-id fallbacks. Proven by TestAutosaveCoversTheWorktree
  in `tools/test_sbe.py`.
- Telemetry writers serialize on an exclusive lock with per-process temp
  paths, and the migrate loss guard recounts the real post-rename file under
  that lock, so a live session's appended row survives a concurrent migrate
  and a maintenance collision cannot report a migration that reached no file.
  Proven by TestTelemetryWriterSerialization in `tools/test_sbe.py`, which
  runs the writers concurrently for real.
- The diagrams FAIL names what it examined (declared entities, components,
  states and systems of record) instead of asserting a whole-dossier absence,
  and a system of record an entity names is a traceable declaration. Proven
  by `a-system-of-record-named-in-the-data-model-traces-a-diagram-node`.
- Guide 01's planted-drift demonstration is replayed from the guide's own
  fenced steps by the suite, and the intake's printed override teaching names
  all three edits while the mismatch FAIL names the completing edit. Proven
  by `guide-01s-drift-demonstration-replays-from-its-own-steps` and the
  override evals in `evals/run_evals.py`.
- An exemption key resolves against the fixture leaf or heading it names, the
  access and legacy axes are non-exemptible by construction, and a waiver that
  excuses no PASS is a meta-test failure. Proven by the `gd_exempt*` guards and
  the dead-waiver guard in `evals/run_evals.py`.
- `verify-install.sh` enumerates every directory entry regardless of type, so a
  symlinked planted module is named rather than invisible, and an eval gates
  `CHECKSUMS.sha256` against the tracked tree so a stale manifest is a red
  suite. Proven by `a-symlinked-planted-module-fails-the-install-check` and
  `the-tracked-manifest-matches-the-tree-it-ships-with`.
