#!/bin/sh
# BrotherSBE SessionStart: digest + mechanical nags. MUST always exit 0.
# Output is injected into session context (10k char cap; we stay far under).
# Resolve the skill directory from this script's own location, so the repo
# works wherever it is cloned.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
# Capture the hook JSON from stdin ONCE so we can both ignore it (digest/nags)
# and replay it to the compaction hint below.
PAYLOAD="$(cat 2>/dev/null)"
cat "$DIR/DIGEST.md" 2>/dev/null
python3 "$DIR/tools/sbe_telemetry.py" startup-nags 2>/dev/null
python3 "$DIR/tools/sbe_telemetry.py" check-update 2>/dev/null
# If this session resumed from a compaction, point it at the autosave.
printf '%s' "$PAYLOAD" | python3 "$DIR/tools/sbe_telemetry.py" compact-hint 2>/dev/null
exit 0
