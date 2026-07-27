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
#   only from a private ref: refs/brothersbe/autosave/<worktree-id>, where the
#   id is derived from the worktree's own path. Per worktree on purpose: one
#   shared ref meant two worktrees of the same repository overwrote each
#   other's only copy of unlanded work. It never touches your
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
AUTOSAVE_NS="refs/brothersbe/autosave"

# The per-worktree ref for the CURRENT directory's repository. The id is git's
# own hash of the worktree's absolute top-level path (git hash-object): stable
# across runs, different per worktree, and collision-resistant, which the
# earlier cksum CRC-32 id was not: CRC-32 collides across ordinary short
# strings, and two colliding worktree paths would silently share one ref,
# restoring exactly the cross-worktree overwrite this namespacing exists to
# prevent. git is already a hard dependency of every path that reaches this.
autosave_ref() {
  top="$(git rev-parse --show-toplevel 2>/dev/null)"
  [ -n "$top" ] || { printf '%s' "$AUTOSAVE_NS"; return 0; }
  wid="$(printf '%s' "$top" | git hash-object --stdin 2>/dev/null)"
  [ -n "$wid" ] && printf '%s/%s' "$AUTOSAVE_NS" "$wid" || printf '%s' "$AUTOSAVE_NS"
}

# The id an OLDER version of this script derived (cksum CRC-32 of the same
# path). Read-only: recover consults it so a snapshot taken before the id
# changed is found rather than orphaned. Nothing writes here anymore.
legacy_autosave_ref() {
  top="$(git rev-parse --show-toplevel 2>/dev/null)"
  [ -n "$top" ] || { printf '%s' "$AUTOSAVE_NS"; return 0; }
  wid="$(printf '%s' "$top" | cksum 2>/dev/null | awk '{print $1}')"
  [ -n "$wid" ] && printf '%s/%s' "$AUTOSAVE_NS" "$wid" || printf '%s' "$AUTOSAVE_NS"
}
TICK_EVERY="${BROTHERSBE_AUTOSAVE_EVERY:-20}"      # snapshot every N tool calls
RUNAWAY_AT="${BROTHERSBE_RUNAWAY_AT:-600}"         # warn once past this many calls

log_line() {
  # Best-effort append to a local log. Never fail the hook if the disk is full.
  mkdir -p "$TEL_DIR" 2>/dev/null || return 0
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" "$1" \
    >> "$TEL_DIR/autosave.log" 2>/dev/null || true
}

# Snapshot the working tree of $1 into its per-worktree autosave ref. Reason in $2.
# Returns silently on any problem; the caller always exits 0 regardless.
snapshot() {
  repo="$1"; reason="$2"
  cd "$repo" 2>/dev/null || return 0
  # Only meaningful in a git repository; a non-git project is a clean no-op.
  git rev-parse --git-dir >/dev/null 2>&1 || { log_line "skip (not a git repo): $repo"; return 0; }
  # THE SNAPSHOT COVERS THE WORKTREE THE REF NAMES, or it fails loudly. The
  # hook's cwd is wherever the session happened to be (a package directory in
  # a monorepo is the ordinary case), and `git add -A -- '.'` from there
  # staged one subdirectory while the ref was filed under the whole worktree:
  # a complete-looking tree with every out-of-cwd file backfilled at HEAD, so
  # unsaved edits elsewhere read as work that was never done, and a session
  # whose unlanded work sat entirely outside its cwd wrote NO ref and NO log
  # line at the token-death moment. The snapshot runs from the worktree top,
  # always; a top this script cannot resolve or enter is logged, never
  # guessed at.
  top="$(git rev-parse --show-toplevel 2>/dev/null)"
  [ -n "$top" ] || { log_line "SKIPPED (cannot resolve the worktree top from $repo): nothing was saved"; return 0; }
  cd "$top" 2>/dev/null || { log_line "SKIPPED (cannot enter the worktree top $top): nothing was saved"; return 0; }

  # A THROWAWAY index. With GIT_INDEX_FILE pointing at a temp file, `git add -A`
  # stages everything (tracked edits AND untracked new files) into that temp
  # index, so the developer's real index and working tree are never touched.
  # Reserve a unique name, then remove the empty file mktemp created: git rejects
  # a zero-byte index ("index file smaller than expected"), so we let git build a
  # fresh valid index at this path itself.
  tmpidx="$(mktemp 2>/dev/null)" || return 0
  rm -f "$tmpidx"
  GIT_INDEX_FILE="$tmpidx"; export GIT_INDEX_FILE
  parent="$(git rev-parse --verify -q HEAD 2>/dev/null)"
  # Seed the temp index from HEAD first. Without this the snapshot held ONLY
  # what `git add` staged, so a TRACKED file matching an exclusion below was
  # absent from the snapshot entirely, along with any unsaved edit to it: the
  # tool whose purpose is "never lose work" dropped tracked work, and the old
  # comment claimed the opposite ("already-tracked files are unaffected").
  # With the seed, an excluded tracked file rides at its last-committed state.
  # What is still NOT captured, stated plainly: an unsaved edit to an excluded
  # file (the edit may be the secret, so it stays out by design), and any file
  # matching the exclusions that was never committed.
  [ -n "$parent" ] && git read-tree HEAD 2>/dev/null
  # Stage everything EXCEPT secret-shaped files. A solo operator has no teammate to
  # catch a stray .env or private key before it becomes a git object; these path
  # patterns are excluded from the snapshot so credentials never enter the autosave
  # ref. The list names the MODERN key and rc formats too: id_ed25519 has been
  # ssh-keygen's default since OpenSSH 8.5, and a list that stopped at id_rsa
  # captured a fresh private key while this comment promised it would not.
  git add -A -- '.' \
    ':(exclude,glob)**/.env' ':(exclude).env' ':(exclude,glob)**/.env.*' \
    ':(exclude,glob)**/.envrc' ':(exclude).envrc' \
    ':(exclude,glob)**/.netrc' ':(exclude).netrc' \
    ':(exclude,glob)**/.npmrc' ':(exclude).npmrc' \
    ':(exclude,glob)**/*.pem' ':(exclude,glob)**/*.key' ':(exclude,glob)**/*.p12' \
    ':(exclude,glob)**/*.keystore' ':(exclude,glob)**/*.jks' ':(exclude,glob)**/*.ppk' \
    ':(exclude,glob)**/id_rsa' ':(exclude,glob)**/id_dsa' \
    ':(exclude,glob)**/id_ecdsa' ':(exclude,glob)**/id_ed25519' \
    ':(exclude,glob)**/*.pfx' 2>/dev/null
  tree="$(git write-tree 2>/dev/null)"

  # Skip if nothing changed since HEAD (avoid a pile of identical snapshots),
  # and SAY SO: this branch used to return without a log line, so a session
  # whose work was missed for any reason later read "no autosave found" with
  # nothing anywhere recording that the hook fired and chose not to save.
  if [ -n "$parent" ]; then
    head_tree="$(git rev-parse -q --verify "HEAD^{tree}" 2>/dev/null)"
    if [ "$tree" = "$head_tree" ]; then
      rm -f "$tmpidx"; unset GIT_INDEX_FILE
      log_line "no snapshot ($reason): the worktree at $top matches HEAD, nothing unlanded to save"
      return 0
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

  [ -n "$commit" ] || { log_line "SKIPPED ($reason): could not write a snapshot commit in $top"; return 0; }
  # Point the private per-worktree ref at the snapshot. Never touches any
  # branch. --create-reflog: the ref is single-slot, so without a reflog a
  # NEWER snapshot made the older one unreachable and gc-eligible, and the
  # harmful ordering (a good snapshot, then a destructive local action, then
  # a snapshot of the damage) destroyed the only copy of the good one. With
  # the reflog every superseded snapshot stays reachable: git reflog <ref>.
  ref="$(autosave_ref)"
  git update-ref --create-reflog "$ref" "$commit" 2>/dev/null && \
    log_line "saved $commit ($reason) at $ref covering the whole worktree $top"
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
    # SERIALIZED read-modify-write. Parallel tool calls are ordinary and a
    # runaway loop (the exact condition the counter exists to detect) fires
    # hooks concurrently, so the unlocked increment lost updates: the
    # throttle skipped snapshot points and the runaway warning printed a
    # count materially below the real one, understating most in exactly the
    # case it is written for. mkdir is the POSIX-portable atomic lock. The
    # wait is bounded (never blocks work); a lock that outlives the wait is
    # presumed dead (ticks are subsecond) and is broken once; if even that
    # fails, this tick is SKIPPED WITH A LOG LINE rather than writing a
    # number nothing measured.
    lock="$ctr.lock"
    tries=0
    until mkdir "$lock" 2>/dev/null; do
      tries=$((tries + 1))
      if [ "$tries" -ge 40 ]; then
        rmdir "$lock" 2>/dev/null
        if ! mkdir "$lock" 2>/dev/null; then
          log_line "tick skipped for $sid: could not take $lock; the count was not incremented"
          exit 0
        fi
        break
      fi
      sleep 0.05 2>/dev/null || sleep 1
    done
    n="$(cat "$ctr" 2>/dev/null)"; n="${n:-0}"; n=$((n + 1))
    printf '%s' "$n" > "$ctr" 2>/dev/null
    # The warned marker is written INSIDE the lock, so two hooks crossing
    # the threshold together cannot both print the warning.
    warn=0
    if [ "$n" -ge "$RUNAWAY_AT" ] && [ ! -f "$ctr.warned" ]; then
      : > "$ctr.warned" 2>/dev/null
      warn=1
    fi
    rmdir "$lock" 2>/dev/null
    # Throttle: only snapshot every Nth tool call, so this stays cheap.
    if [ $((n % TICK_EVERY)) -eq 0 ]; then
      snapshot "$repo" "tick $n"
    fi
    # Runaway warning, once per session (a very long session is a loop smell).
    if [ "$warn" -eq 1 ]; then
      printf '{"systemMessage":"BrotherSBE: this session has made %s tool calls, which can signal an unbounded loop. Consider whether a circuit breaker (section 7) should fire. Your work is autosaved under %s/ (sbe_autosave.sh recover prints the path)."}\n' "$n" "$AUTOSAVE_NS"
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
    # Resolved for THIS worktree; a sibling worktree's snapshots are its own.
    ref="$(autosave_ref)"
    sha="$(git rev-parse -q --verify "$ref" 2>/dev/null)"
    if [ -z "$sha" ]; then
      # A snapshot written by an older version of this script lives under the
      # cksum-derived id; read it rather than orphaning saved work.
      legacy="$(legacy_autosave_ref)"
      sha="$(git rev-parse -q --verify "$legacy" 2>/dev/null)"
      [ -n "$sha" ] && ref="$legacy"
    fi
    if [ -z "$sha" ]; then
      # A snapshot taken before refs were namespaced per worktree lives at the
      # old shared name; read it rather than orphaning saved work.
      sha="$(git rev-parse -q --verify "$AUTOSAVE_NS" 2>/dev/null)"
      [ -n "$sha" ] && ref="$AUTOSAVE_NS"
    fi
    if [ -z "$sha" ]; then
      # The sentence describes the NAMESPACE, not the one computed guess. The
      # id is derived from the worktree's absolute path, so a moved or
      # renamed project changes the id, and "no autosave found in <repo>"
      # was false about a repository holding the snapshot one for-each-ref
      # away: the check reported a conclusion wider than what it examined.
      others="$(git for-each-ref --format='%(refname) -> %(objectname)' "$AUTOSAVE_NS" 2>/dev/null)"
      if [ -n "$others" ]; then
        echo "sbe_autosave: no autosave under this worktree's current id (ref $ref is empty),"
        echo "  but this repository DOES hold autosave snapshot(s) under other id(s), which is"
        echo "  what a moved or renamed worktree looks like (the id derives from the path):"
        printf '%s\n' "$others" | sed 's/^/    /'
        echo "  Inspect one:  git log --oneline -1 <ref>"
        echo "  Recover one:  git worktree add --detach <new-empty-dir> <ref>"
        exit 0
      fi
      echo "sbe_autosave: no autosave found in $repo (ref $ref is empty, and nothing else exists under $AUTOSAVE_NS/)."
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
    echo "  Older superseded snapshots, if any, are listed by: git -C $repo reflog $ref"
    ;;

  *)
    echo "usage: sbe_autosave.sh {precompact|tick <session_id>|recover [repo]}"
    ;;
esac
exit 0
