---
name: status
description: Use when someone wants to know where a BrotherSBE project stands. Wraps the status command and the fence registry, and reframes the raw output as a plain answer with one next action, with technical detail kept below the summary rather than leading it. Invoke as /brothersbe:status.
---

# Status

Report where the work stands in language a person can act on. The engine's JSON is the input
to your answer, never the answer itself.

## Gather

Run the status command and read the whole JSON document before writing a word:

```
"${CLAUDE_PLUGIN_ROOT}/bin/sbe" status --json
```

When `scope.storesInspected.dossiers` names a discovered dossier, also run
`"${CLAUDE_PLUGIN_ROOT}/bin/sbe" status --team --json` and read its `findings` and `changes`
for the per-dossier detail the single-project report rolls up into one summary.

Also run `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" fences` to see the live write fences. A fence
tells the user which files are currently claimed for editing and by what work, which
matters to anyone deciding what to touch next.

If either command fails, report the failure plainly, say what you could still observe, and
recommend `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" doctor --json` as the next action. See
`${CLAUDE_PLUGIN_ROOT}/docs/CLI.md` for what each command covers.

## Reframe, do not relay

Lead with the guided shape, in plain sentences, each sourced from a named field rather than a
paraphrase of the rendered text:

1. **Where you are**: the five sections, `brokenClaims`, `mergeBlockers`, `activeConflicts`,
   `missingEvidence`, `soundEvidence`, read in that order; the first one holding an item names
   the stage. All five empty: read `notes` for the clean or NO-DATA line behind that, and
   `scope.storesInspected` for what was searched.
2. **What is complete**: `soundEvidence`, the COMPLETED EVIDENCE section; `notes.soundEvidence`
   carries the clean or NO-DATA line when it is empty.
3. **What needs attention**: `brokenClaims`, `mergeBlockers`, `activeConflicts` and
   `missingEvidence`, in that order, the same priority `nextAction` itself reads; a live fence
   from the second command is attention too, even when every section above is clean.
4. **The single next action**: `nextAction`, verbatim. This is the same field
   `/brothersbe:next` reads for the same state, not a separate derivation of it.

Technical detail (raw verdict lines, receipt paths, fence entries, exit codes) goes under a
clearly separated section titled "Details", after the summary, never first. Include it: the
detail is how a skeptical reader checks your summary. Just never make anyone read it to
learn where they stand.

## Always close with the response contract

End with, in order: where you are, what is complete, what needs attention, the ONE
recommended next action, why, what BrotherSBE will do automatically, what decision the user
owns, and how success will be verified. Omit an element only when it is genuinely empty,
never because it is inconvenient.
