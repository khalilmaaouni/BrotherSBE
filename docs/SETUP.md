# BrotherSBE: setup

Install is a few minutes. Turning the gates from advisory into blocking is real CI work, and this document is honest about which is which.

## Prerequisites

- Claude Code (BrotherSBE is a Claude Code skill).
- Python 3 on PATH (the tools use the standard library only, no third-party packages, no network).
- Git (the approval gate reads commit trailers and signatures).

## 1. Clone the skill

```
git clone https://github.com/khalilmaaouni/BrotherSBE ~/.claude/skills/brothersbe
```

Standalone: it works with nothing else installed. See [PARITY.md](../PARITY.md) for what it shares with BrotherModeUp.

## 2. Point the vault at a folder you choose

```
export BROTHERSBE_VAULT="$HOME/BrotherSBEVault"   # put this in your shell profile
```

Everything the skill writes (telemetry, correction candidates, session logs) goes there, and nowhere else. Copy the starter memory from `memory-template/` into that folder the first time.

## 3. Wire the hooks

Into `~/.claude/settings.json`, or a project `.claude/settings.json`. The harness fires these, not the model, which is the point: the save-before-you-die rule cannot be run by the actor that is dying.

```json
{
  "hooks": {
    "SessionStart": [
      {"hooks": [{"type": "command",
        "command": "sh ~/.claude/skills/brothersbe/tools/sbe_sessionstart.sh"}]}
    ],
    "SessionEnd": [
      {"hooks": [{"type": "command",
        "command": "python3 ~/.claude/skills/brothersbe/tools/sbe_telemetry.py outcomes-append"}]}
    ],
    "PreCompact": [
      {"hooks": [{"type": "command",
        "command": "sh ~/.claude/skills/brothersbe/tools/sbe_autosave.sh precompact"}]}
    ]
  }
}
```

What each does: SessionStart injects the active-laws digest plus mechanical nags. SessionEnd appends one idempotent telemetry line and scans your short messages for correction candidates (secret-redacted, owner-only). PreCompact snapshots the whole worktree to a private git ref so a token-death is recoverable. Every hook exits 0 and never blocks a session. Opt-outs are in [SECURITY.md](../SECURITY.md).

## 4. Prove it works, in 60 seconds

```
python3 evals/run_evals.py
```

Thirty-seven lines, each a real failure class caught by the check that owns it, ending "37 passed, 0 regressions." That is the whole trust claim, executable. Then see the gates on a directory:

```
python3 tools/sbe_gate.py .            # all four gates, advisory
python3 tools/sbe_gate.py numbers .    # one class
python3 tools/sbe_gate.py --strict .   # enforcing: exits nonzero on any FAIL
```

## 5. Turn the gates from advisory into blocking (the real step)

Cloning the skill gives you the tools. It does not stop a bad merge until you wire `--strict` into the CI of the repository you want guarded. A ready workflow ships at `.github/workflows/brothersbe-gates.yml`; copy it into the guarded repo (and make `tools/` reachable there, by vendoring it or adding a clone step). It runs on every pull request:

```yaml
- run: python3 tools/sbe_gate.py --strict .
- run: python3 tools/sbe_score.py --strict .
```

The first blocks on a failed hard gate (a number with no re-run, an untested migration reverse, an unsigned money-path change, an unrun check). The second blocks on a silent-failure lint. Advisory mode tells a session; only this CI wiring stops a merge, and that is by design.

## What you get, and what you do not

You get a colleague that arrives with its checks already run and says UNVERIFIED when they are not, plus a memory that improves through reviewed pull requests. You do not get autonomy, an oracle, or enforcement without the CI step above. Those omissions are the point: see [DESIGN.md](DESIGN.md) section 1.6.
