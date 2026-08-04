# Beginner Study Protocol

Status: founder-gated, not yet run. This document is the complete, ready-to-execute protocol
for the five beginner sessions required by review 13.1 (External validation protocol,
section 13.1) and scored as control D13-C01 (review 21.5, Deliverable control matrix). Nothing
in here is a placeholder. A facilitator with no prior context on this program should be able
to run all five sessions from this file alone.

Until these five sessions run and pass, dimension D13 (Independent and external validation)
stays at 1.0 out of 5 against a release floor of 5.0 (review 1.2, the release-readiness
scorecard), and BrotherSBE 1.0.0 cannot be tagged stable (review 14, the binary no-release
gate, item "Five unrelated beginner scenarios pass").

## 1. Who can be a participant

Per review 13.1: participants must not have contributed to SBE. In practice that means, for
every candidate:

- has never opened a commit, pull request, issue, or code review comment against the
  BrotherSBE repository or any of its predecessor internal projects;
- has never seen this repository's source code, its design dossiers, or this validation kit
  before their session;
- is not a member of the team that built or reviewed BrotherSBE.

Recruit five such people (review 13.1 and Wave 8 task SBE-W8-001, section 9, "Recruit
unrelated users: minimum five beginner/adjacent users"). "Beginner/adjacent" means: they can
write or read basic backend code (a simple API handler, a simple script) but have not used
BrotherSBE, and ideally have not used a similar design-and-verification tool before. Do not
recruit five people who all know each other or work on the same team; the point of "unrelated"
is that a shared blind spot does not repeat across all five sessions.

## 2. Facilitator rules

These rules exist so the study measures the product, not the facilitator's helpfulness. They
come directly from review 9, Wave 8, task SBE-W8-002 ("Define scenarios before sessions: no
coaching tailored after failures appear") and from review 13.3's principle that a result must
not depend on someone explaining it into existence.

1. **Scenarios are fixed before the first session runs.** The scenario script in section 3
   and the outcome prompts in section 3.3 are locked before session one. Do not adjust the
   script mid-study because an earlier participant struggled; a change made after seeing a
   failure is coaching by another name.
2. **No coaching once a failure appears.** Once a participant hits an error, a stall, a wrong
   turn, or visible confusion, the facilitator does not hint, correct, or suggest a next step.
   The facilitator observes, times, and writes it down. If the participant asks a direct
   question ("what do I type now"), the facilitator says only "please do what you think is
   right" and logs the question as an intervention request (see section 4.3).
3. **Clarifying questions about wording are the one exception.** The facilitator may restate
   the scenario brief in different words if the participant does not understand the English
   of the prompt itself (not the product). Log every such restatement.
4. **The facilitator never touches the keyboard.** The participant runs every command and
   types every answer themselves, including install steps.
5. **Every session is recorded, including failed ones.** A session that goes badly is data,
   not a discard. Do not re-run a participant to get a cleaner result.
6. **One facilitator, one session log per participant**, using the template at
   `release-control/validation-kits/session-log-template.md`.

## 3. The scenario script

Run this script, unchanged, for each of the five participants. Each participant gets a fresh
clean host (section 3.1) and one of the pre-approved provided repositories (section 3.2), and
gives one of the pre-approved outcome prompts (section 3.3).

### 3.1 Clean supported host

"Clean" means: no BrotherSBE plugin, clone, or configuration has ever existed on this machine
or user account, and no BrotherSBE hook lines exist in any `settings.json` the participant's
Claude Code session will read. "Supported" means the host matches what the product currently
claims to support: a Linux or macOS machine with a supported Python 3 and a current Claude
Code install (README.md, "Requirements"; review 12.1, Platform matrix). Prepare one such
machine or fresh container image per session, verified clean immediately before the
participant sits down. Record the OS, Python version, and Claude Code version in the session
log header.

### 3.2 A provided repository

Use one of the small, realistic estate fixtures from
`release-control/validation-kits/estate-matrix.md` (the small Python API estate is the
default choice; use the same one across all five beginner sessions so the five journeys are
comparable). Do not let the participant pick their own repository: review 13.1 calls for
"start in a provided repository", and a self-chosen repository is a different, uncontrolled
scenario.

### 3.3 The step-by-step journey

Read each step aloud to the participant (or hand them a printed card with the same wording)
and then stop talking. The six steps are the six beats review 13.1 requires under "Scenario":

1. **Install on a clean supported host.** Give the participant nothing but the public README.
   Ask them to install BrotherSBE using the instructions there, either the marketplace path or
   the clone path, their choice. Do not tell them which path to pick.
2. **Start in the provided repository.** Ask them to open the provided repository in Claude
   Code and begin working with BrotherSBE. Do not name the command. If they find
   `/brothersbe:start` on their own from the README, that is the intended path; if they try
   something else first, let them and log it as a wrong command choice (section 4.4).
3. **Describe a modest backend outcome.** When BrotherSBE asks what outcome they want, the
   participant reads one of these three pre-approved prompts aloud and types it in, chosen by
   a fixed rotation (participant 1 and 4 get prompt A, participant 2 and 5 get prompt B,
   participant 3 gets prompt C), so the study is not re-improvising the ask each time:
   - Prompt A: "I want an endpoint that returns how many orders were placed in the last 30
     days."
   - Prompt B: "I want a script that finds duplicate customer records by email and reports
     them, without deleting anything."
   - Prompt C: "I want the API to reject a request that is missing a required field, with a
     clear error message instead of a crash."
   Each prompt is deliberately modest: a real but small, low-risk backend change, the kind
   review 12.1's T0/T1 tiers are built for, never touching money, partner data, personal data,
   or a schema.
4. **Follow the recommended next actions.** From here the participant is on their own. They
   should let BrotherSBE tell them what to do next at each stage (this is what
   `/brothersbe:next` and the response contract every skill ends with are for) rather than the
   facilitator directing them.
5. **Reach a reviewed, evidence-backed, PR-ready state.** The session's target is the point
   where BrotherSBE reports the change has a completed design record proportional to its tier,
   passing gates and a run review, and is ready for the participant to open a pull request
   (they do not have to actually open it against a real remote; reaching the recommended
   "open the PR" step is the finish line). Record the wall-clock time from step 2 to this
   point.
6. **Uninstall or retain, intentionally.** Ask the participant one closing question: "do you
   want to keep this installed, or remove it, and why". Whichever they choose, have them
   actually carry it out (uninstall per the README's "Uninstall" section, or explicitly leave
   it installed) rather than just stating an intention. Log which they chose and their stated
   reason verbatim.

## 4. What to measure

Every measure below is required by review 13.1. Record each one in the session log
(`session-log-template.md`) as the session happens, and roll every session's numbers into
`metrics.json` afterward using the field names given here.

### 4.1 Completion rate
Did the participant reach the PR-ready state in step 5 unassisted (per the no-coaching rule)?
Record `true`/`false` per participant. Metric field: `completion`.

### 4.2 Elapsed time
Wall-clock minutes from the start of step 2 (opening the provided repository) to reaching the
PR-ready state in step 5, or to the point the session was called (abandoned or timed out).
Metric field: `elapsed_minutes`.

### 4.3 Number of maintainer interventions
Count every time the facilitator spoke or acted beyond reading the fixed script and the
allowed wording clarification in rule 2.3. This includes answering a direct "what do I do"
question, even with a non-answer like "do what you think is right", because the participant
asking is itself a signal the guided flow did not tell them. Metric field:
`intervention_count`.

### 4.4 Wrong command choices
Count every command, skill invocation, or menu choice the participant made that was not the
one the guided surface (the response contract's "recommended next action") had just told them
to take, whether or not it eventually worked. Metric field: `wrong_command_count`.

### 4.5 Misunderstanding of PASS, NO-DATA, and WAIVED
At the end of the session, before revealing anything, show the participant one evidence line
from their own run (a gate or review verdict) and ask them to explain in their own words what
it means. A **critical misunderstanding** is any answer that treats NO-DATA (nothing was
checked) or WAIVED (a human explicitly excused it) as though it were PASS (it was checked and
it held). Record the verdict shown, their verbatim answer, and a `true`/`false` judgment for
"critical misunderstanding present". Metric field: `evidence_state_misunderstanding`.

### 4.6 Ability to explain what was verified
Separately from 4.5, ask: "in your own words, what did BrotherSBE actually check before
telling you this was ready?" Record the verbatim answer and a facilitator judgment on a 3-point
scale: accurate, partially accurate, could not explain. Metric field: `explains_verification`.

### 4.7 Privacy and telemetry comprehension
Ask: "does this tool send any of your code or data anywhere? How do you know?" A correct
answer references that telemetry categories are opt-in and off by default and that there is no
network call by default (README.md, "Status"; SECURITY.md). Record verbatim answer and a
`true`/`false` for "correctly describes default-off telemetry and no network call". Metric
field: `privacy_comprehension`.

### 4.8 System Usability Scale (SUS) or equivalent
Administer the standard 10-item System Usability Scale immediately after the session, before
any debrief conversation, so later discussion does not anchor the scores. Use the standard
wording and 5-point (strongly disagree to strongly agree) scoring, and compute the standard
0-100 SUS score. Metric field: `sus_score` (with the 10 raw item scores also recorded).

### 4.9 Open-ended trust concerns
Close with: "is there anything about this that you would not trust, or that worried you,
before you'd let it touch a real project?" Record the verbatim answer. This is qualitative;
do not force it into a number. Metric field: `trust_concerns_text`.

## 5. Release thresholds (verbatim from review 13.1)

Every one of the following must hold across the five sessions before D13-C01 counts as met:

- **5/5 complete the core journey.** All five sessions must show `completion = true`.
- **No critical misunderstanding of evidence state.** Every session must show
  `evidence_state_misunderstanding = false`.
- **No undocumented manual settings edit.** If any participant edited a settings file, a
  config, or an environment variable by hand to get past a problem, that edit must already be
  documented in the product's own instructions; an edit invented to route around a gap fails
  this threshold. Record any such edit in the session log verbatim, with a citation to where
  (if anywhere) the product documents it.
- **Median intervention count zero.** Across the five sessions, the median of
  `intervention_count` must be exactly 0.
- **Every high usability failure remediated and rerun.** A "high usability failure" is any
  session where the participant could not proceed for more than five minutes without an
  intervention, or where the SUS score falls in the range usability research treats as poor
  (below 68 on the standard 0-100 SUS scale). Any such failure must be fixed in the product,
  and the fixed version rerun with a fresh, unrelated participant (not the same person, so the
  rerun is not measuring memorized familiarity) before D13-C01 can be marked accepted.

If any threshold is not met, D13-C01 stays not-accepted, D13 stays capped, and 1.0.0 stays
untagged. This is not this document's decision to soften; it is the review's floor.

## 6. After the sessions

1. Fill in every field of `metrics.json` under `beginner_study` for all five sessions.
2. File the five session logs, unedited, alongside this document (or wherever the founder's
   release bundle collects raw evidence).
3. If every threshold in section 5 passed, mark D13-C01 accepted in whatever ledger the
   release program is tracking control acceptance in (review 21.1, 21.13).
4. If any threshold failed, do not mark it accepted, and do not average it away against a
   strong score elsewhere: review 1.2 is explicit that "a strong average never overrides a
   failed floor gate."
