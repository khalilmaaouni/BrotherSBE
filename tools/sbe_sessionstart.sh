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
# The two halves are measured SEPARATELY, because the marker used to assert
# which half was cut and nothing bounded the first one: a large resume brief
# (its size is data-driven, written from a transcript) pushed the hint itself
# past the cap, and the printed line still said "only the digest tail was cut
# (the compaction hint and nags printed first, in full)", naming the wrong
# casualty in the one line whose job is to explain a context loss. The
# recovery-relevant half now gets the whole budget it needs and the marker
# states what was actually cut, measured rather than assumed.
HEAD_OUT="$(
  printf '%s' "$PAYLOAD" | python3 "$DIR/tools/sbe_telemetry.py" compact-hint 2>/dev/null
  python3 "$DIR/tools/sbe_telemetry.py" startup-nags 2>/dev/null
  python3 "$DIR/tools/sbe_telemetry.py" check-update 2>/dev/null
)"
DIGEST_OUT="$(cat "$DIR/DIGEST.md" 2>/dev/null)"
# Bytes, not characters: `head -c` cuts bytes, while ${#VAR} counts characters
# in bash and bytes in dash, so the comparison and the cut disagreed on bash
# with any non-ASCII content. wc -c is bytes on every shell, which makes the
# measurement and the cut the same unit everywhere.
HEAD_LEN=$(printf '%s' "$HEAD_OUT" | wc -c | tr -d ' ')
TOTAL_LEN=$(printf '%s\n%s' "$HEAD_OUT" "$DIGEST_OUT" | wc -c | tr -d ' ')
MARKER_ROOM=220
if [ "$TOTAL_LEN" -le "$CAP" ]; then
  printf '%s\n%s\n' "$HEAD_OUT" "$DIGEST_OUT"
elif [ "$((HEAD_LEN + MARKER_ROOM))" -le "$CAP" ]; then
  printf '%s\n' "$HEAD_OUT"
  printf '%s' "$DIGEST_OUT" | head -c $((CAP - HEAD_LEN - MARKER_ROOM))
  printf '\n[BrotherSBE: output truncated at the %s-character injection cap. The compaction hint and nags printed in full; the digest was cut after %s bytes of its %s. Read DIGEST.md directly for the rest.]\n' \
    "$CAP" "$((CAP - HEAD_LEN - MARKER_ROOM))" "$(printf '%s' "$DIGEST_OUT" | wc -c | tr -d ' ')"
else
  # The hint alone overflows: the digest is dropped ENTIRELY (not "its tail"),
  # and the hint itself is cut. Both facts are stated, because this is exactly
  # the run where a reader most needs to know what they are not seeing.
  printf '%s' "$HEAD_OUT" | head -c $((CAP - MARKER_ROOM))
  printf '\n[BrotherSBE: output truncated at the %s-character injection cap. The compaction hint and nags alone are %s bytes, so THEY were cut after %s bytes and the digest did not print at all. Read the resume brief in your vault and DIGEST.md directly.]\n' \
    "$CAP" "$HEAD_LEN" "$((CAP - MARKER_ROOM))"
fi
exit 0
