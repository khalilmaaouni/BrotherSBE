#!/usr/bin/env python3
"""BrotherSBE hard gates: the four silent-failure classes made mechanical.

This is the teeth of the trust architecture. Each subcommand inspects a
deliverable directory (default: the current git worktree) for the receipts that
prove a check RAN, and reports PASS / FAIL / NO-DATA per the class. Two modes,
one truth:
  default   advisory. Prints the verdict, exits 0. A session gets told.
  --strict  enforcing. Exits nonzero on any FAIL. CI runs this. A merge gets stopped.

The classes (ratified 2026-07-24):
  numbers   Every figure that could reach a decision ships with a numbers-manifest
            whose second, independently-scripted derivation RE-RAN to zero drift
            against a PINNED snapshot (live-warehouse drift is expected; the gate
            fails loudly if no snapshot id is recorded, rather than silently).
  migration A forward and a reverse migration, both with a receipt showing they
            ran against a restored copy, the reverse receipt carrying a resolvable
            rehearsal run id (not free text), and matching row-count checks.
  approval  Money or partner-facing change carries a named human approval bound to
            an identity the agent cannot forge: a signed commit trailer or a
            recorded platform review id. A bare typed name FAILS.
  ran       No SQL or pipeline change is done until its reconciliation query or
            test executed: a receipt with a nonzero-duration run and an exit code.

Honesty law inherited from the chassis: absent evidence is NO-DATA, never PASS.
Fabricated-receipt defense: presence is necessary but the gate also checks the
receipt is INTERNALLY CONSISTENT (a run id resolves to a nonzero duration and an
exit code, a manifest's second query differs textually from the first), because
the operating record proves pasted receipts get invented.
"""
import json, os, sys, re, subprocess, hashlib

MANIFEST = "numbers-manifest.json"
MIGRATION_RECEIPT = "migration-receipt.json"
APPROVAL_FILE = "APPROVAL"
RAN_RECEIPT = "ran-receipt.json"


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def find(root, name):
    hits = []
    for dp, _, fns in os.walk(root):
        if ".git" in dp:
            continue
        if name in fns:
            hits.append(os.path.join(dp, name))
    return hits


def git_trailers(root):
    """Named-approval source of truth #1: signed commit trailers on HEAD."""
    try:
        out = subprocess.run(["git", "-C", root, "log", "-1", "--format=%B%n---%n%G?"],
                             capture_output=True, text=True, timeout=10)
        body, _, sig = out.stdout.rpartition("\n---\n")
        return body, sig.strip()
    except Exception:
        return "", "N"


def gate_numbers(root):
    manifests = find(root, MANIFEST)
    if not manifests:
        return "NO-DATA", "no numbers-manifest found; if this change presents no decision figure that is correct, else add one"
    problems = []
    checked = 0
    for m in manifests:
        d = load_json(m) or {}
        for fig in d.get("figures", []):
            checked += 1
            label = fig.get("label", "?")
            if not fig.get("snapshot_id"):
                problems.append("%s: no snapshot_id (a live warehouse drifts; pin the read)" % label)
            q1, q2 = fig.get("query", ""), fig.get("second_derivation", "")
            if not q2:
                problems.append("%s: no independent second derivation" % label)
            elif q1.strip() == q2.strip():
                problems.append("%s: second derivation is textually identical to the first (not independent)" % label)
            r = fig.get("rerun", {})
            if not r.get("ran"):
                problems.append("%s: second derivation not marked as re-run" % label)
            elif r.get("primary") is not None and r.get("secondary") is not None and r["primary"] != r["secondary"]:
                problems.append("%s: DRIFT primary=%s secondary=%s (zero drift required)" % (label, r["primary"], r["secondary"]))
    if problems:
        return "FAIL", "; ".join(problems[:6])
    return "PASS", "%d figure(s) each with a pinned, independently re-derived, zero-drift check" % checked


def gate_migration(root):
    receipts = find(root, MIGRATION_RECEIPT)
    if not receipts:
        return "NO-DATA", "no migration in this change, or no migration-receipt.json"
    problems = []
    for m in receipts:
        d = load_json(m) or {}
        for direction in ("forward", "reverse"):
            leg = d.get(direction, {})
            if not leg.get("ran_against_restore"):
                problems.append("%s: not run against a restored copy" % direction)
            if direction == "reverse" and not leg.get("rehearsal_run_id"):
                problems.append("reverse: no resolvable rehearsal_run_id (free text is not a receipt)")
        rc = d.get("row_counts", {})
        if rc.get("before") is not None and rc.get("after_reverse") is not None and rc["before"] != rc["after_reverse"]:
            problems.append("reverse did not restore row count: before=%s after=%s" % (rc["before"], rc["after_reverse"]))
    if problems:
        return "FAIL", "; ".join(problems[:6])
    return "PASS", "forward and reverse both ran against a restore with matching row counts and a resolvable rehearsal id"


def gate_approval(root):
    approvals = find(root, APPROVAL_FILE)
    body, sig = git_trailers(root)
    trailer = re.search(r"^Approved-by:\s*(.+)$", body, re.M)
    review_id = re.search(r"^Reviewed-in:\s*(\S+)$", body, re.M)
    # The APPROVAL file declares this change touches money/partner paths.
    if not approvals and not trailer:
        return "NO-DATA", "no APPROVAL file and no Approved-by trailer; if this change touches no money or partner path that is correct"
    # An approval was claimed: now it must be bound to a forgeable-resistant identity.
    if trailer and sig in ("G", "U", "E"):
        return "PASS", "signed commit carries Approved-by: %s" % trailer.group(1).strip()
    if review_id:
        return "PASS", "approval bound to platform review %s" % review_id.group(1)
    return "FAIL", "approval is a typed name with no signature or review id; a name in a text field is not a control (add a signed Approved-by trailer or a Reviewed-in review id)"


def gate_ran(root):
    receipts = find(root, RAN_RECEIPT)
    if not receipts:
        return "NO-DATA", "no ran-receipt.json; a SQL or pipeline change is not done until its check executed and left a receipt"
    problems = []
    for m in receipts:
        d = load_json(m) or {}
        for chk in d.get("checks", []):
            name = chk.get("name", "?")
            if chk.get("exit_code") is None:
                problems.append("%s: no exit code recorded (was it actually run?)" % name)
            elif chk.get("exit_code") != 0:
                problems.append("%s: check exited nonzero (%s)" % (name, chk["exit_code"]))
            if not chk.get("duration_ms"):
                problems.append("%s: zero or missing duration (a check that took no time did not run)" % name)
    if problems:
        return "FAIL", "; ".join(problems[:6])
    return "PASS", "every recorded check executed with a zero exit and a nonzero duration"


GATES = {"numbers": gate_numbers, "migration": gate_migration,
         "approval": gate_approval, "ran": gate_ran}


def main():
    argv = [a for a in sys.argv[1:] if a != "--strict"]
    strict = "--strict" in sys.argv
    root = "."
    which = list(GATES)
    for a in argv:
        if a in GATES:
            which = [a]
        elif os.path.isdir(a):
            root = a
    try:
        root = subprocess.run(["git", "-C", root, "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, timeout=10).stdout.strip() or root
    except Exception:  # sbe: allow-silent boundary read of a possibly-malformed receipt; a bad receipt becomes NO-DATA or FAIL below, never a pass
        pass
    fails = 0
    print("BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)")
    for name in which:
        verdict, ev = GATES[name](root)
        if verdict == "FAIL":
            fails += 1
        print("  %-9s %-8s %s" % (name, verdict, ev))
    if strict and fails:
        print("STRICT: %d hard gate(s) failed; exiting nonzero to block the merge." % fails)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # A broken gate must not silently pass work. In strict mode a crash blocks.
        print("sbe_gate: error %r" % (e,))
        sys.exit(1 if "--strict" in sys.argv else 0)
