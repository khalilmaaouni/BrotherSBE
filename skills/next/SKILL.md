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

Evaluate the rungs in this exact order. Each rung names the exact JSON field or closed
verdict word it decides from (PASS, FAIL, NO-DATA, WAIVED is the whole verdict vocabulary,
never reworded); run the probe, read that field, and stop at the first rung that matches.

1. **Environment broken.** Run `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" doctor --json` and read
   `result`. `FAIL` means at least one `checks[]` entry reads `FAIL`; name it (`name`,
   `detail`) and recommend repairing that specific check, before anything else downstream can
   be trusted.
2. **No intake recorded.** Run `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" status --json` and read
   `scope.storesInspected`. `intake` null and `dossiers` null together mean no flat
   `00-intake.json` exists at the root and dossier discovery found none under the design
   roots either: the work was never scored. Recommend `/brothersbe:kickoff`.
3. **Dossier incomplete for the tier.** Run `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" design --strict
   <dir>` against the root `scope.storesInspected.intake` names, or a dossier
   `scope.storesInspected.dossiers` names. A nonzero exit means the run printed a FAIL line
   somewhere; read that line for the missing or malformed artifact. Recommend
   `/brothersbe:design`.
4. **Planned but not executed.** Read `notes.activeConflicts` from the same
   `sbe status --json` output: it always states "N open task(s) among M total", even when
   `activeConflicts` itself is empty. N greater than zero means a task is claimed and in
   flight: recommend continuing it, named specifically, through the `work` subcommands
   (`work start`, `work check`, `work finish`), each taking the task ID as its argument. When
   `scope.storesInspected.dossiers` names a discovered dossier, also run
   `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" status --team --json` and read `findings` for that
   change's severity 7 ("active tasks", open or FORCED) and severity 8 ("ready tasks", no
   registry record yet) entries: any severity 7 entry means continue that task, named by its
   own `nextAction`; with no severity 7 entry but a severity 8 entry present, nothing has
   started, recommend the `work start` command that finding's `nextAction` names.
5. **A hard gate FAILs, or evidence is missing for the declared tier.** Run
   `python3 "${CLAUDE_PLUGIN_ROOT}/tools/sbe_gate.py" <dir>` (writes nothing, per its own
   "writes: nothing" usage line) and read the verdict word each gate line prints. Then run
   `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" status --json` and read `missingEvidence`.
   - Any gate line reads FAIL: recommend `/brothersbe:verify`, naming the failing gate.
   - No gate reads FAIL, and `missingEvidence` is a non-empty list: recommend
     `/brothersbe:verify`, naming the obligation its first item's `finding` states.
   - No gate reads FAIL, and `missingEvidence` is empty: this rung does not match, even when
     every gate above read NO-DATA. Proceed to rung 6.
   NO-DATA alone is never a reason to recommend `/brothersbe:verify`: `sbe_gate.py`'s own exit
   arithmetic never counts a NO-DATA verdict toward failure (`tools/sbe_gate.py:1615-1633`), a
   T0-declared change owes no evidence at all so `missingEvidence` stays empty for it by
   construction, and CR-08 means `sbe verify` now mints the design, gate and score receipts
   `missingEvidence` would otherwise name, so a single `/brothersbe:verify` run on a clean tree
   clears the obligation before this rung would ever see it again. Recommending verify with
   nothing missing recommends a no-op, which is the loop this rung exists to close.
6. **Review not run.** When `scope.storesInspected.dossiers` names a discovered dossier, run
   `"${CLAUDE_PLUGIN_ROOT}/bin/sbe" status --team --json` and read `findings` for that
   change's severity 11 ("review record") entry. No entry, or one whose `verdict` is not
   `PASS`, means review has not cleared: recommend `/brothersbe:review`, naming that finding's
   `detail`. In the flat single-dossier layout, check directly for `11-review.json` beside the
   intake `scope.storesInspected.intake` names: absent means recommend `/brothersbe:review`.
7. **Everything green.** Recommend finish guidance: write the summary, open the pull
   request, and hand the merge decision to a human. The merge is never this skill's call.

## How to answer

State the one recommended action, then why in exactly one sentence grounded in the field or
verdict word you actually read: name it and its value first (for example, "missingEvidence
names one obligation: no evidence receipt declares a gate run" rather than a paraphrase), then
the plain-language meaning. Do not speculate about rungs you did not probe.

## Always close with the response contract

End every answer with, in order: where you are, what is complete, what needs attention, the
ONE recommended next action, why, what BrotherSBE will do automatically, what decision the
user owns, and how success will be verified. Omit an element only when it is genuinely
empty, never because it is inconvenient.
