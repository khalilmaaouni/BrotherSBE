#!/bin/sh
# test-upgrade-rollback.sh: does upgrading from the previous published tag to
# HEAD, then rolling back to that previous tag, work with nothing more than
# "install, verify, install again, verify, install the old one back, verify"?
#
# What "install" means here, deliberately: the same `git archive <ref> | tar
# x` an operator running docs/RELEASE.md's pin command effectively gets
# (nothing in this project documents an in-place `git pull` upgrade yet), so
# every step below wipes the target directory and re-extracts fresh, rather
# than extracting a newer archive OVER an older one's leftover files. That
# is a stated scope decision, not a silently assumed one: this script proves
# "the previous tag, then HEAD, then the previous tag again each install
# clean and verify clean", not "extracting a newer archive over an older
# checkout in place never leaves a stale file", which is a different claim
# this script does not make.
#
# The kill criterion the plugin conversion plan states for this wave is "an
# install that needs a manual global settings edit"; every install below
# writes only inside one temporary directory this script creates and
# removes on exit, the same discipline scripts/test-install-artifact.sh
# holds itself to.
#
# The honesty this script exists to enforce: as of this wave, this
# repository has never cut a tag (docs/RELEASE.md says so plainly; `main` at
# commit 1c86c9d predates tagging entirely). An upgrade-and-rollback test
# with no previous release to upgrade FROM cannot exercise an upgrade, and a
# script that reported PASSED anyway, or silently skipped with exit 0 and no
# explanation, would be claiming a control ran when it did not. So: when no
# previous tag exists, this prints a NO-DATA verdict naming the reason and
# exits 0 without ever claiming an upgrade was tested. Exit 0 here means
# "nothing failed", the same as everywhere else in this project; it does
# NOT mean "passed". No unit suite asserts this branch, deliberately: the
# moment this repository cuts its first tag the branch stops being
# reachable here, and a suite pinned to it would rot. The honesty was
# exercised directly while this script was calibrated (docs/ROLLOUT.md
# names where), and the sentence it prints says exactly what was not run.
#
# Runs identically from a normal `git clone` and from a git worktree (see
# scripts/test-install-artifact.sh's header for why: `git archive` and
# `git tag`/`git describe` resolve through git's own plumbing, never by
# reading the .git path's type directly).
#
# POSIX sh only, no bashisms. Calls scripts/verify-install.sh rather than
# reimplementing it, same as scripts/test-install-artifact.sh.
#
# Usage:
#   scripts/test-upgrade-rollback.sh

set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$ROOT"

# Find the most recent tag that is an ANCESTOR of HEAD, i.e. a real previous
# release on this line of history, not a tag sitting on an unrelated branch
# or pointing at HEAD itself. `git tag --list` can be empty (today, always);
# guarded explicitly rather than let a bare `for` over an empty command
# substitution misbehave under `set -e` on some shells.
PREV_TAG=""
ALL_TAGS=$(git tag --list 2>/dev/null || true)
if [ -n "$ALL_TAGS" ]; then
    for t in $ALL_TAGS; do
        if ! git merge-base --is-ancestor "$t" HEAD 2>/dev/null; then
            continue
        fi
        if [ "$(git rev-parse "$t^{commit}" 2>/dev/null)" = "$(git rev-parse HEAD)" ]; then
            continue
        fi
        if [ -z "$PREV_TAG" ]; then
            PREV_TAG="$t"
        else
            t_date=$(git log -1 --format=%ct "$t")
            prev_date=$(git log -1 --format=%ct "$PREV_TAG")
            if [ "$t_date" -gt "$prev_date" ]; then
                PREV_TAG="$t"
            fi
        fi
    done
fi

if [ -z "$PREV_TAG" ]; then
    echo "test-upgrade-rollback: NO-DATA. This repository has cut no previous tag yet"
    echo "test-upgrade-rollback: (docs/RELEASE.md: tagging and pushing, steps 5 and 6, have"
    echo "test-upgrade-rollback: never been executed; \`main\` at 1c86c9d predates tagging"
    echo "test-upgrade-rollback: entirely). There is no earlier release to upgrade FROM, so an"
    echo "test-upgrade-rollback: upgrade-then-rollback cannot be exercised against real history"
    echo "test-upgrade-rollback: on this run. This is not a pass: it is a stated absence of the"
    echo "test-upgrade-rollback: one fixture this script needs. No claim is made that an upgrade"
    echo "test-upgrade-rollback: was tested. Once the first tag exists, this script finds it"
    echo "test-upgrade-rollback: automatically and exercises the real path below."
    exit 0
fi

echo "test-upgrade-rollback: previous tag found: $PREV_TAG"

WORKDIR=$(mktemp -d 2>/dev/null || echo "/tmp/sbe-test-upgrade-rollback-work.$$")
mkdir -p "$WORKDIR"
TARGET="$WORKDIR/install"
trap 'rm -rf "$WORKDIR"' EXIT INT TERM

FAILED=0

# install_and_verify REF LABEL: wipe TARGET, archive REF into it fresh, run
# verify-install.sh from that fresh copy. Sets FAILED=1 and prints a FAIL
# line on any problem, rather than exiting immediately, so a run that fails
# early still tells you about the same category of problem at every step
# instead of stopping at the first with the rest unstated.
install_and_verify() {
    ref="$1"
    label="$2"
    rm -rf "$TARGET"
    mkdir -p "$TARGET"
    echo "test-upgrade-rollback: installing $label ($ref) into a fresh directory"
    if ! git archive --format=tar "$ref" | (cd "$TARGET" && tar xf -); then
        echo "test-upgrade-rollback: FAIL, \`git archive $ref\` did not extract cleanly" >&2
        FAILED=1
        return
    fi
    if [ ! -f "$TARGET/scripts/verify-install.sh" ]; then
        echo "test-upgrade-rollback: FAIL, scripts/verify-install.sh did not ship at $label ($ref)" >&2
        FAILED=1
        return
    fi
    echo "test-upgrade-rollback: verifying $label"
    if sh "$TARGET/scripts/verify-install.sh"; then
        echo "test-upgrade-rollback: $label verified clean"
    else
        echo "test-upgrade-rollback: FAIL, verify-install.sh did not pass for $label ($ref) (see its output above)" >&2
        FAILED=1
    fi
}

install_and_verify "$PREV_TAG" "the previous release"
install_and_verify "HEAD" "the upgrade to HEAD"
install_and_verify "$PREV_TAG" "the rollback to the previous release"

echo ""
if [ "$FAILED" -ne 0 ]; then
    echo "test-upgrade-rollback: FAILED. Upgrading $PREV_TAG -> HEAD -> $PREV_TAG did not verify clean at every step; see the FAIL line(s) above." >&2
    exit 1
fi
echo "test-upgrade-rollback: PASSED. $PREV_TAG -> HEAD -> $PREV_TAG, each step archived into a fresh directory and verified with scripts/verify-install.sh, nothing written outside the one temporary directory this script created and removed on exit."
