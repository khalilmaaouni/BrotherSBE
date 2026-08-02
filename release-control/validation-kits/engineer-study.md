# Engineer Study Protocol

Status: founder-gated, not yet run. This is the complete protocol for the five engineer
sessions required by review 13.2 (External validation protocol, section 13.2) and scored as
control D13-C02 (review 21.5, Deliverable control matrix). A facilitator with no prior context
should be able to run all five sessions from this file, the seeded repositories it describes,
and `metrics.json` alone.

Until these five sessions run and pass, dimension D13 stays capped at 1.0 out of 5 against a
release floor of 5.0 (review 1.2), and 1.0.0 cannot be tagged (review 14, "Five unrelated
engineer scenarios pass" and "no release-blocking control is NO-DATA").

## 1. Who can be a participant

Five experienced backend, data, or infrastructure engineers, recruited the same way as the
beginner study: no prior contribution to BrotherSBE, no prior sight of this repository's
source, dossiers, or this kit (review 13.2; Wave 8 task SBE-W8-001, section 9, "minimum five
... experienced engineers"). Per review 21.5's ownership line for D13: the person who
coordinates this study (A10 in the review's role naming) must not also be one of the five
subjects or the final judge of the results; whoever runs the study and whoever scores it must
be different roles.

Each participant should have enough backend or data engineering experience to review a real
pull request unaided; that is what they are being asked to do here, once with SBE and once
without (section 3).

## 2. Seeded-defect repositories

Five repositories, each seeded with a known, deliberately planted set of defects drawn from
the change matrix in review 12.3. Every defect class in review 12.3 is planted in exactly one
of the five repositories below, so the five sessions together exercise the full matrix once.
Each repository also carries one **non-critical control defect**: a change that looks like it
might need scrutiny but is actually safe, used to measure false positives and ceremony
proportionality (review 13.2, "whether SBE causes unnecessary ceremony on low-risk changes").

| Repo | Estate type (review 12.2) | Defect classes planted (review 12.3) | Release-critical? |
|---|---|---|---|
| EN-1 | Small Python API | breaking API change; idempotency defect; check-then-act race; retry without bound | all four critical |
| EN-1 | (control) | backward-compatible API addition | non-critical control |
| EN-2 | Node/TypeScript service (a small billing/order path) | transaction/external-call defect; fan-out doubling revenue; money/partner path requiring approval; silent exception | all four critical |
| EN-3 | Data/dbt project | wrong grain; stale system-of-record mapping; mixed-schema incompatibility; PII export | all four critical |
| EN-4 | SQL migration project, with a Terraform infrastructure change included (review 12.2 items 5 and 6) | migration without rollback; lock-heavy migration; Terraform destructive plan | all three critical |
| EN-4 | (control) | docs-only safe change | non-critical control |
| EN-5 | Evidence/security adversarial fixture, built on the malicious/poisoned repository fixture (review 12.2 item 12) and the evidence matrix (review 12.4) | missing run evidence; forged local receipt; stale receipt; wrong command receipt; prompt injection in README; symlink/FIFO/path attack | all six critical |

That is 22 release-critical defect classes plus 2 non-critical controls, covering every entry
review 12.3 lists. Assign one repository to each of the five engineers, single-blind: the
engineer is told only "this repository has a pending change; review it with BrotherSBE's help
and tell me what you find", never how many defects exist or which ones.

Each repository must be built (fixture code, the seeded defect, and a git history that makes
it look like an ordinary pending change) before any session runs. Building the actual fixture
content is separate follow-up work; this document is the protocol and the acceptance bar the
fixtures must be built and checked against, not the fixture source itself.

## 3. Session structure

For each engineer:

1. Give them the assigned repository and the one-line task brief: "review the pending change
   in this repository. Use BrotherSBE if you want to; you decide how." (Do not force BrotherSBE
   use; a forced-use session cannot measure whether the tool's ceremony matches the change's
   real risk, which is one of the required measures.)
2. Let them run `/brothersbe:kickoff`, `/brothersbe:design`, `/brothersbe:verify`,
   `/brothersbe:review`, or any subset, in any order, exactly as the guided flow recommends.
   Facilitator rules are the same as the beginner study (`beginner-study.md`, section 2): no
   coaching after a failure appears, scenarios fixed before sessions, facilitator never types.
3. Ask the engineer to produce a short written list of what they believe is wrong with the
   change and what they would do about it, whether that list came from BrotherSBE's findings,
   their own reading, or both.
4. Debrief: show them the actual seeded defect list for their repository (never before this
   point) and ask them to mark, for each seeded defect, whether their own list caught it, and
   separately whether anything BrotherSBE's evidence surface reported caught it.

## 4. What to measure (review 13.2)

### 4.1 Critical defect recall
For each engineer's repository, the fraction of that repository's release-critical planted
defects (the "all critical" rows in section 2's table) that BrotherSBE's evidence surface (a
gate, a review finding, or a named check) flagged as actionable, regardless of whether the
engineer independently also caught it by reading. Metric field: `critical_recall` per session,
and `critical_recall_overall` as the sum of caught release-critical defects across all five
repositories divided by 22 (the total planted).

### 4.2 False-positive rate
For each engineer's repository, whether BrotherSBE's evidence surface raised a finding, a
required gate, or extra ceremony against that repository's non-critical control defect (the
backward-compatible API addition in EN-1, or the docs-only change in EN-4) as though it were a
real problem. Record `true`/`false` per control item per session, and roll up per detector
(which named check or gate fired the false positive) so review 13.2's "predeclared threshold
per detector" can be checked per detector, not just in aggregate. Metric field:
`false_positive_by_detector` (a map of detector name to count).

**Predeclared per-detector threshold, fixed by this document before any session runs:** no
single named detector (gate, lint, or review finding class) may fire a confirmed false
positive against a non-critical control item on more than one of the five repositories out of
the two opportunities available (EN-1's control and EN-4's control) unless the founder revises
this number in writing before the sessions run. In plain terms: one false positive from one
detector is tolerated; two or more from the same detector fails this threshold.

### 4.3 Quality and actionability of findings
For every finding BrotherSBE's evidence surface produced that corresponds to a real planted
defect, the engineer rates it on a 3-point scale: actionable (tells them what to do and where),
partially actionable (points at the right area but not the fix), or not actionable (correct
but useless, e.g. a bare fail with no detail). Metric field: `actionability_rating` per finding,
plus `actionability_summary` (counts per rating) per session.

### 4.4 Time to verified plan
Wall-clock minutes from the start of the session to the point BrotherSBE reports a plan (a
task list, a set of gates to clear, or an explicit "here is what needs fixing before this can
merge") that the engineer independently agrees is a correct read of what actually needs fixing.
Metric field: `time_to_verified_plan_minutes`.

### 4.5 Whether evidence is independently understandable
Show the engineer one piece of raw evidence output (a gate verdict, a receipt, a review
finding) with no live explanation from the facilitator, and ask them to explain what it proves
and what it does not, the same test review 13.3 applies to the independent evidence auditor
("must not rely on maintainer explanations"). Record `true`/`false` for "correctly explained
without help" and the verbatim explanation. Metric field: `evidence_independently_understood`.

### 4.6 Ceremony proportionality on low-risk changes
For the two non-critical control items (EN-1's backward-compatible API addition, EN-4's
docs-only change), record the tier BrotherSBE's intake assigned and whether verify/review
demanded artifacts or gates beyond what a low-risk (T0/T1) change should need (review 14,
Core behavior: "Low-risk changes avoid unnecessary high-tier ceremony"). Ask the engineer
directly: "did this feel proportionate to how risky the change actually was?" Metric field:
`ceremony_proportionate` (`true`/`false`) plus the assigned tier and the engineer's verbatim
comment.

## 5. Release thresholds (verbatim from review 13.2)

- **100% detection of the release-critical seeded defects in the agreed corpus.**
  `critical_recall_overall` must equal 1.0 (all 22 of 22).
- **No silent false assurance.** No session may show BrotherSBE's evidence surface reporting a
  planted release-critical defect's area as PASS or verified when that defect was never
  actually exercised by a check; any such case is a hard fail of this threshold regardless of
  the recall number, because it means the tool actively vouched for something broken.
- **False positives below a predeclared threshold per detector.** No detector exceeds the
  ceiling fixed in section 4.2.
- **Expert reviewers rate critical findings actionable.** Every finding tied to a
  release-critical planted defect must be rated `actionable` or `partially actionable`
  (section 4.3); a majority of `not actionable` ratings on critical findings fails this
  threshold.
- **Low-risk path remains proportionate.** Both control items must show
  `ceremony_proportionate = true`.

If any threshold fails, D13-C02 is not accepted, D13 stays capped, and 1.0.0 stays untagged.

## 6. After the sessions

1. Fill in `metrics.json` under `engineer_study` for all five sessions.
2. File the five written findings lists, the debrief marksheets, and the raw evidence output
   shown to each engineer, unedited, alongside this document.
3. Mark D13-C02 accepted only if every threshold in section 5 passed; otherwise remediate the
   specific gap (a missed defect, an over-firing detector, an unclear finding) and rerun that
   repository with a fresh, unrelated engineer, per the "remediate and rerun" rule that also
   governs the beginner study (review 9, Wave 8, SBE-W8-008: "all critical/high findings; no
   paper closure").
