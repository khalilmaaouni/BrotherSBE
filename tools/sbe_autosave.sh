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
# WHAT IT DOES NOT DO
#   A snapshot is a permanent git object. Every candidate file's CONTENT is read
#   before `git add` runs, and a file whose content matches a secret shape, or
#   that is too large or too binary to scan, is kept out and written down in
#   $EXCL_LOG with its reason. That is pattern matching, not a guarantee: a
#   secret in a shape these patterns do not know still enters the snapshot. And
#   the ref is local, which is not the same as private: a backup, a mirror, or
#   any process that copies .git can carry it off this machine.
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

# ---------------------------------------------------------------------------
# THE CONTENT SCAN. Excluding secret-shaped FILE NAMES was never a control over
# secrets: a credential lives in a normally named source file at least as often
# as in a file called .env, and `src/config.py` matches no name pattern anybody
# will ever write. Every candidate file's CONTENT is now read before `git add`
# runs, which is the moment a blob would be created, so a file the scan rejects
# never becomes a git object at all. Rejecting it is not free (the file is left
# out of the snapshot, and an unlanded edit to it is not preserved), so every
# rejection is written down with its reason in $EXCL_LOG.
#
# Three reject conditions besides the name patterns, and the second and third
# are limits rather than detections, which is why they are recorded the same
# way: content matching a secret shape, a file past the size limit (never
# scanned), and a binary file (this scanner cannot read one for secret shapes).
# A candidate whose path git could not print literally is rejected too: a file
# the scanner could not open must never be treated as scanned and clean.
# ---------------------------------------------------------------------------
MAX_BYTES="${BROTHERSBE_AUTOSAVE_MAX_BYTES:-1048576}"       # scan limit, per file
MAX_EXCLUSIONS="${BROTHERSBE_AUTOSAVE_MAX_EXCLUSIONS:-200}" # past this, refuse to snapshot
EXCL_LOG="$TEL_DIR/autosave-exclusions.log"
SECRET_SHAPES='(sk|rk)[-_][A-Za-z0-9_-]{12,}|gh[oprsu]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,}|-----BEGIN[ A-Z]*PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'
SECRET_ASSIGNMENTS='(pass(word|wd|phrase)?|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|credential)s?[[:space:]]*[:=][[:space:]]*.?[A-Za-z0-9/+_=-]{8,}|bearer[[:space:]]+[A-Za-z0-9._~+/=-]{16,}'
# The name patterns, kept as a pathspec list for the `git add` below AND read by
# secret_named() for the record. Two readers, one list, so a name excluded from
# the snapshot is a name the record explains.
STATIC_EXCLUDES="':(exclude,glob)**/.env' ':(exclude).env' ':(exclude,glob)**/.env.*' \
':(exclude,glob)**/.envrc' ':(exclude).envrc' \
':(exclude,glob)**/.netrc' ':(exclude).netrc' \
':(exclude,glob)**/.npmrc' ':(exclude).npmrc' \
':(exclude,glob)**/*.pem' ':(exclude,glob)**/*.key' ':(exclude,glob)**/*.p12' \
':(exclude,glob)**/*.keystore' ':(exclude,glob)**/*.jks' ':(exclude,glob)**/*.ppk' \
':(exclude,glob)**/id_rsa' ':(exclude,glob)**/id_dsa' \
':(exclude,glob)**/id_ecdsa' ':(exclude,glob)**/id_ed25519' \
':(exclude,glob)**/*.pfx'"

excl_record() {
  # The exclusion record. Paths and reasons only, never the matched content: a
  # record of what was kept out of a snapshot must not become the place the
  # secret is written down. Owner-only, best effort, never fatal.
  mkdir -p "$TEL_DIR" 2>/dev/null || return 0
  if [ ! -f "$EXCL_LOG" ]; then
    touch_file "$EXCL_LOG" || return 0
    chmod 600 "$EXCL_LOG" 2>/dev/null
  fi
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" "$1" \
    2>/dev/null >> "$EXCL_LOG" || true
}

secret_named() {
  case "${1##*/}" in
    .env|.env.*|.envrc|.netrc|.npmrc) return 0 ;;
    id_rsa|id_dsa|id_ecdsa|id_ed25519) return 0 ;;
    *.pem|*.key|*.p12|*.keystore|*.jks|*.ppk|*.pfx) return 0 ;;
  esac
  return 1
}

is_binary() {
  # A NUL byte in the first 4096 bytes. dd and tr are POSIX; the byte counts
  # come back through command substitution as numbers, so no NUL ever passes
  # through a shell variable.
  raw="$(dd if="$1" bs=4096 count=1 2>/dev/null | wc -c | tr -d ' 	')"
  txt="$(dd if="$1" bs=4096 count=1 2>/dev/null | tr -d '\000' | wc -c | tr -d ' 	')"
  [ "$raw" != "$txt" ]
}

scan_exclude() {
  # Record one rejection and add it to the pathspec list `git add` will receive.
  # Single quotes inside a path are escaped so the eval below cannot be turned
  # into a command by a filename.
  excluded=$((excluded + 1))
  q="$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
  EXCL_ARGS="$EXCL_ARGS ':(exclude,literal)$q'"
  excl_record "  excluded $1 :: $2"
}

production_repo() {
  # A repository the operator has DECLARED production. Autosave is opt-in there:
  # a snapshot of production work is still a private git object holding whatever
  # the worktree held, and that is a decision for the person who owns the
  # repository rather than a default. Prints the marker it read.
  case "$(printf '%s' "${BROTHERSBE_REPO_CLASS:-}" | tr 'A-Z' 'a-z')" in
    production|prod)
      printf '%s' "BROTHERSBE_REPO_CLASS=$BROTHERSBE_REPO_CLASS"; return 0 ;;
  esac
  if [ -f "$1/.brothersbe-production" ]; then
    printf '%s' "$1/.brothersbe-production"; return 0
  fi
  return 1
}

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

  # OPT-IN IN A PRODUCTION REPOSITORY. Declared with BROTHERSBE_REPO_CLASS or a
  # .brothersbe-production file at the worktree top; enabled with
  # BROTHERSBE_AUTOSAVE_PRODUCTION. The skip names both, so nobody has to guess
  # which of the two is missing.
  marker="$(production_repo "$top")" && {
    case "$(printf '%s' "${BROTHERSBE_AUTOSAVE_PRODUCTION:-}" | tr 'A-Z' 'a-z')" in
      1|true|yes|on) : ;;
      *)
        log_line "SKIPPED ($reason): $top is declared a production repository by $marker, where autosave is opt-in; nothing was saved. Set BROTHERSBE_AUTOSAVE_PRODUCTION=1 to enable it there"
        return 0 ;;
    esac
  }

  # THE CONTENT SCAN RUNS BEFORE ANY GIT OBJECT EXISTS. `git add` is what writes
  # blobs, so a file rejected here is never turned into one, which is the whole
  # difference between this and a path exclusion applied after the fact.
  cand="$(mktemp 2>/dev/null)" || { log_line "SKIPPED ($reason): no temporary file for the content scan in $top; nothing was saved"; return 0; }
  git ls-files --cached --others --exclude-standard > "$cand" 2>/dev/null
  scanned=0
  excluded=0
  EXCL_ARGS=""
  excl_record "scan ($reason) at $top:"
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    case "$f" in
      '"'*)
        scan_exclude "$f" "git printed this path quoted (it holds a newline, a quote or a control character), so the scanner could not open it and will not call it scanned"
        continue ;;
    esac
    if [ -L "$f" ]; then
      continue          # a symlink is stored as its target string, not as content
    fi
    [ -f "$f" ] || continue
    scanned=$((scanned + 1))
    if secret_named "$f"; then
      scan_exclude "$f" "the file name is one of the secret-shaped names"
      continue
    fi
    size="$(wc -c < "$f" 2>/dev/null | tr -d ' 	')"
    case "$size" in
      ''|*[!0-9]*)
        scan_exclude "$f" "its size could not be read, so its content was never scanned"
        continue ;;
    esac
    if [ "$size" -gt "$MAX_BYTES" ]; then
      scan_exclude "$f" "$size bytes, past the $MAX_BYTES byte limit, so its content was never scanned"
      continue
    fi
    if is_binary "$f"; then
      scan_exclude "$f" "binary content, which this scanner cannot read for secret shapes"
      continue
    fi
    if LC_ALL=C grep -Eq -- "$SECRET_SHAPES" "$f" 2>/dev/null ||
       LC_ALL=C grep -Eqi -- "$SECRET_ASSIGNMENTS" "$f" 2>/dev/null; then
      scan_exclude "$f" "content matched a secret shape"
      continue
    fi
  done < "$cand"
  rm -f "$cand"
  excl_record "  scanned $scanned candidate file(s), excluded $excluded"
  if [ "$excluded" -gt "$MAX_EXCLUSIONS" ]; then
    # Fail closed. Past this many pathspecs the single `git add` below can
    # exceed the argument limit, and a failed add produces an EMPTY tree that
    # would then be committed as if it were the work: refusing loudly is the
    # only honest branch, and the record already names every file.
    log_line "SKIPPED ($reason): the content scan excluded $excluded of $scanned candidate file(s) in $top, past the $MAX_EXCLUSIONS this script will pass to git in one command; nothing was saved. Read $EXCL_LOG, then raise BROTHERSBE_AUTOSAVE_MAX_EXCLUSIONS if those exclusions are expected"
    return 0
  fi

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
  # Stage everything EXCEPT what the name patterns and the content scan reject.
  # A solo operator has no teammate to catch a stray .env or private key before
  # it becomes a git object. The name list names the MODERN key and rc formats
  # too: id_ed25519 has been ssh-keygen's default since OpenSSH 8.5, and a list
  # that stopped at id_rsa captured a fresh private key while an earlier version
  # of this comment promised it would not.
  #
  # WHAT THE NAME PATTERNS DO NOT DO, stated here because this comment used to
  # claim the opposite ("so credentials never enter the autosave ref"): a name
  # pattern cannot see a secret in a normally named file, which is where most
  # of them live. That is the content scan's job, above, and even the content
  # scan is pattern matching over the shapes it knows. Neither is a guarantee.
  # docs/KNOWN-LIMITS.md and SECURITY.md carry the full statement.
  #
  # The name patterns and everything the content scan rejected, in one command.
  # eval is what lets a list built at runtime reach git as separate arguments in
  # a shell with no arrays; every path in EXCL_ARGS was single-quoted by
  # scan_exclude with its own quotes escaped, so a filename cannot become a
  # command here.
  eval "git add -A -- '.' $STATIC_EXCLUDES $EXCL_ARGS" 2>/dev/null
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
    log_line "saved $commit ($reason) at $ref covering the whole worktree $top, minus $excluded of $scanned scanned file(s) the content scan rejected (each named with its reason in $EXCL_LOG)"
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
    if [ -f "$EXCL_LOG" ]; then
      echo "  What the snapshot does NOT hold: every file the content scan rejected is named,"
      echo "  with its reason, in $EXCL_LOG. Those files were never copied anywhere; they are"
      echo "  still in your working tree, and any unsaved edit to one of them is only there."
    else
      echo "  No exclusion record exists at $EXCL_LOG, so no snapshot in this vault has"
      echo "  rejected a file yet, or the record was removed."
    fi
    ;;

  *)
    echo "usage: sbe_autosave.sh {precompact|tick <session_id>|recover [repo]}"
    ;;
esac
exit 0
