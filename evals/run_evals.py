#!/usr/bin/env python3
"""BrotherSBE regression evals: each is a real failure class as a fixture, a
planted defect, and an assertion that the corresponding gate CATCHES it. A
release is blocked (exit nonzero) if any eval regresses. This is the mechanism
behind the claim that BrotherSBE is proven in traceable ways: the gates are
tested against the exact defects the operating record produced.

Every fixture is generalized: no client, employer, or private project appears.
"""
import json, os, sys, tempfile, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "..", "tools", "sbe_gate.py")


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


def _approval_with_sig(root, sig):
    original = _gate.git_trailers
    _gate.git_trailers = lambda r: ("change\n\nApproved-by: Someone", sig)
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


@case("valid-untrusted-signature-U-approval-passes", "sig", "PASS")
def c13g2(root):
    return _approval_with_sig(root, "U")


@case("bad-signature-B-is-not-an-approval", "sig", "FAIL")
def c13h(root):
    return _approval_with_sig(root, "B")


@case("expired-signature-X-is-not-an-approval", "sig", "FAIL")
def c13h2(root):
    return _approval_with_sig(root, "X")


@case("unsigned-commit-N-is-not-an-approval", "sig", "FAIL")
def c13h3(root):
    return _approval_with_sig(root, "N")


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
    write(root, "design/legacy/.sbe-exempt", "closed two years ago, kept for history\n")
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
          "def a():\n    try:\n        f()\n    except Exception:\n        pass  # sbe: allow-silent fixture\n")
    return score_check("silent-failure-lints", root, args=(src,))


@case("an-exemption-on-the-pass-line-is-honoured", "score", "PASS")
def sc9(root):
    src = os.path.join(root, "src")
    write(root, "src/swallowy.py",
          "def a():\n    try:\n        f()\n    except Exception:\n        pass  # sbe: allow-silent fixture\n")
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


@case("an-exemption-is-reported-as-a-waiver-not-a-pass", "designrun", "waived")
def v30(root):
    write(root, "design/legacy/00-intake.json", {"tier": "T2", "answers": T2_ANSWERS, "override": None})
    write(root, "design/legacy/.sbe-exempt", "closed two years ago, kept for history\n")
    e = dict(os.environ)
    e["SBE_DOSSIER_ROOT"] = ""
    out = subprocess.run([sys.executable, DESIGN, root], capture_output=True, text=True, env=e)
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "dossier" and parts[1] == "WAIVED":
            return "waived" if "waives artifacts" in line else "waiver-line-does-not-name-the-checks"
    return "no-waiver-line"


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
DOSSIER = {
    "01-purpose.md": PURPOSE,
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


# The counts printed in the shipped docs, checked against the suites that print
# them. Three docs carried "70 evals: 70 passed" through a wave that took the
# real number to 110, and the doc whose whole job is "prove it works in 60
# seconds" was one of them. A number in a doc that nothing recomputes is a stale
# evidence string with a longer half-life.
SHIPPED_DOCS = ("README.md", "docs/SETUP.md", "docs/HOW-IT-WORKS.md", "PUBLISH-CHECKLIST.md",
                "docs/guides/01-quickstart.md", "docs/guides/02-the-gates-in-practice.md",
                "docs/guides/03-the-dossier.md", "docs/guides/04-teams-and-evolution.md",
                "docs/guides/05-a-worked-engagement.md", "evals/README.md", "DIGEST.md",
                "SKILL.md", "PARITY.md", "PRACTICES.md", "RUBRIC.md", "STATE.md")
_REPO = os.path.abspath(os.path.join(HERE, ".."))


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
    checks, regs, scen = meta.counts()
    wrong = []
    for rel in SHIPPED_DOCS:
        p = os.path.join(_REPO, rel)
        if not os.path.isfile(p):
            continue
        for m in _re.finditer(r"(\d+) checks discovered from (\d+) registries in (\d+) module\(s\), "
                              r"(\d+) scenarios run", open(p, errors="replace").read()):
            got = (int(m.group(1)), int(m.group(2)), int(m.group(4)))
            if got != (checks, regs, scen):
                wrong.append("%s: %r but the meta-test walks %d checks, %d registries, %d scenarios"
                             % (rel, m.group(0), checks, regs, scen))
    return "consistent" if not wrong else "; ".join(wrong[:4])


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
