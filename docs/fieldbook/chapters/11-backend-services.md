---
slug: backend-services
title: Scenario, a backend service
part: "5"
verified-against: 1.0.0-rc.28
---

# Scenario, a backend service

An API, a queue consumer, a transactional path. The failure modes here are
less silent than in a warehouse, which changes which parts of the method earn
their keep.

## What bites, and what does not

The numbers gate rarely applies. The migration gate applies the moment a schema
moves. The `ran` gate applies to every reconciliation and integration check.
The approval gate applies on money and partner paths.

What actually earns its keep on service work is the **process phase** and the
**ADR**, because the expensive mistakes are a boundary drawn in the wrong place
and a contract changed without knowing who consumed it.

## Day one: an endpoint changes shape

```bash
mkdir -p design/orders-api-v2
python3 tools/sbe_intake.py design/orders-api-v2
```

"Does this change an API contract others depend on?" Yes. "How many downstream
consumers break if it is wrong?" If the answer is many, that is T2 and six
artifacts. If the endpoint also touches payment, the first match is T3 and it
is seven.

## The process artifact, where the exception path lives

`02-process.md` wants actors, steps with triggers, exception paths, and
handoffs with their contracts. On service work the exception path is the
document.

> Step 3. The payment provider is called. **Exception path:** on a timeout the
> order is left in `pending_payment` and a reconciliation job resolves it
> within fifteen minutes. It is never retried inline, because the provider is
> not idempotent on this endpoint without an idempotency key, and we do not
> send one today.

That last clause is the sentence that prevents a double charge, and it exists
only because a template asked for the exception path by name.

## The ADR, with its flip condition

```bash
printf '2\neventual\nlow\nhigh\n' | python3 tools/sbe_decide.py tables/architecture.json shape
```

Four named criteria: independently deploying teams, consistency requirement,
operational maturity, failure isolation. You get a recommendation, the
alternatives, the criteria that separated them, and what would flip it.

The flip condition is the part teams skip and the part that pays. "Revisit
toward a change data capture stream if operational maturity rises enough to
run a broker on-call rotation and the consumer comes to need sub-second
freshness" is a decision that can be revisited without re-litigating it from
scratch.

If no criterion contributed, the run returns NO-DATA and the recommendation is
suppressed. A recommendation backed by zero evidence is a guess with a table
around it.

## The migration, expand and contract

A service migration has an extra constraint a warehouse one does not: old and
new code run at the same time during deployment.

The `migration-reviewer` covers forward and reverse evidence, expand and
contract compatibility, lock duration, mixed-schema deployment and rollback
time. The gate itself checks the receipt: both legs against a restored copy, a
rehearsal id, matching row counts.

Sequence that survives a rollback:

1. Expand. Add the new column nullable, deploy, write to both.
2. Backfill, with the reconciliation registered as a check and run through the
   evidence wrapper.
3. Read from the new column, deploy.
4. Contract. Drop the old column, in a later release, only after the previous
   release is no longer deployable.

Step 4 in the same release as step 1 is the single most common way a rollback
becomes impossible.

## Boundary calls

Every network call, file read, JSON decode, subprocess and piece of user input
gets an explicit failure path that surfaces the error. No `try!`, no
force-unwrapping external data, no discarded exit codes.

This is where the silent-failure linter lives on service code. `except: pass`
around a downstream call turns an outage into a quietly wrong response, which
is strictly worse than an error, because nobody pages for it.

## Which reviewer you get

`backend-reviewer` covers contract compatibility, idempotency, concurrency,
transaction boundaries, error paths, retries, observability and performance.
Touch authentication, authorization, partner APIs, money movement, file upload,
secrets, dependencies or personal data and `security-reviewer` joins it.

Both are read-only. Neither can fix what it finds, which is what keeps findings
recorded rather than quietly absorbed.

## Week one and month one

**Week one.** `sbe verify` in CI advisory. Register your integration
reconciliation as a check. Agree that a FAIL blocks and a NO-DATA does not.

**Month one.** `--strict` on. Every contract change carries an ADR with a flip
condition, and every migration carries a rehearsed reverse. When somebody asks
why the boundary is where it is, the answer is in the repository.
