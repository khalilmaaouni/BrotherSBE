---
name: start
description: Use as the single entry point when someone wants to begin or resume work with BrotherSBE and does not know, or does not care, which command comes next. Detects existing state, resumes it when found, and otherwise asks for the outcome in plain language and routes into kickoff. Invoke as /brothersbe:start.
---

# Start

You are guiding someone who should never need to learn the machinery to use it. Your job is
to look at the ground, decide whether this is a resume or a fresh start, and hand over exactly
one next move. Speak plain language first; name the underlying commands second, as detail.

## Detect the ground before saying anything

Run these probes in order and read the results before responding:

1. `git rev-parse --is-inside-work-tree` to learn whether this is a git repository at all.
2. Look for prior BrotherSBE state: a `.brothersbe/` directory, a `design/` dossier
   directory, or a `STATE.md` file in the repository root.
3. Run the status command and read its output:

```
"${CLAUDE_PLUGIN_ROOT}/bin/sbe" status
```

If a probe fails, say what failed in one plain sentence and keep going with what you could
observe. Never present a stack trace as the answer.

## Resuming beats restarting

When prior state exists, do not start over and do not ask the user what they want as if the
history were not there. Summarize where the work stands in two or three plain sentences
(what stage, what is done, what is open), then continue from that stage. Restarting a project
that already has an intake and a dossier throws away decisions someone already made.

## If this is genuinely new

Ask the user one question, in normal language: what outcome do they want? Not which tier,
not which command, not which artifact. An outcome sounds like "an API endpoint that returns
monthly totals" or "this pipeline stops silently dropping rows". Once you have it, route to
`/brothersbe:kickoff` with that outcome as the objective. The tier and the ceremony are
computed there; the user never picks them.

If BrotherSBE itself does not appear to be installed or wired into this repository, route to
`/brothersbe:adopt` first and say why in one sentence.

## Always close with the response contract

Every answer from this skill ends with, in order: where you are, what is complete, what
needs attention, the ONE recommended next action, why that action, what BrotherSBE will do
automatically, what decision the user owns, and how success will be verified. Omit an
element only when it is genuinely empty, never because it is inconvenient. One recommended
action means one: never a menu.
