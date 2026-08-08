#!/bin/sh
# BrotherSBE SessionStart: digest + mechanical nags. MUST always exit 0.
# Output is injected into session context (10k char cap). The cap is ENFORCED
# HERE rather than assumed: DIGEST.md was cut down to the three unconditional
# laws (L6, L11, L14), the checked/human legend, a pointer to
# references/laws-full-digest.md for the rest, and the after-compaction
# instruction, so the digest itself now uses only a small slice of that
# budget (see tools/test_sbe.py TestDigestBudget for the enforced ceiling).
# The harness truncates the TAIL, which used to be where the compaction hint
# (the recovery pointer, the most safety-relevant line) printed. So the hint
# and the nags print FIRST, where truncation can never reach them, the digest
# prints last, and if the total runs over the cap this script cuts it itself
# with a visible marker instead of letting the harness cut it in silence.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
CAP=10000
# Capture the hook JSON from stdin ONCE so we can both replay it to the
# compaction hint and ignore it for the digest/nags.
PAYLOAD="$(cat 2>/dev/null)"
# The session baseline (release blocker 1 item 1.2): what the working tree held
# BEFORE this session touched it, so the Stop reconciler can tell a change this
# session made from dirt that was already there. Written under the repository's
# git directory, never into the working tree, because a control that dirties the
# tree it measures reports itself. Its stdout is /dev/null and its stderr is
# kept: SessionStart's stdout is injected into the session context, and a
# baseline path is not context. It always exits 0 and is guarded with `|| true`
# anyway, because SessionStart must never fail a session.
printf '%s' "$PAYLOAD" | python3 "$DIR/tools/sbe_session_baseline.py" write >/dev/null || true
# The two halves are measured SEPARATELY, because the marker used to assert
# which half was cut and nothing bounded the first one: a large resume brief
# (its size is data-driven, written from a transcript) pushed the hint itself
# past the cap, and the printed line still said "only the digest tail was cut
# (the compaction hint and nags printed first, in full)", naming the wrong
# casualty in the one line whose job is to explain a context loss. The
# recovery-relevant half now gets the whole budget it needs and the marker
# states what was actually cut, measured rather than assumed.
# ONE startup emitter is PROFILE-GATED (V1 profile lane): the telemetry nags. The
# default profile is the safety floor plus design, implementation boundaries and
# verification, and the nags are a working-rhythm prompt, so a session that has not
# asked for the ledger spends no context on them. `sbe_profile.py enabled` exits 1
# for "not enabled" AND for every failure it can meet (a missing file, unparseable
# JSON, an unknown module id), carrying the reason on stderr: the smallest surface
# is the safe direction to fail in for a hook that must never fail a session, and
# the reason is printed rather than eaten. The guard sits on the line directly above
# its emitter because tools/sbe_profile.py's own module-isolation check reads this
# file and FAILs when a gated emitter is not guarded by the module that owns it.
#
# TWO emitters are UNCONDITIONAL, and both are unconditional on purpose. The
# compaction hint is the recovery pointer. `check-update` is the notice that the
# governance engine itself changed under the user since their last session, and a
# user who is not told that will trust an install they have not read: silently
# turning it off as a side effect of a size optimisation is the quiet downgrade this
# project exists to refuse. A draft of this lane did gate it behind the release
# module; the measured saving is in references/modules.md, and it did not come close
# to paying for the trust it cost. The release module's own scope therefore EXCLUDES
# this notice, which is why `check-update` is absent from sbe_profile.py's
# STARTUP_EMITTERS and the release row carries DECLARED BUT NOT ENFORCED.
HEAD_OUT="$(
  printf '%s' "$PAYLOAD" | python3 "$DIR/tools/sbe_telemetry.py" compact-hint 2>/dev/null
  if python3 "$DIR/tools/sbe_profile.py" enabled telemetry >/dev/null 2>&1; then
    python3 "$DIR/tools/sbe_telemetry.py" startup-nags 2>/dev/null
  fi
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
