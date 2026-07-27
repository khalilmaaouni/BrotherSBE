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
  #
  # The stderr redirection is ordered BEFORE the append, not after it. Written
  # the other way round, the shell processes redirections left to right, so
  # the failing append emitted the shell's own diagnostic to a stderr that was
  # not yet silenced: on an unwritable vault this printed a raw permission
  # error on every single tool call, out of the one primitive the whole file
  # relies on to be quiet. Same ordering defect as the one that made the tick
  # fatal, in the function that was supposed to be the safe way to do it.
  mkdir -p "$TEL_DIR" 2>/dev/null || return 0
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" "$1" \
    2>/dev/null >> "$TEL_DIR/autosave.log" || true
}

touch_file() {
  # Create or truncate $1, best effort, NEVER fatal, and never noisy.
  #
  # This exists because `: > "$f" 2>/dev/null` was written twice. `:` is a
  # POSIX SPECIAL BUILTIN, and a redirection error on a special builtin is
  # fatal to the shell, so on an unwritable telemetry directory the tick died
  # at that statement: before the lock, before the counter, before any
  # log_line, with no snapshot, no log sentence anywhere, and exit 1 out of a
  # script whose own header promises that every path exits 0. Twelve
  # consecutive ticks produced twelve exit 1s and zero log lines. The
  # `2>/dev/null` was written AFTER the failing redirection as well, so the
  # shell's own diagnostic printed too.
  #
  # `printf` is a REGULAR builtin, where a redirection error sets a status
  # instead of killing the shell, and the stderr redirection is ordered FIRST
  # so it is already in place when the failing one is processed. The rule, and
  # it is the file's existing rule stated for the whole class: every touch of
  # the telemetry directory goes through a primitive that returns a status,
  # like log_line above, because this hook may never be the reason work stops.
  printf '' 2>/dev/null > "$1" || return 1
}

writable_telemetry() {
  # Whether this run can write its own telemetry directory, established ONCE.
  # A hook that cannot write there cannot keep the counter that throttles
  # continuous autosave, and the honest thing is to say so and stand down
  # rather than to discover it mid-statement.
  mkdir -p "$TEL_DIR" 2>/dev/null || return 1
  touch_file "$TEL_DIR/.writable.$$" || return 1
  rm -f "$TEL_DIR/.writable.$$" 2>/dev/null
  return 0
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
    # Established once, at the top, before anything touches the directory: an
    # unwritable or uncreatable telemetry directory used to be discovered by a
    # statement that killed the shell. The counter cannot be kept without it,
    # and a snapshot decision made from a number nothing measured is the
    # sentence this project refuses everywhere else, so the tick stands down
    # and says why, on the same log_line path every other skip uses.
    if ! writable_telemetry; then
      log_line "tick skipped for $sid: the telemetry directory $TEL_DIR cannot be created or written, so the tick counter cannot be kept and no snapshot decision is made from a number nothing measured. Continuous autosave is OFF for this session until that directory is writable"
      exit 0
    fi
    # SERIALIZED read-modify-write. Parallel tool calls are ordinary and a
    # runaway loop (the exact condition the counter exists to detect) fires
    # hooks concurrently, so the unlocked increment lost updates: the
    # throttle skipped snapshot points and the runaway warning printed a
    # count materially below the real one, understating most in exactly the
    # case it is written for. mkdir is the POSIX-portable atomic lock. The
    # wait is bounded (never blocks work). A lock that outlives the whole
    # wait AND predates it is presumed dead and is broken ONCE, with a log
    # line naming the break; a lock created DURING the wait is a live,
    # contended lock (writers are churning), and breaking a live holder puts
    # two writers in the section, so that tick is skipped with a log line
    # instead. If even the break fails, the tick is SKIPPED WITH A LOG LINE
    # rather than writing a number nothing measured.
    lock="$ctr.lock"
    stamp="$ctr.waitstamp.$$"
    touch_file "$stamp"
    tries=0
    until mkdir "$lock" 2>/dev/null; do
      tries=$((tries + 1))
      if [ "$tries" -ge 40 ]; then
        if [ -e "$stamp" ] && [ "$lock" -nt "$stamp" ]; then
          rm -f "$stamp" 2>/dev/null
          log_line "tick skipped for $sid: $lock is live and contended (it was created during this tick's wait, so its holder is not dead); the count was not incremented"
          exit 0
        fi
        rmdir "$lock" 2>/dev/null
        log_line "broke a stale lock for $sid: $lock predates this tick's whole wait and its holder is presumed dead; if that presumption is ever wrong this line is the evidence"
        if ! mkdir "$lock" 2>/dev/null; then
          rm -f "$stamp" 2>/dev/null
          log_line "tick skipped for $sid: could not take $lock; the count was not incremented"
          exit 0
        fi
        break
      fi
      sleep 0.05 2>/dev/null || sleep 1
    done
    rm -f "$stamp" 2>/dev/null
    # The lock is released by the EXIT trap on every path out of the critical
    # section, so no exit can leak the lock directory and wedge the session;
    # the trap is cleared right after the manual release below, so it can
    # never remove a lock a LATER writer has since taken.
    trap 'rmdir "$lock" 2>/dev/null' EXIT
    # Content read back from a file is untrusted input: the counter is
    # validated as digits BEFORE arithmetic. A non-numeric counter used to
    # reach $((n + 1)) and kill the hook with a raw bash diagnostic and exit
    # 1, leaking the lock and wedging the session forever, inside a script
    # whose header promises every path exits 0. An empty counter (a writer
    # killed between truncate and write) used to restart the count silently.
    # Both are now a NAMED reset with a log line.
    n="$(cat "$ctr" 2>/dev/null)"
    case "$n" in
      "")
        [ -f "$ctr" ] && log_line "counter for $sid was empty (a writer died mid-write); count reset to 0"
        n=0 ;;
      *[!0-9]*)
        log_line "counter for $sid held non-numeric content; count reset to 0"
        n=0 ;;
      *)
        # Strip leading zeros so shell arithmetic cannot read 08 as bad octal.
        n="$(printf '%s' "$n" | sed 's/^00*//')"; n="${n:-0}" ;;
    esac
    n=$((n + 1))
    # The counter write is a boundary call like any other: checked, and on
    # failure this tick takes the same path the lock timeout takes (a named
    # skip with a log line). The unchecked write turned continuous autosave
    # silently OFF when the counter was unwritable: the counter never
    # advanced, n recomputed to the same value every tick, n % TICK_EVERY
    # never hit zero, and 25 ticks with real unlanded work produced zero
    # snapshots, zero log lines and exit 0.
    if ! printf '%s' "$n" 2>/dev/null > "$ctr"; then
      log_line "tick skipped for $sid: could not write the counter $ctr; the count was not recorded, so no snapshot decision is made from a number nothing measured. Continuous autosave is OFF for this session until the counter is writable"
      exit 0
    fi
    # The warned marker is written INSIDE the lock, so two hooks crossing
    # the threshold together cannot both print the warning.
    warn=0
    if [ "$n" -ge "$RUNAWAY_AT" ] && [ ! -f "$ctr.warned" ]; then
      touch_file "$ctr.warned"
      warn=1
    fi
    rmdir "$lock" 2>/dev/null
    trap - EXIT
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
