"""Move every version declaration site in one command, and verify they agree.

Why this exists: parity row PT-2. Three release candidates in one night were
bumped by hand across four files (VERSION, .claude-plugin/plugin.json,
.claude-plugin/marketplace.json twice, DIGEST.md line 1), and every manual
pass is one typo away from the release invariant refusing the seal. One
command edits all the sites the invariant reads, from one argument, and then
re-reads every site to prove they now agree, because an edit that is not
re-read is a claim rather than a fact.

What this command deliberately does NOT do, printed as reminders instead of
performed: the CHANGELOG heading (prose a human or the sealing orchestrator
writes), `evals/replay_book.py --write` (book echoes regenerate from live
runs, never from a substitution), and CHECKSUMS.sha256 (regenerated LAST in
the seal order, after git add). Doing those here would hide three steps that
each have their own failure modes behind one that looks atomic.

Refusal semantics, in the house shape: a malformed target version is refused
by name (the accepted shape is the release invariant's own v-digit form,
without the leading v). Sites that ALREADY disagree are refused with every
site and its current value named, because bumping over a disagreement would
bury the evidence of whatever went wrong. A target equal to the current
version is refused as a no-op rather than reported as success, because a
command that succeeds at nothing is the failure this project exists to stop.
`--dry-run` shows every intended edit and writes nothing.
"""
import json
import os
import re
import sys

#: The accepted shape: MAJOR.MINOR.PATCH with an optional -rc.N tail, the
#: same population the release invariant's v-digit tag filter selects from.
VERSION_SHAPE = re.compile(r"^\d+\.\d+\.\d+(-rc\.\d+)?$")

#: Every declaration site the release invariant and the docs treat as live.
#: marketplace.json carries the version twice (the marketplace entry and the
#: plugin entry), which is exactly why a single-file mental model fails.
SITES = ("VERSION", ".claude-plugin/plugin.json",
         ".claude-plugin/marketplace.json", "DIGEST.md")

REMINDERS = (
    "CHANGELOG.md: add the new heading yourself; prose is not substituted",
    "evals/replay_book.py --write: regenerate book echoes from live runs",
    "scripts/checksums.sh CHECKSUMS.sha256: LAST, after git add",
)


def _read(root, rel):
    with open(os.path.join(root, rel), "r") as fh:
        return fh.read()


def _site_versions(root):
    """Read every declared version, one list entry per DECLARATION (so
    marketplace.json contributes two), each as (site-label, value)."""
    found = []
    found.append(("VERSION", _read(root, "VERSION").strip()))
    plugin = json.loads(_read(root, ".claude-plugin/plugin.json"))
    found.append((".claude-plugin/plugin.json version", plugin.get("version")))
    market = json.loads(_read(root, ".claude-plugin/marketplace.json"))
    market_versions = []
    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "version" and isinstance(value, str):
                    market_versions.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(market)
    for index, value in enumerate(market_versions):
        found.append((".claude-plugin/marketplace.json version #%d" % (index + 1), value))
    digest_first = _read(root, "DIGEST.md").splitlines()[0] if _read(root, "DIGEST.md") else ""
    match = re.search(r"version (\d+\.\d+\.\d+(?:-rc\.\d+)?)", digest_first)
    found.append(("DIGEST.md line 1", match.group(1) if match else None))
    return found


def _apply(root, old, new, dry_run):
    """Rewrite each site by exact-string substitution of the OLD version,
    which can only be reached after the agreement check, so the substitution
    is unambiguous by construction. Returns the list of edited sites."""
    edited = []
    for rel in SITES:
        before = _read(root, rel)
        if rel == "VERSION":
            after = new + "\n"
        elif rel == "DIGEST.md":
            lines = before.splitlines(True)
            lines[0] = lines[0].replace("version " + old, "version " + new)
            after = "".join(lines)
        else:
            after = before.replace('"version": "%s"' % old, '"version": "%s"' % new)
        if before != after:
            if not dry_run:
                with open(os.path.join(root, rel), "w") as fh:
                    fh.write(after)
            edited.append(rel)
    return edited


def main(rest, exit_ok=0, exit_failed=1, exit_usage=2):
    argv = list(rest)
    dry_run = "--dry-run" in argv
    argv = [a for a in argv if a != "--dry-run"]
    if len(argv) != 2 or argv[0] != "bump":
        sys.stderr.write(
            "usage: sbe version bump <new-version> [--dry-run]\n"
            "  <new-version> shape: MAJOR.MINOR.PATCH or MAJOR.MINOR.PATCH-rc.N, no leading v\n"
            "  edits: %s (marketplace carries the version twice)\n"
            "  never edits: CHANGELOG.md, book echoes, CHECKSUMS.sha256 (printed as reminders)\n"
            % ", ".join(SITES))
        return exit_usage
    new = argv[1]
    if not VERSION_SHAPE.match(new):
        sys.stderr.write("version bump REFUSED: %r does not match the accepted shape "
                         "MAJOR.MINOR.PATCH[-rc.N] (no leading v)\n" % new)
        return exit_usage

    root = os.getcwd()
    for rel in SITES:
        if not os.path.isfile(os.path.join(root, rel)):
            sys.stderr.write("version bump REFUSED: %s is missing under %s; run from the "
                             "repository root that carries all four declaration sites\n"
                             % (rel, root))
            return exit_failed

    sites = _site_versions(root)
    values = set(value for _, value in sites)
    if None in values or len(values) != 1:
        sys.stderr.write("version bump REFUSED: the declaration sites already disagree, and "
                         "bumping over a disagreement would bury its evidence. Reconcile these "
                         "first:\n")
        for label, value in sites:
            sys.stderr.write("  %-45s %s\n" % (label, value if value is not None else "UNREADABLE"))
        return exit_failed
    old = values.pop()
    if old == new:
        sys.stderr.write("version bump REFUSED: every site already reads %s; a bump to the "
                         "same version succeeds at nothing\n" % new)
        return exit_failed

    edited = _apply(root, old, new, dry_run)
    verb = "would edit" if dry_run else "edited"
    sys.stdout.write("version bump %s -> %s: %s %d file(s): %s\n"
                     % (old, new, verb, len(edited), ", ".join(edited)))

    if not dry_run:
        after = _site_versions(root)
        wrong = [(label, value) for label, value in after if value != new]
        if wrong:
            sys.stderr.write("version bump FAILED its own re-read: these sites do not read "
                             "%s after the edit: %s\n"
                             % (new, "; ".join("%s=%s" % pair for pair in wrong)))
            return exit_failed
        sys.stdout.write("re-read: all %d declaration(s) now read %s\n" % (len(after), new))

    sys.stdout.write("NOT done by this command, in seal order:\n")
    for line in REMINDERS:
        sys.stdout.write("  - %s\n" % line)
    return exit_ok
