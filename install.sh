#!/bin/sh
# install.sh: the one line that installs BrotherSBE the same way on every
# machine on the team. Checks the machine, installs the Claude Code plugin,
# applies the committed team profile through sbe init, and closes with
# sbe doctor's own verdict, never a claim this script invented itself.
#
# Usage:
#   sh install.sh            real run, writes the plugin registration, the
#                             sbe local footprint, and nothing else
#   sh install.sh --dry-run  names every step it would take and writes
#                             nothing; safe to run on any machine, including
#                             one missing a prerequisite, to see what is
#                             missing before touching anything
#
# SBE_INSTALL_REQUIRE=<name> adds one synthetic requirement ahead of the
# real ones, so the missing-prerequisite path can be exercised in a test
# without uninstalling a real tool from the machine running it.
#
# POSIX sh only, no bashisms, same portability intent as
# scripts/verify-install.sh.

set -eu

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$SCRIPT_DIR"

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
    esac
done

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

# apply_team_profile: bin/sbe init writes the local footprint (config,
# dossier directory, receipt); .sbe/team-profile.json is the committed,
# same-for-everyone answer to the choices that command would otherwise ask
# a person to make (dossierRoot, vaultPathPattern, ci, codeGuideDepth,
# schemaVersion), so one clone and one script produce the same install as
# every other teammate's.
apply_team_profile() {
    if [ "$DRY_RUN" = "1" ]; then
        echo "would: apply the team profile with python3 bin/sbe init . --apply, reading .sbe/team-profile.json for dossierRoot, vaultPathPattern, ci, codeGuideDepth, and schemaVersion"
        return 0
    fi
    python3 bin/sbe init . --apply
}

run_doctor() {
    if [ "$DRY_RUN" = "1" ]; then
        echo "would: run bin/sbe doctor and confirm it agrees before printing the PASS line"
        return 0
    fi
    if sh -c 'bin/sbe doctor'; then
        echo "install: PASS, sbe doctor agrees"
    else
        echo "install: sbe doctor did not agree; read what it printed above for exactly what is missing"
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
