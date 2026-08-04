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
   `checks[]` entry reads `FAIL`: name which one, by its `name` and `detail`, and stop there
   rather than reading status at all. When the failing check is `tools` or `plugin-manifest`,
   name `/brothersbe:adopt` as the next stop too: those two are what "not correctly installed"
   looks like in this output.
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
