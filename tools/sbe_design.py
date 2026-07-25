#!/usr/bin/env python3
"""BrotherSBE design checks: the dossier's completeness rules, made mechanical.

Same contract as sbe_gate.py: one function per class returning (verdict, evidence),
advisory by default, --strict exits nonzero so CI can block. A design artifact that
fails its rule is not approved, and the failure names the missing field.

Where it looks. A directory holding ANY numbered dossier artifact (00-intake.json
or any of 01 through 07) is a dossier and is checked. Anchoring the walk on
00-intake.json alone was a one-file-deletion bypass: seven filled-in artifacts with
the intake removed produced `dossier NO-DATA` and `--strict` exit 0 from the
repository root, so deleting one file evaporated the placeholder check, the ADR
check, the data-model check and the diagram check together. A dossier found without
its intake now FAILs and names the missing file, because without the intake there is
no tier and without a tier there is nothing to require.

Set SBE_DOSSIER_ROOT when a repository is supposed to carry a dossier, and a search
that finds none there becomes a FAIL instead of an absence. A dossier that is
history rather than live work carries a `.sbe-archived` file naming why, and is
reported as archived instead of blocking every unrelated merge forever.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbe_intake import required_artifacts, compute_tier, TIERS
from sbe_checks import Check, run_guarded

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
ARCHIVED = ".sbe-archived"
# An override reason has to be reviewable by a human, so it has to be at least a
# sentence. "tbd" and "x" cleared the entire dossier requirement. The threshold is
# stated here, in SKILL.md L15, and in the FAIL text, so it is not a hidden rule.
OVERRIDE_MIN_WORDS = 3
OVERRIDE_MIN_CHARS = 12


def read(root, name):
    path = os.path.join(root, name)
    try:
        return open(path, errors="replace").read()
    except OSError:
        return None


def present(root, name):
    """An artifact counts as present only if it has content.

    `touch 01-purpose.md` cleared tier T1: existence was `read(...) is not None`
    and an empty file reads as the empty string, which the placeholder check then
    passed too because a file with nothing in it carries no unfilled marker. A
    zero-byte design artifact is the absence of a design artifact.
    """
    t = read(root, name)
    return t is not None and t.strip() != ""


def _override_problem(reason):
    """Return why this override reason is not reviewable, or "" if it is.

    A one-character reason waived the entire dossier requirement: any non-empty
    string restored full belief in a hand-written tier. The same file already
    rejects "tbd" and "n/a" as a system-of-record value forty lines away, so it
    rejects them here too. An override is a control only if a human reading the
    weekly diff can tell what was traded away and why.
    """
    if not isinstance(reason, str) or not reason.strip():
        return "no override_reason is recorded"
    stated = _stated_value(reason)
    if not stated:
        return "the override_reason %r names the absence of a reason, not a reason" % reason.strip()[:24]
    if len(stated) < OVERRIDE_MIN_CHARS or len(stated.split()) < OVERRIDE_MIN_WORDS:
        return ("the override_reason %r is too short to review (%d words, %d characters)"
                % (stated[:24], len(stated.split()), len(stated)))
    return ""


def check_artifacts(root):
    intake = read(root, INTAKE)
    if intake is None:
        others = sorted(n for n in ARTIFACT_FILES.values() if read(root, n) is not None)
        if others:
            # Decided 2026-07-25: this is a FAIL, not an absence. A directory
            # carrying dossier artifacts is a dossier; without the intake there is
            # no tier, so nothing can say which artifacts it owes, and reporting
            # NO-DATA here is what made deleting one file a bypass.
            return "FAIL", ("dossier artifacts are present (%s) but there is no %s, so no tier can be "
                            "established and nothing can say which artifacts this dossier owes; "
                            "run sbe_intake.py here" % (", ".join(others), INTAKE))
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
    declared = data.get("override")
    if declared is not None and declared != tier:
        # sbe_intake.py writes this field, so something has to read it. A file
        # that declares an override to one tier and records another is not a
        # dossier anyone can audit.
        return "FAIL", ("00-intake.json declares override %r but records tier %r; the override field and "
                        "the tier field disagree, so neither can be trusted" % (declared, tier))
    if tier != computed:
        reason = data.get("override_reason")
        problem = _override_problem(reason)
        if problem:
            return "FAIL", ("00-intake.json says tier %s but its own answers compute %s, and %s; "
                            "a tier moved without a reviewable reason is an edit, not an override (L15). "
                            "An override reason must be at least %d words and %d characters, because a "
                            "reason nobody can review is not a control"
                            % (tier, computed, problem, OVERRIDE_MIN_WORDS, OVERRIDE_MIN_CHARS))
        direction = "lowering" if TIERS.index(tier) < TIERS.index(computed) else "raising"
        label = ("; declared override %s the tier to %s from computed %s, reason: %s"
                 % (direction, tier, computed, reason.strip()))
    need = required_artifacts(tier)
    missing = [ARTIFACT_FILES[n] for n in need if read(root, ARTIFACT_FILES[n]) is None]
    empty = [ARTIFACT_FILES[n] for n in need
             if ARTIFACT_FILES[n] not in missing and not present(root, ARTIFACT_FILES[n])]
    if missing or empty:
        parts = []
        if missing:
            parts.append("missing: %s" % ", ".join(missing))
        if empty:
            parts.append("present but empty: %s (a zero-byte artifact is the absence of an artifact)"
                         % ", ".join(empty))
        return "FAIL", "tier %s requires %s; %s" % (tier, ", ".join(need), "; ".join(parts))
    return "PASS", "tier %s: every required artifact present%s" % (tier, label)


# The marker as the templates actually ship it: inside an HTML comment. Matching
# the bare string anywhere meant a verification plan that CITED the check ("07
# asserts that no file still contains SBE-TEMPLATE-UNFILLED") FAILed with the
# false sentence "still the shipped template, unedited".
_MARKER_COMMENT = re.compile(r"(?s)<!--(?:(?!-->).)*?%s" % re.escape(UNFILLED_MARKER))


def check_placeholder(root):
    """A copied, unedited template is not a design. Reject the shipped marker."""
    found = {}
    blank = []
    for name in ARTIFACT_FILES.values():
        t = read(root, name)
        if t is None:
            continue
        if t.strip() == "":
            blank.append(name)
        else:
            found[name] = t
    if not found and not blank:
        return "NO-DATA", "no dossier artifacts here, so nothing to check for unfilled template sections"
    if blank:
        return "FAIL", ("zero-byte artifact(s): %s. An empty file carries no unfilled-template marker, "
                        "so passing it would be reporting a clean scan of nothing"
                        % ", ".join(sorted(blank)))
    unfilled = sorted(n for n, t in found.items() if _MARKER_COMMENT.search(t))
    if unfilled:
        return "FAIL", ("still the shipped template, unedited: %s; each carries its %s marker comment, which the template says to "
                        "delete once the section is your own design" % (", ".join(unfilled), UNFILLED_MARKER))
    return "PASS", "%d artifact(s) present, none still carrying an unfilled-template marker" % len(found)


_HEADING = re.compile(r"^(#+)\s*(.*)$")
# "Rejected" anywhere in the heading, as a word. Requiring the heading to BEGIN
# with it meant `### Option A (rejected): synchronous call` counted zero, and the
# convention was written down nowhere outside the template.
_REJECTED_HEADING = re.compile(r"(?i)\brejected\b")
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
            in_rejected = bool(_REJECTED_HEADING.search(h.group(2).strip()))
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


# An entity name may carry a hyphen or a dot. `[A-Za-z_][\w ]*?` could match
# neither, so `payment-token` and `pii.profile`, both explicitly sourceless, were
# dropped from the set and the PASS line asserted "each with a system of record"
# over a set it had silently truncated. That is the same defect as a gate passing
# over an empty manifest, one function deeper.
_ENTITY_BULLET = re.compile(r"^\s*[-*]\s*([A-Za-z_][\w .\-]*?)\s*(?::(.*))?$")
_ENTITY_HEADING = re.compile(r"(?i)entit")


def _entities(t):
    """Entity bullets from the entity sections of a data model.

    Scoped to headings that name entities, because "every bullet above the
    Relationships heading" made an honest `## Notes` list into two entities with
    no system of record and FAILed a correct data model. Where no heading names
    entities at all, the pre-Relationships body is still read, but only bullets
    in `Name: description` form, so a prose bullet is not mistaken for an entity.
    """
    out = {}
    body = re.split(r"(?im)^#+\s*relationships", t)[0]
    sections = []
    current = None
    for line in body.splitlines():
        h = _HEADING.match(line)
        if h:
            current = [] if _ENTITY_HEADING.search(h.group(2)) else None
            if current is not None:
                sections.append(current)
            continue
        if current is not None:
            current.append(line)
    if sections:
        # Inside a section that declares itself to be about entities, EVERY
        # bullet is an entity claim, colon or not: a bullet with no colon is an
        # entity with no system of record, which is the defect, not a non-entity.
        for sec in sections:
            for line in sec:
                m = _ENTITY_BULLET.match(line)
                if m:
                    out[m.group(1).strip()] = (m.group(2) or "").strip()
        return out
    for line in body.splitlines():
        m = _ENTITY_BULLET.match(line)
        if m and m.group(2) is not None:
            out[m.group(1).strip()] = m.group(2).strip()
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
        problems.append("no entity bullets found: list each entity as a bullet under a heading that "
                        "names entities, above the Relationships heading")
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
# Cardinality tokens (||--o{, }o--||, ||--||, }|..|{, ...) are built from the
# characters | o { } . and dash, and at least one of them is never a dash: a run
# of plain dashes between two identifiers ending in a colon is a markdown bullet
# on the line after a heading, which is how `## Components` followed by
# `- OrderQueue: ...` invented an entity called Components.
_ER_LINE = re.compile(r"([A-Za-z_]\w*)\s+[|o{}.\-]*[|o{}][|o{}.\-]*\s+([A-Za-z_]\w*)\s*:")
# Diagrams are code, in a fenced block. Reading the whole file meant any prose
# containing an arrow became a diagram node, so the traceability check reported
# orphans that were sentences.
_FENCE = re.compile(r"(?s)```[^\n]*\n(.*?)```")


def _diagram_nodes(t):
    # HTML comments are not diagram source. Left in, the "-->" that closes one
    # reads as a Mermaid edge and invents a node out of the next word.
    t = re.sub(r"(?s)<!--.*?-->", "", t)
    t = "\n".join(_FENCE.findall(t))
    nodes = set()
    for m in _NODE_SOURCE.finditer(t):
        nodes.add(m.group(1))
    for m in _NODE_DEST.finditer(t):
        nodes.add(m.group(1))
    for m in _ER_LINE.finditer(t):
        nodes.add(m.group(1))
        nodes.add(m.group(2))
    return nodes - DIAGRAM_KEYWORDS


_COMPONENT_HEADING = re.compile(r"(?i)component|runtime|technology map")


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _declared_components(root):
    """Runtime components a diagram is allowed to name, and where each was declared.

    Requiring every diagram node to be an ENTITY in 05-data-model.md failed the
    diagrams the template itself asks for at T3 (system context, container view,
    technology map, failover topology), which are made of services, queues and
    external systems. The published escape was to add the services to the data
    model as entities, which teaches an author to corrupt the conceptual model to
    satisfy a diagram check. So runtime components get their own declared place:
    the first column of the tables in 04-technology-map.md, and bullets under a
    Components heading in 06-diagrams.md itself. Declared somewhere and traceable,
    without pretending a queue is an entity.
    """
    out = {}
    tech = read(root, ARTIFACT_FILES["04"])
    if tech is not None:
        in_table = 0
        for line in tech.splitlines():
            s = line.strip()
            if not s.startswith("|"):
                in_table = 0
                continue
            in_table += 1
            if in_table <= 2:      # header row and its separator
                continue
            cell = s.strip("|").split("|")[0].strip()
            if cell:
                out.setdefault(_norm(cell), "%s: %s" % (ARTIFACT_FILES["04"], cell))
    diagrams = read(root, ARTIFACT_FILES["06"])
    if diagrams is not None:
        in_components = False
        for line in diagrams.splitlines():
            h = _HEADING.match(line)
            if h:
                in_components = bool(_COMPONENT_HEADING.search(h.group(2)))
                continue
            if not in_components:
                continue
            m = _BULLET.match(line)
            if m:
                name = m.group(1).split(":")[0].strip()
                if name:
                    out.setdefault(_norm(name), "%s: %s" % (ARTIFACT_FILES["06"], name))
    return out


def check_diagrams(root):
    t = read(root, ARTIFACT_FILES["06"])
    if t is None:
        return "NO-DATA", "no 06-diagrams.md in this dossier"
    nodes = _diagram_nodes(t)
    if not nodes:
        return "FAIL", ("no diagram nodes found in any fenced code block; a diagram artifact with no "
                        "diagram in it is a defect. Diagrams are code: put the Mermaid source in a "
                        "```mermaid fence so it diffs in review")
    model = read(root, ARTIFACT_FILES["05"])
    entities = {_norm(n): n for n in _entities(model)} if model is not None else {}
    components = _declared_components(root)
    known = dict(components)
    known.update(entities)
    if not known:
        # Without a data model or a component declaration there is nothing to
        # trace against. Reporting PASS here would be the exact defect L5 exists
        # to catch: an empty known set makes every invented node look traceable.
        return "NO-DATA", ("%d diagram node(s), but tracing cannot be verified: no entities in %s and no "
                           "components declared in %s or under a Components heading here"
                           % (len(nodes), ARTIFACT_FILES["05"], ARTIFACT_FILES["04"]))
    orphans = sorted(n for n in nodes if _norm(n) not in known)
    if orphans:
        return "FAIL", ("diagram element(s) appear nowhere else in the dossier: %s. Every node must be an "
                        "entity in %s or a declared component (a row in %s, or a bullet under a Components "
                        "heading in %s)"
                        % (", ".join(orphans[:6]), ARTIFACT_FILES["05"], ARTIFACT_FILES["04"],
                           ARTIFACT_FILES["06"]))
    return "PASS", ("%d diagram node(s), all traceable: %d to entities in %s, %d to declared components"
                    % (len(nodes),
                       sum(1 for n in nodes if _norm(n) in entities),
                       ARTIFACT_FILES["05"],
                       sum(1 for n in nodes if _norm(n) not in entities)))


# Same contract as sbe_gate.GATES: the registry carries the declaration, so the
# honesty meta-test enumerates the checks rather than a hand-written list of them.
CHECKS = {
    "artifacts": Check(check_artifacts, reads=(INTAKE,), kind="json"),
    "adr": Check(check_adr, reads=(ARTIFACT_FILES["03"],), kind="text", empty_expect="FAIL",
                 empty_note="a dossier that carries an empty 03-adr.md claims a decision record and "
                            "supplies none, which is a broken claim rather than an absence"),
    "datamodel": Check(check_data_model, reads=(ARTIFACT_FILES["05"],), kind="text", empty_expect="FAIL",
                       empty_note="an empty 05-data-model.md declares zero entities while claiming to "
                                  "be the data model, and zero entities each with a system of record "
                                  "is the vacuous PASS this check exists to prevent"),
    "diagrams": Check(check_diagrams, reads=(ARTIFACT_FILES["06"], ARTIFACT_FILES["05"]), kind="text",
                      empty_expect="FAIL",
                      empty_note="an empty 06-diagrams.md is a diagram artifact with no diagram in it, "
                                 "which is a broken claim rather than an absence: the dossier says it "
                                 "has diagrams and the file says otherwise"),
    "placeholder": Check(check_placeholder, reads=tuple(ARTIFACT_FILES.values()), kind="text",
                         empty_expect="FAIL",
                         empty_note="a zero-byte artifact carries no unfilled-template marker, so passing "
                                    "it would be reporting a clean scan of a file with nothing in it"),
}


def is_dossier(d):
    """A directory holding an intake file or any dossier artifact."""
    try:
        fns = set(os.listdir(d))
    except OSError:
        return False
    return INTAKE in fns or bool(fns & set(ARTIFACT_FILES.values()))


def find_dossiers(root):
    """Walk for directories carrying ANY numbered dossier artifact.

    Anchoring on 00-intake.json alone meant deleting one file removed the whole
    design gate from a repository-wide run: seven filled artifacts with no intake
    were never opened, and --strict exited 0. Any numbered artifact makes a
    directory a dossier; check_artifacts then FAILs it by name for the missing
    intake, because the tier cannot be established without it.
    """
    hits, archived = [], []
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
        if not (INTAKE in fns or (set(fns) & set(ARTIFACT_FILES.values()))):
            continue
        if ARCHIVED in fns:
            archived.append(dp)
            continue
        hits.append(dp)
    return hits, archived


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
    archived = []
    if os.path.isdir(root) and is_dossier(root):
        targets = [root]
    elif os.path.isdir(root):
        targets, archived = find_dossiers(root)
    else:
        targets = []
    for d in archived:
        print("  %-10s %-8s %s" % ("dossier", "NO-DATA",
              "%s carries %s, so it is history and is not checked. An unfinished dossier from last "
              "year blocking every unrelated merge forever is a gate that gets switched off"
              % (os.path.relpath(d, root), ARCHIVED)))
    if not targets:
        if configured:
            fails += 1
            print("  %-10s %-8s %s" % ("dossier", "FAIL",
                  "SBE_DOSSIER_ROOT=%s holds no dossier (no directory under it contains %s or any of "
                  "01 through 07); this repository declares that it keeps dossiers, so an empty dossier "
                  "root is a broken configuration, not an absence" % (root, INTAKE)))
        else:
            print("  %-10s %-8s %s" % ("dossier", "NO-DATA",
                  "no dossier found under %s: no directory contains %s or any of 01 through 07. If this "
                  "repository is supposed to carry one, set SBE_DOSSIER_ROOT to where dossiers live and "
                  "this becomes a FAIL instead of a report" % (root, INTAKE)))
        # Every requested check still accounts for itself. A check that prints no
        # line is indistinguishable from a check that was removed, and "the gate
        # said nothing" must never be readable as "the gate was satisfied".
        for name in which:
            print("  %-10s %-8s %s" % (name, "NO-DATA",
                  "no dossier under %s, so this check opened no file" % root))
    for target in targets:
        if len(targets) > 1 or os.path.abspath(target) != os.path.abspath(root):
            print("  dossier: %s" % os.path.relpath(target, root))
        for name in which:
            verdict, ev = run_guarded(name, CHECKS[name], target)
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
