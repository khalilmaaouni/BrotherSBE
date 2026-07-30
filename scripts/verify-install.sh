#!/bin/sh
# verify-install.sh: does an installed copy of this repository match a
# published checksum manifest, byte for byte?
#
# This is the direct answer to "how do I know what I installed". The install
# instruction (docs/RELEASE.md, README.md) clones a git ref into
# ~/.claude/skills/brothersbe, and that code then runs automatically on
# every Claude Code session via hooks. A manifest you cannot check against
# is not a security control, it is a claim; this script is the check. It is
# the same product claim in security form: it refuses to say PASSED over a
# file it never examined, in either direction.
#
# POSIX sh only, no bashisms, same portability intent as checksums.sh. Uses
# no git commands itself, on purpose: it only ever reads the manifest and
# re-hashes the files it names, so it works identically on a plain
# directory copy (no .git present) and on a real clone.
#
# Usage:
#   scripts/verify-install.sh [manifest-file] [installed-dir]
#
#   manifest-file  defaults to <installed-dir>/CHECKSUMS.sha256
#   installed-dir  defaults to this script's own parent repository root
#
# Typical use: you cloned a tagged release into
# ~/.claude/skills/brothersbe. The release ships CHECKSUMS.sha256 at the
# repository root (docs/RELEASE.md explains how a maintainer produces it
# with checksums.sh). Run this with no arguments from inside that clone, or
# point it at any two locations explicitly:
#
#   scripts/verify-install.sh
#   scripts/verify-install.sh /path/to/CHECKSUMS.sha256 ~/.claude/skills/brothersbe

set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
DEFAULT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

TARGET="${2:-$DEFAULT_ROOT}"
MANIFEST="${1:-$TARGET/CHECKSUMS.sha256}"

if [ ! -f "$MANIFEST" ]; then
    echo "verify-install: no manifest found at $MANIFEST" >&2
    echo "verify-install: a maintainer generates one with scripts/checksums.sh" \
         "as part of cutting a release (see docs/RELEASE.md); if this copy" \
         "predates the first manifest, there is nothing to verify against." >&2
    exit 2
fi

if command -v sha256sum >/dev/null 2>&1; then
    hash_file() { sha256sum "$1" | cut -c1-64; }
elif command -v shasum >/dev/null 2>&1; then
    hash_file() { shasum -a 256 "$1" | cut -c1-64; }
else
    echo "verify-install: neither sha256sum nor shasum is on PATH; cannot check anything" >&2
    exit 1
fi

WORKDIR=$(mktemp -d 2>/dev/null || echo "/tmp/sbe-verify-install-work.$$")
mkdir -p "$WORKDIR"
trap 'rm -rf "$WORKDIR"' EXIT INT TERM

OK=0
MISMATCHED=0
MISSING=0
: > "$WORKDIR/manifest_paths"

# Manifest lines are "<64 hex chars><two spaces><path>", the format both
# sha256sum and shasum -a 256 produce. Splitting by fixed column position
# (not by whitespace) is deliberate: a path may itself contain spaces, and
# field-splitting would cut it apart.
while IFS= read -r line; do
    [ -z "$line" ] && continue
    expected=$(printf '%s' "$line" | cut -c1-64)
    path=$(printf '%s' "$line" | cut -c67-)
    [ -z "$path" ] && continue
    printf '%s\n' "$path" >> "$WORKDIR/manifest_paths"
    full="$TARGET/$path"
    if [ ! -f "$full" ]; then
        echo "MISSING:   $path"
        MISSING=$((MISSING + 1))
        continue
    fi
    actual=$(hash_file "$full")
    if [ "$actual" = "$expected" ]; then
        OK=$((OK + 1))
    else
        echo "MISMATCH:  $path"
        MISMATCHED=$((MISMATCHED + 1))
    fi
done < "$MANIFEST"

# Second direction of the check, and the half a one-way comparison silently
# lacks. The loop above only asks "does every file the manifest NAMES match
# on disk", which never notices a file that was ADDED: an extra file is
# neither a MISMATCH nor a MISSING, so a one-direction script reports
# PASSED with a planted file still present, which is a completeness
# sentence over a set it never enumerated. This pass asks the other
# direction: does every file that actually EXISTS on disk appear in the
# manifest. The exclusion list below is the same one scripts/checksums.sh
# applies when it cannot use git (kept in sync by comment in both files,
# since each script is self-contained POSIX sh with no shared file to hold
# this list once): machine state and generated files this project's own
# .gitignore already keeps out of what git tracks, so their absence from
# the manifest is expected, not an added file. Stated limit: if $TARGET
# itself contains a character `find -path` treats as glob syntax
# (*, ?, [ ]), the exclusions below can under- or over-match; named here
# rather than silently assumed correct.
MANIFEST_ABS=$(cd "$(dirname "$MANIFEST")" && pwd)/$(basename "$MANIFEST")
MANIFEST_REL=$(printf '%s\n' "$MANIFEST_ABS" | sed "s|^$TARGET/||")

# Every directory entry, whatever its TYPE, not just `-type f`. A manifest is
# a set of hashes of regular files, and `find -type f` never returns a
# symlink, so a planted tools/backdoor.py that is a SYMLINK to code outside
# the tree was neither a MISMATCH, nor a MISSING, nor an EXTRA: it was
# reported as nothing at all, while it ran automatically like every other
# module and the honesty suite imported and executed it. A control-flow file
# the manifest cannot hash is exactly the shape of a planted backdoor, so
# every non-regular entry (symlink, FIFO, socket) inside the install tree is
# named loudly here, never skipped. `-type f -o -type l -o ...` enumerates
# them all; the type of each is decided per entry below.
# The walk's own failures are CAPTURED, not fatal. Under `set -e` a directory
# find cannot enter made find exit nonzero and killed the script with no
# verdict block printed at all: the exit status was still nonzero, so nothing
# passed silently, but the reader got a bare "Permission denied" and no
# statement of what was and was not checked. A check that could not look says
# so, in its own sentence, and still prints everything it did establish.
find "$TARGET" \( -type f -o -type l -o -type p -o -type s \) \
    ! -path "$TARGET/.git/*" \
    ! -path '*/__pycache__/*' \
    ! -path "$TARGET/.superpowers/*" \
    ! -path "$TARGET/.claude/*" \
    ! -path "$TARGET/.brothermode/*" \
    ! -path "$TARGET/docs/superpowers/*" \
    ! -name '.DS_Store' \
    ! -name '*.pyc' \
    ! -name 'STATE.md' \
    ! -path "$TARGET/.brothersbe/install-receipt.json" \
    ! -path "$TARGET/docs/book/BrotherSBE-for-Dummies.html" \
    ! -path "$TARGET/docs/book/estate/orders.csv" \
    ! -path "$TARGET/docs/book/estate/daily_totals.json" \
    ! -name '~$*' \
    ! -name '*.docx' \
    > "$WORKDIR/installed_raw" 2> "$WORKDIR/walk_errors" || true

DENIED=0
if [ -s "$WORKDIR/walk_errors" ]; then
    DENIED=$(wc -l < "$WORKDIR/walk_errors" | tr -d ' ')
    while IFS= read -r err; do
        [ -z "$err" ] && continue
        echo "UNWALKABLE: $err (this check could not enumerate that location, so no verdict below covers what is inside it)"
    done < "$WORKDIR/walk_errors"
fi

EXTRA=0
NONREGULAR=0
while IFS= read -r full; do
    [ -z "$full" ] && continue
    rel=$(printf '%s\n' "$full" | sed "s|^$TARGET/||")
    [ "$rel" = "$MANIFEST_REL" ] && continue
    # A non-regular entry is a failure in its own right: a manifest is hashes
    # of regular files, and it cannot vouch for what a symlink points at or
    # what a FIFO yields, so a control-flow path this check cannot hash is
    # named rather than measured against a set of hashes it can never be in.
    if [ ! -f "$full" ] || [ -L "$full" ]; then
        echo "NON-REGULAR: $rel (a symlink, pipe, or other non-regular file in the install tree; the manifest hashes regular files only, so it cannot vouch for what this resolves to, and something on this host may run it)"
        NONREGULAR=$((NONREGULAR + 1))
        continue
    fi
    if ! grep -q -x -F "$rel" "$WORKDIR/manifest_paths"; then
        echo "EXTRA:     $rel"
        EXTRA=$((EXTRA + 1))
    fi
done < "$WORKDIR/installed_raw"

# The excluded set is ENUMERATED, not silently assumed empty. The completeness
# sentence below used to claim "no file exists on disk that the manifest does
# not name" with no qualifier, which was false whenever anything sat inside an
# excluded path, and one excluded path (*/__pycache__/*) held files the test
# suite would execute. So: every file the exclusions swallowed on THIS run is
# counted and the first few are named; a file among them whose extension is
# executable source is a failure in its own right, because machine state is
# what the exclusions are for and code is not machine state. .git/ itself is
# not enumerated (it is git's own object store, holding thousands of objects).
# EVERY directory entry, whatever its type, exactly as the first walk does.
# The rule "enumerate regardless of type" was applied to the extra-file walk
# and NOT to this one, so the defect it closed was alive one find-invocation
# later, in the walk whose whole reason for existing is that code inside an
# excluded path is not machine state: a SYMLINK to code planted at
# tools/__pycache__/planted.py was skipped by `-type f` here and excluded by
# path up there, so it was reported as nothing at all and the qualifier
# sentence actively vouched for it ("0 file(s), 0 of them source code",
# PASSED). A non-regular entry inside an excluded path is its own named
# failure: the manifest cannot hash what it points at AND it is not
# enumerable as machine state, which is precisely the shape of a plant.
find "$TARGET" \( -type f -o -type l -o -type p -o -type s \) \
    ! -path "$TARGET/.git/*" \
    \( -path '*/__pycache__/*' \
       -o -path "$TARGET/.superpowers/*" \
       -o -path "$TARGET/.claude/*" \
       -o -path "$TARGET/.brothermode/*" \
       -o -path "$TARGET/docs/superpowers/*" \
       -o -name '.DS_Store' \
       -o -name '*.pyc' \
       -o -name 'STATE.md' \
       -o -path "$TARGET/.brothersbe/install-receipt.json" \
       -o -path "$TARGET/docs/book/BrotherSBE-for-Dummies.html" \
       -o -path "$TARGET/docs/book/estate/orders.csv" \
       -o -path "$TARGET/docs/book/estate/daily_totals.json" \
       -o -name '~$*' \
       -o -name '*.docx' \) \
    > "$WORKDIR/excluded_files" 2>/dev/null || true

EXCLUDED=0
EXCLUDED_SOURCE=0
EXCLUDED_NONREGULAR=0
while IFS= read -r full; do
    [ -z "$full" ] && continue
    rel=$(printf '%s\n' "$full" | sed "s|^$TARGET/||")
    EXCLUDED=$((EXCLUDED + 1))
    if [ ! -f "$full" ] || [ -L "$full" ]; then
        echo "EXCLUDED-NON-REGULAR: $rel (a symlink, pipe, or other non-regular entry inside an excluded path; the manifest cannot hash what it resolves to, the exclusions are for machine state and this is not machine state, and something on this host may execute what it points at)"
        EXCLUDED_NONREGULAR=$((EXCLUDED_NONREGULAR + 1))
        continue
    fi
    case "$rel" in
        *.py|*.sh|*.js|*.rb|*.pl|*.php)
            echo "EXCLUDED-SOURCE: $rel (source code inside an excluded path; the manifest cannot vouch for it and something on this host may execute it)"
            EXCLUDED_SOURCE=$((EXCLUDED_SOURCE + 1))
            ;;
    esac
done < "$WORKDIR/excluded_files"

echo ""
echo "verify-install: checked against $MANIFEST"
echo "verify-install: $OK file(s) match, $MISMATCHED mismatched, $MISSING missing, $EXTRA extra (present on disk, absent from the manifest), $NONREGULAR non-regular (a symlink or pipe the manifest cannot hash)"
if [ "$DENIED" -gt 0 ]; then
    echo "verify-install: $DENIED location(s) could not be enumerated (named UNWALKABLE above), so no sentence here covers what is inside them."
fi
echo "verify-install: the excluded paths (*/__pycache__/*, .superpowers/, docs/superpowers/, .brothersbe/install-receipt.json (the local install record, gitignored because it names this machine's absolute path), the built book and the book estate's two generated data files (all three are build outputs regenerated on every run, never fixtures), and files named .DS_Store, *.pyc, STATE.md, ~\$*, *.docx; .git/ not enumerated) currently hold $EXCLUDED entr(y/ies) of any type, $EXCLUDED_SOURCE of them source code and $EXCLUDED_NONREGULAR of them non-regular (a symlink or pipe this check cannot hash)."

if [ "$MISMATCHED" -gt 0 ] || [ "$MISSING" -gt 0 ] || [ "$EXTRA" -gt 0 ] || [ "$EXCLUDED_SOURCE" -gt 0 ] || [ "$EXCLUDED_NONREGULAR" -gt 0 ] || [ "$NONREGULAR" -gt 0 ] || [ "$DENIED" -gt 0 ]; then
    echo "verify-install: FAILED. Do not trust this installed copy until you" \
         "understand why the files above differ from the published manifest." >&2
    if [ "$EXTRA" -gt 0 ]; then
        echo "verify-install: an EXTRA file is exactly the shape of a" \
             "planted backdoor: it runs automatically along with everything" \
             "else in this installation, and the manifest says nothing" \
             "about it because nothing here declared it." >&2
    fi
    if [ "$NONREGULAR" -gt 0 ]; then
        echo "verify-install: a NON-REGULAR file is the same shape by another" \
             "mechanism: a symlink or pipe the manifest cannot hash, pointing" \
             "at code the manifest never saw, invisible to a check that only" \
             "walked regular files." >&2
    fi
    if [ "$EXCLUDED_SOURCE" -gt 0 ]; then
        echo "verify-install: an EXCLUDED-SOURCE file is the same shape one" \
             "level deeper: source code sitting in a path this check does not" \
             "hash, where an earlier version of this script would have said" \
             "PASSED over it without qualification." >&2
    fi
    if [ "$EXCLUDED_NONREGULAR" -gt 0 ]; then
        echo "verify-install: an EXCLUDED-NON-REGULAR entry is the deepest" \
             "shape of the same plant: a symlink inside an excluded path," \
             "invisible to the extra-file walk (excluded by path) and to a" \
             "\`find -type f\` (skipped by type), so both counts read zero" \
             "while the code it resolves to runs like everything else here." >&2
    fi
    exit 1
fi

echo "verify-install: PASSED. Every file the manifest names matches on disk,"
echo "verify-install: and no file exists on disk that the manifest does not name,"
echo "verify-install: outside the excluded paths enumerated above (their current"
echo "verify-install: file count is printed on every run, and source code among"
echo "verify-install: them fails this check)."
echo "verify-install: a manifest records CONTENT, not file mode: a data file" \
     "that arrived with the execute bit set still matches its hash here, so" \
     "this says the bytes are the published bytes and says nothing about" \
     "permissions."
echo "verify-install: this does not prove the manifest itself is authentic;" \
     "it proves your files match whatever manifest you pointed this at. Get" \
     "the manifest from the release you trust (the tag's git history, or a" \
     "release asset), not from the same untrusted channel as the code."
