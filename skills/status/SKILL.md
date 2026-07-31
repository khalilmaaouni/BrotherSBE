---
name: status
description: Use when someone wants to know where a BrotherSBE project stands. Wraps the status command and the fence registry, and reframes the raw output as a plain answer with one next action, with technical detail kept below the summary rather than leading it. Invoke as /brothersbe:status.
---

# Status

Report where the work stands in language a person can act on. The raw machinery output is
the input to your answer, never the answer itself.

## Gather

Run the status command and read all of it before writing a word:

```
"${CLAUDE_PLUGIN_ROOT}/bin/sbe" status
```

Also run `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" fences` to see the live write fences. A fence
tells the user which files are currently claimed for editing and by what work, which
matters to anyone deciding what to touch next.

If either command fails, report the failure plainly, say what you could still observe, and
recommend the doctor check as the next action. See `${CLAUDE_PLUGIN_ROOT}/docs/CLI.md` for
what each command covers.

## Reframe, do not relay

Lead with the guided shape, in plain sentences:

1. **Where you are**: which stage of the lifecycle this project is in right now.
2. **What is complete**: the stages and checks already done, stated as facts you saw in the
   output, not as guesses.
3. **What needs attention**: anything failing, missing, stale, or fenced, in order of how
   much it blocks progress.
4. **The single next action**: one recommendation, consistent with what `/brothersbe:next`
   would pick from the same state.

Technical detail (raw verdict lines, receipt paths, fence entries, exit codes) goes under a
clearly separated section titled "Details", after the summary, never first. Include it: the
detail is how a skeptical reader checks your summary. Just never make anyone read it to
learn where they stand.

## Always close with the response contract

End with, in order: where you are, what is complete, what needs attention, the ONE
recommended next action, why, what BrotherSBE will do automatically, what decision the user
owns, and how success will be verified. Omit an element only when it is genuinely empty,
never because it is inconvenient.
