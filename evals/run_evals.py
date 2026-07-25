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


def main():
    passed = failed = 0
    for name, klass, expect, fn in CASES:
        with tempfile.TemporaryDirectory() as d:
            try:
                if klass in ("tier", "decide", "sig", "lints"):
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
