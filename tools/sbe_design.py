#!/usr/bin/env python3
"""BrotherSBE design checks: the dossier's completeness rules, made mechanical.

Same contract as sbe_gate.py: one function per class returning (verdict, evidence),
advisory by default, --strict exits nonzero so CI can block. A design artifact that
fails its rule is not approved, and the failure names the missing field.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbe_intake import required_artifacts

ARTIFACT_FILES = {
    "01": "01-purpose.md", "02": "02-process.md", "03": "03-adr.md",
    "04": "04-technology-map.md", "05": "05-data-model.md",
    "06": "06-diagrams.md", "07": "07-verification.md",
}
CARDINALITIES = ("one-to-one", "one-to-many", "many-to-one", "many-to-many")


def read(root, name):
    path = os.path.join(root, name)
    try:
        return open(path, errors="replace").read()
    except OSError:
        return None


def check_artifacts(root):
    intake = read(root, "00-intake.json")
    if intake is None:
        return "NO-DATA", "no 00-intake.json; run sbe_intake.py to compute the tier"
    try:
        tier = json.loads(intake).get("tier")
    except ValueError:
        return "FAIL", "00-intake.json is not valid JSON"
    need = required_artifacts(tier)
    missing = [ARTIFACT_FILES[n] for n in need if read(root, ARTIFACT_FILES[n]) is None]
    if missing:
        return "FAIL", "tier %s requires %s; missing: %s" % (tier, ", ".join(need), ", ".join(missing))
    return "PASS", "tier %s: every required artifact present" % tier


def check_adr(root):
    t = read(root, ARTIFACT_FILES["03"])
    if t is None:
        return "NO-DATA", "no 03-adr.md in this dossier"
    problems = []
    rejected = len(re.findall(r"(?im)^#+\s*rejected\b", t))
    if rejected < 2:
        problems.append("only %d rejected alternative(s); an ADR needs at least 2" % rejected)
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


def check_data_model(root):
    t = read(root, ARTIFACT_FILES["05"])
    if t is None:
        return "NO-DATA", "no 05-data-model.md in this dossier"
    problems = []
    ents = _entities(t)
    if not ents:
        problems.append("no entities found under an Entities heading")
    for name, meta in ents.items():
        if "system of record" not in meta.lower():
            problems.append("entity '%s' has no system of record" % name)
    rel_block = re.split(r"(?im)^#+\s*relationships", t)
    if len(rel_block) > 1:
        for line in rel_block[1].splitlines():
            if re.match(r"\s*[-*]\s+", line) and not any(c in line.lower() for c in CARDINALITIES):
                problems.append("relationship '%s' has no cardinality" % line.strip()[:48])
    if problems:
        return "FAIL", "; ".join(problems[:6])
    return "PASS", "%d entities, each with a system of record; every relationship carries cardinality" % len(ents)


def check_diagrams(root):
    t = read(root, ARTIFACT_FILES["06"])
    if t is None:
        return "NO-DATA", "no 06-diagrams.md in this dossier"
    model = read(root, ARTIFACT_FILES["05"]) or ""
    known = set(_entities(model))
    nodes = set()
    for m in re.finditer(r"([A-Za-z_]\w*)\s*--", t):
        nodes.add(m.group(1))
    for m in re.finditer(r"-->\s*(?:\|[^|]*\|\s*)?([A-Za-z_]\w*)", t):
        nodes.add(m.group(1))
    nodes -= {"flowchart", "graph", "sequenceDiagram", "erDiagram", "LR", "TD", "RL", "BT"}
    if not nodes:
        return "FAIL", "no diagram nodes found; a diagram artifact with no diagram is a defect"
    orphans = sorted(n for n in nodes if known and n not in known)
    if orphans:
        return "FAIL", "diagram element(s) appear nowhere else in the dossier: %s" % ", ".join(orphans[:6])
    return "PASS", "%d diagram node(s), all traceable to dossier artifacts" % len(nodes)


CHECKS = {"artifacts": check_artifacts, "adr": check_adr,
          "datamodel": check_data_model, "diagrams": check_diagrams}


def main():
    argv = [a for a in sys.argv[1:] if a != "--strict"]
    strict = "--strict" in sys.argv
    root = "."
    which = list(CHECKS)
    for a in argv:
        if a in CHECKS:
            which = [a]
        elif os.path.isdir(a):
            root = a
    fails = 0
    print("BROTHERSBE DESIGN CHECKS  (advisory unless --strict; NO-DATA is never a pass)")
    for name in which:
        verdict, ev = CHECKS[name](root)
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
