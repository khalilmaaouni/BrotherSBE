---
name: verify
description: Use when work is about to be called done, a figure that could reach a decision has been produced, a schema migration is part of the change, the change touches money or a partner path, or a verification plan is being written. Runs the hard gates and reports PASS, FAIL or NO-DATA with the evidence each verdict actually read. Invoke as /brothersbe:verify.
---

# Verify

An agent earns trust in exact proportion to how mechanically its output can be checked.
This skill is that rule pointed at the finished work.

Read `${CLAUDE_PLUGIN_ROOT}/SKILL.md`, then
`${CLAUDE_PLUGIN_ROOT}/references/phase-verification.md` and
`${CLAUDE_PLUGIN_ROOT}/references/laws-hard-gates.md` (L7 to L10).

## The four hard gates

```
python3 "${CLAUDE_PLUGIN_ROOT}/tools/sbe_gate.py" numbers    <dir>
python3 "${CLAUDE_PLUGIN_ROOT}/tools/sbe_gate.py" migration  <dir>
python3 "${CLAUDE_PLUGIN_ROOT}/tools/sbe_gate.py" approval   <dir>
python3 "${CLAUDE_PLUGIN_ROOT}/tools/sbe_gate.py" ran        <dir>
```

Passing a directory instead of a gate name runs the set. These four plus the silent-failure
lints are refused rather than waived: an operator instruction in session can override a
default, never a hard gate.

## The scored surface and the design completeness check

```
python3 "${CLAUDE_PLUGIN_ROOT}/tools/sbe_score.py"  --strict --strict-soft <dir>
python3 "${CLAUDE_PLUGIN_ROOT}/tools/sbe_design.py" --strict <dir>
```

## How to read a verdict

- **PASS** means required evidence was inspected and met the control.
- **FAIL** means required evidence was inspected and violated it.
- **NO-DATA** means the control examined nothing, and it names why. NO-DATA is never a pass,
  and a run that opened no file reports NO-DATA rather than "clean".

Report the verdict with the command that produced it and the evidence it names. Never
summarize a gate you did not run, and never re-word a NO-DATA into a pass because the work
looks right.

## The honest limit on all of it, today

These gates check the internal shape of an evidence file. They do not yet check where that
file came from. A receipt can be written by the same agent whose work it is meant to verify,
and a fabricated duration, exit code, row count or rerun result still satisfies the schema.
Commit-bound, wrapper-generated evidence is the next thing being built. Until it lands, treat
a local PASS as advisory and read `${CLAUDE_PLUGIN_ROOT}/docs/KNOWN-LIMITS.md`.
