#!/usr/bin/env python3
"""BrotherSBE design checks: the dossier's completeness rules, made mechanical.

Same contract as sbe_gate.py: one function per class returning (verdict, evidence),
advisory by default, --strict exits nonzero so CI can block. A design artifact that
fails its rule is not approved, and the failure names the missing field.

Where it looks. A directory holding a dossier (00-intake.json, or any of the seven
artifact files) is checked directly. Anything else is treated as a search root and
walked for directories containing 00-intake.json, because the documented layout puts
dossiers in `design/<project>/` while CI runs from the repository root: a checker
that only ever opened `<root>/00-intake.json` reported NO-DATA with a full dossier
two directories away, and passed. Set SBE_DOSSIER_ROOT when a repository is supposed
to carry a dossier, and a search that finds none there becomes a FAIL instead of an
absence.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbe_intake import required_artifacts, compute_tier, TIERS

ARTIFACT_FILES = {
    "01": "01-purpose.md", "02": "02-process.md", "03": "03-adr.md",
    "04": "04-technology-map.md", "05": "05-data-model.md",
    "06": "06-diagrams.md", "07": "07-verification.md",
}
CARDINALITIES = ("one-to-one", "one-to-many", "many-to-one", "many-to-many")
INTAKE = "00-intake.json"
# Every shipped template carries this marker. Deleting it is part of filling the
# section in, so a dossier copied wholesale and never edited fails with the
# artifact named, rather than clearing the design gate on someone else's example.
UNFILLED_MARKER = "SBE-TEMPLATE-UNFILLED"
SKIP_DIRS = (".git", "node_modules", "__pycache__", ".venv", "venv", "vendor")


def read(root, name):
    path = os.path.join(root, name)
    try:
        return open(path, errors="replace").read()
    except OSError:
        return None


def check_artifacts(root):
    intake = read(root, INTAKE)
    if intake is None:
        return "NO-DATA", "no 00-intake.json; run sbe_intake.py to compute the tier"
    try:
        data = json.loads(intake)
    except ValueError:
        return "FAIL", "00-intake.json is not valid JSON"
    if not isinstance(data, dict):
        return "FAIL", "00-intake.json is not a JSON object"
    tier = data.get("tier")
    if tier not in TIERS:
        return "NO-DATA", "00-intake.json has no valid tier (got %r); expected one of %s" % (tier, ", ".join(TIERS))
    # The tier is RE-DERIVED from the answers stored beside it, never trusted as
    # written. Trusting the field made the whole dossier requirement two keystrokes
    # away: editing "T3" to "T0" cleared every artifact, silently, with the gate
    # still printing PASS. L15's rule that a tier moved with a null reason is an
    # edit and not an override is enforced exactly here.
    answers = data.get("answers")
    if not isinstance(answers, dict) or not answers:
        return "NO-DATA", ("00-intake.json records tier %s but carries no answers, so the tier cannot be re-derived; "
                           "a tier nothing can recompute is a typed claim, not a computed one (rerun sbe_intake.py)" % tier)
    computed = compute_tier(answers)
    label = ""
    if tier != computed:
        reason = data.get("override_reason")
        if isinstance(reason, str) and reason.strip():
            label = "; declared override to %s from computed %s, reason: %s" % (tier, computed, reason.strip())
        else:
            return "FAIL", ("00-intake.json says tier %s but its own answers compute %s, and no override_reason is recorded; "
                            "a tier moved with a null reason is an edit, not an override (L15)" % (tier, computed))
    need = required_artifacts(tier)
    missing = [ARTIFACT_FILES[n] for n in need if read(root, ARTIFACT_FILES[n]) is None]
    if missing:
        return "FAIL", "tier %s requires %s; missing: %s" % (tier, ", ".join(need), ", ".join(missing))
    return "PASS", "tier %s: every required artifact present%s" % (tier, label)


def check_placeholder(root):
    """A copied, unedited template is not a design. Reject the shipped marker."""
    present = {}
    for name in ARTIFACT_FILES.values():
        t = read(root, name)
        if t is not None:
            present[name] = t
    if not present:
        return "NO-DATA", "no dossier artifacts here, so nothing to check for unfilled template sections"
    unfilled = sorted(n for n, t in present.items() if UNFILLED_MARKER in t)
    if unfilled:
        return "FAIL", ("still the shipped template, unedited: %s; each carries its %s marker, which the template says to "
                        "delete once the section is your own design" % (", ".join(unfilled), UNFILLED_MARKER))
    return "PASS", "%d artifact(s) present, none still carrying an unfilled-template marker" % len(present)


_HEADING = re.compile(r"^(#+)\s*(.*)$")
_REJECTED_HEADING = re.compile(r"(?i)^rejected\b")
_BULLET = re.compile(r"^\s*[-*]\s+(.*\S)\s*$")


def _rejected_alternatives(t):
    """Count rejected ALTERNATIVES, not headings that contain the word.

    Counting `^#+\\s*rejected` headings got both halves wrong: an ADR listing two
    real alternatives as bullets under one "Rejected alternatives" heading failed,
    while two empty "## Rejected" headings with nothing under either passed. That
    inverts the incentive the rule exists to create, teaching an author to add
    headings rather than alternatives. An alternative counts here only if it
    carries at least one non-empty line of its own: bullets under a rejected
    heading count individually, and a heading whose body is prose counts once.
    """
    lines = t.splitlines()
    found = []
    in_rejected = False
    body, bullets = [], []

    def close():
        if not in_rejected:
            return
        if bullets:
            found.extend(bullets)
        elif any(l.strip() for l in body):
            found.append(" ".join(l.strip() for l in body if l.strip())[:60])

    for line in lines:
        h = _HEADING.match(line)
        if h:
            close()
            body, bullets = [], []
            in_rejected = bool(_REJECTED_HEADING.match(h.group(2).strip()))
            continue
        if not in_rejected:
            continue
        b = _BULLET.match(line)
        if b:
            bullets.append(b.group(1)[:60])
        else:
            body.append(line)
    close()
    return found


def check_adr(root):
    t = read(root, ARTIFACT_FILES["03"])
    if t is None:
        return "NO-DATA", "no 03-adr.md in this dossier"
    problems = []
    rejected = len(_rejected_alternatives(t))
    if rejected < 2:
        problems.append("only %d rejected alternative(s); an ADR needs at least 2, each with at least one line saying why it lost "
                        "(an empty heading is not an alternative)" % rejected)
    if not re.search(r"(?im)^#+\s*criteria", t):
        problems.append("no Criteria section naming what decided it")
    if not re.search(r"(?im)^#+\s*decision", t):
        problems.append("no Decision section")
    if not re.search(r"(?im)^#+\s*consequences", t):
        problems.append("no Consequences section")
    if not re.search(r"(?im)what would flip", t):
        problems.append("no 'What would flip this' section; an ADR without it is a tombstone")
    if problems:
        return "FAIL", "; ".join(problems)
    return "PASS", "%d alternatives rejected, criteria, decision, consequences, and flip condition present" % rejected


def _entities(t):
    out = {}
    body = re.split(r"(?im)^#+\s*relationships", t)[0]
    for line in body.splitlines():
        m = re.match(r"\s*[-*]\s*([A-Za-z_][\w ]*?)\s*(?::(.*))?$", line)
        if m:
            out[m.group(1).strip()] = (m.group(2) or "").strip()
    return out


# "system of record" followed by a value, with the separator optional so both
# "system of record: the CRM" and "system of record the CRM" are read. Substring
# matching alone let "no system of record known yet" through, because the phrase
# was present; the value is what the rule is actually about.
_SOR = re.compile(r"(?i)system of record\s*[:=]?\s*(.+)")
_NO_SOR = re.compile(r"(?i)\bno\s+system\s+of\s+record\b")
# Values that name the absence of an answer rather than an answer.
_EMPTY_VALUES = ("tbd", "tba", "todo", "none", "unknown", "n/a", "na", "?", "??",
                 "not decided", "undecided", "not known", "unclear", "to be decided")
# A cardinality must stand as its own token. Without the guards, "one-to-many-ish"
# satisfied a substring test, so a sentence explicitly saying the cardinality was
# undecided cleared the gate that exists to decide it.
_CARDINALITY = re.compile(r"(?i)(?<![\w-])(%s)(?![\w-])" % "|".join(CARDINALITIES))


def _stated_value(v):
    v = v.strip().strip(".;,").strip()
    v = re.sub(r"^(?:is|was|are)\s+", "", v, flags=re.I).strip()
    return "" if v.lower() in _EMPTY_VALUES else v


def check_data_model(root):
    t = read(root, ARTIFACT_FILES["05"])
    if t is None:
        return "NO-DATA", "no 05-data-model.md in this dossier"
    problems = []
    ents = _entities(t)
    if not ents:
        problems.append("no entity bullets found above the Relationships heading")
    for name, meta in ents.items():
        m = _SOR.search(meta)
        if not m or _NO_SOR.search(meta):
            problems.append("entity '%s' has no system of record" % name)
        elif not _stated_value(m.group(1)):
            problems.append("entity '%s' names a system of record with no value (%r); an undecided source is not a source"
                            % (name, m.group(1).strip()[:24]))
    rel_block = re.split(r"(?im)^#+\s*relationships", t)
    if len(rel_block) > 1:
        for line in rel_block[1].splitlines():
            if re.match(r"\s*[-*]\s+", line) and not _CARDINALITY.search(line):
                problems.append("relationship '%s' has no cardinality" % line.strip()[:48])
    if problems:
        return "FAIL", "; ".join(problems[:6])
    return "PASS", "%d entities, each with a system of record; every relationship carries cardinality" % len(ents)


DIAGRAM_KEYWORDS = {"flowchart", "graph", "sequenceDiagram", "erDiagram", "LR", "TD", "RL", "BT"}

# A node name followed by a shape wrapper (square, round, curly, or the double-round
# "circle" form) or by a bare "--"/"-->" edge. Order matters: the double-paren
# alternative must come before the single-paren one or it never gets a chance to match.
_SHAPE_OR_EDGE = r"\[[^\]\n]*\]|\(\([^)\n]*\)\)|\([^)\n]*\)|\{[^}\n]*\}|--"
_NODE_SOURCE = re.compile(r"([A-Za-z_]\w*)\s*(?:%s)" % _SHAPE_OR_EDGE)
_NODE_DEST = re.compile(r"-->\s*(?:\|[^|]*\|\s*)?([A-Za-z_]\w*)")
# erDiagram relationship line: ENTITY <cardinality> ENTITY : label
# Cardinality tokens (||--o{, }o--||, ||--||, }|..|{, ...) are built only from
# the characters | o { } . and dash, so a run of those between two identifiers,
# ending in a colon, is an entity-relationship line, not a flowchart arrow.
_ER_LINE = re.compile(r"([A-Za-z_]\w*)\s+[|o{}.\-]+\s+([A-Za-z_]\w*)\s*:")


def _diagram_nodes(t):
    # HTML comments are not diagram source. Left in, the "-->" that closes one
    # reads as a Mermaid edge and invents a node out of the next word.
    t = re.sub(r"(?s)<!--.*?-->", "", t)
    nodes = set()
    for m in _NODE_SOURCE.finditer(t):
        nodes.add(m.group(1))
    for m in _NODE_DEST.finditer(t):
        nodes.add(m.group(1))
    for m in _ER_LINE.finditer(t):
        nodes.add(m.group(1))
        nodes.add(m.group(2))
    return nodes - DIAGRAM_KEYWORDS


def check_diagrams(root):
    t = read(root, ARTIFACT_FILES["06"])
    if t is None:
        return "NO-DATA", "no 06-diagrams.md in this dossier"
    nodes = _diagram_nodes(t)
    if not nodes:
        return "FAIL", "no diagram nodes found; a diagram artifact with no diagram is a defect"
    model = read(root, ARTIFACT_FILES["05"])
    known = set(_entities(model)) if model is not None else set()
    if not known:
        # Without a data model there is nothing to trace against. Reporting PASS
        # here would be the exact defect L5 exists to catch: an empty known set
        # makes every invented node look traceable.
        return "NO-DATA", ("%d diagram node(s), but tracing cannot be verified without "
                           "entities in %s" % (len(nodes), ARTIFACT_FILES["05"]))
    orphans = sorted(n for n in nodes if n not in known)
    if orphans:
        return "FAIL", "diagram element(s) appear nowhere else in the dossier: %s" % ", ".join(orphans[:6])
    return "PASS", "%d diagram node(s), all traceable to dossier artifacts" % len(nodes)


CHECKS = {"artifacts": check_artifacts, "adr": check_adr,
          "datamodel": check_data_model, "diagrams": check_diagrams,
          "placeholder": check_placeholder}


def is_dossier(d):
    """A directory holding an intake file or any dossier artifact."""
    try:
        fns = set(os.listdir(d))
    except OSError:
        return False
    return INTAKE in fns or bool(fns & set(ARTIFACT_FILES.values()))


def find_dossiers(root):
    """Walk for directories carrying an intake file. The intake is the anchor:
    without it there is no tier, and without a tier there is nothing to require."""
    hits = []
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
        if INTAKE in fns:
            hits.append(dp)
    return hits


def main():
    strict = "--strict" in sys.argv
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    root = "."
    which = list(CHECKS)
    for a in argv:
        if a in CHECKS:
            which = [a]
        elif os.path.isdir(a):
            root = a
        else:
            print("sbe_design: %r is neither a check name (%s) nor a directory."
                  % (a, ", ".join(CHECKS)))
            sys.exit(1)
    # SBE_DOSSIER_ROOT is the declaration that this repository keeps dossiers.
    # Declared and empty is a broken configuration, so it FAILS; undeclared and
    # empty is a repository with nothing to check, which is NO-DATA and says so.
    configured = os.environ.get("SBE_DOSSIER_ROOT", "").strip()
    if configured:
        root = configured
    fails = 0
    print("BROTHERSBE DESIGN CHECKS  (advisory unless --strict; NO-DATA is never a pass)")
    if os.path.isdir(root) and is_dossier(root):
        targets = [root]
    elif os.path.isdir(root):
        targets = find_dossiers(root)
    else:
        targets = []
    if not targets:
        if configured:
            fails += 1
            print("  %-10s %-8s %s" % ("dossier", "FAIL",
                  "SBE_DOSSIER_ROOT=%s holds no dossier (no directory under it contains %s); "
                  "this repository declares that it keeps dossiers, so an empty dossier root is a broken "
                  "configuration, not an absence" % (root, INTAKE)))
        else:
            print("  %-10s %-8s %s" % ("dossier", "NO-DATA",
                  "no dossier found under %s: no directory contains %s. If this repository is supposed to carry "
                  "one, set SBE_DOSSIER_ROOT to where dossiers live and this becomes a FAIL instead of a report"
                  % (root, INTAKE)))
    for target in targets:
        if len(targets) > 1 or os.path.abspath(target) != os.path.abspath(root):
            print("  dossier: %s" % os.path.relpath(target, root))
        for name in which:
            verdict, ev = CHECKS[name](target)
            if verdict == "FAIL":
                fails += 1
            print("  %-10s %-8s %s" % (name, verdict, ev))
    if strict and fails:
        print("STRICT: %d design check(s) failed; exiting nonzero to block the merge." % fails)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("sbe_design: error %r" % (e,))
        sys.exit(1 if "--strict" in sys.argv else 0)
