# Spec: the guided layer (start, next, status, help) and the program ledger

Date: 2026-07-31. Owner: orchestrator session bd3f338d. Founder approved the scope the same
day through question windows: guided layer plus cleanup, park then prune all worktrees, and
commit the program ledger into the repository.

Source of intent: the founder's master plan (BrotherSBE Public Release Master Plan,
2026-07-31, baseline dacee900), carried into this repository at program/MASTER-PLAN.md.
This spec implements its Feature 1 (Guided Project Navigator) and its section 9 ledger as
one vertical slice, and nothing else from it.

## The problem, in one line

The product exposes its machinery first. A new user opening this repository or installing
the plugin sees twenty two subcommands, six skills, seven agents, and no obvious first move.

## What ships in this slice

Four new plugin skills, one beginner rewrite of the README opening, and a tracked program
ledger. The engine (tools/, src/brothersbe/, gates, evals) is not modified anywhere in this
slice. The skills are a presentation layer that routes into what already exists, which is
the master plan's own architectural rule 6.3: wrap the proven engine, do not rewrite it.

### 1. skills/start/SKILL.md, invoked as /brothersbe:start

The one entry point. Behavior it instructs:

- Detect the ground first: is this a git repository, does .brothersbe/ or a design/ dossier
  or STATE.md exist, what does `sbe status` say. Resuming beats restarting: when prior
  BrotherSBE state exists, summarize it and continue from its stage instead of starting over.
- If new: ask the user what outcome they want in normal language (the master plan's Loop 1
  wording), then route to /brothersbe:kickoff with that outcome as the objective. Never ask
  the user to pick a tier or a command.
- Always end with the response contract below.

### 2. skills/next/SKILL.md, invoked as /brothersbe:next

Exactly one recommended action, chosen by a fixed priority ladder evaluated from observable
state (each probe is a command that exists today):

1. Installation or environment broken (`sbe doctor` FAIL) then repair guidance first.
2. No intake recorded (no 00-intake.json in the dossier root) then /brothersbe:kickoff.
3. Dossier incomplete for the tier (`sbe design` artifacts check not passing) then
   /brothersbe:design.
4. Work planned but not executed (`sbe plan` output with open tasks, `sbe work` state) then
   continue the open task.
5. Evidence or gates not green (`sbe verify`, `sbe gate`) then /brothersbe:verify.
6. Review not run then /brothersbe:review.
7. Everything green then finish guidance: summary, pull request, human merge.

The skill instructs picking the FIRST matching rung, stating why in one sentence, and
never listing the whole ladder as the answer.

### 3. skills/status/SKILL.md, invoked as /brothersbe:status

Wraps `sbe status` and the fence registry, and reframes the output in the guided shape:
where you are, what is complete, what needs attention, the single next action. Technical
detail (raw verdict lines, receipt paths) goes under a collapsed or clearly separated
"details" section, never first.

### 4. skills/help/SKILL.md, invoked as /brothersbe:help

Plain-language orientation: what BrotherSBE is (a colleague that designs before it builds
and refuses to claim what it did not check), the lifecycle in one diagram-free paragraph,
the three entry skills (start, next, status), and only then the full map of specialist
skills and commands for users who want it. A flat command list is never the primary answer.

### The response contract, shared by all four

Every user-facing answer from these skills carries, in order: where you are, what is
complete, what needs attention, the ONE recommended next action, why, what BrotherSBE will
do automatically, what decision the user owns, and how success will be verified. Omit an
element only when it is genuinely empty, never because it is inconvenient.

### 5. README.md opening rewrite

The first screen of the README becomes beginner-first: what this is in two sentences, the
promise (install once, describe the outcome, follow one recommended action at a time), the
install command, and /brothersbe:start as the only first move. The existing engineering
content moves below a clearly named line, unchanged. The copy-ready CI block and every
other guarded excerpt keeps its exact bytes.

### 6. program/ ledger

- program/MASTER-PLAN.md: the founder's plan, verbatim (its own dash characters survive as
  quoted source material; new prose written for this repository stays dash-free).
- program/PROGRAM.yaml: release objective, version target, owner, waves, gates summary.
- program/work-items/BR-0000.yaml: this slice itself, recorded with owner, acceptance,
  status, evidence, so the ledger starts truthful rather than aspirational.
- program/README.md: what the ledger is, what updates it, and the honest statement that
  STATUS generation and event alerts are later waves (master plan section 9), not built yet.

## Constraints, all mechanical, all enforced by the existing battery

- Frontmatter: name equals the directory name; description present, quoted when it holds
  a colon; no value starting with a YAML structure character.
- Every ${CLAUDE_PLUGIN_ROOT}/path cited must exist (drift test).
- Zero em or en dashes in new prose (program/MASTER-PLAN.md is quoted source and exempt;
  the scan configuration must reflect that exemption explicitly, never silently).
- No client or private names (TestNoPrivateNameShips).
- Python floor 3.9; this slice adds no Python.
- No skill references a command that does not exist in `sbe` today.
- CHECKSUMS.sha256 regenerated last, by the orchestrator, never by a writer.

## Done-checks

- `claude plugin validate .` exits 0.
- `python3 tools/test_sbe.py` all OK (skill frontmatter, citation drift, YAML rules).
- `python3 evals/run_evals.py` at or above the session baseline with 0 regressions.
- `bash scripts/verify-install.sh` reports 0 mismatched, 0 missing, 0 extra after the
  manifest regeneration.
- A dash scan over every new and edited file returns only the declared MASTER-PLAN.md
  exemption.
- Reading the README top screen answers, without scrolling: what is this, why should a
  beginner care, and what is the one first command.
