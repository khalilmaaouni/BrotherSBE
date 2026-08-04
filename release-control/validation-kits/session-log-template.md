# Session Log Template

Copy this file once per session (beginner or engineer) before that session starts. Fill it in
live, as the session happens, in real time. Do not reconstruct a log from memory afterward: a
log written after the fact is not a timestamped record, it is a summary, and summaries are
exactly what review 13.3 says an independent audit must not have to take on trust.

Name each copy `session-log-<study>-<session_id>.md`, for example
`session-log-beginner-B1.md` or `session-log-engineer-E3.md`, using the session IDs already
defined in `metrics.json`.

---

## Session header

Fill in before the participant arrives.

- Study type: `beginner` or `engineer`
- Session ID (matches `metrics.json`):
- Date:
- Facilitator name:
- Participant ID (no real name in this file; keep the name-to-ID mapping in a separate,
  access-restricted file if one is needed):
- Host OS and version:
- Python version:
- Claude Code version:
- Provided repository / assigned repo (beginner: the estate from `estate-matrix.md`;
  engineer: the repo ID from `engineer-study.md` section 2):
- Outcome prompt used, if beginner session (A, B, or C, from `beginner-study.md` section 3.3):

## Live event log

One row per event, added the moment it happens. Never batch several minutes of events into one
row after the fact.

| Timestamp (HH:MM:SS) | Event type | What happened, verbatim where possible |
|---|---|---|
| | session-start | |
| | | |
| | | |

Event types to use (add rows as needed, do not merge two events into one row):

- `session-start`, `session-end`
- `step-started` (which numbered step from the scenario script)
- `step-completed`
- `command-run` (the exact command or skill invocation the participant typed or triggered)
- `wrong-command` (a command/choice that did not match the guided recommendation, per
  `beginner-study.md` section 4.4 or the equivalent engineer measure)
- `participant-question` (verbatim question)
- `facilitator-response` (verbatim response; should be empty or the fixed non-answer script
  for anything past a wording clarification, per the no-coaching rule)
- `intervention` (anything beyond the fixed script; count these against the intervention
  metric)
- `error-or-stall` (what the participant hit, and how long before they moved past it or the
  facilitator logged it as unresolved)
- `evidence-shown` (which verdict or receipt was shown to the participant for the
  comprehension check, verbatim)
- `settings-edit` (any manual edit to a config, settings file, or environment variable, with
  the exact change and a note on whether the product already documents it)

## End-of-session capture

Fill in immediately after the live portion ends, before any debrief conversation that could
anchor the answers (especially before the SUS questionnaire).

### For a beginner session

- Completion (reached PR-ready state unassisted): yes / no
- Elapsed minutes (step 2 start to step 5 reached, or to abandonment):
- Intervention count (tally from the event log):
- Wrong-command count (tally from the event log):
- Evidence line shown for the PASS/NO-DATA/WAIVED check:
- Participant's verbatim explanation of that evidence line:
- Judgment: critical misunderstanding present (treated NO-DATA/WAIVED as PASS)? yes / no
- Participant's verbatim answer to "what did BrotherSBE actually check?":
- Judgment: accurate / partially accurate / could not explain
- Participant's verbatim answer to the privacy/telemetry question:
- Judgment: correctly describes default-off telemetry and no network call? yes / no
- SUS questionnaire: record all 10 raw item scores (1 to 5) here, then compute the 0-100 score
  per the standard SUS formula.
- Participant's verbatim open-ended trust concerns:
- Uninstall or retain: which did the participant choose, and their stated reason, verbatim:
- Any undocumented settings edit (cross-reference the event log): yes / no, detail:

### For an engineer session

- Repo assigned and its planted defects (copy from `metrics.json`, do not re-derive from
  memory):
- Engineer's written findings list (attach verbatim, or paste inline):
- Per planted release-critical defect: caught by BrotherSBE's evidence surface? yes / no.
  Caught by the engineer's own reading, independent of BrotherSBE? yes / no.
- Per non-critical control defect: did BrotherSBE's evidence surface raise a finding, gate, or
  extra ceremony against it? yes / no. If yes, which detector?
- Actionability rating for each critical finding: actionable / partially actionable / not
  actionable, with the engineer's one-line reason.
- Time to verified plan (minutes), and what confirmed the engineer agreed it was correct:
- Evidence line shown for the independent-understanding check, and the engineer's verbatim
  explanation:
- Judgment: correctly explained without help? yes / no
- Tier BrotherSBE's intake assigned to the non-critical control item's change:
- Engineer's verbatim answer to "did this feel proportionate to how risky the change actually
  was?":
- Judgment: ceremony proportionate? yes / no

## Facilitator sign-off

- I confirm this log was written live, during the session, not reconstructed afterward: yes / no
- I confirm no coaching occurred once a failure appeared, per the facilitator rules: yes / no
- Facilitator signature and date:

## After completing this log

Transcribe every field above into the matching session object in `metrics.json` (same
session_id), then file this log itself, unedited, in the release evidence bundle alongside the
other session logs. This log is the raw evidence an independent auditor would want to see under
review 13.3; `metrics.json` is the rolled-up, scoreable version of the same facts.
