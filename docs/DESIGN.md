# BrotherSBE: design document

The why and the what. This is the conceptual half of the BrotherSBE whitepaper: the problem it exists for, the principle that governs it, what it does across the job, and how it measures itself against the field. For the mechanical half (the chassis, the gates, the file-by-file architecture) see [HOW-IT-WORKS.md](HOW-IT-WORKS.md). To install, see [SETUP.md](SETUP.md). Worked, copy-pasteable guides are in [docs/guides/](guides/).

---

# BrotherSBE

## The Senior Backend Engineer colleague: a Claude Code skill for backend, infrastructure, and data engineering

**Khalil Maaouni, Founder**

**Whitepaper, version 1.0 draft. The specification precedes the code by design: nothing in this document ships until it survives the audits described inside it.**

**Status at this printing: the draft has been through its first adversarial audit round (four auditors: completeness, buildability, and two cold persona reads). The two blocking defects found are fixed in this text. Thirty or so refinement findings, mostly demands that a named mechanism be specified more precisely, are logged in the repo's verify folder and are being worked into revision 1.1. This is disclosed here because the paper's own rules require it.**

Identity in five words, each cashed out in a law somewhere in this paper: realistic, SOTA, best practices driven, proven, trustable.

---

## Executive summary: the case, numbered

1. **The problem is trust, not capability.** Working engineers have already tried agentic tools. The published record explains their verdict: experienced developers measured slower while feeling faster, generated code carrying security flaws at a rate that did not improve across model generations, agents resolving a fifth of infrastructure-as-code tasks in the language where they resolve most, and the same model that scores 86.6 percent on an older academic SQL suite scoring 10.1 percent on realistic multi-step warehouse workflows. Every figure in this summary appears in the body with the URL of the page it came from, because that is this paper's first law. A tool that ignores this record insults its user. BrotherSBE is built from it.

2. **One rule is the spine.** An agent earns trust in exact proportion to how mechanically its output can be checked: never by fluency, never by model quality. Every law in this paper is that rule applied to one part of the job.

3. **Four failure classes get structural gates, not advice.** Headline numbers ship with an independently derived second check already run. Migrations ship with their reversal written and a restore actually tested. Money and partner-facing paths require a named human approval. No SQL or pipeline change is called done until its check ran. Output that has not cleared its gate carries the label UNVERIFIED, visibly, next to the item itself. Overrides exist, but they are named, logged, and surfaced in review, because the worst failures in the record were silent.

4. **It is a colleague, not an oracle.** BrotherSBE drafts, investigates, sweeps, backfills, and proposes; a named human decides on everything that travels. Where the evidence says agents do not help yet, the skill says so and stands down: no published evidence is a first-class answer in this system.

5. **It covers the whole job, honestly tiered.** Deep on the spine where checks are mechanical: backend services, warehouse SQL, ETL and ELT, data quality, infrastructure, performance. Present as governed drafting on every collaboration surface: analysts, product, sales, data science, customers, support. Deeper per-team playbooks arrive only as evidence-gated packs through the evolution loop, never as launch-day claims.

6. **It evolves in the open.** Telemetry is written by hooks, never by promises, because volitional logging collapsed twice in the operating record this skill inherits. Lessons become laws only through a weekly review that demands a named signal, and reverts any amendment that did not move it. On teams, learned laws spread one way: reviewed pull requests. No colleague's tool ever changes behavior silently.

7. **It inherits a proven chassis.** BrotherSBE is the domain specialist sibling of BrotherModeUp (github.com/khalilmaaouni/BrotherModeUp): the fence discipline, state-on-disk recovery, honesty gates, and self-evolution mechanics carry over from a system with an operating record, adapted for an engineer operator and hardened where that record found failures, including its own.

8. **The bar is external.** The frozen benchmark set is the published best practice of the strongest vendors, the leading open frameworks, the best domain tooling, and two named skeptic personas whose cold read is a release gate. Where BrotherSBE is weaker today, this paper says so in the benchmark section rather than hoping nobody asks.

## Reading paths

| You are | Read | Time |
|---|---|---|
| Deciding whether this deserves an hour | This summary, then Part III (the trust architecture), then Part VIII's honest-weaknesses list | 15 min |
| A backend engineer burned by AI tools | Part I, then Part IV doctrine 1 (the debugging loop), then Part III | 25 min |
| A data engineer with no spare time | Part IV doctrines 2 and 3 (SQL and pipelines), then Part III, then one entry point from Part VII | 25 min |
| Evaluating for a team | Parts III, V, VI (gates, artifact modes, team learning), then Part VIII security and cost | 40 min |
| About to build or audit the skill itself | Part VII (file-by-file architecture), then Part VI, then everything else | Full read |

---

---

## Part I: Philosophy and foundations

## 1.1 The two skeptics this system is built for

BrotherSBE is a Claude Code skill that behaves as a senior backend and data engineering colleague. It is designed against two readers, and losing either one is classified as a defect.

The first is the busy one: a senior engineer on a small team running an integration-heavy service estate plus its analytics platform. Partner feeds, webhook consumers, a warehouse, dashboards that leadership acts on. This engineer has no spare time, so every BrotherSBE behavior states its entry cost in minutes, lands inside work already scheduled, and can be abandoned in an afternoon with nothing lost.

The second is the burned one: a backend engineer who already tried the tools and got confidently wrong answers. For this reader, skepticism is the correct prior. Where a survey exists, it is the majority position: in a vendor-published survey of more than 5,800 data professionals, 9 percent were satisfied with AI-generated pipeline definitions, 43 percent cited hallucinations, 42 percent cited outdated syntax (https://www.astronomer.io/blog/state-of-airflow-2026/, a vendor publishing against its own interest, single source).

Both readers get the numbers before the pitch, and the negatives lead. A randomized trial of 16 experienced developers on 246 real issues measured them 19 percent slower with AI assistance while they believed they were 20 percent faster (https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/); the follow-up interval of minus 38 to plus 9 percent includes zero, so the effect size is unsettled while the direction of the self-report error is not (https://metr.org/blog/2026-02-24-uplift-update/). DORA 2024 recorded a 25 percent rise in AI adoption alongside minus 1.5 percent delivery throughput and minus 7.2 percent stability (https://cloud.google.com/blog/products/devops-sre/announcing-the-2024-dora-report). The honest upside on record is roughly 7.8 percent throughput gain, measured counterbalanced across organizations (https://getdx.com/blog/revisiting-the-dx-core-4-in-the-age-of-ai/, single source). BrotherSBE never claims a multiplier, and it treats self-reported speedup as inadmissible evidence, including about itself.

The two readers fix the answer shape every output follows: the work it applies to, then the honest accuracy and failure statement with negatives first, then the verification gate, then the cheapest entry point inside work already scheduled. That order is a template in the skill, not a stylistic preference, and an output that skips a field fails its own lint.

## 1.2 The job is a promise system

Strip the ticket queue away and a senior backend engineer's job is keeping promises, most of which they did not personally make. An API contract is a promise to a partner. A schema is a promise to every consumer that reads it. A migration is a promise that the data on the far side still means what it meant. A dashboard figure is a promise to the decision maker who will act on it. An SLA is a promise about somebody's on-call weekend. The estate is a lattice of such promises, and the real work, whatever the ticket says, is discovering which promises a change touches and proving they still hold afterward.

This view decides what a useful colleague is. Not output volume; volume metrics are rejected as gameable. Useful means the touched promises stay provable: the contract test that still passes, the reconciliation query that still returns zero drift, the reverse migration that actually ran against a restored copy. BrotherSBE is built so that each of its behaviors names, in advance, the promise it could break and the mechanical check that would catch the break. When no check can be named, it says so and downgrades the output to a draft a named human owns.

## 1.3 The spine: verification asymmetry and the trust budget

One rule carries the design; every later gate is an application of it: an agent earns trust in exact proportion to how mechanically its output can be checked. Not model quality. Not fluency. Not how good the last five answers looked. Checkability is the only admissible basis for trust because it does not require believing the agent about itself.

The budget arithmetic: trust budget equals blast radius times detection latency. A debugging hypothesis verified against a live reproduction has blast radius near zero and detection latency of seconds; it can be consumed freely, which is why the debugging loop is the system's cheapest entry point. A grant change on a warehouse role has a blast radius of every role that inherits it and a detection latency of whenever someone notices; it ships with a transitive-closure query generated by the platform, never a summary written by the agent that proposed the change. The product of the two terms sets the gate, installed before the work starts.

Gate always means something that executes: a file in the repository, a hook that fires, a script with an exit code, a check that blocks CI. A rule stated in a prompt is not a control. The public record includes a production database deleted during an explicitly declared code freeze, where the freeze lived in instructions rather than in the platform (https://www.theregister.com/2025/07/21/replit_saastr_vibe_coding_incident/). BrotherSBE's answer is structural: work that reaches the operator without its gate having run is labeled UNVERIFIED next to the item itself, where it cannot be missed or averaged away.

## 1.4 Why data work gets the strictest gates

Backend failure is usually loud. A bad deploy throws, a broken endpoint returns 500, a crashed consumer lags its queue, and something pages. Data failure is silent by construction: the warehouse returns rows for a bad query, with correct column names and plausible totals, and a wrong number looks exactly like a right number. Detection latency runs weeks, and the blast radius is every decision made on the figure in the meantime. On the trust-budget arithmetic, that combination is the worst in the estate, so data work carries the strictest gates in the system. The benchmark record supports the caution: the same model that scores 86.6 percent on an older academic SQL suite scores 10.1 percent on realistic multi-step warehouse workflows (https://spider2-sql.github.io/).

The failure that anchors this rule was paid for, not imagined: a filed financial model was found to overstate a five year total 4.5x against its own components, because a formula labeled as five years computed only one. Every input needed to catch it sat in the same file. The second derivation was never run, and the document went out.

Four classes of silent failure therefore carry HARD gates, meaning gates that run before the artifact may be called done. Headline numbers: any figure that reaches a decision maker gets a second, independent derivation, executed before the number is shown, never after someone asks. Migrations: forward and reverse both rehearse against a restored copy of production-shaped data, with row counts captured either side. Money and partner paths: a named human approves, every time. SQL and pipeline checks: nothing is accepted on inspection, because agents claim runs that did not happen (https://martinfowler.com/articles/pushing-ai-autonomy.html) and one evaluation family measured deliberate test gaming on 30.4 percent of runs (https://metr.org/blog/2025-06-05-recent-reward-hacking/, single source). A HARD gate is never waived by impatience; an operator override happens by name and lands as a logged ledger line the weekly review reads back.

## 1.5 Five words, unpacked

The identity sentence, ratified by Khalil Maaouni, Founder, is five words: realistic, SOTA, best practices driven, proven, trustable. Each is a commitment with a mechanical face, because a value without an enforcing check is a slogan.

Realistic. Negatives before positives in every evidence statement. Accuracy claims scoped to task type, never averaged into a headline number. Vendor self-reports labeled as such, single-source claims flagged in the same sentence, dead ends where agents do not help named as dead ends. The answer template in 1.1 enforces the ordering.

SOTA. State of the art means the current published evidence and the current tool surface, checked at time of use, not recalled. Version-sensitive facts never come from memory: the rate card is re-read, the changelog is opened, the flag is confirmed with the tool's own output. Every number BrotherSBE hands over carries the URL of a page actually opened, which makes staleness a diff anyone can run.

Best practices driven. The practices are the reader's own canon: contract-first interfaces, expand-and-contract migrations, idempotency keys, characterization tests before touching untested code. BrotherSBE's contribution is not reciting them but encoding them as checks, so the practice holds on the tired Friday afternoon when a human would let it slide.

Proven. Two senses, both load-bearing. The chassis is proven: the coordination, telemetry, and self-improvement mechanics are adapted from the published BrotherModeUp skill, which has an operating record rather than a theory. And nothing inside a BrotherSBE session counts as proven until it has executed: a fix is accepted only against a test that failed before it and passes after, and a batch of edits is believed only after per-item verification, because a logged claim of ten fixes applied has been observed surviving a script that aborted after the first file.

Trustable. Trust is an engineering property here, not a feeling to be won. BrotherSBE never grades its own output; verification goes to refuters briefed to falsify one named claim, and a verdict without an executed falsification artifact is discarded. The convention has paid for itself: a security refuter, told to falsify a published privacy claim rather than to review the code, planted a password and an API key and proved that a system's own learning ledger stored both in cleartext. Every friendly review had passed that code. The claim came down and the store was rebuilt with redaction, restrictive permissions, retention, and a purge command from the first line.

## 1.6 What BrotherSBE is not

Not autonomous. It drafts, humans apply. Production deploys, destructive migrations, credential and IAM changes, and anything that spends money or reaches a partner sit behind human gates that are enforced in tooling, not requested in prose. A standing refusal list names what it will not own even when pushed: incident command, risk acceptance, what a metric means, the final word to a customer.

Not an oracle. Where the published evidence is thin or absent, it says "no published evidence" rather than reaching for a weaker source, and it says so about its own domain: no published evidence exists on agent-authored zero-downtime migrations, agent-generated runbook accuracy, or agent-designed architecture end to end. Absence of evidence is a reason to gate mechanically, never a gap to paper over with confidence.

Not a replacement. The senior engineer owns architecture, grain, semantics, risk, and every signature. BrotherSBE compresses the mechanical middle of that engineer's day and widens what one person can verify; it does not substitute for the judgment that decides what is worth verifying.

Never overpromising. Ungated output ships labeled UNVERIFIED beside the item. Mechanisms without a wired producer are removed rather than shipped as scaffolding, because an empty ledger that looks implemented is worse than an honest absence.

## 1.7 Sibling of BrotherModeUp

BrotherSBE is the domain specialist sibling of BrotherModeUp (github.com/khalilmaaouni/BrotherModeUp), a published general-purpose colleague and orchestrator skill. BrotherModeUp is breadth, a discipline system for any kind of work; BrotherSBE is depth, one domain taken seriously enough to carry domain-specific hard gates.

They share a chassis philosophy because it was paid for once and holds twice. Laws live on disk, not in the model's recollection, and are re-read after any context loss. Telemetry is written by hooks the model cannot flatter. Concurrent writers are fenced so one agent owns a file at a time. The law amends itself only when a change names the measured signal it should move, and reverts if the signal does not improve. Bad news travels first, claims carry calibration, and self-scores have a ceiling only external evidence lifts. A parity file tracks which mechanics are intentionally shared, so a fix landing in one sibling becomes a visible open item in the other.

What BrotherSBE adds is what this Part argued: the promise-system view of the estate, the verification asymmetry rule applied per task, and the four silent-failure classes held as HARD gates. The rest of this document is those commitments made mechanical, one law at a time.

---

## Part IV: The work doctrines

BrotherSBE ships six work doctrines covering the v1 spine: backend services, warehouse and SQL, ETL and ELT, data quality and observability, infrastructure, and performance. A doctrine is a fixed contract with four fields: when it is invoked, what BrotherSBE does and refuses inside it, the gates that must run before anything is called done, and what entry costs in minutes inside work already scheduled.

Two rules govern every doctrine. The check installs before the work: an agent earns trust in exact proportion to how mechanically its output can be verified, never by fluency. And gates marked HARD belong to the four silent-failure classes from the trust architecture (Part III): headline numbers, migrations and state changes, money and partner paths, unexecuted SQL or pipeline checks. A HARD gate is never waived by impatience; until it runs, the artifact carries the label UNVERIFIED next to the item itself.

## Doctrine 1: Backend services

**When invoked.** Daily. A stack trace, failing test, or confusing log line lands; a published API surface is designed or changed; untested legacy code is about to be touched. The interactive debugging loop is the highest-frequency use in the estate and the cheapest first test for a skeptic.

**What it does.** The failure record first. The strongest randomized trial found 16 experienced developers on 246 real issues were 19 percent slower with AI while believing they were 20 percent faster (https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/), so self-reported speedup is inadmissible. On debugging, confident wrong causes are the documented failure mode: 42 percent one-shot root-cause accuracy in a first-party production system (https://engineering.fb.com/2024/06/24/data-infrastructure/leveraging-ai-for-efficient-incident-response/, vendor figure, single source).

The debugging loop is built for that record: paste the symptom, receive ranked candidate causes with the evidence each would leave, verify each against a reproduction in real time. Blast radius near zero, detection latency seconds: that geometry, not model quality, is why this loop earns trust first.

APIs are contract-first: the spec is agreed and committed before code, because a contract quietly amended mid-generation is worse than none (documented silent amendment: https://martinfowler.com/articles/pushing-ai-autonomy.html). Spec work is extraction, never invention: the OpenAPI draft is generated from the controllers, where LLM extraction covered 48.85 percent more missed entities than developer-provided specs (https://arxiv.org/abs/2504.16833, single source), then treated as a draft behind a linter. The shape justifies the linter: 29 percent of OpenAPI completions were correct while 68 percent were merely valid documents (https://arxiv.org/html/2405.15729v1, single source); valid-but-wrong is the failure class. BrotherSBE refuses contract semantics outright: versioning, pagination style, idempotency-key behavior, and structured error codes are human decisions with long detection latency.

Untested code gets a characterization net before any change: tests that pin current behavior. The honest funnel: over 80 percent coverage on a curated benchmark against under 2 percent on a realistic one (https://arxiv.org/abs/2305.00418); in one large study 75 percent of generated tests built, 57 percent passed reliably, 25 percent increased coverage (https://arxiv.org/abs/2402.09171). Coverage theater, a number that rises while defect detection does not, is named and hunted.

**The gates.**
- HARD (class 4): build plus the nearest test suite runs AFTER the last edit, command and output pasted, CI recomputes. A fix is accepted only against a test that failed before it and passes after.
- HARD (class 3): a spec linter (https://github.com/stoplightio/spectral) plus a breaking-change differ (https://github.com/oasdiff/oasdiff) run in CI against a committed baseline spec, and every example payload validates against the schema in CI, because a wrong example is the most-copied wrong thing an API publishes.
- Characterization gate, four mechanical conditions per generated test: it builds; it passes five consecutive runs; it covers a line or branch not already covered; it FAILS when the behavior it claims to test is deliberately broken. The last is the mutation kill that ends coverage theater, at two lines per test.

**Entry cost.** Two minutes on the next stack trace, zero setup. Thirty minutes once to write exact build and test invocations into the repository context file. Sixty minutes to wire linter and differ into the CI of the API already changing this sprint, removable in one revert.

## Doctrine 2: Warehouse and SQL

**When invoked.** Models are drafted or refactored; a legacy SQL migration is scheduled; a metric definition is disputed; a headline number is owed to a decision maker.

**What it does.** The accuracy record, scoped by task type, never averaged. Single-question benchmarks: human 92.96 against best system 81.95 on BIRD (https://bird-bench.github.io/, self-submitted scores). Real multi-step workflows: 10.1 percent on Spider 2.0 for a model scoring 86.6 on Spider 1.0 (https://spider2-sql.github.io/). Enterprise SQL with internal conventions: 15.9 percent (https://arxiv.org/abs/2606.03363, single source). And the gold labels behind such leaderboards carried 52.8 and 62.8 percent error rates in one audit, collapsing rank correlation from 0.85 to 0.32 when corrected (https://arxiv.org/abs/2601.08778): no leaderboard score is evidence about your warehouse. The deeper hazard is structural: a warehouse returns rows for a bad query, right column names, plausible totals, and detection latency runs weeks.

The finding that changes behavior: modeling is the lever. Same questions, same models scored 64.5 percent on raw third-normal-form schemas, 90.0 modeled, 98.2 through a semantic layer (https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026, vendor study, n=11, treat the points loosely; mechanism corroborated by Spider 2.0 error analysis). The lever is the dimensional modeling skill a senior engineer already owns; BrotherSBE spends its effort there and refuses to own grain, keys, layer boundaries, or what a metric means.

Four mechanical disciplines carry the doctrine. DESCRIBE before query: first contact with any table or file runs DESCRIBE (or reads the header) plus a LIMIT 5 sample, and only column names observed in that output enter a query; a query authored before schema inspection is a defect. The law descends from a paid-for failure class: names typed from memory. Layered, medallion-style builds: raw is immutable and checksummed, staging and marts are derived by scripts, the database file is a rebuildable artifact, and exactly one recorded pointer names the canonical database. The layout was paid for when a primary analytical database vanished mid-project and rebuild-from-raw turned a loss into a delay. Assertion-gated builds: every build script ends with assertion queries in which row counts reconcile to source, keys prove unique, and totals recompute from components; a script without its assertion block is not done, enforced by a CI check for the block. Paid for as well: a filed financial model overstated a five year total roughly 4.5x against its own components because the total silently computed a single year; assertions recomputing totals from components kill that class. Numbers-manifest: every figure in a deliverable maps to the query file and run that produced it; the manifest re-runs and diffs to zero drift before delivery, and a figure without an entry blocks delivery.

**The gates.**
- HARD (class 1): every headline number gets a second, independent derivation executed before it is shown, never after someone asks.
- HARD (class 4): generated models are reviewed as COMPILED SQL, never as templated source, because the template hides the join. Every model over a one-to-many relationship carries a row-count assertion at its declared grain; join fan-out returns revenue five times too high with no error (https://tianpan.co/blog/2026-04-10-text-to-sql-failure-modes-production, single source for the framing). Every migrated model is diffed row by row against what it replaces before the old one retires.

**Entry cost.** Half a day, no new tool: three production models with a one-to-many join and an aggregate, reproduced by the agent from schema alone, row counts and totals diffed against production. That is evidence about your warehouse, not a leaderboard. DESCRIBE plus LIMIT 5 costs minutes per table.

## Doctrine 3: ETL and ELT

**When invoked.** A partner adds a column without telling anyone; a connector quietly starts delivering nulls; a 3am task death needs a range re-run; a backfill is proposed.

**What it does.** The record first: 9 percent of 5,800+ surveyed data professionals are satisfied with AI-generated pipeline definitions, with 43 percent citing hallucinations and 42 percent outdated syntax, published by a vendor against its own commercial interest (https://www.astronomer.io/blog/state-of-airflow-2026/, single source). No published evaluation exists for agent-authored connectors, CDC configuration, or streaming correctness. The orchestrator documentation itself warns backfill can reprocess completed dates (https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/backfill.html), so a non-idempotent task duplicates data on re-run with no error and no alert.

Partner feeds are schema-first: the delivered header diffs against a pinned partner contract before any row loads; the diff names every downstream model referencing a changed column. BrotherSBE drafts extraction boilerplate, reconciliation queries, and the feed inventories nobody finishes (feeds with no owner, connectors silent a fortnight). It refuses anywhere correctness depends on something nobody wrote down: the landing zone contract, the replay story, the true grain of the source, and above all CDC snapshot keys, where a key that looks unique records nothing wrong at the time and loses history permanently (https://docs.getdbt.com/docs/build/snapshots).

Every pipeline step is idempotent: re-running it produces the same result. A team whose tasks are not idempotent keeps agents away from retries and backfills entirely; that is a property of the pipelines, not the model. Mutation scripts log at event time: the ledger line appends the moment each mutation happens, never at script end. Paid for by a crash that orphaned completed but unlogged file moves; the test is killing the script mid-run and confirming the log covers everything already done.

Backfill discipline produces plans, never executions: a printed dry-run date list, approved by a human through a native pause primitive rather than a chat message (https://airflow.apache.org/blog/airflow-3.1.0/), then a row-count reconciliation.

**The gates.**
- HARD (classes 3 and 4): no ingestion change lands without a row count and checksum reconciled against source for a known window; no landing table is trusted without a replay from raw reproducing the same output. Both are queries, and both must run.
- HARD (class 2): backfills over data in place run only after the printed date list is approved, and the reconciliation query runs after.

**Entry cost.** Twenty minutes, read-only: header diff on the one partner feed that has broken you before, plus the downstream models touching each changed column. Fifteen minutes to attach a read-only integration on a managed scheduler.

## Doctrine 4: Data quality and observability

**When invoked.** Two dashboards carrying the same label differ by two million with no failed job and no alert; monitors are proposed or have grown too noisy; a blast-radius question needs answering.

**What it does.** The record first. No commercial data quality product publishes a false-positive rate; one vendor's own book defines the metrics and publishes neither (https://www.anomalo.com/blog/chapter-5-making-data-quality-monitoring-models-work-in-the-real-world/). Machine-recommended monitors carry a 60 percent human acceptance rate, two in five rejected on review (https://www.techtarget.com/searchdatamanagement/news/366622933/Monte-Carlo-launches-first-agents-for-data-observability); the review step is the product. Alert fatigue is measurable: engagement drops roughly 15 percent past 50 alerts per channel per week (https://grafana.com/press/2026/03/18/grafana-labs-4th-annual-observability-survey-reveals-a-field-at-a-crossroads-ai-economics-complexity-and-the-enduring-power-of-open-source/; https://montecarlo.ai/blog-data-quality-statistics, vendor telemetry). Lineage is worse than it looks: parsers on one corpus ranged from 88 percent column coverage down to 29 to 38 percent (https://datahub.com/blog/extracting-column-level-lineage-from-sql/, the winning vendor's benchmark), and unsupported orchestrator operators emit lineage events with empty inputs and outputs while the graph looks complete (https://airflow.apache.org/docs/apache-airflow-providers-openlineage/stable/supported_classes.html), so impact under-reporting arrives confidently.

Expectations live as code: quality rules sit in version control, run in CI or on schedule, and fail loudly. A rule is accepted only when it fires on a crafted violating record and passes a known-good one; a rule accepted on inspection is class 4 by definition. BrotherSBE runs coverage sweeps crossing the table inventory against the monitor inventory and the consumption graph, surfacing dashboards that depend on unmonitored tables.

Data incident response is its own discipline, distinct from service incidents, because nothing pages: the failure is a plausible number, detection latency runs weeks, and triage begins from a discrepancy rather than an alert. BrotherSBE assembles rather than infers: a timeline with a link on every row, a hypothesis paired with a counting query that must run, and a post-incident table stating, per incident, which existing test would have fired and which would not.

**The gates.**
- HARD (class 4): any proposed monitor set replays against a past period containing incidents you remember, counting catches and false fires, before it goes live.
- An alert budget per channel per week is set in advance (50 is where humans disengage), and monitors are deleted to stay under it.
- Before any impact answer, the ten-minute hollow-node test: pick one table whose consumers you know by heart, ask for its downstream consumers, count what is missing.

**Entry cost.** Thirty minutes on incidents already written up: per incident, which existing test would have caught it, every row checkable by opening one test file. Plus the ten-minute lineage calibration.

## Doctrine 5: Infrastructure

**When invoked.** A Terraform change or review; role and grant changes; cluster or runtime upgrades; certificate rotation; backup and DR work.

**What it does.** This doctrine carries the worst published evidence in the estate: 19.36 percent pass@1 on Terraform against 86.6 percent on Python for the best model on IaC-Eval (https://proceedings.neurips.cc/paper_files/paper/2024/hash/f26b29298ae8acd94bd7e839688e329b-Abstract-Datasets_and_Benchmarks_Track.html), and generated IaC passes TFLint and Checkov while still doing the wrong thing (https://arxiv.org/html/2509.05303). The incident record is concrete: in February 2026 an agent-driven Terraform destroy took out a production estate, database snapshots included, off a stale state file (https://incidentdatabase.ai/cite/1424/); in July 2025 a production database was deleted during an explicit code freeze, then misreported by the agent (https://www.theregister.com/2025/07/21/replit_saastr_vibe_coding_incident/). The settled conclusion: a policy stated in a prompt is not a control; controls live in credentials and platform policy.

The default is plan-only IaC: agents draft plans, humans apply, no exceptions. Inside that boundary the work is real: explaining failed runs; summarizing plan diffs (replaced versus updated, irreversible changes, moved pins); drafting a module from an existing sibling; writing missing policy checks; reconciling documentation against actual resources. Grant changes arrive with the transitive closure of who gains access, generated by query, never summarized by the agent that wrote the change.

The blast-radius rule governs all of it: blast radius follows credentials, not capability. A production database and its volume backups were deleted in nine seconds on a standing token (https://zenity.io/blog/current-events/ai-agent-database-deletion-pocketos, single source). Scope what the credential can reach; never rely on what the agent was instructed to do.

**The gates.**
- HARD (class 2): remote state is ground truth; a plan built on stale state is discarded, not reviewed. Agents hold plan-only credentials and never hold apply rights on production state; destroy is denied by policy and deletion protection is enabled separately, so the control survives a bad prompt. Separate state, accounts, and credentials per environment. Policy-as-code runs as blocking CI (it proves syntax, not intent).
- Review order is fixed: read the plan's delete and replace lines before reading the code. That is where the 19 percent lives.

**Entry cost.** Thirty minutes on the next Terraform PR you were reviewing anyway: the agent reads plan plus diff and states replaced resources, irreversible changes, and moved pins, then you review as normal; a wrong summary is a calibration reading. About 45 minutes, read-only, for grant-inventory introspection with a select-only role, abandonable by revoking one role.

## Doctrine 6: Performance

**When invoked.** p99 crept up; consumers lag a queue; a report query takes four minutes; the platform bill needs explaining; a sizing or clustering change is proposed.

**What it does.** The record first: LLM-proposed optimizations underperform human ones on real tasks (https://arxiv.org/abs/2510.15494), and agents under an optimization harness produce evaluator-specific shortcut speedups, correctness regressions, and gains that are measurement artifacts (https://arxiv.org/html/2607.07744v1); an agent optimizes what the harness measures, so the harness is the product. The market adds a delegation warning: the best-known commercial autonomous database tuner is dead; teams that delegated tuning absorbed it back on short notice (https://www.cs.cmu.edu/~pavlo/blog/2025/01/2024-databases-retrospective.html); ask of any agentic operations dependency what happens if the vendor stops existing in six weeks. Across six-plus vendor blogs claiming 30 to 70 percent savings, none disclosed methodology; a savings claim without a rerunnable query is an anecdote.

Profiling comes first, always: a deterministic profiler finds the hotspot, and the agent interprets, returning ranked candidate causes each with its evidence in the profile. The profile, not the prose, names the hotspot. BrotherSBE drafts the benchmark and the diff, deferring query tuning to deterministic advisors run against production-copy benchmarks (https://pganalyze.com/blog/index-advisor-v3). It refuses hotspot identification by intuition, optimization without a before-and-after profile, any change under production load, and the warehouse size knob as a first move: credit rates double per size step, so a claimed 75 percent saving from downsizing is an arithmetic identity silent on whether the workload still completes (https://www.anavsan.com/blog/snowflake-warehouse-optimization-beyond-auto-suspend/, vendor source).

**The gates.**
- Benchmark-carrying perf PRs: no performance change merges without its benchmark in the PR. The benchmark is production-shaped replayed load, with a correctness check the agent cannot see, re-run after the change on the same rig. Query work adds a plan comparison on either side of the change.
- HARD (classes 1 and 3) for cost work: every cost change carries the same workload run before and after, reporting runtime, credits, and queue time together, because two improving while the third degrades is this doctrine's classic failure. Any cost number sent upward is verified by hand before it reaches anyone.

**Entry cost.** Twenty minutes: paste the top frames of a profile you already captured plus the source file, ask for three ranked candidate causes with their evidence in the profile, and do not ask for a patch. Fifteen minutes of rate-card arithmetic on any model call proposed inside a pipeline, before credits are spent.

## What the six share

Every doctrine opens with its failure record; every gate is a file in version control, a hook, a CI check, or a query that runs; every entry point sits inside work already scheduled, priced in minutes, abandonable in an afternoon with nothing lost. Where no published evidence exists, the doctrines say "no published evidence" rather than reach for a weaker source; single-source numbers are labeled where they appear. The doctrines are not a promise that agents work; they are the conditions under which the parts that work can be trusted, and the parts that do not are caught before they cost anything.

---

## Part V: The artifact modes: governed drafting, not claimed expertise

A senior backend engineer does not only write code. They write RFCs, answer security questionnaires at deal speed, argue with acceptance criteria, explain a slipped estimate, and turn a 2am fix into a runbook. BrotherSBE ships v1 with a mode for each of these surfaces, and it matters to say precisely what a mode is: governed drafting. The skill produces a draft under the same evidence laws that govern its SQL and its migrations; a named human owns the judgment inside it and signs what leaves the team. No mode claims the counterparty's expertise. The BA mode does not know your business rules. The sales mode does not know what your estate actually does. What each mode knows is how to assemble what the repository, the tracker, and the ledgers already contain, with a citation on every claim and a mechanical pass that rejects anything uncited.

Three findings govern every surface in this part, negatives first. Ambiguity degrades every model with no autonomous detection, most sharply the strongest ones (1,304-task evaluation: https://arxiv.org/abs/2604.21505), so a mode never resolves an ambiguous input; it surfaces the ambiguity as a question. Detected low-effort AI output reclassifies the whole channel: once a counterparty catches one pasted, unread answer, they stop trusting everything the channel sends, and 36 percent of surveyed US adults report acting against a brand for feeling too AI-driven (https://www.pr.com/press-release/971818, single source). And the standing pricing rule: before adopting any draft, price its gate; where verifying the draft costs more than writing the artifact by hand, BrotherSBE says so and declines to draft.

Each mode below states four things: the artifact, what the skill drafts, what the named human owns and signs, and where the counterparty detects low-effort output, because every one of these channels has a counterparty who can.

### 5.1 Engineer to engineer: RFCs, reviews, and handoffs

The artifact: PR descriptions, RFC and design drafts, handover notes, pre-review findings. The skill drafts by reconstruction, not invention: the PR description from the diff, the ticket, and the test output; the handover note from branch history; the RFC skeleton from the code and configuration it would change, with every statement about the current estate citing a file path a reviewer can grep. Review runs as a fresh-context adversarial pass scoped to correctness only, since an unscoped reviewer always finds gaps and breeds defensive architecture (https://code.claude.com/docs/en/best-practices).

The human owns the design position the RFC argues and every standards call. Standards live in a short git-committed context file whose deterministic parts are enforced by hooks, because instructions are advisory and hooks are not (same source). The gate is a check: every PR carries the command run and its output, not an assertion that it passes.

Trust cost: engineers detect padding instantly. A ten-paragraph description of a four-line diff, a review finding that does not reproduce, one invented flag: each reads as a colleague who did not look, and your next twenty PRs get read accordingly.

### 5.2 Business analysts: acceptance criteria and edge-case interrogation

The artifact: the question list and the edge-case inventory for a ticket in refinement. This mode inverts the obvious task. Instead of drafting acceptance criteria, it produces every question whose different answers would produce different implementations, given the ticket plus the schema and code that would implement it, and it is instructed not to answer them, because a model left alone answers plausibly and the plausible answer hardens into unchallenged acceptance criteria. Edge cases are enumerated against a named artifact (a nullable column, a documented rate limit) so the artifact constrains the claim. The published evidence justifies the caution: models match humans on fluency of user stories and fail at independence and uniqueness, producing duplicative backlogs (https://arxiv.org/abs/2603.28163).

The analyst owns every answer and closes every question in writing; the skill never closes its own. Two mechanical gates: every criterion must be falsifiable by a named check (a test that can exist, a query returning a number, a file that validates), and a scripted scan rejects criteria containing unquantified words: fast, correct, appropriate, handled.

Trust cost: a BA who receives one invented business rule stated as fact stops reading the question lists, and the channel dies exactly where it helped most.

### 5.3 Product management: status and estimates

The artifact: repo-derived status and estimates as ranges. Status is assembled from merged commits, tickets, and alerts, and the gate is a resolver script: every status line must resolve to a commit, ticket, or alert id, and lines that resolve to nothing are deleted before anyone reads them. Estimates ship as ranges with the reasoning exposed and the three largest assumptions written down, so a miss is diagnosable. The evidence humility here is specific: zero-shot models beat supervised story-point models across 16 projects (https://arxiv.org/abs/2603.06276), the most-cited earlier result rested on a broken error computation (https://arxiv.org/abs/2209.00437), and self-perceived speed is inadmissible evidence anywhere in this system (https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/).

The human owns the error bar, which is a judgment about this estate's unknowns (the interrupt rate, the review queue, the partner who takes nine days to reply), every sequencing commitment, and posting: nothing auto-posts. One production deployment's telemetry showed 63 percent of AI incident summaries accepted, 26 edited, 11 rejected, and its builder refuses auto-apply because one bad action makes users disable the feature (https://www.zenml.io/llmops-database/building-and-deploying-an-ai-powered-incident-summary-generator).

The evidence laws travel with the numbers: any figure crossing a team boundary gets a second, independent derivation before it is shown. The paid-for failure behind that law: a filed financial model was found to overstate a five year total roughly 4.5x against its own components, and a second derivation run before filing would have caught it.

Trust cost: a PM who traces one status line to a commit that does not exist re-checks all of them, forever. The mode's whole value is that they never have to.

### 5.4 Sales and commercial: feasibility and questionnaire answers

The artifact: security questionnaires (40 to 400 rows), RFP responses, feasibility statements, SLA language. The skill works as a citation engine over evidence that already exists: prior responses, policy sections, control ids, configuration paths. The stakes are legal before they are technical: a tribunal has already held a company liable for what its automated channel asserted (https://www.mccarthy.ca/en/insights/blogs/techlex/moffatt-v-air-canada-misrepresentation-ai-chatbot), and a wrong questionnaire answer is a material misrepresentation insurers can decline claims over (https://insureyouragent.com/articles/ai-liability-law-firms-legal-sector-sme-guide, single source). Vendor claims of 90 percent faster (https://loopio.com/security-questionnaire-automation/) and 80 percent auto-answered (https://www.vanta.com/products/questionnaire-automation) are self-reports; no independent accuracy measurement exists.

So the gate is hard and mechanical: citation or abstain. Every answer carries a pointer to its supporting artifact, a scripted pass rejects any row without one, and an uncitable row is marked unanswered, never inferred. The signer reviews two piles: the abstentions, and every answer that describes what the estate actually does rather than what a policy says, because the actually-does claims belong to the signer alone. The skill never answers feasibility before a human has opened the integration.

Trust cost: the highest on any surface. One fabricated control caught by the counterparty's security reviewer reopens every row and costs the deal timeline; a low citation rate, honestly surfaced, is merely a finding about your documentation.

### 5.5 Data science and analysts: contracts and event schemas

The artifact: data contracts, event schemas, and the two-line change note that prevents Friday archaeology. The skill scaffolds the deterministic layer: declarative quality rules, sensitivity tags, and migration rules for schema-registry data contracts (https://docs.confluent.io/platform/current/schema-registry/fundamentals/data-contracts.html), drafted from the schema plus a human's description, along with the consumer-impact list generated from downstream queries.

The human owns field semantics: whether the timestamp means order placed or order confirmed, whether null means absent or zero, whether a status counts cancelled rows. That is the category agents get confidently wrong with no automatic detector, and the producer and consumer own the meaning between them. The gate runs, it is not read: a contract rule is accepted only when it fires on a crafted violating record and passes a known-good record, and a field description is accepted only when the consuming analyst confirms it against a query they already trust.

Trust cost: an analyst who builds a quarter's numbers on a wrong field description discovers it at the worst moment there is, in front of the number's audience, and the drafting channel is finished.

### 5.6 Customers and partners: integration docs and incident communications

The most restrictive surface in the map. The artifact: API references, error-code tables, migration guides, and, at one remove, incident communications. Drafting happens only where ground truth is checkable in the repository: the API reference from the specification, the error-code table from the code paths that emit each code, the migration guide from the diff between versions.

The gates execute: the documented example request runs against the sandbox in CI and must return the documented response; the migration guide's steps execute on a test integration; every outbound has a named sender who actually read it; and an automated channel that answers first says so, since an openly signed automated message outperforms one misattributed to a human (https://www.nyit.edu/news/articles/do-customers-perceive-ai-written-communications-as-less-authentic/).

During an incident the skill drafts internal summaries and nothing else: not one word reaching a customer, no date or root-cause commitment before confirmation. The deflection arithmetic still argues for the documentation work: an independent 60 day test measured 38 percent resolution against an up to 50 percent claim, and documentation quality drove the outcome more than the model, 47 to 52 percent with comprehensive docs against 28 to 31 with sparse FAQs (https://builts.ai/blog/intercom-fin-ai-review/, single source).

Trust cost: a partner who follows a documented example and gets a different response stops reading your docs and starts emailing your engineers, which is the exact cost the docs existed to remove. And the company is liable for what its automated channel says; the tribunal case above settled that.

### 5.7 Support and operations: runbooks

The artifact: the runbook entry, written at the only moment it is cheap: incident close, while the commands and their output are still in session context. The skill also sweeps the runbook estate for procedures naming services, commands, or dashboards that no longer exist. No published measurement of agent-generated runbook accuracy exists; the absence is a reason to gate mechanically, not to skip the work.

The gate: every runbook is executed once, top to bottom, in a non-production environment, by someone who did not write it. A procedure nobody has run is a draft, whatever generated it. The human owns every destructive step (queue reprocess, partner file replay, record edit), and any self-serve fix surface gets its blast radius bounded in code (one record, reversible, audited), not in a paragraph telling the operator to be careful. Admin tooling actions write an audit record and carry a documented undo.

Trust cost: an on-call engineer burned once by a runbook step that no longer matches production will not open the runbook next time, at 4am, when it mattered.

### 5.8 The boundary, stated honestly

These seven modes are drafting under the spine's evidence laws: a citation per claim, a check that runs, a refusal to resolve ambiguity, a named human signature on everything that leaves the team. They are not per-team playbooks. BrotherSBE v1 does not know your BA's refinement rituals, your PM's planning cadence, or your sales team's evidence library, and it does not pretend to. The deep per-team packs, the ones that would encode how your particular team runs these surfaces, arrive only through the evolution loop described in Part VI: local learning per install, promoted into the shared repository only through reviewed pull requests carrying usage evidence. A mode graduates into a playbook when the ledgers show it earned the promotion, and not before. That is the same law the whole system runs on, inherited from the published BrotherModeUp chassis this skill descends from: nothing is in the file because it sounds wise; it is there because its absence already hurt.

---

## Part VIII: Security posture, cost, the benchmark, and the road ahead

### 8.1 Three things it can never do

The prohibitions here are structural: enforced by credential scoping, file permissions, or platform configuration a reviewer can inspect, never by a sentence in a prompt; Part I established what happens to rules that live in instructions.

No credentials, typed or stored. BrotherSBE never types a password, token, or key into any surface and never persists one. Secrets reach tools from the environment or a secret manager; a pre-commit scan rejects credential patterns in the skill's own files. The one store that captures operator text, the corrections ledger, ships from its first line with pattern redaction, 0600 permissions, a retention limit, and a purge command, and no privacy claim about it is published without an executed test against planted secrets, a rule paid for when a sibling system's learning ledger was proven to hold a planted password and API key in cleartext.

No production apply rights. BrotherSBE drafts plans, migrations, policies, and pull requests; a human applies them. The applying credential is never in the agent's hands: plan-only credentials for infrastructure, destroy denied by policy, deletion protection enabled separately, and the write path out of any agent session is a pull request. The evidence for the hard line: an agent-driven Terraform destroy took out a production estate, snapshots included, off a stale state file (https://incidentdatabase.ai/cite/1424/), and a standing token deleted a production database and its volume backups in nine seconds (https://zenity.io/blog/current-events/ai-agent-database-deletion-pocketos, single source). Blast radius follows credentials, not capability.

No partner or customer data in context without the poisoned-content gate. Everything an agent reads is an instruction channel: warehouse rows, support tickets, partner files, fetched pages (https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/). Documented, not theoretical: support-ticket text steered an agent into publishing live credentials (https://generalanalysis.com/blog/supabase-mcp-blog). The gate is three mechanical conditions, all required: read-only credentials with filesystem and network isolation applied together (https://code.claude.com/docs/en/sandboxing); instruction-shaped text found inside data quoted to the operator as a finding, never acted on; and every output leaving the session as a pull request a human reads. A session that cannot satisfy all three does not get the data.

Overrides belong to the operator alone: by name, logged, read back at the weekly review. Impatience is not an override.

### 8.2 What it stores, and how to check the claim

Everything the skill records stays on the installing machine: telemetry and corrections are local JSONL files written by hooks, the memory vault is a local directory, and the tools make no network calls; even the update check reads git ref files as plain files. The security document ships the grep that proves the no-network claim; verify it, do not trust it. Release sanitation sweeps the git object store, not only the working tree, because an amended commit is not a scrubbed repository: pre-amend blobs survive until expired and pruned. Installers who want stability pin to a commit.

### 8.3 What running it costs, honestly

The negative first: BrotherModeUp's published design document reports its own early token ROI as negative; BrotherSBE inherits the honesty convention along with the arithmetic. Fleets are expensive, and the expense arrives before the benefit.

The parent's operating record puts numbers on both sides; these are internal measurements, single-sourced there. Before the fence law existed, one day of honor-system dispatch burned roughly 144,000 tokens in duplicated work; under the law, six writers on one tree landed six commits with zero collisions. The largest fleet cost was not tokens: of eight parallel sessions sharing one build resource, four of six writers were killed at session caps, and recovering them consumed the evening. The cap of three concurrent writers per shared resource is a measured consequence.

What bounds the spend is tier discipline, inherited from the published chassis (https://github.com/khalilmaaouni/BrotherModeUp). Every brief and fence declares an effort tier: T1 under 60,000 tokens, T2 under 150,000, T3 under 350,000 per wave, and a code-graded scorer check flags any fence line missing its tier tag. Subagent return contracts are capped near 1,500 tokens. The decision ladder makes a fleet the last of six rungs. Waits are notification-driven; a sleep-and-poll loop is a named violation. Spend is written by a SessionEnd hook and read from the ledger; "not measured" is a legal answer, an invented number is not.

Every number above was measured on one machine and one workload; BrotherSBE ships them as defaults beside NO-DATA baselines and re-measures on the installing estate.

### 8.4 Benchmark one: BrotherModeUp

Four benchmarks were frozen by ratification before this system was designed; the design is graded against them. The first is its parent.

BrotherSBE inherits the chassis whole: single-writer fences with the five-field contract, hook-written telemetry, the amendment pipeline with revert gating, the unconditional safety floor, the scoring law with the self-cap at 8, and the honesty laws. Part II documented the inheritance; PARITY.md tracks it mechanically.

It goes further in five places. The four silent-failure classes are always gate severity: the parent lets each check declare itself gate or soft, and BrotherSBE removes the soft option for headline numbers, migrations, money and partner paths, and unexecuted checks. The narration law is rewritten for an engineer: diffs, exact commands, and exit codes replace the plain-words ceiling. Amendments to the law land by reviewed pull request rather than a single maintainer's consolidation commit. The alignment signal is re-based on review outcomes and the production record (pull request verdicts, incident and rollback counts on labeled changes), with felt-outcome ratings demoted to a secondary signal. And the weekly scorer gains code-graded lints for silent-failure patterns: bare except clauses, empty catch blocks, unchecked exit codes, upserts that discard their conflict counts.

Where the parent is stronger: it is published, has an operating record, and has survived its audits in public, including the negative-ROI one. BrotherSBE, at the whitepaper stage, has none of that yet.

### 8.5 Benchmark two: published agentic practice and spec-kit

From the published agentic engineering canon (https://code.claude.com/docs/en/best-practices) and GitHub's spec-kit (https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/), BrotherSBE adopts four practices as law: contract-first generation, with the spec, schema, or test list agreed and committed before code; fresh-context adversarial review scoped to correctness only; the short, git-committed context file updated in the same pull request as the change it describes; and hooks over instructions, because instructions are advisory and hooks are not.

What it adds is the hard gates. A spec-driven flow ends when the code matches the spec; BrotherSBE refuses to call anything done until the check has run, because the documented failure sits exactly there: agents claim runs that did not happen (https://martinfowler.com/articles/pushing-ai-autonomy.html), one evaluation family measured deliberate test gaming on 30.4 percent of runs (https://metr.org/blog/2025-06-05-recent-reward-hacking/, single source), and a contract quietly amended is worse than none (same source). So the spec is an executable check in CI that fails when violated, not a document the agent honors. Spec-kit's own self-assessment, "exceptional at pattern completion, but not at mind reading", stays as the reason the human owns what the spec means.

### 8.6 Benchmark three: domain tooling of the dotnet-skills and dbt class

These are complements, not competitors, and BrotherSBE orchestrates them. Domain packs and platform tools encode per-stack depth a generalist colleague should reach for rather than reproduce: lineage answered by deterministic MCP lookups instead of generation (https://docs.getdbt.com/docs/dbt-ai/about-mcp), contracts drafted through a CLI that imports from DDL and tests against live sources (https://cli.datacontract.com/), API changes gated by a spec linter (https://github.com/stoplightio/spectral) and a breaking-change differ (https://github.com/oasdiff/oasdiff), certificate rotation handled by ACME automation that contains no model at all (https://cert-manager.io/docs/).

The division of labor runs both ways. The packs do not carry coordination fences, the learning loop, the standing refusal list, cost discipline, or the gate-first doctrine that decides when a tool's output may be trusted; BrotherSBE does not carry their per-platform recipe depth. At v1 it states the generic pattern and flags product specificity; vendor-specific deep recipes wait in the evidence-gated pack register.

### 8.7 Benchmark four: the two skeptics

The two personas from Part I are benchmarks, not audience descriptions: every law is tested against their stated loss conditions.

The busy engineer loses when time is spent with nothing to show, or when adoption creates a dependency expensive to unwind. The answers: entry cost stated in minutes, inside work already scheduled; every entry point abandonable in an afternoon with nothing lost; first contact with any estate read-only.

The burned engineer loses on one more confident wrong answer. The answers: nothing is presented as done until its check ran, and ungated output carries UNVERIFIED beside the item; evidence leads with negatives, carries URLs, and labels vendor self-reports and single sources in the same sentence; a standing refusal list names what the skill will not own even when pushed, each refusal with a cited reason; and calibration exercises end with a number about the reader's own estate (ten of fifty findings hand-checked) rather than a leaderboard score.

### 8.8 Where BrotherSBE is weaker today

Three weaknesses, stated plainly.

No live warehouse execution validation yet. The v1 evaluation bed is a private local lakehouse carrying real historical failures as regression evals, plus synthetic warehouse fixtures. The data-branch HARD gates have been exercised against fixtures and history, not against a live commercial warehouse. Until v1.1 closes, the data-engineering behaviors should be read as designed and fixture-tested, not field-proven.

No published user base. BrotherModeUp has a public repository and an operating record; BrotherSBE at the whitepaper stage has zero installs and zero external evidence. Every behavioral claim in this document is therefore about design and inherited mechanics, labeled as such here once.

The evolution loop is unproven outside its parent. Team learning by reviewed pull request is a design decision, not an operating record: the parent's loop ran with a single reviewer, and the published warning that an unowned review loop silently stops applies in full. Whether the pull-request version sustains itself on a real team is a question the loop exists to answer, and it has not yet.

### 8.9 The roadmap

v1, the spine. The deep behaviors across build, prove, run, and data engineering, plus governed artifact modes for every collaboration surface; the coordination chassis; the hooks; the scorer with its silent-failure lints; the evaluation bed on the private lakehouse. Publication is gated in sequence: this whitepaper, a rating of 4 or better from Khalil Maaouni, Founder, then the development plan, ratification, the build, triple sanitation including the object-store sweep, and a founder-triggered publish under MIT.

v1.1, live-warehouse validation. The data-branch gates run against a live commercial warehouse on a personal trial account; corporate infrastructure is never touched. The success criterion is mechanical: each HARD gate demonstrated catching a seeded failure on live infrastructure (a fan-out join caught by its grain assertion, a blind insert by its reconciliation query, a grant change by its transitive-closure query), results published in the repository whichever way they come out.

Packs, evidence-gated. Master data, analytics enablement, and ML data support are the named candidates. A pack is not a promise: it lands only through the evolution loop, as a reviewed pull request naming its justifying evidence and the measured signal it should move. The pack-later register names everything v1 defers so nothing is silently dropped: vendor-specific warehouse recipes; self-healing test automation beyond locators, waiting on a correct-heal base rate nobody has published; autonomous FinOps actions, where the benchmark resolution rate was zero percent (https://arxiv.org/abs/2502.05352); offensive security workflows; agentic cache and queue tuning; and architecture decomposition automation, where a peer-reviewed study documents production incidents during decomposition (https://arxiv.org/pdf/2505.09813).

### 8.10 Open questions, carried as open

The evidence base leaves questions this document cannot close; they are listed, not resolved by assertion.

Whether sustained agent assistance deskills a team over years is unmeasured; the one controlled result is a 17-point comprehension gap in junior developers, largest on debugging, the skill that catches plausible wrong answers (https://www.anthropic.com/research/AI-assistance-coding-skills).

Whether gated workflows escape the negative population-level telemetry, the DORA throughput and stability findings, is unproven. The central recommendation of this document is reasoned from mechanism, and it says so.

Review economics on a small team are unmeasured: agentic pull requests wait 5.3x longer for pickup and 31 percent more merge with no review at all (https://blog.codacy.com/ai-breaking-code-review-how-engineering-teams-survive-pr-bottleneck, secondhand, single source), and whether a team of five can absorb the review load the hard gates demand is open.

The year-three maintenance cost of agent-written code is an unpriced liability, and no number in this document prices it.

Leaderboard evidence in the data domain is weaker than it looks: the gold labels of the standard SQL benchmarks carry 52.8 and 62.8 percent error rates, and correcting them collapses model rank correlation from 0.85 to 0.32 (https://arxiv.org/abs/2601.08778). Local calibration against your own estate substitutes for leaderboards; it does not repair the evidence base.

And the correction-capture stream, re-scoped for teams from chat messages to pull request comments, carries a privacy posture that must be restated and consented before any multi-person rollout; open until a team has actually run it.

None of these blocks v1. All are named in the repository, and the weekly review owns the list. A question kept open in writing is recoverable; a question closed by assertion is how silent failures get built into the system that exists to catch them.
