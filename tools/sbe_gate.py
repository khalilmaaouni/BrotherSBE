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
            ran against a restored copy, the reverse receipt recording a rehearsal
            run id AS A NON-BLANK STRING, and row counts that were RECORDED and
            that match. Recorded, not merely keyed: two empty strings compare
            equal, so a gate whose only emptiness test was `is None` reported
            "1 row-count comparison(s) matched" about a pair of blanks.
            Two limits, stated because the evidence line used to overstate both:
            this gate does not resolve the rehearsal id against any job system,
            and a receipt with no row counts is NO-DATA rather than a pass,
            because the reverse restoring the rows is the half it cannot assert
            without them.
  approval  Money or partner-facing change carries a named human approval bound
            to something stronger than a typed name. Two paths, and they are NOT
            equally strong, so this says exactly what each one proves:
              Approved-by: with a signature THIS HOST verified (git %G? = G or U)
                proves a key holder signed the commit. The agent cannot produce
                this without the private key.
              Reviewed-in: <review id> proves only that an id in the right shape
                was written into the commit message. This gate does not resolve
                it against any platform, so an agent can type one. It is a
                pointer for a human to follow, not a forgery-resistant control.
                Resolve it in CI (a job that queries your review platform for
                that id) if you need it to be one.
            A bare typed name FAILS. A signature the host cannot check (git
            %G? = E, the normal result on a runner with no imported keys) is
            NO-DATA, never an approval: CI must import the signer's public keys,
            or the team standardises on the weaker keyless Reviewed-in: path
            knowing what it does and does not prove.
  ran       No SQL or pipeline change is done until its reconciliation query or
            test executed: a receipt with a nonzero-duration run and an exit code.

Honesty law inherited from the chassis: absent evidence is NO-DATA, never PASS.
Three states, not two, and the difference is load-bearing: a missing receipt is
NO-DATA (nothing was claimed), a receipt that exists but records zero items is
NO-DATA naming that fact (a claim of nothing is still nothing), and a receipt
that exists and cannot be parsed is a FAIL (a broken claim, not an absent one).
A gate that reported PASS over zero items would print evidence asserting work
that was never inspected, which is worse than having no gate at all.
Fabricated-receipt defense: presence is necessary but the gate also checks the
receipt is INTERNALLY CONSISTENT (a run id resolves to a nonzero duration and an
exit code, a manifest's second query differs textually from the first), because
the operating record proves pasted receipts get invented.
"""
import json, os, sys, re, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbe_checks import Check, run_guarded, stated

MANIFEST = "numbers-manifest.json"
MIGRATION_RECEIPT = "migration-receipt.json"
APPROVAL_FILE = "APPROVAL"
RAN_RECEIPT = "ran-receipt.json"
SKIP_DIRS = (".git", "node_modules", "__pycache__", ".venv", "venv", "vendor")


def load_receipt(path):
    """Parse a receipt into (object, error).

    error is non-empty when the file exists but is not a usable receipt, and the
    caller turns that into a FAIL: a receipt that cannot be read is a broken
    claim, not an absent one. Absence of the file is NO-DATA, decided elsewhere
    on purpose.

    Valid JSON of the wrong TYPE is a broken claim too, and it used to be the
    hole: `json.load` returned a list or a string happily, the gate called .get
    on it, the exception escaped to the top-level handler, every gate after it
    never ran, nothing printed a verdict for any of them, and advisory mode
    exited 0. A crash that deletes a gate is the absent-check defect wearing a
    traceback. The type is checked here, once, where the file is opened.
    """
    try:
        with open(path) as f:
            obj = json.load(f)
    except (OSError, ValueError) as e:
        return None, "not readable as JSON (%s)" % type(e).__name__
    if not isinstance(obj, dict):
        return None, ("top-level JSON is %s, not an object; a receipt is a JSON object"
                      % type(obj).__name__)
    return obj, ""


def _items(d, key):
    """Return (items, note) for a receipt's item list.

    items is [] when the key is missing, is not a list, or is an empty list.
    note names the reason so the NO-DATA evidence can distinguish a genuinely
    empty receipt from a misspelled key, which otherwise look identical.
    """
    v = d.get(key)
    if isinstance(v, list) and v:
        return v, ""
    if v is None:
        other = ", ".join(sorted(k for k in d if k != key))
        return [], ("no '%s' list; top-level keys present: %s" % (key, other)
                    if other else "no '%s' key and nothing else in the file" % key)
    if not isinstance(v, list):
        return [], "'%s' is %s, not a list" % (key, type(v).__name__)
    return [], "'%s' is an empty list" % key


def find(root, name):
    hits = []
    for dp, dns, fns in os.walk(root):
        # Match directory NAMES, not a substring of the path: `.git` as a
        # substring test also hid `.github/`, so the workflow that wires these
        # gates into CI was invisible to every one of them.
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
        if name in fns:
            hits.append(os.path.join(dp, name))
    return hits


def _partial(nothing, checked, kind, unit):
    """Evidence for a run where some receipts held items and some declared none.

    Reporting PASS here was the headline fix surviving in a repository with more
    than one deliverable, which is the normal case: the note naming the empty
    receipt was computed, collected, and then discarded unless EVERY receipt was
    empty. One good manifest anywhere in the tree restored the old behaviour for
    all the rest. A verdict covers every receipt it walked or it names the ones
    it could not cover.
    """
    return ("NO-DATA", "%d %s verified, but %d %s present that declares none (%s); "
                       "the verdict cannot cover a receipt with nothing in it, so it says so "
                       "instead of passing over it"
            % (checked, unit, len(nothing), kind, "; ".join(nothing[:4])))


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
    unreadable = []
    nothing = []
    checked = 0
    for m in manifests:
        d, err = load_receipt(m)
        if d is None:
            unreadable.append("%s: %s" % (os.path.relpath(m, root), err))
            continue
        figs, note = _items(d, "figures")
        if not figs:
            nothing.append("%s: %s" % (os.path.relpath(m, root), note))
            continue
        for fig in figs:
            checked += 1
            if not isinstance(fig, dict):
                problems.append("entry %d in %s is %s, not a figure object"
                                % (checked, os.path.relpath(m, root), type(fig).__name__))
                continue
            # Every field below goes through stated(), not through truthiness and
            # not through `is None`. A manifest carrying "" or " " in every field
            # parsed, held every required key, and cleared this gate, and the
            # evidence line then reported a re-derivation that compared two empty
            # strings. An empty value is an absent value.
            label = stated(fig.get("label")) or "figure %d" % checked
            if stated(fig.get("label")) is None:
                problems.append("%s in %s records no label, so nothing in the report can say which "
                                "figure was checked" % (label, os.path.relpath(m, root)))
            if stated(fig.get("snapshot_id")) is None:
                problems.append("%s: no snapshot_id (a live warehouse drifts; pin the read)" % label)
            q1, q2 = stated(fig.get("query")), stated(fig.get("second_derivation"))
            if q1 is None:
                problems.append("%s: no query recorded, so there is nothing for the second derivation to be independent of" % label)
            if q2 is None:
                problems.append("%s: no independent second derivation" % label)
            elif q1 is not None and str(q1).strip() == str(q2).strip():
                problems.append("%s: second derivation is textually identical to the first (not independent)" % label)
            r = fig.get("rerun")
            if not isinstance(r, dict):
                problems.append("%s: rerun is %s, not an object recording the re-derivation"
                                % (label, type(r).__name__))
                continue
            primary, secondary = stated(r.get("primary")), stated(r.get("secondary"))
            if not stated(r.get("ran")):
                problems.append("%s: second derivation not marked as re-run" % label)
            elif primary is None or secondary is None:
                have = ", ".join(k for k in ("primary", "secondary") if stated(r.get(k)) is not None)
                problems.append("%s: rerun marked ran but the value(s) needed to prove zero drift "
                                "were not recorded (recorded: %s). Two empty values compare equal "
                                "and prove nothing, so this is a failure and not a zero-drift pass"
                                % (label, have or "neither"))
            elif primary != secondary:
                problems.append("%s: DRIFT primary=%s secondary=%s (zero drift required)" % (label, r["primary"], r["secondary"]))
    if unreadable:
        return "FAIL", ("manifest present but unparseable: %s; a receipt that cannot be read is a broken claim, not an absent one"
                        % ", ".join(unreadable))
    if problems:
        return "FAIL", "; ".join(problems[:6])
    if not checked:
        return "NO-DATA", ("manifest present but records no figures (%s); an empty manifest proves nothing, so it is NO-DATA, never a pass"
                           % "; ".join(nothing))
    if nothing:
        return _partial(nothing, checked, "manifest", "figure(s)")
    return "PASS", "%d figure(s) each with a pinned, independently re-derived, zero-drift check" % checked


def gate_migration(root):
    receipts = find(root, MIGRATION_RECEIPT)
    if not receipts:
        return "NO-DATA", "no migration in this change, or no migration-receipt.json"
    problems = []
    unreadable = []
    nothing = []
    checked = 0      # receipts that recorded both legs
    compared = 0     # row-count comparisons actually made
    for m in receipts:
        rel = os.path.relpath(m, root)
        d, err = load_receipt(m)
        if d is None:
            unreadable.append("%s: %s" % (rel, err))
            continue
        legs = {k: d.get(k) for k in ("forward", "reverse")}
        if all(v is None for v in legs.values()) and "row_counts" not in d:
            other = ", ".join(sorted(d)) or "nothing at all"
            nothing.append("%s: no forward and no reverse leg recorded; top-level keys present: %s"
                           % (rel, other))
            continue
        for direction in ("forward", "reverse"):
            leg = legs[direction]
            if not isinstance(leg, dict):
                problems.append("%s: %s leg is %s, not an object" % (rel, direction, type(leg).__name__))
                continue
            # The boolean IS the claim, so it has to be the boolean. A whitespace
            # string is truthy, and " " satisfied this test while asserting
            # nothing at all about a restored copy.
            if leg.get("ran_against_restore") is not True:
                problems.append("%s: %s is not marked as run against a restored copy (recorded %r, "
                                "and only the value true is that claim)"
                                % (direction, direction, leg.get("ran_against_restore")))
            if direction != "reverse":
                continue
            rid = leg.get("rehearsal_run_id")
            if stated(rid) is None:
                problems.append("reverse: no rehearsal_run_id recorded (this gate checks the id is "
                                "present, is a string and is not blank, and cannot resolve it "
                                "against a job system)")
            elif not isinstance(rid, str):
                problems.append("reverse: rehearsal_run_id is %s, not a run id string"
                                % type(rid).__name__)
        checked += 1
        # The row counts are the half that used to be asserted without being read.
        # A receipt with no row_counts had the comparison skipped and the PASS
        # evidence still said "with matching row counts": a sentence about work
        # nothing did. Absent counts are an absence (NO-DATA). Half a count is a
        # broken claim (FAIL), because recording `before` and not `after_reverse`
        # says a count was taken and then does not produce it.
        rc = d.get("row_counts")
        if rc is None:
            nothing.append("%s: both legs recorded but no row_counts, so nothing compared the rows "
                           "the reverse was supposed to restore" % rel)
        elif not isinstance(rc, dict):
            problems.append("%s: row_counts is %s, not an object" % (rel, type(rc).__name__))
        elif stated(rc.get("before")) is None or stated(rc.get("after_reverse")) is None:
            # `is None` was the whole emptiness test here, so a row_counts block
            # holding "" in both fields compared equal, incremented the counter,
            # and produced "1 row-count comparison(s) matched" about two empty
            # strings. A count that was not recorded is not a count that matched.
            have = ", ".join(sorted(k for k in rc if stated(rc.get(k)) is not None)) or "neither"
            problems.append("%s: row_counts records %s; a blank or half-recorded count proves "
                            "nothing, and both before and after_reverse are required as recorded "
                            "values" % (rel, have))
        else:
            compared += 1
            if rc["before"] != rc["after_reverse"]:
                problems.append("reverse did not restore row count: before=%s after=%s"
                                % (rc["before"], rc["after_reverse"]))
    if unreadable:
        return "FAIL", ("migration receipt present but unparseable: %s; a receipt that cannot be read is a broken claim, not an absent one"
                        % ", ".join(unreadable))
    if problems:
        return "FAIL", "; ".join(problems[:6])
    if not checked:
        return "NO-DATA", ("migration receipt present but records no migration (%s); an empty receipt "
                           "proves nothing, so it is NO-DATA, never a pass" % "; ".join(nothing))
    if nothing:
        return "NO-DATA", ("%d receipt(s) with both legs run against a restore, but %d recorded no row "
                           "counts (%s); the reverse restoring the rows is the half this gate cannot "
                           "assert, so it does not"
                           % (checked, len(nothing), "; ".join(nothing[:4])))
    return "PASS", ("%d receipt(s): forward and reverse both ran against a restore, %d row-count "
                    "comparison(s) matched, and a rehearsal id string is recorded"
                    % (checked, compared))


def gate_approval(root):
    approvals = find(root, APPROVAL_FILE)
    body, sig = git_trailers(root)
    trailer = re.search(r"^Approved-by:\s*(.+)$", body, re.M)
    review_id = re.search(r"^Reviewed-in:\s*(\S+)$", body, re.M)
    # The APPROVAL file declares this change touches money/partner paths.
    if not approvals and not trailer:
        return "NO-DATA", "no APPROVAL file and no Approved-by trailer; if this change touches no money or partner path that is correct"
    # An approval was claimed: now it must be bound to a forgeable-resistant identity.
    # Only a signature that VERIFIED counts. git's %G? returns G (good) and U (good,
    # untrusted-but-valid) for a signature this host actually checked. E means the
    # signature could not be checked at all, which on a runner with no imported keys
    # is the expected result for every signed commit, including one signed by a key
    # nobody on the team recognises. Accepting E would trust the unknown while
    # rejecting a known key that had merely expired, so E is NO-DATA, not an approval.
    if trailer and sig in ("G", "U"):
        return "PASS", "signed commit carries Approved-by: %s" % trailer.group(1).strip()
    if review_id:
        # Say what this proves, in the evidence line, every time. The id is not
        # resolved against any platform: this gate reads the commit message the
        # agent wrote. Claiming more than that in the evidence string is the same
        # defect as claiming a row count nothing compared.
        return "PASS", ("commit records Reviewed-in: %s. This gate checked the trailer is present "
                        "and does not resolve the id against a review platform, so it points a "
                        "human at a review rather than proving one happened"
                        % review_id.group(1))
    if trailer and sig == "E":
        return "NO-DATA", ("signature present but this host could not verify it (git %G? = E): import the signer's public key "
                           "into the verifying keyring, or use a Reviewed-in: review id, which needs no keyring. "
                           "An unverifiable signature is not an approval")
    return "FAIL", "approval is a typed name with no signature or review id; a name in a text field is not a control (add a signed Approved-by trailer or a Reviewed-in review id)"


def gate_ran(root):
    receipts = find(root, RAN_RECEIPT)
    if not receipts:
        return "NO-DATA", "no ran-receipt.json; a SQL or pipeline change is not done until its check executed and left a receipt"
    problems = []
    unreadable = []
    nothing = []
    checked = 0
    for m in receipts:
        d, err = load_receipt(m)
        if d is None:
            unreadable.append("%s: %s" % (os.path.relpath(m, root), err))
            continue
        chks, note = _items(d, "checks")
        if not chks:
            nothing.append("%s: %s" % (os.path.relpath(m, root), note))
            continue
        for chk in chks:
            checked += 1
            if not isinstance(chk, dict):
                problems.append("entry %d in %s is %s, not a check object"
                                % (checked, os.path.relpath(m, root), type(chk).__name__))
                continue
            name = stated(chk.get("name")) or "check %d" % checked
            if stated(chk.get("name")) is None:
                problems.append("%s in %s records no name, so nothing in the report can say what "
                                "ran" % (name, os.path.relpath(m, root)))
            # An exit code is an integer and a duration is a number. `False`
            # satisfied `!= 0` and `True` satisfied a truthiness test, so
            # {"exit_code": false, "duration_ms": true} passed as "a zero exit and
            # a nonzero duration". Booleans are neither.
            code = chk.get("exit_code")
            if code is None:
                problems.append("%s: no exit code recorded (was it actually run?)" % name)
            elif isinstance(code, bool) or not isinstance(code, int):
                problems.append("%s: exit_code is %r, which is not an exit status integer"
                                % (name, code))
            elif code != 0:
                problems.append("%s: check exited nonzero (%s)" % (name, code))
            ms = chk.get("duration_ms")
            if isinstance(ms, bool) or not isinstance(ms, (int, float)):
                problems.append("%s: duration_ms is %r, which is not a measured duration in "
                                "milliseconds" % (name, ms))
            elif ms <= 0:
                problems.append("%s: zero or negative duration (a check that took no time did not run)" % name)
    if unreadable:
        return "FAIL", ("ran-receipt present but unparseable: %s; a receipt that cannot be read is a broken claim, not an absent one"
                        % ", ".join(unreadable))
    if problems:
        return "FAIL", "; ".join(problems[:6])
    if not checked:
        return "NO-DATA", ("ran-receipt present but records no checks (%s); a receipt with nothing in it is exactly what a run that never happened produces, so it is NO-DATA, never a pass"
                           % "; ".join(nothing))
    if nothing:
        return _partial(nothing, checked, "ran-receipt", "check(s)")
    return "PASS", "%d recorded check(s), each with a zero exit and a nonzero duration" % checked


# The registry is the contract. Each gate declares the evidence it opens, what its
# empty state is, and a worked receipt that SHOULD pass, and
# evals/test_no_data_class.py discovers exactly this dict: a gate added later is
# covered by the meta-test the moment it is registered, because it cannot be
# registered without the declaration. The full_fixture receipts below are minimal
# on purpose: every field in them is a field the PASS sentence asserts over, so
# the honesty test can empty any one of them and demand the PASS goes away.
GATES = {
    "numbers": Check(
        gate_numbers, reads=(MANIFEST,), kind="json", item_key="figures",
        full_fixture={"files": {MANIFEST: {"figures": [{
            "label": "gmv", "snapshot_id": "snap-2026-07",
            "query": "SELECT SUM(amount) FROM orders",
            "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
            "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]}}}),
    "migration": Check(
        gate_migration, reads=(MIGRATION_RECEIPT,), kind="json",
        full_fixture={"files": {MIGRATION_RECEIPT: {
            "forward": {"ran_against_restore": True},
            "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job-8842"},
            "row_counts": {"before": 100, "after_reverse": 100}}}}),
    "approval": Check(
        gate_approval, reads=(APPROVAL_FILE,), kind="git", empty_expect="FAIL",
        empty_fixture="",
        empty_note="the presence of an APPROVAL file IS the claim that this change touches a "
                   "money or partner path. An empty one is that claim with no identity behind "
                   "it, which is a broken claim and not an absence, so it FAILs rather than "
                   "reporting NO-DATA",
        full_fixture={"files": {APPROVAL_FILE: "touches the partner payout path\n"},
                      "git": {"message": "payout batching\n\nReviewed-in: PR-99999"}}),
    "ran": Check(
        gate_ran, reads=(RAN_RECEIPT,), kind="json", item_key="checks",
        full_fixture={"files": {RAN_RECEIPT: {"checks": [
            {"name": "reconcile", "exit_code": 0, "duration_ms": 812}]}}}),
}


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
    except Exception:  # sbe: allow-silent not a git worktree; root stays as given and every gate below still runs and still prints
        pass
    fails = 0
    print("BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)")
    for name in which:
        # Guarded per gate: a crash inside one gate used to abort the loop, so
        # every gate after it printed nothing at all and advisory mode exited 0.
        # A gate that vanishes is worse than a gate that fails.
        verdict, ev = run_guarded(name, GATES[name], root)
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
