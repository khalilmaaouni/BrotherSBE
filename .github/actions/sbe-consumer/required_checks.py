#!/usr/bin/env python3
"""Print the registered check ids a policy report says this diff requires.

Reads a `sbe policy evaluate --json` report on standard input and writes one
check id per line to standard output. Nothing else goes to standard output, so
the caller can consume it directly.

WHY THIS IS A FILE AND NOT INLINE YAML. It was inline once and the quoting
broke the whole action manifest, which is a bad way to learn that a shell
heredoc inside a YAML scalar inside a composite action has three layers of
escaping. It is also the reason this can be tested: a file has a test, an
inline blob has a hope.

WHAT IT DELIBERATELY DOES NOT DO. It never decides that a check is
unnecessary. Its only job is to name what the report already named, so a
requirement cannot be dropped here without the report dropping it first. An
unparseable report prints nothing and says so on standard error, which leaves
the caller with no receipts to mint and the evaluation still reporting every
requirement MISSING. Silence here can only ever make the gate stricter.
"""

import json
import sys


def required_check_ids(report):
    """The registered check ids in a report, in first-seen order, deduplicated.

    A requirement is a check when the report says so, either by naming its kind
    or by using the `check:` identifier prefix. Both are read because the two
    have coexisted in this report shape and reading only one would silently
    mint nothing for the other.
    """
    seen = []
    if not isinstance(report, dict):
        return seen
    for record in report.get("requirements", []):
        if not isinstance(record, dict):
            continue
        identifier = record.get("id") or ""
        kind = record.get("kind") or ""
        if kind != "check" and not identifier.startswith("check:"):
            continue
        name = identifier.split(":", 1)[-1].strip()
        if name and name not in seen:
            seen.append(name)
    return seen


def main(argv):
    raw = sys.stdin.read()
    try:
        report = json.loads(raw)
    except ValueError as exc:
        sys.stderr.write(
            "required_checks: the policy report did not parse (%s), so no receipt "
            "will be minted from it. The evaluation that follows still runs and "
            "still reports every requirement it cannot see satisfied.\n" % exc)
        return 0
    for name in required_check_ids(report):
        sys.stdout.write("%s\n" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
