---
name: kickoff
description: Use at the start of any backend, infrastructure, or data engineering task, before designing or writing anything. Classifies the work profile, maps the ground (git state, disk, the repo's own build and test commands), scores the intake into a tier, and names the checks that will verify the work before the work begins. Invoke as /brothersbe:kickoff.
---

# Kickoff

You are the engineer's senior colleague. This skill starts a piece of work correctly, which
is the cheapest place to prevent the expensive mistakes.

## First, load the law

Read `${CLAUDE_PLUGIN_ROOT}/SKILL.md` before anything else. It carries the spine, the
unconditional floor (L6 forcing conditions, L11 silent-failure lints, L14 blast radius), and
the routing table that says which reference file to load when. Do not work from memory of it.

## Then run the six mechanical steps

1. CLASSIFY in one line: the work profile (backend service, warehouse and SQL, pipeline, data
   quality, infrastructure, performance, or artifact mode) and the tier from L1.
2. Read memory: project overview, open items, failures index, LEARNED.md. Say so if memory is
   missing. Never block on it.
3. Map the ground: `git status` first (foreign changes mean coordinate, never overwrite), disk
   as a numeric gate, the repo's own build, test and CI commands copied verbatim from its
   README, Makefile or CI file, one cheap probe per named dependency.
4. Name the check that will verify the work BEFORE writing it, plus the kill criteria per step.
5. Open STATE.md: fences and decisions, updated at every milestone so any kill resumes from
   disk.
6. Score the intake:

```
"${CLAUDE_PLUGIN_ROOT}/bin/sbe" intake --help
```

The intake writes `00-intake.json` into the dossier directory. The tier it computes decides
which artifacts `/brothersbe:design` will require and which gates `/brothersbe:verify` will
run.

## What this skill cannot do yet, stated plainly

The tier is computed from **answers**, not from the diff. Nothing here inspects OpenAPI files,
schemas, protobuf definitions, migration files or data models to check those answers against
what the change actually touches, so an answer that understates the risk lowers the ceremony
and no check notices. That gap is the reason the change-detection engine is being built; until
it ships, treat the tier as a claim by the operator rather than a measurement of the change.
Read `${CLAUDE_PLUGIN_ROOT}/docs/KNOWN-LIMITS.md` before relying on it for anything that
touches money, partner data, personal data, or production state.

## Next

`/brothersbe:design` for the dossier, `/brothersbe:verify` for the gates.
