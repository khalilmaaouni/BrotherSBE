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
from sbe_intake import required_artifacts, compute_tier, read_answers, TIERS, QUESTIONS
from sbe_checks import (Check, run_guarded, answered, answered_as, derivation_fold, vacuous,
                        domain_vacuous, all_vacuous, distinct, one_line, Pruner,
                        evidence_problem, without_comments)

ARTIFACT_FILES = {
    "01": "01-purpose.md", "02": "02-process.md", "03": "03-adr.md",
    "04": "04-technology-map.md", "05": "05-data-model.md",
    "06": "06-diagrams.md", "07": "07-verification.md",
}
# How a data model is allowed to write a cardinality. Four spellings shipped, and
# `1:N`, `N:1` and `1..*` were reported as "has no cardinality" about lines that
# carry one, with no accepted set named anywhere in the message. Crow's-foot
# shorthand and UML multiplicity are how data models are actually annotated, and a
# gate that rejects the two most common notations in the discipline is a gate that
# gets switched off. Named here, printed in the FAIL text, compiled below.
CARDINALITY_FORMS = (
    "one-to-one, one-to-many, many-to-one, many-to-many (hyphens or spaces)",
    "1:1, 1:N, N:1, N:M, 1:many (crow's foot shorthand)",
    "1..1, 0..1, 1..*, 0..* (UML multiplicity)",
    "1-to-many, N to 1 and the other mixed spellings of the same two ends",
    "prose: has one / has many / belongs to exactly one / zero or more",
    "a Mermaid erDiagram relationship line, whose cardinality symbols count",
)
INTAKE = "00-intake.json"
# Every shipped template carries this marker. Deleting it is part of filling the
# section in, so a dossier copied wholesale and never edited fails with the
# artifact named, rather than clearing the design gate on someone else's example.
UNFILLED_MARKER = "SBE-TEMPLATE-UNFILLED"
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
# The same floor for an artifact BODY, which had none: see present().
ARTIFACT_MIN_WORDS = 2
ARTIFACT_MIN_CHARS = 8


def read(root, name):
    """The artifact's text, or None when nothing readable is there.

    None is the ABSENCE answer only. A path that exists and cannot be read (a
    chmod 000 file, a directory wearing the name, a FIFO, a broken symlink) is
    the ACCESS axis, reported by read_problem below; every check asks that
    question first, because "no 05-data-model.md in this dossier" printed over a
    file that is present and unreadable is a false sentence, and a FIFO opened
    here used to hang the whole tool with no verdict in either mode.

    A UTF-8 byte-order mark is presentation, not content: left in place it glued
    itself to the first heading, which then matched no heading pattern, so a
    BOM'd artifact silently lost its first section.
    """
    path = os.path.join(root, name)
    if evidence_problem(path):
        return None
    try:
        text = open(path, errors="replace").read()
    except OSError:
        return None
    return text.lstrip("\ufeff")


def read_problem(root, name):
    """Why this artifact exists here and cannot be read, or "" (absent or readable)."""
    return evidence_problem(os.path.join(root, name))


def _substantive_lines(t):
    """Lines that are content rather than scaffolding.

    A heading is a promise of content, not content. An HTML comment is a note to
    the author. Neither says anything about the design, so neither is what a tier
    asked for.
    """
    body = without_comments(t)
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

    And the same argument one level further in again: a file whose every line
    under its headings reads "TODO" is the template with its marker deleted and
    nothing written in its place. Filling a section in with a placeholder is not
    filling it in.
    """
    t = read(root, name)
    if t is None or not _substantive_lines(t) or all_vacuous(t):
        return False
    # And a floor, because there was none at all: `# Purpose\nx\n` cleared a tier
    # while an override reason and a rejected alternative each carry a
    # reviewability threshold, on the argument that "any non-empty string" is too
    # weak for something a human is asked to accept instead of evidence. An
    # artifact is more than either. The floor is the LOWER of the two thresholds
    # on purpose: rejecting "Fails freshness." would be rejecting honest work.
    body = " ".join(l.strip() for l in _substantive_lines(t))
    return len(body) >= ARTIFACT_MIN_CHARS and len(body.split()) >= ARTIFACT_MIN_WORDS


# Words that carry no subject matter. A coherence test built on shared words has
# to know which words are shared by every document in the world, or "the system
# changes the data" would tie a banana to a tractor.
_COMMON_WORDS = frozenset("""
about above after again against all also and any are because been before being
below between both but can cannot could did does doing done down during each
either else etc even every few for from further had has have having here how
however into its itself just less like made make many may might more most must
need needs neither never new not now off once only onto other others ought our
ours out over own per rather same shall should since some such than that the
their theirs them then there these they this those through thus too under until
upon use used uses using very was way well were what when where whether which
while who whom whose why will with within without would you your yours
change changes changed data date day days design detail details document
documents each end ends example examples file files first form forms general
goal goals group groups hour hours idea ideas info information item items
level levels line lines list lists main model models name named names next
note notes number numbers order orders page pages part parts people phase
phases place places plan plans point points process processes product products
project projects purpose reason reasons record records result results rule
rules run runs same section sections service services set sets side sign
simple site sites size sizes state states step steps stop system systems
table tables task tasks team teams test tests thing things time times tool
tools type types unit units update updates user users value values version
versions view views week weeks work works year years
therefore furthermore additionally moreover meanwhile nevertheless nonetheless
consequently hence likewise similarly instead otherwise anyway besides indeed
perhaps maybe currently approximately overall broadly accordingly notably
specifically typically generally essentially effectively basically certainly
clearly obviously importantly usually often sometimes always already finally
initially eventually recently previously later earlier soon mostly mainly
largely slightly fairly quite really truly actually
""".split())
# The last block is the connective and adverb class, added because the coherence
# rule was defeated by ONE of them: four artifacts about bananas, lawnmowers, a
# tractor fleet and Mars each carried the word "Therefore" and that word alone
# tied them into a dossier, so the fixture this rule's own docstring names still
# cleared five of five. A word list is still a list, disclosed as such below;
# what changed is that the class these words belong to (words that connect
# sentences rather than naming anything) is named here, so the next one found
# joins its class instead of being one more instance.
_TERM = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}")


def _subject_terms(text):
    """The words in this artifact that carry its subject matter.

    Case-folded, four characters or more, minus the words every document shares.
    Crude on purpose: the question this answers is not "what is this about" but
    "is this about anything the rest of the dossier is about", and for that a
    word list is enough and a cleverer method would be a claim nobody can check.
    """
    # Fenced code is NOT stripped. A diagram artifact's subject matter lives
    # inside its ```mermaid fence and nowhere else, and stripping it made an
    # honest 06-diagrams.md read as an artifact about the words "Context" and
    # "Sequence".
    body = without_comments(text)
    out = set()
    for w in _TERM.findall(body):
        lw = w.lower()
        if len(lw) >= 4 and lw not in _COMMON_WORDS:
            out.add(lw)
    return out


def _coherence_problem(root, name, others):
    """Why this artifact belongs to a different dossier, or "" if it belongs to this one.

    The rule four of the seven required artifacts had no rule at all. `present()`
    was the entire content test for 01-purpose, 02-process, 04-technology-map and
    07-verification: two words and eight characters each. So a T3 dossier, the
    maximum-ceremony tier, whose purpose was about bananas, whose process was
    about lawnmowers, whose technology map was a tractor fleet and whose
    verification plan verified Mars, cleared five of five design checks. Every
    sentence the report printed was narrowly true and the dossier proved nothing.

    Coherence is the point. An artifact that never mentions anything named
    anywhere else in its own dossier is not an artifact, it is filler. Two ways
    to satisfy it, because one rule alone would reject honest work: name
    something the dossier DECLARES (an entity, a runtime component, a lifecycle
    state), or share any subject word with another artifact in the same dossier.
    A dossier with nothing else to compare against is not measured, and the
    verdict says so rather than passing quietly.
    """
    text = read(root, name)
    if text is None:
        return ""
    mine = _subject_terms(text)
    declared = set()
    for label in _declared_names(root, exclude=name):
        declared |= {w.lower() for w in _TERM.findall(label) if len(w) >= 3}
    if mine & declared:
        return ""
    theirs = set()
    for other in others:
        if other == name:
            continue
        theirs |= _subject_terms(read(root, other) or "")
    if not theirs and not declared:
        return None          # nothing to be coherent with; not measurable
    if mine & theirs:
        return ""
    return ("%s shares no named subject with any other artifact in this dossier (nothing it "
            "mentions is an entity, a runtime component or a lifecycle state declared here, and "
            "no substantive word in it appears in any sibling artifact); an artifact about a "
            "different system than the one this dossier designs is filler, not an artifact"
            % name)


def _declared_names(root, exclude=""):
    """Every name this dossier declares: entities, runtime components, lifecycle states."""
    out = []
    model = read(root, ARTIFACT_FILES["05"])
    if model is not None and ARTIFACT_FILES["05"] != exclude:
        out.extend(_entities(model))
    for norm, where in _declared_components(root).items():
        if not where.startswith(exclude or "\0"):
            out.append(where.split(": ", 1)[-1])
    for norm, where in _declared_states(root).items():
        if not where.startswith(exclude or "\0"):
            out.append(where.split(": ", 1)[-1])
    return out


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
    problem = read_problem(root, INTAKE)
    if problem:
        return "FAIL", ("%s is %s, so no tier can be read; an intake that exists and cannot be "
                        "read is a broken claim, not an absence" % (INTAKE, problem))
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
    # "none" is the shipped answer to "how many downstream consumers break if it
    # is wrong", so it is an answer here and nowhere else in this file. Carved
    # out at the call site rather than removed from the shared list, so a system
    # of record recorded as "none" is still the absence of one.
    unanswered = [k for k, _ in QUESTIONS
                  if answered(answers.get(k), allow=("none",)) is None]
    if unanswered:
        return "NO-DATA", ("00-intake.json records tier %s but leaves %s unanswered, so the tier "
                           "cannot be re-derived from a complete intake. A blank answer is not a "
                           "no, and neither is the word TBD; rerun sbe_intake.py"
                           % (tier, ", ".join(unanswered)))
    # Answered is not the same as readable. Every answer is now converted to the
    # meaning it records before any rule reads it, and an answer outside the
    # accepted vocabulary is a broken claim rather than an absence: the intake
    # says something, and nothing here can tell which thing. Reading these five
    # for truthiness meant "n" to every question computed the highest tier and
    # `consumers: "several"` computed the lowest, and this re-derivation, whose
    # entire job is to catch a hand-edited tier, recomputed the same wrong answer
    # and agreed with the file.
    _values, unreadable = read_answers(answers)
    if unreadable:
        return "FAIL", ("00-intake.json records tier %s but %s, so the tier cannot be re-derived "
                        "from answers this tool can read. An answer written in a vocabulary "
                        "nothing recognizes is a broken claim, not an absence; rerun sbe_intake.py"
                        % (tier, "; ".join(unreadable)))
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
        # A stored tier that differs from the computed one IS an override, and
        # L15 says an override sets BOTH fields. Only the reason was enforced, so
        # a file could move a tier with `override` null forever, and null is what
        # sbe_intake.py writes: the unenforced path was the default path. Both
        # fields are named here, because the author has to be told which one is
        # missing and what to write in it.
        reason = data.get("override_reason")
        missing = []
        if declared is None:
            missing.append("its override field is null, so nothing in the file declares the move")
        problem = _override_problem(reason)
        if problem:
            missing.append(problem)
        if missing:
            return "FAIL", ("00-intake.json says tier %s but its own answers compute %s, and %s; an "
                            "override sets BOTH fields and they must agree with each other, so this "
                            "file needs override: %r beside an override_reason of at least %d words "
                            "and %d characters. A tier moved with either field missing is an edit, "
                            "not an override (L15)"
                            % (tier, computed, "; ".join(missing), tier,
                               OVERRIDE_MIN_WORDS, OVERRIDE_MIN_CHARS))
        direction = "lowering" if TIERS.index(tier) < TIERS.index(computed) else "raising"
        label = ("; declared override %s the tier to %s from computed %s, reason: %s"
                 % (direction, tier, computed, reason.strip()))
    elif declared is not None:
        # The fields agree with each other and with the answers, so the override
        # exercised nothing. Said out loud, because a field carrying a tier reads
        # like a control that fired, and silence here would let a stale one keep
        # reading that way.
        label = ("; the override field records %s, which is the tier these answers compute, so it "
                 "moved no tier" % declared)
    need = required_artifacts(tier)
    if not need:
        # A tier that requires nothing gives this check nothing to open, and
        # "tier T0: every required artifact present" read exactly like a verified
        # T3 line at a glance. By the project's own law a claim of nothing is
        # still nothing, so it says so instead.
        return "NO-DATA", ("tier %s requires no artifact, so this check opened none and there is "
                           "nothing here it can vouch for%s" % (tier, label))
    wanted = [ARTIFACT_FILES[n] for n in need]
    # The ACCESS axis: an artifact that exists and cannot be read is neither
    # missing nor empty, and reporting it as "missing" is a false sentence about
    # a file that is sitting right there.
    unreadable = ["%s (%s)" % (n, read_problem(root, n)) for n in wanted if read_problem(root, n)]
    missing = [n for n in wanted if read(root, n) is None and not read_problem(root, n)]
    empty = [n for n in wanted if n not in missing and not read_problem(root, n)
             and not present(root, n)]
    # The content rule four of the seven artifacts never had: see
    # _coherence_problem. Only artifacts that are present and non-empty are asked,
    # because "this file is empty" and "this file is about something else" are two
    # different sentences and the first one is already printed above.
    unrelated, unmeasured = [], []
    # Every artifact PRESENT in the dossier, not only the ones this tier requires.
    # Passing `wanted` meant a T1 purpose brief coherent with the 04-technology-map
    # sitting beside it FAILed with the sentence "no substantive word in it appears
    # in any sibling artifact", about a sibling artifact it shares four words with.
    # A file the author wrote is part of this dossier whether or not the tier
    # obliged them to write it.
    siblings = [n for n in ARTIFACT_FILES.values() if read(root, n) is not None]
    for n in wanted:
        if n in missing or n in empty:
            continue
        problem = _coherence_problem(root, n, siblings)
        if problem is None:
            unmeasured.append(n)
        elif problem:
            unrelated.append(problem)
    if missing or empty or unrelated or unreadable:
        parts = []
        if missing:
            parts.append("missing: %s" % ", ".join(missing))
        if unreadable:
            parts.append("present but not readable: %s (an artifact this check cannot open is a "
                         "broken claim, not an absent one)" % ", ".join(unreadable))
        if empty:
            parts.append("present but carrying no content of their own: %s (a zero-byte artifact, one "
                         "holding only headings and comments, one whose every line is a placeholder, "
                         "or one whose whole body is under %d words and %d characters, is the absence "
                         "of an artifact)"
                         % (", ".join(empty), ARTIFACT_MIN_WORDS, ARTIFACT_MIN_CHARS))
        parts.extend(unrelated)
        return "FAIL", "tier %s requires %s; %s" % (tier, ", ".join(need), "; ".join(parts))
    return "PASS", ("tier %s: every required artifact present, carrying content, and naming subject "
                    "matter the rest of this dossier also names%s%s"
                    % (tier,
                       "" if not unmeasured else
                       "; except %s, which this dossier has nothing else to be coherent with, so "
                       "that was not checked" % ", ".join(unmeasured),
                       label))


# The marker as the templates actually ship it: inside an HTML comment. Matching
# the bare string anywhere meant a verification plan that CITED the check ("07
# asserts that no file still contains SBE-TEMPLATE-UNFILLED") FAILed with the
# false sentence "still the shipped template, unedited".
_MARKER_COMMENT = re.compile(r"(?s)<!--(?:(?!-->).)*?%s" % re.escape(UNFILLED_MARKER))


def check_placeholder(root):
    """A copied, unedited template is not a design. Reject the shipped marker."""
    found = {}
    blank = []
    unreadable = []
    for name in ARTIFACT_FILES.values():
        problem = read_problem(root, name)
        if problem:
            # A file this check could not open is a file it cannot call scanned,
            # and "none still carrying an unfilled-template marker" over a set
            # that silently excluded it is a completeness sentence over a
            # truncated set.
            unreadable.append("%s (%s)" % (name, problem))
            continue
        t = read(root, name)
        if t is None:
            continue
        # An empty file carries no unfilled marker, and neither does a file whose
        # every line says TODO. Both are the shipped template with the marker
        # deleted and nothing put in its place, which is the state this check
        # exists to name, so both are the absence of an artifact rather than a
        # clean scan of one. A file whose body was commented out is the same
        # state one edit later: nothing renders, so nothing was written. The
        # marker is searched in the RAW text first, because the templates ship
        # it inside a comment, and a template that still carries it is named as
        # the template it is rather than as a blank.
        if _MARKER_COMMENT.search(t):
            found[name] = t
        elif t.strip() == "" or all_vacuous(t) or not _substantive_lines(t):
            blank.append(name)
        else:
            found[name] = t
    if unreadable:
        return "FAIL", ("artifact(s) present that this check could not read: %s; a file that "
                        "cannot be opened cannot be scanned for the unfilled-template marker, so "
                        "passing over it would be reporting a clean scan of nothing"
                        % ", ".join(unreadable))
    if not found and not blank:
        return "NO-DATA", "no dossier artifacts here, so nothing to check for unfilled template sections"
    if blank:
        return "FAIL", ("artifact(s) with nothing written in them: %s. A zero-byte file, a file "
                        "whose every line under its headings is a placeholder, and a file whose "
                        "whole body sits inside HTML comments, carry no unfilled-template marker, "
                        "so passing them would be reporting a clean scan of nothing"
                        % ", ".join(sorted(blank)))
    unfilled = sorted(n for n, t in found.items() if _MARKER_COMMENT.search(t))
    if unfilled:
        return "FAIL", ("still the shipped template, unedited: %s; each carries its %s marker comment, which the template says to "
                        "delete once the section is your own design" % (", ".join(unfilled), UNFILLED_MARKER))
    return "PASS", "%d artifact(s) present, none still carrying an unfilled-template marker" % len(found)


_HEADING = re.compile(r"^(#+)\s*(.*)$")
# The four sections an ADR owes, and the words an author actually writes for
# each. The shipped template uses the first spelling of each, and SKILL.md L3
# names them, but an ADR written in plain English ("What we weighed", "Roads not
# taken", "What we are doing", "What this costs us", "When we would revisit
# this") failed all five checks on VOCABULARY while carrying every one of the
# things the law asks for. That is a gate rejecting correct work, which is how a
# gate gets switched off, and a gate that is off catches nothing at all. The rule
# is about the content under the heading; these are the ways of spelling the
# heading, listed here and in SKILL.md L3 so the set is reviewable and
# extensible rather than folklore.
_SECTION_WORDS = {
    "Criteria": ("Criteria", "Criterion", "What we weighed", "How we chose",
                 "How we decided", "What mattered", "Decision drivers",
                 "Deciding factors", "Forces"),
    "Decision": ("Decision", "What we are doing", "What we chose", "What we decided",
                 "What we will do", "Chosen option", "Chosen approach", "Our choice",
                 "The call"),
    "Consequences": ("Consequences", "What this costs", "Costs", "Costs and benefits",
                     "Implications", "What we give up", "Impact", "So what"),
    "What would flip this": ("What would flip this", "What would change our mind",
                             "What would reverse this", "When we would revisit this",
                             "Revisit", "Reconsider", "Reversal"),
}


def _heading_alternatives(spellings):
    """One regex per section, built from the spellings a reader is shown.

    Built rather than written twice, because the FAIL message names the accepted
    set and a set that drifts from the pattern it describes is a doc claim
    nothing recomputes. First person singular is accepted alongside the plural,
    and a trailing "this" or "it" is optional, so "What we weighed" and "What I
    weighed" and "When we would revisit" all land.
    """
    out = []
    for s in spellings:
        pat = re.escape(s.lower()).replace(r"\ ", r"\s+")
        pat = pat.replace(r"we\s+", r"(?:we|i)\s+")
        pat = re.sub(r"\\?\s*this$", r"(?:\\s+this)?", pat)
        out.append(pat)
    return "|".join(out)
# Matched anywhere in the heading line, not anchored to its first word: an author
# writes `## When would we revisit this?` as often as `## Revisit`.
_SECTION_ANCHORED = {label: r"^#+\s*(?:%s)" % _heading_alternatives(words)
                     for label, words in _SECTION_WORDS.items()}
_SECTION_PATTERNS = {label: r"^#+[^\n]*\b(?:%s)" % _heading_alternatives(words)
                     for label, words in _SECTION_WORDS.items()}
# The flip condition may also be a stated line with no heading of its own, and
# that fallback stays narrow on purpose: a heading is a declaration, a sentence
# in the middle of a paragraph is not, so only the explicit phrasings count.
_FLIP_IN_PROSE = r"what would flip|what would change (?:our|my|this) mind|what would reverse"
# "Rejected" anywhere in the heading, as a word, plus the plain-English ways of
# saying it. Requiring the heading to BEGIN with the word meant
# `### Option A (rejected): synchronous call` counted zero, and the convention
# was written down nowhere outside the template.
#
# And then the list was still an allow-list of the phrasings somebody had already
# tried. `## Alternatives considered` passed and `## Options considered` failed:
# synonyms, opposite verdicts. `## Considered options`, which is the heading the
# MADR template ships and therefore the single most common ADR heading in
# existence, failed outright, and the FAIL text listed the accepted FORMS and
# never the accepted WORDS, so the one thing the author needed was the one thing
# withheld. A gate nobody can predict is a gate people route around.
#
# Now: the head noun is enough. "Alternatives", "options" and "rejected" carry the
# meaning; whatever an author puts around them is theirs. The set is named here,
# is printed in full in the FAIL text, and is what the pattern is built from, so
# the message and the rule cannot drift apart.
REJECTED_HEADING_WORDS = (
    "rejected", "alternatives", "alternative", "options", "roads not taken",
    "not taken", "not chosen", "ruled out", "discarded", "dropped", "declined",
    "did not pick", "did not choose", "didn't pick", "didn't choose", "why not",
    # "Trade-offs considered" is how half the ADRs in the wild spell this
    # section, and it failed with 0 alternatives found.
    "trade-offs", "tradeoffs", "trade offs", "trade-off", "tradeoff",
)
_REJECTED_HEADING = re.compile(
    r"(?i)(?:%s)" % "|".join(r"\b%s\b" % w.replace(" ", r"\s+").replace("'", "'?")
                             for w in REJECTED_HEADING_WORDS))
_BULLET = re.compile(r"^\s*[-*]\s+(.*\S)\s*$")
# A numbered list is a list. `1.` and `2)` were not read as alternatives at all,
# while forty lines away the same file already accepts `^\d+[.)]\s+` as a
# relationship line, so one authoring form was recognised in one artifact and
# rejected in another for no stated reason.
_LIST_ITEM = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.*\S)\s*$")
# The forms an ADR may list its rejected alternatives in. Named here, printed in
# the FAIL text, and implemented by _rejected_alternatives: a gate that rejects
# three of the four ways an engineer writes this, with a message describing none
# of them, is a gate that gets argued with and then switched off.
ALTERNATIVE_FORMS = ("a bullet list (- or *)", "a numbered list (1. or 2))",
                     "one sub-heading per alternative, each with a body",
                     "one paragraph per alternative",
                     "a comparison table (one row per alternative; a row whose "
                     "verdict-like column says chosen is the decision, not an "
                     "alternative)")


def _rejected_alternatives(t):
    """Count rejected ALTERNATIVES, not headings that contain the word.

    Counting `^#+\\s*rejected` headings got both halves wrong: an ADR listing two
    real alternatives as bullets under one "Rejected alternatives" heading failed,
    while two empty "## Rejected" headings with nothing under either passed. That
    inverts the incentive the rule exists to create, teaching an author to add
    headings rather than alternatives. An alternative counts here only if it
    carries at least one non-empty line of its own.

    Four authoring forms, because three of the four ordinary ones FAILed while
    the ADRs carried everything the law asks for: bullets and numbered items count
    individually; a sub-heading per alternative counts once each, with its body as
    the reason; and prose counts one alternative per paragraph. An alternative
    still has to say why it lost, which is what the reviewability threshold below
    holds, and an empty heading still counts nothing.
    """
    found = []
    level = None           # heading depth of the open rejected section
    blocks = []            # (title, items, body) for the section and each sub-heading

    def close():
        for _title, items, body in blocks:
            if items:
                found.extend(items)
                continue
            table = _table_alternatives(body)
            if table:
                found.extend(table)
                continue
            paragraphs, current = [], []
            for l in body:
                if l.strip():
                    current.append(l.strip())
                elif current:
                    paragraphs.append(" ".join(current))
                    current = []
            if current:
                paragraphs.append(" ".join(current))
            if not paragraphs:
                continue
            if _title is None:
                # The section's own body: one alternative per paragraph, which is
                # how an author who writes prose separates them.
                found.extend(p[:60] for p in paragraphs)
            else:
                # A sub-heading IS one alternative however many paragraphs it
                # takes to explain. Counting paragraphs here would let one
                # alternative satisfy the rule that asks for two.
                found.append(("%s: %s" % (_title, " ".join(paragraphs)))[:60])
        del blocks[:]

    for line in t.splitlines():
        h = _HEADING.match(line)
        if h:
            depth, title = len(h.group(1)), h.group(2).strip()
            if level is not None and depth > level:
                blocks.append((title, [], []))     # a sub-heading inside the section
                continue
            close()
            level = depth if _REJECTED_HEADING.search(title) else None
            if level is not None:
                blocks.append((None, [], []))
            continue
        if level is None or not blocks:
            continue
        item = _LIST_ITEM.match(line)
        if item:
            blocks[-1][1].append(item.group(1)[:60])
        else:
            blocks[-1][2].append(line)
    close()
    return found


def _table_alternatives(body):
    """Rejected alternatives written as rows of a comparison table.

    The data-model check reads tables and this one did not, so an ADR whose
    alternatives sat in an Option / Verdict / Why table failed with "only 1
    distinct rejected alternative(s)" over a section naming three. One row is
    one alternative; a row whose verdict-shaped column says the option was
    chosen is the decision, not an alternative, and is left out.
    """
    rows = [l.strip() for l in body if l.strip().startswith("|")]
    if len(rows) < 3:
        return []
    header = [c.strip() for c in rows[0].strip("|").split("|")]
    verdict_col = next((i for i, h in enumerate(header)
                        if re.search(r"(?i)verdict|decision|status|outcome|chosen", h)), None)
    out = []
    for r in rows[2:]:
        if not set(r) - set("|-: "):
            continue
        cells = [c.strip() for c in r.strip("|").split("|")]
        if not cells or not cells[0]:
            continue
        if verdict_col is not None and verdict_col < len(cells) and re.search(
                r"(?i)\b(chosen|selected|accepted|picked|winner)\b", cells[verdict_col]):
            continue
        out.append(" | ".join(c for c in cells if c)[:60])
    return out


def _sections(t):
    """(heading text, body lines) for every heading in a document, in order."""
    out = []
    current = None
    for line in t.splitlines():
        h = _HEADING.match(line)
        if h:
            current = (h.group(2).strip(), [])
            out.append(current)
        elif current is not None:
            current[1].append(line)
    return out


def _section_body(t, heading_pattern):
    """The lines under the heading matching a pattern, or None if there is none.

    A heading is not a section. `^#+\\s*criteria` matched `## Criteria` with
    nothing whatsoever under it, and the ADR check then reported "criteria,
    decision, consequences and flip condition present" over four empty headings.
    That is the empty-values defect in markdown: every key present, every value
    blank.

    Where more than one heading matches, the one with content wins. Matching the
    first one made the DOCUMENT TITLE `# 03. Architecture decision record` the
    Decision section, whose body is the blank line before `## Context`, and the
    check then FAILed a correct ADR with "the Decision heading is present with
    nothing under it". A section that exists lower down is the section.
    """
    matches = [(title, body) for title, body in _sections(t)
               if re.search(heading_pattern, "#" + title, re.I)]
    if not matches:
        return None
    for _title, body in matches:
        if [l for l in body if l.strip()]:
            return body
    return matches[0][1]


def _required_section(t, label, problems):
    # Anchored first, so a heading that merely mentions the word (a title, a
    # cross-reference) never shadows the real section; the looser match is the
    # fallback that lets an author write "When would we revisit this?".
    body = _section_body(t, _SECTION_ANCHORED[label])
    if body is None:
        body = _section_body(t, _SECTION_PATTERNS[label])
    if body is None:
        problems.append("no %s section (this heading is accepted as any of: %s)"
                        % (label, ", ".join(_SECTION_WORDS[label])))
    elif not [l for l in body if l.strip()]:
        problems.append("the %s heading is present with nothing under it, so it names nothing; a "
                        "heading is a promise of content, not content" % label)


def check_adr(root):
    problem = read_problem(root, ARTIFACT_FILES["03"])
    if problem:
        return "FAIL", ("%s is %s; an artifact that exists and cannot be read is a broken claim, "
                        "not an absent one" % (ARTIFACT_FILES["03"], problem))
    t = read(root, ARTIFACT_FILES["03"])
    if t is None:
        return "NO-DATA", "no 03-adr.md in this dossier"
    # The rendered text: a decision record whose alternatives or criteria sit
    # inside an HTML comment is a record that renders without them, and four
    # sibling functions in this file already read it that way.
    t = without_comments(t)
    problems = []
    # Deduplicated by the shared rule, because `gate_numbers` learned that a
    # figure listed twice is one figure and this threshold did not: the same
    # rejected alternative pasted twice cleared "an ADR needs at least 2". With
    # the derivation fold, not the plain one, because a trailing period bought
    # a second alternative: two spellings of one sentence are one sentence
    # however they are punctuated.
    alternatives, dupes = distinct(_rejected_alternatives(t), reduce=derivation_fold)
    rejected = len(alternatives)
    if rejected < 2:
        problems.append("only %d distinct rejected alternative(s) found under a "
                        "rejected-alternatives heading%s; an ADR needs at least 2, each with at "
                        "least one line saying why it lost (an empty heading is not an "
                        "alternative). The heading is accepted as anything containing any of: %s. "
                        "Accepted forms under it: %s"
                        % (rejected,
                           "" if not dupes else " (%d duplicate line(s) counted once)" % dupes,
                           ", ".join(REJECTED_HEADING_WORDS), "; ".join(ALTERNATIVE_FORMS)))
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
    _required_section(t, "Criteria", problems)
    _required_section(t, "Decision", problems)
    _required_section(t, "Consequences", problems)
    # The flip condition is accepted as a heading with content or, as before this
    # change, as a stated line anywhere in the document. Only the empty-heading
    # form is new, and only that form is rejected.
    flip = _section_body(t, _SECTION_ANCHORED["What would flip this"])
    if flip is None:
        flip = _section_body(t, _SECTION_PATTERNS["What would flip this"])
    if flip is None:
        if not [l for l in t.splitlines() if re.search(_FLIP_IN_PROSE, l, re.I) and l.strip()]:
            problems.append("no 'What would flip this' section; an ADR without it is a tombstone "
                            "(this heading is accepted as any of: %s)"
                            % ", ".join(_SECTION_WORDS["What would flip this"]))
    elif not [l for l in flip if l.strip()]:
        problems.append("the 'What would flip this' heading is present with nothing under it, so "
                        "the ADR names no condition that would reverse the decision")
    if problems:
        return "FAIL", "; ".join(problems)
    # What this sentence may claim is what the threshold measured. It used to read
    # "rejected with a stated reason" over `- Synchronous ledger call` and
    # `- Nightly batch reconciliation`, two bullets that name two options and give
    # no reason at all: both clear two words and eight characters, and no rule
    # here can tell a reason from a longer name. So the count says what was
    # measured and names the part that is human review.
    return ("PASS", "%d distinct rejected alternatives, each carrying at least %d words and %d "
                    "characters of its own text (that the text says why the option lost, rather "
                    "than restating its name, is human review)%s, and criteria, "
                    "decision, consequences and flip condition each carry content"
                    % (rejected, ALTERNATIVE_MIN_WORDS, ALTERNATIVE_MIN_CHARS,
                       "" if not dupes else
                       " (%d duplicate line(s) counted once)" % dupes))


# An entity name may carry a hyphen or a dot. `[A-Za-z_][\w ]*?` could match
# neither, so `payment-token` and `pii.profile`, both explicitly sourceless, were
# dropped from the set and the PASS line asserted "each with a system of record"
# over a set it had silently truncated. That is the same defect as a gate passing
# over an empty manifest, one function deeper.
_ENTITY_BULLET = re.compile(r"^\s*[-*]\s*([A-Za-z_][\w .\-]*?)\s*(?::(.*))?$")
_ENTITY_HEADING = re.compile(r"(?i)entit")
# Markdown emphasis is presentation, not identity. `- **Order**: ...` and a
# table cell `| **Order** |` were invisible to patterns anchored on a letter,
# and the FAIL message then described the exact form the author had used.
# Paired ** __ * and backticks are unwrapped; single underscores are left
# alone, because identifiers carry them.
_EMPHASIS = re.compile(r"(\*\*|__|\*|`)(\S(?:[^*`]*?\S)?)\1")


def _plain(s):
    return _EMPHASIS.sub(r"\2", s or "")


def _joined_bullets(lines):
    """Lines with each bullet's soft-wrapped continuation folded back onto it.

    A false failure, and the worst kind: an entity bullet wrapped at 80 columns
    lost the half of itself that named its system of record, and the check FAILed
    with the sentence "entity 'RefundEvent' has no system of record" about a
    bullet that named one on its second line. An evidence line asserting
    something the artifact contradicts is this project's own defect class
    inverted, and wrapping a long line is the ordinary thing an author does.

    A continuation is an indented, non-empty line that is not itself a bullet, a
    heading, a table row or a fence. Everything else passes through untouched, so
    a paragraph after a bullet list is still a paragraph.
    """
    out = []
    for line in lines:
        stripped = line.strip()
        is_continuation = (
            out and _BULLET.match(out[-1]) and line[:1] in (" ", "\t") and stripped
            and not _BULLET.match(line) and not stripped.startswith(("#", "|", "```", ">"))
            and not re.match(r"^\d+[.)]\s", stripped))
        if is_continuation:
            out[-1] = out[-1].rstrip() + " " + stripped
        else:
            out.append(line)
    return out


def _table_entities(lines):
    """Entities written as a markdown table row: first cell the name, the rest its meta.

    Relationships were readable as a table and entities were not, so a data model
    written as tables throughout FAILed with "no entity bullets found" over a
    document that names every entity and every system of record. The asymmetry was
    documented, which makes it a stated restriction rather than a silent one, and
    it is still a gate failing correct work over an authoring form the same file
    accepts one heading further down.

    The header row and its `---` separator are skipped, exactly as they are for
    relationships, and a row whose first cell is empty is not an entity.

    A COLUMN HEADED `System of record` applies to its column. Without that, the
    phrase had to be repeated inside every cell, so a five-entity table produced
    five identical FAILs and the eval certifying "or as table rows" was written
    as `| Customer | system of record: the CRM |`, a cell restating its own
    column header, which is a fixture shaped to the parser rather than to an
    author. The header is read, and a cell under a system-of-record column is
    read as the answer to that column.
    """
    out, row, header = {}, 0, []
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue
        row += 1
        cells = [c.strip() for c in s.strip("|").split("|")]
        if row == 1:
            header = cells
            continue
        if row == 2 or not set(s) - set("|-: "):
            continue        # separator, or a row with nothing in it
        name = cells[0]
        if not name or not re.match(r"^[A-Za-z_][\w .\-]*$", name):
            continue
        # Joined with the cell separator, so a value cannot run into the next
        # column: see the note beside _SOR.
        meta = []
        for i, c in enumerate(cells[1:], start=1):
            head = header[i] if i < len(header) else ""
            is_sor_column = bool(head and _SOR_HEADER.match(head))
            if not c:
                if is_sor_column:
                    # An empty cell under a system-of-record column is the
                    # DECLARED absence of one. Dropping it with the other empty
                    # cells let the word "owner" in a Notes cell answer for it,
                    # so a table whose ownership column was blank in every row
                    # passed as "each with a system of record".
                    meta.append("system of record: ")
                continue
            if is_sor_column and not _SOR.search(c):
                # The column says what this cell is. Restated in the phrase the
                # value test reads, so one rule reads both authoring forms.
                meta.append("system of record: %s" % c)
            else:
                meta.append(c)
        out[name] = " | ".join(meta)
    return out


def _entity_bullets(t):
    """(entities, declared): the entity set this document states, and how it was found.

    `declared` is True when a heading whose name contains "entit" scoped the set,
    which is the form L4 describes and the only form this check will assert an
    entity COUNT over.

    Scoped to those headings because "every bullet above the Relationships
    heading" made an honest `## Notes` list into two entities with no system of
    record and FAILed a correct data model. The fallback for a document that
    names no such heading (a model whose section is called "Conceptual model",
    say) used to read every bullet in `Name: description` form, which is the same
    defect wearing the other face: it read `- Rollout plan: we ship on Tuesday`
    as an entity, and the same list with an ownership phrase in it bought the
    sentence "2 entities, each with a system of record" over a file that
    declares no entity at all.

    So the fallback still reads, because a model without a formal Entities
    heading should not be exempt from the rule, but it reads only bullets that
    NAME THE SYSTEM THAT OWNS THEM, which is the one thing every entity bullet
    in this law has to carry and the one thing a note never does. What it read is
    printed in the verdict, and the verdict is never better than NO-DATA, because
    a set this function had to guess at is not a set the evidence line may count.
    """
    out = {}
    t = _plain(without_comments(t))
    body = re.split(r"(?im)^#+\s*relationships", t)[0]
    sections = []
    current = None
    for line in _joined_bullets(body.splitlines()):
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
            out.update(_table_entities(sec))
            for line in sec:
                m = _ENTITY_BULLET.match(line)
                if m and m.group(2) is None and _SOR.search(line):
                    # No colon, but the bullet names an owner in prose:
                    # `- Order. The OMS is the system of record.` used to read
                    # the WHOLE sentence as the entity name and then print
                    # "does not name the system that owns it" about a line
                    # naming one in plain sight. The name is the first
                    # sentence; the rest is its description.
                    m2 = re.match(r"^\s*[-*]\s*([A-Za-z_][\w.-]*(?:\s+[A-Za-z_][\w.-]*){0,3}?)"
                                  r"\s*[.;,]\s+(.*\S)\s*$", line)
                    if m2:
                        out[m2.group(1).strip()] = m2.group(2).strip()
                        continue
                if m:
                    out[m.group(1).strip()] = (m.group(2) or "").strip()
        return out, True
    for line in _joined_bullets(body.splitlines()):
        m = _ENTITY_BULLET.match(line)
        if m and m.group(2) is not None and _SOR.search(m.group(2)):
            out[m.group(1).strip()] = m.group(2).strip()
    return out, False


def _entities(t):
    """Every name this document offers as an entity, read the widest way.

    For TRACING (the diagram check and the coherence test), not for the data
    model check. The two want opposite guesses: a name tracing missed becomes a
    false orphan and a false FAIL over an honest diagram, while a name the data
    model check reads by mistake becomes an assertion about a bullet nobody wrote
    as an entity. So tracing keeps the wide fallback and the check that has to
    print a count uses `_entity_bullets`, which says which set it got and refuses
    to count a set it guessed at.
    """
    t = _plain(without_comments(t))
    ents, declared = _entity_bullets(t)
    if declared:
        return ents
    out = dict(ents)
    for line in _joined_bullets(re.split(r"(?im)^#+\s*relationships", t)[0].splitlines()):
        m = _ENTITY_BULLET.match(line)
        if m and m.group(2) is not None:
            out.setdefault(m.group(1).strip(), m.group(2).strip())
    return out


# How an entity is allowed to name the system that owns it. The rule is that the
# owning system is NAMED; the phrase used to name it was a hidden allow-list of
# one. "source of truth" is the most common synonym in the discipline and it
# FAILed with the sentence "entity 'Order' has no system of record" about a line
# that names one in plain sight, and the message never said what phrase it wanted.
# Named here, printed in the FAIL text, compiled below, longest phrase first so
# "owned by" wins over "owner".
SOR_PHRASES = ("system of record", "system of truth", "source of truth", "book of record",
               "authoritative source", "mastered by", "owned by", "owner", "sor")
_SOR_ALT = "|".join(re.escape(p).replace(r"\ ", r"\s+")
                    for p in sorted(SOR_PHRASES, key=len, reverse=True))
# The separator is optional so both "system of record: the CRM" and "system of
# record the CRM" are read. Substring matching alone let "no system of record
# known yet" through, because the phrase was present; the value is what the rule
# is actually about.
# The value stops at a cell boundary. Capturing `(.+)` ran a table row's
# system-of-record cell straight into its Notes cell, so `| Customer | TBD |
# core |` read as the value "TBD core", which is not a placeholder, and a
# nameless owner passed on the strength of an unrelated column.
_SOR = re.compile(r"(?i)(?<![\w-])(?:%s)(?![\w-])\s*[:=]?\s*([^|]+)" % _SOR_ALT)
# A table COLUMN whose heading is one of the phrases and nothing else.
_SOR_HEADER = re.compile(r"(?i)^\s*(?:%s)\s*$" % _SOR_ALT)
_NO_SOR = re.compile(r"(?i)\bno\s+(?:%s)(?![\w-])" % _SOR_ALT)
# The value may sit BEFORE the phrase: "The OMS is the system of record." names
# the OMS, and capturing only what follows the phrase left "." as the value, so
# an honest sentence FAILed as "names a system of record with no value".
_SOR_BEFORE = re.compile(
    r"(?i)\b((?:the\s+|our\s+|its\s+)?[A-Za-z_][\w.-]*(?:\s+[A-Za-z_][\w.-]*){0,4}?)"
    r"\s+(?:is|are|was|remains)\s+(?:the\s+|our\s+|its\s+)?(?:%s)(?![\w-])" % _SOR_ALT)
# The list of values that name the absence of an answer used to live HERE, as a
# private constant, and that is precisely how the fourth round of this defect
# happened: this file refused the token "todo" as a system of record while
# sbe_gate.py, which never imported it, accepted "TODO" as a pinned warehouse
# snapshot in the same run. It now lives in sbe_checks.VACUOUS_VALUES, imported
# by every tool, extended in one place. See the comment beside it there.
# A cardinality must stand as its own token. Without the guards, "one-to-many-ish"
# satisfied a substring test, so a sentence explicitly saying the cardinality was
# undecided cleared the gate that exists to decide it. The accepted notations are
# CARDINALITY_FORMS at the top of this file; this is what they compile to.
_CARD_END = r"(?:one|many|1|n|m|\*)"
_CARDINALITY = re.compile(
    r"(?ix)(?<![\w.*-])(?:"
    r"   %s \s*[-\s]?\s* to \s*[-\s]?\s* %s"      # one-to-many, 1-to-many, N to 1
    r" | %s \s*:\s* %s"                            # 1:N, N:1, 1:1, many:1
    r" | [0-9*]+ \s*\.\.\s* [0-9*]+"               # 1..*, 0..1 (UML multiplicity)
    r")(?![\w-])" % (_CARD_END, _CARD_END, _CARD_END, _CARD_END))
# Cardinality written as an English sentence: "An Order has many OrderLines,
# and every OrderLine belongs to exactly one Order" carries both ends and
# failed with a message listing every notation except the one people speak.
_CARD_PROSE = re.compile(
    r"(?ix)\b(?:has|have|holds|hold|contains|contain|owns|own)\s+"
    r"(?:exactly\s+|at\s+least\s+|at\s+most\s+)?(?:one|many|zero\s+or\s+more|one\s+or\s+more)\b"
    r"|\bbelongs?\s+to\s+(?:exactly\s+)?one\b"
    r"|\bexactly\s+one\b")


def _stated_value(v):
    """The value this text records, or "" when it names the absence of one.

    A thin wrapper over the shared predicate so the call sites here keep reading
    in strings rather than in None.

    Through answered_as with the derivation fold, not answered on the raw text,
    because this was the reduce-then-test ordering bug alive in one more place:
    a system of record written as `-- see above` is not blank and is not a
    single vacuity token, so it survived answered(), while the same project
    refused the identical string as a derivation. The fold strips comments,
    punctuation and case FIRST, and the vacuity test reads what is left.
    """
    return answered_as(v, derivation_fold) or ""


def check_data_model(root):
    problem = read_problem(root, ARTIFACT_FILES["05"])
    if problem:
        return "FAIL", ("%s is %s; an artifact that exists and cannot be read is a broken claim, "
                        "not an absent one" % (ARTIFACT_FILES["05"], problem))
    t = read(root, ARTIFACT_FILES["05"])
    if t is None:
        return "NO-DATA", "no 05-data-model.md in this dossier"
    # The rendered text, for the same reason as check_adr: a commented-out
    # entity list read as "2 entities, each with a system of record" while the
    # artifacts check called the same file the absence of an artifact. Emphasis
    # is unwrapped so a bolded entity name is still an entity name.
    t = _plain(without_comments(t))
    problems = []
    ents, declared_by_heading = _entity_bullets(t)
    # What this check had to guess at, said in the verdict rather than folded into
    # a count. See _entity_bullets: a Notes list read as an entity set is the same
    # defect as a PASS over an empty manifest, one function deeper.
    read_note = ("" if declared_by_heading else
                 "; no heading in %s names entities, so the set above was read from the bullet(s) "
                 "here that name a system that owns them (%s), and a bullet naming none was left as "
                 "the prose it is. Put them under a heading whose name contains \"entit\" to have "
                 "this check read them as the entity set"
                 % (ARTIFACT_FILES["05"], ", ".join(sorted(ents)) or "none"))
    if not ents:
        problems.append(
            "no entity found: list each entity as a bullet, or as a row of a markdown "
            "table whose first column is the entity name, under a heading that names "
            "entities, above the Relationships heading"
            if declared_by_heading else
            "no entity found: no heading in %s names entities (a heading whose name contains "
            "\"entit\"), and no bullet above the Relationships heading names the system that owns "
            "it, so nothing here was read as an entity and a list of notes was left as notes. List "
            "each entity as a bullet, or as a row of a markdown table whose first column is the "
            "entity name, under a heading that names entities" % ARTIFACT_FILES["05"])
    for name, meta in ents.items():
        if domain_vacuous(name):
            # An entity called TBD is a note to the author. The PASS sentence
            # counts entities, so a placeholder counted as one. Scoped: an entity
            # name is DOMAIN CONTENT, so the words an engineer can honestly mean
            # (none, pending, unknown) are not placeholders here. See
            # sbe_checks.DOMAIN_WORDS.
            problems.append("entity %r names no entity; a placeholder in the entity list is counted "
                            "by the sentence 'N entities, each with a system of record'" % name)
            continue
        m = _SOR.search(meta)
        if not m or _NO_SOR.search(meta):
            problems.append("entity '%s' does not name the system that owns it (accepted as any of: "
                            "%s, as `<phrase>: the OMS` on the bullet, or as a table column headed "
                            "with one of them)" % (name, ", ".join(SOR_PHRASES)))
        else:
            value = _stated_value(m.group(1))
            if not value:
                # The name may sit before the phrase: "The OMS is the system of
                # record." is an owner named in the discipline's most ordinary
                # sentence shape.
                mb = _SOR_BEFORE.search(meta)
                value = _stated_value(mb.group(1)) if mb else ""
            if not value:
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
    rels, er_rels, table_row = [], [], 0
    for line in (rel_body or []):
        # A Mermaid erDiagram under the Relationships heading IS a relationship
        # list, and its cardinality symbols are cardinality: refusing it told an
        # author to restate their own diagram as bullets.
        if _ER_LINE.search(line.strip()):
            er_rels.append(line.strip())
    # Folded for the same reason the entity bullets are: a relationship wrapped
    # at 80 columns kept its name on the first line and its cardinality on the
    # second, and FAILed as "has no cardinality" against a line that carried one.
    for line in _joined_bullets(rel_body or []):
        s = line.strip()
        if re.match(r"\s*[-*]\s+", line) or re.match(r"^\d+[.)]\s+", s):
            rels.append(s)
        elif s.startswith("|"):
            table_row += 1
            if table_row > 2 and set(s) - set("|-: "):   # skip header and separator
                rels.append(s)
    for line in rels:
        if not (_CARDINALITY.search(line) or _CARD_PROSE.search(line)):
            problems.append("relationship '%s' names no cardinality this tool can read (accepted: "
                            "%s)" % (line[:48], "; ".join(CARDINALITY_FORMS)))
    rels = rels + er_rels
    if problems:
        # The truncation is named. Six of eight sourceless entities were printed
        # and the other two were dropped out of a message that reads as the whole
        # list, which is the same defect as a count over a set the tool shortened
        # itself.
        return "FAIL", ("; ".join(problems[:6])
                        + ("" if len(problems) <= 6 else
                           "; and %d more not shown" % (len(problems) - 6))
                        + (read_note if ents else ""))
    if not declared_by_heading:
        # Everything this check asks of an entity holds for the ones it read, and
        # it still cannot say it read the entity SET rather than a prose list. So
        # it says that, instead of counting. NO-DATA neither blocks the honest
        # author nor lends the count a sentence nothing earned.
        return "NO-DATA", ("%d bullet(s) name a system that owns them and were read as entities (%s), "
                           "each carrying one, and %d relationship line(s) read; but no heading in %s "
                           "names entities, so this check cannot say that set is the entity set rather "
                           "than a prose list, and it does not assert an entity count over one. Put "
                           "them under a heading whose name contains \"entit\" and this check reads "
                           "them as the entity set"
                           % (len(ents), ", ".join(sorted(ents)), len(rels), ARTIFACT_FILES["05"]))
    if not rels:
        return "NO-DATA", ("%d entities, each with a system of record, but no relationship line was "
                           "found (%s), so nothing was checked for cardinality and this check cannot "
                           "say that every relationship carries one"
                           % (len(ents),
                              "no Relationships heading" if rel_body is None
                              else "the Relationships heading has nothing under it that reads as a "
                                   "relationship: list them as bullets, table rows, or an erDiagram"))
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
    # mindmap used to be read as a flowchart, which is a half-parse: the shaped
    # root matched and every bare-word child was dropped in silence, so two
    # undeclared children sat under a verdict saying "all traceable". A mindmap
    # names a node on every content line, so it gets a parser that reads every
    # content line.
    "stateDiagram-v2": "state", "mindmap": "mindmap",
    # C4 has its own statement grammar, `Person(alias, "Label")`, and reading it
    # as a flowchart made the Mermaid KEYWORDS `Person` and `System` into orphan
    # node names, so the canonical Mermaid dialect for the system-context diagram
    # that SKILL.md Phase 5 asks a T2 or T3 author to draw FAILed, inventing the
    # orphans it then reported. It gets a parser instead.
    "C4Context": "c4", "C4Container": "c4", "C4Component": "c4",
    "C4Dynamic": "c4", "C4Deployment": "c4",
    # block-beta names its blocks as bare identifiers on a line, which the
    # flowchart parser reads only when they carry a shape or an edge, so a real
    # diagram produced no nodes and was reported as "a diagram artifact with no
    # diagram in it".
    "block-beta": "block",
    "journey": "none", "gantt": "none", "pie": "none", "timeline": "none",
    "gitGraph": "none", "quadrantChart": "none", "requirementDiagram": "none",
    "sankey-beta": "none", "xychart-beta": "none",
}
# C4 statement keywords, by what each one contributes.
_C4_ELEMENT = {"Person", "Person_Ext", "System", "System_Ext", "SystemDb", "SystemDb_Ext",
               "SystemQueue", "SystemQueue_Ext", "Container", "Container_Ext", "ContainerDb",
               "ContainerDb_Ext", "ContainerQueue", "Component", "Component_Ext", "ComponentDb",
               "ComponentQueue", "Node", "Node_L", "Node_R", "Deployment_Node"}
_C4_REL = {"Rel", "BiRel", "Rel_U", "Rel_D", "Rel_L", "Rel_R", "Rel_Up", "Rel_Down",
           "Rel_Left", "Rel_Right", "Rel_Back", "RelIndex"}
_C4_GROUPING = {"Boundary", "Enterprise_Boundary", "System_Boundary", "Container_Boundary",
                "Node_Boundary", "Deployment_Node"}
_C4_CALL = re.compile(r"^\s*([A-Za-z_]\w*)\s*\(\s*([A-Za-z_][\w.-]*)\s*(?:,\s*\"([^\"]*)\")?")
_BLOCK_STATEMENTS = {"columns", "space", "block", "end", "style", "classDef", "class",
                     "click", "direction", "down", "up", "%%"}
_BLOCK_TOKEN = re.compile(r"(?<![\w.\-\[\"])([A-Za-z_][\w.-]*)(?::\d+)?(?![\w.\-\[\"(])")
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


def _strip_edge_labels(s, skipped):
    """Drop inline edge labels, NAMING each one dropped.

    An edge label is not a node and discarding it is right: L5 says the parser
    that touches edge labels exists to discard their words so they are not
    mistaken for nodes. It discarded them in silence, though, and the same law
    promises that every token read as syntax rather than as a node is named in
    the evidence line, on every verdict. `C[Customer] -- Ledger --> O[Order]`
    dropped "Ledger" out of the set the verdict then reported as complete, which
    is the truncated-set defect that sentence exists to prevent.
    """
    def sub(m):
        label = m.group(0)[2:len(m.group(0)) - len(m.group(1))].strip()
        if label:
            skipped.append("%s (an inline edge label, not a node)" % label)
        return " %s " % m.group(1)
    return _INLINE_EDGE_LABEL.sub(sub, s)
# ONE identifier grammar for every dialect. Seven patterns spelled a node id as
# `[A-Za-z_]\w*` while the flowchart, C4 and block-beta patterns beside them,
# and the data model's own entity rule, all accepted hyphens and dots. Hyphens
# are the dominant naming convention in backend and infrastructure work, so the
# mismatch failed in both directions at once: `participant feed-poller` was
# silently dropped (a hyphenated orphan then PASSed as "all traceable", and an
# honest hyphenated participant was never read), `in-transit -->
# out-for-delivery` was shredded into the invented orphans `in`, `transit`,
# `out` and `delivery`, and `class feed-poller` was truncated to a node called
# `feed`. L4's own worked example (`payment-token`, `pii.profile`) could not be
# drawn in an erDiagram of itself.
_IDENT = r"[A-Za-z_][\w.-]*"
# erDiagram relationship line: ENTITY <cardinality> ENTITY : label
# Cardinality tokens (||--o{, }o--||, ||--||, }|..|{, ...) are built from the
# characters | o { } . and dash, and at least one of them is never a dash: a run
# of plain dashes between two identifiers ending in a colon is a markdown bullet
# on the line after a heading, which is how `## Components` followed by
# `- OrderQueue: ...` invented an entity called Components. The whitespace
# around the cardinality keeps the identifier's own hyphens and dots out of it.
_ER_LINE = re.compile(r"(%s)\s+[|o{}.\-]*[|o{}][|o{}.\-]*\s+(%s)\s*:" % (_IDENT, _IDENT))
_ER_BLOCK = re.compile(r"^\s*(%s)\s*\{" % _IDENT)
_SEQ_PARTICIPANT = re.compile(r"^\s*(?:participant|actor)\s+(%s)(?:\s+as\s+(.+?))?\s*$" % _IDENT)
_SEQ_MESSAGE = re.compile(r"^\s*(%s)\s*<?-{1,2}[>x)]{1,2}\s*(%s)\s*:" % (_IDENT, _IDENT))
_CLASS_DECL = re.compile(r"^\s*class\s+(%s)" % _IDENT)
_CLASS_REL = re.compile(r"(%s)\s*[<*o|]?[-.]{2,}[>*o|]*\s*(%s)" % (_IDENT, _IDENT))
_STATE_EDGE = re.compile(r"(\[\*\]|%s)\s*-->\s*(\[\*\]|%s)" % (_IDENT, _IDENT))
# Diagrams are code, in a fenced block. Reading the whole file meant any prose
# containing an arrow became a diagram node, so the traceability check reported
# orphans that were sentences.
_FENCE = re.compile(r"(?s)```[^\n]*\n(.*?)```")


def _label_text(raw):
    return raw.strip("[](){}<>/\\ ").strip("\"'").strip()


def _diagram_nodes(t):
    """(nodes, kinds, skipped, states) for every fenced diagram in an artifact.

    nodes maps a node id to the label written on it, because a node is traceable
    by either. kinds lists the diagram types declared. skipped names every token
    this parser deliberately did not treat as a node, and WHY, because a token
    dropped in silence is a completeness claim over a truncated set. states is
    the subset of node ids that came out of a state diagram, because a state is
    neither an entity nor a runtime component and holding it to either was a
    false failure with no documented way out.
    """
    # HTML comments are not diagram source. Left in, the "-->" that closes one
    # reads as a Mermaid edge and invents a node out of the next word.
    t = without_comments(t)
    nodes, kinds, skipped, states = {}, [], [], set()

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
            # Read as a flowchart, an unrecognised dialect turned its own
            # statement keywords into orphan node names and FAILed a correct
            # diagram. SKILL.md L5's own rule is that a type this tool cannot
            # trace is NO-DATA and not a failure, so it is not read, it is
            # reported, and check_diagrams turns it into NO-DATA.
            kinds.append("unrecognised:%s" % first)
            skipped.append("%s (a diagram type this tool has no parser for, so nothing in this "
                           "block was read as a node)" % first)
            continue
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
                            states.add(g)
                continue
            if kind == "mindmap":
                if s.startswith("::") or word.startswith("::icon"):
                    skipped.append("%s (a %s style statement, not a node)" % (word, first))
                    continue
                m = _NODE_LABELLED.search(s)
                if m:
                    add(m.group(1), _label_text(m.group(2)))
                elif s.strip("()[]{}"):
                    # A bare line IS a node in a mindmap. Reading only the
                    # shaped root and dropping the children was a half-parse:
                    # the verdict said "all traceable" over children it never
                    # read.
                    add(_label_text(s))
                continue
            if kind == "c4":
                m = _C4_CALL.match(s)
                if not m:
                    if word and any(ch.isalnum() for ch in word):
                        skipped.append("%s (a %s statement, not an element)" % (word, first))
                    continue
                keyword, alias, label = m.group(1), m.group(2), (m.group(3) or "").strip()
                if keyword in _C4_GROUPING:
                    # A boundary groups elements, exactly as `subgraph` does in a
                    # flowchart, and a flowchart's subgraph is skipped and named.
                    skipped.append("%s(%s) (a %s boundary, which groups elements rather than "
                                   "being one)" % (keyword, alias, first))
                    continue
                if keyword in _C4_ELEMENT:
                    add(alias, label)
                    continue
                if keyword in _C4_REL:
                    args = [a.strip().strip("\"") for a in s[s.find("(") + 1:].split(",")]
                    for a in args[:2]:
                        if re.match(r"^[A-Za-z_][\w.-]*$", a):
                            add(a)
                    continue
                skipped.append("%s (a %s statement, not an element)" % (keyword, first))
                continue
            if kind == "block":
                if word.split(":")[0] in _BLOCK_STATEMENTS or s.startswith("%%"):
                    skipped.append("%s (a %s statement, not a block)" % (word, first))
                    continue
                s = _strip_edge_labels(s, skipped)
                for m in _NODE_LABELLED.finditer(s):
                    add(m.group(1), _label_text(m.group(2)))
                bare = _NODE_LABELLED.sub(" ", s)
                for m in _BLOCK_TOKEN.finditer(bare):
                    if m.group(1) not in _BLOCK_STATEMENTS:
                        add(m.group(1))
                continue
            if kind == "none":
                continue
            # flowchart, graph and the node-shaped types
            if word in _FLOW_STATEMENTS or s.startswith("%%"):
                skipped.append("%s (a %s statement, not a node)" % (word, first))
                continue
            s = _strip_edge_labels(s, skipped)
            for m in _NODE_LABELLED.finditer(s):
                add(m.group(1), _label_text(m.group(2)))
            bare = _NODE_LABELLED.sub(" ", s)
            for m in _NODE_SOURCE.finditer(bare):
                add(m.group(1))
            for m in _NODE_DEST.finditer(bare):
                add(m.group(1))
    return nodes, kinds, sorted(set(skipped)), states


_COMPONENT_HEADING = re.compile(r"(?i)component|runtime|technology map")
_STATE_HEADING = re.compile(r"(?i)state|status|lifecycle")


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
        tech = _plain(without_comments(tech))
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
    # Bullets under a component-naming heading count in EITHER file, which is
    # what L5's INPUTS line promises: a technology map written as bullets is
    # the honest form half the discipline uses, and reading bullets only out of
    # 06-diagrams.md made the law overclaim against its own tool.
    for artifact in (ARTIFACT_FILES["04"], ARTIFACT_FILES["06"]):
        text = read(root, artifact)
        if text is None:
            continue
        text = _plain(without_comments(text))
        in_components = False
        for line in text.splitlines():
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
                    out.setdefault(_norm(name), "%s: %s" % (artifact, name))
    return out


def _declared_states(root):
    """Lifecycle states a state diagram is allowed to name, and where each was declared.

    The third traceability target, and it exists because the second one was
    being abused. A `stateDiagram-v2` of an entity's lifecycle FAILed by default:
    a state is not an entity and not a runtime component, no document anywhere
    told an author how to make one trace, and the only way through was to declare
    Draft, Placed and Shipped as runtime COMPONENTS. That is exactly the
    pathology L5 removed for queues (corrupting a model to please a tool),
    reproduced one diagram type over.

    A state is declared as a bullet under a heading naming states, statuses or a
    lifecycle, in 05-data-model.md or in 06-diagrams.md itself, or in a
    `status: draft | placed | shipped` line in the data model. Declared
    somewhere and traceable, without pretending a state is a service.
    """
    out = {}
    for artifact in (ARTIFACT_FILES["05"], ARTIFACT_FILES["06"]):
        text = read(root, artifact)
        if text is None:
            continue
        text = without_comments(text)
        in_states = False
        for line in _joined_bullets(text.splitlines()):
            h = _HEADING.match(line)
            if h:
                in_states = bool(_STATE_HEADING.search(h.group(2)))
                continue
            m = re.match(r"(?i)^\s*[-*|]?\s*(?:status|state|lifecycle)\s*(?:values)?\s*[:=]\s*(.+)$",
                         line)
            if m:
                for token in re.split(r"[,|/]| or | then |->|-->", m.group(1)):
                    name = token.strip().strip(".;`").strip()
                    if name and not domain_vacuous(name):
                        out.setdefault(_norm(name), "%s: %s" % (artifact, name))
                continue
            if not in_states:
                continue
            b = _BULLET.match(line)
            if b:
                name = b.group(1).split(":")[0].strip()
                if name and not domain_vacuous(name):
                    out.setdefault(_norm(name), "%s: %s" % (artifact, name))
    return out


def check_diagrams(root):
    problem = read_problem(root, ARTIFACT_FILES["06"])
    if problem:
        return "FAIL", ("%s is %s; an artifact that exists and cannot be read is a broken claim, "
                        "not an absent one" % (ARTIFACT_FILES["06"], problem))
    t = read(root, ARTIFACT_FILES["06"])
    if t is None:
        return "NO-DATA", "no 06-diagrams.md in this dossier"
    nodes, kinds, skipped, states = _diagram_nodes(t)
    # Every skipped token, on every verdict line. A parser that discards tokens in
    # silence and then reports "all traceable" is asserting completeness over a
    # set it truncated itself.
    note = ("; tokens read as diagram syntax rather than as nodes: %s" % ", ".join(skipped)) if skipped else ""
    if not kinds:
        return "FAIL", ("no fenced code block holding a diagram; a diagram artifact with no diagram "
                        "in it is a defect. Diagrams are code: put the Mermaid source in a "
                        "```mermaid fence so it diffs in review")
    if not nodes:
        # A gantt or a pie chart is a real diagram that names no element this
        # check can trace, and a dialect this tool has no parser for is a diagram
        # it did not read. Failing either as "a diagram artifact with no diagram
        # in it" is rejecting correct work, which gets the gate switched off, and
        # a gate that is off catches less than a gate that is honest.
        bare = [k for k in kinds
                if DIAGRAM_TYPES.get(k) == "none" or k.startswith("unrecognised:")]
        if bare and len(bare) == len(kinds):
            return "NO-DATA", ("%s diagram(s) present, and nothing in them could be read as a node "
                               "this check can trace (the type declares none, or this tool has no "
                               "parser for it), so nothing here was checked for traceability%s"
                               % (", ".join(sorted(set(bare))), note))
        return "FAIL", ("fenced %s block(s) found but no diagram node could be read out of them; a "
                        "diagram artifact with no diagram in it is a defect%s"
                        % (", ".join(sorted(set(kinds))), note))
    model = read(root, ARTIFACT_FILES["05"])
    entities = {_norm(n): n for n in _entities(model)} if model is not None else {}
    components = _declared_components(root)
    declared_states = _declared_states(root)
    known = dict(components)
    known.update(entities)
    known.update(declared_states)
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
    # A state whose dossier declares no states at all is not an orphan, it is
    # unmeasured. Reporting FAIL over it rejected a correct entity-lifecycle
    # diagram and pushed authors to declare their states as runtime components;
    # reporting PASS over it would be this project's own defect. So the check
    # says which nodes it could not trace and why, and returns NO-DATA, which
    # neither blocks a merge nor claims anything.
    untraced_states = sorted(n for n in orphans if n in states) if not declared_states else []
    orphans = [n for n in orphans if n not in untraced_states]
    if orphans:
        placeholders = [n for n in orphans if domain_vacuous(n)]
        placeholder_note = ("" if not placeholders else
                            " Of these, %s name(s) nothing: a node called TBD or XXX is a note to "
                            "the author, and declaring it as a state or a component would not make "
                            "it one." % ", ".join(placeholders[:4]))
        return "FAIL", ("diagram element(s) appear nowhere else in the dossier: %s.%s Every node must be an "
                        "entity in %s or a declared component (a row in %s, or a bullet under a Components "
                        "heading in %s or %s), matched on the node id or on its label. A state diagram's states "
                        "trace to states declared as bullets under a States, Status or Lifecycle heading, "
                        "or to a `status: draft | placed | shipped` line in %s%s"
                        % (", ".join(orphans[:6]), placeholder_note, ARTIFACT_FILES["05"],
                           ARTIFACT_FILES["04"], ARTIFACT_FILES["04"], ARTIFACT_FILES["06"],
                           ARTIFACT_FILES["05"], note))
    if untraced_states:
        return "NO-DATA", ("%d diagram node(s) in %s, of which %d are lifecycle state(s) this dossier "
                           "declares nowhere (%s), so their traceability was not checked and this "
                           "check cannot say every node traces. Declare the states as bullets under a "
                           "States, Status or Lifecycle heading in %s, or as a `status: draft | placed "
                           "| shipped` line, and they become traceable%s"
                           % (len(nodes), ", ".join(sorted(set(kinds))), len(untraced_states),
                              ", ".join(untraced_states[:6]), ARTIFACT_FILES["05"], note))
    hits = [resolved(nid, label) for nid, label in nodes.items()]
    comp_hits = [h for h in hits if h in components and h not in entities]
    # Declaration and use in one file is a weaker trace than a cross-artifact
    # one, and the sentence used to hide the difference: a lone 06-diagrams.md
    # listing its own nodes as Components bullets satisfied "all traceable"
    # without anything outside the file agreeing. Still accepted (the bullet is
    # a declaration a reader can find), but said out loud.
    self_declared = sorted(set(h for h in comp_hits
                               if components[h].startswith(ARTIFACT_FILES["06"])))
    self_note = ("" if not self_declared else
                 "; %d of the component trace(s) resolve to bullets declared in this artifact "
                 "itself, so for those the declaration and the diagram are one file; a row in %s "
                 "is the cross-artifact form" % (len(self_declared), ARTIFACT_FILES["04"]))
    return "PASS", ("%d diagram node(s) in %s, all traceable: %d to entities in %s, %d to declared "
                    "components, %d to declared lifecycle states%s%s"
                    % (len(nodes), ", ".join(sorted(set(kinds))),
                       sum(1 for h in hits if h in entities),
                       ARTIFACT_FILES["05"],
                       len(comp_hits),
                       sum(1 for h in hits if h in declared_states and h not in entities
                           and h not in components), self_note, note))


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
        check_artifacts, reads=(INTAKE,), kind="json", severity="gate",
        full_fixture={"files": {
            INTAKE: {"tier": "T1",
                     "answers": {"changes_contract": False, "crosses_boundary": True,
                                 "reversible_under_hour": True, "touches_sensitive": False,
                                 "consumers": "none"}},
            ARTIFACT_FILES["01"]: _FX_PURPOSE}}),
    "adr": Check(check_adr, reads=(ARTIFACT_FILES["03"],), kind="text", severity="gate", empty_expect="FAIL",
                 empty_note="a dossier that carries an empty 03-adr.md claims a decision record and "
                            "supplies none, which is a broken claim rather than an absence",
                 full_fixture={"files": {ARTIFACT_FILES["03"]: _FX_ADR}}),
    "datamodel": Check(check_data_model, reads=(ARTIFACT_FILES["05"],), kind="text", severity="gate", empty_expect="FAIL",
                       empty_note="an empty 05-data-model.md declares zero entities while claiming to "
                                  "be the data model, and zero entities each with a system of record "
                                  "is the vacuous PASS this check exists to prevent",
                       full_fixture={"files": {ARTIFACT_FILES["05"]: _FX_DATA_MODEL}}),
    "diagrams": Check(check_diagrams, reads=(ARTIFACT_FILES["06"], ARTIFACT_FILES["05"]), kind="text", severity="gate",
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
    "placeholder": Check(check_placeholder, reads=tuple(ARTIFACT_FILES.values()), kind="text", severity="gate",
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


def parse_exemption(text):
    """(checks waived, reason, problem) for a `.sbe-exempt` file.

    Format, and it is not free text any more:

        checks: adr, diagrams
        reason: this dossier was closed in 2024 and is kept for history; the
                decision record it points at moved to the archive.

    An exemption used to be a paragraph, and waiving EVERYTHING was what a
    paragraph did by default: three words of filler switched off all five design
    checks for a directory, and nothing in the file said which checks the author
    thought they were waiving. Waiving everything by default is not an exemption,
    it is an off switch. So the checks are named, one by one, and an author who
    means all of them says all of them. The reason is held to the same
    reviewability threshold as a tier override, because an exemption waives
    strictly more than an override does.

    What this does NOT do, stated plainly rather than implied: it cannot tell a
    real reason from a well-formed fake one. No mechanical test can. That is why
    the waiver prints as WAIVED rather than PASS, names every check it covers,
    and is surfaced in CI as something a human is shown.
    """
    checks, reason_lines, seen_reason = [], [], False
    for line in (text or "").splitlines():
        m = re.match(r"(?i)^\s*checks\s*:\s*(.*)$", line)
        if m and not seen_reason:
            checks.extend(c.strip() for c in re.split(r"[,\s]+", m.group(1)) if c.strip())
            continue
        m = re.match(r"(?i)^\s*reason\s*:\s*(.*)$", line)
        if m:
            seen_reason = True
            reason_lines.append(m.group(1))
            continue
        if seen_reason:
            reason_lines.append(line)
    reason = " ".join(l.strip() for l in reason_lines if l.strip()).strip()
    if not checks and not seen_reason:
        return [], (text or "").strip(), (
            "it names no checks and no reason. An exemption states which of the %d design checks it "
            "waives and why, as two fields:  checks: %s  and  reason: <at least %d words>. A file of "
            "free text waives everything by default, which is an off switch and not an exemption"
            % (len(CHECKS), ", ".join(CHECKS), OVERRIDE_MIN_WORDS))
    if not checks:
        return [], reason, ("it records a reason but names no checks; list the ones it waives "
                            "(checks: %s), because an exemption that names nothing waives everything"
                            % ", ".join(CHECKS))
    unknown = [c for c in checks if c not in CHECKS]
    if unknown:
        return [], reason, ("it waives %s, which %s not a design check; the checks are %s"
                            % (", ".join(unknown), "are" if len(unknown) > 1 else "is",
                               ", ".join(CHECKS)))
    problem = _reviewability_problem(reason, "exemption reason")
    if problem:
        return [], reason, problem
    return checks, reason, ""


def find_dossiers(root):
    """Walk for directories carrying ANY numbered dossier artifact.

    Anchoring on 00-intake.json alone meant deleting one file removed the whole
    design gate from a repository-wide run: seven filled artifacts with no intake
    were never opened, and --strict exited 0. Any numbered artifact makes a
    directory a dossier; check_artifacts then FAILs it by name for the missing
    intake, because the tier cannot be established without it.
    """
    hits, exempt, refused = [], [], []
    pruner = Pruner()
    # onerror: a directory this walk cannot enter may hold a dossier, and os.walk
    # swallows the refusal by default, so a chmod 000 design/ directory made the
    # run print "no directory contains 00-intake.json" about a tree that held
    # one, at exit 0, with five checks silently removed. The refusal now lands in
    # the note every dossier line prints.
    for dp, dns, fns in os.walk(root, onerror=pruner.onerror):
        dns[:] = pruner(dp, dns)
        if not (INTAKE in fns or (set(fns) & set(ARTIFACT_FILES.values()))):
            continue
        if EXEMPT in fns:
            # `touch .sbe-exempt` waived all five checks for a dossier and the
            # report printed the sentence ".sbe-exempt names why: no reason
            # recorded", which asserts a reason while naming its absence. Then a
            # reviewable-length paragraph waived all five without naming one of
            # them. An exemption waives strictly more than a tier override does,
            # so it is held to the override's threshold AND has to say what it
            # waives. An exemption that does neither does not exempt: the dossier
            # is checked, and the broken exemption is its own failure, so that
            # nobody discovers it by noticing the gate went quiet.
            waived, reason, problem = parse_exemption(read(dp, EXEMPT))
            if problem:
                refused.append((dp, problem))
                hits.append(dp)
                continue
            exempt.append((dp, waived, reason))
            # A partial exemption still gets checked for everything it did not
            # waive. Only a dossier that waived every check drops out of the walk.
            if sorted(waived) != sorted(CHECKS):
                hits.append(dp)
            continue
        hits.append(dp)
    return hits, exempt, refused, pruner.note(
        lambda f: f == INTAKE or f in set(ARTIFACT_FILES.values()))


def main():
    strict = "--strict" in sys.argv
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    root = "."
    roots = []
    which = list(CHECKS)
    for a in argv:
        if a in CHECKS:
            which = [a]
        elif os.path.isdir(a):
            roots.append(a)
            root = a
        else:
            print("sbe_design: %r is neither a check name (%s) nor a directory."
                  % (a, ", ".join(CHECKS)))
            sys.exit(1)
    if len(roots) > 1:
        # The last one used to win in silence: a failing dossier passed first
        # on the command line was neither checked nor mentioned while --strict
        # exited 0 on the survivor.
        print("sbe_design: one directory at a time, got %d (%s)."
              % (len(roots), ", ".join(roots)))
        sys.exit(1)
    # SBE_DOSSIER_ROOT is the declaration that this repository keeps dossiers.
    # Declared and empty is a broken configuration, so it FAILS; undeclared and
    # empty is a repository with nothing to check, which is NO-DATA and says so.
    configured = os.environ.get("SBE_DOSSIER_ROOT", "").strip()
    if configured:
        root = configured
    fails = 0
    waivers = 0
    # A waiver is not a pass, so CI must be able to act on one without reading
    # prose. --strict-waivers turns every waiver into a failure for teams that
    # want an exemption to expire on contact; without it the run still exits 0
    # and the shipped workflow surfaces the WAIVED line as an annotation a human
    # is shown. Either way the machine can tell a waiver from a verdict.
    strict_waivers = "--strict-waivers" in sys.argv
    print("BROTHERSBE DESIGN CHECKS  (advisory unless --strict; NO-DATA is never a pass; "
          "WAIVED is not a pass either)")
    exempt, refused, pruned = [], [], ""
    if os.path.isdir(root):
        # ALWAYS walk. This used to be `if is_dossier(root): targets = [root]`,
        # so a root that was itself a dossier skipped the walk that finds every
        # other one, and a stray `00-intake.json` in a repository root made every
        # dossier below it invisible: `--strict` printed five NO-DATA lines and
        # exited 0 over a tree holding seven unedited templates. `sbe_intake.py`
        # writes exactly that file to the directory it is run from, and the README
        # tells the reader to run it, so the off switch installed itself.
        # A root that is itself a dossier is one more dossier, not a reason to
        # stop, and find_dossiers reports it as one because os.walk starts there.
        targets, exempt, refused, pruned = find_dossiers(root)
    else:
        targets = []
    waived_by = {os.path.abspath(d): set(w) for d, w, _ in exempt}
    for d, waived, why in exempt:
        # Printed as a WAIVER, never as a pass and never in silence, and marked
        # so that it cannot be skimmed as one: PASS is a verdict about work that
        # was examined, and this is a declaration that nothing examined it. The
        # line names the directory and every check the waiver covers, because an
        # exemption nobody can see is an exemption nobody can withdraw, and a
        # dossier from last year blocking every unrelated merge forever is a gate
        # that gets switched off instead.
        waivers += len(waived)
        print("  %-10s %-8s %s" % (">> dossier", "WAIVED", one_line(
              "%s: %s waives %s here (of %d design checks), stated reason: %s. Nothing opened a file "
              "for %s in that directory, so this is a waiver and not a verdict about the work"
              % (os.path.relpath(d, root), EXEMPT, ", ".join(sorted(waived)), len(CHECKS),
                 " ".join(why.split())[:200],
                 "those checks" if len(waived) < len(CHECKS) else "any check"))))
    for d, problem in refused:
        fails += 1
        print("  %-10s %-8s %s" % ("dossier", "FAIL", one_line(
              "%s carries a %s that does not exempt anything: %s. An exemption waives all %d design "
              "checks for a dossier, which is more than a tier override waives, so it states a "
              "reviewable reason or it does not exempt; this dossier is checked below"
              % (os.path.relpath(d, root), EXEMPT, problem, len(CHECKS)))))
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
                  "root is a broken configuration, not an absence%s" % (root, INTAKE, pruned)))
        else:
            print("  %-10s %-8s %s" % ("dossier", "NO-DATA",
                  "no dossier found under %s: no directory contains %s or any of 01 through 07. If this "
                  "repository is supposed to carry one, set SBE_DOSSIER_ROOT to where dossiers live and "
                  "this becomes a FAIL instead of a report%s" % (root, INTAKE, pruned)))
        # Every requested check still accounts for itself. A check that prints no
        # line is indistinguishable from a check that was removed, and "the gate
        # said nothing" must never be readable as "the gate was satisfied".
        # The phrase "so this check opened no file" is load-bearing: it is how
        # evals/test_no_data_class.py tells a verdict this fallback printed from a
        # verdict the check itself produced, so a scenario cannot be counted as
        # covering a check it never reached. Change it in both places or not at all.
        for name in which:
            # Two different absences, two different sentences: "no dossier under
            # X" printed two lines under a waiver naming one was a run
            # contradicting itself. The load-bearing phrase stays in both.
            if exempt:
                print("  %-10s %-8s %s" % (name, "NO-DATA",
                      "every dossier under %s is waived, so this check opened no file%s"
                      % (root, pruned)))
            else:
                print("  %-10s %-8s %s" % (name, "NO-DATA",
                      "no dossier under %s, so this check opened no file%s" % (root, pruned)))
    if targets and pruned:
        # A dossier the walk refused to enter is a dossier no verdict below covers.
        print("  %-10s %-8s %s" % ("dossier", "NO-DATA",
              "%d dossier(s) checked under %s%s" % (len(targets), root, pruned)))
    for target in targets:
        if len(targets) > 1 or os.path.abspath(target) != os.path.abspath(root):
            print("  dossier: %s" % os.path.relpath(target, root))
        skip = waived_by.get(os.path.abspath(target), set())
        for name in which:
            if name in skip:
                waivers += 1
                print("  %-10s %-8s %s" % (">> " + name, "WAIVED",
                      "%s in %s names this check, so nothing opened a file for it here"
                      % (EXEMPT, os.path.relpath(target, root))))
                continue
            verdict, ev = run_guarded(name, CHECKS[name], target)
            if verdict == "FAIL":
                fails += 1
            # one_line: evidence quotes artifact content, and an artifact
            # carrying a newline must not write its own report lines.
            print("  %-10s %-8s %s [severity: %s]"
                  % (name, verdict, one_line(ev), CHECKS[name].severity))
    if waivers:
        print("WAIVERS: %d check(s) were waived by a %s and examined nothing. A waiver is not a "
              "pass; run `--strict --strict-waivers` to make one block a merge." % (waivers, EXEMPT))
    if strict_waivers and waivers:
        fails += waivers
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
