#!/bin/sh
# install.sh: the one line that installs BrotherSBE the same way on every
# machine on the team. Checks the machine, installs the Claude Code plugin,
# applies the committed team profile through sbe init, and closes with
# sbe doctor's own verdict, never a claim this script invented itself.
#
# Usage:
#   sh install.sh                  real run: resolves the target project
#                                   (the directory this was invoked from,
#                                   or --target below), writes the plugin
#                                   registration and the sbe local
#                                   footprint into THAT project, and
#                                   nothing else
#   sh install.sh --dry-run        names every step it would take,
#                                   including the resolved target and any
#                                   refusal that target would hit, and
#                                   writes nothing; safe on any machine,
#                                   including one missing a prerequisite
#   sh install.sh --target <path>  installs into <path> instead of the
#                                   directory this was invoked from;
#                                   a relative <path> resolves against
#                                   that directory, not against this
#                                   script's own location
#   sh install.sh --developer-self-test
#                                   the one way to point the resolved
#                                   target at this BrotherSBE clone
#                                   itself; every other invocation refuses
#                                   that target outright (see below)
#
# THE RESOLVED TARGET IS NEVER THIS CLONE UNLESS --developer-self-test
# SAYS SO ON PURPOSE. Before this flag existed, this script always `cd`ed
# into its own directory and then told sbe init to install into ".", so
# running install.sh from inside a project silently initialized this
# BrotherSBE clone instead: a person could watch a PASS and still have an
# untouched project. Both sides of that comparison are resolved with
# `cd ... && pwd` before they are compared, so a symlink or a trailing
# slash cannot hide the match.
#
# SBE_INSTALL_REQUIRE=<name> adds one synthetic requirement ahead of the
# real ones, so the missing-prerequisite path can be exercised in a test
# without uninstalling a real tool from the machine running it.
#
# POSIX sh only, no bashisms, same portability intent as
# scripts/verify-install.sh.

set -eu

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
# Captured before any cd below moves this script's own idea of "here" out
# from under the caller: this is the one fact "sh install.sh" run with no
# --target has to go on for what the caller meant by "my project".
INVOKED_FROM=$(pwd)

DRY_RUN=0
DEVELOPER_SELF_TEST=0
TARGET_ARG=""
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --developer-self-test)
            DEVELOPER_SELF_TEST=1
            shift
            ;;
        --target)
            if [ $# -lt 2 ]; then
                echo "install: --target requires a path argument"
                exit 2
            fi
            TARGET_ARG="$2"
            shift 2
            ;;
        --target=*)
            TARGET_ARG="${1#--target=}"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Resolve the target BEFORE the historical `cd "$SCRIPT_DIR"` a few lines
# down runs, and compare it against SCRIPT_DIR the same way: both put
# through `cd ... && pwd`, so a relative path, a trailing slash or a
# symlinked clone all resolve to the same string a straight `=` can compare.
if [ -n "$TARGET_ARG" ]; then
    RAW_TARGET="$TARGET_ARG"
else
    RAW_TARGET="$INVOKED_FROM"
fi

if [ ! -d "$RAW_TARGET" ]; then
    echo "install: MISSING target: '$RAW_TARGET' is not a directory; pass an existing project directory with --target, or run install.sh from inside one"
    exit 2
fi
TARGET=$(cd "$RAW_TARGET" && pwd)

echo "install: resolved target: $TARGET"

if [ "$TARGET" = "$SCRIPT_DIR" ] && [ "$DEVELOPER_SELF_TEST" != "1" ]; then
    echo "install: REFUSED: the resolved target ($TARGET) is this BrotherSBE clone itself, not a project that consumes it. Installing here would silently rewrite this clone's own working tree instead of your project's, which is the exact defect this refusal exists to close. Do one of: run install.sh from inside your own project's directory instead of this clone, or re-run with --target /path/to/your-project; if you mean to test install.sh against this clone on purpose, re-run with --developer-self-test."
    exit 1
fi

cd "$SCRIPT_DIR"

# need <name> <remedy>: refuses with the exact remedy a person can act on,
# never a bare "not found". Read only (command -v), so it is safe to run in
# both --dry-run and a real install.
need() {
    name="$1"
    remedy="$2"
    if ! command -v "$name" >/dev/null 2>&1; then
        echo "install: MISSING $name: $remedy"
        exit 1
    fi
}

check_prereqs() {
    if [ -n "${SBE_INSTALL_REQUIRE:-}" ]; then
        if [ "$DRY_RUN" = "1" ]; then
            echo "would: check $SBE_INSTALL_REQUIRE is on PATH (SBE_INSTALL_REQUIRE, a synthetic requirement added for testing the refusal path only)"
        fi
        need "$SBE_INSTALL_REQUIRE" "install $SBE_INSTALL_REQUIRE and re-run install.sh"
    fi

    if [ "$DRY_RUN" = "1" ]; then
        echo "would: check git is on PATH"
    fi
    need git "install git (for example, Xcode Command Line Tools on macOS, or your package manager) and re-run install.sh"

    if [ "$DRY_RUN" = "1" ]; then
        echo "would: check python3 is on PATH and is version 3.9 or newer"
    fi
    need python3 "install Python 3.9 or newer and re-run install.sh"
    if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
        echo "install: MISSING python3: found a Python older than 3.9; install Python 3.9 or newer and re-run install.sh"
        exit 1
    fi

    if [ "$DRY_RUN" = "1" ]; then
        echo "would: check claude is on PATH (the Claude Code CLI)"
    fi
    need claude "install the Claude Code CLI and re-run install.sh"
}

# install_plugin: registers this project as a Claude Code plugin. Prefers
# claude plugin marketplace add pointed straight at the repository once a
# published, citable tag exists there (the same "pin to a tag" convention
# docs/ROLLOUT.md already documents for adopting teams); otherwise names and
# takes the clone fallback, mirroring the clone target README.md and
# docs/ROLLOUT.md already use (~/.claude/skills/brothersbe), so a machine
# with no published tag yet still ends with a working local marketplace
# source. Both branches finish with the same claude plugin install call.
install_plugin() {
    origin_url=$(git config --get remote.origin.url 2>/dev/null || true)
    version=$(python3 -c "import json; print(json.load(open('.claude-plugin/plugin.json'))['version'])")
    tag="v$version"
    clone_dest="$HOME/.claude/skills/brothersbe"

    if [ "$DRY_RUN" = "1" ]; then
        echo "would: install the brothersbe plugin: claude plugin marketplace add $origin_url then claude plugin install brothersbe@brothersbe, if tag $tag is published on $origin_url; otherwise take the clone fallback (git clone $origin_url $clone_dest, or update it if it is already there, then claude plugin marketplace add $clone_dest, then claude plugin install brothersbe@brothersbe)"
        return 0
    fi

    if [ -z "$origin_url" ]; then
        echo "install: MISSING origin remote: this clone has no git remote named origin; add one (git remote add origin <repository-url>) and re-run install.sh"
        exit 1
    fi

    if git ls-remote --tags "$origin_url" "refs/tags/$tag" 2>/dev/null | grep -q "$tag"; then
        echo "install: $tag is published on $origin_url, adding the marketplace directly"
        claude plugin marketplace add "$origin_url"
        claude plugin install brothersbe@brothersbe
    else
        echo "install: $tag is not published on $origin_url yet, taking the clone fallback"
        if [ -d "$clone_dest/.git" ]; then
            echo "install: updating the existing clone at $clone_dest"
            git -C "$clone_dest" pull --ff-only
        else
            echo "install: cloning $origin_url to $clone_dest"
            mkdir -p "$(dirname "$clone_dest")"
            git clone "$origin_url" "$clone_dest"
        fi
        claude plugin marketplace add "$clone_dest"
        claude plugin install brothersbe@brothersbe
    fi
}

# The installation report apply_team_profile() below prints after a real
# run: parses sbe init's own --json result and states, as separate lines,
# what the team profile requested, what was actually applied, what was
# rejected by name, and which files were written versus already up to
# date. Kept as a python3 script (not a jq pipeline) because python3 is
# already a hard prerequisite (check_prereqs above) and jq is not. No
# apostrophe appears anywhere in this string: it is embedded in install.sh
# with single quotes, so an apostrophe would end the string early.
PY_TEAM_PROFILE_REPORT='
import json
import sys

data = json.loads(sys.argv[1])
profile = data.get("teamProfile") or {}


def names(values):
    if values:
        return ", ".join(values)
    return "none"


requested = profile.get("requested", [])
applied = profile.get("applied", {})
rejected = profile.get("rejected", [])
source = profile.get("source")
path = profile.get("path")

print("install: team profile requested: %s" % names(requested))
if path:
    print("install: team profile source: %s (%s)" % (path, source))
else:
    print("install: team profile source: none found; built-in defaults used")
applied_pairs = ["%s=%s" % (key, applied[key]) for key in sorted(applied)]
print("install: team profile applied: %s" % names(applied_pairs))
print("install: team profile rejected by name: %s" % names(rejected))
print("install: files written: %s" % names(data.get("written", [])))
print("install: files already up to date, skipped: %s" % names(data.get("skipped", [])))
for warning in data.get("warnings", []):
    print("install: WARNING %s" % warning)
'

# apply_team_profile: bin/sbe init writes the local footprint (config,
# dossier directory, receipt) into the RESOLVED TARGET, never into this
# clone (that was DEFECT 1: the old `cd "$SCRIPT_DIR"` above ran before
# `bin/sbe init . --apply`, so "." always meant this clone, not whoever's
# project ran the script). .sbe/team-profile.json is the committed,
# same-for-everyone answer to the choices that command would otherwise ask
# a person to make (dossierRoot, vaultPathPattern, ci, codeGuideDepth,
# schemaVersion); the report below names every one of those fields as
# requested, applied or rejected, because a field the profile named and
# init silently ignored was DEFECT 2, and "silent" is exactly what a
# structured report closes off.
apply_team_profile() {
    if [ "$DRY_RUN" = "1" ]; then
        echo "would: apply the team profile with python3 bin/sbe init $TARGET --apply, reading .sbe/team-profile.json (from $TARGET when it carries one, otherwise this installation's own copy at $SCRIPT_DIR) for dossierRoot, vaultPathPattern, ci, codeGuideDepth, and schemaVersion; any field outside that set is rejected by name in the report below, never silently ignored"
        return 0
    fi
    init_json=$(python3 bin/sbe init "$TARGET" --apply --json)
    python3 -c "$PY_TEAM_PROFILE_REPORT" "$init_json"
}

# run_doctor: closes the install with sbe doctor's own verdict, graded
# against the RESOLVED TARGET, never this clone (that was DEFECT 3: `cd
# "$SCRIPT_DIR"` above put every earlier version of this function's cwd at
# this clone before it ran `bin/sbe doctor`, so doctor's git and identity
# checks, which read the CALLING process's cwd rather than their own script
# location, described this BrotherSBE clone's git tree, and "install: PASS,
# sbe doctor agrees" graded the distribution instead of the project that was
# just initialized). The fix: cd into $TARGET in a subshell before invoking
# doctor, so cwd-based checks describe $TARGET, while the doctor binary
# itself is still called by its absolute path under $SCRIPT_DIR, so its
# tool-presence check (repo_root(), computed from that script's own file
# location, not cwd) keeps resolving against this installation's own tools/
# regardless of which directory doctor is graded against. The closing line
# names $TARGET so the proof states what it graded, never leaving that
# implicit.
run_doctor() {
    if [ "$DRY_RUN" = "1" ]; then
        echo "would: run bin/sbe doctor and confirm it agrees before printing the PASS line"
        return 0
    fi
    if (cd "$TARGET" && "$SCRIPT_DIR/bin/sbe" doctor); then
        echo "install: PASS, sbe doctor agrees (graded $TARGET)"
    else
        echo "install: sbe doctor did not agree (graded $TARGET); read what it printed above for exactly what is missing"
        exit 1
    fi
}

check_prereqs
install_plugin
apply_team_profile
run_doctor

if [ "$DRY_RUN" = "1" ]; then
    echo "install: dry run, nothing written."
fi
