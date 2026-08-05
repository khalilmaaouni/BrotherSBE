---
name: start
description: Use as the single entry point when someone wants to begin or resume work with BrotherSBE and does not know, or does not care, which command comes next. Detects existing state, resumes it when found, and otherwise asks for the outcome in plain language and routes into kickoff. Invoke as /brothersbe:start.
---

# Start

You are guiding someone who should never need to learn the machinery to use it. Your job is
to look at the ground, decide whether this is a resume or a fresh start, and hand over exactly
one next move. Speak plain language first; name the underlying commands second, as detail.

## Detect the ground before saying anything

Run these two commands, in order, and read the JSON before responding:

1. `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" doctor --json`. Read `result`. `FAIL` means at least one
   `checks[]` entry reads `FAIL`: name which one, by its `name` and `detail`.

   When the failing check is `project-init`, this is the ordinary shape of a fresh install:
   the marketplace path never runs `sbe init`, so a beginner's very first
   `/brothersbe:start` can land in a repository with no local footprint at all. Say so in
   plain language, not the raw JSON, then repair it before doing anything else, following
   the same preview-then-apply consent register every write-capable skill here uses (see
   `/brothersbe:adopt`: dry run by default, `--apply` reserved for an explicit yes):
     a. Preview: `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" init .` (dry run by default, writes
        nothing). Show the user what it proposes to create.
     b. Ask the user, in plain language, whether to apply it. Write nothing until they say
        yes.
     c. On yes, run `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" init . --apply`, confirm what it wrote,
        then re-run `sbe doctor --json` once to confirm `project-init` now reads `PASS`
        before continuing to step 2 below.
     d. If the user declines, say plainly that the rest of this flow needs the footprint
        and stop here rather than guessing at what to do instead.

   For any OTHER failing check, stop there rather than reading status at all. When the
   failing check is `tools` or `plugin-manifest`, name `/brothersbe:adopt` as the next stop
   too: those two are what "not correctly installed" looks like in this output.
2. `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" status --json`. Read `scope.storesInspected`: every field
   `null`, including `dossiers`, means nothing was found anywhere this run looked, so this is
   genuinely new. Any non-null field means prior state exists.

If a command fails outright for a reason other than a doctor FAIL, say what failed in one
plain sentence and keep going with what you could observe. Never present a stack trace as the
answer.

## Resuming beats restarting

When step 2 found prior state, do not start over and do not ask the user what they want as if
the history were not there. Read `nextAction` from the same `sbe status --json` output, and
name what `scope.storesInspected` found (which stores, and which dossiers when
`storesInspected.dossiers` is non-null): that is the two or three plain sentences that say
what stage, what is done, what is open. Continue from that stage. Restarting a project that
already has an intake and a dossier throws away decisions someone already made.

## If this is genuinely new

Ask the user one question, in normal language: what outcome do they want? Not which tier,
not which command, not which artifact. An outcome sounds like "an API endpoint that returns
monthly totals" or "this pipeline stops silently dropping rows". Once you have it, route to
`/brothersbe:kickoff` with that outcome as the objective. The tier and the ceremony are
computed there; the user never picks them.

## Always close with the response contract

Every answer from this skill ends with, in order: where you are, what is complete, what
needs attention, the ONE recommended next action, why that action, what BrotherSBE will do
automatically, what decision the user owns, and how success will be verified. Omit an
element only when it is genuinely empty, never because it is inconvenient. One recommended
action means one: never a menu.
