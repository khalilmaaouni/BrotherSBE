# The operating model and BrotherSBE are the same mechanism

Source: a data infrastructure acceleration plan and operating model deck, 31
slides, supplied 2026-08-08, plus two ingestion-strategy boards. Anonymised
here and in the booklet: no company, no product codename, no person.

This is the most important input the booklet has received, because it removes
the need to invent scenarios. The operating model already describes, in business
language, almost every control BrotherSBE implements in engineering language. The
booklet's job is now to show the translation, not to argue for the idea.

## The translation table

| What the operating model calls it | What BrotherSBE calls it | How close |
|---|---|---|
| Classify the dataset once, then it is a lookup not a debate (Class 1 to 4, by how many functions consume it) | The intake tier, computed from five objective questions, first match wins, T0 to T3 | **Near-exact.** Both refuse to let the person in a hurry decide how much rigour applies. Both key partly on consumer count. |
| Six handovers, each with a receiver who may refuse it, and a stated ceiling in days | `sbe handover`: prepare, show, acknowledge, reject. Ownership stays with the outgoing owner until a named human receiver acknowledges | **Exact.** The refusal right and the named receiver are the same design. |
| The contract registry, held before anything is built | The dossier: purpose, process, ADR, data model, verification, written before code | **Near-exact**, with one real gap: the model registers a contract centrally, BrotherSBE commits it beside the code. |
| Certification: only the hub may mark data Official | The approval gate: a host-verified signed trailer naming somebody other than the author; self-approval fails | **Strong**, with the known limit that nothing detects a change that *needed* certification and declared none. |
| Checks run inside the pipeline, every time it loads | The `ran` gate: a check that exited zero and took nonzero time, with a receipt | **Exact.** |
| One agreed meaning per number (semantic views) | The numbers gate: a second derivation against a pinned snapshot | **Complementary.** The model agrees the definition; the gate proves the figure reproduces. |
| Only one tool writes to a table | One writer per file, fenced before dispatch | **Exact**, at a different grain. |
| Exceptions and shortcuts, every one logged with an owner and a date to repay it | `sbe exceptions`: exceptions, their owners and their expiry; and the visible `# sbe: allow-silent <reason>` marker whose reason is read | **Exact.** Both refuse a silent waiver. |
| Five procedures enforced from day one, seven guidance first and enforced later | Advisory in a session (print the verdict, exit zero), enforcing in CI under `--strict` | **Exact.** This is the same rollout philosophy, independently arrived at. |
| One squad per source, which lands the data then dissolves | Fence, dispatch, close the fence with an inline evidence block | **Close.** |
| Anything the Council does not decide in one cycle is approved as asked | A flip condition, and a stated default so silence is never mistaken for a decision | **Related**, and worth calling out as a risk: a default-approve rule is the opposite posture to NO-DATA never passing. The booklet should name that tension rather than smooth it. |

## Where BrotherSBE does NOT map, stated so the booklet cannot overpromise

- It does not run the Council, broker capacity, or allocate vendor engineers.
- Its tier measures **change risk**, not dataset class. A Class 3 enterprise-key
  dataset and a T3 change are different axes that often coincide. Do not present
  them as the same number.
- It cannot certify. It can prove that a declared approval was signed by someone
  other than the author, which is the mechanical half of certification only.
- It has no view on business definitions, master data matching, or whether the
  five shared entities are the right five.
- It never writes to production, so nothing in the twelve-week plan's delivery
  path is executed by it.

## The three seams the booklet should build its scenarios on

All three are the customer's own words, generalised.

1. **"Curated zone, purpose zone and marketplace are empty. Data quality: barely
   anything checks anything."** A platform that is architecturally correct and
   evidentially empty. This is NO-DATA at estate scale, and it is the cleanest
   possible illustration that a diagram is not a control.
2. **"Each function builds its own way out."** Commercial on one warehouse,
   supply chain on another, vending on a third. Divergence is not a discipline
   problem; it is what a queue produces. The booklet should say so.
3. **The fast lane.** "If we trust a source, we connect it however is quickest
   and tidy the plumbing later. We never skip the quality checks." That sentence
   is BrotherSBE's whole posture in one line: ceremony scales with risk, evidence
   never does.

## The scenario the data seat should now use

Replace the invented re-graining story with this shape, generalised:

A trusted source is connected on the fast lane in week two. It lands in Bronze
unchanged, is cleaned into Silver against shared keys, and becomes a certified
Gold product read by a serving layer through an open table format, one copy of
the files, one access list. The change that follows is a shared-key change to
the customer entity, which is Class 3 by the model's rule and T3 by the intake's
rule for two different reasons, and it crosses six handovers each with a receiver
who may refuse it.

Every gate fires somewhere real in that path, and the honest limits fire too:
nothing detects that the certification was needed, and the second derivation
proves text difference rather than independence.

## Note on the ingestion decision layer

The two boards describe a four-way ingestion decision (native sharing, then a
managed platform connector, then a managed vendor, then custom or specialist),
with named owners, guardrails and a keep/expand/retire review. That is a
**decision table with criteria and a flip condition**, which is exactly the
artifact `sbe_decide.py` produces. Use it as the booklet's worked decision-table
example instead of the shipped architecture-shape table, because it is real.

Two cautions carried over from the refuted research: Fivetran's parent now also
owns dbt, and Databricks' declarative pipeline product is **Lakeflow pipelines**,
not Delta Live Tables. Any board reproduced in the booklet must use current
names.
