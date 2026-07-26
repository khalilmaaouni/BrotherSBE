#!/usr/bin/env python3
"""BrotherSBE regression evals: each is a real failure class as a fixture, a
planted defect, and an assertion that the corresponding gate CATCHES it. A
release is blocked (exit nonzero) if any eval regresses. This is the mechanism
behind the claim that BrotherSBE is proven in traceable ways: the gates are
tested against the exact defects the operating record produced.

Every fixture is generalized: no client, employer, or private project appears.
"""
import fnmatch, json, os, sys, tempfile, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "..", "tools", "sbe_gate.py")
INTAKE = os.path.join(HERE, "..", "tools", "sbe_intake.py")


DESIGN_CLASSES = ("artifacts", "adr", "datamodel", "diagrams", "placeholder")
DESIGN = os.path.join(HERE, "..", "tools", "sbe_design.py")
TEMPLATES = os.path.join(HERE, "..", "templates", "dossier")


def run_gate(root, klass):
    script = DESIGN if klass in DESIGN_CLASSES else GATE
    out = subprocess.run([sys.executable, script, klass, root],
                         capture_output=True, text=True)
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == klass:
            return parts[1]
    return "?"


def write(root, rel, obj):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(obj, f) if isinstance(obj, (dict, list)) else f.write(obj)


def git_init(root):
    subprocess.run(["git", "-C", root, "init", "-q"], check=True)
    subprocess.run(["git", "-C", root, "config", "user.email", "e@e"], check=True)
    subprocess.run(["git", "-C", root, "config", "user.name", "T"], check=True)


CASES = []


def case(name, klass, expect):
    def deco(fn):
        CASES.append((name, klass, expect, fn))
        return fn
    return deco


# Design-side evals: the tier is computed, not judged.
from importlib.machinery import SourceFileLoader
_intake = SourceFileLoader("sbe_intake", os.path.join(HERE, "..", "tools", "sbe_intake.py")).load_module()


@case("tier-trivial-when-reversible-and-isolated", "tier", "T0")
def t1(root):
    return _intake.compute_tier({"changes_contract": False, "crosses_boundary": False,
                                 "reversible_under_hour": True, "touches_sensitive": False,
                                 "consumers": "none"})


@case("tier-system-when-sensitive", "tier", "T3")
def t2(root):
    return _intake.compute_tier({"changes_contract": False, "crosses_boundary": False,
                                 "reversible_under_hour": True, "touches_sensitive": True,
                                 "consumers": "none"})


@case("tier-feature-when-contract-changes", "tier", "T2")
def t3(root):
    return _intake.compute_tier({"changes_contract": True, "crosses_boundary": False,
                                 "reversible_under_hour": True, "touches_sensitive": False,
                                 "consumers": "some"})


@case("tier-change-when-one-boundary", "tier", "T1")
def t4(root):
    return _intake.compute_tier({"changes_contract": False, "crosses_boundary": True,
                                 "reversible_under_hour": True, "touches_sensitive": False,
                                 "consumers": "none"})


def _tier_or_refusal(answers):
    """The tier, or the sentence naming the answer the rule refused to interpret."""
    try:
        return _intake.compute_tier(answers)
    except _intake.UnreadableIntake as e:
        return "REFUSED: %s" % e


@case("tier-reads-the-y-n-vocabulary-its-own-prompt-teaches", "tier", "T0")
def t5(root):
    # Every answer honest, every answer written the way the tool asks for it. This
    # computed T3 (the maximum) because the string "n" is truthy, so an engineer
    # answering no to all five questions was handed seven artifacts of ceremony,
    # and a gate that blocks honest work is a gate that gets switched off.
    return _tier_or_refusal({"changes_contract": "n", "crosses_boundary": "n",
                             "reversible_under_hour": "y", "touches_sensitive": "n",
                             "consumers": "none"})


@case("tier-no-to-reversible-is-a-no-not-a-yes", "tier", "T3")
def t6(root):
    # The reproduction from the review, in the direction that hides work rather
    # than inflating it: "no, this is not reversible in under an hour" is the T3
    # rule's own trigger, and the string "no" being truthy computed T0, which
    # requires no artifact at all and makes every design check report NO-DATA at
    # exit 0.
    return _tier_or_refusal({"changes_contract": False, "crosses_boundary": False,
                             "reversible_under_hour": "no", "touches_sensitive": False,
                             "consumers": "none"})


@case("tier-refuses-a-consumers-value-it-does-not-know", "tier",
      "REFUSED: consumers='several' is not a recognized value (accepted: none, some, many)")
def t7(root):
    # "several" matched neither "some" nor "many" and fell through to the lowest
    # tier. An unrecognized value must never quietly mean no risk; it is reported
    # as unrecognized, exactly as sbe_decide.py reports one.
    return _tier_or_refusal({"changes_contract": False, "crosses_boundary": False,
                             "reversible_under_hour": True, "touches_sensitive": False,
                             "consumers": "several"})


@case("tier-refuses-an-answer-outside-the-yes-no-vocabulary", "tier",
      "REFUSED: touches_sensitive='maybe' is not a recognized value "
      "(accepted: false, n, no, true, y, yes, or a JSON boolean)")
def t8(root):
    return _tier_or_refusal({"changes_contract": False, "crosses_boundary": False,
                             "reversible_under_hour": True, "touches_sensitive": "maybe",
                             "consumers": "none"})


@case("tier-refuses-a-blank-answer-rather-than-reading-it-as-a-no", "tier",
      "REFUSED: crosses_boundary='' is not a recognized value "
      "(accepted: false, n, no, true, y, yes, or a JSON boolean)")
def t9(root):
    return _tier_or_refusal({"changes_contract": False, "crosses_boundary": "",
                             "reversible_under_hour": True, "touches_sensitive": False,
                             "consumers": "none"})


@case("an-unknown-tier-is-refused-rather-than-owing-no-artifact", "tier",
      "REFUSED: unknown tier 'T9'")
def t10(root):
    try:
        return _intake.required_artifacts("T9")
    except ValueError as e:
        return "REFUSED: %s" % str(e).split(" (expected")[0]


# 1. The filed model that overstated a five year total against its own components.
@case("overstated-total-caught", "numbers", "FAIL")
def c1(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "five_year_total", "snapshot_id": "snap_2026_07",
        "query": "SELECT SUM(y) FROM plan", "second_derivation": "SELECT y1+y2+y3+y4+y5 FROM plan_wide",
        "rerun": {"ran": True, "primary": 1938, "secondary": 432}}]})


# 2. A correct figure passes: pinned, independent, zero drift.
@case("sound-number-passes", "numbers", "PASS")
def c2(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": "snap_2026_07",
        "query": "SELECT SUM(amount) FROM orders", "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
        "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]})


# 3. A figure whose "second" check is a copy of the first is not independent.
@case("non-independent-derivation-caught", "numbers", "FAIL")
def c3(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "x", "snapshot_id": "s", "query": "SELECT SUM(a) FROM t",
        "second_derivation": "SELECT SUM(a) FROM t", "rerun": {"ran": True, "primary": 5, "secondary": 5}}]})


# 4. A number with no pinned snapshot against a live warehouse: drift risk.
@case("unpinned-read-caught", "numbers", "FAIL")
def c4(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "x", "query": "SELECT 1", "second_derivation": "SELECT 1 FROM dual",
        "rerun": {"ran": True, "primary": 1, "secondary": 1}}]})


# 4b. A figure marked rerun ran=true but missing the values needed to prove zero
# drift (no primary, no secondary) must FAIL, not PASS: a gate that reports
# "zero-drift check" without the numbers to compare is a figure shipping
# unverified while the evidence line claims otherwise.
@case("rerun-marked-ran-with-no-values-caught", "numbers", "FAIL")
def c4b(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "x", "snapshot_id": "s", "query": "SELECT SUM(a) FROM t",
        "second_derivation": "SELECT SUM(b) FROM t2", "rerun": {"ran": True}}]})


# 4c. An empty manifest is the cheapest way to defeat this gate: commit a file
# with no figures in it and a two-state checker prints PASS over zero figures,
# in evidence words that claim they were pinned and re-derived. Present but
# empty is NO-DATA, never a pass.
@case("empty-figures-manifest-is-nodata", "numbers", "NO-DATA")
def c4c(root):
    write(root, "numbers-manifest.json", {"figures": []})


# 4d. A manifest that exists and cannot be parsed is a broken claim, not an
# absent one, so it FAILs rather than falling back to the missing-file NO-DATA.
@case("malformed-manifest-caught", "numbers", "FAIL")
def c4d(root):
    write(root, "numbers-manifest.json", "this is not json at all\n")


# 4e. A misspelled key (figure, not figures) must not read as zero problems.
@case("misspelled-figures-key-is-nodata", "numbers", "NO-DATA")
def c4e(root):
    write(root, "numbers-manifest.json", {"figure": [{"label": "revenue"}]})


# 4f. A figure with no query at all has nothing for the second derivation to be
# independent of, so the textual-difference test is vacuous and must not pass.
@case("figure-with-no-query-caught", "numbers", "FAIL")
def c4f(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "x", "snapshot_id": "s", "second_derivation": "SELECT SUM(b) FROM t2",
        "rerun": {"ran": True, "primary": 5, "secondary": 5}}]})


# 5. A migration whose reverse never ran against a restore.
@case("untested-reverse-caught", "migration", "FAIL")
def c5(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": False},
        "row_counts": {"before": 100, "after_reverse": 100}})


# 6. A migration whose reverse receipt is free text, no resolvable id.
@case("unresolvable-rehearsal-id-caught", "migration", "FAIL")
def c6(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True},
        "row_counts": {"before": 100, "after_reverse": 100}})


# 7. A sound migration passes.
@case("sound-migration-passes", "migration", "PASS")
def c7(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job_8842"},
        "row_counts": {"before": 100, "after_reverse": 100}})


# 8. A reverse that dropped rows is caught by the row-count check.
@case("lossy-reverse-caught", "migration", "FAIL")
def c8(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job_1"},
        "row_counts": {"before": 100, "after_reverse": 61}})


# 9. A money-path change with only a typed name is not an approval.
@case("typed-name-approval-caught", "approval", "FAIL")
def c9(root):
    write(root, "APPROVAL", "touches partner billing path\n")
    git_init(root)
    open(os.path.join(root, "x"), "w").write("1")
    subprocess.run(["git", "-C", root, "add", "."], check=True)
    subprocess.run(["git", "-C", root, "commit", "-qm", "change\n\nApproved-by: Someone"], check=True)


# 10. A change with no money/partner claim needs no approval (NO-DATA, not fail).
@case("no-approval-needed-is-nodata", "approval", "NO-DATA")
def c10(root):
    git_init(root)
    open(os.path.join(root, "x"), "w").write("1")
    subprocess.run(["git", "-C", root, "add", "."], check=True)
    subprocess.run(["git", "-C", root, "commit", "-qm", "internal refactor"], check=True)


# 11. An SQL change with a receipt whose check has no exit code did not really run.
@case("unrun-check-caught", "ran", "FAIL")
def c11(root):
    write(root, "ran-receipt.json", {"checks": [{"name": "reconcile", "duration_ms": 0}]})


# 12. A pipeline change whose reconciliation actually ran passes.
@case("executed-check-passes", "ran", "PASS")
def c12(root):
    write(root, "ran-receipt.json", {"checks": [{"name": "reconcile", "exit_code": 0, "duration_ms": 812}]})


# 13. A check that ran and FAILED is caught (agent claimed green on red).
@case("green-on-red-caught", "ran", "FAIL")
def c13(root):
    write(root, "ran-receipt.json", {"checks": [{"name": "row_parity", "exit_code": 1, "duration_ms": 400}]})


# 13b. A zero-check receipt is exactly the artifact produced by a session that
# wants to look done without running anything. Present but empty is NO-DATA.
@case("empty-checks-receipt-is-nodata", "ran", "NO-DATA")
def c13b(root):
    write(root, "ran-receipt.json", {"checks": []})


# 13c. An unparseable ran-receipt is a broken claim, so it FAILs.
@case("malformed-ran-receipt-caught", "ran", "FAIL")
def c13c(root):
    write(root, "ran-receipt.json", "<<<garbage>>>\n")


# 13d. A key typo (check, not checks) must not read as zero problems.
@case("misspelled-checks-key-is-nodata", "ran", "NO-DATA")
def c13d(root):
    write(root, "ran-receipt.json", {"check": [{"name": "recon"}]})


# 13e. An unparseable migration receipt is a broken claim, not an absence.
@case("malformed-migration-receipt-caught", "migration", "FAIL")
def c13e(root):
    write(root, "migration-receipt.json", "{not json\n")


# The %G? codes, pinned. These call gate_approval directly with the signature
# status substituted, because producing a real E needs a signed commit whose key
# is absent from the keyring, which cannot be built inside a hermetic fixture.
# The decision under test is the mapping from code to verdict, and that is what
# is pinned here: G and U are approvals, E is NO-DATA, everything else FAILs.
_gate = SourceFileLoader("sbe_gate", os.path.join(HERE, "..", "tools", "sbe_gate.py")).load_module()
try:
    _checks = SourceFileLoader("sbe_checks", os.path.join(HERE, "..", "tools", "sbe_checks.py")).load_module()
except OSError as e:
    # This suite is run against older trees on purpose, to measure what it would
    # have caught. A tree with no sbe_checks.py is one of them, and the fixture
    # that needs it reports that rather than taking the whole run down.
    _checks = None
    _CHECKS_IMPORT_ERROR = "sbe_checks.py is not in this tree (%s)" % e


def _approval_with_sig(root, sig, approver="Someone", authors=("Dana Author", "dana@example.com")):
    """The approval verdict for a signature state, with the approver named.

    `authors` is what git says wrote the commit. It is a separate identity from
    the approver by default, because self-approval is its own FAIL now and these
    fixtures are about the SIGNATURE STATE, one variable at a time.
    """
    original = _gate.git_trailers
    _gate.git_trailers = lambda r: ("change\n\nApproved-by: %s" % approver, sig, list(authors))
    try:
        return _gate.gate_approval(root)[0]
    finally:
        _gate.git_trailers = original


# 13f. E means the signature could not be verified here, which on a runner with
# no imported keys is the result for EVERY signed commit, including one signed
# by a key nobody on the team recognises. Accepting it would trust the unknown
# while rejecting a known key that had merely expired. NO-DATA, not an approval.
@case("unverifiable-signature-E-is-not-an-approval", "sig", "NO-DATA")
def c13f(root):
    return _approval_with_sig(root, "E")


@case("verified-signature-G-approval-passes", "sig", "PASS")
def c13g(root):
    return _approval_with_sig(root, "G")


@case("valid-untrusted-signature-U-is-not-an-approval", "sig", "NO-DATA")
def c13g2(root):
    # U is "cryptographically valid, no matching principal". Under SSH signing,
    # the default for teams adopting commit signing today, that is exactly what
    # a key the agent generated for itself produces ("No principal matched"),
    # so accepting U made L9's "an agent without the private key cannot produce
    # it" false in four commands: ssh-keygen, two git configs, one commit.
    return _approval_with_sig(root, "U")


@case("a-trailing-period-does-not-make-a-second-person", "sig", "FAIL")
def c13i(root):
    return _approval_with_sig(root, "G", approver="Dana Author.")


@case("a-reordered-name-does-not-make-a-second-person", "sig", "FAIL")
def c13i2(root):
    return _approval_with_sig(root, "G", approver="Author, Dana")


@case("an-initial-does-not-make-a-second-person", "sig", "FAIL")
def c13i3(root):
    return _approval_with_sig(root, "G", approver="D. Author")


@case("a-plus-address-does-not-make-a-second-person", "sig", "FAIL")
def c13i4(root):
    return _approval_with_sig(root, "G", approver="dana+ops@example.com")


@case("a-role-suffix-does-not-make-a-second-person", "sig", "FAIL")
def c13i5(root):
    return _approval_with_sig(root, "G", approver="Dana Author (approver)")


@case("approved-by-todo-names-no-approver", "sig", "FAIL")
def c13i6(root):
    return _approval_with_sig(root, "G", approver="TODO")


@case("a-genuinely-different-approver-still-passes", "sig", "PASS")
def c13i7(root):
    # The control: hardening the identity comparison must not read every
    # colleague as the author.
    return _approval_with_sig(root, "G", approver="Robin Reviewer <robin@example.com>")


@case("bad-signature-B-is-not-an-approval", "sig", "FAIL")
def c13h(root):
    return _approval_with_sig(root, "B")


@case("expired-signature-X-is-not-an-approval", "sig", "FAIL")
def c13h2(root):
    return _approval_with_sig(root, "X")


@case("unsigned-commit-N-is-not-an-approval", "sig", "FAIL")
def c13h3(root):
    return _approval_with_sig(root, "N")


@case("a-soft-hyphen-does-not-make-a-second-person", "sig", "FAIL")
def c13i8(root):
    # U+00AD renders as nothing in git, GitHub and every ordinary terminal, so
    # this approver line READS as the author's own name and mailbox. The word
    # comparison and the plus-address canonicalization were both defeated by
    # two invisible bytes; identities now compare on their rendered skeleton.
    return _approval_with_sig(root, "G",
                              approver="Da\u00adna Author <dana+ops@exampl\u00ade.com>")


@case("a-homoglyph-does-not-make-a-second-person", "sig", "FAIL")
def c13i9(root):
    # Cyrillic U+0430 for ASCII "a": no invisible character at all, renders
    # identically, compares differently on code points. The skeleton maps the
    # lookalike onto the letter it renders as, so this reads as the author.
    return _approval_with_sig(root, "G", approver="D\u0430n\u0430 Author")


@case("a-confusable-outside-the-curated-table-is-refused-not-passed", "sig", "FAIL")
def c13i10(root):
    # COPTIC SMALL LETTER O (U+2C9F) renders as `o` and sat outside the
    # curated homoglyph table, so `Dana Authⲟr` compared as a second
    # person and restored the self-approval PASS on the money gate. The rule
    # replaces the table as the load-bearing part: a word mixing alphabets
    # after normalization and confusable folding is refused by name, so
    # certification of difference no longer depends on table coverage.
    return _approval_with_sig(root, "G", approver="Dana Authⲟr")


@case("a-same-script-lookalike-letter-is-refused-not-passed", "sig", "FAIL")
def c13i11(root):
    # LATIN LETTER SMALL CAPITAL A (U+1D00): same script family as ASCII, in
    # no confusable table, renders as the author's name. A mixed-SCRIPT rule
    # alone would pass it; the alphabet-readability rule refuses it, which is
    # the probe that the closure is a rule over the class and not a wider list.
    return _approval_with_sig(root, "G", approver="Dᴀna Author")


@case("a-multi-script-forgery-is-refused-whatever-scripts-it-uses", "sig", "FAIL")
def c13i12(root):
    # Armenian vo (U+0578, renders as n) plus Coptic o: two scripts the table
    # holds no rows for, in one identity. The forge must not depend on any
    # single script being catalogued.
    return _approval_with_sig(root, "G", approver="Daոa Authⲟr")


@case("a-partially-mapped-single-script-word-is-refused-not-passed", "sig", "FAIL")
def c13i13(root):
    # Cyrillic `Дана` (Dana): some letters fold to ASCII
    # through the confusable table and Д does not, so the folded word
    # mixes alphabets, which is precisely the point where table coverage runs
    # out. The refusal fires exactly there instead of certifying a difference
    # the fold cannot vouch for.
    return _approval_with_sig(root, "G", approver="Дана Author")


@case("a-wholly-single-script-approver-still-passes", "sig", "PASS")
def c13i14(root):
    # The control: an honest identity written wholly in one script reads and
    # compares. Refusing every non-Latin approver would be the gate rejecting
    # correct work, which is how gates get switched off.
    return _approval_with_sig(root, "G", approver="田中太郎 <tanaka@example.com>")


@case("an-invisible-character-is-not-an-answer-and-not-a-derivation", "numbers", "FAIL")
def c14inv(root):
    # snapshot_id is TODO plus a zero-width space; the second derivation is the
    # primary query plus one soft hyphen, rendering identically to it. Both
    # cleared the gate while its sentence asserted a pinned, independently
    # re-derived figure.
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": "TODO\u200b",
        "query": "SELECT SUM(amount) FROM orders",
        "second_derivation": "SELECT SUM(amount) FROM orders\u00ad",
        "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]})


@case("a-malformed-digit-grouping-is-not-a-number", "evidence", "refused")
def ev_num1(root):
    # "1,2,3" is not a number in any locale and read as 123; "17,5,70" read as
    # 17570, the worked example's own GMV, so a mistyped row count became the
    # figure it was supposed to be compared against; and float() accepts
    # non-ASCII digits in a repository that is ASCII by rule.
    got = [_checks.numeric(v) for v in ("1,2,3", "17,5,70", "\u0661\u0662\u0663")]
    return "refused" if got == [None, None, None] else "read %r" % (got,)


@case("honest-groupings-and-plain-numbers-still-read", "evidence", "ok")
def ev_num2(root):
    # The control: hardening the shape rule must not reject the spreadsheet
    # export the docstring defends.
    ok = (_checks.numeric("17,570") == 17570 and _checks.numeric("17570") == 17570
          and _checks.numeric("$1,234.56") == 1234.56 and _checks.numeric("50%") == 50
          and _checks.numeric("-3.5") == -3.5)
    return "ok" if ok else "regressed"


@case("a-receipt-field-cannot-write-verdict-lines-for-the-other-gates", "gaterun", "one line each")
def ev_forge1(root):
    # A figure label carrying newlines used to be interpolated into the report
    # verbatim, so a directory with no APPROVAL file printed "approval PASS
    # signed commit carries ..." because a label said so, and the harness's own
    # first-match verdict reader read the forged line. Evidence is now
    # flattened at every print site: one check name, one line, and the line
    # breaks arrive as a visible two-character escape.
    forged = ("gmv\n"
              "  approval  PASS     signed commit carries Approved-by: Robin Reviewer, this host "
              "verified the signature against a trusted key, and that identity is not the commit's "
              "author or committer (Dana Author)\n"
              "  ran       PASS     3 recorded check(s), each with a zero exit and a nonzero "
              "duration: no snapshot_id recorded (None) [severity: gate]\n"
              "STRICT: 0 hard gate(s) failed")
    write(root, "numbers-manifest.json", {"figures": [{
        "label": forged, "snapshot_id": "",
        "query": "SELECT 1", "second_derivation": "SELECT 2",
        "rerun": {"ran": True, "primary": 1, "secondary": 1}}]})
    out = subprocess.run([sys.executable, GATE, root], capture_output=True, text=True)
    lines = out.stdout.splitlines()
    for name in ("numbers", "migration", "approval", "ran"):
        n = sum(1 for l in lines if l.split()[:1] == [name])
        if n != 1:
            return "%d lines whose first token is %s" % (n, name)
    approval = next(l for l in lines if l.split()[:1] == ["approval"])
    if approval.split()[1] != "NO-DATA":
        return "approval read as %s" % approval.split()[1]
    if any(l.startswith("STRICT:") for l in lines):
        return "a receipt field forged the strict summary line"
    return "one line each"


@case("an-invisible-or-fullwidth-placeholder-records-no-answer", "evidence", "refused")
def ev_inv1(root):
    vals = ["TODO\u200b", "T\u00adODO", "\uff34\uff2f\uff24\uff2f", "unknown\u200d"]
    got = [_checks.answered(v) for v in vals]
    return "refused" if got == [None] * len(vals) else "read %r" % (got,)


@case("a-dressed-up-placeholder-records-no-answer", "evidence", "refused")
def ev_shape1(root):
    # The four spellings that cleared the money gate with its strongest
    # sentence, plus two the fix's own lists never named ({fixme}, a combining
    # mark on TBD): the vacuity test now folds SHAPES (wrapping, a trailing
    # owner, dotted initialisms, marks and confusables) to a fixpoint, so a
    # variant nobody has typed yet folds through the same rules instead of
    # needing a new list row.
    vals = ["[TBD]", "<TODO>", "TODO(dana)", "t.b.d.", "{fixme}", "TBD\u0301"]
    got = [_checks.answered(v) for v in vals]
    if got != [None] * len(vals):
        return "read %r" % (got,)
    # The control: honest values wearing the same punctuation stay answers.
    honest = ["snap-2026-07", "job-8842 (rerun)", "(see runbook 7)", "$100"]
    kept = [_checks.answered(v) for v in honest]
    return "refused" if all(k is not None for k in kept) else "refused honest %r" % (kept,)


@case("a-bracketed-placeholder-is-not-a-pin", "numbers", "FAIL")
def ev_shape2(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": "[TBD]",
        "query": "SELECT SUM(amount) FROM orders",
        "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
        "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]})


@case("a-container-snapshot-id-pins-nothing", "numbers", "FAIL")
def ev_shape3(root):
    # `snapshot_id: true` was closed a round ago; the sibling container shapes
    # were not, and the vacuity test is defined only on strings, so a dict or a
    # list carrying a placeholder was a pinned snapshot. The migration gate
    # already refuses a dict where a run id belongs; this is the same type rule
    # at the numbers gate's identifier.
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": {"note": "TODO"},
        "query": "SELECT SUM(amount) FROM orders",
        "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
        "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]})


@case("a-list-snapshot-id-pins-nothing", "numbers", "FAIL")
def ev_shape4(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": ["TODO"],
        "query": "SELECT SUM(amount) FROM orders",
        "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
        "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]})


@case("the-gate-examines-the-directory-it-was-named-not-the-git-toplevel", "gaterun", "NO-DATA")
def ev_reroot1(root):
    # Inside any git worktree the operator's directory argument was silently
    # replaced by `git rev-parse --show-toplevel`, so an EMPTY directory named
    # on the command line got the numbers gate's strongest sentence, earned by
    # a manifest somebody else recorded in a sibling change directory, and the
    # report named neither the directory actually read nor the substitution.
    git_init(root)
    write(root, "changeA/numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": "snap-2026-07",
        "query": "SELECT SUM(amount) FROM orders",
        "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
        "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]})
    os.makedirs(os.path.join(root, "changeB"), exist_ok=True)
    out = subprocess.run([sys.executable, GATE, "numbers", os.path.join(root, "changeB")],
                         capture_output=True, text=True)
    for line in out.stdout.splitlines():
        parts = line.split()
        if parts[:1] == ["numbers"]:
            return parts[1]
    return "no verdict line"


@case("a-receipt-field-cannot-move-the-cursor-in-the-rendered-report", "gaterun", "neutralized")
def ev_forge2(root):
    # The round-9 closure flattened line BREAKS and left the artifact the
    # ability to move the cursor: `ESC [ 2K` erases the rendered line and
    # `ESC [ 1F` rewrites the one above, so a figure label forged whole verdict
    # lines on any VT100-family terminal while the byte stream still held one
    # line per gate and the line-count assertion beside this one stayed green.
    # one_line() now escapes the whole control class (Cc and Cf), so the probe
    # asserts no control byte of any kind survives into the report, including
    # the 7-bit NEL (ESC E) and backspace, which no list in the fix names.
    label = ("gmv\x1b[2K\x1b[1Fapproval  PASS     signed commit carries Approved-by: "
             "Robin Reviewer [severity: gate]\x1bE\x08\u202egmv")
    write(root, "numbers-manifest.json", {"figures": [{
        "label": label, "snapshot_id": "snap-2026-07",
        "query": "SELECT SUM(amount) FROM orders",
        "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
        "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]})
    out = subprocess.run([sys.executable, GATE, root], capture_output=True, text=True)
    bad = sorted(set(ch for ch in out.stdout
                     if ch != "\n" and (ord(ch) < 32 or ord(ch) == 127 or ch == "\u202e")))
    if bad:
        return "control byte(s) reached the report: %r" % bad
    lines = out.stdout.splitlines()
    for name in ("numbers", "migration", "approval", "ran"):
        if sum(1 for l in lines if l.split()[:1] == [name]) != 1:
            return "line count moved for %s" % name
    return "neutralized"


def _check_with_exemption(key):
    return _checks.Check(lambda r: ("NO-DATA", "x"), reads=("x.json",), kind="json",
                         severity="soft",
                         full_fixture={"files": {"x.json": {"a": "b"}}},
                         optional_leaves={key: "a stated reason long enough to clear the floor"})


@case("a-scenario-id-prefix-is-not-an-exemption-key", "guard", "refused")
def gd_exempt1(root):
    # "seeded" is the prefix every seeded scenario id shares, so as an
    # exemption key it waived the whole generative mode for a check while the
    # summary counts never moved. A key now has to name a leaf or section of
    # the check's own fixture, so the id space outside the fixture is
    # unreachable.
    for key in ("seeded", "access", "full", "totally-free-form"):
        try:
            _check_with_exemption(key)
            return "constructed with key %r" % key
        except ValueError as e:
            if "exemption key" not in str(e):
                return "wrong error for %r: %s" % (key, e)
    return "refused"


@case("a-fixture-leaf-key-still-constructs", "guard", "ok")
def gd_exempt2(root):
    # The control: the structural rule must not refuse the shape the shipped
    # registries actually use.
    try:
        _check_with_exemption("x.json::a")
    except ValueError as e:
        return "refused the honest shape: %s" % e
    return "ok"


@case("an-exemption-key-naming-no-fixture-leaf-is-refused", "guard", "refused")
def gd_exempt_leaf(root):
    # The prefix check passed the FILE half and left the leaf half unvalidated,
    # so a constructor-legal key could name a leaf the fixture does not have,
    # and where a fixture file shared a name with a derived scenario namespace
    # one key waived a whole axis. The WHOLE key resolves now: a `::` leaf must
    # be a leaf or subtree of that file's JSON.
    for key in ("x.json::nonexistent", "x.json::a.deeper.path", "x.json::*"):
        try:
            _check_with_exemption(key)
            return "constructed with key %r naming no fixture leaf" % key
        except ValueError as e:
            if "not a leaf or subtree" not in str(e):
                return "wrong error for %r: %s" % (key, e)
    # The control: a real subtree path still constructs.
    try:
        _checks.Check(lambda r: ("NO-DATA", "x"), reads=("x.json",), kind="json", severity="soft",
                      full_fixture={"files": {"x.json": {"a": {"b": 1}}}},
                      optional_leaves={"x.json::a/*": "a stated reason long enough to clear the floor"})
    except ValueError as e:
        return "refused an honest subtree key: %s" % e
    return "refused"


@case("an-access-scenario-cannot-be-waived-by-any-key", "guard", "unwaivable")
def gd_exempt_axis(root):
    # The derived scenario-id namespace and the fixture-filename namespace were
    # the same string space, so a check whose fixture held a file named
    # `access` could write a legal key that matched the whole ACCESS axis under
    # the cap. Exemptibility is structural now: legacy, access and
    # declared-reads scenarios are non-exemptible whatever a key spells,
    # because "no PASS over evidence this tool could not open" is not a
    # sentence any exemption may narrow.
    meta = SourceFileLoader("tndc_axis", os.path.join(HERE, "test_no_data_class.py")).load_module()
    tool = meta.ADAPTERS[("sbe_gate.py", "GATES")]
    check = _gate.GATES["numbers"]
    for maker in (meta.legacy_cases, meta.access_cases):
        for sc in maker(tool, check):
            if sc.exemptible:
                return "a %s scenario (%s) is marked exemptible" % (sc.label, sc.sid)
    # And a hollowing scenario IS exemptible, so the flag is not constant-false.
    if not any(sc.exemptible for sc in meta.hollow_cases(tool, check)):
        return "no hollowing scenario is exemptible, so the flag means nothing"
    return "unwaivable"


@case("one-exemption-key-cannot-waive-a-whole-leaf-sweep", "guard", "capped")
def gd_exempt3(root):
    # The demonstrated bypass: a legal-format key naming one JSON leaf of the
    # numbers fixture matched the leaf's entire value sweep, and one such key
    # hid a real regression on that leaf behind an unchanged scenario total.
    # The meta-test now caps waived SCENARIOS per check; this eval rebuilds the
    # numbers check with exactly that key and asserts its sweep breadth is
    # over the cap, so the meta-test would fail it by count.
    meta = SourceFileLoader("tndc_guard", os.path.join(HERE, "test_no_data_class.py")).load_module()
    fx = _gate.GATES["numbers"].full_fixture
    clone = _checks.Check(_gate.gate_numbers, reads=(_gate.MANIFEST,), kind="json",
                          severity="gate", item_key="figures", full_fixture=fx,
                          optional_leaves={
                              "numbers-manifest.json::figures[0].snapshot_id":
                                  "a plausible-sounding sentence shaped like the shipped ones"})
    tool = meta.ADAPTERS[("sbe_gate.py", "GATES")]
    scs = (meta.legacy_cases(tool, clone) + meta.hollow_cases(tool, clone)
           + meta.access_cases(tool, clone))
    matched = sum(1 for sc in scs if clone.optional_leaves.get(sc.sid.split("|")[0]))
    if matched <= meta.WAIVED_SCENARIO_CAP:
        return ("a leaf key matches only %d scenario(s), inside the cap of %d, so the cap "
                "no longer bites" % (matched, meta.WAIVED_SCENARIO_CAP))
    return "capped"


@case("a-dead-waiver-that-excuses-nothing-is-a-meta-test-failure", "guard", "flagged dead")
def gd_dead_waiver(root):
    # Two of the four declared waivers shielded nothing: the placeholder
    # exemption's own scenarios FAILed anyway, so it excused no PASS while the
    # summary counted it. A waiver is alive (it excuses a real PASS) or it is
    # red, because a waiver that shields nothing is a pre-approved mark waiting
    # for a regression to hide under. This rebuilds the diagrams check with a
    # legal key on a leaf whose sweep never needs excusing (a booleanish leaf
    # that FAILs on any hollowing) and asserts the meta-test flags it dead.
    meta = SourceFileLoader("tndc_dead", os.path.join(HERE, "test_no_data_class.py")).load_module()
    fx = _design_mod.CHECKS["diagrams"].full_fixture
    # 05-data-model.md##Entities: hollowing the Entities section makes the
    # diagram untraceable, so every matched scenario FAILs and the waiver
    # excuses nothing.
    clone = _checks.Check(_design_mod.check_diagrams,
                          reads=_design_mod.CHECKS["diagrams"].reads, kind="text",
                          severity="gate", empty_expect="FAIL",
                          empty_note="x",
                          full_fixture=fx,
                          optional_leaves={"05-data-model.md##Entities":
                                           "a reason long enough to clear the reviewability floor"})
    tool = meta.ADAPTERS[("sbe_design.py", "CHECKS")]
    scs = (meta.legacy_cases(tool, clone) + meta.hollow_cases(tool, clone)
           + meta.access_cases(tool, clone))
    excused = 0
    for sc in scs:
        if not (sc.exemptible and clone.optional_leaves.get(sc.sid.split("|")[0])):
            continue
        import tempfile as _tf
        with _tf.TemporaryDirectory() as d:
            for rel, content in meta.subst(sc.files, d).items():
                tool.place(d, rel, content)
            if sc.setup:
                sc.setup(d)
            out = tool.invoke(d, "diagrams", meta.subst(sc.env, d))
            meta.restore_access(d)
        got, _ = meta.verdict_and_evidence(out.stdout, "diagrams")
        if got == "PASS":
            excused += 1
    return "flagged dead" if excused == 0 else "the waiver excused %d PASS(es), so it is alive" % excused


@case("a-module-planted-in-a-bytecode-cache-is-refused-not-executed", "guard", "refused unrun")
def gd_planted(root):
    # A .py under tools/__pycache__/ was imported and EXECUTED by the module
    # walk, counted in "N module(s)", and reported zero failures, while the
    # install verifier's exclusion list kept it invisible on disk. The walk
    # now refuses anything inside a bytecode cache (the interpreter owns that
    # directory name), names it as a failure, and never imports it.
    import shutil
    for rel in ("tools", "evals"):
        shutil.copytree(os.path.join(_REPO, rel), os.path.join(root, rel))
    cache = os.path.join(root, "tools", "__pycache__")
    os.makedirs(cache, exist_ok=True)
    marker = os.path.join(root, "PLANTED-RAN")
    with open(os.path.join(cache, "planted.py"), "w") as f:
        f.write("open(%r, 'w').write('this code executed')\n" % marker)
    meta = SourceFileLoader("tndc_planted",
                            os.path.join(root, "evals", "test_no_data_class.py")).load_module()
    sources = meta.tool_sources()
    if os.path.exists(marker):
        return "the planted module was executed"
    if any("__pycache__" in s for s in sources):
        return "the planted module was walked as source"
    if not any("planted.py" in p for p in meta.PLANTED_SOURCE):
        return "the planted module was skipped in silence, not named"
    return "refused unrun"


SCORE_TOOL = os.path.join(HERE, "..", "tools", "sbe_score.py")
TELEMETRY_TOOL = os.path.join(HERE, "..", "tools", "sbe_telemetry.py")
_design_mod = SourceFileLoader("sbe_design_eval",
                               os.path.join(HERE, "..", "tools", "sbe_design.py")).load_module()

# Every arrow form the Mermaid dialects ship, one fixture each: the identifier
# grammar was greedy through a trailing hyphen, so every two-dash arrow minted
# a phantom `Name-` node (the dashed reply `-->>`, the default idiom in every
# tutorial, FAILed honest work), and the unmatched activation suffix made
# `B-->>-A:` parse as no message at all (an undeclared service in one passed
# "all traceable").
ARROW_FORMS = {
    "solid ->": "Alpha->Beta: x", "solid ->>": "Alpha->>Beta: x",
    "dashed -->": "Alpha-->Beta: x", "dashed reply -->>": "Beta-->>Alpha: x",
    "activation ->>+": "Alpha->>+Beta: x", "deactivation -->>-": "Beta-->>-Alpha: x",
    "async -)": "Alpha-)Beta: x", "async dashed --)": "Alpha--)Beta: x",
    "cross -x": "Alpha-xBeta: x", "cross dashed --x": "Alpha--xBeta: x",
}


@case("every-sequence-arrow-form-reads-both-ends-and-mints-no-phantom", "evidence", "all clean")
def ev_arrows(root):
    for label, line in sorted(ARROW_FORMS.items()):
        body = ("x\n```mermaid\nsequenceDiagram\n  participant Alpha\n  participant Beta\n"
                "  %s\n```\n" % line)
        nodes, _kinds, _skipped, _states, _unread = _design_mod._diagram_nodes(body)
        if sorted(nodes) != ["Alpha", "Beta"]:
            return "%s -> %s" % (label, sorted(nodes))
    for label, block in (
            ("flowchart open ---", "flowchart LR\n  Alpha---Beta"),
            ("flowchart -->", "flowchart LR\n  Alpha-->Beta"),
            ("state -->", "stateDiagram-v2\n  Alpha --> Beta"),
            ("class --|>", "classDiagram\n  Alpha --|> Beta"),
            ("er ||--o{", "erDiagram\n  Alpha ||--o{ Beta : has")):
        nodes, _kinds, _skipped, _states, _unread = _design_mod._diagram_nodes(
            "x\n```mermaid\n%s\n```\n" % block)
        if sorted(nodes) != ["Alpha", "Beta"]:
            return "%s -> %s" % (label, sorted(nodes))
    return "all clean"


@case("the-default-dashed-reply-arrow-is-not-an-orphan", "diagrams", "PASS")
def ar1(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Producer: system of record: the queue.\n"
          "- Worker: system of record: the scheduler.\n"
          "## Relationships\n- Producer to Worker: one-to-many.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n## Delivery\n```mermaid\nsequenceDiagram\n"
          "  participant Producer\n  participant Worker\n"
          "  Producer->>Worker: deliver\n  Worker-->>Producer: 2xx or error\n```\n")


@case("a-ghost-service-in-a-deactivation-reply-is-caught", "diagrams", "FAIL")
def ar2(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Customer: system of record: the CRM.\n"
          "## Relationships\n- Customer to Customer: one-to-one, self.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nsequenceDiagram\n"
          "  Customer->>+Customer: self check\n"
          "  Customer-->>-totally-undeclared-service: reply lands on a ghost\n```\n")


@case("a-japanese-data-model-is-a-data-model", "datamodel", "PASS")
def uni1(root):
    # Every name grammar required an ASCII first letter while its continuation
    # class was Unicode-wide, so a dossier whose ubiquitous language is not
    # ASCII-first FAILed with a message instructing the author to do exactly
    # what they had done. A name starts at any letter, by property.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- 注文: system of record: the order service.\n"
          "- 注文明細: system of record: the order service.\n"
          "## Relationships\n- 注文 to 注文明細: one-to-many.\n")


@case("a-japanese-diagram-traces-to-japanese-entities", "diagrams", "PASS")
def uni2(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- 注文: system of record: the order service.\n"
          "- 注文明細: system of record: the order service.\n"
          "## Relationships\n- 注文 to 注文明細: one-to-many.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nerDiagram\n  注文 ||--o{ 注文明細 : 含む\n```\n")


@case("a-non-latin-ghost-node-is-an-orphan-not-a-silent-drop", "diagrams", "FAIL")
def uni3(root):
    # The 9a-C6 shape: a node in a non-Latin script was dropped by the ASCII
    # grammar and the check printed "all traceable" over what was left, with
    # the dropped token absent even from the disclosure channel.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Order: system of record: the OMS.\n"
          "- Payment: system of record: the ledger.\n"
          "## Relationships\n- Order to Payment: one-to-many.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nerDiagram\n  Order ||--o{ Payment : has\n"
          "  幽霊サービス ||--o{ Order : haunts\n```\n")


@case("an-accented-ghost-in-a-sequence-message-is-caught", "diagrams", "FAIL")
def uni4(root):
    # The 9b-2 shape: _SEQ_MESSAGE anchored on an ASCII sender, so a message
    # line whose first identifier starts with a non-ASCII letter was skipped
    # WHOLE, ghost included, and "all traceable" printed over the remainder.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Journal: system of record: the ledger.\n"
          "- Écriture: system of record: the ledger.\n"
          "## Relationships\n- Journal to Écriture: one-to-many.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nsequenceDiagram\n  participant Écriture\n"
          "  Écriture->>règlement-fantôme: not declared anywhere\n```\n")


@case("an-accented-entity-is-counted-not-silently-dropped", "evidence", "counted")
def uni5(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Journal: system of record: the ledger.\n"
          "- Écriture: system of record: the ledger.\n"
          "## Relationships\n- Journal to Écriture: one-to-many.\n")
    line = gate_line(root, "datamodel")
    if line.split()[1:2] != ["PASS"]:
        return line
    return "counted" if "2 entities" in line else line


@case("create-participant-keeps-its-alias-and-traces", "diagrams", "PASS")
def uni6(root):
    # Documented Mermaid syntax (v10.3+): `create participant A as
    # audit-worker` lost the alias, so A could not trace to the declared
    # component and an honest diagram FAILed naming an id the author never
    # meant to trace, with create and destroy dropped in silence.
    write(root, "04-technology-map.md",
          "# Technology map\n## Components\n| Component | Runtime |\n| --- | --- |\n"
          "| gateway | Go |\n| audit-worker | Python |\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nsequenceDiagram\n  participant G as gateway\n"
          "  create participant A as audit-worker\n  G->>A: audit this\n  destroy A\n```\n")


@case("the-skipped-list-names-canonical-note-and-destroy", "evidence", "named")
def uni7(root):
    # Mermaid's docs write `Note over G,W: text` capitalized; the statement
    # set held lowercase members and membership did not fold, so the canonical
    # spelling vanished from the skipped list the docstring promises is
    # complete, and so did create/destroy.
    body = ("x\n```mermaid\nsequenceDiagram\n  participant G\n  participant W\n"
            "  G->>W: go\n  Note over G,W: settled\n  destroy W\n```\n")
    _nodes, _kinds, skipped, _states, unread = _design_mod._diagram_nodes(body)
    if unread:
        return "unread: %s" % unread
    named = "; ".join(skipped)
    if "Note (" not in named:
        return "Note dropped from the skipped list: %s" % named
    if "destroy (" not in named:
        return "destroy dropped from the skipped list: %s" % named
    return "named"


@case("an-ampersand-multi-edge-reads-every-member", "diagrams", "FAIL")
def uni8(root):
    # `A & B --> C & D` is documented flowchart syntax; only arrow-adjacent
    # identifiers were read, so a ghost in an outer position passed "all
    # traceable" over a false node count.
    write(root, "04-technology-map.md",
          "# Technology map\n## Components\n| Component | Runtime |\n| --- | --- |\n"
          "| gateway | Go |\n| ledger | Java |\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nflowchart LR\n"
          "  totally-undeclared-shadow & gateway --> ledger\n```\n")


@case("an-ampersand-ghost-as-last-destination-is-caught", "diagrams", "FAIL")
def uni9(root):
    write(root, "04-technology-map.md",
          "# Technology map\n## Components\n| Component | Runtime |\n| --- | --- |\n"
          "| gateway | Go |\n| ledger | Java |\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nflowchart LR\n"
          "  gateway --> ledger & totally-undeclared-shadow\n```\n")


@case("a-line-the-parser-cannot-read-refuses-all-traceable", "diagrams", "NO-DATA")
def uni10(root):
    # A dropped-in-silence line was how every ghost above traveled. What the
    # parser cannot read at all is now a confession in the verdict, and the
    # completeness sentence is refused: a node could be hiding in it.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Order: system of record: the OMS.\n"
          "## Relationships\n- Order to Order: one-to-one, self.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nsequenceDiagram\n  participant Order\n"
          "  Order->>Order: check\n  🧾->>Order: a sender no grammar reads\n```\n")


@case("a-faithful-madr-with-one-rejection-fails-the-floor", "adr", "FAIL")
def madr1(root):
    # MADR's Considered Options section includes the chosen option BY
    # DEFINITION, and every bullet under it was counted as a rejected
    # alternative: the two-alternatives floor was satisfiable by
    # chosen-plus-one, the exact single-alternative ADR it exists to refuse.
    write(root, "03-adr.md",
          "# ADR\n## Context and Problem Statement\nRetried refunds double-settle.\n"
          "## Decision Drivers\nsettlement latency, audit trail\n"
          "## Considered Options\n- Idempotency key: dedupe retries at the boundary.\n"
          "- Nightly batch reconciliation: sweep duplicates after the fact.\n"
          "## Decision Outcome\nChosen option: \"Idempotency key\", because it stops the "
          "double-settle before it lands.\n"
          "## Consequences\nOne more key to mint and store.\n"
          "## What would flip this\nSub-second settlement becoming a requirement.\n")


@case("a-madr-with-two-real-rejections-passes-with-an-honest-count", "evidence", "counted")
def madr2(root):
    write(root, "03-adr.md",
          "# ADR\n## Context and Problem Statement\nRetried refunds double-settle.\n"
          "## Decision Drivers\nsettlement latency, audit trail\n"
          "## Considered Options\n- Idempotency key: dedupe retries at the boundary.\n"
          "- Nightly batch reconciliation: sweep duplicates after the fact.\n"
          "- Synchronous ledger call: ties checkout to ledger availability.\n"
          "### Pros and Cons of the Options\n"
          "#### Idempotency key\nGood, because it stops the double-settle early.\n"
          "#### Nightly batch reconciliation\nBad, because it misses the daily deadline.\n"
          "#### Synchronous ledger call\nBad, because it couples availability.\n"
          "## Decision Outcome\nChosen option: \"Idempotency key\", because it stops the "
          "double-settle before it lands.\n"
          "## Consequences\nOne more key to mint and store.\n"
          "## What would flip this\nSub-second settlement becoming a requirement.\n")
    line = gate_line(root, "adr")
    if line.split()[1:2] != ["PASS"]:
        return line
    if "2 distinct rejected alternatives" not in line:
        return "count wrong: %s" % line
    return "counted" if "counted as the decision" in line else "exclusion undisclosed: %s" % line


@case("a-gfm-table-without-leading-pipes-is-a-table", "datamodel", "PASS")
def gfm1(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "Entity | Meaning | System of record\n--- | --- | ---\n"
          "Customer | the buyer | the CRM\nOrder | a confirmed purchase | the order service\n"
          "\n## Relationships\n- Customer to Order: one-to-many.\n")


@case("a-setext-heading-is-a-heading", "datamodel", "PASS")
def setext1(root):
    write(root, "05-data-model.md",
          "Data model\n==========\n\nEntities\n--------\n"
          "- Customer: system of record: the CRM.\n- Order: system of record: the OMS.\n"
          "\nRelationships\n-------------\n- Customer to Order: one-to-many.\n")


@case("a-non-latin-sibling-is-a-named-script-limit-not-an-absence", "designrun", "disclosed")
def i6run(root):
    write(root, "00-intake.json",
          {"tier": "T1", "answers": {"changes_contract": False, "crosses_boundary": True,
                                     "reversible_under_hour": True, "touches_sensitive": False,
                                     "consumers": "none"}})
    write(root, "01-purpose.md",
          "# Purpose\nProblem: refunds settle late.\nUsers: support desk.\n"
          "Success: refunds reach a terminal state daily.\n")
    write(root, "02-process.md",
          "# Process\n返金の処理は毎日実行される。サポートデスクが結果を確認する。\n"
          "返金が失敗した場合は台帳に記録される。\n")
    out = subprocess.run([sys.executable, DESIGN, "artifacts", root],
                         capture_output=True, text=True)
    line = next((l for l in out.stdout.splitlines() if l.strip().startswith("artifacts")), "")
    if "nothing else to be coherent with" in line:
        return "still claims the sibling does not exist"
    if "different" not in line or "script" not in line:
        return "got: %s" % line.strip()[:140]
    return "disclosed"


def _score_lines(root, files):
    """Run the scorer against a throwaway vault holding `files` and return stdout."""
    for rel, content in files.items():
        if isinstance(content, list):
            # A list is JSONL here (one object per line), not a JSON array.
            content = "".join(json.dumps(row) + "\n" for row in content)
        write(root, rel, content)
    out = subprocess.run([sys.executable, SCORE_TOOL],
                         capture_output=True, text=True,
                         env=dict(os.environ, BROTHERSBE_VAULT=root,
                                  BROTHERSBE_REGISTRIES="", SBE_LINT_ROOT=""))
    return out.stdout


@case("migrate-preserves-the-line-it-cannot-parse-and-backs-up-bytes", "guard", "preserved")
def gd_migrate(root):
    # The loss guard compared two counts produced by the same lossy reader, so
    # it could never see the loss: the unparseable line vanished from the
    # ledger AND from the backup while the tool printed "count ok".
    led = "99-System/telemetry/outcomes.jsonl"
    original = ('{"schema":2,"session_id":"s1","ts":"2026-07-27T09:00:00Z"}\n'
                "{oops half a line\n"
                '{"schema":1,"session_id":"s2","out_tokens":10}\n')
    write(root, led, original)
    out = subprocess.run([sys.executable, TELEMETRY_TOOL, "migrate"],
                         capture_output=True, text=True,
                         env=dict(os.environ, BROTHERSBE_VAULT=root))
    body = open(os.path.join(root, led)).read()
    if "{oops half a line" not in body:
        return "the unparseable line was deleted from the ledger"
    backups = [f for f in os.listdir(os.path.dirname(os.path.join(root, led)))
               if ".bak-migrate" in f]
    if len(backups) != 1:
        return "no backup written"
    bak = open(os.path.join(root, "99-System/telemetry", backups[0])).read()
    if bak != original:
        return "the backup is not a byte copy of the original"
    if "unparseable line(s) preserved verbatim" not in out.stdout:
        return "the preserved line is not named: %s" % out.stdout.strip()
    return "preserved"


@case("a-reduction-does-not-delete-the-rows-the-disclosure-counts", "guard", "two named")
def gd_undated(root):
    # Two rows with no session_id and unreadable timestamps collapsed into ONE
    # under the dedupe key "?" before the undated guard could count them, so
    # the FAIL said "1 session row(s)" about a file holding two.
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = _score_lines(root, {"99-System/telemetry/outcomes.jsonl":
                              [{"ts": "bogus"}, {"ts": "bogus2"},
                               {"schema": 2, "session_id": "real1", "ts": now}]})
    line = next((l for l in out.splitlines() if l.startswith("ledger-coverage")), "")
    if "2 session row(s) carry no readable timestamp" not in line:
        return "got: %s" % line[:120]
    return "two named"


@case("one-prediction-in-five-spellings-is-one-prediction", "guard", "one counted")
def gd_predict(root):
    ledger = ("# Operator model\n## Prediction ledger\n"
              "date | prediction | seal | scored on | hit\n"
              "2026-07-01 | the queue drains | seal-1 | review | yes\n"
              "2026-07-02 | the queue drains. | seal-2 | review | yes\n"
              "2026-07-03 | The queue drains | seal-3 | review | yes\n"
              "2026-07-04 | the queue drains; | seal-4 | review | yes\n"
              "2026-07-05 | the queue drains, | seal-5 | review | yes\n")
    out = _score_lines(root, {"50-Reference/operator-model.md": ledger})
    line = next((l for l in out.splitlines() if l.startswith("prediction-seals")), "")
    if "1 sealed" not in line or "4 repeated prediction(s) counted once" not in line:
        return "got: %s" % line[:120]
    return "one counted"


@case("a-sealed-placeholder-is-not-a-prediction", "guard", "not counted")
def gd_predict2(root):
    # The vacuity rule reached the seal column and not the prediction: five
    # sealed TBD rows counted as five predictions.
    ledger = ("# Operator model\n## Prediction ledger\n"
              "date | prediction | seal | scored on | hit\n"
              + "".join("2026-07-0%d | TBD | seal-%d | review | yes\n" % (i, i)
                        for i in range(1, 6)))
    out = _score_lines(root, {"50-Reference/operator-model.md": ledger})
    line = next((l for l in out.splitlines() if l.startswith("prediction-seals")), "")
    if not line.split()[1:2] == ["NO-DATA"]:
        return "got: %s" % line[:120]
    return "not counted"


@case("one-rating-in-six-spellings-is-one-rating", "guard", "one counted")
def gd_ratings(root):
    rows = [{"score": 5, "task": "t", "note": n}
            for n in ("good", "good.", "good,", "good;", "GOOD", " good ")]
    out = _score_lines(root, {"99-System/telemetry/ratings.jsonl": rows})
    line = next((l for l in out.splitlines() if l.startswith("felt-outcome-ratings")), "")
    if "1 distinct ratings" not in line:
        return "got: %s" % line[:120]
    return "one counted"


@case("an-unreadable-review-timestamp-cannot-hide-the-real-reviews", "guard", "named")
def gd_reviews(root):
    # max() over raw timestamp strings let {"ts": "whenever"} beat every date
    # lexically, and the check reported "no review recorded" about a file
    # holding one from seconds ago.
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = _score_lines(root, {"99-System/telemetry/reviews.jsonl":
                              [{"ts": now}, {"ts": "whenever"}]})
    line = next((l for l in out.splitlines() if l.startswith("review-cadence")), "")
    if "no readable timestamp" not in line or "'whenever'" not in line:
        return "got: %s" % line[:120]
    return "named"


@case("an-infinite-cache-counter-is-not-a-measurement", "guard", "refused")
def gd_cacheinf(root):
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write(root, "99-System/telemetry/outcomes.jsonl",
          '{"schema":2,"session_id":"sess-0001","ts":"%s","cache_read":Infinity,"cache_write":5}\n'
          % now)
    out = subprocess.run([sys.executable, SCORE_TOOL],
                         capture_output=True, text=True,
                         env=dict(os.environ, BROTHERSBE_VAULT=root,
                                  BROTHERSBE_REGISTRIES="", SBE_LINT_ROOT=""))
    line = next((l for l in out.stdout.splitlines() if l.startswith("cache-economy")), "")
    if not line.split()[1:2] == ["FAIL"] or "not counts" not in line:
        return "got: %s" % line[:120]
    return "refused"


@case("dedup-refuses-to-rewrite-a-file-it-cannot-fully-read", "guard", "refused")
def gd_dedup(root):
    led = "99-System/telemetry/outcomes.jsonl"
    original = ('{"schema":2,"session_id":"s1","ts":"2026-07-27T09:00:00Z"}\n'
                "{broken\n")
    write(root, led, original)
    out = subprocess.run([sys.executable, TELEMETRY_TOOL, "dedup"],
                         capture_output=True, text=True,
                         env=dict(os.environ, BROTHERSBE_VAULT=root))
    if open(os.path.join(root, led)).read() != original:
        return "dedup rewrote a file with unparseable lines"
    if "refusing to rewrite" not in out.stdout:
        return "the refusal is not named: %s" % out.stdout.strip()[:120]
    return "refused"


@case("verify-install-fails-over-source-in-an-excluded-path", "guard", "named and failed")
def gd_vinstall(root):
    # The completeness sentence claimed "no file exists on disk that the
    # manifest does not name" over paths the enumeration excluded by name.
    # The exclusions are now enumerated and counted on every run, and source
    # code among them is its own failure.
    import hashlib, shutil
    inst = os.path.join(root, "inst")
    os.makedirs(os.path.join(inst, "scripts"))
    shutil.copy(os.path.join(_REPO, "scripts", "verify-install.sh"),
                os.path.join(inst, "scripts", "verify-install.sh"))
    write(root, "inst/hello.txt", "hi\n")
    with open(os.path.join(inst, "CHECKSUMS.sha256"), "w") as f:
        for rel in ("hello.txt", "scripts/verify-install.sh"):
            h = hashlib.sha256(open(os.path.join(inst, rel), "rb").read()).hexdigest()
            f.write("%s  %s\n" % (h, rel))
    clean = subprocess.run(["sh", os.path.join(inst, "scripts", "verify-install.sh"),
                            os.path.join(inst, "CHECKSUMS.sha256"), inst],
                           capture_output=True, text=True)
    if clean.returncode != 0:
        return "the control tree failed: %s" % (clean.stdout + clean.stderr)[-200:]
    if "outside the excluded paths" not in clean.stdout:
        return "the PASSED sentence still claims completeness with no qualifier"
    os.makedirs(os.path.join(inst, "tools", "__pycache__"))
    write(root, "inst/tools/__pycache__/planted.py", "print('invisible')\n")
    planted = subprocess.run(["sh", os.path.join(inst, "scripts", "verify-install.sh"),
                              os.path.join(inst, "CHECKSUMS.sha256"), inst],
                             capture_output=True, text=True)
    if planted.returncode == 0:
        return "planted source in an excluded path still passes"
    if "EXCLUDED-SOURCE" not in planted.stdout or "planted.py" not in planted.stdout:
        return "the failure does not name the planted file"
    return "named and failed"


@case("a-symlinked-planted-module-fails-the-install-check", "guard", "named and failed")
def gd_vinstall_symlink(root):
    # `find -type f` never returns a symlink, so a planted tools/backdoor.py
    # pointing at code OUTSIDE the tree was reported as nothing at all by
    # verify-install and imported-and-executed by the honesty suite. The check
    # enumerates every directory entry regardless of type now, and a
    # non-regular entry the manifest cannot hash is its own failure.
    import hashlib, shutil
    inst = os.path.join(root, "inst")
    os.makedirs(os.path.join(inst, "scripts"))
    os.makedirs(os.path.join(inst, "tools"))
    shutil.copy(os.path.join(_REPO, "scripts", "verify-install.sh"),
                os.path.join(inst, "scripts", "verify-install.sh"))
    write(root, "inst/tools/real.py", "def f():\n    return 1\n")
    with open(os.path.join(inst, "CHECKSUMS.sha256"), "w") as f:
        for rel in ("tools/real.py", "scripts/verify-install.sh"):
            h = hashlib.sha256(open(os.path.join(inst, rel), "rb").read()).hexdigest()
            f.write("%s  %s\n" % (h, rel))
    clean = subprocess.run(["sh", os.path.join(inst, "scripts", "verify-install.sh"),
                            os.path.join(inst, "CHECKSUMS.sha256"), inst],
                           capture_output=True, text=True)
    if clean.returncode != 0:
        return "the control tree failed: %s" % (clean.stdout + clean.stderr)[-200:]
    payload = os.path.join(root, "outside-payload.py")
    write(root, "outside-payload.py", "print('PLANTED')\n")
    os.symlink(payload, os.path.join(inst, "tools", "backdoor.py"))
    planted = subprocess.run(["sh", os.path.join(inst, "scripts", "verify-install.sh"),
                              os.path.join(inst, "CHECKSUMS.sha256"), inst],
                             capture_output=True, text=True)
    if planted.returncode == 0:
        return "the symlinked planted module still passes"
    if "NON-REGULAR" not in planted.stdout or "backdoor.py" not in planted.stdout:
        return "the failure does not name the symlinked module: %s" % planted.stdout[-200:]
    return "named and failed"


@case("a-symlinked-module-under-tools-fails-the-honesty-suite", "guard", "refused unwalked")
def gd_symlink_module(root):
    # The other half of the same hole: tool_sources() walked with `find`-like
    # semantics and imported every .py, symlinks included, so the planted
    # module RAN inside the suite whose one job is refusing to report over
    # what it did not examine. A non-regular .py under tools/ is refused by
    # name now, never imported.
    import shutil
    for rel in ("tools", "evals"):
        shutil.copytree(os.path.join(_REPO, rel), os.path.join(root, rel))
    payload = os.path.join(root, "outside-payload.py")
    marker = os.path.join(root, "PLANTED-RAN")
    write(root, "outside-payload.py", "open(%r, 'w').write('ran')\n" % marker)
    os.symlink(payload, os.path.join(root, "tools", "backdoor.py"))
    meta = SourceFileLoader("tndc_symlink",
                            os.path.join(root, "evals", "test_no_data_class.py")).load_module()
    sources = meta.tool_sources()
    if os.path.exists(marker):
        return "the symlinked module was executed"
    if any("backdoor.py" in s for s in sources):
        return "the symlinked module was walked as source"
    if not any("backdoor.py" in p for p in meta.NONREGULAR_SOURCE):
        return "the symlinked module was dropped in silence, not named"
    return "refused unwalked"


@case("the-tracked-manifest-matches-the-tree-it-ships-with", "guard", "matches")
def gd_manifest_fresh(root):
    # A pristine clone of HEAD failed its own integrity check: CHECKSUMS.sha256
    # went stale across a whole fix wave because nothing gated the manifest
    # against the tree, so the security page's first verification called every
    # honest fresh install untrustworthy and the shipped harness a planted
    # backdoor. This recomputes the manifest from the tracked tree and diffs it
    # against the committed one, so a stale manifest is a red suite (the same
    # shape as the doc-count guards) and no commit can leave one behind.
    import re as _re
    gen = subprocess.run(["sh", os.path.join(_REPO, "scripts", "checksums.sh")],
                         capture_output=True, text=True, cwd=_REPO)
    if gen.returncode != 0:
        return "checksums.sh did not run: %s" % (gen.stderr or gen.stdout)[-200:]
    committed = open(os.path.join(_REPO, "CHECKSUMS.sha256"), errors="replace").read()
    # The generator omits the manifest file itself; compare the rest verbatim.
    want = "".join(l + "\n" for l in gen.stdout.splitlines()
                   if l.strip() and not l.endswith("CHECKSUMS.sha256"))
    have = "".join(l + "\n" for l in committed.splitlines()
                   if l.strip() and not l.endswith("CHECKSUMS.sha256"))
    if want == have:
        return "matches"
    wl = {l.split("  ", 1)[1]: l[:64] for l in want.splitlines() if "  " in l}
    hl = {l.split("  ", 1)[1]: l[:64] for l in have.splitlines() if "  " in l}
    drift = [p for p in sorted(set(wl) | set(hl))
             if wl.get(p) != hl.get(p)][:4]
    return "the tracked manifest is stale for: %s (regenerate with scripts/checksums.sh " \
           "CHECKSUMS.sha256)" % ", ".join(drift)


T2_ANSWERS = {"changes_contract": True, "crosses_boundary": False,
              "reversible_under_hour": True, "touches_sensitive": False, "consumers": "some"}
T1_ANSWERS = {"changes_contract": False, "crosses_boundary": True,
              "reversible_under_hour": True, "touches_sensitive": False, "consumers": "none"}
T3_ANSWERS = {"changes_contract": True, "crosses_boundary": True,
              "reversible_under_hour": False, "touches_sensitive": True, "consumers": "many"}
PURPOSE = "# Purpose\nProblem: x\nUsers: y\nSuccess: z\nNon-goals: w\nIf wrong: v\n"


@case("missing-required-artifact-caught", "artifacts", "FAIL")
def d1(root):
    write(root, "00-intake.json", {"tier": "T2", "answers": T2_ANSWERS, "override": None})
    write(root, "01-purpose.md", PURPOSE)


@case("complete-t1-dossier-passes", "artifacts", "PASS")
def d2(root):
    write(root, "00-intake.json", {"tier": "T1", "answers": T1_ANSWERS, "override": None})
    write(root, "01-purpose.md", PURPOSE)


@case("adr-without-rejected-alternatives-caught", "adr", "FAIL")
def d3(root):
    write(root, "03-adr.md", "# ADR\n## Decision\nUse a modular monolith.\n## Consequences\nOne deploy.\n")


@case("adr-with-alternatives-and-flip-passes", "adr", "PASS")
def d4(root):
    write(root, "03-adr.md", "# ADR\n## Criteria\nteam size, consistency\n"
                             "## Options considered\n### Rejected: microservices\nToo much ops load.\n"
                             "### Rejected: single script\nNo isolation.\n"
                             "## Decision\nModular monolith.\n## Consequences\nOne deploy.\n"
                             "## What would flip this\nMore than three deploying teams.\n")


@case("unspecified-cardinality-caught", "datamodel", "FAIL")
def d5(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer: system of record CRM\n"
                                    "## Relationships\n- Customer to Order: ?\n")


@case("entity-without-system-of-record-caught", "datamodel", "FAIL")
def d6(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer\n"
                                    "## Relationships\n- Customer to Order: one-to-many\n")


@case("sound-data-model-passes", "datamodel", "PASS")
def d7(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer: system of record CRM\n"
                                    "- Order: system of record OMS\n"
                                    "## Relationships\n- Customer to Order: one-to-many, optional\n")


@case("orphan-diagram-node-caught", "diagrams", "FAIL")
def d8(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer: system of record CRM\n")
    write(root, "06-diagrams.md", "```mermaid\nflowchart LR\n  Customer --> Invoice\n```\n")


@case("consistent-diagram-passes", "diagrams", "PASS")
def d9(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer: system of record CRM\n"
                                    "- Order: system of record OMS\n")
    write(root, "06-diagrams.md", "```mermaid\nflowchart LR\n  Customer -->|places| Order\n```\n")


# 10. A node written with bracket shape syntax that appears nowhere else in the
# dossier must still be caught as an orphan (regex must capture bracket nodes).
@case("orphan-node-in-bracket-syntax-caught", "diagrams", "FAIL")
def d10(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Order: system of record OMS\n")
    write(root, "06-diagrams.md", "```mermaid\nflowchart LR\n  FakeVendor[Not A Real Entity] --> Order\n```\n")


# 11. A legitimate erDiagram (entity-relationship syntax) whose entities all
# appear in the data model must pass, not hard-fail with "no diagram nodes found".
@case("er-diagram-nodes-recognized-passes", "diagrams", "PASS")
def d11(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- CUSTOMER: system of record CRM\n"
                                    "- ORDER: system of record OMS\n")
    write(root, "06-diagrams.md", "```mermaid\nerDiagram\n  CUSTOMER ||--o{ ORDER : places\n```\n")


# 13. A diagram with no data model to trace against must be NO-DATA, never PASS:
# with an empty known-entity set every invented node looks traceable, which is the
# defect L5 exists to catch.
@case("diagram-without-data-model-is-nodata", "diagrams", "NO-DATA")
def d13(root):
    write(root, "06-diagrams.md", "```mermaid\nflowchart LR\n  Invented --> AlsoInvented\n```\n")


# 12. An intake file with no tier key must be NO-DATA, never a silent PASS.
@case("missing-tier-is-nodata", "artifacts", "NO-DATA")
def d12(root):
    write(root, "00-intake.json", {"answers": {}, "override": None})


# The trust boundary the whole design gate sits on: the tier written in the file
# against the tier its own answers compute. Trusting the field made every artifact
# requirement two keystrokes away.
@case("tier-lowered-by-hand-without-a-reason-caught", "artifacts", "FAIL")
def d14(root):
    write(root, "00-intake.json", {"tier": "T0", "answers": T3_ANSWERS,
                                   "override": None, "override_reason": None})


@case("declared-override-with-a-reason-is-honoured", "artifacts", "PASS")
def d15(root):
    write(root, "00-intake.json", {"tier": "T1", "answers": T3_ANSWERS, "override": "T1",
                                   "override_reason": "read-only backfill, agreed with the data owner"})
    write(root, "01-purpose.md", PURPOSE)


@case("intake-without-answers-is-nodata", "artifacts", "NO-DATA")
def d16(root):
    write(root, "00-intake.json", {"tier": "T3", "override": None})


@case("malformed-intake-caught", "artifacts", "FAIL")
def d17(root):
    write(root, "00-intake.json", "{not json at all\n")


# An ADR listing its alternatives as bullets under one heading is the natural
# authoring form and must pass; two empty headings must not.
@case("bulleted-rejected-alternatives-pass", "adr", "PASS")
def d18(root):
    write(root, "03-adr.md", "# ADR\n## Criteria\nlatency, freshness\n"
                             "## Rejected alternatives\n"
                             "- Synchronous API call: ties checkout latency to warehouse availability.\n"
                             "- Nightly batch: fails the freshness requirement.\n"
                             "## Decision\nPublish to a queue.\n## Consequences\nOne more moving part.\n"
                             "## What would flip this\nSub-second freshness becomes a requirement.\n")


@case("empty-rejected-headings-caught", "adr", "FAIL")
def d19(root):
    write(root, "03-adr.md", "# ADR\n## Criteria\nc\n## Rejected\n## Rejected\n"
                             "## Decision\nd\n## Consequences\ne\n## What would flip this\nf\n")


# Prose that says the opposite of what the rule requires must not pass on a
# substring match: a stated TBD is not a system of record, and "one-to-many-ish"
# is not a cardinality.
@case("undecided-system-of-record-caught", "datamodel", "FAIL")
def d20(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer: system of record: TBD\n"
                                    "- Order: no system of record known yet\n"
                                    "## Relationships\n- Customer to Order: one-to-many\n")


@case("hedged-cardinality-caught", "datamodel", "FAIL")
def d21(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer: system of record CRM\n"
                                    "## Relationships\n- Customer to Order: this is a one-to-many-ish thing we have not decided\n")


# A dossier copied from templates/dossier and never edited must not clear the
# design gate on someone else's example.
@case("unedited-copied-template-caught", "placeholder", "FAIL")
def d22(root):
    for name in os.listdir(TEMPLATES):
        if name.endswith(".md") and name[0].isdigit():
            write(root, name, open(os.path.join(TEMPLATES, name)).read())
    write(root, "00-intake.json", {"tier": "T3", "answers": T3_ANSWERS, "override": None})


@case("edited-dossier-has-no-unfilled-marker", "placeholder", "PASS")
def d23(root):
    write(root, "01-purpose.md", PURPOSE)


@case("no-artifacts-at-all-is-nodata-not-a-pass", "placeholder", "NO-DATA")
def d24(root):
    write(root, "00-intake.json", {"tier": "T0", "answers": {"reversible_under_hour": True,
                                                             "consumers": "none"}, "override": None})


# The CI wiring case: the documented layout puts the dossier in design/<project>/
# while CI runs from the repository root. Checking only <root>/00-intake.json
# reported NO-DATA and exit 0 with a full dossier two directories away.
@case("dossier-in-a-subdirectory-is-found", "artifacts", "FAIL")
def d25(root):
    write(root, "design/orders/00-intake.json", {"tier": "T2", "answers": T2_ANSWERS, "override": None})
    write(root, "design/orders/01-purpose.md", PURPOSE)


@case("complete-dossier-in-a-subdirectory-passes", "artifacts", "PASS")
def d26(root):
    write(root, "design/orders/00-intake.json", {"tier": "T1", "answers": T1_ANSWERS, "override": None})
    write(root, "design/orders/01-purpose.md", PURPOSE)


SCORE = os.path.join(HERE, "..", "tools", "sbe_score.py")


def run_score_lints(args):
    out = subprocess.run([sys.executable, SCORE] + args, capture_output=True, text=True)
    for line in out.stdout.splitlines():
        parts = line.split()
        if parts and parts[0] == "silent-failure-lints":
            return parts[1]
    return "?"


# A lint run that opened no file reported PASS with the evidence word "clean",
# which asserts the opposite of what happened. Nothing scanned is NO-DATA.
@case("lints-with-no-root-are-nodata-not-clean", "lints", "NO-DATA")
def s1(root):
    return run_score_lints([])


@case("lints-on-a-mistyped-path-are-caught", "lints", "FAIL")
def s2(root):
    return run_score_lints([os.path.join(root, "no-such-dir")])


@case("lints-on-real-source-name-what-was-scanned", "lints", "PASS")
def s3(root):
    write(root, "ok.py", "def f():\n    return 1\n")
    return run_score_lints([root])


@case("lints-catch-a-swallowed-error", "lints", "FAIL")
def s4(root):
    write(root, "bad.py", "try:\n    f()\nexcept:\n    pass\n")  # sbe: allow-silent this is the lint FIXTURE: the swallow is the defect under test, written into a temp file, never executed here
    return run_score_lints([root])


@case("lints-do-not-fail-a-repo-over-a-virtualenv-with-an-unusual-name", "lints", "PASS")
def s5(root):
    # The one gate a .sbe-exempt cannot waive, failing a team over code it did not
    # write and cannot fix. `.venv` and `venv` were the entire skip list here, so
    # `.venv-whisper` (or `.tox`, or `env39`) put every vendored file through it:
    # 1127 hits in 8109 files against a real repository. Vendored code is now
    # skipped by detection, not by exact name.
    write(root, "src/app.py", "def f():\n    return 1\n")
    write(root, ".venv-whisper/lib/python3.9/site-packages/thirdparty.py",
          "try:\n    f()\nexcept Exception:\n    pass\n")  # sbe: allow-silent this is the lint FIXTURE: the swallow is the defect under test, written into a temp file, never executed here
    return run_score_lints([root])


@case("lints-still-read-the-repos-own-source-beside-a-virtualenv", "lints", "FAIL")
def s6(root):
    # The control for the case above: skipping vendored trees must not become a
    # way to hide the repository's own swallowed error one directory over.
    write(root, ".venv-whisper/pyvenv.cfg", "home = /usr/bin\n")
    write(root, ".venv-whisper/lib/thirdparty.py",
          "try:\n    f()\nexcept Exception:\n    pass\n")  # sbe: allow-silent lint FIXTURE, see above
    write(root, "src/app.py",
          "try:\n    f()\nexcept Exception:\n    pass\n")  # sbe: allow-silent lint FIXTURE, see above
    return run_score_lints([root])


_decide = SourceFileLoader("sbe_decide", os.path.join(HERE, "..", "tools", "sbe_decide.py")).load_module()
_TABLES = json.load(open(os.path.join(HERE, "..", "tables", "architecture.json")))


@case("small-team-strong-consistency-is-not-microservices", "decide", "modular monolith")
def a1(root):
    r = _decide.recommend(_TABLES["shape"], {"deploying_teams": 1, "consistency": "strong",
                                             "ops_maturity": "low", "failure_isolation": "low"})
    return r["recommendation"]


@case("many-teams-high-isolation-is-services", "decide", "services")
def a2(root):
    r = _decide.recommend(_TABLES["shape"], {"deploying_teams": 6, "consistency": "eventual",
                                             "ops_maturity": "high", "failure_isolation": "high"})
    return r["recommendation"]


@case("recommendation-always-names-a-flip-condition", "decide", "yes")
def a3(root):
    r = _decide.recommend(_TABLES["shape"], {"deploying_teams": 1, "consistency": "strong",
                                             "ops_maturity": "low", "failure_isolation": "low"})
    return "yes" if r["flip_condition"] and len(r["alternatives"]) == 2 else "no"


# Discriminates services from event-driven on deploying_teams=3, which only
# event-driven's range covers (services needs 4+). The many-teams fixture above
# ties services and event-driven and only resolves by table-order tie-break; if
# the deploying_teams criterion were broken this fixture would fail where that
# one would not.
@case("low-team-count-high-isolation-is-event-driven", "decide", "event-driven")
def a4(root):
    r = _decide.recommend(_TABLES["shape"], {"deploying_teams": 3, "consistency": "eventual",
                                             "ops_maturity": "high", "failure_isolation": "high"})
    return r["recommendation"]


# An empty context contributes zero criteria: the recommender must say NO-DATA,
# never a confident guess dressed up as a recommendation.
@case("empty-context-is-no-data", "decide", "NO-DATA")
def a5(root):
    r = _decide.recommend(_TABLES["shape"], {})
    return r["verdict"]


# A non-numeric value for a number criterion must not crash; it must land in
# unrecognized, just like an unrecognized choice value.
@case("non-numeric-number-criterion-is-unrecognized", "decide", "unrecognized")
def a6(root):
    r = _decide.recommend(_TABLES["shape"], {"deploying_teams": "notanumber"})
    return "unrecognized" if r["unrecognized"] and not r["deciding_criteria"] else "fail"


# Asking for a decision family that has no table must name the tables that ship,
# not raise KeyError. One table exists; the laws say so, and so does the tool.
@case("unknown-table-key-names-what-ships", "decide", "named-error")
def a7(root):
    table, err = _decide.load_table(os.path.join(HERE, "..", "tables", "architecture.json"), "storage")
    return "named-error" if table is None and "shape" in err else "fail"


@case("missing-table-file-names-itself", "decide", "named-error")
def a8(root):
    table, err = _decide.load_table(os.path.join(root, "nope.json"), "shape")
    return "named-error" if table is None and "cannot read table file" in err else "fail"


# ---------------------------------------------------------------------------
# Second wave. The defect these pin is one defect: a verdict that asserts
# something the tool never inspected. The first wave fixed six named instances
# of it and a re-review found four more alive in the files that wave edited, so
# every fixture below is either a new instance of that class or the positive
# path of a behaviour that had none.
# ---------------------------------------------------------------------------

def gate_line(root, klass):
    """The whole verdict line, so a fixture can pin the EVIDENCE and not only the
    verdict. A gate that says PASS for the right reason and a gate that says PASS
    while claiming work nobody did are the same string to a verdict-only test."""
    script = DESIGN if klass in DESIGN_CLASSES else GATE
    out = subprocess.run([sys.executable, script, klass, root], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == klass:
            return line.strip()
    return ""


def design_run(root, env=None):
    """--strict from a search root: 'blocked' or 'clear'. Some behaviour only
    exists at the top level (which dossiers are walked, what --strict does with
    them) and a per-check runner cannot see it."""
    e = dict(os.environ)
    e["SBE_DOSSIER_ROOT"] = ""
    e.update(env or {})
    out = subprocess.run([sys.executable, DESIGN, "--strict", root],
                         capture_output=True, text=True, env=e)
    return "blocked" if out.returncode else "clear"


# 14. The migration gate asserted "with matching row counts" over receipts that
# recorded none: the comparison was skipped when the key was absent and the
# evidence string said it happened anyway.
@case("migration-with-no-row-counts-is-nodata", "migration", "NO-DATA")
def m1(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": "rehearse-991"}})


@case("half-a-row-count-is-caught", "migration", "FAIL")
def m2(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job_1"},
        "row_counts": {"before": 100}})


@case("empty-migration-receipt-is-nodata", "migration", "NO-DATA")
def m3(root):
    write(root, "migration-receipt.json", {})


# A rehearsal id that is a boolean satisfied a bare truthiness test while the
# evidence line called it resolvable.
@case("non-string-rehearsal-id-is-caught", "migration", "FAIL")
def m4(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": True},
        "row_counts": {"before": 100, "after_reverse": 100}})


@case("sound-migration-evidence-counts-what-it-compared", "evidence", "counted")
def m5(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job_8842"},
        "row_counts": {"before": 100, "after_reverse": 100}})
    line = gate_line(root, "migration")
    return "counted" if "1 row-count comparison(s) matched" in line else line


# 15. Valid JSON of the wrong TYPE crashed the tool inside the gate loop, so the
# crashing gate and every gate after it printed no verdict at all and advisory
# mode exited 0. A gate that vanishes is worse than a gate that fails.
@case("wrong-type-manifest-is-caught", "numbers", "FAIL")
def w1(root):
    write(root, "numbers-manifest.json", "[{\"figures\": []}]\n")


@case("wrong-type-ran-receipt-is-caught", "ran", "FAIL")
def w2(root):
    write(root, "ran-receipt.json", "\"a string\"\n")


@case("wrong-type-migration-receipt-is-caught", "migration", "FAIL")
def w3(root):
    write(root, "migration-receipt.json", "42\n")


@case("non-object-figure-entry-is-caught", "numbers", "FAIL")
def w4(root):
    write(root, "numbers-manifest.json", {"figures": ["just a string"]})


@case("a-crashing-check-fails-instead-of-disappearing", "guard", "FAIL")
def w5(root):
    if _checks is None:
        return _CHECKS_IMPORT_ERROR

    def boom(_):
        raise RuntimeError("the receipt reader exploded")
    verdict, ev = _checks.run_guarded("boom", boom, root)
    return verdict if "exploded" in ev else "evidence lost the exception"


# Severity is declared at write time, or the check does not exist: the split
# between a blocking check and a graded one used to live in which FILE a check
# was written into, which no reader could see without tracing the call.
@case("a-check-without-a-declared-severity-is-refused", "guard", "refused")
def w5a(root):
    if _checks is None:
        return _CHECKS_IMPORT_ERROR
    try:
        _checks.Check(lambda _: ("PASS", "x"), reads=("f",), kind="text",
                      full_fixture={"files": {"f": "worked example\n"}})
    except ValueError as e:
        return "refused" if "severity" in str(e) else "refused for the wrong reason: %s" % e
    return "registered with no severity at all"


@case("a-severity-outside-gate-or-soft-is-refused", "guard", "refused")
def w5b(root):
    if _checks is None:
        return _CHECKS_IMPORT_ERROR
    try:
        _checks.Check(lambda _: ("PASS", "x"), reads=("f",), kind="text", severity="advisory",
                      full_fixture={"files": {"f": "worked example\n"}})
    except ValueError as e:
        return "refused" if "severity" in str(e) else "refused for the wrong reason: %s" % e
    return "registered under a severity the exit-code mapping does not define"


@case("a-planted-extra-file-fails-the-install-check", "guard", "planted-file-caught")
def w5d(root):
    # verify-install.sh checks both directions. The one-direction version of
    # this script reports PASSED with a planted file still present, because an
    # added file is neither a MISMATCH nor a MISSING; this fixture plants one
    # and requires exit 1 naming it as EXTRA.
    import shutil
    sdir = os.path.join(root, "scripts")
    os.makedirs(sdir)
    for s in ("checksums.sh", "verify-install.sh"):
        shutil.copy(os.path.join(_REPO, "scripts", s), os.path.join(sdir, s))
    write(root, "tools/ok.py", "def f():\n    return 1\n")
    write(root, "README.md", "a tiny install\n")
    gen = subprocess.run(["sh", os.path.join(sdir, "checksums.sh"), "CHECKSUMS.sha256"],
                         capture_output=True, text=True, cwd=root, timeout=60)
    if gen.returncode != 0:
        return "manifest generation failed: %s" % gen.stderr[:80]
    clean = subprocess.run(["sh", os.path.join(sdir, "verify-install.sh")],
                           capture_output=True, text=True, cwd=root, timeout=60)
    if clean.returncode != 0:
        return "clean tree did not verify: %s" % (clean.stdout + clean.stderr)[:120]
    write(root, "planted.py", "import os\n")
    planted = subprocess.run(["sh", os.path.join(sdir, "verify-install.sh")],
                             capture_output=True, text=True, cwd=root, timeout=60)
    if planted.returncode != 1:
        return "planted file exited %d, not 1" % planted.returncode
    return ("planted-file-caught" if "EXTRA:     planted.py" in planted.stdout
            else "exit 1 without naming the extra file")


@case("every-verdict-line-names-its-severity", "gaterun", "printed")
def w5c(root):
    # The declaration is only visible if the output carries it: a severity a
    # reader can see only in the source is the file-location split with a new name.
    out = subprocess.run([sys.executable, GATE, root], capture_output=True, text=True)
    lines = [l for l in out.stdout.splitlines() if l.startswith("  ")]
    if not lines:
        return "no verdict lines at all"
    missing = [l for l in lines if "[severity: gate]" not in l and "[severity: soft]" not in l]
    return "printed" if not missing else "unlabelled: %s" % missing[0][:60]


# 16. The empty-manifest fix held only while the empty manifest was the ONLY
# one: the note naming it was collected and then discarded unless every manifest
# was empty, so one good deliverable anywhere in the tree restored the old
# behaviour for all the rest. A repository with more than one deliverable is the
# normal case.
GOOD_FIGURE = {"figures": [{
    "label": "gmv", "snapshot_id": "snap_2026_07",
    "query": "SELECT SUM(amount) FROM orders", "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
    "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]}
GOOD_CHECK = {"checks": [{"name": "reconcile", "exit_code": 0, "duration_ms": 812}]}


@case("one-empty-manifest-among-good-ones-is-nodata", "numbers", "NO-DATA")
def p1(root):
    write(root, "a/numbers-manifest.json", GOOD_FIGURE)
    write(root, "b/numbers-manifest.json", {"figures": []})


@case("one-misspelled-manifest-among-good-ones-is-nodata", "numbers", "NO-DATA")
def p2(root):
    write(root, "a/numbers-manifest.json", GOOD_FIGURE)
    write(root, "b/numbers-manifest.json", {"figuers": [{"label": "typo key"}]})


@case("one-empty-ran-receipt-among-good-ones-is-nodata", "ran", "NO-DATA")
def p3(root):
    write(root, "a/ran-receipt.json", GOOD_CHECK)
    write(root, "b/ran-receipt.json", {"checks": []})


@case("two-good-manifests-still-pass", "numbers", "PASS")
def p4(root):
    write(root, "a/numbers-manifest.json", GOOD_FIGURE)
    write(root, "b/numbers-manifest.json", GOOD_FIGURE)


# 17. The approval gate's Reviewed-in path is an unvalidated regex match against
# a commit message the agent writes. The law used to call approval "bound to an
# identity the agent cannot forge". The tool is what it is; the evidence line now
# says so, and this pins that it keeps saying so.
@case("reviewed-in-evidence-does-not-claim-a-resolved-review", "evidence", "disclosed")
def ap1(root):
    write(root, "APPROVAL", "touches partner billing path\n")
    git_init(root)
    open(os.path.join(root, "x"), "w").write("1")
    subprocess.run(["git", "-C", root, "add", "."], check=True)
    subprocess.run(["git", "-C", root, "commit", "-qm", "payout batching\n\nReviewed-in: PR-99999"], check=True)
    line = gate_line(root, "approval")
    return "disclosed" if "does not resolve the id" in line else line


# 18. The one-file-deletion bypass. Seven filled artifacts with the intake
# removed were never opened from the repository root, and --strict exited 0.
@case("dossier-without-its-intake-is-caught", "artifacts", "FAIL")
def x1(root):
    write(root, "01-purpose.md", PURPOSE)
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer: system of record CRM\n")


@case("dossier-without-its-intake-in-a-subdirectory-is-found", "designrun", "blocked")
def x2(root):
    write(root, "design/proj/01-purpose.md", PURPOSE)
    write(root, "design/proj/03-adr.md", "# ADR\n")
    return design_run(root)


@case("an-exempt-dossier-does-not-block-an-unrelated-merge", "designrun", "clear")
def x3(root):
    write(root, "design/legacy/00-intake.json", {"tier": "T2", "answers": T2_ANSWERS, "override": None})
    write(root, "design/legacy/.sbe-exempt",
          "checks: artifacts, adr, datamodel, diagrams, placeholder\n"
          "reason: closed two years ago, kept for history\n")
    return design_run(root)


# 19. A one-character override reason waived the entire dossier requirement.
@case("one-character-override-reason-is-not-an-override", "artifacts", "FAIL")
def o1(root):
    write(root, "00-intake.json", {"tier": "T0", "answers": T3_ANSWERS,
                                   "override": "T0", "override_reason": "x"})


@case("override-reason-that-says-tbd-is-not-an-override", "artifacts", "FAIL")
def o2(root):
    write(root, "00-intake.json", {"tier": "T0", "answers": T3_ANSWERS,
                                   "override": "T0", "override_reason": "  tbd "})


@case("override-field-disagreeing-with-the-tier-is-caught", "artifacts", "FAIL")
def o3(root):
    write(root, "00-intake.json", {"tier": "T1", "answers": T3_ANSWERS, "override": "T2",
                                   "override_reason": "read-only backfill, agreed with the data owner"})
    write(root, "01-purpose.md", PURPOSE)


# The positive path of the tier recompute had no fixture that could fail: with a
# valid reason the written tier is used, which is what the code did before the
# recompute existed too. What the recompute adds is the DISCLOSURE, so that is
# what this pins.
@case("an-honoured-override-names-the-tier-it-was-lowered-from", "evidence", "labelled")
def o4(root):
    write(root, "00-intake.json", {"tier": "T1", "answers": T3_ANSWERS, "override": "T1",
                                   "override_reason": "read-only backfill, agreed with the data owner"})
    write(root, "01-purpose.md", PURPOSE)
    line = gate_line(root, "artifacts")
    return "labelled" if ("lowering the tier to T1 from computed T3" in line
                          and line.split()[1] == "PASS") else line


# 20. `touch 01-purpose.md` cleared tier T1, and the placeholder check passed the
# same empty file because a file with nothing in it carries no marker.
@case("zero-byte-artifact-does-not-clear-a-tier", "artifacts", "FAIL")
def z1(root):
    write(root, "00-intake.json", {"tier": "T1", "answers": T1_ANSWERS, "override": None})
    write(root, "01-purpose.md", "")


@case("zero-byte-artifact-is-not-an-edited-dossier", "placeholder", "FAIL")
def z2(root):
    write(root, "01-purpose.md", "")


# 21. The data model check was wrong in both directions: an honest bullet list
# outside the entity section became entities with no source, and an entity name
# carrying a hyphen or a dot was dropped from the set the PASS line asserted over.
@case("an-honest-notes-list-is-not-a-set-of-entities", "datamodel", "PASS")
def e1(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Customer: system of record: the CRM.\n"
          "## Notes\n- All timestamps are stored in UTC\n- Soft deletes are used everywhere\n"
          "## Relationships\n- Customer to Order: one-to-many\n")


@case("a-hyphenated-entity-with-no-source-is-not-dropped", "datamodel", "FAIL")
def e2(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Subscriber: system of record: the identity service.\n"
          "- payment-token: the stored card token. Nobody knows who owns this.\n"
          "- pii.profile: personal data. Nobody knows who owns this either.\n")


# 22. Requiring every diagram node to be an ENTITY failed the diagrams the
# template asks for at T3, and the published escape was to add services to the
# conceptual data model, which corrupts the model to satisfy a diagram check.
@case("a-declared-runtime-component-is-traceable", "diagrams", "PASS")
def g1(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Order: system of record: the order service.\n")
    write(root, "04-technology-map.md",
          "# Technology map\n| Component | Technology | Owner |\n|---|---|---|\n"
          "| EventBus | Managed queue | Platform team |\n")
    write(root, "06-diagrams.md", "```mermaid\nflowchart LR\n  Order --> EventBus\n```\n")


@case("an-invented-node-is-still-an-orphan-with-components-declared", "diagrams", "FAIL")
def g2(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Order: system of record: the order service.\n")
    write(root, "04-technology-map.md",
          "# Technology map\n| Component | Technology | Owner |\n|---|---|---|\n"
          "| EventBus | Managed queue | Platform team |\n")
    write(root, "06-diagrams.md", "```mermaid\nflowchart LR\n  Order --> LedgerService\n```\n")


# 23. Prose is not a diagram. A markdown bullet after a heading read as an
# erDiagram relationship line and invented a node out of the heading.
@case("prose-outside-a-fence-is-not-a-diagram-node", "diagrams", "PASS")
def g3(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Order: system of record: the order service.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n## Components\n- OrderQueue: described in prose, not a node\n"
          "The order flows to the warehouse.\n```mermaid\nflowchart LR\n  Order --> OrderQueue\n```\n")


# 24. `### Option A (rejected): ...` counted zero, and the convention appeared
# only in the template.
@case("rejected-named-inside-a-heading-counts", "adr", "PASS")
def r1(root):
    write(root, "03-adr.md", "# ADR\n## Criteria\nlatency\n"
                             "### Option A (rejected): synchronous call\nTies checkout to the warehouse.\n"
                             "### Option B (rejected): nightly batch\nFails freshness.\n"
                             "## Decision\nQueue.\n## Consequences\nOne more part.\n"
                             "## What would flip this\nSub-second freshness.\n")


# 25. An artifact that legitimately CITES the marker FAILed with the false
# sentence "still the shipped template, unedited".
@case("an-artifact-citing-the-marker-is-not-unedited", "placeholder", "PASS")
def r2(root):
    write(root, "07-verification.md",
          "# Verification\nOne assertion here is that no dossier file still contains the string "
          "SBE-TEMPLATE-UNFILLED, which is how we know the template was edited.\n")


SCORE_CHECKS = ("ledger-coverage", "schema-2-uniform", "cache-economy", "vault-log-per-active-day",
                "fence-hygiene", "correction-latency", "budget-vs-tier", "prediction-seals",
                "felt-outcome-ratings", "review-cadence", "silent-failure-lints")


def score_check(name, vault, env=None, args=()):
    e = dict(os.environ)
    e.update({"BROTHERSBE_VAULT": vault, "BROTHERSBE_REGISTRIES": "", "SBE_LINT_ROOT": ""})
    e.update(env or {})
    out = subprocess.run([sys.executable, SCORE] + list(args), capture_output=True, text=True, env=e)
    for line in out.stdout.splitlines():
        parts = line.split()
        if parts and parts[0] == name:
            return parts[1]
    return "no-verdict-line"


def _ledger(root, body):
    write(root, "99-System/telemetry/outcomes.jsonl", body)
    return root


# 26. Three checks read `PASS if not <empty list>`, so a fresh checkout printed
# "0 pre-schema-2 lines remain PASS" over a corpus with no rows: the project's
# own law inverted inside the project's own scorer, in its default state.
@case("empty-ledger-is-not-schema-uniformity", "score", "NO-DATA")
def sc1(root):
    return score_check("schema-2-uniform", _ledger(root, ""))


@case("zero-active-days-is-not-a-session-log-pass", "score", "NO-DATA")
def sc2(root):
    return score_check("vault-log-per-active-day", _ledger(root, ""))


@case("zero-corrections-is-not-a-latency-pass", "score", "NO-DATA")
def sc3(root):
    return score_check("correction-latency", root)


@case("a-malformed-ledger-line-is-a-fail", "score", "FAIL")
def sc4(root):
    return score_check("schema-2-uniform", _ledger(root, "{not json\n"))


@case("a-ledger-line-of-the-wrong-type-is-a-fail", "score", "FAIL")
def sc5(root):
    return score_check("ledger-coverage", _ledger(root, "\"a string\"\n"))


@case("a-malformed-ledger-does-not-delete-the-other-checks", "score", "NO-DATA")
def sc6(root):
    # The crashing scorer took every check down with it, including ones reading
    # a different file entirely.
    return score_check("prediction-seals", _ledger(root, "\"a string\"\n"))


# The fence check appended the SKILL'S OWN STATE.md to the registry list on every
# run, so an operator with no registries configured got a green fence-discipline
# line sourced from the author's machine. Reproduced hermetically: the tools under
# test are copied beside a STATE.md carrying a tier-tagged fence line, which is
# exactly the layout that produced the phantom PASS.
@case("budget-vs-tier-does-not-score-the-skills-own-registry", "score", "NO-DATA")
def sc7(root):
    import shutil
    shutil.copytree(os.path.dirname(os.path.abspath(SCORE)), os.path.join(root, "tools"))
    write(root, "STATE.md",
          "# State\n## Fences\n- agent: builder | tier T2 | objective: ship the thing\n")
    e = dict(os.environ)
    e.update({"BROTHERSBE_VAULT": os.path.join(root, "vault"),
              "BROTHERSBE_REGISTRIES": "", "SBE_LINT_ROOT": ""})
    out = subprocess.run([sys.executable, os.path.join(root, "tools", "sbe_score.py")],
                         capture_output=True, text=True, env=e)
    for line in out.stdout.splitlines():
        parts = line.split()
        if parts and parts[0] == "budget-vs-tier":
            return parts[1]
    return "no-verdict-line"


@case("an-all-exempted-scan-is-not-clean", "score", "NO-DATA")
def sc8(root):
    src = os.path.join(root, "src")
    write(root, "src/swallowy.py",
          "def a():\n    try:\n        f()\n    except Exception:\n        pass  # sbe: allow-silent lint fixture, never executed\n")
    return score_check("silent-failure-lints", root, args=(src,))


@case("an-exemption-on-the-pass-line-is-honoured", "score", "PASS")
def sc9(root):
    src = os.path.join(root, "src")
    write(root, "src/swallowy.py",
          "def a():\n    try:\n        f()\n    except Exception:\n        pass  # sbe: allow-silent lint fixture, never executed\n")
    write(root, "src/clean.py", "def b():\n    return 1\n")
    return score_check("silent-failure-lints", root, args=(src,))


# ---------------------------------------------------------------------------
# Third wave. One defect, one more shape of it. The first two waves modelled
# absent evidence as an absent FILE; every fixture below is a receipt that
# EXISTS, parses, carries every required key, and holds nothing in one of them.
# The rest are the mirror image: correct work that the gates were rejecting,
# because a gate that rejects correct work gets switched off, and a gate that is
# off catches less than a gate that is merely incomplete.
# ---------------------------------------------------------------------------

@case("blank-rerun-values-are-not-a-zero-drift-check", "numbers", "FAIL")
def v1(root):
    # `is None` was the only emptiness test, so two empty strings compared equal
    # and the evidence reported a re-derivation that compared nothing.
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "revenue", "snapshot_id": "snap-1", "query": "select 1",
        "second_derivation": "select 2", "rerun": {"ran": True, "primary": "", "secondary": ""}}]})


@case("whitespace-rerun-values-are-not-a-zero-drift-check", "numbers", "FAIL")
def v2(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "revenue", "snapshot_id": "snap-1", "query": "select 1",
        "second_derivation": "select 2", "rerun": {"ran": True, "primary": " ", "secondary": " "}}]})


@case("a-whitespace-snapshot-id-is-not-a-pinned-read", "numbers", "FAIL")
def v3(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "revenue", "snapshot_id": "  ", "query": "select 1",
        "second_derivation": "select 2", "rerun": {"ran": True, "primary": 5, "secondary": 5}}]})


def _one_figure(root, query, second):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": "snap-2026-07-25", "query": query,
        "second_derivation": second, "rerun": {"ran": True, "primary": 5, "secondary": 5}}]})


@case("a-trailing-semicolon-does-not-make-a-second-derivation", "numbers", "FAIL")
def v4a(root):
    # Copying the query into the second field and adding a semicolon bought
    # "1 figure(s) each with a pinned, independently re-derived, zero-drift check",
    # the strongest sentence this tool prints. It is the lazy thing, not the
    # dishonest thing, which is exactly why the gate must not reward it.
    _one_figure(root, "SELECT SUM(amount) FROM orders", "SELECT SUM(amount) FROM orders;")


@case("a-trailing-comment-does-not-make-a-second-derivation", "numbers", "FAIL")
def v4b(root):
    _one_figure(root, "SELECT SUM(amount) FROM orders",
                "SELECT SUM(amount) FROM orders -- rerun 2026-07-25")


@case("a-block-comment-and-a-reindent-do-not-make-a-second-derivation", "numbers", "FAIL")
def v4c(root):
    _one_figure(root, "SELECT SUM(amount) FROM orders",
                "/* second pass */ select  sum(amount)\n  from orders")


@case("a-genuinely-different-second-derivation-still-passes", "numbers", "PASS")
def v4d(root):
    # The control. Normalising more text before comparing must not start failing
    # the honest case it exists to protect.
    _one_figure(root, "SELECT SUM(amount) FROM orders",
                "SELECT SUM(qty * price) FROM order_lines")


@case("a-figure-listed-twice-is-counted-once", "gaterun", "1 figure(s)")
def v4e(root):
    # "2 figure(s) each ..." over one object listed twice: the count in the
    # evidence line is what a reader takes as the amount of work checked.
    fig = {"label": "gmv", "snapshot_id": "snap-1", "query": "SELECT SUM(a) FROM t",
           "second_derivation": "SELECT SUM(b) FROM u",
           "rerun": {"ran": True, "primary": 5, "secondary": 5}}
    write(root, "numbers-manifest.json", {"figures": [fig, dict(fig)]})
    out = subprocess.run([sys.executable, GATE, "numbers", root], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if line.strip().startswith("numbers"):
            return " ".join(line.split("PASS")[-1].split()[:2]) if "PASS" in line else "not-a-pass"
    return "no-line"


@case("a-figure-with-no-label-is-caught", "numbers", "FAIL")
def v4(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "", "snapshot_id": "snap-1", "query": "select 1",
        "second_derivation": "select 2", "rerun": {"ran": True, "primary": 5, "secondary": 5}}]})


@case("a-whitespace-rerun-flag-is-not-a-rerun", "numbers", "FAIL")
def v5(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "revenue", "snapshot_id": "snap-1", "query": "select 1",
        "second_derivation": "select 2", "rerun": {"ran": " ", "primary": 5, "secondary": 5}}]})


@case("a-whitespace-second-derivation-is-not-independent", "numbers", "FAIL")
def v6(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "revenue", "snapshot_id": "snap-1", "query": "select 1",
        "second_derivation": "   ", "rerun": {"ran": True, "primary": 5, "secondary": 5}}]})


@case("blank-row-counts-are-not-a-matched-comparison", "migration", "FAIL")
def v7(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job-1"},
        "row_counts": {"before": "", "after_reverse": ""}})


@case("a-whitespace-rehearsal-id-is-not-a-run-id", "migration", "FAIL")
def v8(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": " "},
        "row_counts": {"before": 100, "after_reverse": 100}})


@case("a-whitespace-restore-claim-is-not-a-restore", "migration", "FAIL")
def v9(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": " "},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job-1"},
        "row_counts": {"before": 100, "after_reverse": 100}})


@case("a-recorded-check-with-no-name-is-caught", "ran", "FAIL")
def v10(root):
    write(root, "ran-receipt.json", {"checks": [{"name": " ", "exit_code": 0, "duration_ms": 812}]})


@case("booleans-are-not-an-exit-code-and-a-duration", "ran", "FAIL")
def v11(root):
    # {"exit_code": false} satisfied `!= 0` and {"duration_ms": true} satisfied a
    # truthiness test, so this passed as "a zero exit and a nonzero duration".
    write(root, "ran-receipt.json", {"checks": [
        {"name": "recon", "exit_code": False, "duration_ms": True}]})


@case("an-intake-with-blank-answers-is-nodata", "artifacts", "NO-DATA")
def v12(root):
    write(root, "00-intake.json", {"tier": "T0", "answers": {k: "" for k, _ in _intake.QUESTIONS},
                                   "override": None})


@case("a-tier-that-requires-nothing-reports-nothing", "artifacts", "NO-DATA")
def v13(root):
    # "tier T0: every required artifact present" read exactly like a verified T3
    # line while nothing had been opened at all.
    write(root, "00-intake.json", {"tier": "T0", "answers": {
        "changes_contract": False, "crosses_boundary": False, "reversible_under_hour": True,
        "touches_sensitive": False, "consumers": "none"}, "override": None})


@case("an-intake-answering-no-in-words-does-not-collapse-a-t3-to-a-t0", "artifacts", "FAIL")
def v13b(root):
    # The whole of C1 in one file. Four honest booleans, one honest answer written
    # as the word the prompt asks for, and the tier field agreeing with what the
    # truthiness rule computed from it: tier T0, no artifact owed, every design
    # check NO-DATA, --strict --strict-waivers exit 0. The re-derivation whose job
    # is to catch a hand-edited tier agreed, because it made the same mistake.
    write(root, "00-intake.json", {"tier": "T0", "answers": {
        "changes_contract": False, "crosses_boundary": False,
        "reversible_under_hour": "no", "touches_sensitive": False,
        "consumers": "none"}, "override": None, "override_reason": None})


@case("an-intake-whose-consumers-value-nothing-recognizes-fails", "artifacts", "FAIL")
def v13c(root):
    write(root, "00-intake.json", {"tier": "T0", "answers": {
        "changes_contract": False, "crosses_boundary": False,
        "reversible_under_hour": True, "touches_sensitive": False,
        "consumers": "several"}, "override": None, "override_reason": None})


@case("an-honest-intake-written-entirely-in-y-n-still-passes", "artifacts", "PASS")
def v13d(root):
    # The other half of the same fix, and the half that decides whether the gate
    # survives contact with a team: an intake in the vocabulary the tool's own
    # prompt teaches, honest in every answer, must pass rather than be argued with.
    write(root, "00-intake.json", {"tier": "T1", "answers": {
        "changes_contract": "n", "crosses_boundary": "Y",
        "reversible_under_hour": "yes", "touches_sensitive": "no",
        "consumers": "None"}, "override": None, "override_reason": None})
    write(root, "01-purpose.md", PURPOSE)


@case("an-artifact-of-headings-only-does-not-clear-a-tier", "artifacts", "FAIL")
def v14(root):
    write(root, "00-intake.json", {"tier": "T1", "answers": T1_ANSWERS, "override": None})
    write(root, "01-purpose.md", "# Purpose\n\n## Problem\n\n## Users\n")


@case("an-empty-criteria-heading-is-not-criteria", "adr", "FAIL")
def v15(root):
    write(root, "03-adr.md", "# ADR\n## Criteria\n## Rejected alternatives\n"
                             "- Synchronous call: ties checkout to the ledger.\n"
                             "- Nightly batch: misses the freshness requirement.\n"
                             "## Decision\nQueue.\n## Consequences\nOne more part.\n"
                             "## What would flip this\nSub-second freshness.\n")


@case("a-one-letter-rejection-reason-is-not-a-reason", "adr", "FAIL")
def v16(root):
    write(root, "03-adr.md", "# ADR\n## Criteria\nlatency\n## Rejected alternatives\n- a\n- b\n"
                             "## Decision\nQueue.\n## Consequences\nOne more part.\n"
                             "## What would flip this\nSub-second freshness.\n")


@case("no-relationships-under-the-heading-is-nodata", "datamodel", "NO-DATA")
def v17(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer: system of record CRM\n"
                                    "## Relationships\n")


@case("a-relationship-table-with-no-cardinality-is-caught", "datamodel", "FAIL")
def v18(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Customer: system of record CRM\n- Order: system of record OMS\n"
          "## Relationships\n| From | To | Cardinality |\n|---|---|---|\n| Customer | Order | not decided |\n")


@case("a-relationship-table-with-cardinality-passes", "datamodel", "PASS")
def v19(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Customer: system of record CRM\n- Order: system of record OMS\n"
          "## Relationships\n| From | To | Cardinality |\n|---|---|---|\n| Customer | Order | one-to-many |\n")


@case("labelled-mermaid-nodes-are-traced-by-their-label", "diagrams", "PASS")
def v20(root):
    # A[Customer] --> B[Order] is the single most common Mermaid idiom there is,
    # and it FAILed as two orphans named A and B.
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer: system of record CRM\n"
                                    "- Order: system of record OMS\n")
    write(root, "06-diagrams.md", "```mermaid\nflowchart LR\n  A[Customer] --> B[Order]\n```\n")


@case("a-labelled-node-naming-nothing-is-still-an-orphan", "diagrams", "FAIL")
def v21(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer: system of record CRM\n")
    write(root, "06-diagrams.md", "```mermaid\nflowchart LR\n  A[Customer] --> B[Invoice]\n```\n")


@case("a-sequence-diagram-is-a-diagram", "diagrams", "PASS")
def v22(root):
    # The shipped template tells a T2 author that this file wants a sequence
    # diagram, and the shipped check called one "a diagram artifact with no
    # diagram in it".
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer: system of record CRM\n"
                                    "- Order: system of record OMS\n")
    write(root, "06-diagrams.md",
          "```mermaid\nsequenceDiagram\n  participant Customer\n  participant Order\n"
          "  Customer->>Order: places\n  Order->>Customer: confirms\n```\n")


@case("a-sequence-diagram-participant-can-still-be-an-orphan", "diagrams", "FAIL")
def v23(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer: system of record CRM\n")
    write(root, "06-diagrams.md",
          "```mermaid\nsequenceDiagram\n  participant Customer\n  participant Warehouse\n"
          "  Customer->>Warehouse: places\n```\n")


@case("a-node-named-after-a-direction-keyword-is-not-dropped", "diagrams", "FAIL")
def v24(root):
    # Five nodes went in, one came out, and the verdict said "all traceable".
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Order: system of record OMS\n")
    write(root, "06-diagrams.md",
          "```mermaid\nflowchart LR\n  Order --> TD\n  TD --> LR\n  LR --> BT\n  BT --> graph\n```\n")


@case("the-diagram-evidence-names-what-it-skipped", "evidence", "named")
def v25(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer: system of record CRM\n"
                                    "- Order: system of record OMS\n")
    write(root, "06-diagrams.md", "```mermaid\nflowchart LR\n  A[Customer] --> B[Order]\n```\n")
    line = gate_line(root, "diagrams")
    return "named" if ("flowchart LR" in line and "tokens read as diagram syntax" in line
                       and line.split()[1] == "PASS") else line


@case("a-gantt-chart-is-not-a-missing-diagram", "diagrams", "NO-DATA")
def v26(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Order: system of record OMS\n")
    write(root, "06-diagrams.md",
          "```mermaid\ngantt\n  title Rollout\n  section Phase 1\n  Migrate :a1, 2026-07-01, 30d\n```\n")


@case("an-er-diagram-still-passes", "diagrams", "PASS")
def v27(root):
    write(root, "05-data-model.md", "# Data model\n## Entities\n- CUSTOMER: system of record CRM\n"
                                    "- ORDER: system of record OMS\n")
    write(root, "06-diagrams.md", "```mermaid\nerDiagram\n  CUSTOMER ||--o{ ORDER : places\n```\n")


@case("a-zero-byte-exemption-does-not-waive-a-failing-dossier", "designrun", "blocked")
def v28(root):
    # `: > .sbe-exempt` turned two failing checks into exit 0, and the report
    # said ".sbe-exempt names why: no reason recorded".
    write(root, "design/proj/00-intake.json", {"tier": "T3", "answers": T3_ANSWERS, "override": None})
    write(root, "design/proj/01-purpose.md", PURPOSE)
    write(root, "design/proj/.sbe-exempt", "")
    return design_run(root)


@case("a-thin-exemption-reason-does-not-waive-a-dossier", "designrun", "blocked")
def v29(root):
    write(root, "design/proj/00-intake.json", {"tier": "T3", "answers": T3_ANSWERS, "override": None})
    write(root, "design/proj/01-purpose.md", PURPOSE)
    write(root, "design/proj/.sbe-exempt", "tbd\n")
    return design_run(root)


EXEMPTION = ("checks: artifacts, adr, datamodel, diagrams, placeholder\n"
             "reason: closed two years ago, kept for history\n")


@case("an-exemption-is-reported-as-a-waiver-not-a-pass", "designrun", "waived")
def v30(root):
    write(root, "design/legacy/00-intake.json", {"tier": "T2", "answers": T2_ANSWERS, "override": None})
    write(root, "design/legacy/.sbe-exempt", EXEMPTION)
    e = dict(os.environ)
    e["SBE_DOSSIER_ROOT"] = ""
    out = subprocess.run([sys.executable, DESIGN, root], capture_output=True, text=True, env=e)
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "dossier" and parts[2] == "WAIVED":
            named = all(c in line for c in DESIGN_CLASSES)
            return "waived" if named else "waiver-line-does-not-name-the-checks"
    return "no-waiver-line"


# An exemption that names no checks waives everything by default, which is an off
# switch rather than an exemption. Measured before this: three words of filler in
# a free-text file switched off all five design checks for a directory and
# --strict exited 0 with a T3 dossier missing six of seven artifacts.
@case("an-exemption-that-names-no-checks-does-not-waive", "designrun", "blocked")
def v30a(root):
    write(root, "design/proj/00-intake.json", {"tier": "T3", "answers": T3_ANSWERS, "override": None})
    write(root, "design/proj/01-purpose.md", PURPOSE)
    write(root, "design/proj/.sbe-exempt",
          "this dossier was closed two years ago and is kept only for history\n")
    return design_run(root)


# An exemption scoped to one check leaves the other four running, so an author
# waiving `diagrams` on an archived dossier no longer also waives `artifacts`.
@case("a-scoped-exemption-waives-only-the-checks-it-names", "designrun", "blocked")
def v30b(root):
    write(root, "design/proj/00-intake.json", {"tier": "T3", "answers": T3_ANSWERS, "override": None})
    write(root, "design/proj/01-purpose.md", PURPOSE)
    write(root, "design/proj/.sbe-exempt",
          "checks: diagrams\nreason: the diagrams moved to the architecture wiki in 2024\n")
    return design_run(root)


@case("an-exemption-naming-a-check-that-does-not-exist-does-not-waive", "designrun", "blocked")
def v30c(root):
    write(root, "design/proj/00-intake.json", {"tier": "T3", "answers": T3_ANSWERS, "override": None})
    write(root, "design/proj/01-purpose.md", PURPOSE)
    write(root, "design/proj/.sbe-exempt",
          "checks: everything\nreason: this dossier was archived when the team disbanded\n")
    return design_run(root)


# A waiver is not a pass, and CI must be able to act on it without reading prose.
@case("a-waiver-blocks-under-strict-waivers", "designrun", "blocked")
def v30d(root):
    write(root, "design/legacy/00-intake.json", {"tier": "T2", "answers": T2_ANSWERS, "override": None})
    write(root, "design/legacy/.sbe-exempt", EXEMPTION)
    e = dict(os.environ)
    e["SBE_DOSSIER_ROOT"] = ""
    out = subprocess.run([sys.executable, DESIGN, "--strict", "--strict-waivers", root],
                         capture_output=True, text=True, env=e)
    return "blocked" if out.returncode else "clear"


@case("asking-for-a-table-family-by-name-names-the-tables-that-ship", "guard", "named")
def v30g(root):
    # L12 promises that asking for a table that does not exist names the tables
    # that do. `sbe_decide.py architecture`, which is how the sentence reads,
    # treated the argument as a file path and named no tables at all.
    out = subprocess.run([sys.executable, os.path.join(_REPO, "tools", "sbe_decide.py"),
                          "architecture"], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if out.returncode == 0:
        return "exit 0 for a table family that has no table"
    return "named" if "Tables that ship: shape" in out.stdout else out.stdout.strip()[:80]


@case("the-meta-test-lint-sees-a-verdict-in-a-subpackage-and-in-a-lookup-table", "guard", "caught")
def v30f(root):
    """The honesty meta-test's own discovery, probed rather than read.

    Three holes, all proved by building the shadow check the file exists to
    forbid. Its walk was `os.listdir`, one level deep, so a registry in
    `tools/quality/extra.py` was invisible to the registry walk AND to the source
    lint while the summary line printed "20 checks discovered ... 0 failure(s)"
    over twenty-one. And the lint resolved a constant and a name but not a `BinOp`
    or a `Subscript`, so `"PA" + "SS"` and a `{"ok": "PASS"}` lookup returned the
    verdict from a function it never saw. A coverage count that reads complete is
    what makes each of those silent.
    """
    meta = SourceFileLoader("meta_probe", os.path.join(HERE, "test_no_data_class.py")).load_module()
    tools = os.path.join(root, "tools")
    os.makedirs(os.path.join(tools, "quality"))
    write(tools, "quality/extra.py",
          "def gate_shadow(root):\n"
          "    return \"PASS\", \"quality is fine (examined nothing at all)\"\n\n"
          "def gate_shadow_concat(root):\n"
          "    return \"PA\" + \"SS\", \"examined nothing\"\n\n"
          "_V = {\"ok\": \"PASS\"}\n\n"
          "def gate_shadow_dict(root):\n"
          "    return _V[\"ok\"], \"examined nothing\"\n")
    original = meta.TOOLS_DIR
    try:
        meta.TOOLS_DIR = tools
        found = {name for _fn, name, _why in meta.pass_returning_functions()}
        walked = set(meta.tool_sources())
    finally:
        meta.TOOLS_DIR = original
    want = {"gate_shadow", "gate_shadow_concat", "gate_shadow_dict"}
    if os.path.join("quality", "extra.py") not in walked:
        return "the walk never reached a module one directory down: %s" % sorted(walked)
    missing = sorted(want - found)
    return "caught" if not missing else "the lint did not see %s" % ", ".join(missing)


def _waiver_grep_pattern():
    """The pattern the shipped CI actually uses to decide a waiver happened.

    Read out of the workflow rather than restated here, so this eval is a check on
    the file that ships and not on a copy of it that agrees with itself.
    """
    import re as _re
    wf = open(os.path.join(_REPO, ".github/workflows/brothersbe-gates.yml"), errors="replace").read()
    m = _re.search(r"if grep -q(\w*) '([^']+)' design-checks\.out", wf)
    return (m.group(1), m.group(2)) if m else (None, None)


def _design_output(root, args=()):
    e = dict(os.environ)
    e["SBE_DOSSIER_ROOT"] = ""
    return subprocess.run([sys.executable, DESIGN] + list(args) + [root],
                          capture_output=True, text=True, env=e).stdout


@case("the-ci-waiver-annotation-does-not-fire-on-a-run-with-no-waiver", "guard", "differs")
def v30e(root):
    """The CI step must behave differently on a waived run and a clean one.

    It did not. `grep -q 'WAIVED'` matched the banner sbe_design.py prints on every
    single run ("WAIVED is not a pass either"), so every clean run annotated the
    job summary with "a .sbe-exempt waived one or more design checks. Nothing
    opened a file for them" over a run in which every check opened its files. An
    always-on assurance signal carries no information; this one asserted something
    false, and it is the only control that makes WAIVED visible in CI at all,
    since the exit code deliberately cannot.

    The pattern under test is read out of the shipped workflow, and the two
    outputs are produced by running the real tool, so this cannot pass by
    agreeing with itself.
    """
    import re as _re
    flags, pattern = _waiver_grep_pattern()
    if pattern is None:
        return "the workflow no longer greps design-checks.out for a waiver at all"
    rx = _re.compile(pattern, 0 if "E" in (flags or "") else 0)
    clean_dir = os.path.join(root, "clean")
    waived_dir = os.path.join(root, "waived")
    for d, exempt in ((clean_dir, None), (waived_dir, EXEMPTION)):
        write(d, "design/proj/00-intake.json", {"tier": "T1", "answers": T1_ANSWERS, "override": None})
        write(d, "design/proj/01-purpose.md", PURPOSE)
        if exempt:
            write(d, "design/proj/.sbe-exempt", exempt)
    clean_hits = [l for l in _design_output(clean_dir).splitlines() if rx.search(l)]
    waived_hits = [l for l in _design_output(waived_dir).splitlines() if rx.search(l)]
    if clean_hits:
        return "the CI pattern %r fires on a run with no waiver: %r" % (pattern, clean_hits[0][:80])
    if not waived_hits:
        return "the CI pattern %r does not fire on a run that waived five checks" % pattern
    return "differs"


@case("a-blank-session-id-is-a-broken-ledger-row", "score", "FAIL")
def v31(root):
    return score_check("schema-2-uniform", _ledger(root, json.dumps({"schema": 2, "session_id": " "}) + "\n"))


@case("an-unreadable-ledger-row-does-not-delete-the-other-checks", "score", "NO-DATA")
def v32(root):
    # One well-formed JSON line whose session_id is an object raised inside the
    # shared context, OUTSIDE the per-check guard: eleven verdict lines became
    # one error line and advisory mode exited 0.
    body = json.dumps({"schema": 2, "session_id": {"a": 1}, "ts": "2026-07-25T10:00:00Z"}) + "\n"
    return score_check("prediction-seals", _ledger(root, body))


@case("an-unreadable-ledger-row-fails-the-checks-that-read-it", "score", "FAIL")
def v33(root):
    body = json.dumps({"schema": 2, "session_id": {"a": 1}, "ts": "2026-07-25T10:00:00Z"}) + "\n"
    return score_check("ledger-coverage", _ledger(root, body))


@case("an-undated-correction-is-not-a-fresh-one", "score", "FAIL")
def v34(root):
    write(root, "99-System/telemetry/corrections.jsonl", json.dumps({"text": "x"}) + "\n")
    return score_check("correction-latency", root)


@case("a-zero-byte-session-log-is-not-a-session-log", "score", "FAIL")
def v35(root):
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc)
    _ledger(root, json.dumps({"session_id": "s1", "ts": now.isoformat().replace("+00:00", "Z")}) + "\n")
    write(root, "10-Projects/demo/Sessions/%s-session.md" % now.date().isoformat(), "")
    return score_check("vault-log-per-active-day", root)


@case("a-scan-of-empty-source-files-is-not-clean", "score", "NO-DATA")
def v36(root):
    src = os.path.join(root, "src")
    write(root, "src/empty.py", "")
    return score_check("silent-failure-lints", root, args=(src,))


@case("cache-counters-that-are-not-counts-are-caught", "score", "FAIL")
def v37(root):
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")
    return score_check("cache-economy", _ledger(root, json.dumps(
        {"session_id": "s1", "ts": now, "cache_read": "", "cache_write": ""}) + "\n"))


# The honest path, at every tier. A gate is only worth having if correct work
# clears it, so a complete dossier is a fixture too, and it uses the ordinary
# authoring idioms rather than the ones that happen to suit the parser.
# The complete-dossier fixtures use a purpose written about the system the rest of
# the dossier designs. PURPOSE above is a SHAPE fixture ("Problem: x, Users: y")
# and is deliberately about nothing, which is now a FAIL in its own right: an
# artifact that names nothing any sibling artifact names is filler.
DOSSIER_PURPOSE = ("# Purpose\nProblem: refunds settle late and the support desk cannot say why.\n"
                   "Users: the support desk and the finance close.\n"
                   "Success: every refund reaches a terminal state within one business day.\n"
                   "Non-goals: repricing, partial refunds.\n"
                   "If wrong: a customer waits and nobody can see where the refund stopped.\n")
DOSSIER = {
    "01-purpose.md": DOSSIER_PURPOSE,
    "02-process.md": "# Process\nThe refund is requested, approved, and settled.\n"
                     "Each step names its owner and its failure path.\n",
    "03-adr.md": "# ADR\n## Criteria\nsettlement latency, operational load\n"
                 "## Rejected alternatives\n"
                 "- Synchronous call to the ledger: ties checkout to ledger availability.\n"
                 "- Nightly batch: misses the one business day requirement.\n"
                 "## Decision\nPublish refund events to a queue.\n"
                 "## Consequences\nOne more moving part to operate.\n"
                 "## What would flip this\nSub-second settlement becoming a requirement.\n",
    "04-technology-map.md": "# Technology map\n| Component | Technology | Owner |\n|---|---|---|\n"
                            "| RefundQueue | Managed queue | Platform team |\n",
    "05-data-model.md": "# Data model\n## Entities\n- Customer: system of record: the CRM.\n"
                        "- Refund: system of record: the ledger service.\n"
                        "## Relationships\n- Customer to Refund: one-to-many, optional.\n",
    "06-diagrams.md": "# Diagrams\n## Context\n```mermaid\nflowchart LR\n"
                      "  C[Customer] --> R[Refund]\n```\n"
                      "## Sequence\n```mermaid\nsequenceDiagram\n  participant Customer\n"
                      "  participant Refund\n  Customer->>Refund: requests\n```\n",
    "07-verification.md": "# Verification\nA reconciliation query compares refunds settled against\n"
                          "refunds requested, and it runs in CI.\n",
}
TIER_ANSWERS = {"T0": {"changes_contract": False, "crosses_boundary": False,
                       "reversible_under_hour": True, "touches_sensitive": False,
                       "consumers": "none"},
                "T1": T1_ANSWERS, "T2": T2_ANSWERS, "T3": T3_ANSWERS}


def _complete_dossier(root, tier):
    write(root, "design/refunds/00-intake.json",
          {"tier": tier, "answers": TIER_ANSWERS[tier], "override": None})
    for n in _intake.required_artifacts(tier):
        name = {"01": "01-purpose.md", "02": "02-process.md", "03": "03-adr.md",
                "04": "04-technology-map.md", "05": "05-data-model.md",
                "06": "06-diagrams.md", "07": "07-verification.md"}[n]
        write(root, "design/refunds/" + name, DOSSIER[name])
    return design_run(root)


@case("a-complete-t0-dossier-blocks-nothing", "designrun", "clear")
def h0(root):
    return _complete_dossier(root, "T0")


@case("a-complete-t1-dossier-blocks-nothing", "designrun", "clear")
def h1(root):
    return _complete_dossier(root, "T1")


@case("a-complete-t2-dossier-blocks-nothing", "designrun", "clear")
def h2(root):
    return _complete_dossier(root, "T2")


@case("a-complete-t3-dossier-blocks-nothing", "designrun", "clear")
def h3(root):
    return _complete_dossier(root, "T3")


@case("a-change-with-no-numbers-and-no-migration-blocks-nothing", "gaterun", "clear")
def h4(root):
    git_init(root)
    open(os.path.join(root, "x"), "w").write("1")
    subprocess.run(["git", "-C", root, "add", "."], check=True)
    subprocess.run(["git", "-C", root, "commit", "-qm", "internal refactor"], check=True)
    out = subprocess.run([sys.executable, GATE, "--strict", root], capture_output=True, text=True)
    return "blocked" if out.returncode else "clear"


# ---------------------------------------------------------------------------
# Round four of one defect: the value is PRESENT, NON-EMPTY, and vacuous.
#
# Measured against the tree that shipped it: a manifest with snapshot_id "TODO"
# and rerun.primary = rerun.secondary = "pending" produced "numbers PASS 1
# figure(s) each with a pinned, independently re-derived, zero-drift check" and
# --strict exit 0, and the other three hard gates fell to "unknown", "TODO" and
# "-" in the same run. Every clause of those four evidence lines was false. The
# fix is one shared predicate (sbe_checks.VACUOUS_VALUES and answered()), and the
# mechanical closure is the vacuous-token sweep in evals/test_no_data_class.py;
# these fixtures pin the named cases the review reproduced by hand.
# ---------------------------------------------------------------------------

@case("a-placeholder-snapshot-id-is-not-a-pinned-read", "numbers", "FAIL")
def w1(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "Q3 revenue", "snapshot_id": "TODO",
        "query": "SELECT SUM(amount) FROM orders",
        "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
        "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]})


@case("two-pending-values-are-not-zero-drift", "numbers", "FAIL")
def w2(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "Q3 revenue", "snapshot_id": "snap-2026-07",
        "query": "SELECT SUM(amount) FROM orders",
        "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
        "rerun": {"ran": True, "primary": "pending", "secondary": "pending"}}]})


@case("a-second-derivation-differing-only-in-case-is-not-independent", "numbers", "FAIL")
def w3(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": "snap-2026-07",
        "query": "SELECT SUM(amount) FROM orders",
        "second_derivation": "select sum(amount) from orders",
        "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]})


@case("a-second-derivation-differing-only-in-whitespace-is-not-independent", "numbers", "FAIL")
def w4(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": "snap-2026-07",
        "query": "SELECT SUM(amount) FROM orders",
        "second_derivation": "SELECT  SUM(amount)\n  FROM orders",
        "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]})


@case("rerun-ran-as-the-string-false-is-not-a-re-run", "numbers", "FAIL")
def w5(root):
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": "snap-2026-07",
        "query": "SELECT SUM(amount) FROM orders",
        "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
        "rerun": {"ran": "false", "primary": 17570, "secondary": 17570}}]})


@case("a-figure-value-recorded-as-a-numeric-string-still-passes", "numbers", "PASS")
def w6(root):
    # The type check must not reject an honest receipt exported from a
    # spreadsheet: a count written as "17,570" is a count.
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": "snap-2026-07",
        "query": "SELECT SUM(amount) FROM orders",
        "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
        "rerun": {"ran": True, "primary": "17,570", "secondary": "17570"}}]})


@case("row-counts-of-unknown-are-not-a-matched-comparison", "migration", "FAIL")
def w7(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job-8842"},
        "row_counts": {"before": "unknown", "after_reverse": "unknown"}})


@case("a-placeholder-rehearsal-id-is-not-a-rehearsal-id", "migration", "FAIL")
def w8(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": "TODO"},
        "row_counts": {"before": 100, "after_reverse": 100}})


@case("a-placeholder-check-name-does-not-say-what-ran", "ran", "FAIL")
def w9(root):
    write(root, "ran-receipt.json", {"checks": [{"name": "TODO", "exit_code": 0,
                                                 "duration_ms": 1}]})


@case("a-hyphen-is-not-a-review-id", "approval", "FAIL")
def w10(root):
    write(root, "APPROVAL", "touches the partner payout path\n")
    git_init(root)
    open(os.path.join(root, "x"), "w").write("1")
    subprocess.run(["git", "-C", root, "add", "."], check=True)
    subprocess.run(["git", "-C", root, "commit", "-qm", "payout batching\n\nReviewed-in: -"],
                   check=True)


# I4, adjudicated: an unverifiable signature already reports NO-DATA on the
# grounds that this host cannot check it. A Reviewed-in id is in the identical
# state, so it gets the identical verdict. While it was a PASS, the strongest
# sentence this gate could print about a money-movement change cost one hyphen.
@case("an-unresolved-review-id-is-nodata-not-a-pass", "approval", "NO-DATA")
def w11(root):
    write(root, "APPROVAL", "touches the partner payout path\n")
    git_init(root)
    open(os.path.join(root, "x"), "w").write("1")
    subprocess.run(["git", "-C", root, "add", "."], check=True)
    subprocess.run(["git", "-C", root, "commit", "-qm", "payout batching\n\nReviewed-in: PR-482"],
                   check=True)


@case("a-tbd-system-of-record-and-a-todo-snapshot-are-refused-by-one-list", "evidence", "one-list")
def w12(root):
    # The structural point, pinned: sbe_design.py refused "todo" as a system of
    # record while sbe_gate.py accepted "TODO" as a pinned snapshot, because the
    # list was a private constant in one file that the other never imported.
    sys.path.insert(0, os.path.join(HERE, "..", "tools"))
    import sbe_checks, sbe_design, sbe_gate
    shared = sbe_checks.VACUOUS_VALUES
    for mod in (sbe_design, sbe_gate):
        if any(isinstance(v, (tuple, list, set, frozenset)) and "todo" in {str(x).lower() for x in v}
               and v is not shared for k, v in vars(mod).items() if k.isupper()):
            return "%s carries its own vacuity list" % mod.__name__
    return "one-list" if sbe_design._stated_value("TODO") == "" and \
        sbe_checks.answered("TODO") is None else "predicates disagree"


# ---------------------------------------------------------------------------
# Honest work that used to be blocked. A gate that rejects correct work gets
# switched off by its users, which destroys the system more surely than a hole
# does, so each of these is a fixture in its own right.
# ---------------------------------------------------------------------------

@case("a-soft-wrapped-entity-bullet-keeps-its-system-of-record", "datamodel", "PASS")
def y1(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "- RefundEvent: one refund action against an order, as recorded by the\n"
          "  ledger; system of record: the ledger service.\n"
          "- Customer: system of record: the CRM.\n"
          "## Relationships\n- Customer to RefundEvent: one-to-many, optional.\n")


@case("a-soft-wrapped-relationship-keeps-its-cardinality", "datamodel", "PASS")
def y2(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Customer: system of record: the CRM.\n"
          "- Refund: system of record: the ledger service.\n"
          "## Relationships\n"
          "- Customer to Refund, where a refund is always raised against an order\n"
          "  that the customer placed: one-to-many, optional.\n")


@case("an-adr-written-in-prose-headings-passes", "adr", "PASS")
def y3(root):
    write(root, "03-adr.md",
          "# How we are settling refunds\n"
          "## What we weighed\nSettlement latency, operational load, auditability.\n"
          "## Roads not taken\n"
          "- A synchronous call to the ledger: ties checkout latency to ledger availability.\n"
          "- Nightly batch reconciliation: misses the one business day requirement.\n"
          "## What we are doing\nPublish refund events to a queue and settle asynchronously.\n"
          "## What this costs us\nOne more moving part to operate, and an ordering guarantee.\n"
          "## When we would revisit this\nSub-second settlement becoming a requirement.\n")


_ADR_REST = ("## Criteria\nSettlement latency, operational load, auditability.\n"
             "## Decision\nPublish refund events to a queue and settle asynchronously.\n"
             "## Consequences\nOne more moving part to operate.\n"
             "## What would flip this\nSub-second settlement becoming a requirement.\n")


@case("an-adr-whose-alternatives-are-prose-paragraphs-passes", "adr", "PASS")
def y3a(root):
    # Three of the four ordinary ways to write this FAILed, with a message that
    # named none of the accepted forms and described an empty heading that was not
    # there. A gate that rejects correct work is argued with and then switched off.
    write(root, "03-adr.md",
          "# ADR\n## Rejected alternatives\n"
          "We considered a synchronous call to the ledger. We rejected it because it ties "
          "checkout latency to ledger availability.\n\n"
          "We considered nightly batch reconciliation. It misses the one business day "
          "requirement.\n" + _ADR_REST)


@case("an-adr-whose-alternatives-are-a-numbered-list-passes", "adr", "PASS")
def y3b(root):
    write(root, "03-adr.md",
          "# ADR\n## Rejected alternatives\n"
          "1. Synchronous call to the ledger: ties checkout latency to ledger availability.\n"
          "2. Nightly batch reconciliation: misses the one business day requirement.\n" + _ADR_REST)


@case("an-adr-with-one-sub-heading-per-alternative-passes", "adr", "PASS")
def y3c(root):
    write(root, "03-adr.md",
          "# ADR\n## Rejected alternatives\n"
          "### Synchronous call to the ledger\nTies checkout latency to ledger availability.\n"
          "### Nightly batch reconciliation\nMisses the one business day requirement.\n" + _ADR_REST)


@case("one-alternative-in-any-form-is-still-not-two", "adr", "FAIL")
def y3d(root):
    # The control. Accepting more forms must not accept fewer alternatives, and
    # sub-headings must count once each rather than once per paragraph.
    write(root, "03-adr.md",
          "# ADR\n## Rejected alternatives\n"
          "### Synchronous call to the ledger\nTies checkout latency to ledger availability.\n\n"
          "It also doubles the blast radius of a ledger outage.\n" + _ADR_REST)


@case("an-empty-sub-heading-is-still-not-an-alternative", "adr", "FAIL")
def y3e(root):
    write(root, "03-adr.md",
          "# ADR\n## Rejected alternatives\n### Synchronous call\n### Nightly batch\n" + _ADR_REST)


@case("a-data-model-written-as-tables-throughout-passes", "datamodel", "PASS")
def y3f(root):
    # Relationships were readable as a table and entities were not, so a data model
    # written as tables FAILed with "no entity bullets found" over a document
    # naming every entity and every system of record.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "| Entity | System of record | Notes |\n| --- | --- | --- |\n"
          "| Customer | system of record: the CRM | core |\n"
          "| Refund | system of record: the ledger service | derived |\n"
          "## Relationships\n| From | To | Cardinality |\n| --- | --- | --- |\n"
          "| Customer | Refund | one-to-many |\n")


@case("an-entity-table-row-with-no-system-of-record-still-fails", "datamodel", "FAIL")
def y3g(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "| Entity | System of record |\n| --- | --- |\n"
          "| Customer | system of record: the CRM |\n"
          "| Refund | to be decided |\n"
          "## Relationships\n- Customer to Refund: one-to-many.\n")


@case("an-entity-lifecycle-state-diagram-with-declared-states-passes", "diagrams", "PASS")
def y4(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Order: system of record: the OMS.\n"
          "## Order states\n- Draft\n- Placed\n- Shipped\n"
          "## Relationships\n- Order to Order: one-to-one, self.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n## Order lifecycle\n```mermaid\nstateDiagram-v2\n"
          "  [*] --> Draft\n  Draft --> Placed\n  Placed --> Shipped\n  Shipped --> [*]\n```\n")


@case("an-undeclared-lifecycle-state-is-nodata-not-a-false-failure", "diagrams", "NO-DATA")
def y5(root):
    # Before: FAIL, "diagram element(s) appear nowhere else in the dossier:
    # Draft, Placed, Shipped", with no document anywhere telling an author how to
    # make a state diagram trace. The only way through was to declare the states
    # as runtime COMPONENTS, which is the model-corrupting pathology L5 removed
    # for queues, reproduced one diagram type over.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Order: system of record: the OMS.\n"
          "## Relationships\n- Order to Order: one-to-one, self.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n## Order lifecycle\n```mermaid\nstateDiagram-v2\n"
          "  [*] --> Draft\n  Draft --> Placed\n  Placed --> Shipped\n  Shipped --> [*]\n```\n")


@case("an-invented-flowchart-node-still-fails-beside-a-state-diagram", "diagrams", "FAIL")
def y6(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Order: system of record: the OMS.\n"
          "## Order states\n- Draft\n- Placed\n"
          "## Relationships\n- Order to Order: one-to-one, self.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nstateDiagram-v2\n  [*] --> Draft\n  Draft --> Placed\n```\n"
          "## Context\n```mermaid\nflowchart LR\n  X[MysteryBox] --> Y[GhostQueue]\n```\n")


# The counts printed in the shipped docs, checked against the suites that print
# them. Three docs carried "70 evals: 70 passed" through a wave that took the
# real number to 110, and the doc whose whole job is "prove it works in 60
# seconds" was one of them. A number in a doc that nothing recomputes is a stale
# evidence string with a longer half-life.
SHIPPED_DOCS = ("README.md", "docs/SETUP.md", "docs/HOW-IT-WORKS.md", "PUBLISH-CHECKLIST.md",
                "docs/guides/01-quickstart.md", "docs/guides/02-the-gates-in-practice.md",
                # This entry read "03-the-dossier.md" for a wave, a file that does
                # not exist, and both guards `continue` past a path they cannot
                # open, so the whole guide was silently exempt from them. A list
                # of documents to check is itself evidence, and a name in it that
                # opens nothing is the absent-file defect in a tuple.
                "docs/guides/03-work-doctrines.md", "docs/guides/04-teams-and-evolution.md",
                "docs/guides/05-a-worked-engagement.md", "evals/README.md", "DIGEST.md",
                "LAWS-REFERENCE.md",
                "INVARIANTS.md",
                # STATE.md was named here and is excluded by .gitignore, so it is in
                # nobody's clone. The guard below caught it as an absent file, and
                # only in a fresh clone: on the author's machine the untracked file
                # was present, the suite was green, and CI was red on arrival. The
                # shippable artifact is the template, so the template is what ships.
                "SKILL.md", "PARITY.md", "PRACTICES.md", "RUBRIC.md", "STATE.template.md")
_REPO = os.path.abspath(os.path.join(HERE, ".."))


@case("every-eval-case-invariants-md-cites-is-a-case-the-suite-defines", "docs", "consistent")
def dc_inv(root):
    # INVARIANTS.md names the asserting test for each promise, on the argument
    # that "a promise nothing asserts is a wish with a serial number". The
    # citation IS the promise's evidence, and it was asserted by nobody: a
    # rename in the suite left the register pointing at a case that no longer
    # exists, silently. This parses every backticked hyphenated token in
    # INVARIANTS.md and fails on one that is not a defined eval case, so the
    # register's own citations degrade loudly the way the counts already do.
    import re as _re
    body = open(os.path.join(_REPO, "INVARIANTS.md"), errors="replace").read()
    names = {name for name, _k, _e, _fn in CASES}
    # A citation-shaped token: backticked, hyphenated, all lowercase words, no
    # slash (a path) and no space. The reinjection table cites case names in
    # this exact shape; a plain-English hyphenated word (there are none today)
    # would have to also be a real case name to pass, which is the point.
    cited = {t for t in _re.findall(r"`([a-z][a-z0-9-]{6,})`", body) if "-" in t}
    unknown = sorted(c for c in cited if c not in names)
    if not cited:
        return "INVARIANTS.md cites no eval case at all, so this guard proved nothing"
    return "consistent" if not unknown else (
        "INVARIANTS.md cites %d case(s) the suite does not define: %s"
        % (len(unknown), ", ".join(unknown[:4])))


@case("no-shipped-doc-prints-an-eval-count-the-suite-does-not-produce", "docs", "consistent")
def dc1(root):
    import re as _re
    wrong = []
    for rel in SHIPPED_DOCS:
        p = os.path.join(_REPO, rel)
        if not os.path.isfile(p):
            continue
        body = open(p, errors="replace").read()
        for m in _re.finditer(r"(\d+) evals: (\d+) passed, (\d+) regressions", body):
            if (int(m.group(1)), int(m.group(2)), int(m.group(3))) != (len(CASES), len(CASES), 0):
                wrong.append("%s: %r but the suite has %d cases" % (rel, m.group(0), len(CASES)))
        for m in _re.finditer(r'ending "(\d+) passed, (\d+) regressions', body):
            if (int(m.group(1)), int(m.group(2))) != (len(CASES), 0):
                wrong.append("%s: %r but the suite has %d cases" % (rel, m.group(0), len(CASES)))
    return "consistent" if not wrong else "; ".join(wrong[:4])


@case("no-shipped-doc-prints-a-meta-test-count-the-meta-test-does-not-produce", "docs", "consistent")
def dc2(root):
    import re as _re
    meta = SourceFileLoader("test_no_data_class",
                            os.path.join(HERE, "test_no_data_class.py")).load_module()
    checks, regs, scen, waived = meta.counts()
    wrong = []
    for rel in SHIPPED_DOCS:
        p = os.path.join(_REPO, rel)
        if not os.path.isfile(p):
            continue
        for m in _re.finditer(r"(\d+) checks discovered from (\d+) registries in (\d+) module\(s\), "
                              r"(\d+) scenarios run(?:, (\d+) waived by declared exemption)?",
                              open(p, errors="replace").read()):
            got = (int(m.group(1)), int(m.group(2)), int(m.group(4)))
            if got != (checks, regs, scen) or (m.group(5) is not None
                                               and int(m.group(5)) != waived):
                wrong.append("%s: %r but the meta-test walks %d checks, %d registries, %d "
                             "scenarios, %d waived"
                             % (rel, m.group(0), checks, regs, scen, waived))
    return "consistent" if not wrong else "; ".join(wrong[:4])


@case("every-shipped-doc-path-in-this-suite-opens-a-file", "docs", "consistent")
def dc0(root):
    missing = [rel for rel in SHIPPED_DOCS if not os.path.isfile(os.path.join(_REPO, rel))]
    return "consistent" if not missing else "SHIPPED_DOCS names %s, which opens nothing" % missing


@case("every-shipped-doc-path-in-this-suite-is-actually-shipped", "docs", "consistent")
def dc6(root):
    """A path this suite depends on has to exist in the reader's copy, not only here.

    `STATE.md` was in SHIPPED_DOCS and in `.gitignore` at the same time. It is
    therefore in no clone of this repository, so the guard above FAILed for every
    reader and passed for the one machine that happened to hold the untracked
    file: the shipped CI was red on its first pull request, on a step unrelated to
    the change, with an error naming a file the reader cannot find. Opening a file
    is not evidence that the file ships. This asks the two questions that are, and
    a path that answers neither is named here rather than discovered by a stranger.
    """
    problems = []
    tracked = None
    try:
        out = subprocess.run(["git", "-C", _REPO, "ls-files", "-z", "--"] + list(SHIPPED_DOCS),
                             capture_output=True, text=True)
        if out.returncode == 0:
            tracked = set(p for p in out.stdout.split("\0") if p)
    except OSError:
        # Not swallowed: `tracked` stays None and the .gitignore reading below is
        # what runs, and the absence of git is reported in the evidence.
        tracked = None
    if tracked is not None:
        problems += ["%s is not tracked by git, so it is in nobody's clone" % rel
                     for rel in SHIPPED_DOCS if rel not in tracked]
    # The .gitignore reading runs either way, because a source tarball has no git
    # and a guard that can only run in a working repository is the same blindness
    # one layer out. Plain patterns only: a name, or a name anchored to the root.
    ignore = os.path.join(_REPO, ".gitignore")
    patterns = []
    if os.path.isfile(ignore):
        for line in open(ignore, errors="replace").read().splitlines():
            s = line.strip()
            if s and not s.startswith(("#", "!")):
                patterns.append(s.strip("/"))
    elif tracked is None:
        return ("neither git nor a .gitignore is readable here, so whether these paths ship "
                "could not be checked at all; this is reported rather than passed over")
    for rel in SHIPPED_DOCS:
        for pat in patterns:
            if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(os.path.basename(rel), pat):
                problems.append("%s is excluded by .gitignore rule %r, so it is in nobody's clone"
                                % (rel, pat))
    return "consistent" if not problems else "; ".join(sorted(set(problems))[:4])


@case("every-quoted-verdict-line-in-the-docs-carries-its-declared-severity", "docs", "consistent")
def dc7(root):
    """The doc-quote guard for verdict lines. A formatting change landed in the
    tools (the severity suffix) and 45 quoted verdict lines across five docs
    kept the old shape, silently: the class was unguarded because nothing
    mechanical connected a pasted verdict line to the tool that prints it.
    This sweeps every shipped doc for lines shaped like a check verdict
    (a registered check name followed by PASS/FAIL/NO-DATA) and requires each
    to end with the severity suffix the registry declares for that check, so
    the next formatting change fails here instead of going stale on the page.
    Byte-exactness of whole engagements is the replay harness's job (dc9);
    this pins the shape and the severity of every quoted line everywhere."""
    import re as _re
    _score = SourceFileLoader("sbe_score_docquote",
                              os.path.join(_REPO, "tools", "sbe_score.py")).load_module()
    severities = {}
    for reg in (_gate.GATES, _design_mod.CHECKS, _score.CHECKS):
        for name, check in reg.items():
            severities[name] = check.severity
    names = "|".join(sorted(severities))
    line_re = _re.compile(r"^\s*(%s)\s+(PASS|FAIL|NO-DATA)\b.*$" % names)
    wrong = []
    for rel in SHIPPED_DOCS:
        p = os.path.join(_REPO, rel)
        if not os.path.isfile(p):
            continue
        for n, line in enumerate(open(p, errors="replace").read().splitlines(), 1):
            m = line_re.match(line)
            if not m:
                continue
            if "so this check opened no file" in line:
                # The design tool's no-dossier reporter prints these fallback
                # lines itself, without a severity suffix, because no check
                # produced a verdict; the load-bearing phrase is the same one
                # the meta-test keys on. A quote of one is correct as printed.
                continue
            want = "[severity: %s]" % severities[m.group(1)]
            if not line.rstrip().endswith(want):
                wrong.append("%s:%d quotes a %s verdict line without its %s suffix"
                             % (rel, n, m.group(1), want))
    return "consistent" if not wrong else "; ".join(wrong[:6])


@case("guide-01s-verbatim-workflow-fence-is-the-shipped-workflow", "docs", "consistent")
def dc8(root):
    # The one doc that promises the FULL file "verbatim" handed out a copy
    # without the hardening the workflow's own header calls the control
    # everything else rests on (no SHA pinning, no read-only permissions, no
    # seeded meta-test), and a prior sync claim about this fence was false.
    # Byte comparison, so "verbatim" means verbatim.
    guide = open(os.path.join(_REPO, "docs/guides/01-quickstart.md"), errors="replace").read()
    wf = open(os.path.join(_REPO, ".github/workflows/brothersbe-gates.yml"),
              errors="replace").read()
    marker = "The workflow, verbatim:"
    if marker not in guide:
        return "guide 01 no longer carries the verbatim marker"
    i = guide.index(marker)
    try:
        start = guide.index("```yaml\n", i) + len("```yaml\n")
        end = guide.index("\n```", start)
    except ValueError:
        return "no yaml fence follows the verbatim marker"
    return "consistent" if guide[start:end + 1] == wf else \
        "the fence under 'verbatim' differs from the shipped workflow"


@case("guide-05s-output-blocks-are-what-the-tools-print", "docs", "consistent")
def dc9(root):
    # The guide's opening claim, made mechanical: evals/replay_guide05.py
    # writes every artifact block byte for byte, runs every command block, and
    # diffs each captured output against the block the guide shows. A stale
    # quote fails the gate instead of going stale on the page; a maintainer
    # repairs it with `python3 evals/replay_guide05.py --write`, which pastes
    # the LIVE output, so nobody ever hand-types an expected block.
    out = subprocess.run([sys.executable, os.path.join(HERE, "replay_guide05.py")],
                         capture_output=True, text=True, timeout=310)
    tail = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else "(no output)"
    if out.returncode == 0 and tail.endswith(", 0 differ"):
        return "consistent"
    return tail


@case("no-copy-ready-ci-block-shows-fewer-steps-than-the-shipped-workflow", "docs", "consistent")
def dc3(root):
    # A reader who copies a CI fence gets what the fence shows. Three docs showed
    # three steps while the workflow ran six, and the three they omitted were the
    # regression evals, the honesty meta-test and the tool tests: exactly the
    # suites whose absence from the merge path this project had just finished
    # fixing. A prose count and a fence are both claims about a file that ships.
    import re as _re
    wf = open(os.path.join(_REPO, ".github/workflows/brothersbe-gates.yml"),
              errors="replace").read()
    real = _re.findall(r"^      - name: (.+)$", wf, _re.M)
    wrong = []
    for rel in SHIPPED_DOCS:
        p = os.path.join(_REPO, rel)
        if not os.path.isfile(p):
            continue
        body = open(p, errors="replace").read()
        for m in _re.finditer(r"(?sm)^```yaml\n(.*?)^```$", body):
            block = m.group(1)
            if "sbe_gate.py --strict" not in block:
                continue
            shown = _re.findall(r"^\s*- name: (.+)$", block, _re.M)
            missing = [n for n in real if n not in shown]
            if missing:
                wrong.append("%s: a copy-ready CI block omits %d of the %d shipped steps (%s)"
                             % (rel, len(missing), len(real), "; ".join(missing[:3])))
    return "consistent" if not wrong else "; ".join(wrong[:3])


@case("no-copy-ready-ci-block-runs-the-meta-test-weaker-than-the-workflow", "docs", "consistent")
def dc_seed(root):
    # A reader assembling CI from a doc fragment gets what the fragment shows.
    # Three docs showed the meta-test step as one unseeded command while the
    # shipped workflow runs it twice (the fixed sweep, then the seeded random
    # composition --seed 1 --seed 2 --seed 3), so the assemble-the-steps path
    # silently installed weaker coverage than the copy-the-file path. The
    # workflow's own seeded invocation is the bar; any doc CI block that runs
    # the meta-test at all must run it too, or it degrades in silence.
    import re as _re
    wf = open(os.path.join(_REPO, ".github/workflows/brothersbe-gates.yml"),
              errors="replace").read()
    if "--seed" not in wf:
        return "the shipped workflow no longer runs the seeded meta-test, so this guard is stale"
    wrong = []
    for rel in SHIPPED_DOCS:
        p = os.path.join(_REPO, rel)
        if not os.path.isfile(p):
            continue
        body = open(p, errors="replace").read()
        for m in _re.finditer(r"(?sm)^```yaml\n(.*?)^```$", body):
            block = m.group(1)
            if "test_no_data_class.py" not in block:
                continue
            if "--seed" not in block:
                wrong.append("%s: a CI block runs the meta-test without the seeded pass the "
                             "shipped workflow runs" % rel)
    return "consistent" if not wrong else "; ".join(sorted(set(wrong))[:3])


_CHECK_LINE = None


def _checker_line_re():
    """The pasted-output line shape: two spaces, a check name, a verdict, evidence."""
    global _CHECK_LINE
    import re as _re
    if _CHECK_LINE is None:
        names = set()
        for mod, attr in (("sbe_gate.py", "GATES"), ("sbe_design.py", "CHECKS"),
                          ("sbe_score.py", "CHECKS")):
            m = SourceFileLoader(mod[:-3] + "_names", os.path.join(_REPO, "tools", mod)).load_module()
            names |= set(getattr(m, attr))
        names |= {"dossier"}          # printed by sbe_design.py's own reporter
        _CHECK_LINE = _re.compile(r"^  (>> )?(%s)\s+(PASS|FAIL|NO-DATA|WAIVED)\s+(\S.*)$"
                                  % "|".join(_re.escape(n) for n in sorted(names, key=len, reverse=True)))
    return _CHECK_LINE


def _evidence_templates():
    """Every sentence the three checkers can print, from their own source.

    The docs paste tool output verbatim, and tool output is built from `%`
    templates that are string constants in the source. Reading them out with ast
    is what lets a guard named for ALL checker lines cover all of them: a pasted
    line whose sentence no template can produce is a line the tool does not
    produce today. Candidates shorter than this in literal text are dropped,
    because a template that is mostly `%s` would match anything and a guard that
    matches anything is the defect this file exists to catch.
    """
    import ast as _ast, re as _re
    out = []
    for mod in ("sbe_gate.py", "sbe_design.py", "sbe_score.py", "sbe_checks.py"):
        tree = _ast.parse(open(os.path.join(_REPO, "tools", mod), errors="replace").read())
        for node in _ast.walk(tree):
            if not (isinstance(node, _ast.Constant) and isinstance(node.value, str)):
                continue
            for piece in [node.value] + node.value.split("; "):
                text = " ".join(piece.split())
                literal = _re.sub(r"%[-\d.]*[sdrf%]", "", text)
                if len(literal.strip()) < 16:
                    continue
                pattern = _re.escape(text)
                pattern = _re.sub(r"%[-\\\d.]*[sdrf]", ".*?", pattern).replace("%%", "%")
                out.append(_re.compile(pattern))
    return out


@case("no-shipped-doc-prints-a-checker-line-the-checker-does-not-produce", "docs", "consistent")
def dc7(root):
    """Every pasted checker line in every shipped doc, against what the tools can print.

    The guard that carried this name recomputed ONE line, from one of the twenty
    checks, by filtering `if not line.startswith("silent-failure-lints")`. It
    printed `consistent` and was counted among the suite as evidence for a claim
    about all shipped docs and all checker lines, while forty-six of the
    forty-seven pasted lines went unread and three of them were stale. A guard
    whose name asserts a property it implements over one case is this project's
    own defect class at the guard layer.

    Exact recomputation is only possible for a line the suite can reproduce (the
    lint line, in the case below). For the rest, the sentence a checker prints is
    built from `%` templates that live in its source, so a line no template can
    produce is a line the tool cannot print. That is checkable over all of them.
    """
    import re as _re
    line_re, templates = _checker_line_re(), _evidence_templates()
    wrong, seen = [], 0
    for rel in SHIPPED_DOCS:
        p = os.path.join(_REPO, rel)
        if not os.path.isfile(p):
            continue
        body = open(p, errors="replace").read()
        quoted = [("inline quote", " ".join(q.split()))
                  for q in _re.findall(r"`(?:PASS|FAIL|NO-DATA|WAIVED)\s\s+([^`]+)`", body)]
        for raw in body.splitlines():
            m = line_re.match(raw.rstrip())
            if not m:
                continue
            seen += 1
            evidence = " ".join(m.group(4).split())
            # The severity suffix is appended by each tool's main(), outside
            # every evidence template, so it is stripped before template
            # matching; that the suffix is present and correct on quoted lines
            # is its own guard above.
            evidence = _re.sub(r"\s*\[severity: (?:gate|soft)\]$", "", evidence)
            for fragment in [evidence] + evidence.split("; "):
                if any(rx.fullmatch(fragment) for rx in templates):
                    break
            else:
                wrong.append("%s: %r is not a sentence %s can print today"
                             % (rel, evidence[:70], m.group(2)))
        # A checker sentence quoted inline, without its check name, is the same
        # claim in a smaller font: guide 04 quoted `FAIL  gmv_q3: no snapshot_id
        # (a live warehouse drifts; pin the read)`, and the sentence the tool
        # prints today ends "A placeholder is not a pin", which is the clause this
        # whole fix range exists to be able to print.
        for _kind, evidence in quoted:
            seen += 1
            for fragment in [evidence] + evidence.split("; "):
                if any(rx.fullmatch(fragment) for rx in templates):
                    break
            else:
                wrong.append("%s: the inline quote %r is not a sentence any checker prints today"
                             % (rel, evidence[:70]))
    if not seen:
        return "this guard found no checker line at all in any shipped doc, so it proved nothing"
    return "consistent" if not wrong else "%d of %d pasted line(s) stale: %s" % (
        len(wrong), seen, "; ".join(wrong[:3]))


@case("no-shipped-doc-prints-a-silent-failure-lint-line-the-scorer-does-not-produce",
      "docs", "consistent")
def dc4(root):
    # The lint line pasted in guide 02 names the exempted lines BY NUMBER, and
    # those numbers move whenever anything above them moves: one of them was a
    # wave stale and pointed at an unrelated statement. Recomputed here rather
    # than re-audited by eye every wave.
    import re as _re
    out = subprocess.run([sys.executable, SCORE, os.path.join(_REPO, "tools")],
                         capture_output=True, text=True, cwd=_REPO)
    live = [l for l in out.stdout.splitlines() if l.startswith("silent-failure-lints")]
    if not live:
        return "the scorer printed no silent-failure-lints line at all"
    live = _re.sub(r"\s+", " ", live[0]).replace(os.path.join(_REPO, "tools"), "tools/")
    wrong = []
    for rel in SHIPPED_DOCS:
        p = os.path.join(_REPO, rel)
        if not os.path.isfile(p):
            continue
        for line in open(p, errors="replace").read().splitlines():
            if not line.startswith("silent-failure-lints"):
                continue
            if _re.sub(r"\s+", " ", line) != live:
                wrong.append("%s pastes a lint line the tool does not produce today" % rel)
    return "consistent" if not wrong else "; ".join(wrong[:3])


@case("no-shipped-doc-prints-a-check-count-the-scorer-does-not-produce", "docs", "consistent")
def dc5(root):
    import re as _re
    scorer = SourceFileLoader("sbe_score_count",
                              os.path.join(_REPO, "tools", "sbe_score.py")).load_module()
    n = len(scorer.CHECKS)
    words = {8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen"}
    wrong = []
    for rel in SHIPPED_DOCS:
        p = os.path.join(_REPO, rel)
        if not os.path.isfile(p):
            continue
        body = open(p, errors="replace").read()
        # Scoped to the phrasings that are ABOUT the scorer's registry. "Nine
        # checks green: five design, four gates" counts something else and is
        # not this eval's business.
        for m in _re.finditer(r"(\w+) mechanical checks\b|one of (\w+) check lines\b", body):
            word = (m.group(1) or m.group(2)).lower()
            if word in words.values() and word != words.get(n):
                wrong.append("%s: %r but sbe_score.py registers %d checks" % (rel, m.group(0), n))
            if word.isdigit() and int(word) in words and int(word) != n:
                wrong.append("%s: %r but sbe_score.py registers %d checks" % (rel, m.group(0), n))
    return "consistent" if not wrong else "; ".join(wrong[:4])


# ---------------------------------------------------------------------------
# Round six. Two classes, one structural and one social.
#
# STRUCTURAL: every test in this project ran BEFORE its normalization instead of
# after, so every normalization could manufacture a fresh non-answer that nothing
# rechecked. `second_derivation: "#"` is not blank, is not a vacuity token,
# survives answered(), and folds to the empty string, and the gate then printed
# "a second derivation whose text differs beyond case, whitespace and comments,
# re-run to zero drift" over a derivation that computes nothing, with both
# figures the string "inf". Reduce first, test second: sbe_checks.answered_as.
#
# SOCIAL: the checks were rejecting honest work. `## Options considered` failed
# while `## Alternatives considered` passed; MADR, the most widely used ADR
# template there is, failed outright; `source of truth` failed with the sentence
# "has no system of record" about a line naming one; `1:N` was "no cardinality";
# and `pending`, the first state of every payment system in existence, was
# refused as a placeholder because one shared vacuity list was being applied to
# domain content as well as to evidence fields. A gate that rejects correct work
# gets switched off, and a gate that is off catches nothing at all. Each row
# below is one of those forms, as a fixture.
# ---------------------------------------------------------------------------

_GOOD_FIG = {"label": "gmv", "snapshot_id": "snap-2026-07",
             "query": "SELECT SUM(amount) FROM orders",
             "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
             "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}


def _fig(root, **over):
    fig = json.loads(json.dumps(_GOOD_FIG))
    for k, v in over.items():
        if k == "rerun":
            fig["rerun"].update(v)
        else:
            fig[k] = v
    write(root, "numbers-manifest.json", {"figures": [fig]})


@case("a-second-derivation-that-is-only-a-comment-is-not-a-derivation", "numbers", "FAIL")
def r6a(root):
    # The reproduction, one character long. `#` is not blank, is not in
    # VACUOUS_VALUES, and derivation_fold turns it into "".
    _fig(root, second_derivation="#")


@case("a-second-derivation-that-is-a-comment-with-words-in-it-is-not-a-derivation",
      "numbers", "FAIL")
def r6b(root):
    _fig(root, second_derivation="-- rerun on 2026-07-26 by hand, same query")


@case("a-primary-derivation-that-is-only-a-comment-is-not-a-derivation", "numbers", "FAIL")
def r6c(root):
    # The same hole in the other direction: the FIRST derivation could be a
    # comment too, and then the second one "differed" from nothing.
    _fig(root, query="-- see the dashboard")


@case("an-infinite-figure-is-not-a-zero-drift-measurement", "numbers", "FAIL")
def r6d(root):
    # float() accepts "inf", "Infinity" and "1e400", so two infinities compared
    # equal and bought the strongest sentence this project prints.
    _fig(root, rerun={"primary": "inf", "secondary": "inf"})


@case("a-not-a-number-figure-is-not-a-measurement", "numbers", "FAIL")
def r6e(root):
    _fig(root, rerun={"primary": "nan", "secondary": "nan"})


@case("a-negative-row-count-is-not-a-row-count", "migration", "FAIL")
def r6f(root):
    # -1 == -1, so "1 row-count comparison(s) matched" was printed about a pair
    # of counts no table has ever had.
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job-8842"},
        "row_counts": {"before": -1, "after_reverse": -1}})


@case("an-infinite-row-count-is-not-a-row-count", "migration", "FAIL")
def r6g(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job-8842"},
        "row_counts": {"before": "inf", "after_reverse": "inf"}})


@case("a-fractional-row-count-is-not-a-row-count", "migration", "FAIL")
def r6h(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job-8842"},
        "row_counts": {"before": 2.5, "after_reverse": 2.5}})


@case("a-zero-row-count-is-still-a-count", "migration", "PASS")
def r6i(root):
    # The control. A migration over an empty table counted zero rows and counted
    # them, and rejecting that would be rejecting honest work.
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job-8842"},
        "row_counts": {"before": 0, "after_reverse": 0}})


@case("self-approval-is-not-approval", "sig", "FAIL")
def r6j(root):
    # One person, one key: they authored the commit, signed it, and wrote their
    # own name into the Approved-by trailer. The gate compared nothing and
    # printed "signed commit carries Approved-by: Dana Author" over it.
    return _approval_with_sig(root, "G", approver="Dana Author <dana@example.com>",
                              authors=("Dana Author", "dana@example.com"))


@case("self-approval-by-email-alone-is-not-approval", "sig", "FAIL")
def r6k(root):
    return _approval_with_sig(root, "G", approver="dana@example.com",
                              authors=("Dana Author", "dana@example.com"))


@case("a-second-party-approval-still-passes", "sig", "PASS")
def r6l(root):
    # The control for the two above: the whole point is a SECOND party, so one
    # must still pass or the gate is unusable.
    return _approval_with_sig(root, "G", approver="Sam Reviewer <sam@example.com>",
                              authors=("Dana Author", "dana@example.com"))


# --- the honest forms an engineer writes -----------------------------------

_ADR_BODY = ("- Synchronous call to the ledger: ties checkout latency to ledger availability.\n"
             "- Nightly batch reconciliation: misses the one business day requirement.\n")


def _adr(root, rejected_heading, criteria="## Criteria\nsettlement latency, operational load\n",
         body=None):
    write(root, "03-adr.md",
          "# ADR\n" + criteria + rejected_heading + "\n" + (body if body is not None else _ADR_BODY)
          + "## Decision\nPublish refund events to a queue and settle asynchronously.\n"
            "## Consequences\nOne more moving part to operate.\n"
            "## What would flip this\nSub-second settlement becoming a requirement.\n")


@case("adr-heading-options-considered-passes", "adr", "PASS")
def r6m(root):
    _adr(root, "## Options considered")


@case("adr-heading-considered-options-madr-passes", "adr", "PASS")
def r6n(root):
    # The MADR template's own heading. A canonical MADR document failed outright,
    # and the message listed four accepted FORMS and no accepted WORDS.
    _adr(root, "## Considered options")


@case("adr-heading-alternatives-bare-passes", "adr", "PASS")
def r6o(root):
    _adr(root, "## Alternatives")


@case("adr-heading-other-options-passes", "adr", "PASS")
def r6p(root):
    _adr(root, "## Other options")


@case("adr-subheading-not-chosen-passes", "adr", "PASS")
def r6q(root):
    _adr(root, "## Alternatives",
         body="### Not chosen: synchronous ledger call\nTies checkout latency to the ledger.\n"
              "### Not chosen: nightly batch\nMisses the one business day requirement.\n")


@case("adr-subheading-we-did-not-pick-passes", "adr", "PASS")
def r6r(root):
    _adr(root, "## Alternatives",
         body="### We did not pick a synchronous ledger call\nIt ties checkout to the ledger.\n"
              "### We did not pick nightly batch\nIt misses the one business day requirement.\n")


@case("adr-criteria-heading-deciding-factors-passes", "adr", "PASS")
def r6s(root):
    _adr(root, "## Rejected alternatives",
         criteria="## Deciding factors\nsettlement latency, operational load\n")


@case("the-same-rejected-alternative-twice-is-one-alternative", "adr", "FAIL")
def r6t(root):
    # gate_numbers learned that a figure listed twice is one figure; this
    # threshold did not, so a copy-paste cleared "an ADR needs at least 2".
    _adr(root, "## Rejected alternatives",
         body="- Nightly batch reconciliation: misses the one business day requirement.\n"
              "- Nightly batch reconciliation: misses the one business day requirement.\n")


def _model(root, entities, relationships="## Relationships\n- Customer to Order: one-to-many.\n"):
    write(root, "05-data-model.md", "# Data model\n## Entities\n" + entities + relationships)


@case("datamodel-source-of-truth-passes", "datamodel", "PASS")
def r6u(root):
    _model(root, "- Customer: source of truth: the CRM.\n- Order: source of truth: the OMS.\n")


@case("datamodel-owner-passes", "datamodel", "PASS")
def r6v(root):
    _model(root, "- Customer: owner: the CRM.\n- Order: owner: the OMS.\n")


@case("datamodel-sor-abbreviation-passes", "datamodel", "PASS")
def r6w(root):
    _model(root, "- Customer: SoR: the CRM.\n- Order: SoR: the OMS.\n")


@case("datamodel-mastered-by-passes", "datamodel", "PASS")
def r6x(root):
    _model(root, "- Customer: mastered by the CRM.\n- Order: authoritative source: the OMS.\n")


@case("datamodel-table-with-a-system-of-record-column-passes", "datamodel", "PASS")
def r6y(root):
    # The column says what the cell is. Requiring every cell to restate its own
    # column header made five entities into five identical FAILs, and the eval
    # that certified "or as table rows" was written in a shape no author uses.
    _model(root,
           "| Entity | System of record | Notes |\n| --- | --- | --- |\n"
           "| Customer | the CRM | core |\n| Order | the OMS | core |\n")


@case("datamodel-a-still-nameless-owner-in-a-table-column-fails", "datamodel", "FAIL")
def r6z(root):
    # The control: reading the column must not turn an empty cell into an answer.
    _model(root,
           "| Entity | System of record | Notes |\n| --- | --- | --- |\n"
           "| Customer | TBD | core |\n| Order | the OMS | core |\n")


def _cardinality_case(root, token):
    _model(root, "- Customer: system of record: the CRM.\n- Order: system of record: the OMS.\n",
           "## Relationships\n- Customer to Order: %s.\n" % token)


@case("datamodel-cardinality-1-to-N-passes", "datamodel", "PASS")
def r6aa(root):
    _cardinality_case(root, "1:N")


@case("datamodel-cardinality-N-to-1-passes", "datamodel", "PASS")
def r6ab(root):
    _cardinality_case(root, "N:1")


@case("datamodel-cardinality-uml-multiplicity-passes", "datamodel", "PASS")
def r6ac(root):
    _cardinality_case(root, "1..*")


@case("datamodel-cardinality-1-to-many-hyphenated-passes", "datamodel", "PASS")
def r6ad(root):
    _cardinality_case(root, "1-to-many")


@case("datamodel-cardinality-one-to-many-spaced-passes", "datamodel", "PASS")
def r6ae(root):
    _cardinality_case(root, "one to many")


@case("datamodel-an-undecided-cardinality-still-fails", "datamodel", "FAIL")
def r6af(root):
    # The control. Widening the notation must not widen it to nothing.
    _cardinality_case(root, "not decided yet")


_STATE_MODEL = ("# Data model\n## Entities\n- Payment: system of record: the ledger.\n"
                "## Status and lifecycle\nstatus: pending | captured | settled\n"
                "## Relationships\n- Payment to Payment: one-to-one.\n")


@case("pending-is-a-payment-state-not-a-placeholder", "diagrams", "PASS")
def r6ag(root):
    # The quotable one. A senior engineer models a payment lifecycle, uses the
    # word every payment system uses for its first state, and is told the state
    # "appears nowhere else in the dossier" while it sits declared four lines
    # above under a heading called Lifecycle, because an internal list of
    # placeholder tokens like tbd and xxx happens to contain it. The implied fix
    # was to rename a domain concept to satisfy a linter.
    write(root, "05-data-model.md", _STATE_MODEL)
    write(root, "06-diagrams.md",
          "# Diagrams\n## Lifecycle\n```mermaid\nstateDiagram-v2\n"
          "  [*] --> pending\n  pending --> captured\n  captured --> settled\n```\n")


@case("none-is-a-domain-value-not-a-placeholder", "diagrams", "PASS")
def r6ah(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Shipment: system of record: the WMS.\n"
          "## Status and lifecycle\nstatus: none | booked | delivered\n"
          "## Relationships\n- Shipment to Shipment: one-to-one.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n## Lifecycle\n```mermaid\nstateDiagram-v2\n"
          "  [*] --> none\n  none --> booked\n  booked --> delivered\n```\n")


@case("a-state-called-tbd-is-still-a-placeholder", "diagrams", "FAIL")
def r6ai(root):
    # The control for the two above: scoping the list to domain content must not
    # empty it. `tbd` is a note to the author in any context, so it is not a
    # declared state however it is written down, the diagram node that names it
    # does not trace, and the FAIL says which of the orphans name nothing.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Shipment: system of record: the WMS.\n"
          "## Status and lifecycle\nstatus: tbd | booked\n"
          "## Relationships\n- Shipment to Shipment: one-to-one.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n## Lifecycle\n```mermaid\nstateDiagram-v2\n"
          "  [*] --> tbd\n  tbd --> booked\n```\n")


@case("mermaid-c4context-passes", "diagrams", "PASS")
def r6aj(root):
    # The canonical Mermaid dialect for the system-context diagram SKILL.md
    # Phase 5 asks a T2 or T3 author to draw. Read as a flowchart, it turned its
    # own keywords Person and System into the orphans it then reported.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Customer: system of record: the CRM.\n"
          "- Payment: system of record: the ledger.\n"
          "## Relationships\n- Customer to Payment: one-to-many.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n## Context\n```mermaid\nC4Context\n  title Payments\n"
          "  Enterprise_Boundary(b0, \"Acme\") {\n"
          "    Person(Customer, \"Customer\", \"a buyer\")\n"
          "    System(Payment, \"Payment\", \"the payment service\")\n"
          "  }\n  Rel(Customer, Payment, \"pays with\")\n```\n")


@case("mermaid-block-beta-passes", "diagrams", "PASS")
def r6ak(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Customer: system of record: the CRM.\n"
          "- Payment: system of record: the ledger.\n"
          "## Relationships\n- Customer to Payment: one-to-many.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n## Blocks\n```mermaid\nblock-beta\n  columns 2\n  Customer Payment\n```\n")


@case("an-unreadable-diagram-dialect-is-nodata-not-a-failure", "diagrams", "NO-DATA")
def r6al(root):
    # SKILL.md L5's own rule: a type this tool cannot trace is NO-DATA and not a
    # failure. Read as a flowchart, an unknown dialect invented orphans out of
    # its own statement keywords.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Customer: system of record: the CRM.\n"
          "## Relationships\n- Customer to Customer: one-to-one.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n## Something new\n```mermaid\nzenUmlDiagram\n  A.method(B)\n```\n")


# --- discovery: what the walk reaches --------------------------------------

@case("a-stray-intake-in-the-root-does-not-hide-the-dossiers-below-it", "designrun", "blocked")
def r6am(root):
    # `if is_dossier(root): targets = [root]` skipped the walk entirely, so one
    # 00-intake.json in a repository root made every dossier under it invisible
    # and --strict exited 0 over unedited templates. sbe_intake.py wrote exactly
    # that file to wherever it was run, and the README says to run it.
    write(root, "00-intake.json",
          {"tier": "T0", "answers": TIER_ANSWERS["T0"], "override": None})
    for name in ("01-purpose.md", "02-process.md", "03-adr.md", "04-technology-map.md",
                 "05-data-model.md", "06-diagrams.md", "07-verification.md"):
        write(root, "design/payhook/" + name,
              "# Section\n<!-- SBE-TEMPLATE-UNFILLED replace this -->\nfill this in please\n")
    return design_run(root)


@case("a-dossier-in-a-directory-called-vendor-is-still-a-dossier", "designrun", "blocked")
def r6an(root):
    # Discovery must not depend on what somebody named a directory. `mv plain
    # vendor` turned two FAILs into two NO-DATAs at exit 0, and the evidence line
    # said "no directory contains 00-intake.json" about a tree that held one.
    write(root, "vendor/refunds/00-intake.json",
          {"tier": "T2", "answers": TIER_ANSWERS["T2"], "override": None})
    write(root, "vendor/refunds/01-purpose.md", PURPOSE)
    return design_run(root)


@case("a-manifest-in-a-directory-called-vendor-is-still-read", "numbers", "FAIL")
def r6ao(root):
    write(root, "vendor/reports/numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": "", "query": "SELECT 1",
        "second_derivation": "SELECT 2", "rerun": {"ran": True, "primary": 1, "secondary": 1}}]})


@case("a-real-virtualenv-is-still-pruned-by-its-marker", "lints", "PASS")
def r6ap(root):
    # The control for the three above: detection moved from the NAME to the
    # marker, and the marker still has to work, or the one gate a .sbe-exempt
    # cannot waive starts failing teams over code they did not write.
    write(root, "src/app.py", "def f():\n    return 1\n")
    write(root, "toolchain/pyvenv.cfg", "home = /usr/bin\n")
    write(root, "toolchain/lib/thirdparty.py",
          "try:\n    f()\nexcept Exception:\n    pass\n")  # sbe: allow-silent lint FIXTURE, see s5
    return run_score_lints([root])


# --- the artifacts nobody had a content rule for ----------------------------

_UNRELATED = {
    "01-purpose.md": "# Purpose\nBananas ripen faster beside an apple.\n",
    "02-process.md": "# Process\nLawnmower maintenance happens each spring.\n",
    "03-adr.md": DOSSIER["03-adr.md"],
    "04-technology-map.md": "# Technology map\n| Machine | Make |\n|---|---|\n"
                            "| Tractor | Fordson |\n",
    "05-data-model.md": DOSSIER["05-data-model.md"],
    "06-diagrams.md": DOSSIER["06-diagrams.md"],
    "07-verification.md": "# Verification\nWe verify Mars by telescope on clear nights.\n",
}


@case("a-t3-dossier-of-unrelated-artifacts-is-not-a-dossier", "artifacts", "FAIL")
def r6aq(root):
    # Five of five PASS on a T3 dossier about bananas, lawnmowers, tractors and
    # Mars. `present()` was the entire content rule for four of the seven
    # artifacts: two words and eight characters each. Every sentence the report
    # printed was narrowly true and the dossier as a whole proved nothing.
    write(root, "00-intake.json", {"tier": "T3", "answers": TIER_ANSWERS["T3"], "override": None})
    for name, body in _UNRELATED.items():
        write(root, name, body)


@case("a-t3-dossier-about-one-system-still-passes", "artifacts", "PASS")
def r6ar(root):
    # The control, and the one that matters more: the coherence rule must not
    # reject an honest dossier whose artifacts talk about different LAYERS of the
    # same system.
    write(root, "00-intake.json", {"tier": "T3", "answers": TIER_ANSWERS["T3"], "override": None})
    for name, body in DOSSIER.items():
        write(root, name, body)


# --- the lint aimed at SQL, on SQL ------------------------------------------

@case("a-conflict-skipping-upsert-in-a-sql-file-is-caught", "lints", "FAIL")
def r6as(root):
    # L11 names .sql first and the pattern needed a Python `.execute(` on the
    # same line, so the one lint that exists for warehouse work could not fire on
    # a warehouse file.
    write(root, "load.sql",
          "INSERT INTO orders (id, amount)\nSELECT id, amount FROM staging\n"
          "ON CONFLICT (id) DO NOTHING;\n")  # sbe: allow-silent this is the lint FIXTURE: the skipping upsert is the defect under test, written into a temp file and never executed here
    return run_score_lints([root])


@case("a-conflict-skipping-upsert-split-over-lines-is-caught", "lints", "FAIL")
def r6at(root):
    write(root, "load.sql",
          "INSERT INTO orders (id) SELECT id FROM staging\nON CONFLICT (id)\n  DO NOTHING;\n")  # sbe: allow-silent lint FIXTURE, see the case above
    return run_score_lints([root])


@case("a-conflict-skipping-upsert-in-a-python-variable-is-caught", "lints", "FAIL")
def r6au(root):
    write(root, "load.py",
          "SQL = \"INSERT INTO orders (id) VALUES (1) ON CONFLICT (id) DO NOTHING\"\n"  # sbe: allow-silent lint FIXTURE, see the case above
          "def load(conn):\n    conn.execute(SQL)\n")
    return run_score_lints([root])


@case("a-real-upsert-that-updates-is-not-a-silent-failure", "lints", "PASS")
def r6av(root):
    # The control. ON CONFLICT DO UPDATE is the legitimate upsert and flagging it
    # would be the false positive that gets the lint switched off.
    write(root, "load.sql",
          "INSERT INTO orders (id, amount) VALUES (1, 2)\n"
          "ON CONFLICT (id) DO UPDATE SET amount = excluded.amount;\n")
    return run_score_lints([root])


@case("the-lint-reads-a-users-own-file-called-sbe-score", "lints", "FAIL")
def r6aw(root):
    # The self-skip was a BASENAME comparison against every file in the CALLER's
    # tree, so a user's own sbe_score.py was never opened and "1 file(s) scanned,
    # clean" was printed over a directory holding two, one of which swallowed
    # every error it met.
    write(root, "clean.py", "def f():\n    return 1\n")
    write(root, "sbe_score.py",
          "def g():\n    try:\n        risky()\n    except:\n        pass\n")  # sbe: allow-silent lint FIXTURE, see s5
    return run_score_lints([root])


# --- staleness arithmetic ---------------------------------------------------

def _reviews(root, body):
    write(root, "99-System/telemetry/reviews.jsonl", body)
    return root


@case("a-review-dated-in-the-future-is-a-broken-record", "score", "FAIL")
def r6ax(root):
    # `age_days` returns a negative number for a future timestamp and four checks
    # compared it with <= or > without a floor, so review-cadence printed
    # "last review: -1620.2d ago" and called it a PASS, and the genuinely stale
    # 2020 review in the same ledger was masked because max() picked the future
    # row.
    return score_check("review-cadence", _reviews(
        root, "{\"ts\": \"2020-01-01T00:00:00Z\"}\n{\"ts\": \"2031-01-01T00:00:00Z\"}\n"))


@case("a-correction-dated-in-the-future-is-a-broken-record", "score", "FAIL")
def r6ay(root):
    write(root, "99-System/telemetry/corrections.jsonl", "{\"ts\": \"2031-01-01T00:00:00Z\"}\n")
    return score_check("correction-latency", root)


@case("a-session-dated-in-the-future-is-a-broken-record", "score", "FAIL")
def r6az(root):
    return score_check("ledger-coverage", _ledger(
        root, "{\"session_id\": \"s1\", \"ts\": \"2031-01-01T00:00:00Z\"}\n"))


@case("six-copies-of-one-rating-are-one-rating", "score", "FAIL")
def r6ba(root):
    # The dedupe rule gate_numbers learned, applied to the two thresholds in this
    # file that counted the same row N times.
    write(root, "99-System/telemetry/ratings.jsonl",
          "".join("{\"score\": 5}\n" for _ in range(6)))
    return score_check("felt-outcome-ratings", root)


@case("six-distinct-ratings-still-pass", "score", "PASS")
def r6bb(root):
    write(root, "99-System/telemetry/ratings.jsonl",
          "".join("{\"score\": %d}\n" % s for s in (5, 4, 3, 2, 1, 0)))
    return score_check("felt-outcome-ratings", root)


# --- the meta-test's own lint, probed with the spellings that evaded it ------

@case("the-meta-test-lint-sees-five-more-spellings-of-the-verdict-pass", "guard", "caught")
def r6bc(root):
    """Five ways to return PASS that the lint could not see, from the review.

    Each was proved against the shipped tree by dropping the function into
    tools/ and watching the run print 0 failures: an f-string is a JoinedStr and
    not a Constant; a name bound by `from sbe_checks import VERDICTS` is bound by
    no Assign; a lambda is not a FunctionDef; `.upper()` and `"".join(...)` are
    Calls. Enumerating node types is the hand-fix-the-instance loop this project
    exists to break, so the lint was inverted: a (verdict, evidence) return whose
    head is not PROVABLY one of FAIL or NO-DATA is a candidate, and the way out
    is a named allowlist rather than another node type.
    """
    meta = SourceFileLoader("meta_probe2",
                            os.path.join(HERE, "test_no_data_class.py")).load_module()
    tools = os.path.join(root, "tools")
    os.makedirs(tools)
    write(tools, "exotic.py",
          "from sbe_checks import VERDICTS\n"
          "_ok = lambda: \"PASS\"\n\n"
          "def gate_fstring(root):\n"
          "    return f\"PASS\", \"examined nothing\"\n\n"
          "def gate_imported_constant(root):\n"
          "    return VERDICTS[0], \"examined nothing\"\n\n"
          "def gate_lambda(root):\n"
          "    return _ok(), \"examined nothing\"\n\n"
          "def gate_upper(root):\n"
          "    return \"pass\".upper(), \"examined nothing\"\n\n"
          "def gate_join(root):\n"
          "    return \"\".join([\"PA\", \"SS\"]), \"examined nothing\"\n\n"
          "def gate_indirect(root):\n"
          "    verdict = compute()\n"
          "    return verdict, \"examined nothing\"\n\n"
          "def honest_fail(root):\n"
          "    return \"FAIL\", \"this one is provably not a pass\"\n")
    original = meta.TOOLS_DIR
    try:
        meta.TOOLS_DIR = tools
        found = {name for _fn, name, _why in meta.pass_returning_functions()}
    finally:
        meta.TOOLS_DIR = original
    want = {"gate_fstring", "gate_imported_constant", "gate_lambda", "gate_upper",
            "gate_join", "gate_indirect"}
    missing = sorted(want - found)
    if missing:
        return "the lint did not see %s" % ", ".join(missing)
    if "honest_fail" in found:
        return "the lint flagged honest_fail, which provably returns FAIL"
    return "caught"


@case("intake-writes-its-file-into-the-directory-it-was-given", "guard", "written-where-asked")
def r6bd(root):
    # It took no path argument, accepted one, ignored it, and wrote to wherever
    # it was run from, printing a line that reads like it worked.
    target = os.path.join(root, "design", "payhook")
    os.makedirs(target)
    out = subprocess.run([sys.executable, INTAKE, target], input="y\ny\ny\ny\nmany\n",
                         capture_output=True, text=True, cwd=root)
    if out.returncode != 0:
        return "exit %d: %s" % (out.returncode, out.stdout.strip()[:80])
    if os.path.isfile(os.path.join(root, "00-intake.json")):
        return "it wrote to the directory it was run from, not the one it was given"
    return ("written-where-asked" if os.path.isfile(os.path.join(target, "00-intake.json"))
            else "no 00-intake.json was written anywhere")


@case("intake-help-does-not-block-on-stdin", "guard", "help-printed")
def r6be(root):
    out = subprocess.run([sys.executable, INTAKE, "--help"], input="",
                         capture_output=True, text=True, timeout=20)
    return ("help-printed" if out.returncode == 0 and "usage: sbe_intake.py" in out.stdout
            else "exit %d: %s" % (out.returncode, (out.stdout + out.stderr).strip()[:80]))


# ---------------------------------------------------------------------------
# Two laws that claimed an enforcement their tool did not deliver, which
# is this project's own worst failure class rather than an edge case.
#
# L15 said an override sets BOTH fields and that they must agree. Only the reason
# was enforced: a tier differing from the computed one with `override` null took a
# path nothing checked, and `override: null` is what every intake file the shipped
# tool writes starts with, so the unenforced path was the default path.
#
# L4 said a bullet in some other section "is prose and is not read as an entity".
# The fallback for a model with no entity heading read exactly that bullet, so an
# honest Notes list FAILed as two sourceless entities, and the same list with an
# ownership phrase in it PASSed as "2 entities, each with a system of record" over
# a file that declares no entity at all.

@case("a-moved-tier-with-a-null-override-field-fails", "artifacts", "FAIL")
def s7a(root):
    write(root, "00-intake.json", {"tier": "T1", "answers": T3_ANSWERS, "override": None,
                                   "override_reason": "the auditor requires the full dossier"})
    write(root, "01-purpose.md", PURPOSE)


@case("an-incomplete-override-names-both-fields", "evidence", "both-named")
def s7b(root):
    write(root, "00-intake.json", {"tier": "T1", "answers": T3_ANSWERS, "override": None,
                                   "override_reason": "the auditor requires the full dossier"})
    write(root, "01-purpose.md", PURPOSE)
    line = gate_line(root, "artifacts")
    if line.split()[1:2] != ["FAIL"]:
        return line
    return ("both-named" if "override field" in line and "override_reason" in line else line)


@case("an-override-field-that-moves-no-tier-is-reported-as-moving-nothing",
      "evidence", "no-move-stated")
def s7c(root):
    # The other direction of "both fields agree": the fields agree with each other
    # and with the answers, so nothing was overridden. Silence there would let a
    # stale field read as a control that was exercised.
    write(root, "00-intake.json", {"tier": "T1", "answers": T1_ANSWERS, "override": "T1",
                                   "override_reason": "kept at T1 after the review"})
    write(root, "01-purpose.md", PURPOSE)
    line = gate_line(root, "artifacts")
    if line.split()[1:2] != ["PASS"]:
        return line
    return "no-move-stated" if "moved no tier" in line else line


@case("a-notes-list-with-no-entity-heading-is-not-read-as-entities",
      "evidence", "prose-left-as-prose")
def s7d(root):
    write(root, "05-data-model.md",
          "# Data model\n## Notes\n- Rollout plan: we ship on Tuesday behind a flag\n"
          "- Open question: who owns retention after the migration\n")
    line = gate_line(root, "datamodel")
    return ("prose-left-as-prose"
            if "Rollout plan'" not in line and "no entity" in line else line)


@case("a-notes-list-that-names-an-owner-is-not-an-entity-count", "datamodel", "NO-DATA")
def s7e(root):
    # The mirror case: the same prose with an ownership phrase in it used to buy
    # "2 entities, each with a system of record" over a file holding no entity.
    write(root, "05-data-model.md",
          "# Data model\n## Notes\n- Rollout plan: owned by the platform team\n"
          "- Open question: owner: the data guild\n"
          "## Relationships\n- Customer to Order: one-to-many.\n")


@case("a-data-model-with-no-entity-heading-is-still-checked", "datamodel", "FAIL")
def s7f(root):
    # The half that must survive the fix: a model whose heading reads "Conceptual
    # model" is not exempt from the rule just because it never says "entities".
    write(root, "05-data-model.md",
          "# Data model\n## Conceptual model\n- Customer: system of record: the CRM.\n"
          "- Order: system of record: TBD\n"
          "## Relationships\n- Customer to Order: one-to-many.\n")


@case("a-data-model-with-no-entity-heading-says-what-it-read", "evidence", "disclosed")
def s7g(root):
    write(root, "05-data-model.md",
          "# Data model\n## Conceptual model\n- Customer: system of record: the CRM.\n"
          "- Order: system of record: the OMS.\n"
          "## Relationships\n- Customer to Order: one-to-many.\n")
    line = gate_line(root, "datamodel")
    if line.split()[1:2] != ["NO-DATA"]:
        return line
    return ("disclosed" if "Customer" in line and "entit" in line else line)


@case("a-diagram-still-traces-to-a-model-with-no-entity-heading", "diagrams", "PASS")
def s7h(root):
    # Tracing reads the wider set on purpose: a name it does not know produces a
    # false orphan, so the guess there runs the other way from the data-model
    # check's. This pins that the scoping fix did not invent orphans.
    write(root, "05-data-model.md",
          "# Data model\n## Conceptual model\n- Customer: system of record: the CRM.\n"
          "- Order: system of record: the OMS.\n")
    write(root, "06-diagrams.md", "```mermaid\nflowchart LR\n  Customer --> Order\n```\n")


# ---------------------------------------------------------------------------
# The law-by-law sweep. Each of these is a sentence a law
# printed that its tool did not do, or a tool doing something its law never said.
# The fix went to whichever side was wrong, and the fixture pins it either way.

def score_lint_line(args):
    """The whole silent-failure-lints line, so a fixture can pin the EVIDENCE."""
    out = subprocess.run([sys.executable, SCORE] + args, capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if line.strip().startswith("silent-failure-lints"):
            return line.strip()
    return ""


@case("a-number-outside-every-range-is-reported-not-dropped", "decide", "reported")
def w1(root):
    # It vanished: `deploying_teams=0` produced "no criterion was answered" over a
    # run that answered one, and beside a second criterion it produced a confident
    # recommendation with nothing saying half the input had been discarded, while
    # the type error one line above it was reported.
    r = _decide.recommend(_TABLES["shape"], {"deploying_teams": 0, "consistency": "strong"})
    return "reported" if any("deploying_teams=0" in u for u in r["unrecognized"]) else "dropped"


@case("a-flip-condition-belongs-to-the-recommendation-not-the-table", "decide", "its-own")
def w1b(root):
    # L12's promise was guarded only by "the string is truthy", so deleting the
    # per-recommendation lookup and falling back to the one table-wide string
    # would still have passed CI, which is the defect that string was added to
    # fix: a run recommending services off nine teams and high isolation was
    # handed a flip condition naming two conditions that were already true.
    shared = _TABLES["shape"]["flip"]
    seen = set()
    for teams, cons, ops, iso in ((1, "strong", "low", "low"), (9, "eventual", "high", "high"),
                                  (3, "eventual", "high", "high")):
        r = _decide.recommend(_TABLES["shape"], {"deploying_teams": teams, "consistency": cons,
                                                 "ops_maturity": ops, "failure_isolation": iso})
        if r["flip_condition"] == shared:
            return "%s was handed the table-wide flip condition" % r["recommendation"]
        seen.add(r["flip_condition"])
    return "its-own" if len(seen) == 3 else "two recommendations share one flip condition"


@case("a-review-id-of-more-than-one-word-is-a-pointer-not-a-failure", "gaterun", "NO-DATA")
def w2(root):
    # `^Reviewed-in:\s*(\S+)$` was a shape rule no law declared: a human-written
    # id fell past the branch and got the FAIL that says no review id is recorded.
    git_init(root)
    open(os.path.join(root, "APPROVAL"), "w").write("touches the partner payout path\n")
    subprocess.run(["git", "-C", root, "add", "."], check=True)
    subprocess.run(["git", "-C", root, "commit", "-qm",
                    "payout batching\n\nReviewed-in: PR 99999 on the payments board"], check=True)
    out = subprocess.run([sys.executable, GATE, "approval", root], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if line.strip().startswith("approval"):
            return line.split()[1]
    return "no-line"


@case("an-exemption-with-no-reason-waives-nothing", "lints", "FAIL")
def w3(root):
    # L11 writes the marker as `# sbe: allow-silent <reason>` and the reason was
    # decoration: the bare marker suppressed the finding, in the one gate a
    # .sbe-exempt cannot waive.
    write(root, "bad.py", "try:\n    f()\nexcept:  # sbe" + ": allow-silent\n    pass\n")  # sbe: allow-silent this is the lint FIXTURE: the swallow is the defect under test, written into a temp file, never executed here
    return run_score_lints([root])


@case("an-exemption-carrying-a-reason-still-waives", "lints", "PASS")
def w4(root):
    write(root, "ok.py", "def g():\n    return 2\n")
    write(root, "bad.py", "try:\n    f()\nexcept:  # sbe" + ": allow-silent boundary read, the "  # sbe: allow-silent this is the lint FIXTURE: the swallow is the defect under test, written into a temp file, never executed here
                          "caller handles the absence\n    pass\n")
    return run_score_lints([root])


@case("a-checked-subprocess-call-with-a-nested-call-is-not-a-hit", "lints", "PASS")
def w5(root):
    # A lint firing on correct code is how a gate gets switched off: the lookahead
    # ended at the closing paren of the NESTED call and never saw check=True.
    write(root, "ok.py", 'import shlex, subprocess\nsubprocess.run(shlex.split("ls -l"), check=True)\n')
    return run_score_lints([root])


@case("a-long-conflict-skipping-upsert-is-still-caught", "lints", "FAIL")
def w6(root):
    # The pattern gave up after 300 characters, so the law's "stops at the
    # statement's semicolon" was false about any statement longer than that.
    write(root, "up.sql", "INSERT INTO t (id) VALUES (1) ON CONFLICT (id) /* %s */ DO NOTHING;\n"  # sbe: allow-silent this is the lint FIXTURE: the skipping upsert is the defect under test, written into a temp file and never executed here
          % ("x" * 400))
    return run_score_lints([root])


@case("a-truncated-hit-list-says-how-many-it-did-not-name", "lints", "counted")
def w7(root):
    for i in range(7):
        write(root, "f%d.py" % i, "try:\n    f()\nexcept:\n    pass\n")  # sbe: allow-silent this is the lint FIXTURE: the swallow is the defect under test, written into a temp file, never executed here
    line = score_lint_line([root])
    return "counted" if "and 2 more not named" in line else line


@case("an-empty-file-is-not-counted-as-source-examined", "lints", "named")
def w8(root):
    write(root, "empty.py", "")
    write(root, "ok.py", "def f():\n    return 1\n")
    line = score_lint_line([root])
    return "named" if "hold nothing to examine" in line and "empty.py" in line else line


@case("an-artifact-coherent-with-a-file-the-tier-did-not-require-passes", "artifacts", "PASS")
def w9(root):
    # The sibling set was the TIER-REQUIRED list, so a T1 purpose brief sharing
    # four words with the 04-technology-map beside it FAILed with the sentence
    # "no substantive word in it appears in any sibling artifact".
    write(root, "00-intake.json", {"tier": "T1", "answers": T1_ANSWERS, "override": None})
    write(root, "01-purpose.md",
          "# Purpose\nRefund settlement latency must fall under one business day.\n")
    write(root, "04-technology-map.md",
          "# Technology map\n| Component | Technology | Owner |\n|---|---|---|\n"
          "| Widget | Postgres holding refund settlement rows | Platform |\n")


@case("an-inline-edge-label-is-named-in-the-skipped-tokens", "evidence", "named")
def w10(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Customer: system of record: the CRM.\n"
          "- Order: system of record: the OMS.\n")
    write(root, "06-diagrams.md",
          "```mermaid\nflowchart LR\n  C[Customer] -- Ledger --> O[Order]\n```\n")
    line = gate_line(root, "diagrams")
    return "named" if "Ledger (an inline edge label, not a node)" in line else line


@case("a-truncated-entity-failure-says-how-many-it-did-not-show", "evidence", "counted")
def w11(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n" + "".join("- %s\n" % n for n in
          ("Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel")))
    line = gate_line(root, "datamodel")
    return "counted" if "and 2 more not shown" in line else line


@case("the-adr-pass-line-claims-only-what-the-threshold-measured", "evidence", "measured")
def w12(root):
    # Two bullets that name two options and give no reason at all cleared the
    # threshold, and the verdict said "rejected with a stated reason" over them.
    # No rule here can tell a reason from a longer name, so the sentence says
    # what it measured and names the rest as human review.
    write(root, "03-adr.md",
          "# ADR\n## Criteria\nlatency, freshness\n## Rejected alternatives\n"
          "- Synchronous ledger call\n- Nightly batch reconciliation\n"
          "## Decision\nPublish to a queue.\n## Consequences\nOne more moving part.\n"
          "## What would flip this\nSub-second freshness becomes a requirement.\n")
    line = gate_line(root, "adr")
    if line.split()[1:2] != ["PASS"]:
        return line
    return ("measured" if "stated reason" not in line and "human review" in line else line)


@case("the-lint-numbers-this-repository-prints-are-the-numbers-it-computes",
      "docs", "consistent")
def w13(root):
    """SKILL.md states this repository's own lint run. Both numbers were stale.

    A number in a doc that nothing recomputes is a stale evidence string with a
    longer half-life, which is the argument the eval-count and checker-line
    guards beside this one already make. This one recomputes the two numbers L11
    prints about this repository from a live run.
    """
    import re as _re
    body = open(os.path.join(_REPO, "SKILL.md"), errors="replace").read()
    m = _re.search(r"(\w+) waived hits and (\w+) files that were scanned and genuinely found clean",
                   body)
    if not m:
        return "SKILL.md no longer states the waived-hit and clean-file counts of its own lint run"
    # Written either way: the sentence carried spelled-out words for a wave and
    # digits after, and a guard that reads one form and not the other is a guard
    # that goes quiet on an edit rather than failing on one.
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
    def _n(tok):
        return int(tok) if tok.isdigit() else words.get(tok.lower(), -1)
    said = (_n(m.group(1)), _n(m.group(2)))
    # Over the TRACKED tree, not the live working directory. The lint walks
    # whatever it is pointed at, so an untracked scratch directory holding
    # Python (a reviewer's probe copy) flipped this eval for the local
    # developer while CI, on a fresh checkout with no untracked files, stayed
    # green: the gate's verdict depended on files in nobody's clone, and the
    # message it printed then blamed SKILL.md's pinned numbers. The tracked
    # files copied with their WORKING-TREE content are exactly what a reader
    # gets on their next pull, and the copy excludes the untracked scratch, so
    # this is hermetic without lagging the edit under test.
    import shutil
    listing = subprocess.run(["git", "-C", _REPO, "ls-files", "-z"],
                             capture_output=True)
    if listing.returncode != 0:
        return "could not list the tracked tree: %s" % (
            listing.stderr.decode("utf-8", "replace")[:120])
    with tempfile.TemporaryDirectory() as d:
        for rel in listing.stdout.decode("utf-8", "surrogateescape").split("\0"):
            if not rel:
                continue
            src = os.path.join(_REPO, rel)
            if not os.path.isfile(src):
                continue
            dst = os.path.join(d, rel)
            os.makedirs(os.path.dirname(dst) or d, exist_ok=True)
            shutil.copy(src, dst)
        # Run the COPIED scorer, so its self-skip (samefile against __file__)
        # resolves to the copy it is scanning rather than the original in the
        # repo; pointed at its own tree, exactly the shipped invocation.
        copied_score = os.path.join(d, "tools", "sbe_score.py")
        out = subprocess.run([sys.executable, copied_score, d], capture_output=True, text=True)
    line = next((l for l in out.stdout.splitlines()
                 if l.strip().startswith("silent-failure-lints")), "")
    verdict = line.split()[1] if len(line.split()) > 1 else "?"
    if verdict != "PASS":
        # When the lint itself did not PASS, say so, rather than reporting the
        # absence of the counts it wanted to read as if SKILL.md had drifted.
        return "the tracked-tree lint did not PASS (got %s): %s" % (verdict, line.strip()[:120])
    waived = _re.search(r"(\d+) suppressed", line)
    clean = _re.search(r"(\d+) file\(s\) holding no match at all", line)
    if not waived or not clean:
        return "the tracked-tree lint line printed no suppressed or clean-file count: %s" % line.strip()[:120]
    got = (int(waived.group(1)), int(clean.group(1)))
    return ("consistent" if said == got else
            "SKILL.md says %r but the tracked tree has %d waived hits and %d clean files"
            % (m.group(0), got[0], got[1]))


# ---------------------------------------------------------------------------
# The ACCESS axis: evidence that exists and cannot be opened. The suite held
# zero occurrences of chmod, symlink or mkfifo, so no fixture had ever
# distinguished a check that read clean evidence from a check that read nothing.
# The meta-test sweeps the class per check; these pin the mixed shapes it cannot
# generate (some evidence readable, some not) and the evidence sentences.

_CAN_DROP_ACCESS = os.name == "posix" and os.geteuid() != 0


@case("an-unreadable-source-file-fails-the-lint", "lints", "FAIL")
def x1(root):
    # chmod 000 on a source file removed it from the lint, from the count, and
    # from the sentence: "1 file(s) scanned, clean" over a directory holding a
    # swallowed error the scan was refused access to.
    if not _CAN_DROP_ACCESS:
        return "FAIL"      # as root, access cannot be taken away; the meta-test declares the same limit
    write(root, "clean.py", "def f():\n    return 1\n")
    write(root, "evil.py", "try:\n    f()\nexcept:\n    pass\n")  # sbe: allow-silent this is the lint FIXTURE: the swallow is the defect under test, written into a temp file, never executed here
    os.chmod(os.path.join(root, "evil.py"), 0)
    return run_score_lints([root])


@case("an-unreadable-directory-fails-the-lint", "lints", "FAIL")
def x2(root):
    if not _CAN_DROP_ACCESS:
        return "FAIL"
    write(root, "ok.py", "def f():\n    return 1\n")
    write(root, "locked/evil.py", "try:\n    f()\nexcept:\n    pass\n")  # sbe: allow-silent this is the lint FIXTURE: the swallow is the defect under test, written into a temp file, never executed here
    os.chmod(os.path.join(root, "locked"), 0)
    try:
        return run_score_lints([root])
    finally:
        os.chmod(os.path.join(root, "locked"), 0o755)


@case("a-symlinked-source-directory-is-disclosed-not-silent", "evidence", "disclosed")
def x3(root):
    # os.walk does not follow directory symlinks, so a symlinked tree holding a
    # hit was neither walked, nor pruned, nor recorded, and the verdict printed
    # "clean" over a set that silently excluded it.
    write(root, "repo/ok.py", "def f():\n    return 1\n")
    write(root, "elsewhere/evil.py", "try:\n    f()\nexcept:\n    pass\n")  # sbe: allow-silent this is the lint FIXTURE: the swallow is the defect under test, written into a temp file, never executed here
    os.symlink(os.path.join(root, "elsewhere"), os.path.join(root, "repo", "vendor_link"))
    line = score_lint_line([os.path.join(root, "repo")])
    return ("disclosed" if "symlinked directory" in line and "vendor_link" in line
            else line or "no-lint-line")


@case("fence-lint-names-a-denied-registry-instead-of-shrinking-the-list", "evidence", "occupied")
def x_fence_denial(root):
    # The dispatch aid read BROTHERSBE_REGISTRIES through a raw glob, and a
    # glob returns FEWER paths, not an error, over a directory it cannot
    # enter: chmod 000 on one project made its money-path fence vanish and,
    # with the whole tree denied, the aid printed "no live fences found" over
    # two live fences. Its one job is that no writer launches into an occupied
    # file set, so a registry it cannot read is OCCUPIED, never empty.
    if not _CAN_DROP_ACCESS:
        return "occupied"
    write(root, "reg/projA/STATE.md", "# STATE\n- agent w1 tier T1 editing tools/x.py\n")
    write(root, "reg/projB/STATE.md", "# STATE\n- agent w9 editing money paths\n")
    os.chmod(os.path.join(root, "reg", "projB"), 0)
    env = dict(os.environ,
               BROTHERSBE_REGISTRIES=os.path.join(root, "reg", "*", "STATE.md"))
    try:
        out = subprocess.run([sys.executable, TELEMETRY_TOOL, "fence-lint", root],
                             capture_output=True, text=True, env=env, timeout=60)
        blind = subprocess.run([sys.executable, TELEMETRY_TOOL, "fence-lint", root],
                               capture_output=True, text=True, timeout=60,
                               env=dict(env, BROTHERSBE_REGISTRIES=os.path.join(
                                   root, "no-such", "*", "STATE.md")))
    finally:
        os.chmod(os.path.join(root, "reg", "projB"), 0o755)
    if "agent w1 tier T1" not in out.stdout:
        return "the readable fence vanished: %s" % out.stdout.strip()[:120]
    if "could not be read" not in out.stdout or "occupied" not in out.stdout:
        return "the denial was silent: %s" % out.stdout.strip()[:160]
    # The control: a pattern matching nothing readable OR denied still says
    # "no live fences", so the denial sentence is not printed unconditionally.
    if "no live fences found" not in blind.stdout:
        return "the control run lost its no-fences sentence: %s" % blind.stdout.strip()[:120]
    return "occupied"


@case("the-lint-self-skip-is-file-identity-not-path-spelling", "evidence", "skipped itself")
def x3b(root):
    # realpath resolves symlinks and nothing else, so the same file reached
    # through a case-different spelling (TOOLS/ on macOS's default
    # case-insensitive filesystem) was two identities: the tool scanned
    # ITSELF and FAILed the honest shipped tree with four "defects" that were
    # its own regex literals. Identity is the file, not the spelling:
    # samefile compares inodes. Reproduced portably with a HARDLINK, a
    # spelling axis the case fix would not cover and case-sensitive CI can run.
    import shutil
    tdir = os.path.join(root, "tools")
    os.makedirs(tdir)
    for fn in ("sbe_score.py", "sbe_checks.py", "sbe_telemetry.py"):
        shutil.copy(os.path.join(_REPO, "tools", fn), os.path.join(tdir, fn))
    write(root, "tools/clean.py", "def f():\n    return 1\n")
    link = os.path.join(tdir, "scanner-hardlink.py")
    os.link(os.path.join(tdir, "sbe_score.py"), link)
    e = dict(os.environ)
    e.update({"BROTHERSBE_VAULT": root, "BROTHERSBE_REGISTRIES": "", "SBE_LINT_ROOT": ""})
    out = subprocess.run([sys.executable, link, tdir], capture_output=True, text=True, env=e)
    line = next((l for l in out.stdout.splitlines()
                 if l.strip().startswith("silent-failure-lints")), "")
    if "own source was not scanned" not in line:
        return "self-skip disclosure missing: %s" % line.strip()[:120]
    if line.split()[1:2] != ["PASS"]:
        return "the tool read its own regex literals as defects: %s" % line.strip()[:120]
    return "skipped itself"


@case("unreadable-registry-files-never-shrink-the-registry", "score", "FAIL")
def x4(root):
    # chmod 000 on the registry files holding the violations turned two FAILs
    # into two PASSes whose sentences said "untagged in: none", over a registry
    # set silently reduced from five files to one.
    if not _CAN_DROP_ACCESS:
        return "FAIL"
    for i in (1, 2, 3, 4):
        write(root, "reg/bad%d.md" % i,
              "# State\n## Fences\n- agent: builder | objective: ship gate %d | open\n" % i)
    write(root, "reg/good.md",
          "# State\n## Fences\n- agent: builder | tier T2 | objective: ship the refund gate\n")
    for i in (1, 2, 3, 4):
        os.chmod(os.path.join(root, "reg", "bad%d.md" % i), 0)
    return score_check("budget-vs-tier", root,
                       env={"BROTHERSBE_REGISTRIES": os.path.join(root, "reg", "*.md")})


@case("an-unreadable-artifact-is-a-broken-claim-not-an-absence", "datamodel", "FAIL")
def x5(root):
    if not _CAN_DROP_ACCESS:
        # As root, read access cannot be taken away, so the fixture degrades to
        # a model that FAILs for a readable reason; the meta-test declares the
        # same host limit on its access scenarios.
        write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer\n"
                                        "## Relationships\n- Customer to Customer: one-to-one.\n")
        return
    write(root, "05-data-model.md", "# Data model\n## Entities\n- Customer: system of record: the CRM.\n"
                                    "## Relationships\n- Customer to Customer: one-to-one.\n")
    os.chmod(os.path.join(root, "05-data-model.md"), 0)


@case("a-directory-wearing-an-artifacts-name-is-not-an-absence", "evidence", "named")
def x6(root):
    # `mkdir 05-data-model.md` used to produce "no 05-data-model.md in this
    # dossier", a sentence asserting absence over something present. The intake
    # beside it is what makes the directory a dossier the walk enters.
    write(root, "00-intake.json", "{}")
    os.makedirs(os.path.join(root, "05-data-model.md"))
    line = gate_line(root, "datamodel")
    if line.split()[1:2] != ["FAIL"]:
        return line
    return "named" if "a directory, not a file" in line else line


@case("an-unenterable-directory-is-named-not-vanished", "evidence", "named")
def x7(root):
    # chmod 000 on a dossier directory made the run print "no directory contains
    # 00-intake.json" about a tree that held one, with five checks silently
    # removed at exit 0.
    if not _CAN_DROP_ACCESS:
        return "named"
    write(root, "design/00-intake.json", "{}")
    os.chmod(os.path.join(root, "design"), 0)
    try:
        out = subprocess.run([sys.executable, DESIGN, root], capture_output=True, text=True,
                             env=dict(os.environ, SBE_DOSSIER_ROOT=""))
    finally:
        os.chmod(os.path.join(root, "design"), 0o755)
    return ("named" if "could not be entered" in out.stdout else
            "the refused directory is not named anywhere in the run")


@case("a-fifo-receipt-is-refused-not-hung", "gaterun", "FAIL")
def x8(root):
    # A FIFO where a receipt was expected hung all three tools forever, in both
    # modes, with no verdict line at all: worse than a crash, because a crash at
    # least prints a FAIL.
    os.mkfifo(os.path.join(root, "ran-receipt.json"))
    try:
        out = subprocess.run([sys.executable, GATE, "ran", root], capture_output=True,
                             text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return "the tool hung on a FIFO"
    for line in out.stdout.splitlines():
        if line.strip().startswith("ran"):
            return line.split()[1]
    return "no-verdict-line"


@case("a-pruned-tree-past-the-inspection-budget-is-still-disclosed", "evidence", "disclosed")
def x9(root):
    # The 4000-directory inspection budget was decremented in silence: once it
    # ran out, every remaining pruned tree was discarded without being looked
    # at, hidden() returned the same [] it returns when nothing was hidden, and
    # the disclosure vanished on exactly the trees it exists for (a real
    # node_modules routinely exceeds 4000 directories).
    write(root, "clean.py", "def f():\n    return 1\n")
    write(root, "aaa_cache/CACHEDIR.TAG", "")
    for i in range(4100):
        os.makedirs(os.path.join(root, "aaa_cache", "d%04d" % i))
    write(root, "zzz_cache/CACHEDIR.TAG", "")
    write(root, "zzz_cache/evil.py", "try:\n    f()\nexcept:\n    pass\n")  # sbe: allow-silent this is the lint FIXTURE: the swallow is the defect under test, written into a temp file, never executed here
    line = score_lint_line([root])
    return ("disclosed" if "not fully inspected" in line and "budget ran out" in line
            else line or "no-lint-line")


# ---------------------------------------------------------------------------
# Values that are present, well-formed, and still record nothing: a NaN
# duration, an integer where a derivation's text belongs, prose that denies an
# owner, an empty ownership column answered by a neighbouring cell.


@case("a-nan-duration-is-not-a-measured-run", "ran", "FAIL")
def v1(root):
    # `NaN <= 0` is False and json.load accepts bare NaN, so this receipt read
    # as "each with a zero exit and a nonzero duration": a false evidence
    # sentence over a value that measures nothing.
    write(root, "ran-receipt.json",
          '{"checks": [{"name": "reconcile", "exit_code": 0, "duration_ms": NaN}]}')


@case("an-infinite-duration-is-not-a-measured-run", "ran", "FAIL")
def v2(root):
    write(root, "ran-receipt.json",
          '{"checks": [{"name": "reconcile", "exit_code": 0, "duration_ms": Infinity}]}')


@case("an-integer-pair-is-not-a-second-derivation", "numbers", "FAIL")
def v3(root):
    # The reduction was applied only to strings, so two integers skipped the
    # reduce-then-test fix entirely and bought "a second derivation whose text
    # differs beyond case, whitespace and comments" over fields holding no text.
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": "snap-1", "query": 0, "second_derivation": 1,
        "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]})


@case("prose-that-denies-an-owner-is-not-a-system-of-record", "datamodel", "FAIL")
def v4(root):
    # "we have not yet decided who the owner is" left the capture "is", and "the
    # owner is still unknown" left "is still unknown": remnants a one-shot
    # copula strip plus a whole-string token list could not refuse, so two
    # entities that deny their owner in plain English were reported as "2
    # entities, each with a system of record".
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "- Customer: we have not yet decided who the owner is\n"
          "- Refund: the owner is still unknown\n"
          "## Relationships\n- Customer to Refund: one-to-many.\n")


@case("a-real-owner-after-a-copula-still-passes", "datamodel", "PASS")
def v5(root):
    # The control: stripping copulas to a fixpoint must not eat a named system.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "- Customer: The system of record is the CRM.\n"
          "- Refund: system of record: the ledger.\n"
          "## Relationships\n- Customer to Refund: one-to-many.\n")


@case("an-empty-ownership-column-is-not-answered-by-another-column", "datamodel", "FAIL")
def v6(root):
    # The System-of-record column is empty in every row; the Notes column
    # mentions the word "owner". Empty cells were dropped before the join, so
    # the phrase test read the Notes cell and the table passed as "each with a
    # system of record" over a column that declares nothing.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "| Entity | System of record | Notes |\n|---|---|---|\n"
          "| Customer |  | still deciding who the owner should be |\n"
          "| Refund |  | still deciding who the owner should be |\n"
          "## Relationships\n- Customer to Refund: one-to-many.\n")


@case("see-above-is-not-a-system-of-record", "datamodel", "FAIL")
def v7(root):
    # The reduce-then-test bug in the data model: `-- see above` is not blank
    # and is not a single vacuity token, so it survived a test that read the
    # raw text, while the identical string was refused as a derivation.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "- Customer: owner: -- see above\n"
          "- Refund: system of record: the ledger.\n"
          "## Relationships\n- Customer to Refund: one-to-many.\n")


# ---------------------------------------------------------------------------
# HTML comments render as nothing and must count as nothing, everywhere; and a
# coherence link needs subject matter, not a connective.


@case("a-commented-out-entity-list-is-not-a-data-model", "datamodel", "FAIL")
def h1(root):
    # Four functions stripped comments and four did not, so this file was "the
    # absence of an artifact" to the artifacts check and "2 entities, each with
    # a system of record" to the data-model check, in the same run.
    write(root, "05-data-model.md",
          "# Data model\n\n## Entities\n\n"
          "<!-- the entity list moved to the wiki; keeping the old one here for reference\n"
          "- Customer: system of record: the CRM.\n"
          "- Refund: system of record: the ledger service.\n-->\n\n"
          "## Relationships\n- Customer to Refund: one-to-many, optional.\n")


@case("diagram-nodes-do-not-trace-to-commented-out-entities", "diagrams", "NO-DATA")
def h2(root):
    # The diagram check reported its nodes traceable to entities that do not
    # exist in the rendered document.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "<!--\n- Customer: system of record: the CRM.\n"
          "- Refund: system of record: the ledger service.\n-->\n"
          "## Relationships\n- Customer to Refund: one-to-many.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nflowchart LR\n  Customer --> Refund\n```\n")


@case("a-commented-out-alternative-is-not-an-alternative", "adr", "FAIL")
def h3(root):
    write(root, "03-adr.md",
          "# ADR\n## Criteria\nlatency, auditability\n"
          "## Rejected alternatives\n"
          "<!--\n- Synchronous call: ties checkout to ledger availability.\n"
          "- Nightly batch: misses the deadline.\n-->\n"
          "## Decision\nPublish to a queue.\n## Consequences\nOne more moving part.\n"
          "## What would flip this\nSub-second settlement becoming a requirement.\n")


@case("a-connective-is-not-shared-subject-matter", "artifacts", "FAIL")
def h4(root):
    # The docstring's own fixture: bananas, lawnmowers, a tractor fleet and
    # Mars, tied into one dossier by the word "Therefore" in each artifact.
    write(root, "00-intake.json", {"tier": "T3", "answers": TIER_ANSWERS["T3"], "override": None})
    unrelated = dict(_UNRELATED)
    unrelated["01-purpose.md"] = ("# Purpose\nBananas ripen unevenly in the shed. Therefore we "
                                  "want a ripening schedule.\n")
    unrelated["02-process.md"] = ("# Process\nThe lawnmower is pushed across the paddock. "
                                  "Therefore the grass is shortened.\n")
    unrelated["04-technology-map.md"] = ("# Technology map\nOur tractor fleet runs on diesel. "
                                         "Therefore we keep a fuel bowser on site.\n")
    unrelated["07-verification.md"] = ("# Verification\nWe will verify the Martian regolith "
                                       "sample by spectroscopy. Therefore a lander is needed.\n")
    for name, body in unrelated.items():
        write(root, name, body)


@case("a-second-connective-is-not-shared-subject-matter-either", "artifacts", "FAIL")
def h5(root):
    # The class, not the instance: any word that connects sentences rather than
    # naming anything must not tie two artifacts together.
    write(root, "00-intake.json", {"tier": "T3", "answers": TIER_ANSWERS["T3"], "override": None})
    unrelated = dict(_UNRELATED)
    unrelated["01-purpose.md"] = "# Purpose\nBananas ripen unevenly. Additionally, sheds are dark.\n"
    unrelated["02-process.md"] = "# Process\nMowing happens in spring. Additionally, blades dull.\n"
    unrelated["04-technology-map.md"] = ("# Technology map\nThe tractor burns diesel. "
                                         "Additionally, it leaks.\n")
    unrelated["07-verification.md"] = ("# Verification\nMars is verified by telescope. "
                                       "Additionally, at night.\n")
    for name, body in unrelated.items():
        write(root, name, body)


# ---------------------------------------------------------------------------
# Hyphenated and dotted node names in every dialect. Seven identifier patterns
# excluded the dominant backend naming convention, which both hid undeclared
# services (a hyphenated orphan was dropped, then "all traceable" printed) and
# rejected honest work (a correct lifecycle failed with four orphans the author
# never typed). Both directions are pinned, per dialect.

_HYPHEN_MODEL = ("# Data model\n## Entities\n"
                 "- order-service: system of record: the OMS.\n"
                 "- payment-gateway: system of record: the ledger.\n"
                 "## Relationships\n- order-service to payment-gateway: one-to-many.\n")


@case("a-hyphenated-participant-is-read-and-traced", "diagrams", "PASS")
def g1(root):
    write(root, "05-data-model.md", _HYPHEN_MODEL)
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nsequenceDiagram\n  participant order-service\n"
          "  participant payment-gateway\n  order-service->>payment-gateway: charge\n```\n")


@case("a-hyphenated-undeclared-participant-is-an-orphan", "diagrams", "FAIL")
def g2(root):
    # The hole: `participant totally-undeclared-service` was read as no node at
    # all, so a box that exists nowhere passed the gate whose one job is to
    # catch a diagram drifting from the system it claims to show.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Customer: system of record: the CRM.\n"
          "## Relationships\n- Customer to Customer: one-to-one.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nsequenceDiagram\n  participant Customer\n"
          "  participant totally-undeclared-service\n"
          "  Customer->>totally-undeclared-service: nothing anywhere declares this\n```\n")


@case("a-hyphenated-lifecycle-is-not-shredded-into-fragments", "diagrams", "PASS")
def g3(root):
    # The false rejection: `in-transit --> out-for-delivery` used to match as
    # `transit --> out`, and the author was handed four orphans they never
    # typed, with no next step but renaming a domain concept.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Shipment: system of record: the WMS.\n"
          "## Lifecycle\n- created\n- in-transit\n- out-for-delivery\n- delivered\n"
          "## Relationships\n- Shipment to Shipment: one-to-one.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nstateDiagram-v2\n  [*] --> created\n"
          "  created --> in-transit\n  in-transit --> out-for-delivery\n"
          "  out-for-delivery --> delivered\n```\n")


@case("l4s-own-worked-example-draws-in-an-erdiagram", "diagrams", "PASS")
def g4(root):
    # L4 promises `payment-token` and `pii.profile` are read rather than
    # silently dropped; an erDiagram of those two names produced "no diagram
    # node could be read out of them".
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "- payment-token: system of record: the vault.\n"
          "- pii.profile: system of record: the identity service.\n"
          "## Relationships\n- payment-token to pii.profile: one-to-one.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nerDiagram\n  payment-token ||--o| pii.profile : masks\n```\n")


@case("a-hyphenated-class-is-not-truncated-to-a-prefix", "diagrams", "FAIL")
def g5(root):
    # classDiagram manufactured a node called `feed` out of `class feed-poller`
    # and then traced or orphaned a name the author never wrote. The FAIL must
    # name the full identifier.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Customer: system of record: the CRM.\n"
          "## Relationships\n- Customer to Customer: one-to-one.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nclassDiagram\n  class feed-poller\n```\n")


@case("the-truncated-class-fail-names-the-full-identifier", "evidence", "full-name")
def g6(root):
    g5(root)
    line = gate_line(root, "diagrams")
    if line.split()[1:2] != ["FAIL"]:
        return line
    return "full-name" if "feed-poller" in line else line


@case("mindmap-children-are-read-not-dropped", "diagrams", "FAIL")
def g7(root):
    # Two undeclared children sat under "1 diagram node(s) in mindmap, all
    # traceable": a half-parse, which L5 says a dialect must not get.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Customer: system of record: the CRM.\n"
          "## Relationships\n- Customer to Customer: one-to-one.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nmindmap\n  root((Customer))\n"
          "    UndeclaredThingOne\n    UndeclaredThingTwo\n```\n")


@case("a-declared-mindmap-still-passes", "diagrams", "PASS")
def g8(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- Customer: system of record: the CRM.\n"
          "- Order: system of record: the OMS.\n"
          "## Relationships\n- Customer to Order: one-to-many.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nmindmap\n  root((Customer))\n    Order\n```\n")


# ---------------------------------------------------------------------------
# Shared rules adopted at every call site: the dedupe rule in the two gates that
# never had it, units on the drift comparison, the reviewability floor on lint
# exemptions, one marker never waiving two swallows, and ages nobody computed.


@case("one-check-written-five-times-is-one-check", "evidence", "counted-once")
def u1(root):
    chk = {"name": "reconcile", "exit_code": 0, "duration_ms": 812}
    write(root, "ran-receipt.json", {"checks": [dict(chk) for _ in range(5)]})
    line = gate_line(root, "ran")
    if line.split()[1:2] != ["PASS"]:
        return line
    return ("counted-once" if "1 recorded check(s)" in line and "4 identical" in line else line)


@case("one-receipt-copied-into-two-directories-is-one-rehearsal", "evidence", "counted-once")
def u2(root):
    receipt = {"forward": {"ran_against_restore": True},
               "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job-8842"},
               "row_counts": {"before": 100, "after_reverse": 100}}
    write(root, "a/migration-receipt.json", receipt)
    write(root, "b/migration-receipt.json", receipt)
    line = gate_line(root, "migration")
    if line.split()[1:2] != ["PASS"]:
        return line
    return ("counted-once" if "1 receipt(s)" in line and "1 identical receipt(s)" in line else line)


@case("a-rate-and-a-currency-amount-are-not-zero-drift", "numbers", "FAIL")
def u3(root):
    # numeric() strips "%" and "$" as formatting, so "50%" and "$50" compared
    # equal and bought the strongest sentence this gate prints.
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "refund rate", "snapshot_id": "snap-1",
        "query": "SELECT refunds FROM daily", "second_derivation": "SELECT paid FROM ledger",
        "rerun": {"ran": True, "primary": "50%", "secondary": "$50"}}]})


@case("a-percentage-is-not-a-row-count", "migration", "FAIL")
def u4(root):
    write(root, "migration-receipt.json", {
        "forward": {"ran_against_restore": True},
        "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job-8842"},
        "row_counts": {"before": "50%", "after_reverse": "50%"}})


@case("a-zero-width-space-is-not-a-second-derivation", "numbers", "FAIL")
def u5(root):
    # str.split() does not split on U+200B, so one invisible character made a
    # copy-paste of the first query an "independent second derivation".
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": "snap-1",
        "query": "SELECT SUM(amount) FROM orders",
        "second_derivation": "SELECT SUM(amount)\u200b FROM orders",
        "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]})


@case("a-boolean-snapshot-id-pins-nothing", "numbers", "FAIL")
def u6(root):
    # answered() keeps False as an answer on purpose (a zero row count is an
    # answer), so `"snapshot_id": false` read as a pinned read.
    write(root, "numbers-manifest.json", {"figures": [{
        "label": "gmv", "snapshot_id": False,
        "query": "SELECT SUM(amount) FROM orders",
        "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
        "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]})


@case("snapshot-reuse-is-disclosed-across-case", "evidence", "disclosed")
def u7(root):
    # The reuse disclosure compared raw ids while every other comparison folds,
    # so ids differing only in case lost the disclosure and the PASS read as two
    # independent pins.
    write(root, "numbers-manifest.json", {"figures": [
        {"label": "gmv", "snapshot_id": "SNAP-1", "query": "SELECT SUM(amount) FROM orders",
         "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
         "rerun": {"ran": True, "primary": 17570, "secondary": 17570}},
        {"label": "aov", "snapshot_id": "snap-1", "query": "SELECT AVG(amount) FROM orders",
         "second_derivation": "SELECT SUM(amount)/COUNT(*) FROM orders",
         "rerun": {"ran": True, "primary": 88, "secondary": 88}}]})
    line = gate_line(root, "numbers")
    if line.split()[1:2] != ["PASS"]:
        return line
    return "disclosed" if "share a snapshot id" in line else line


@case("a-directory-named-after-a-gate-is-refused-not-eaten", "guard", "refused")
def u8(root):
    os.makedirs(os.path.join(root, "numbers"))
    out = subprocess.run([sys.executable, GATE, "numbers"], capture_output=True, text=True,
                         cwd=root)
    return ("refused" if out.returncode == 1 and "both a gate name and a directory" in out.stdout
            else "exit %d: %s" % (out.returncode, out.stdout.strip()[:80]))


@case("two-gate-roots-are-refused-not-last-wins", "guard", "refused")
def u9(root):
    a, b = os.path.join(root, "a"), os.path.join(root, "b")
    os.makedirs(a), os.makedirs(b)
    out = subprocess.run([sys.executable, GATE, a, b], capture_output=True, text=True)
    return ("refused" if out.returncode == 1 and "one directory at a time" in out.stdout
            else "exit %d: %s" % (out.returncode, out.stdout.strip()[:80]))


@case("two-design-roots-are-refused-not-last-wins", "guard", "refused")
def u10(root):
    a, b = os.path.join(root, "a"), os.path.join(root, "b")
    os.makedirs(a), os.makedirs(b)
    out = subprocess.run([sys.executable, DESIGN, a, b], capture_output=True, text=True)
    return ("refused" if out.returncode == 1 and "one directory at a time" in out.stdout
            else "exit %d: %s" % (out.returncode, out.stdout.strip()[:80]))


@case("two-lint-roots-are-refused-not-last-wins", "lints", "FAIL")
def u11(root):
    a, b = os.path.join(root, "a"), os.path.join(root, "b")
    os.makedirs(a), os.makedirs(b)
    write(root, "a/evil.py", "try:\n    f()\nexcept:\n    pass\n")  # sbe: allow-silent this is the lint FIXTURE: the swallow is the defect under test, written into a temp file, never executed here
    write(root, "b/ok.py", "def f():\n    return 1\n")
    return run_score_lints([a, b])


@case("an-exemption-reason-of-x-waives-nothing", "lints", "FAIL")
def u12(root):
    write(root, "bad.py", "try:\n    f()\nexcept:  # sbe" + ": allow-silent x\n    pass\n")  # sbe: allow-silent this is the lint FIXTURE: the swallow is the defect under test, written into a temp file, never executed here
    return run_score_lints([root])


@case("the-marker-pasted-as-its-own-reason-waives-nothing", "lints", "FAIL")
def u13(root):
    write(root, "bad.py", "try:\n    f()\nexcept:  # sbe" + ": allow-silent sbe" + ": allow-silent\n    pass\n")  # sbe: allow-silent this is the lint FIXTURE: the swallow is the defect under test, written into a temp file, never executed here
    return run_score_lints([root])


@case("one-marker-does-not-waive-a-second-unrelated-hit", "lints", "FAIL")
def u14(root):
    # The upsert pattern crosses newlines, so its span enclosed the except
    # block, and a reason written about the except waived the upsert too.
    write(root, "t.py",  # sbe: allow-silent this is the lint FIXTURE: both swallows are the defects under test, written into a temp file, never executed here
          'UPSERT = """\nINSERT INTO ledger (id, amount) VALUES (%s, %s)\nON CONFLICT (id)\n"""\n'
          'try:\n    load()\nexcept:  # sbe: allow-silent retry loop above already logs the failure\n'
          '    pass\nMORE = """\nDO NOTHING\n"""\n')
    return run_score_lints([root])


@case("unreadable-timestamps-never-fall-out-of-the-window", "score", "FAIL")
def u15(root):
    # ctx.recent mapped an unreadable timestamp to the sentinel 99, meaning
    # "old", so rows nothing had measured silently left the 7-day window and
    # "1/1 sessions >= 90%; below floor: none" printed over 99 unmeasured rows.
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = [json.dumps({"schema": 2, "session_id": "good", "ts": now,
                        "cache_read": 95, "cache_write": 5})]
    rows += [json.dumps({"schema": 2, "session_id": "s%d" % i, "ts": "not-a-timestamp",
                         "cache_read": 1, "cache_write": 99}) for i in range(3)]
    return score_check("cache-economy", _ledger(root, "\n".join(rows) + "\n"))


@case("sessions-without-cache-fields-are-disclosed", "evidence", "disclosed")
def u16(root):
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = [json.dumps({"schema": 2, "session_id": "good", "ts": now,
                        "cache_read": 95, "cache_write": 5}),
            json.dumps({"schema": 2, "session_id": "bare", "ts": now})]
    _ledger(root, "\n".join(rows) + "\n")
    e = dict(os.environ)
    e.update({"BROTHERSBE_VAULT": root, "BROTHERSBE_REGISTRIES": "", "SBE_LINT_ROOT": ""})
    out = subprocess.run([sys.executable, SCORE], capture_output=True, text=True, env=e)
    line = next((l for l in out.stdout.splitlines() if l.startswith("cache-economy")), "")
    return "disclosed" if "carry no cache fields" in line else line or "no-line"


@case("five-tbd-seals-are-zero-sealed-predictions", "score", "NO-DATA")
def u17(root):
    write(root, "50-Reference/operator-model.md",
          "# Operator model\n## Prediction ledger\n"
          "date | prediction | seal | scored on | hit\n"
          + "".join("2026-07-0%d | the queue depth stays under 1k | TBD | review | yes\n" % i
                    for i in range(1, 6)))
    return score_check("prediction-seals", root)


@case("one-prediction-on-five-dates-is-one-prediction", "score", "FAIL")
def u18(root):
    # The dedupe keyed on the whole row including the date, so it could never
    # fold the rows its own docstring says it exists to fold.
    write(root, "50-Reference/operator-model.md",
          "# Operator model\n## Prediction ledger\n"
          "date | prediction | seal | scored on | hit\n"
          + "".join("2026-07-0%d | the queue depth stays under 1k | seal-%d | review | yes\n"
                    % (i, i) for i in range(1, 6)))
    return score_check("prediction-seals", root)


@case("six-timestamps-of-one-rating-are-one-rating", "score", "FAIL")
def u19(root):
    # The writer stamps a fresh timestamp on every row, so the whole-row dedupe
    # was structurally unreachable: six copies of one 5/5 rating cleared the
    # "6 distinct ratings" threshold.
    rows = [json.dumps({"ts": "2026-07-25T10:00:0%d.%06dZ" % (i, i), "score": 5,
                        "task": "ship the refund gate", "note": "solid"}) for i in range(6)]
    write(root, "99-System/telemetry/ratings.jsonl", "\n".join(rows) + "\n")
    return score_check("felt-outcome-ratings", root)


@case("a-trailing-period-is-not-a-second-alternative", "adr", "FAIL")
def u20(root):
    # distinct() used the weaker of the two reductions, so one alternative
    # written twice, differing by case and one period, counted as "2 distinct
    # rejected alternatives".
    write(root, "03-adr.md",
          "# ADR\n## Criteria\nlatency, freshness\n## Rejected alternatives\n"
          "- Nightly batch reconciliation, it misses the deadline\n"
          "- nightly batch reconciliation, it misses the deadline.\n"
          "## Decision\nPublish to a queue.\n## Consequences\nOne more moving part.\n"
          "## What would flip this\nSub-second freshness becomes a requirement.\n")


# ---------------------------------------------------------------------------
# The decision tool: ghost votes, silent ties, swallowed arguments.

DECIDE = os.path.join(HERE, "..", "tools", "sbe_decide.py")


@case("a-vote-for-a-ghost-option-is-reported-not-counted", "decide", "reported")
def q1(root):
    table = {"options": ["alpha", "beta"], "flip": "flip line",
             "criteria": [{"name": "c1", "kind": "choice", "note": "", "scores": {"yes": ["gamma"]}},
                          {"name": "c2", "kind": "choice", "note": "", "scores": {"yes": ["alpha"]}}]}
    r = _decide.recommend(table, {"c1": "yes", "c2": "yes"})
    ghost_named = any("gamma" in u and "not among this table's options" in u
                      for u in r["unrecognized"])
    return ("reported" if ghost_named and r["evidence"] == 1 else
            "evidence=%d unrecognized=%r" % (r["evidence"], r["unrecognized"]))


@case("an-exact-tie-is-disclosed-not-decided-in-silence", "decide", "disclosed")
def q2(root):
    table = {"options": ["alpha", "beta"], "flip": "flip line",
             "criteria": [{"name": "c1", "kind": "choice", "note": "",
                           "scores": {"yes": ["alpha", "beta"]}}]}
    r = _decide.recommend(table, {"c1": "yes"})
    return "disclosed" if r["tie"] == ["alpha", "beta"] else "tie=%r" % r["tie"]


@case("key-value-answers-are-read-not-swallowed", "guard", "answered")
def q3(root):
    # Every argument after the table name used to be discarded without a word,
    # and the tool then asked its questions interactively: key=value is the
    # first thing an engineer or an agent tries.
    out = subprocess.run([sys.executable, DECIDE, "shape", "deploying_teams=1",
                          "consistency=strong", "ops_maturity=low", "failure_isolation=low"],
                         input="", capture_output=True, text=True, timeout=20)
    return ("answered" if out.returncode == 0 and "Recommendation: modular monolith" in out.stdout
            else "exit %d: %s" % (out.returncode, out.stdout.strip()[:80]))


@case("an-argument-the-table-cannot-read-is-refused-by-name", "guard", "refused")
def q4(root):
    out = subprocess.run([sys.executable, DECIDE, "shape", "THIS_IS_GARBAGE=999"],
                         input="", capture_output=True, text=True, timeout=20)
    return ("refused" if out.returncode == 1 and "THIS_IS_GARBAGE" in out.stdout
            else "exit %d: %s" % (out.returncode, out.stdout.strip()[:80]))


@case("a-closed-stdin-is-a-named-refusal-not-a-repr", "guard", "named")
def q5(root):
    out = subprocess.run([sys.executable, DECIDE, "shape"], input="",
                         capture_output=True, text=True, timeout=20)
    return ("named" if out.returncode == 1 and "stdin closed before" in out.stdout
            and "EOFError" not in out.stdout
            else "exit %d: %s" % (out.returncode, out.stdout.strip()[:120]))


# ---------------------------------------------------------------------------
# Honest forms a competent engineer writes, each previously refused.


@case("a-bold-entity-name-is-an-entity-name", "datamodel", "PASS")
def f1(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "- **Order**: a customer order. system of record: oms\n"
          "- **OrderLine**: a line on an order. system of record: oms\n"
          "## Relationships\n- Order one-to-many OrderLine\n")


@case("a-bold-entity-in-a-table-is-an-entity", "datamodel", "PASS")
def f2(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "| Entity | Meaning | System of record |\n| --- | --- | --- |\n"
          "| **Order** | a customer order | oms |\n"
          "| **OrderLine** | a line on an order | oms |\n"
          "## Relationships\n- Order one-to-many OrderLine\n")


@case("an-entity-bullet-without-a-colon-still-names-its-owner", "datamodel", "PASS")
def f3(root):
    # The FAIL used to quote a line containing "system of record" in the same
    # sentence it claimed named none, because with no colon the whole sentence
    # became the entity NAME.
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "- Order. The OMS is the system of record.\n"
          "- OrderLine. The OMS is the system of record.\n"
          "## Relationships\n- Order one-to-many OrderLine\n")


@case("adr-alternatives-as-a-comparison-table-count", "adr", "PASS")
def f4(root):
    write(root, "03-adr.md",
          "# ADR\n## Criteria\nlatency, auditability\n"
          "## Alternatives considered\n"
          "| Option | Verdict | Why |\n| --- | --- | --- |\n"
          "| Synchronous ledger call | rejected | ties checkout to ledger uptime |\n"
          "| Nightly batch | rejected | misses the one business day deadline |\n"
          "| Event queue | chosen | decouples checkout from settlement |\n"
          "## Decision\nPublish refund events to a queue.\n"
          "## Consequences\nOne more moving part.\n"
          "## What would flip this\nSub-second settlement becoming a requirement.\n")


@case("a-trade-offs-considered-heading-is-an-alternatives-heading", "adr", "PASS")
def f5(root):
    write(root, "03-adr.md",
          "# ADR\n## Criteria\nlatency, auditability\n"
          "## Trade-offs considered\n"
          "- Synchronous ledger call: ties checkout to ledger uptime.\n"
          "- Nightly batch: misses the deadline.\n"
          "## Decision\nPublish to a queue.\n## Consequences\nOne more moving part.\n"
          "## What would flip this\nSub-second settlement becoming a requirement.\n")


@case("cardinality-written-in-prose-is-cardinality", "datamodel", "PASS")
def f6(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "- Order: system of record: oms\n- OrderLine: system of record: oms\n"
          "## Relationships\n"
          "- An Order has many OrderLines, and every OrderLine belongs to exactly one Order.\n")


@case("relationships-as-an-erdiagram-are-relationships", "datamodel", "PASS")
def f7(root):
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n"
          "- Order: system of record: oms\n- OrderLine: system of record: oms\n"
          "## Relationships\n```mermaid\nerDiagram\n  Order ||--o{ OrderLine : contains\n```\n")


@case("a-technology-map-written-as-bullets-declares-components", "diagrams", "PASS")
def f8(root):
    # L5's INPUTS promises component bullets "in either file"; only
    # 06-diagrams.md was read, so an honest bulleted technology map produced
    # orphans and the law overclaimed against its own tool.
    write(root, "04-technology-map.md",
          "# Technology map\n## Components\n"
          "- feedqueue: SQS, owned by platform, fails on poison messages, recovers via DLQ\n"
          "- ingestworker: Python on ECS, owned by supply, fails on parse error, recovers by replay\n")
    write(root, "05-data-model.md",
          "# Data model\n## Entities\n- FeedFile: system of record: the landing bucket.\n"
          "## Relationships\n- FeedFile to FeedFile: one-to-one.\n")
    write(root, "06-diagrams.md",
          "# Diagrams\n```mermaid\nflowchart LR\n  feedqueue --> ingestworker\n```\n")


@case("an-asterisk-bullet-fence-line-is-a-fence-line", "score", "FAIL")
def f9(root):
    # Markdown treats `*` and `-` as the same bullet; the fence checks read only
    # `- `, so an asterisk-bulleted registry got permanently green fence
    # discipline over untagged live fences.
    write(root, "reg/STATE.md",
          "# State\n## Fences\n* agent: builder | objective: ship the refund gate | open\n")
    return score_check("budget-vs-tier", root,
                       env={"BROTHERSBE_REGISTRIES": os.path.join(root, "reg", "*.md")})


@case("a-self-declared-component-trace-is-disclosed", "evidence", "disclosed")
def f10(root):
    # One file declaring its own nodes as Components bullets is declaration and
    # use in one place; still accepted, now said out loud instead of counted
    # silently inside "all traceable".
    write(root, "06-diagrams.md",
          "# Diagrams\n## Components\n- Alpha\n- Beta\n## Context\n"
          "```mermaid\nflowchart LR\n  Alpha --> Beta\n```\n")
    line = gate_line(root, "diagrams")
    if line.split()[1:2] != ["PASS"]:
        return line
    return "disclosed" if "declared in this artifact itself" in line else line


def main():
    passed = failed = 0
    for name, klass, expect, fn in CASES:
        with tempfile.TemporaryDirectory() as d:
            try:
                if klass in ("tier", "decide", "sig", "lints", "score", "designrun",
                             "gaterun", "evidence", "guard", "docs"):
                    verdict = fn(d)
                else:
                    fn(d)
                    verdict = run_gate(d, klass)
            except Exception as e:
                verdict = "ERROR:%r" % e
        ok = verdict == expect
        passed += ok
        failed += not ok
        print("  %-38s want=%-8s got=%-8s %s" % (name, expect, verdict, "ok" if ok else "REGRESSION"))
    print("\n%d evals: %d passed, %d regressions." % (len(CASES), passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
