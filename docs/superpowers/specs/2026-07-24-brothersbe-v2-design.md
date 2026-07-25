# BrotherSBE v2: design specification

**Khalil Maaouni, Founder. 2026-07-24. Status: awaiting approval. Nothing is built until this is approved.**

## 1. What went wrong in v1, precisely

v1 shipped a verification system: four hard gates, an eval bed, lints, CI wiring. All of it works and all of it survives. But verification is the last mile of engineering, and v1 treated it as the whole road. A colleague who only checks your work at the end has skipped every phase where the expensive mistakes are actually made: understanding the purpose, mapping the process, choosing the architecture, modeling the data.

The missing foundation, named exactly: architecture design and recommendation, question-and-answer clarification at critical phases, data modeling and data architecture, source-system mapping with failover and recovery, technology mapping, professional diagrams, and laws deterministic enough to be controls rather than preferences.

v2 builds the road. The backend is the bedrock of every capability, product, solution, and analysis a business runs, so the skill that supports it has to start where the bedrock starts: with purpose, then process, then structure.

## 2. The order of operations (the spine of v2)

Every engagement runs in this order, and each stage gates the next.

**Purpose (business analysis).** What is this for, who needs it, what does success look like, what breaks if it is wrong, what is explicitly out of scope. No design starts while the purpose is unstated.

**Process.** The workflow as it exists and as it will exist: actors, steps, triggers, decision points, exception paths, and the handoffs between systems and people. A process map precedes an architecture, because an architecture is a machine for running a process.

**Architecture.** Shape decided against named criteria, with alternatives judged and a recommendation stated. Reliability, repeatability, and coherence are design properties chosen here, not bolted on later. Technology map, source systems, failover, redundancy, recovery.

**Data.** Conceptual, then logical, then physical. Relationships, cardinalities, keys, attribute roles, systems of record, historization. The engineer lens, then the analyst lens, then the scientist lens.

**Expression.** Diagrams as code and documentation a human follows without effort, sized to the difficulty of the task, brief by default.

**Verification.** The v1 engine, unchanged in substance, now checking design artifacts as well as code.

## 3. The deliverable: a design dossier

A dossier is a set of numbered, versioned artifacts under `design/<project>/`. Each has a template, a completeness rule, and a gate. Which artifacts exist is decided by the tier.

| # | Artifact | Completeness rule (mechanically checkable) |
|---|---|---|
| 00 | Intake and tier | Five scored answers present, tier computed, any override named and logged |
| 01 | Purpose brief | Problem, users, success criteria, explicit non-goals, what breaks if wrong |
| 02 | Process map | Every step has an actor, a trigger, and an exception path; every handoff names both sides |
| 03 | Architecture decision record | At least two rejected alternatives, the criteria that decided it, consequences, and what would flip the decision |
| 04 | Technology map | Every component names its technology, its owner, its failure mode, and its recovery path |
| 05 | Data model | Conceptual entities with meanings; logical relationships with cardinality and optionality; every entity has a system of record; attribute roles assigned; historization stated |
| 06 | Diagram set | Tier-required diagrams present, every node named, every edge labeled with what flows and how, no orphan elements |
| 07 | Verification plan | Every claim the design makes names the check that will prove it |

The human approves each artifact before the next begins. An artifact that fails its completeness rule is not approved, and the failure names the missing field.

## 4. The tier: how ceremony gets sized

Intake asks five questions with objective answers:

1. Does this change a data model, an API contract, or a file interface others depend on?
2. Does it cross a service, system, or team boundary?
3. Is it reversible in under an hour?
4. Does it touch money, partner data, personal data, or production state?
5. How many downstream consumers break if it is wrong (none, some, many)?

| Tier | Trigger | Dossier |
|---|---|---|
| T0 trivial | Reversible, no boundary crossed, no dependents | None. Do the work. |
| T1 change | One boundary or a few dependents | One page: purpose, approach, risk, the check |
| T2 feature | Contract or model change, or many dependents | 01, 02, 03, 05 (delta), 06 (two diagrams), 07 |
| T3 system | New system, or money/partner/personal data, or irreversible | Full dossier, alternatives judged, technology map, recovery design |

An engineer may override the tier in either direction. The override is named and logged, and appears in the weekly review. This is the mechanism that keeps a one-line fix from generating six documents, and it is the direct answer to "brief always."

## 5. How architecture gets decided

For each shape question, BrotherSBE holds a decision table with named criteria and editable default thresholds. The consultation (asking the engineer about their context) is the intake to the table, not a replacement for it.

**The shape question** (monolith, modular monolith, services, event-driven) is scored against: number of independently deploying teams, deployment independence needed, consistency requirement, read and write asymmetry, failure isolation requirement, operational maturity (on-call, tracing, CI), and data coupling. A four-person team with no on-call and strong consistency needs does not get a microservice recommendation, and the table says why.

**The other tables**: synchronous versus asynchronous integration, shared database versus database per service, orchestration versus choreography, consistency model, caching strategy, and the failover posture (active-active, active-passive, backup and restore) against a stated recovery time and recovery point objective.

Every table produces the same output: a recommendation, a first and second alternative with the criteria that separated them, the consequences accepted, and **what would flip this decision**, so the record stays alive as the estate changes.

Thresholds ship as defaults and are re-measured on the installing estate. A team that disagrees with a number changes it in a reviewed pull request.

## 6. How data gets modeled

**Conceptual.** Entities, meanings, identities, business rules, in plain language, no technology. Derived from the purpose brief and the process map.

**Logical.** Relationships with explicit cardinality and optionality; keys and identity strategy; attribute roles (identifier, descriptor, measure, foreign key, temporal, status); normalization decisions with their reasons; historization and slowly-changing strategy; and the source-system map naming, for every entity, its system of record, its refresh contract, and what happens when that source is unavailable.

The three lenses apply here, in this order, each a checklist against the logical model:
- **Engineer**: can this be loaded reliably, idempotently, at volume, and recovered after a failure?
- **Analyst**: can the real questions be answered without heroic joins, and is every grain and metric unambiguous?
- **Scientist**: is history preserved, is leakage prevented, are features derivable?

**Physical.** Engine-specific types, indexes, partitioning, clustering, constraints, and the migration path with its reverse.

Gate: no physical model while the logical model has an unspecified cardinality or an entity with no system of record.

## 7. Diagrams and documentation

Diagrams are code (Mermaid), committed with the design, diffed in review, rendered by the platform. Required set by tier: T1 one context diagram; T2 adds a workflow or sequence diagram and an entity-relationship diagram for the data delta; T3 adds system context and container views, the technology map, and the failover topology.

Mechanical completeness: every node named, every edge labeled with what flows and by what protocol or trigger, every relationship carrying cardinality, and no element that appears in a diagram but nowhere else in the dossier (or the reverse, at T2 and above). A checker script enforces exactly this, so a diagram cannot drift from its design without failing.

Documentation is brief by default, written for a human to follow in order, commented where a choice is non-obvious.

## 8. When BrotherSBE stops and asks

Checkpoints sit at artifact gates, scaled by tier: T0 none, T1 one, T2 three, T3 all. Between gates it proceeds without asking.

Four conditions force an immediate stop at any tier: an ambiguity that would change the design, a discovered contradiction between what was stated and what the code or data shows, a collision with a hard gate (money, partner, personal data, production state), or a disproven assumption.

Every checkpoint has the same shape: what I found, my recommendation, the alternatives, the one decision I need, and what I will do if you say nothing. The last line keeps the loop moving and makes the default visible, so silence is never mistaken for approval on something irreversible.

## 9. Law form

Every law is written as: **WHEN** (observable trigger), **INPUTS** (what it reads), **RULE** (a decision table or explicit condition, never an adjective), **OUTPUT** (exactly one of: proceed, proceed with a label, stop and ask, refuse), **ENFORCED BY** (a script, checker, gate, template field, or explicitly "human review").

A law that cannot name its enforcement point is not a law. It moves to `PRACTICES.md`, which is honest about being advice. This split is what makes the law file shorter, sharper, and shorter to read.

## 10. What v2 keeps from v1

The gate engine, the eval bed, the lints, the chassis, the CI wiring: all retained. The gates gain design-side checks using the same mechanism and the same two modes (advisory in session, blocking in CI): an ADR with no rejected alternatives fails; a logical model with an unspecified cardinality fails; an entity with no system of record fails; an orphan diagram element fails; a missing tier-required artifact fails. Every new check ships with a fixture proving it catches its defect, exactly as the existing thirteen do.

## 11. Build order

1. The law rewrite: SKILL.md in the new form, PRACTICES.md split out.
2. The dossier: templates for artifacts 00 to 07, with their completeness rules.
3. The decision tables: architecture, integration, data storage, consistency, failover.
4. The design checker: `sbe_design.py`, plus fixtures in the eval bed for every new check.
5. The diagram checker: cross-reference against the dossier.
6. The whitepaper rewrite in the correct order, and a worked end-to-end example on a realistic system.

## 12. Success criteria

An engineer with a real task can go from "we need to build X" to an approved, diagrammed, verifiable design without writing a document from scratch, and a second engineer reading only the dossier can build the thing. Every law names its enforcement point. Every artifact has a completeness rule a script can check. The word count of the law file goes down, not up.
