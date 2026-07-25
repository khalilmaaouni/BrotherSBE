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
that finds none there becomes a FAIL instead of an absence. A directory that holds
dossier-shaped files without being live design work (the shipped templates, a
finished project's dossier from two years ago) carries a `.sbe-exempt` file whose
contents say why, and the report prints that reason on every run as a WAIVER
instead of the directory blocking every unrelated merge forever. The reason meets
the same reviewability threshold as a tier override: a zero-byte `.sbe-exempt`
turned a failing dossier into exit 0 while the report printed the sentence
"`.sbe-exempt` names why: no reason recorded", which asserts a reason and names
its absence in the same breath. An exemption states a reviewable reason or it
does not exempt, and a broken one is its own FAIL rather than a quiet gate.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbe_intake import required_artifacts, compute_tier, TIERS, QUESTIONS
from sbe_checks import Check, run_guarded, stated

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
# One visible exemption, with its reason inside the file and printed on every run.
# A directory can hold dossier-shaped files without being live design work: the
# shipped templates in templates/dossier/ are the obvious case, and a finished
# project's dossier from last year is the other. Both need to be skippable, and
# neither may be skippable quietly, so the reason is the file's contents and the
# report prints it. There is no env-var list and no hardcoded path.
EXEMPT = ".sbe-exempt"
# An override reason has to be reviewable by a human, so it has to be at least a
# sentence. "tbd" and "x" cleared the entire dossier requirement. The threshold is
# stated here, in SKILL.md L15, and in the FAIL text, so it is not a hidden rule.
OVERRIDE_MIN_WORDS = 3
OVERRIDE_MIN_CHARS = 12
# A rejected alternative also has to say why it lost, and `- a` satisfied a FAIL
# text that promised "at least one line saying why it lost". Its threshold is
# LOWER than an override's, deliberately and by measurement: at three words the
# rule rejected "Fails freshness." and "No isolation.", which are complete
# reasons an engineer would actually write. A gate that rejects correct work gets
# switched off, and a gate that is off catches nothing at all.
ALTERNATIVE_MIN_WORDS = 2
ALTERNATIVE_MIN_CHARS = 8


def read(root, name):
    path = os.path.join(root, name)
    try:
        return open(path, errors="replace").read()
    except OSError:
        return None


def _substantive_lines(t):
    """Lines that are content rather than scaffolding.

    A heading is a promise of content, not content. An HTML comment is a note to
    the author. Neither says anything about the design, so neither is what a tier
    asked for.
    """
    body = re.sub(r"(?s)<!--.*?-->", "", t or "")
    return [l for l in body.splitlines()
            if l.strip() and not l.lstrip().startswith("#")]


def present(root, name):
    """An artifact counts as present only if it has content under its headings.

    `touch 01-purpose.md` cleared tier T1: existence was `read(...) is not None`
    and an empty file reads as the empty string, which the placeholder check then
    passed too because a file with nothing in it carries no unfilled marker. A
    zero-byte design artifact is the absence of a design artifact.

    The same argument one level in: a file holding the template's headings and
    nothing under any of them is the empty-VALUES shape of the same defect, and
    it cleared a tier the same way. The keys being present is not the values
    being filled in.
    """
    t = read(root, name)
    return t is not None and bool(_substantive_lines(t))


def _override_problem(reason):
    """Return why this override reason is not reviewable, or "" if it is.

    A one-character reason waived the entire dossier requirement: any non-empty
    string restored full belief in a hand-written tier. The same file already
    rejects "tbd" and "n/a" as a system-of-record value forty lines away, so it
    rejects them here too. An override is a control only if a human reading the
    weekly diff can tell what was traded away and why.
    """
    return _reviewability_problem(reason, "override_reason")


def _reviewability_problem(text, what, min_words=OVERRIDE_MIN_WORDS,
                           min_chars=OVERRIDE_MIN_CHARS):
    """Return why this free-text justification is not reviewable, or "" if it is.

    One threshold, used everywhere a human is asked to accept a written reason
    instead of evidence: a tier override, a rejected alternative in an ADR, and a
    `.sbe-exempt` waiving a whole dossier. Each of those was shipped with its own
    rule or with none at all, and the one with none waived the most.
    """
    if not isinstance(text, str) or not text.strip():
        return "no %s is recorded" % what
    value = _stated_value(text)
    if not value:
        return "the %s %r names the absence of a reason, not a reason" % (what, text.strip()[:24])
    if len(value) < min_chars or len(value.split()) < min_words:
        return ("the %s %r is too short to review (%d words, %d characters; at least %d words and "
                "%d characters are required)"
                % (what, value[:24], len(value.split()), len(value), min_words, min_chars))
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
    # Every one of the five questions has to be ANSWERED, not merely keyed. An
    # intake carrying all five keys with "" in them re-derived a tier out of five
    # blanks and the gate reported it as computed. compute_tier reads a blank as
    # a no, so a blanked intake silently computed a lower tier than the truth.
    unanswered = [k for k, _ in QUESTIONS if stated(answers.get(k)) is None]
    if unanswered:
        return "NO-DATA", ("00-intake.json records tier %s but leaves %s unanswered, so the tier "
                           "cannot be re-derived from a complete intake. A blank answer is not a "
                           "no; rerun sbe_intake.py" % (tier, ", ".join(unanswered)))
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
    if not need:
        # A tier that requires nothing gives this check nothing to open, and
        # "tier T0: every required artifact present" read exactly like a verified
        # T3 line at a glance. By the project's own law a claim of nothing is
        # still nothing, so it says so instead.
        return "NO-DATA", ("tier %s requires no artifact, so this check opened none and there is "
                           "nothing here it can vouch for%s" % (tier, label))
    missing = [ARTIFACT_FILES[n] for n in need if read(root, ARTIFACT_FILES[n]) is None]
    empty = [ARTIFACT_FILES[n] for n in need
             if ARTIFACT_FILES[n] not in missing and not present(root, ARTIFACT_FILES[n])]
    if missing or empty:
        parts = []
        if missing:
            parts.append("missing: %s" % ", ".join(missing))
        if empty:
            parts.append("present but carrying no content of their own: %s (a zero-byte artifact, "
                         "or one holding only headings and comments, is the absence of an artifact)"
                         % ", ".join(empty))
        return "FAIL", "tier %s requires %s; %s" % (tier, ", ".join(need), "; ".join(parts))
    return "PASS", ("tier %s: every required artifact present and carrying content%s"
                    % (tier, label))


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


def _section_body(t, heading_pattern):
    """The lines under the first heading matching a pattern, or None if absent.

    A heading is not a section. `^#+\\s*criteria` matched `## Criteria` with
    nothing whatsoever under it, and the ADR check then reported "criteria,
    decision, consequences and flip condition present" over four empty headings.
    That is the empty-values defect in markdown: every key present, every value
    blank.
    """
    lines = t.splitlines()
    body, capturing = [], False
    for line in lines:
        h = _HEADING.match(line)
        if h:
            if capturing:
                break
            capturing = bool(re.search(heading_pattern, line, re.I))
            continue
        if capturing:
            body.append(line)
    if not capturing and not body:
        return None
    return body


def _required_section(t, pattern, label, problems):
    body = _section_body(t, pattern)
    if body is None:
        problems.append("no %s section" % label)
    elif not [l for l in body if l.strip()]:
        problems.append("the %s heading is present with nothing under it, so it names nothing; a "
                        "heading is a promise of content, not content" % label)


def check_adr(root):
    t = read(root, ARTIFACT_FILES["03"])
    if t is None:
        return "NO-DATA", "no 03-adr.md in this dossier"
    problems = []
    alternatives = _rejected_alternatives(t)
    rejected = len(alternatives)
    if rejected < 2:
        problems.append("only %d rejected alternative(s); an ADR needs at least 2, each with at least one line saying why it lost "
                        "(an empty heading is not an alternative)" % rejected)
    # The FAIL text above promises "at least one line saying why it lost", and
    # `- a` satisfied it. An override reason carries a reviewability threshold;
    # so does this, and it is the same threshold.
    thin = [a for a in alternatives
            if _reviewability_problem(a, "rejection reason", ALTERNATIVE_MIN_WORDS,
                                      ALTERNATIVE_MIN_CHARS)]
    if thin and rejected >= 2:
        problems.append("%d rejected alternative(s) carry no reviewable reason (%s); an alternative "
                        "with no stated reason for losing is a heading, not a decision record"
                        % (len(thin), "; ".join(repr(a[:24]) for a in thin[:3])))
    _required_section(t, r"^#+\s*criteria", "Criteria", problems)
    _required_section(t, r"^#+\s*decision", "Decision", problems)
    _required_section(t, r"^#+\s*consequences", "Consequences", problems)
    # The flip condition is accepted as a heading with content or, as before this
    # change, as a stated line anywhere in the document. Only the empty-heading
    # form is new, and only that form is rejected.
    flip = _section_body(t, r"what would flip")
    if flip is None:
        if not [l for l in t.splitlines() if re.search(r"what would flip", l, re.I) and l.strip()]:
            problems.append("no 'What would flip this' section; an ADR without it is a tombstone")
    elif not [l for l in flip if l.strip()]:
        problems.append("the 'What would flip this' heading is present with nothing under it, so "
                        "the ADR names no condition that would reverse the decision")
    if problems:
        return "FAIL", "; ".join(problems)
    return ("PASS", "%d alternatives rejected with a stated reason, and criteria, decision, "
                    "consequences and flip condition each carry content" % rejected)


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
    # Relationships were read as "every bullet after the Relationships heading",
    # which had it wrong in both directions. A section heading with nothing under
    # it, and a section written as a markdown table, both produced zero inspected
    # lines and the PASS still said "every relationship carries cardinality": a
    # sentence about work nothing did. The section is now scoped to itself, both
    # authoring forms are read, and the count is in the verdict so a reader can
    # tell ten checked relationships from none.
    rel_body = _section_body(t, r"^#+\s*relationships")
    rels, table_row = [], 0
    for line in (rel_body or []):
        s = line.strip()
        if re.match(r"\s*[-*]\s+", line) or re.match(r"^\d+[.)]\s+", s):
            rels.append(s)
        elif s.startswith("|"):
            table_row += 1
            if table_row > 2 and set(s) - set("|-: "):   # skip header and separator
                rels.append(s)
    for line in rels:
        if not _CARDINALITY.search(line):
            problems.append("relationship '%s' has no cardinality" % line[:48])
    if problems:
        return "FAIL", "; ".join(problems[:6])
    if not rels:
        return "NO-DATA", ("%d entities, each with a system of record, but no relationship line was "
                           "found (%s), so nothing was checked for cardinality and this check cannot "
                           "say that every relationship carries one"
                           % (len(ents),
                              "no Relationships heading" if rel_body is None
                              else "the Relationships heading has nothing under it that reads as a "
                                   "relationship: list them as bullets or as table rows"))
    return "PASS", ("%d entities, each with a system of record; %d relationship line(s) read, each "
                    "carrying cardinality" % (len(ents), len(rels)))


# The Mermaid diagram types this check knows, and what each one offers a
# traceability check. "nodes" means the type names things that must appear
# elsewhere in the dossier; "none" means it is a real, correct diagram that
# declares no such things, and reporting "a diagram artifact with no diagram in
# it" over one of those is a false failure. Two false failures were shipped: a
# `sequenceDiagram`, which the template itself tells a T2 author to write, and
# any flowchart using the ordinary `A[Customer] --> B[Order]` idiom.
DIAGRAM_TYPES = {
    "flowchart": "nodes", "graph": "nodes", "sequenceDiagram": "sequence",
    "erDiagram": "er", "classDiagram": "class", "stateDiagram": "state",
    "stateDiagram-v2": "state", "C4Context": "nodes", "mindmap": "nodes",
    "journey": "none", "gantt": "none", "pie": "none", "timeline": "none",
    "gitGraph": "none", "quadrantChart": "none", "requirementDiagram": "none",
    "sankey-beta": "none", "block-beta": "nodes", "xychart-beta": "none",
}
DIRECTIONS = {"LR", "RL", "TB", "TD", "BT"}
# Statement keywords that begin a line without naming a node. A token skipped for
# being one of these is REPORTED, never dropped: a diagram whose four nodes were
# all named after direction keywords lost four of five and the verdict still said
# "all traceable" over the one that survived.
_FLOW_STATEMENTS = {"subgraph", "end", "click", "style", "classDef", "class",
                    "linkStyle", "direction", "accTitle", "accDescr", "%%"}
_SEQ_STATEMENTS = {"activate", "deactivate", "note", "loop", "alt", "else", "opt",
                   "end", "par", "and", "rect", "autonumber", "title", "critical",
                   "break", "box", "link", "%%"}

_SHAPE = (r"\[\[[^\]\n]*\]\]|\[\([^)\n]*\)\]|\[/[^\]\n]*/\]|\[[^\]\n]*\]|"
          r"\(\(\([^)\n]*\)\)\)|\(\([^)\n]*\)\)|\([^)\n]*\)|"
          r"\{\{[^}\n]*\}\}|\{[^}\n]*\}|>[^\]\n]*\]")
# A node id carrying a label: the label is what a human reads, and it is what a
# data model calls the thing. Capturing only the id made `R[Refund] --> RL[RefundLine]`,
# the single most common Mermaid idiom there is, fail as two orphans named R and RL.
_NODE_LABELLED = re.compile(r"([A-Za-z_][\w.-]*)\s*(%s)" % _SHAPE)
_NODE_SOURCE = re.compile(r"([A-Za-z_][\w.-]*)\s*(?:--|==|-\.|~~)")
_NODE_DEST = re.compile(r"(?:--+>|--+|==+>|-\.-*>|~~+)\s*(?:\|[^|]*\|\s*)?([A-Za-z_][\w.-]*)")
# `A -- places --> B`: the words of an inline edge label are not nodes.
_INLINE_EDGE_LABEL = re.compile(r"--\s*[^-|>\n]+?\s*(--+>|--+)")
# erDiagram relationship line: ENTITY <cardinality> ENTITY : label
# Cardinality tokens (||--o{, }o--||, ||--||, }|..|{, ...) are built from the
# characters | o { } . and dash, and at least one of them is never a dash: a run
# of plain dashes between two identifiers ending in a colon is a markdown bullet
# on the line after a heading, which is how `## Components` followed by
# `- OrderQueue: ...` invented an entity called Components.
_ER_LINE = re.compile(r"([A-Za-z_]\w*)\s+[|o{}.\-]*[|o{}][|o{}.\-]*\s+([A-Za-z_]\w*)\s*:")
_ER_BLOCK = re.compile(r"^\s*([A-Za-z_]\w*)\s*\{")
_SEQ_PARTICIPANT = re.compile(r"^\s*(?:participant|actor)\s+([A-Za-z_]\w*)(?:\s+as\s+(.+?))?\s*$")
_SEQ_MESSAGE = re.compile(r"^\s*([A-Za-z_]\w*)\s*<?-{1,2}[>x)]{1,2}\s*([A-Za-z_]\w*)\s*:")
_CLASS_DECL = re.compile(r"^\s*class\s+([A-Za-z_]\w*)")
_CLASS_REL = re.compile(r"([A-Za-z_]\w*)\s*[<*o|]?[-.]{2,}[>*o|]*\s*([A-Za-z_]\w*)")
_STATE_EDGE = re.compile(r"(\[\*\]|[A-Za-z_]\w*)\s*-->\s*(\[\*\]|[A-Za-z_]\w*)")
# Diagrams are code, in a fenced block. Reading the whole file meant any prose
# containing an arrow became a diagram node, so the traceability check reported
# orphans that were sentences.
_FENCE = re.compile(r"(?s)```[^\n]*\n(.*?)```")


def _label_text(raw):
    return raw.strip("[](){}<>/\\ ").strip("\"'").strip()


def _diagram_nodes(t):
    """(nodes, kinds, skipped) for every fenced diagram in an artifact.

    nodes maps a node id to the label written on it, because a node is traceable
    by either. kinds lists the diagram types declared. skipped names every token
    this parser deliberately did not treat as a node, and WHY, because a token
    dropped in silence is a completeness claim over a truncated set.
    """
    # HTML comments are not diagram source. Left in, the "-->" that closes one
    # reads as a Mermaid edge and invents a node out of the next word.
    t = re.sub(r"(?s)<!--.*?-->", "", t)
    nodes, kinds, skipped = {}, [], []

    def add(nid, label=""):
        if nid in DIRECTIONS and not label and nid not in nodes:
            # Only reachable when a direction word stands completely alone; a
            # node genuinely named LR carries a shape or an edge and lands above.
            skipped.append("%s (a layout direction on its own line)" % nid)
            return
        if nid not in nodes or (label and not nodes[nid]):
            nodes[nid] = label

    for block in _FENCE.findall(t):
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        head = lines[0].strip()
        first = head.split()[0]
        kind = DIAGRAM_TYPES.get(first)
        if kind is None:
            kinds.append("unrecognised:%s" % first)
            kind = "nodes"          # read it as a flowchart rather than ignore it
            body = lines
        else:
            kinds.append(first)
            body = lines[1:]
            rest = head.split()[1:]
            # The declaration line is where flowchart/graph/LR/TD live. Stripping
            # them from EVERY line is what deleted nodes named after them; they
            # are stripped here, once, from the one line that declares the
            # diagram, and named in the report.
            skipped.append("%s%s (the diagram declaration: type%s)"
                           % (first, (" " + " ".join(rest)) if rest else "",
                              " and direction" if rest else ""))
        for line in body:
            s = line.strip()
            word = s.split()[0] if s.split() else ""
            if kind == "sequence":
                if word in _SEQ_STATEMENTS or s.startswith("%%"):
                    skipped.append("%s (a %s statement, not a participant)" % (word, first))
                    continue
                m = _SEQ_PARTICIPANT.match(s)
                if m:
                    add(m.group(1), (m.group(2) or "").strip())
                    continue
                m = _SEQ_MESSAGE.match(s)
                if m:
                    add(m.group(1))
                    add(m.group(2))
                continue
            if kind == "er":
                m = _ER_BLOCK.match(s)
                if m:
                    add(m.group(1))
                    continue
                m = _ER_LINE.search(s)
                if m:
                    add(m.group(1))
                    add(m.group(2))
                continue
            if kind == "class":
                m = _CLASS_DECL.match(s)
                if m:
                    add(m.group(1))
                    continue
                m = _CLASS_REL.search(s)
                if m:
                    add(m.group(1))
                    add(m.group(2))
                continue
            if kind == "state":
                for m in _STATE_EDGE.finditer(s):
                    for g in (m.group(1), m.group(2)):
                        if g != "[*]":
                            add(g)
                continue
            if kind == "none":
                continue
            # flowchart, graph and the node-shaped types
            if word in _FLOW_STATEMENTS or s.startswith("%%"):
                skipped.append("%s (a %s statement, not a node)" % (word, first))
                continue
            s = _INLINE_EDGE_LABEL.sub(lambda m: " %s " % m.group(1), s)
            for m in _NODE_LABELLED.finditer(s):
                add(m.group(1), _label_text(m.group(2)))
            bare = _NODE_LABELLED.sub(" ", s)
            for m in _NODE_SOURCE.finditer(bare):
                add(m.group(1))
            for m in _NODE_DEST.finditer(bare):
                add(m.group(1))
    return nodes, kinds, sorted(set(skipped))


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
    nodes, kinds, skipped = _diagram_nodes(t)
    # Every skipped token, on every verdict line. A parser that discards tokens in
    # silence and then reports "all traceable" is asserting completeness over a
    # set it truncated itself.
    note = ("; tokens read as diagram syntax rather than as nodes: %s" % ", ".join(skipped)) if skipped else ""
    if not kinds:
        return "FAIL", ("no fenced code block holding a diagram; a diagram artifact with no diagram "
                        "in it is a defect. Diagrams are code: put the Mermaid source in a "
                        "```mermaid fence so it diffs in review")
    if not nodes:
        bare = [k for k in kinds if DIAGRAM_TYPES.get(k) == "none"]
        if bare and len(bare) == len(kinds):
            # A gantt or a pie chart is a real diagram that names no element this
            # check can trace. Failing it as "a diagram artifact with no diagram
            # in it" would be rejecting correct work, which gets the gate switched
            # off, and a gate that is off catches less than a gate that is honest.
            return "NO-DATA", ("%s diagram(s) present, and this diagram type declares no nodes that "
                               "can be traced to entities or components, so nothing here was checked "
                               "for traceability%s" % (", ".join(sorted(set(bare))), note))
        return "FAIL", ("fenced %s block(s) found but no diagram node could be read out of them; a "
                        "diagram artifact with no diagram in it is a defect%s"
                        % (", ".join(sorted(set(kinds))), note))
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
                           "components declared in %s or under a Components heading here%s"
                           % (len(nodes), ARTIFACT_FILES["05"], ARTIFACT_FILES["04"], note))

    def resolved(nid, label):
        # A node is traceable by its id or by the label written on it. An author
        # writing `R[Refund]` has named the entity; insisting the id spell it out
        # tells them to rename every node or switch the gate off.
        for candidate in (nid, label):
            if candidate and _norm(candidate) in known:
                return _norm(candidate)
        return None

    orphans = sorted(nid for nid, label in nodes.items() if resolved(nid, label) is None)
    if orphans:
        return "FAIL", ("diagram element(s) appear nowhere else in the dossier: %s. Every node must be an "
                        "entity in %s or a declared component (a row in %s, or a bullet under a Components "
                        "heading in %s), matched on the node id or on its label%s"
                        % (", ".join(orphans[:6]), ARTIFACT_FILES["05"], ARTIFACT_FILES["04"],
                           ARTIFACT_FILES["06"], note))
    hits = [resolved(nid, label) for nid, label in nodes.items()]
    return "PASS", ("%d diagram node(s) in %s, all traceable: %d to entities in %s, %d to declared "
                    "components%s"
                    % (len(nodes), ", ".join(sorted(set(kinds))),
                       sum(1 for h in hits if h in entities),
                       ARTIFACT_FILES["05"],
                       sum(1 for h in hits if h not in entities), note))


# Worked dossier fragments that SHOULD pass. The honesty meta-test hollows these:
# it drops the body under one heading at a time, blanks the file, and empties it to
# zero bytes, and demands that none of that leaves a PASS standing. They are written
# in the ordinary idioms an engineer uses (labelled Mermaid node ids, bulleted
# alternatives, a relationships table) so that a change which starts rejecting honest
# work fails here first.
_FX_PURPOSE = ("# Purpose\nProblem: refunds settle late and support cannot say why.\n"
               "Users: the support desk and the finance close.\n"
               "Success: every refund reaches a terminal state within one business day.\n"
               "Non-goals: repricing, partial refunds.\nIf wrong: refunds stall silently.\n")
_FX_ADR = ("# ADR\n## Criteria\nsettlement latency, operational load, auditability\n"
           "## Rejected alternatives\n"
           "- Synchronous call to the ledger: ties checkout latency to ledger availability.\n"
           "- Nightly batch reconciliation: misses the one business day requirement.\n"
           "## Decision\nPublish refund events to a queue and settle asynchronously.\n"
           "## Consequences\nOne more moving part to operate, and an ordering guarantee to hold.\n"
           "## What would flip this\nSub-second settlement becoming a requirement.\n")
_FX_DATA_MODEL = ("# Data model\n## Entities\n"
                  "- Customer: system of record: the CRM.\n"
                  "- Refund: system of record: the ledger service.\n"
                  "## Relationships\n"
                  "- Customer to Refund: one-to-many, optional.\n")
_FX_DIAGRAMS = ("# Diagrams\n## Context\n"
                "```mermaid\nflowchart LR\n  C[Customer] --> R[Refund]\n```\n")

# Same contract as sbe_gate.GATES: the registry carries the declaration, so the
# honesty meta-test discovers the checks rather than carrying a hand-written list.
CHECKS = {
    "artifacts": Check(
        check_artifacts, reads=(INTAKE,), kind="json",
        full_fixture={"files": {
            INTAKE: {"tier": "T1",
                     "answers": {"changes_contract": False, "crosses_boundary": True,
                                 "reversible_under_hour": True, "touches_sensitive": False,
                                 "consumers": "none"}},
            ARTIFACT_FILES["01"]: _FX_PURPOSE}}),
    "adr": Check(check_adr, reads=(ARTIFACT_FILES["03"],), kind="text", empty_expect="FAIL",
                 empty_note="a dossier that carries an empty 03-adr.md claims a decision record and "
                            "supplies none, which is a broken claim rather than an absence",
                 full_fixture={"files": {ARTIFACT_FILES["03"]: _FX_ADR}}),
    "datamodel": Check(check_data_model, reads=(ARTIFACT_FILES["05"],), kind="text", empty_expect="FAIL",
                       empty_note="an empty 05-data-model.md declares zero entities while claiming to "
                                  "be the data model, and zero entities each with a system of record "
                                  "is the vacuous PASS this check exists to prevent",
                       full_fixture={"files": {ARTIFACT_FILES["05"]: _FX_DATA_MODEL}}),
    "diagrams": Check(check_diagrams, reads=(ARTIFACT_FILES["06"], ARTIFACT_FILES["05"]), kind="text",
                      empty_expect="FAIL",
                      empty_note="an empty 06-diagrams.md is a diagram artifact with no diagram in it, "
                                 "which is a broken claim rather than an absence: the dossier says it "
                                 "has diagrams and the file says otherwise",
                      full_fixture={"files": {ARTIFACT_FILES["06"]: _FX_DIAGRAMS,
                                              ARTIFACT_FILES["05"]: _FX_DATA_MODEL}},
                      optional_leaves={
                          "05-data-model.md##Relationships":
                              "this check traces diagram nodes to the ENTITIES declared in the data "
                              "model, and says nothing about its relationships. Emptying the "
                              "relationships section leaves every entity it traced against intact, "
                              "and the datamodel check's own sweep is what holds that section to "
                              "its sentence"}),
    "placeholder": Check(check_placeholder, reads=tuple(ARTIFACT_FILES.values()), kind="text",
                         empty_expect="FAIL",
                         empty_note="a zero-byte artifact carries no unfilled-template marker, so passing "
                                    "it would be reporting a clean scan of a file with nothing in it",
                         full_fixture={"files": {ARTIFACT_FILES["01"]: _FX_PURPOSE}},
                         optional_leaves={
                             "01-purpose.md##Purpose":
                                 "this check's sentence claims only that no artifact still carries the "
                                 "unfilled-template marker, and that claim stays true and fully examined "
                                 "when a section body is emptied. Whether an artifact of headings with "
                                 "nothing under them satisfies its tier is the artifacts check's "
                                 "sentence, and the same sweep holds it to it there"}),
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
    hits, exempt, refused = [], [], []
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
        if not (INTAKE in fns or (set(fns) & set(ARTIFACT_FILES.values()))):
            continue
        if EXEMPT in fns:
            reason = (read(dp, EXEMPT) or "").strip()
            # `touch .sbe-exempt` waived all five checks for a dossier and the
            # report printed the sentence ".sbe-exempt names why: no reason
            # recorded", which asserts a reason while naming its absence. An
            # exemption waives strictly more than a tier override does, and the
            # override already had to be reviewable, so this is held to the same
            # threshold. An exemption that states no reviewable reason does not
            # exempt: the dossier is checked, and the broken exemption is its own
            # failure so that nobody discovers it by noticing the gate went quiet.
            problem = _reviewability_problem(reason, "exemption reason")
            if problem:
                refused.append((dp, problem))
                hits.append(dp)
                continue
            exempt.append((dp, reason))
            continue
        hits.append(dp)
    return hits, exempt, refused


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
    exempt, refused = [], []
    if os.path.isdir(root) and is_dossier(root):
        targets = [root]
    elif os.path.isdir(root):
        targets, exempt, refused = find_dossiers(root)
    else:
        targets = []
    for d, why in exempt:
        # Printed as a WAIVER, never as a pass and never in silence. The line
        # names the directory and every check the waiver covers, because an
        # exemption nobody can see is an exemption nobody can withdraw, and a
        # dossier from last year blocking every unrelated merge forever is a gate
        # that gets switched off instead.
        print("  %-10s %-8s %s" % ("dossier", "WAIVED",
              "%s: %s waives %s here, stated reason: %s. Nothing below opened a file in that "
              "directory, so this is a waiver and not a verdict about the work"
              % (os.path.relpath(d, root), EXEMPT, ", ".join(CHECKS),
                 " ".join(why.split())[:200])))
    for d, problem in refused:
        fails += 1
        print("  %-10s %-8s %s" % ("dossier", "FAIL",
              "%s carries a %s that does not exempt anything: %s. An exemption waives all %d design "
              "checks for a dossier, which is more than a tier override waives, so it states a "
              "reviewable reason or it does not exempt; this dossier is checked below"
              % (os.path.relpath(d, root), EXEMPT, problem, len(CHECKS))))
    if not targets:
        if exempt:
            # Saying "no dossier found under X" underneath a waiver naming one is
            # a false sentence, and with SBE_DOSSIER_ROOT set it FAILed with
            # "holds no dossier" about a root that demonstrably held one.
            print("  %-10s %-8s %s" % ("dossier", "NO-DATA",
                  "every dossier found under %s (%d) is waived by a %s, so no check opened a file. "
                  "The waiver line(s) above name each one and the reason given"
                  % (root, len(exempt), EXEMPT)))
        elif configured:
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
        # The phrase "so this check opened no file" is load-bearing: it is how
        # evals/test_no_data_class.py tells a verdict this fallback printed from a
        # verdict the check itself produced, so a scenario cannot be counted as
        # covering a check it never reached. Change it in both places or not at all.
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
