#!/bin/sh
# ---------------------------------------------------------------------------
# BrotherSBE autosave: mechanical work-preservation.
#
# WHY THIS EXISTS
#   Every "never lose work" rule in the constitution (disk-first, checkpoint at
#   green, "any kill is resumable") is PROSE the model must remember to run. But
#   the moment work is most likely to be erased, running out of tokens (which
#   triggers a context compaction) or failing over and over, is exactly the
#   moment the model is least able to remember anything. So the rule "save before
#   you die" was being executed by the actor that is dying. This script closes
#   that hole mechanically: the harness fires it, not the model.
#
# WHAT IT DOES
#   Takes a snapshot of the ENTIRE working tree, including untracked (new) files,
#   which are the most-likely-lost work, and stores it as a git commit reachable
#   only from a private ref: refs/brothersbe/autosave. It never touches your
#   branch, your index, or your working tree, and it NEVER pushes anywhere. The
#   snapshot is local git only, so the audited zero-network property still holds.
#
# INVARIANTS (do not break these)
#   - Never blocks work: every path exits 0, always.
#   - No network: runs git locally only, never `git push`, never a remote.
#   - Non-invasive: uses a throwaway temp index (GIT_INDEX_FILE) so the real
#     index and working tree are never modified; only a custom ref is written.
#
# MODES
#   precompact   run from the PreCompact hook (fires right before a compaction,
#                i.e. the token-death moment). Snapshots once.
#   tick         run from the PostToolUse hook, OPT-IN via BROTHERSBE_AUTOSAVE.
#                Snapshots every N tool calls and warns once on a runaway session.
#   recover      print exactly how to get the saved work back. A save with no
#                restore is a half-feature, so this mode is not optional.
# ---------------------------------------------------------------------------

# Vault telemetry dir: same location sbe_telemetry.py uses, for the log + counters.
VAULT="${BROTHERSBE_VAULT:-$HOME/BrotherSBEVault}"
TEL_DIR="$VAULT/99-System/telemetry"
AUTOSAVE_REF="refs/brothersbe/autosave"
TICK_EVERY="${BROTHERSBE_AUTOSAVE_EVERY:-20}"      # snapshot every N tool calls
RUNAWAY_AT="${BROTHERSBE_RUNAWAY_AT:-600}"         # warn once past this many calls

log_line() {
  # Best-effort append to a local log. Never fail the hook if the disk is full.
  mkdir -p "$TEL_DIR" 2>/dev/null || return 0
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" "$1" \
    >> "$TEL_DIR/autosave.log" 2>/dev/null || true
}

# Snapshot the working tree of $1 into refs/brothersbe/autosave. Reason in $2.
# Returns silently on any problem; the caller always exits 0 regardless.
snapshot() {
  repo="$1"; reason="$2"
  cd "$repo" 2>/dev/null || return 0
  # Only meaningful in a git repository; a non-git project is a clean no-op.
  git rev-parse --git-dir >/dev/null 2>&1 || { log_line "skip (not a git repo): $repo"; return 0; }

  # A THROWAWAY index. With GIT_INDEX_FILE pointing at a temp file, `git add -A`
  # stages everything (tracked edits AND untracked new files) into that temp
  # index, so the developer's real index and working tree are never touched.
  # Reserve a unique name, then remove the empty file mktemp created: git rejects
  # a zero-byte index ("index file smaller than expected"), so we let git build a
  # fresh valid index at this path itself.
  tmpidx="$(mktemp 2>/dev/null)" || return 0
  rm -f "$tmpidx"
  GIT_INDEX_FILE="$tmpidx"; export GIT_INDEX_FILE
  # Stage everything EXCEPT secret-shaped files. A solo operator has no teammate to
  # catch a stray .env or private key before it becomes a git object; these path
  # patterns are excluded from the snapshot so credentials never enter the autosave
  # ref. Already-tracked files are unaffected (that is a pre-existing repo choice).
  git add -A -- '.' \
    ':(exclude,glob)**/.env' ':(exclude).env' ':(exclude,glob)**/.env.*' \
    ':(exclude,glob)**/*.pem' ':(exclude,glob)**/*.key' ':(exclude,glob)**/*.p12' \
    ':(exclude,glob)**/*.keystore' ':(exclude,glob)**/id_rsa' ':(exclude,glob)**/id_dsa' \
    ':(exclude,glob)**/*.pfx' 2>/dev/null
  tree="$(git write-tree 2>/dev/null)"
  parent="$(git rev-parse --verify -q HEAD 2>/dev/null)"

  # Skip if nothing changed since HEAD (avoid a pile of identical snapshots).
  if [ -n "$parent" ]; then
    head_tree="$(git rev-parse -q --verify "HEAD^{tree}" 2>/dev/null)"
    if [ "$tree" = "$head_tree" ]; then
      rm -f "$tmpidx"; unset GIT_INDEX_FILE; return 0
    fi
  fi

  if [ -n "$tree" ]; then
    if [ -n "$parent" ]; then
      commit="$(git commit-tree "$tree" -p "$parent" -m "brothersbe autosave: $reason" 2>/dev/null)"
    else
      # Fresh repo with no commits yet: no parent to point at.
      commit="$(git commit-tree "$tree" -m "brothersbe autosave: $reason" 2>/dev/null)"
    fi
  fi
  rm -f "$tmpidx"; unset GIT_INDEX_FILE

  [ -n "$commit" ] || return 0
  # Point the private ref at the snapshot. Never touches any branch.
  git update-ref "$AUTOSAVE_REF" "$commit" 2>/dev/null && \
    log_line "saved $commit ($reason) in $repo"
}

# Read the cwd the hook was invoked for out of its JSON stdin payload. Falls
# back to $PWD. Uses python only to parse JSON; no network, no git here.
hook_cwd() {
  payload="$(cat 2>/dev/null)"
  cwd="$(printf '%s' "$payload" | python3 -c \
    'import json,sys;
try: print((json.load(sys.stdin) or {}).get("cwd",""))
except Exception: print("")' 2>/dev/null)"
  [ -n "$cwd" ] && printf '%s' "$cwd" || printf '%s' "$PWD"
}

case "$1" in
  precompact)
    # Fired right before the context is compacted (the token-death moment).
    repo="$(hook_cwd)"
    snapshot "$repo" "precompact"
    ;;

  tick)
    # OPT-IN continuous autosave for the death that is NOT a compaction (a hard
    # kill or crash mid-build). Off unless BROTHERSBE_AUTOSAVE is set.
    [ -n "$BROTHERSBE_AUTOSAVE" ] || exit 0
    repo="$(hook_cwd)"
    sid="${2:-session}"
    ctr="$TEL_DIR/.autosave-tick-$(printf '%s' "$sid" | tr -c 'A-Za-z0-9_-' '_')"
    mkdir -p "$TEL_DIR" 2>/dev/null
    n="$(cat "$ctr" 2>/dev/null)"; n="${n:-0}"; n=$((n + 1))
    printf '%s' "$n" > "$ctr" 2>/dev/null
    # Throttle: only snapshot every Nth tool call, so this stays cheap.
    if [ $((n % TICK_EVERY)) -eq 0 ]; then
      snapshot "$repo" "tick $n"
    fi
    # Runaway warning, once per session (a very long session is a loop smell).
    if [ "$n" -ge "$RUNAWAY_AT" ] && [ ! -f "$ctr.warned" ]; then
      : > "$ctr.warned" 2>/dev/null
      printf '{"systemMessage":"BrotherSBE: this session has made %s tool calls, which can signal an unbounded loop. Consider whether a circuit breaker (section 7) should fire. Your work is autosaved at %s."}\n' "$n" "$AUTOSAVE_REF"
    fi
    ;;

  recover)
    # Get the saved work back WITHOUT touching the live working tree. An
    # earlier version printed an in-place `git restore --source=<ref>
    # --worktree .` command, which can DELETE a tracked file the snapshot
    # never captured; a recovery path that can destroy work is worse than
    # none. This mode now checks the snapshot out into a NEW detached
    # worktree at a temporary path. It does NOT modify your files, your
    # index, or your branch: you copy back what you want, by hand.
    repo="${2:-$PWD}"
    cd "$repo" 2>/dev/null || { echo "sbe_autosave: cannot enter $repo"; exit 0; }
    sha="$(git rev-parse -q --verify "$AUTOSAVE_REF" 2>/dev/null)"
    if [ -z "$sha" ]; then
      echo "sbe_autosave: no autosave found in $repo (ref $AUTOSAVE_REF is empty)."
      exit 0
    fi
    # mktemp -d creates the directory at mode 0700 (owner-only). The chmod is
    # defense in depth, not the load-bearing half. The directory is NOT
    # removed before `git worktree add`: git accepts an existing empty
    # directory and leaves its mode alone, so there is no window where the
    # checkout could land at the process umask instead of owner-only.
    tmpdir="$(mktemp -d 2>/dev/null)" || { echo "sbe_autosave: could not create a temporary directory."; exit 0; }
    chmod 700 "$tmpdir" 2>/dev/null
    if ! git worktree add --detach "$tmpdir" "$sha" >/dev/null 2>&1; then
      rmdir "$tmpdir" 2>/dev/null
      echo "sbe_autosave: could not create a recovery worktree for $sha."
      exit 0
    fi
    # Report the mode the platform actually gave, not the one we asked for.
    perms="$(ls -ld "$tmpdir" 2>/dev/null | awk '{print $1}')"
    echo "sbe_autosave: recovered snapshot $sha into a NEW worktree at:"
    echo "  $tmpdir"
    echo "  permissions: $perms (owner-only intended; this line reports what the platform gave, it does not promise enforcement on platforms that ignore POSIX modes)"
    echo "  Your live working tree at $repo was never touched. Inspect the folder"
    echo "  above, copy back what you need, then remove it with:"
    echo "  git -C $repo worktree remove $tmpdir"
    ;;

  *)
    echo "usage: sbe_autosave.sh {precompact|tick <session_id>|recover [repo]}"
    ;;
esac
exit 0
