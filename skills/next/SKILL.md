---
name: next
description: Use when someone asks what to do next in a BrotherSBE project. Evaluates a fixed priority ladder against observable state and returns exactly one recommended action with a one sentence reason, never a menu of options. Invoke as /brothersbe:next.
---

# Next

One question, one answer. This skill exists so the user never has to hold the lifecycle in
their head: you evaluate the ladder below against what you can actually observe, pick the
FIRST rung that matches, and recommend that single action. Never list the whole ladder as
the answer, and never offer two options when the ladder picked one.

## The priority ladder

Evaluate the rungs in this exact order. Each probe is a command or check that exists today;
run the probe, read the result, and stop at the first rung that matches.

1. **Environment broken.** Run `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" doctor`. Any FAIL means
   nothing downstream can be trusted, so the recommendation is repair guidance for the
   specific failure, before anything else.
2. **No intake recorded.** No `00-intake.json` in the dossier root means the work was never
   scored. Recommend `/brothersbe:kickoff`.
3. **Dossier incomplete for the tier.** Run `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" design` and
   read its artifacts check. Not passing means design work remains. Recommend
   `/brothersbe:design`.
4. **Planned but not executed.** Run `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" status` and read
   its summary for an open or in-progress task, and check whether the dossier holds a
   `08-plan.json` with tasks not yet finished. An open task means the recommendation is to
   continue that task, named specifically, through the `work` subcommands (`work start`,
   `work check`, `work finish`), each of which takes the task as its argument.
5. **Evidence or gates not green.** Run `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" verify` and
   `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" gate`. Anything not green means recommend
   `/brothersbe:verify`.
6. **Review not run.** No review verdict recorded for the current change means recommend
   `/brothersbe:review`.
7. **Everything green.** Recommend finish guidance: write the summary, open the pull
   request, and hand the merge decision to a human. The merge is never this skill's call.

## How to answer

State the one recommended action, then why in exactly one sentence grounded in the probe
result you actually saw (for example, quoting the failing doctor line or naming the missing
artifact). Do not speculate about rungs you did not probe.

## Always close with the response contract

End every answer with, in order: where you are, what is complete, what needs attention, the
ONE recommended next action, why, what BrotherSBE will do automatically, what decision the
user owns, and how success will be verified. Omit an element only when it is genuinely
empty, never because it is inconvenient.
