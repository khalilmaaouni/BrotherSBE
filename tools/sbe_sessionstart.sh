#!/bin/sh
# BrotherSBE SessionStart: digest + mechanical nags. MUST always exit 0.
# Output is injected into session context (10k char cap). The cap is ENFORCED
# HERE rather than assumed: the digest alone uses most of that budget, and the
# harness truncates the TAIL, which used to be where the compaction hint (the
# recovery pointer, the most safety-relevant line) printed. So the hint and
# the nags print FIRST, where truncation can never reach them, the digest
# prints last, and if the total runs over the cap this script cuts it itself
# with a visible marker instead of letting the harness cut it in silence.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
CAP=10000
# Capture the hook JSON from stdin ONCE so we can both replay it to the
# compaction hint and ignore it for the digest/nags.
PAYLOAD="$(cat 2>/dev/null)"
OUT="$(
  printf '%s' "$PAYLOAD" | python3 "$DIR/tools/sbe_telemetry.py" compact-hint 2>/dev/null
  python3 "$DIR/tools/sbe_telemetry.py" startup-nags 2>/dev/null
  python3 "$DIR/tools/sbe_telemetry.py" check-update 2>/dev/null
  cat "$DIR/DIGEST.md" 2>/dev/null
)"
if [ "${#OUT}" -gt "$CAP" ]; then
  printf '%s' "$OUT" | head -c $((CAP - 200))
  printf '\n[BrotherSBE: output truncated at the %s-character injection cap. Only the digest tail was cut (the compaction hint and nags printed first, in full); read DIGEST.md directly for the rest.]\n' "$CAP"
else
  printf '%s\n' "$OUT"
fi
exit 0
