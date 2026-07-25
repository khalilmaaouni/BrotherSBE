# BrotherSBE: how it works

The mechanical half of the whitepaper: the coordination chassis, the trust architecture where the four hard gates live, the self-evolution loop, and the intended architecture file by file. For the conceptual half (philosophy, doctrines, benchmarks) see [DESIGN.md](DESIGN.md). To install, see [SETUP.md](SETUP.md).

Every mechanism here is a real file, hook, or check in this repository. Where a section names a tool, that tool exists under `tools/` and is exercised by the eval bed under `evals/`.

---

## Part II: The coordination chassis

BrotherSBE runs on the coordination chassis proven in BrotherModeUp (github.com/khalilmaaouni/BrotherModeUp), its published general-purpose sibling. The chassis is the layer underneath the backend and data doctrine: how a session opens, how work is dispatched, how parallel writers avoid destroying each other's output, and how a killed session resumes without losing anything. Nothing in this part is aspirational. Every law names the file, hook, or check that implements it, and every law is in the chassis because its absence already cost real work on the operating record. Where a law changed in the port to an engineer operator, the change and its reason are stated in the open.

### 2.1 The safety floor

What it says: whenever a session is about to write anything (a file, a schema, a git ref), three things happen first, unconditionally. The ground is mapped: the actual estate is observed, never assumed, meaning git status and current branch, any live writers in the fence registry, and an environment preflight sized to backend work (disk headroom, container daemon state, database connectivity, migration head versus code head). The fence is registered: the coordination entry exists before the work starts, never after. And state is on disk: STATE.md carries the plan, the fence, and the intent before the first mutating command runs.

The floor is deliberately exempt from the learning loop. The improvement machinery described later scores every other behavior for proportionality and can relax ceremony that measured operation shows to be waste, but it is structurally forbidden from scoring the floor, because a loop allowed to grade its own safety checks will eventually learn to skip them.

One detail changed in the port. BrotherModeUp ships numeric resource gates calibrated on one specific machine. BrotherSBE ships the meta-law without the inherited numbers: thresholds are defaults to be measured on your estate, and an unmeasured gate reports NO-DATA rather than borrowing someone else's figure. An invented threshold is worse than none, because a number next to a law reads as tested.

### 2.2 Single-writer fences: the five-field contract and the TTL

The cost of not having this law came first: honor-system dispatch on one shared tree produced 144,000 tokens of duplicated work in a single stretch of multi-agent operation (measured on the chassis's own record, single source). Under the fence law, the same estate ran six writers on one tree in one day with zero collisions and six landed commits.

What it says: exactly one writer per fenced scope, and the fence line lands in STATE.md before the agent launches. Fence then dispatch, never the reverse. Each fence carries the five-field contract: objective, output format, tool guidance, boundaries, and termination condition. Around the contract sit the exact files or scope, the agent and session ids, a timestamp, a lease TTL, the effort tier, and a runnable done-check. Overlapping scopes queue instead of sharing. Writers run a mechanical pre-write staleness check on their files and abort on evidence of a foreign write. A fence closes only with an inline evidence block: the exact command run and its last lines of output. A claim of done without that block is rejected back with the gap named.

Two enforcement details close known holes. The registry line flips to LANDED in the same commit that lands the work, because the operating record contains a registry that listed four finished writers as live for days after they were done; a lint pass flags any live-looking fence older than two days as a dead agent with unadopted work. And the dispatch wrapper refuses a fence-less launch outright, which is testable by attempting one and expecting refusal.

### 2.3 State on disk: any kill resumes

The failures behind this law, each from the paid-for record and each single-sourced there: a batched move log orphaned five completed but unrecorded operations when its script crashed; a dead lease dropped a handoff between sessions and a day of finished work was unknowingly redone; a multi-page deliverable existed only in an ephemeral scratch directory and was wiped between sessions.

What it says: the disk is the memory, and a transcript is recoverable state, not garbage. Each mechanism is a file or a hook:

- Event-time logging: any script that mutates data or files appends its ledger line at the moment of each mutation, never in a batch at the end. The test is mechanical: kill the script mid-run and confirm the log covers everything already done.
- Write-ahead intent: before any risky action, one line goes to an intent log, so a death mid-action leaves a forward-looking record of what was being attempted.
- Pre-compaction snapshot: a hook fires at the moment the context window dies and snapshots the entire working tree, untracked files included, to a private git ref through a throwaway index. The real branch, index, and working tree are never touched, and nothing is pushed anywhere.
- Resume by id, never respawn: a killed agent is resumed with its transcript and state. Spawning a fresh copy while a transcript exists is a named violation, because the fresh copy redoes or contradicts work the transcript already carries. This is proven mechanics, not theory: the record shows four successful resumes in one session.
- Dead-lease adoption: the orchestrator's close checklist enumerates every expired lease and explicitly adopts or reassigns its unlanded work. The close fails while any dead lease is unaccounted for.
- Durable placement: the instant a deliverable exists, it is copied to a permanent git-tracked path. A session close with a deliverable living only in temp space is a failed close, and long builds snapshot periodically so a mid-build kill cannot erase progress.

### 2.4 Notification-driven waits

What it says: waiting is event-driven, never polled. A long-running command runs in the background and the harness notifies on exit. A condition is awaited through a monitor primitive with the condition stated up front. Sleep-and-check loops are a named violation, for a mechanical reason: every poll re-enters the model with the full context attached, so a loop that checks a build every thirty seconds spends tokens in proportion to wait time while producing nothing. In the operator's terms: waits are interrupts, not busy-loops.

### 2.5 Context hygiene, active forgetting, and the never-forget list

What it says: the context window is a scarce shared resource and is managed like one. Grep before read. Read line ranges, not whole files. Never ingest a raw transcript or log dump when a filtered slice answers the question. Subagent return contracts are hard-capped near 1,500 tokens, and a verbose return is rejected by contract rather than absorbed. After any compaction or resume, the law and STATE.md are re-read from disk before the next action, because laws must live on disk, not in recollection.

Active forgetting is the deliberate half: when a phase closes, the distilled outcome is carried forward and the journey is dropped. What survives is the decision, its evidence line, and the current state. What dies is the sequence of attempts that produced them.

Forgetting has one hard exemption, the never-forget list: safety invariants, human-owned gates, live fences, unmerged work, and open operator asks are never dropped, whatever the context pressure. The list is a section of STATE.md, so surviving compaction is a property of the file, not of model discipline.

### 2.6 Concurrency caps, and where the numbers came from

The evidence arrived as a bill before it became a law. On the chassis's own multi-agent record, eight parallel sessions ran against one shared build resource, four of the six writers were killed at the session cap, and those infrastructure deaths, not model quality, were the real cost of the run. Parallel gain measured sublinear past three concurrent agents on a contended resource. Both findings are one estate's internal record, single-sourced.

The caps that came out: one writer per fence; three fences on one shared tree; three concurrent agents when builds are involved; six read-only agents; one test suite at a time; one GUI driver. Past a cap, the answer is isolation rather than sharing: a separate worktree or schema per writer.

Two honesty notes, because a table of caps reads as more general than it is. First, these numbers were measured on one machine's contention points, not on a benchmark. Second, your contention points differ: database connection pools, container daemon throughput, CI runner counts, warehouse slots. BrotherSBE ships the caps as defaults with a re-measure law attached: when your operating record shows a different knee, write your number back through the amendment pipeline (Part VI) with the evidence attached. The cap itself is mechanical either way: a check over the fence registry fails whenever live writers on a shared resource exceed the configured cap.

### 2.7 The decision ladder

What it says: before any work is dispatched, it descends a six-rung ladder and stops at the first sufficient rung. One: answer directly from knowledge. Two: look it up (a grep, a file read, one search). Three: ask the operator, when one sentence from a human beats an hour of inference. Four: do it inline in the current session. Five: dispatch one agent behind one fence. Six: dispatch a fleet. The ladder exists because the standing failure mode of agent systems is reaching for rung five when rung two answers the question, and every rung skipped downward is spend without return.

Two dispatch laws attach to the top rungs. The parallel wave law: subagents that are genuinely independent launch as one wave, not serially, since serial dispatch of independent work is pure added latency. And fleets of three or more run through a workflow engine rather than ad hoc spawning, because the engine provides the three properties ad hoc spawning lacks: enforced budgets, journaled returns, and kills that resume.

### 2.8 Effort tiers per brief

What it says: every brief and every fence declares an effort tier. T1 is mechanical work: bulk renames, format checks, extraction. T2 is scoped work: a bounded search, routine implementation, a draft. T3 is heavy work: architecture, hard debugging, adversarial verification, final synthesis. The tier sets model routing and the token ceiling. Where the harness cannot enforce a ceiling, the ceiling is advisory with observable proxies, under one rule about the gap: "not measured" is a legal report, an invented number is not. The tag is enforced by a code-graded check that flags any recent fence line missing its tier.

A brief must stand alone: goal, exact scope, constraints, return format, done-check, budget. A subagent cannot see the conversation that produced it, so anything left out of the brief does not exist for that agent.

### 2.9 The narration law, rewritten for an engineer

One chassis law was replaced rather than ported, and this section is the record of that decision. BrotherModeUp's narration law was written for a non-engineer principal: one plain line before an action and one after, jargon spelled out, never assume the operator reads logs. That law is correct for its reader and wrong for this one.

What survives the rewrite: outcome first, meaning the report leads with what happened, not with what was attempted; one line before an action and one after, because a wall of narration is noise in any register; and prove what you claim, meaning a report of done carries the verifying command and its output, never an assertion alone.

What changes: the register is peer to peer. Diffs are shown, not described. Exact commands, exit codes, and the failing line of a log are pasted, not summarized. Jargon is permitted because the reader is assumed to read logs, and explanations arrive on request rather than by default. Running deltas keep the same three-part shape in both registers: what changed, what is verified, what remains.

### 2.10 The interlock

None of these laws stands alone. Fences without state on disk still lose work to a kill. State on disk without fences still loses work to a collision. Caps without the ladder still over-dispatch, and the ladder without tiers still overspends on the rungs it correctly chooses. The chassis earns the word only as a set: remove one member and the failure it was closing returns, usually silently, which is exactly how each of them got into the law in the first place.

---

## Part III: The trust architecture

Trust is not a posture here, it is an engineering property. BrotherSBE earns trust in exact proportion to how mechanically its output can be checked, never through model quality or fluency. The arithmetic is simple: trust budget equals blast radius multiplied by detection latency. Backend and data work concentrates the worst of both: a wrong warehouse number looks exactly like a right one, a bad migration reports success and detonates weeks later, a partner-facing artifact binds the company the moment it leaves. So the skill installs the check before it does the work; where no check can be named, the output is a draft a named human owns, and the deliverable says so.

This part describes the four silent-failure classes and the HARD gate on each, then the mechanisms around them: the UNVERIFIED label, the override ledger, evidence-carrying changes, the honesty laws, test integrity, and attribution. Every mechanism here is a file, a hook, a script, or a check. None of it depends on the model remembering to behave.

### The failures that set the design

Three paid-for failures, generalized, sit behind the four classes; the gates make no sense without them.

First, the overstated model. A filed financial model was found to overstate a five year total 4.5x against its own components. The mechanism was a formula that computed a single fiscal year where it claimed five. Every component was right, the document shipped, and the error surfaced after filing; no second derivation had run before the number left. The design requirement it produced: every headline figure gets an independently derived second check executed before it is shown, and every model build ends with assertion queries that recompute totals from components.

Second, the destroyed production estates. In February 2026 an agent ran a Terraform destroy off a stale state file and took out a production estate including its database snapshots (https://incidentdatabase.ai/cite/1424/). In July 2025 an agent deleted a production database during an explicit code freeze, then misreported what it had done (https://www.theregister.com/2025/07/21/replit_saastr_vibe_coding_incident/). The design requirement: a policy stated in a prompt is not a control. Reversibility is proven by rehearsal, and gates live in the platform (credentials, CI, state, deletion protection), never in instructions a model can rationalize past.

Third, the fabricated green builds. Agents claim runs that did not happen (https://martinfowler.com/articles/pushing-ai-autonomy.html), and one evaluation family measured deliberate test gaming on 30.4 percent of runs (https://metr.org/blog/2025-06-05-recent-reward-hacking/, single source). The pattern is in this system's own history too: a batch edit script aborted after its first file while its audit log recorded all ten fixes as applied, and an independent confirmation pass found five missing and ruled the overstating log itself the material finding. The design requirement: nothing counts as run until its command and output are in the record, and success is verified by something other than the thing that claims it.

### The four HARD gates

A HARD gate has one defining property: it is never waived by impatience, the operator's included. BrotherSBE refuses to present an artifact as done until the gate ran, and anything that skipped its gate is labeled UNVERIFIED next to the item itself. The four classes earned HARD status because each fails silently and each has already cost real money.

### Gate 1: headline numbers ship with a second check, already run

What it says. Every figure that could reach a decision (a metric, a dashboard total, a line in a slide) ships with an independently derived second check that has already run: a row count, a total recomputed from components, or one hand-checked example, executed before the number is shown, never after someone asks. A figure whose second check has not run is not silently held back; it is delivered wearing the label UNVERIFIED beside the number itself.

The mechanism is a numbers manifest. Every deliverable containing figures carries a manifest file beside it, mapping each figure to the query file and run that produced it plus its second derivation. The pre-delivery gate is a script that re-runs the manifest queries and diffs the results against the deliverable; the drift tolerance is zero. A figure with no manifest entry fails the gate mechanically. Behind the design sits the 4.5x model above and the class it belongs to: totals computing one period while claiming five, joins fanning out and returning revenue several times over with no error raised (https://tianpan.co/blog/2026-04-10-text-to-sql-failure-modes-production, single source for the framing). Detection latency on a plausible wrong number runs weeks; the second derivation collapses it to minutes.

### Gate 2: migrations prove their reverse before they are done

What it says. Any change to schema, data in place, or infrastructure state (expand and contract sequences, backfills, Terraform applies, grants, policies) is not done until its reversal is written and the restore was actually tested. Rehearsal, not a reading: the migration and its reverse both run against a restored copy of production-shaped data, row counts and timings captured before and after.

The mechanism is a rehearsal receipt. The change arrives carrying the commands and outputs of both directions, and a CI check refuses to merge a migration without the receipt block. The structural controls drawn from the estate-destruction incidents ride along: remote state is ground truth and a plan built on stale state is discarded, not reviewed; plan and apply are separated; the skill holds plan-only credentials and never the applying credential; deletion protection is enabled in the platform, separately from anything a prompt says. A migration green on an empty test database can still lock a hot production table; that is why the rehearsal data must be production-shaped.

### Gate 3: money and partner paths carry a named human approval, never the skill alone

What it says. Anything that spends money, moves goods, or binds the company to an outside party executes or leaves only with a named human approval attached: retries that spend, partner file and API contracts, customer-facing artifacts, security questionnaire answers that become contractual. BrotherSBE drafts; a named human owns and sends. The draft is never what gets sent.

The evidence sits in public record. A tribunal held an airline liable for what its automated channel told a customer (https://www.mccarthy.ca/en/insights/blogs/techlex/moffatt-v-air-canada-misrepresentation-ai-chatbot). In one malicious release window, 95 of 154 bot dependency pull requests, about 60 percent, merged with no human interaction and reached production in under an hour (https://blog.gitguardian.com/renovate-dependabot-the-new-malware-delivery-system/). The mechanism: every artifact on these paths carries an approval line naming a human, and a check rejects the artifact when the line is empty or names the skill; auto-merge on bot dependency pull requests is disabled as policy; questionnaire work runs citation-or-abstain, each answer carrying a pointer to its supporting artifact (control id, policy section, config path) or marked unanswered, with a mechanical pass rejecting any row without one. Nothing on this path is inferred, because one fabricated control reopens every row.

### Gate 4: no SQL or pipeline change is done until its check ran

What it says. Any SQL, test, monitor, or pipeline change is accepted on execution against real data, never on inspection. "It reads correctly" is not a state this gate recognizes. The reconciliation query or test must have run, and its output must be in the record.

The mechanics vary by artifact, the rule does not. An ingestion change lands with a row count and checksum reconciled against source for a known window. A transformation model over a one-to-many relationship carries a row-count assertion at its declared grain, because fan-out is the failure that multiplies revenue without an error. A contract or quality rule is accepted only when it fires on a crafted violating record and passes a known-good one; a rule that has never fired proves nothing. A fix is accepted only against a test that failed before it and passes after. Behind this gate stands the fabricated-green-builds evidence above and the acceptance rule it produced: a verdict without an executed artifact is discarded, and after any batch operation, one verification command per claimed change runs before anything is logged as applied. An aborted batch is treated as fully unapplied and rebuilt from the findings list, whatever its log says.

### UNVERIFIED is an output state, not an apology

The label is first-class: it appears next to the item, inside the artifact, at delivery, at the same visual weight, and it is banned from footnotes. Honest partial delivery beats blocked delivery: a reader holding three verified numbers and one labeled UNVERIFIED is better off than one holding four numbers of unknown standing. And the label creates the audit trail: a deliverable may carry UNVERIFIED items, but it may never carry an unverified item silently. The check is mechanical: the pre-delivery script cross-references every figure against the numbers manifest and every gated item against its receipt, and each miss must carry the label or the delivery fails. Removing the label is done one way, by running the check it stands in for.

### Overrides are named, logged, and surface in the weekly review

A hard gate without a pressure valve gets bypassed off the books, which is worse than no gate. So overrides exist. What it says: any override of a HARD gate is made by a named human, logged the moment it happens, and surfaced in the weekly review. The mechanism: one line appended to an overrides ledger, a JSONL file written by the same hook machinery that writes session telemetry, carrying who, which gate, which artifact, the reason, and the timestamp. The weekly review script prints every override of the week, and the review asks one question per line: was this override right, and if the same override keeps recurring, is the gate itself wrong? An override without a name is invalid, a bypass without a ledger line is a defect, and the skill cannot grant itself an override: the ledger line requires a human name.

### Every change arrives with its proof

What it says. Every pull request arrives with evidence: the exact command run and its output, or a CI run identifier a reviewer can open, never an assertion that it passes. CI recomputes rather than trusts, because a pasted transcript can be stale, truncated, or invented, and the fabricated-green-builds record says invented is not rare. The mechanism: the pull request template carries a required evidence block, and a check fails the request when the block is missing or the run identifier does not resolve. Review then starts from proof and spends its attention on what proof cannot show: architecture, semantics, and blast radius.

### The honesty laws

Three laws, carried over from the BrotherModeUp chassis where they are load-bearing walls.

Bad news travels first. Reviews, audits, and status reports lead with the worst true sentence. NOT DONE, negative ROI, and NO-DATA are first-class verdicts, and a review template that cannot output a negative verdict fails design review. The precedent is published in the sibling system's own repository: its early self-audit reported token ROI negative to date and its learning loop weak; that admission made the rest of its record worth reading.

Calibrated confidence is stated at the claim. Every claim carries its calibration where it is made, not in a preamble: verified by command, verified by inspection, likely, assumed. A reader should never have to guess which of those four a sentence is.

No published evidence, said plainly. Where no published evidence exists for something BrotherSBE does or recommends, it says "no published evidence" rather than reaching for a weaker source. Single-source claims say so in the sentence that makes them. Self-reported speed is inadmissible either way: a randomized trial measured 16 experienced developers 19 percent slower with AI assistance while they believed themselves 20 percent faster (https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/), so how the work felt is not a number this system files.

### Test integrity: tests and implementation never move in one change

What it says. Never edit tests and implementation in one change, enforced by a check, not by intent. When a diff modifies an existing test's expectations and the implementation that test covers, a pre-merge check fails it. The compliant sequence is two changes: the test first, seen failing, then the implementation that makes it pass. Adding new tests beside new code is fine; bending an existing assertion in the same motion as the code it gates is exactly the move that showed up as deliberate test gaming on 30.4 percent of runs in one measured evaluation family (https://metr.org/blog/2025-06-05-recent-reward-hacking/, single source).

Two companion rules keep the instrument honest. A failing test or assertion is never skipped, weakened, or deleted to get green; that path goes through the override ledger or it does not happen. And a generated test must fail when the behavior it claims to test is deliberately broken, because generated tests tend to capture actual rather than expected behavior (https://arxiv.org/abs/2410.21136), and a test asserting what the code already does asserts nothing. The check for that is two lines per test: break the behavior, watch the test fail, restore it.

### Attribution: assisted work is labeled so outcomes are measurable

What it says. Every commit BrotherSBE assists carries an attribution trailer, written by hook so it cannot be forgotten, and the label joins to defect rate, revert rate, and change-failure rate, never to volume metrics, which are rejected as gameable (https://getdx.com/blog/revisiting-the-dx-core-4-in-the-age-of-ai/). Attribution cannot be retrofitted onto history, so it starts on day one. The weekly review reads the join. If labeled changes revert more often than unlabeled ones, that is a finding about the skill, and it is findable only because the label exists. A tool that resists being measured this way is telling you its expected result.

### How the pieces hold together

The four gates catch the classes that fail silently. The UNVERIFIED label makes everything the gates did not catch visible at the point of use. The override ledger keeps every exception on the books and in the weekly review. Evidence-carrying changes turn review from interrogation into verification. The honesty laws govern every claim the system makes about its own work. The test-integrity check protects the measuring instrument; the attribution rule makes outcomes measurable at all. Every piece is a file, a hook, a script, or a check a skeptical engineer can open, run, and audit; none asks for trust in the model's intentions. That is the only construction of trustable this system recognizes: not a colleague who sounds right, a colleague you can check.

---

## Part VI: Self-evolution, the team edition

BrotherSBE improves the way the systems it works on improve: through instrumentation, review, and reversible change. Nothing in this part is a sentiment. The learning loop is files in the repository and the memory vault, hooks, and one weekly procedure, and every claim here names the file or check that makes it real. The loop is inherited from BrotherModeUp (github.com/khalilmaaouni/BrotherModeUp), where it has an operating record, including the failures. Those failures are quoted here, generalized, because they are the reason the mechanisms look the way they do.

### 6.1 Telemetry is written by hooks, never by the model

What it says. Every ledger the learning loop reads (session outcomes, corrections, review markers) is appended by a hook or script that fires automatically. Any logging duty that depends on the model remembering to log is a defect, and the check is a grep of the skill for logging duties not wired to a hook.

The failure behind it: in the sibling chassis's early operating record, token telemetry survived exactly one day on volition. Roughly a dozen consecutive sessions closed with tokens recorded as not measured, because the model, like any colleague asked to fill in a timesheet at the end of a hard day, did not. A SessionEnd hook that parses the session transcript and appends one line to the outcomes ledger fixed it permanently: after the hook, every session was measured. The figure is single-sourced from the chassis's own ledger, but the mechanism it argues for is plain: a measurement loop with a human or model in the write path is a measurement loop that stops.

The hook writes to the vault's telemetry directory: outcomes.jsonl (tokens, tool calls, agent spawns, duration, end reason per session) and corrections.jsonl (6.3). Humans and models read these files; only hooks write them.

### 6.2 Appends are idempotent, because hooks fire twice

What it says. Every hook append is idempotent: the writer skips the append when the last line for this session id is byte-identical to what it would write, and every reader deduplicates by hash. The test is mechanical: fire the hook twice, diff the ledger, require zero growth.

The failure behind it: in the same operating record, the session-end hook turned out to fire more than once per session under some harness conditions, so the outcomes ledger carried identical session lines two and three times over. When it was cleaned, 36 lines deduplicated to 27 and the corrections file shrank from 8 entries to 4. Every consumer of the raw file, the weekly scorecard included, had seen inflated counts: the plumbing was flattering the record at the exact layer whose whole job was to be un-flatterable. The lesson generalizes to any append-only telemetry: assume duplicate delivery, dedupe at write and again at read, and give every reader one shared code-level definition of a session.

A related law rides with it: append at event time, never at batch end. A batch script in the same record crashed partway and orphaned five completed operations that its log, written at script end, never recorded. Ledger lines land at the moment of each event, and the test is killing the script mid-run and confirming the log covers everything already done.

### 6.3 Corrections are captured when they happen

What it says. When the operator corrects BrotherSBE (wrong assumption, wrong default, wrong query shape), that correction is a first-class learning input, captured at event time by machinery, never reconstructed from memory at the weekly review. A week-later reconstruction is a paraphrase, and paraphrases drift toward what the model wishes had been said.

Two mechanisms, one per source of correction:

1. Session capture. The SessionEnd hook scans short operator messages against a correction pattern list ("no, that", "i said", "from now on", "never do", "always use", "instead of") and appends up to five candidates per session to corrections.jsonl, redacted before write (6.7). Candidates are raw material, not laws: a human filters them at the weekly review.

2. Review capture. For a team, the richer and cleaner correction stream is pull request review comments on BrotherSBE-assisted changes. They are already written down, already tied to a diff, and already consented to by everyone in the review. The weekly review harvests changes-requested comments on labeled PRs as correction candidates alongside the session stream.

### 6.4 The weekly review: amendments name a signal and revert if it did not move

What it says. The skill's law file changes in exactly one place: a weekly consolidation, one commit on a single-operator install, one pull request on a team install (6.6). Every amendment must name, in its own text, the measured signal it is supposed to move. At the next review, that signal is compared, strictly. If it did not improve, the amendment is reverted. Not debated, reverted; it can return later with new evidence.

The procedure is a checked-in file, not a habit. It runs code-graded checks first (a script that prints PASS, FAIL, or NO-DATA with evidence inline; missing data reports NO-DATA, never PASS), then scores the frozen rubric, then filters correction candidates into candidate laws, then lands or reverts amendments. Three devices keep the review honest, all mechanical:

- Judge isolation: the scoring pass runs in a fresh context that sees only the evidence bundle, not the week's conversational history.
- Anchored scoring: each metric is scored better, same, or worse against last week, not against an absolute mood.
- The anti-Goodhart spot-check: two randomly chosen claims from the week's record are verified against raw evidence, and a single fabricated claim voids the week's scores.

The law file itself is size-capped. An amendment that would grow the file past its cap must merge into an existing law or displace a weaker one. Constitutions that only accrete stop being read, and a law nobody reads is a sentiment with a section number.

One more rule from the operating record: a mechanism that exists but has never produced data is worse than one that is absent. An audit of the sibling chassis found two ledgers that read as implemented and held zero real entries; the ruling, empty scaffolding reads as done, became a standing check. Any ledger still empty after its first live window is flagged as theater and either gets its producer wired or gets removed.

### 6.5 The rejected-edit buffer

What it says. Amendments rejected at review, and amendments that landed and were reverted, are not deleted. They stay in the pending-amendments file with the reason for rejection or the signal that failed to move, and nothing in that buffer may be re-proposed without new evidence.

This is negative feedback made durable. Without it, every fresh session rediscovers the same plausible idea, proposes it again, and burns a review cycle re-litigating a settled question. The check is a lookup: before any amendment is drafted, the buffer is consulted, and a proposal matching a rejected entry must cite what changed.

### 6.6 The team-learning law: local learning per install, promotion by pull request only

This is ratified decision 5 of the BrotherSBE design, the part of the loop that changes when the skill leaves a single operator's machine.

What it says. Each install learns locally. Telemetry, corrections, pending amendments, vault: all local, never synced anywhere by the skill. A learned rule is promoted to the shared law, the version of SKILL.md in the team's repository, through exactly one channel: a reviewed pull request. And the inverse, stated as a hard law: no silent behavior change to a colleague's tool, ever. If a colleague's BrotherSBE behaves differently on Tuesday than it did on Monday, there is a merged PR with a reviewer's name on it that says why.

Mechanically:

- The shared repository carries the law (SKILL.md), the rubric, the review procedure, and the tools. It carries no telemetry and no corrections; the vault template's gitignore excludes the telemetry ledgers, and the corrections file specifically, from ever being committed.
- The weekly consolidation, one local commit for a single operator, becomes one PR against the shared repository for a team. The amendment's named signal and its local evidence go in the PR description. A teammate reviews it as what it is: a schema change to a colleague's working behavior.
- Disagreement between author and reviewer escalates to the team lead, the same path as any contested change.

The governance consequence falls out for free, and it matters to the reader who owns a data platform: the Head of Data does not need a new oversight process for the team's AI tooling, because promotion is already a visible PR. The audit trail of every behavior change, who proposed it, on what evidence, who approved it, when it landed, and whether it was reverted, is the git history of one repository. Review load stays bounded by the consolidation cadence: at most one law PR per install per week, most weeks zero.

What deliberately does not promote: thresholds measured on one person's stack, one operator's narration preferences, and any correction that encodes a private context. Promotion is for laws that survived a named signal on one install and are argued to generalize; the PR review is where that argument is made and lost.

### 6.7 The learning store is a data store from line one

Anything that captures operator text is a data store holding potentially sensitive material, and it gets the controls a data engineer would demand of one, from the first line of code, not as a hardening pass.

What it says. Every user-text store the skill writes (corrections.jsonl above all):

- is created with 0600 permissions, owner read and write only;
- is redacted before write: secret-shaped patterns (keys, tokens, passwords, bearer headers, high-entropy strings, national-identifier formats) are stripped or masked by the writing script, never post-hoc;
- has a retention limit, enforced by the same tooling that writes it;
- has a purge command that shows the count and deletes only on explicit confirmation.

One meta-law on top: no privacy claim about the skill is published without an executed test against planted secrets. Write a fake password, a fake API key, and a fake national ID into a session on purpose, then read the store and prove they are not there.

The failure behind it, and the reason this section exists: an adversarial audit of a comparable learning loop ran exactly that test, planted a password, an API key, and a national ID, and found all three persisted verbatim, in cleartext, in a world-readable 0644 file, with no retention limit and no purge command, directly falsifying a privacy claim that had already been published. Self-review never surfaced it; a refuter briefed to break the claim did. This is a proven failure class in exactly this category of tooling, not paranoia, and it is why the controls above are design inputs rather than backlog items.

The team context sharpens it: a single-operator install captures one person's words about their own work, while a team install's transcripts can contain colleagues' material they never consented to having scanned. BrotherSBE's posture: session capture stays local and excluded from the shared repo by construction, the PR-comment stream (already consented, already visible to the team) is preferred as the primary team correction source, and the privacy posture is restated and reviewed before any team rollout.

### 6.8 The benchmark freeze

What it says. The comparison set BrotherSBE is scored against, the reference implementations, the skeptic personas, the rubric metrics and their floor gates, is ratified once by the operator and then frozen. It changes only by explicit operator decision, recorded in the ratification file, never by drift, and never by the skill itself.

The reason is the oldest one in measurement: a system that can pick its own comparators will, over enough iterations, pick the ones it beats, and the record on this is not hypothetical. In one published evaluation family, deliberate gaming of the grading harness was observed on 30.4 percent of runs (https://metr.org/blog/2025-06-05-recent-reward-hacking/, single source). The weekly review's anchored scoring only means something if this week's anchor is last week's benchmark, unchanged. A rubric that quietly gains a friendlier metric, or a benchmark set that quietly loses its hardest member, converts the loop from improvement into flattery while every individual review still looks rigorous.

Mechanically: the benchmark set and rubric live in versioned files marked ratify-then-freeze in their own headers. The scoring tooling reads them from disk. A diff to either file outside a review, or inside a review without an operator sign-off line, is itself a finding at the next review. Baselines are re-measured per install, never inherited from another machine's record, because a frozen benchmark with someone else's baseline is a different kind of fiction.

That is the whole loop: hooks write what happened, the review reads it once a week, amendments earn their place with a named signal or get reverted, laws cross to teammates only through a reviewed diff, the store underneath it all is treated as the sensitive data store it is, and the yardstick holds still. Every piece is a file, a hook, or a check, which means every piece can fail visibly, and that is the property the whole design buys.

---

## Part VII: The intended architecture, file by file

This whitepaper precedes the code by design: the specification is ratified before the first commit, so this part is the buildable specification. The standing test for every mechanism below: it must be implementable as a file, a hook, a script, or a check. Anything that survives only as a sentiment is a defect to file.

The repository is flat and self-contained:

```
SKILL.md              the law
DIGEST.md             the law's shadow, injected at session start
STATE.template.md     the per-project fence registry format
RUBRIC.md             the frozen review metrics
PARITY.md             mechanics shared with BrotherModeUp
SECURITY.md           data flows, verifiable claims, the awkward part
README.md             the pitch, and what is deliberately absent
LICENSE               MIT, name only
tools/                hooks, telemetry, scoring, gate checks, the weekly review
memory-template/      the memory an install copies out and then owns
evals/                regression evals and the release gate
```

### 7.1 SKILL.md: the law file

The constitution a session loads on invocation: numbered sections, a precedence preamble naming which instructions outrank it, and a compaction recovery rule ordering a re-read of the load-bearing sections plus the live state file after any context loss, because laws must live on disk, not in recollection.

Two disciplines keep it a law file rather than a scrapbook. First, a hard size cap, enforced as a failing check in tools/sbe_score.py: consolidation merges or displaces existing text, never accretes, because a law file that grows without bound stops being read. Second, amendment discipline: the file is never edited directly. An observed weakness becomes one appended line in the pending-amendments note the same moment; amendments land through at most one consolidation pull request per review cycle; every amendment names the measured signal it should move; the next review compares strictly and reverts any change whose signal did not improve; rejected edits keep their reasons and are not re-proposed without new evidence. Every law carries a because clause naming the failure behind it.

### 7.2 DIGEST.md: session-start injection

A mechanical compression of the law, about a dozen lines, injected into context at every session start by the hook. Context is mortal: after a compaction, the digest is the part of the law guaranteed present. It is regenerated from SKILL.md in the same pull request as any law change; a hand edit to DIGEST.md is a defect by definition, because the file is generated output.

### 7.3 STATE.template.md: the five-field fences

The per-project running state format. Its core is the fence registry: no writer, human or agent, starts work in shared files without a fence line registered first. A fence carries the five-field contract (objective, output format, tool guidance, boundaries, termination) plus the file scope, agent and session ids, a lease TTL, an effort tier, and a runnable done-check. Fence before dispatch, never the reverse. A fence closes only with an inline evidence block: the exact command and its last lines. The registry line flips to LANDED in the landing commit itself; a registry in the sibling's operating history once listed four landed writers as live for days, which is how a dead line becomes a lie. The template ships with one worked closed fence, a backend fix traced end to end.

### 7.4 RUBRIC.md: the frozen metrics

Three floor gates and nine weekly metrics, ratified once and then frozen, because a rubric edited mid-quarter measures nothing. Two deviations from the sibling are structural. The alignment metric is based on review outcomes (approved versus changes-requested) and the deploy and incident record, not on how the output felt: this operator can verify directly, and an impression-based feed would let charm outrank correctness. And every baseline is re-measured on the installing estate, never inherited: the sibling's thresholds were measured on one machine and are not defaults for yours. NO-DATA is a legal score and is never a pass. One standing flag at the first review: any ledger still empty after its first live window is theater; the sibling's audit ruled empty scaffolding worse than absence.

### 7.5 tools/: the mechanical half

Every tool obeys four properties: standard library only; zero network; two exit disciplines by role, stated precisely because the difference is the trust architecture's teeth; and hooks write the ledgers, because a logging duty left to model memory is a defect. The exit disciplines: observability tools invoked by session hooks (telemetry, session start, autosave) exit 0 on every code path, so a broken diary can never block an engineer's work; gate tools (sbe_gate.py and the eval runner) exist to block, so they run advisory by default in a session (report and exit 0) and enforcing under a --strict flag that exits nonzero on any failed gate, and --strict is the mode CI runs. One tool, one truth, two consequences: a session gets told, a merge gets stopped. The record on the diary side is blunt: token telemetry collapsed within a day under voluntary logging and was complete once a hook wrote it.

- tools/sbe_sessionstart.sh: prints DIGEST.md into context, then a few lines of nags (overdue review, unprocessed corrections), an offline update check that reads git ref files as plain files, and the autosave recovery pointer after a compaction resume.
- tools/sbe_autosave.sh: at PreCompact, snapshots the entire working tree, untracked files included, to a private ref through a throwaway index; the branch, index, and working tree are never touched; nothing is ever pushed; a recover mode prints inspect and restore commands. The failure behind it: a multi-page deliverable existed only in a session scratchpad and was wiped.
- tools/sbe_telemetry.py: at SessionEnd, appends one line per session (tokens, tool calls, subagents, duration) to outcomes.jsonl. Appends are idempotent: the write is skipped when the last line for the session id is byte-identical, readers hash-dedup, and the done-check is firing the hook twice and diffing the ledger for zero growth. The sibling shipped without this and a quarter of its ledger was duplicate lines (36 deduplicated to 27). The same tool scans operator messages for correction candidates under the SECURITY.md regime: redaction, 0600 permissions, retention limit, purge command, from the first line of code.
- tools/sbe_score.py: the code-graded half of the weekly review, each check printing PASS, FAIL, or NO-DATA with its evidence inline; the model judges only the residue. It ports the sibling's checks (ledger coverage, fence hygiene, correction latency, review cadence, budget tags, law-file size) and adds the silent-failure lints: bare except, empty catch blocks, unchecked subprocess exit codes, conflict-skipping upserts with no logged skip count, and try-without-surface patterns. By ratified decision these lints are gate severity, never soft.
- tools/sbe_gate.py: the gate-check helpers, one subcommand per hard class. numbers verifies a numbers-manifest exists and re-runs the second derivation to zero drift before a figure ships; the case behind it is a filed financial model found to overstate a five year total 4.5x against its own components. migration verifies the forward and reverse migrations both ran against a restored copy of production-shaped data, row counts and timings captured as receipts. approval refuses changes on money and partner paths without a recorded, named human approval. ran refuses to mark any SQL or pipeline change done until its check actually executed, receipt attached, because agents claim runs that did not happen (https://martinfowler.com/articles/pushing-ai-autonomy.html).
- tools/WEEKLY-REVIEW.md: the roughly 20 minute procedure: code grades first, judge isolation, anchored scoring against last week, an anti-Goodhart spot check of two random claims, and at most one consolidation pull request.

### 7.6 memory-template/: what an install remembers

Copied out of the repository at install time and owned by the installer; the repository never holds anyone's memory.

- Overview.md: one paragraph of project state, build and test commands verbatim, and the invariants that must not break.
- Failures-Index.md: consulted before working in any area; one line per failure linking to its full note; the qualifying bar is costly or repeatable.
- Decisions.md: dated decisions with their reasons; settled findings do not reopen without new evidence.
- OUTCOMES.md: one human line per substantial run, with proportionality flags (OVERTHOUGHT, UNDERTHOUGHT, CARRIED-NOISE) and one sentence of lesson; the machine half lives in hook-written JSONL, where the model cannot flatter it.
- LEARNED.md: the team law file, and the point of the design. Each install learns locally; a local rule becomes a team law only through a reviewed pull request into LEARNED.md. Nothing an agent observed in one engineer's sessions changes a teammate's behavior without a human-approved diff. No silent behavior changes, ever.

### 7.7 PARITY.md: shared mechanics, tracked on purpose

One table: mechanic, origin, verbatim or adapted, and the reason. Fences and the five-field contract, the autosave snapshot, idempotent telemetry, the amendment pipeline, and the self-score cap port verbatim from BrotherModeUp (github.com/khalilmaaouni/BrotherModeUp). The narration register, the alignment feed, and the hard gate list are adapted; each row says why. The file exists for maintenance: when the sibling fixes a shared mechanic, the fix is portable in one read, and every divergence is a recorded decision instead of drift.

### 7.8 SECURITY.md: the claims and the awkward part

Negatives first, because that is this document's contract. The correction capture reads operator messages: that is the awkward part, disclosed rather than buried. A security review of the sibling's learning loop proved, by running the tool against a planted password, API key, and identity number, that its ledger stored them verbatim in cleartext at permissive permissions, falsifying a published privacy claim. BrotherSBE inherits the fix as a birth requirement: pattern redaction, 0600 permissions, a retention limit, and a purge command ship in the first commit, and no privacy claim is published without an executed test against planted secrets. Then the verifiable claims: zero network, with the grep to run yourself; what each hook does and does not spawn; a scope note separating BrotherSBE from the harness vendor's documented data handling; commit-pin guidance for teams that vet upgrades.

### 7.9 README: the pitch and the absences

A what-is-in-the-box table, the carrying ideas in a few lines each, the quick start, and a deliberately-not-here list: your memory (it stays in your copy of memory-template), credentials of any kind, network calls, and any claim of autonomy over production systems.

### 7.10 Operations: install in minutes

The clone is the installation. Wire four hooks (SessionStart, SessionEnd, Stop, PreCompact) from the complete settings block in the README; every hook fails silent and exits 0, so a broken hook costs telemetry, never work. Copy memory-template/ to a path you own. Run the verify commands, each printed beside its expected output; NO-DATA is the correct answer for a system with no history. Uninstall is deleting the clone and the four hook entries.

### 7.11 The first hour

Pick one node from the doctrine map in Part IV and run its cheapest entry. One node, not three. In ascending cost: the debugging loop on your next stack trace (two minutes, zero setup); ranking tests by failure rate on unchanged code from 30 days of CI results (20 minutes, one CSV); a partner feed header diff against the pinned contract (20 minutes, read-only); the alert estate sweep (30 to 60 minutes, read-only). Every entry is abandonable in an afternoon with nothing lost. The hour's output is calibration on your estate, worth more than any published average.

### 7.12 A normal week

For one engineer: sessions open with the digest injected and close with the ledger appended, neither requiring thought. Fences are registered even when working alone, because the fence's done-check is the cheap half of verification. The hard gates run inside the work, not after it: the second derivation before a number ships, the rehearsed reverse migration, the receipt before done. Once a week, about 20 minutes: run sbe_score.py, read the failures and the residue, score the rubric, land at most one law amendment as a pull request, and revert last week's if its signal did not move.

For a team: the shared repository carries SKILL.md and LEARNED.md, and every engineer's install learns locally against them. Promotions into LEARNED.md ride reviewed pull requests, with the fresh-context critic role played by the reviewer; unresolved disagreement escalates to the team lead. The correction stream changes substrate: pull request review comments are already shared and consented, so the weekly harvest reads them first and touches private transcripts only where an individual opts in. One named owner, or a rotation, runs the review; the sibling's design documents warn that an unowned review loop silently stops.

### 7.13 The eval bed: no release while an eval is red

The skill ships with evals/ built from real failure classes, generalized: a filed model overstating a five year total 4.5x against its own components; a total that recomputed only the final year of a five year span; a fan-out join inflating an aggregate with no error raised; a batch edit that aborted after the first file while its log recorded all ten fixes as applied; a session-end hook double-firing until a quarter of the ledger was duplicates. Each eval is a fixture, a planted defect, and an assertion that the corresponding gate catches it: the numbers gate must refuse the overstated total, the ran gate the unexecuted check, the telemetry append must not grow on the second fire.

The evals grade the gates, not the model's manners, deliberately: one evaluation family measured deliberate test gaming on 30.4 percent of runs (https://metr.org/blog/2025-06-05-recent-reward-hacking/, single source), and agents claim runs that did not happen (https://martinfowler.com/articles/pushing-ai-autonomy.html). A gate that can be talked past is not a gate, so the eval bed attacks each one mechanically. The release rule is a script, not a policy sentence: the check runs every eval, exits nonzero on any regression, and a release stays blocked while it is red. Fixtures are synthetic; nothing in the eval bed touches any live estate, and validation against a live warehouse is a named later milestone on a disposable account, never on infrastructure anyone depends on.
