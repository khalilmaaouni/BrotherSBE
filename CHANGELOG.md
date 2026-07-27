# Changelog

Newest first. Each entry names the behavior that changed and the check or test
that proves it, because a changelog line nothing can verify is a press release.
What this file does NOT record: internal working notes and measurements from
the estates this project was built on, which stay untracked by the publish
checklist's own rules.

## 1.0.0-rc.1 (unreleased)

The first named version. Before this line the only name for an install was a
commit hash, which `tools/sbe_telemetry.py check-update` compares but no human
can read a promise into.

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
- The MADR chosen option is the decision, not a rejected alternative, so the
  two-alternatives floor cannot be satisfied by chosen-plus-one. Proven by
  `a-faithful-madr-with-one-rejection-fails-the-floor` and
  `a-madr-with-two-real-rejections-passes-with-an-honest-count`.
- An exemption key resolves against the fixture leaf or heading it names, the
  access and legacy axes are non-exemptible by construction, and a waiver that
  excuses no PASS is a meta-test failure. Proven by the `gd_exempt*` guards and
  the dead-waiver guard in `evals/run_evals.py`.
- `verify-install.sh` enumerates every directory entry regardless of type, so a
  symlinked planted module is named rather than invisible, and an eval gates
  `CHECKSUMS.sha256` against the tracked tree so a stale manifest is a red
  suite. Proven by `a-symlinked-planted-module-fails-the-install-check` and
  `the-tracked-manifest-matches-the-tree-it-ships-with`.
