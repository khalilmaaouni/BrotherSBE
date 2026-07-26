#!/usr/bin/env python3
"""The registry contract every BrotherSBE check is registered under.

Why this file exists. Six named instances of one defect were fixed by hand and
the same defect was found alive in four more places inside the same files. A
check that reports PASS over evidence it never examined converts absence into
false assurance, which is the failure this whole project exists to prevent. One
more hand fix would have removed six more instances and left the class.

So a check is no longer just a function. A check is a function PLUS a mechanical
declaration of what it reads, what its empty states are, and a worked positive
example of its evidence:

  reads          the evidence file(s) or tree the check opens
  kind           how that evidence is shaped, which decides what "malformed" means
  item_key       for a JSON receipt holding a list, the key naming that list
  empty_expect   the verdict when the evidence exists and declares nothing
  full_fixture   evidence that SHOULD pass, from which the honesty test derives
                 the empty-value shapes mechanically
  full_expect    the verdict full_fixture produces, PASS unless the check cannot
                 reach PASS on any evidence this host can build, in which case
                 full_expect_reason says why and is printed on every run
  optional_leaves fields in full_fixture the PASS sentence does not assert over,
                 each with a stated reason, printed on every run

Two rounds of this fix modelled "absent evidence" as an absent FILE, and the
defect survived as absent VALUES: a receipt that exists, parses, carries every
key, and holds "" in all of them. `full_fixture` exists so that no one has to
think of that shape again. The honesty test hollows the declared fixture leaf by
leaf, subtree by subtree, and whole, in empty strings, whitespace and nulls, and
requires that none of it produces a PASS. A field nobody empties is a field
nobody tested.

A fourth round found the same defect one level deeper again: the value was
present, non-empty, and vacuous. `snapshot_id: "TODO"` with `primary` and
`secondary` both `"pending"` produced "1 figure(s) each with a pinned,
independently re-derived, zero-drift check" and exit 0. The defence already
existed in this repository, as a private constant in one tool that no gate
imported, which is why VACUOUS_VALUES and `answered()` live in THIS file: one
definition, imported everywhere, extended in one place.

empty_expect can never be PASS. The constructor refuses it.

What that guarantee is, exactly, stated without overclaim after three rounds of
this claim being too broad: the DECLARATION is enforced by this constructor (a
check cannot be registered that names PASS as its empty state, and cannot be
registered without a positive fixture to hollow), and the RUNTIME is tested by
evals/test_no_data_class.py over the registries it discovers and the scenarios
it derives. It is not a proof over all inputs. It is an enforced declaration plus
a mechanical scenario sweep, and the sweep prints its own coverage so the claim
is checkable rather than asserted.
"""

import errno, glob as _glob, json, math, os, re, stat, unicodedata

KINDS = ("json", "jsonl", "text", "tree", "git")


def evidence_problem(path):
    """Why this path exists and still cannot be read as evidence, or "" if it can.

    The ACCESS axis. Seven review rounds probed what the evidence SAYS: absent
    files, absent keys, empty values, vacuous values, wrong order. The axis nobody
    probed was whether the tool could OPEN the evidence at all: a chmod 000 source
    file vanished from a lint's count, a chmod 000 registry file turned two FAILs
    into two PASSes whose sentences said "none", and a FIFO where a receipt was
    expected hung every tool forever with no verdict in either mode.

    The rule, in one place so every tool applies the same one: a path that is
    absent is an absence (the caller's NO-DATA); a path that EXISTS and cannot be
    read is a broken claim and is named. A FIFO, socket or device is refused here
    BY ITS STAT, before any open(), because open() on a FIFO blocks forever and a
    gate that vanishes is worse than a gate that fails.

    Returns "" both for an absent path and for a readable regular file: the
    caller distinguishes those two with os.path.lexists, which never blocks.

    An "absent" path is only known to be absent when the tree above it can be
    entered. The axis was closed on the evidence FILE and stayed open one level
    up: chmod 000 on a PARENT directory made lexists() return False, the
    caller read that as an absence, and a FAIL became a NO-DATA (or a PASS
    saying "none") over evidence sitting on disk. So absence is now checked
    against the nearest existing ancestor: if that ancestor cannot be entered,
    this path's existence is unknowable, which is a broken claim and is named.
    """
    if not os.path.lexists(path):
        parent = os.path.dirname(os.path.abspath(path))
        while True:
            if os.path.lexists(parent):
                if os.path.isdir(parent) and not os.access(parent, os.X_OK | os.R_OK):
                    return ("inside a directory that cannot be entered (%s), so whether it "
                            "even exists could not be checked" % parent)
                return ""
            up = os.path.dirname(parent)
            if up == parent:
                return ""
            parent = up
    try:
        st = os.stat(path)
    except OSError as e:
        if getattr(e, "errno", None) == errno.ELOOP:
            return "a symlink loop, which resolves to nothing"
        if isinstance(e, FileNotFoundError):
            return "a symlink pointing at nothing"
        return "present but not statable (%s)" % type(e).__name__
    if stat.S_ISDIR(st.st_mode):
        return "a directory, not a file"
    if not stat.S_ISREG(st.st_mode):
        return ("not a regular file (a pipe, socket or device; opening one can block "
                "forever, so it is refused by name instead)")
    if not os.access(path, os.R_OK):
        return "present but unreadable (permission denied)"
    return ""

def glob_with_denials(pattern):
    """(paths this glob matches, directories it could not look inside).

    glob.glob returns FEWER paths, not an error, when a directory along the
    pattern cannot be entered: an unreadable parent never enters the result,
    so to the caller the evidence is not unreadable, it is absent, and a FAIL
    over the files inside it became a PASS whose sentence said "none". The
    per-file ACCESS check ran only over what discovery returned, which is the
    file-level fix applied to the file it was going to open rather than to the
    evidence the pattern claimed to cover.

    So discovery itself accounts for what it could not see: every directory
    matched by any PREFIX of the pattern is checked for enterability, and the
    denied ones come back by name for the caller's verdict to carry. The
    checks that consume this treat a denial like an unreadable registry file:
    a FAIL, never a smaller evidence set.
    """
    pattern = os.path.expanduser(pattern)
    hits = _glob.glob(pattern, recursive=True)
    denied = []
    parts = pattern.split(os.sep)
    for i in range(1, len(parts)):
        prefix = os.sep.join(parts[:i])
        if not prefix.strip(os.sep):
            continue
        for d in _glob.glob(prefix, recursive=True):
            if os.path.isdir(d) and not os.access(d, os.X_OK | os.R_OK):
                denied.append(d)
    for d in hits:
        if os.path.isdir(d) and not os.access(d, os.X_OK | os.R_OK):
            denied.append(d)
    return hits, sorted(set(denied))


# Directories no check walks into, in one place because the three tools that walk
# a repository each carried their own list and the shortest of them was on the one
# gate that cannot be waived. `tools/sbe_score.py` skipped exactly `.venv` and
# `venv`, so a virtualenv called `.venv-whisper` put third-party code through the
# silent-failure lint: 1127 hits in 8109 files against a real repository on the
# author's machine, every one of them inside a vendored site-packages, with no
# `.sbe-exempt` path out because that file is read only by the design checks. A
# team that cannot fix the code the gate fails on and cannot waive it switches the
# gate off, which costs more than any hole this project has closed.
#
# And then the cure had the disease. The list was a list of NAMES, so `mv plain
# vendor` turned two FAILs into two NO-DATAs at exit 0, and the evidence line
# said "no directory contains 00-intake.json" about a tree that held one.
# Discovery that depends on what somebody named a directory is the defect this
# file's own docstrings say discovery must not have.
#
# So: a directory is pruned when something INSIDE it identifies it as somebody
# else's code or a generated cache. A name may corroborate a marker. A name may
# never prune on its own. The consequence is stated rather than hidden: a hand
# vendored tree carrying no marker IS walked, and the lint reads it.
SKIP_MARKERS = ("pyvenv.cfg", "CACHEDIR.TAG")
NODE_MARKERS = (".package-lock.json", ".yarn-integrity", ".modules.yaml", ".bin")


def skip_reason(parent, name):
    """Why this directory holds somebody else's code, or None when it is ours.

    Every branch reads the directory's CONTENTS. `node_modules` is the one place
    a name appears at all, and it appears next to a marker, never instead of one.
    """
    path = os.path.join(parent, name)
    try:
        entries = set(os.listdir(path))
    except OSError:
        # Not readable is not the same as not ours. Left in the walk, where the
        # caller's own error handling reports it.
        return None
    if "pyvenv.cfg" in entries:
        return "a virtualenv (it carries pyvenv.cfg)"
    if any(e.endswith((".dist-info", ".egg-info", ".egg-link")) for e in entries):
        return "installed third-party packages (it carries .dist-info or .egg-info entries)"
    if name in ("site-packages", "dist-packages") and entries:
        # Structural, not nominal: an installed-packages directory sits under a
        # `lib/pythonX.Y/` path, which is a shape a repository does not have by
        # accident. A directory called site-packages anywhere else is walked.
        parts = os.path.normpath(parent).split(os.sep)[-3:]
        if any(p in ("lib", "lib64") or p.startswith("python") for p in parts):
            return "installed third-party packages (a %s directory under a lib/pythonX.Y path)" % name
    if "CACHEDIR.TAG" in entries:
        return "a tool cache (it carries CACHEDIR.TAG)"
    if {"HEAD", "objects", "refs"} <= entries:
        return "a version-control object store (it carries HEAD, objects and refs)"
    if entries and all(e.endswith((".pyc", ".pyo")) for e in entries):
        return "compiled bytecode only (every entry is a .pyc or .pyo)"
    if name == "node_modules" and entries:
        if entries & set(NODE_MARKERS):
            return "installed node packages (a node_modules tree carrying package metadata)"
        for e in sorted(entries)[:20]:
            if os.path.isfile(os.path.join(path, e, "package.json")):
                return "installed node packages (its entries carry their own package.json)"
    return None


class Pruner:
    """os.walk pruning that keeps a record of what it removed, and why.

    The second half of the fix, and the half that matters more. Pruning is how a
    FAIL becomes a NO-DATA in silence: the check opens nothing, reports an
    absence, and the sentence it prints is false about the tree. Every walker in
    this project now prunes through one of these and prints `note()` on its
    verdict, so a directory that was not examined is a directory a reader is
    told about.
    """

    LIMIT = 4000        # directories inspected while looking for hidden evidence

    def __init__(self):
        self.pruned = []            # (path, reason)
        self.denied = []            # directories os.walk could not enter

    def __call__(self, parent, dirnames):
        """For os.walk's `dns[:] = pruner(dp, dns)`."""
        keep = []
        for d in sorted(dirnames):
            path = os.path.join(parent, d)
            if os.path.islink(path):
                # os.walk(followlinks=False) never descends into a symlinked
                # directory, and nothing said so: a symlinked source tree holding
                # a lint hit was neither walked, nor pruned, nor recorded, and the
                # verdict printed "clean" over a set that silently excluded it.
                # Recorded as pruned, so hidden() inspects the target and note()
                # names it when it holds evidence this walk was looking for.
                self.pruned.append((path, "a symlinked directory, which this walk does not follow"))
                continue
            why = skip_reason(parent, d)
            if why is None:
                keep.append(d)
            else:
                self.pruned.append((path, why))
        return keep

    def onerror(self, err):
        """For os.walk's `onerror=`: a directory the walk could not enter.

        os.walk swallows the OSError and yields nothing by default, so a
        chmod 000 directory was neither walked, nor pruned, nor reported, and
        the meta-test's own guarantee sentence returned to "0 failure(s)" over a
        tree it could not see into. Every walker passes this, and note() names
        what was refused on every verdict.
        """
        self.denied.append(getattr(err, "filename", None) or "?")

    def hidden(self, wanted):
        """(pruned trees holding a wanted file, pruned trees the budget left uninspected).

        The budget used to be silent: once its 4000 directories were spent, every
        remaining pruned path was discarded without wanted() being called, and
        hidden() returned the same [] it returns when nothing was hidden. A real
        node_modules exceeds 4000 directories, so on exactly the trees this
        machinery exists for, the disclosure vanished. Exhaustion is now its own
        channel and note() prints it.
        """
        out, uninspected, budget = [], [], self.LIMIT
        for path, why in self.pruned:
            if budget <= 0:
                uninspected.append("%s (%s)" % (path, why))
                continue
            found = False
            for _dp, _dns, fns in os.walk(path):
                budget -= 1
                if any(wanted(f) for f in fns):
                    out.append("%s (%s)" % (path, why))
                    found = True
                    break
                if budget <= 0:
                    break
            if budget <= 0 and not found:
                uninspected.append("%s (%s)" % (path, why))
        return sorted(set(out)), sorted(set(uninspected))

    def note(self, wanted):
        """The sentence a verdict carries when this walk did not examine something.

        Three channels, each printed: pruned trees that hold candidate evidence,
        pruned trees the inspection budget never reached, and directories the
        walk was refused entry to. A verdict that stays silent about any of them
        is a completeness sentence over a set the tool truncated itself.
        """
        h, uninspected = self.hidden(wanted)
        parts = []
        if h:
            parts.append("; %d pruned director(y/ies) hold file(s) this check reads and were NOT "
                         "examined, so this verdict does not cover them: %s"
                         % (len(h), "; ".join(h[:4])))
        if uninspected:
            parts.append("; %d pruned director(y/ies) were not fully inspected (the %d-directory "
                         "inspection budget ran out), so this verdict cannot say whether they hold "
                         "files this check reads: %s"
                         % (len(uninspected), self.LIMIT, "; ".join(uninspected[:4])))
        if self.denied:
            d = sorted(set(self.denied))
            parts.append("; %d director(y/ies) could not be entered (permission or I/O error), so "
                         "this verdict does not cover them: %s" % (len(d), "; ".join(d[:4])))
        return "".join(parts)


VERDICTS = ("PASS", "FAIL", "NO-DATA")


class Check:
    def __init__(self, fn, reads, kind, severity=None, item_key=None,
                 empty_expect="NO-DATA", empty_note="", empty_fixture=None,
                 full_fixture=None, no_full_fixture="", optional_leaves=None,
                 full_expect="PASS", full_expect_reason=""):
        if kind not in KINDS:
            raise ValueError("unknown evidence kind %r (expected one of %s)"
                             % (kind, ", ".join(KINDS)))
        if severity not in ("gate", "soft"):
            # Declared at write time, refused otherwise, exactly as PASS-on-empty
            # is refused below. The split used to live in which FILE a check was
            # written into, so a reader could not tell a blocking check from a
            # graded one without tracing the call.
            raise ValueError(
                "a check must declare its severity at write time: 'gate' (a FAIL blocks a "
                "--strict run) or 'soft' (a FAIL is graded, and blocks only under the opt-in "
                "--strict-soft), got %r. Severity says only what a FAIL does to the exit "
                "code; it does not change what the check examines or reports" % (severity,))
        if empty_expect == "PASS":
            raise ValueError(
                "a check may not declare PASS as its empty-evidence verdict: "
                "evidence that declares nothing is NO-DATA when it is an absence "
                "and FAIL when it is a broken claim, and never a pass")
        if empty_expect not in ("NO-DATA", "FAIL"):
            raise ValueError("empty_expect must be NO-DATA or FAIL, got %r" % empty_expect)
        if empty_expect == "FAIL" and not empty_note:
            raise ValueError("a check whose empty evidence FAILs must say why (empty_note)")
        if full_fixture is None and not no_full_fixture:
            raise ValueError(
                "a check must declare full_fixture, a worked example of evidence that SHOULD "
                "pass, so the honesty test can hollow its values and prove the check does not "
                "report PASS over empty ones. A check with no positive example must say why "
                "in no_full_fixture, and that reason is printed on every run")
        if full_fixture is not None:
            if not isinstance(full_fixture, dict) or not full_fixture.get("files"):
                raise ValueError(
                    "full_fixture must be a dict carrying a non-empty 'files' mapping of "
                    "relative path to content (a dict or list is written as JSON, a string "
                    "verbatim), optionally with 'env' and 'git' keys")
        if full_expect not in VERDICTS:
            raise ValueError("full_expect must be one of %s, got %r" % (", ".join(VERDICTS), full_expect))
        if full_expect != "PASS" and not full_expect_reason:
            raise ValueError(
                "a check whose worked positive example does not reach PASS must say why "
                "(full_expect_reason). The honesty test asserts the fixture produces exactly this "
                "verdict, so an unstated ceiling would let a check quietly stop being able to pass")
        fixture_files = (full_fixture or {}).get("files", {}) if isinstance(full_fixture, dict) else {}
        for path, why in (optional_leaves or {}).items():
            if not why:
                raise ValueError(
                    "optional_leaves[%r] has no reason. A field exempted from the empty-value "
                    "sweep is a field nobody tests, so the exemption states why the PASS "
                    "sentence does not assert over it" % path)
            # The key names a leaf or section OF THIS CHECK'S OWN FIXTURE, and
            # nothing else. The sweep matches exemptions by scenario-id prefix,
            # and the id space is wider than the fixture: every seeded
            # scenario's id begins with one word, so a single free-form key
            # could waive the whole generative mode for a check while the
            # printed scenario total never moved. A key is
            # `<fixture file>::<leaf path>` or `<fixture file>##<heading>`;
            # anything else is an off switch wearing an exemption's clothes.
            if not any(path.startswith(f + "::") or path.startswith(f + "##")
                       for f in fixture_files):
                raise ValueError(
                    "optional_leaves[%r] is not a valid exemption key: it does not name a leaf "
                    "('<fixture file>::<leaf path>') or a section ('<fixture file>##<heading>') "
                    "of this check's own full_fixture (files: %s). A key matched by scenario-id "
                    "prefix instead of by fixture leaf can waive an entire sweep at once"
                    % (path, ", ".join(sorted(fixture_files)) or "none"))
        if len(optional_leaves or {}) > 3:
            # The exemption list had no cap and its key space includes scenario
            # ids, so a check that examines nothing could exempt itself from
            # every scenario with a page of boilerplate reasons and still count
            # as covered. Three is a ceiling, not a budget: no shipped check
            # needs more than one, and a check that wants four exemptions is a
            # check whose sentence asserts too much.
            raise ValueError(
                "optional_leaves declares %d exemptions; at most 3 are allowed. A check that "
                "exempts more of its own fixture than that is exempting itself from the sweep "
                "that exists to test it; narrow the PASS sentence instead"
                % len(optional_leaves))
        self.fn = fn
        self.reads = tuple(reads)
        self.kind = kind
        self.severity = severity
        self.item_key = item_key
        self.empty_expect = empty_expect
        self.empty_note = empty_note
        # Some checks read evidence that has no JSON shape at all (a markdown
        # artifact, a source tree, a commit trailer). The meta-test reports those
        # as declared not-applicable rather than skipping them quietly.
        self.empty_fixture = empty_fixture
        self.full_fixture = full_fixture
        self.no_full_fixture = no_full_fixture
        self.optional_leaves = dict(optional_leaves or {})
        self.full_expect = full_expect
        self.full_expect_reason = full_expect_reason

    def __call__(self, *a, **kw):
        return self.fn(*a, **kw)


def stated(value):
    """The value actually recorded here, or None if this field records nothing.

    The one definition of emptiness the whole project shares. Two rounds of
    fixes read absence as a missing FILE and let an empty VALUE through: a
    manifest holding "" in every field parsed, carried every key, and cleared
    every gate, and the evidence line then reported zero drift over two empty
    strings. `is None` is not an emptiness test. This is.

    None, an empty or whitespace-only string, and an empty list, dict or tuple
    all record nothing. False and 0 record something: a zero row count and a
    zero exit code are answers, and a check that treated them as absent would
    reject honest work. A NaN or an infinity records nothing: json.load accepts
    bare NaN, `NaN <= 0` is False, and a receipt carrying one cleared a check
    whose sentence then asserted "a nonzero duration" over a value that is not
    a number of milliseconds of anything.

    This is emptiness only. "TODO" is not empty and records nothing either;
    that is `answered()` below, and a field whose content the verdict sentence
    describes goes through THAT one.
    """
    if value is None:
        return None
    if isinstance(value, float) and _not_a_measurement(value):
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (list, dict, tuple, set)) and not value:
        return None
    return value


# Tokens that are present, non-empty, and still name no answer. ONE list, here,
# because the fourth round of this defect was caused by there being two: this
# module owned `stated()` and sbe_design.py privately owned an equivalent list,
# so the project refused the token "todo" as a system of record and accepted it
# as a pinned warehouse snapshot in the same run. Every tool imports this.
#
# Add to it freely. A token belongs here when a reader seeing it in a receipt
# would learn nothing about the work: it is a note to the author, not a value.
# It does NOT belong here if an engineer could honestly mean it (which is why
# "0", "false" and short real identifiers are absent: a zero row count and a
# zero exit code are answers).
VACUOUS_VALUES = frozenset((
    "todo", "to do", "tbd", "tba", "tbc", "fixme", "xxx",
    "placeholder", "n/a", "na", "none", "null", "nil", "unknown",
    "pending", "-", "--", "---", "?", "??", "???",
    "foo", "bar", "baz", "same", "as above", "see above", "ditto",
    "not decided", "undecided", "not known", "unclear",
    "to be decided", "to be determined",
))

# The scoping decision, in one place, because the list above was being applied to
# things that are not evidence fields at all.
#
# `pending` is a vacuous answer in a receipt and the standard first state of every
# payment, order, job and queue in existence. A reviewer modelled a payment, named
# its first state `pending`, and the diagram check told them the state "appears
# nowhere else in the dossier" while it sat declared four lines above under a
# heading called Lifecycle. The implied fix was to rename a domain concept to
# satisfy a linter, and SKILL.md L5 already carries the sentence that condemns
# that: a check that makes the honest artifact fail is a check that teaches people
# to corrupt it.
#
# So there are two populations and they get two tests:
#
#   EVIDENCE FIELDS   things a person fills in to prove work happened: a
#                     snapshot id, a rehearsal run id, an override reason, a
#                     system of record, an intake answer. `answered()` and
#                     `vacuous()` apply the whole list to these.
#   DOMAIN CONTENT    things the engineer authored as the subject matter: entity
#                     names, state names, diagram node labels, component names.
#                     `domain_vacuous()` applies the list MINUS the words below.
#
# A word belongs here when an engineer can honestly mean it as a name in a model.
# `todo`, `tbd`, `xxx`, `foo` and the punctuation tokens are notes to the author
# in any context, so they stay refused everywhere.
DOMAIN_WORDS = frozenset(("none", "pending", "unknown", "unclear", "undecided", "null", "nil"))
# Leading words that carry no answer of their own: copulas, modals and hedges.
# Stripped to a FIXPOINT inside vacuous(), with the whole test re-run on every
# remnant, because stripping once and testing once was the R7 order bug one
# level in: "is still unknown" lost its "is", left "still unknown", and "still
# unknown" is not in the token list even though "unknown" is, so a two-word
# remnant escaped a test built for whole strings. Any reduction's OUTPUT goes
# back through the whole test until nothing changes.
_LEADING_NOISE = re.compile(
    r"^(?:it\s+is|is|was|are|be|being|been|will\s+be|would\s+be|should\s+be|shall\s+be|"
    r"still|yet|currently|now|probably|likely|maybe|perhaps)\b\s*", re.I)

# The yes/no vocabulary, in one place, for the same reason VACUOUS_VALUES is in
# one place. A fifth round of one defect: the intake asks its five questions as
# "(y/n)" and then read the answers for Python truthiness, so an intake answering
# "n" to every question computed the HIGHEST tier (the string "n" is truthy) and
# an intake answering "no" to "is this reversible" computed the LOWEST one. The
# rule that decides how much evidence a change owes was the one rule reading its
# inputs by truth-of-the-object rather than by meaning, in a file the tools that
# already fixed this shape never imported.
#
# Extended here, once, and every caller that asks "is this answer a yes" gets the
# extension. A token belongs here only if it is unambiguous written down alone: a
# blank, a "maybe" and a "1" are not answers to a yes/no question and are refused
# by name rather than guessed at.
AFFIRMATIVE = frozenset(("true", "yes", "y"))
NEGATIVE = frozenset(("false", "no", "n"))
BOOLEAN_VOCABULARY = tuple(sorted(AFFIRMATIVE | NEGATIVE))


def boolean_answer(value):
    """The yes/no this field records, or None if it records neither.

    A JSON boolean, or one of the words the prompts teach, trimmed and in any
    case. Anything else is None, which every caller turns into a named refusal
    that quotes the value it could not read: "the string false is truthy" is the
    project's own stated law (SKILL.md L14) and this is the function that keeps
    it true wherever a claim is written as a word instead of a boolean.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        # plain_text first: "n" plus one zero-width joiner was neither yes nor
        # no, so the intake tier rule refused a real answer over a character no
        # reader can see. Same normalization as fold() and vacuous(), one place.
        v = " ".join(plain_text(value).split()).strip(" \t.;,:!\"'`").casefold()
        if v in AFFIRMATIVE:
            return True
        if v in NEGATIVE:
            return False
    return None


# The invisible class, closed as a CLASS rather than as a list of code points.
# fold() shipped a five-code-point zero-width list after one invisible character
# made a copy-paste read as an independent second derivation, and the next
# probe appended a SOFT HYPHEN instead: same defect, sixth code point, and the
# list also protected exactly one of the several functions that compare or
# test text. The membership rule is now Unicode's own: every format-class
# character (category Cf covers soft hyphens, zero-widths, directional marks,
# invisible operators and the BOM) plus the visually-empty combining marks
# that are not Cf (variation selectors, the combining grapheme joiner, the
# Mongolian selectors). NFKC runs first, so a compatibility spelling that
# RENDERS as ASCII (a fullwidth TODO) is read as what a reader sees.
_INVISIBLE_MARKS = frozenset(
    "\u034f"                                            # combining grapheme joiner
    + "".join(chr(c) for c in range(0x180B, 0x180E))    # Mongolian variation selectors
    + "".join(chr(c) for c in range(0xFE00, 0xFE10)))   # variation selectors


def _is_invisible(ch):
    return (ch in _INVISIBLE_MARKS or unicodedata.category(ch) == "Cf"
            or 0xE0100 <= ord(ch) <= 0xE01EF)           # variation selectors supplement


def plain_text(text):
    """The text as it renders: compatibility forms folded, invisible characters gone.

    ONE normalization, used by fold(), vacuous() and boolean_answer(), because
    the last round of this defect was caused by there being one strip in one
    function: a placeholder wearing a zero-width space was "an answer" to the
    vacuity test while the fold two functions up would have erased it. A
    character a reader cannot see is not content a reader can review, wherever
    the text is about to be compared, tested or counted.
    """
    t = unicodedata.normalize("NFKC", str(text))
    return "".join(ch for ch in t if not _is_invisible(ch))


def fold(text):
    """A text reduced to what it actually says: no case, no stray whitespace.

    Two derivations that differ only in case or in internal whitespace are one
    derivation. `str.strip()` was the whole comparison, so `SELECT SUM(amount)
    FROM orders` and `select  sum(amount)  from orders` were reported as an
    independent second check of each other.

    Invisible characters are removed first (plain_text above): `str.split()`
    does not split on U+200B, so one invisible character made a copy-paste of
    the first query an "independent second derivation", and a soft hyphen did
    the same one round later. A character a reader cannot see is not a
    difference a reader can review.
    """
    return " ".join(plain_text(text).split()).casefold()


# The homoglyph table: code points that render as an ASCII letter without being
# one. NFKD-plus-strip-marks handles the accent family; these are the distinct
# letters (mostly Cyrillic and Greek) that survive every Unicode normalization
# while being indistinguishable from ASCII on screen. Curated rather than
# exhaustive on purpose: the full Unicode confusables table is thousands of
# rows, and this holds the letter-for-letter lookalikes an identity is actually
# forged with. Extend it here; every identity comparison reads through it. The
# direction of error is deliberate: mapping one Cyrillic letter too many makes
# a rare honest name collide and FAIL a money-gate comparison, which costs a
# clarifying commit, while a missing row costs the control.
_CONFUSABLES = {
    # Cyrillic
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p", "\u0441": "c",
    "\u0443": "y", "\u0445": "x", "\u0456": "i", "\u0455": "s", "\u0458": "j",
    "\u04bb": "h", "\u051b": "q", "\u051d": "w", "\u0501": "d", "\u043a": "k",
    "\u043c": "m", "\u043d": "h", "\u0442": "t", "\u0432": "b", "\u0433": "r",
    "\u043f": "n", "\u0438": "u", "\u0475": "v", "\u0461": "w", "\u0454": "e",
    # Greek
    "\u03b1": "a", "\u03bf": "o", "\u03bd": "v", "\u03b9": "i", "\u03ba": "k",
    "\u03c1": "p", "\u03c4": "t", "\u03c5": "u", "\u03c7": "x", "\u03b5": "e",
    "\u03b7": "n", "\u03bc": "m", "\u03c9": "w", "\u03c3": "s", "\u03b2": "b",
    # Latin letters that survive NFKD with no combining mark to strip
    "\u0131": "i", "\u0142": "l", "\u00f8": "o", "\u0111": "d", "\u0127": "h",
}


def skeleton(text):
    """A string reduced to what a reader SEES: the anti-forgery identity form.

    fold() removes what is invisible; this also removes what is misleadingly
    visible. An identity comparison that reads code points reads them the way a
    parser enjoys them, and a forged identity is typed the way a person reads
    it: one Cyrillic letter inside an ASCII name renders identically and
    compares differently, so the self-approval guard on the money gate accepted
    the commit's own author as a second person. Accents are decomposed and
    dropped (NFKD, then every combining mark), then the confusable table maps
    the surviving lookalikes onto the ASCII they render as. For prose and
    derivations fold() remains the right reduction; for anything compared AS AN
    IDENTITY, this is.
    """
    t = unicodedata.normalize("NFKD", fold(text))
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return "".join(_CONFUSABLES.get(ch, ch) for ch in t)


# Every kind of line break, including the Unicode separators a terminal renders
# as new lines. NOT the Cf class: these are Cc/Zl/Zp and plain_text leaves them
# alone, because inside a document a newline is structure; inside a ONE-LINE
# report field it is a forgery vector.
_LINE_BREAKS = re.compile("[\r\n\v\f\x85\u2028\u2029]+")


def one_line(text):
    """An evidence sentence flattened onto the single line the report owns.

    A verdict is one printed line, and the parsers this project ships (and the
    humans reading a CI log) take the first line whose first token is a check
    name. Several evidence strings interpolate receipt-authored values with %s,
    and nothing anywhere flattened them, so a receipt field containing newlines
    wrote verdict lines FOR THE OTHER GATES into the report: a directory with
    no APPROVAL file printed "approval PASS signed commit carries ..." because
    a figure label said so. The artifact under inspection must not get to write
    any part of the report except inside its own line, so every print site
    passes its evidence through this, and a line break becomes the visible
    two-character escape a reader can see and question.
    """
    return _LINE_BREAKS.sub(" \\\\n ", str(text))


_BLOCK_COMMENT = re.compile(r"(?s)/\*.*?\*/")
_LINE_COMMENT = re.compile(r"(?:--|#)[^\n]*")


def derivation_fold(text):
    """A derivation reduced to the work it actually does.

    `fold()` collapsed case and whitespace, and that left a cosmetic edit buying
    the strongest sentence this project prints: appending `;` to a copied query,
    or pasting it back with `-- rerun 2026-07-25` on the end, was accepted as an
    independent second derivation of the figure. Neither is fabrication; both are
    the lazy thing rather than the dishonest thing, and answering them with "1
    figure independently re-derived" is the gate asserting more than it examined.

    Comments, trailing punctuation, case and whitespace are removed. What this
    still cannot do is stated rather than implied: renaming an alias is a textual
    difference and this will accept it, and no test here proves the two
    derivations read different tables or different columns. Text difference is
    the floor, not proof of independence, and the PASS sentence and SKILL.md L14
    say exactly that and no more.
    """
    t = _BLOCK_COMMENT.sub(" ", str(text))
    t = _LINE_COMMENT.sub(" ", t)
    return fold(t).strip(" \t;.,")


def vacuous(value, allow=()):
    """True when this value is present and non-empty and still records no answer.

    Round four of one defect. `stated()` answers "is this field blank", every
    gate asked it correctly, and nothing anywhere asked "is this field an
    ANSWER". A placeholder is not blank, so `snapshot_id: "TODO"` cleared a gate
    whose evidence line then asserted a pinned read, and two `"pending"` values
    compared equal and were reported as zero drift.

    `allow` names tokens that ARE answers in one field's domain: the intake asks
    how many downstream consumers break and "none" is the honest answer to that
    question, while "none" as a system of record is the absence of one. A field
    that carves a token out says so at the call site, in one place a reader can
    find, rather than the shared list being quietly weakened for everyone.

    The loop is the fix for the sixth shape of this defect: the copula stripper
    ran ONCE and its output was compared against a list of whole strings, so
    "is still unknown" reduced to "still unknown" and escaped a list that holds
    "unknown", and "should be" (the remnant of "still deciding who the owner
    should be") escaped everything. Every strip re-enters the whole test until
    nothing changes, so a remnant is judged by the same rules as the original.
    """
    if not isinstance(value, str):
        return False
    # plain_text first, the same normalization fold() applies, because this
    # function had its own weaker one: a placeholder wearing one zero-width
    # space, one soft hyphen, or a fullwidth spelling was "an answer" here
    # while fold() two functions up would have erased the disguise. The
    # invisible-character defence existed in this file and was not the shared
    # rule; now it is.
    v = " ".join(plain_text(value).split()).strip(" \t.;,:!\"'`").casefold()
    allowed = {a.casefold() for a in allow}
    while True:
        if v in allowed:
            return False
        if not v:
            return True
        # A value with no letter and no digit anywhere in it records nothing,
        # whatever the punctuation spells. The list carried "-", "--", "?" and
        # "???" one at a time and a lone "#" walked past all four of them, which
        # is the list-of-instances failure this project keeps finding one level
        # in. This is the rule those four entries were reaching for, and it
        # holds for the ones nobody typed.
        if not any(ch.isalnum() for ch in v):
            return True
        if v in VACUOUS_VALUES:
            return True
        stripped = _LEADING_NOISE.sub("", v).strip(" \t.;,:!\"'`")
        if stripped == v:
            return False
        v = stripped


def domain_vacuous(value):
    """True when this DOMAIN NAME is a placeholder rather than a thing.

    The scoped test: see DOMAIN_WORDS above. An entity called TBD is a note to the
    author; a state called `pending` is a payment lifecycle.
    """
    return vacuous(value, allow=DOMAIN_WORDS)


def answered(value, allow=()):
    """The answer recorded here, or None if this field records none.

    `stated()` plus the vacuity list: the test every field goes through when the
    verdict sentence is going to assert something ABOUT its content. Use
    `stated()` only where any non-blank value is genuinely acceptable.
    """
    v = stated(value)
    if isinstance(v, str) and vacuous(v, allow):
        return None
    return v


def answered_as(value, reduce, allow=()):
    """The answer this field records once it is reduced to what it actually says.

    ORDER, and the order was wrong everywhere. The vacuity test ran on the RAW
    value and the reduction ran after it, so every reduction this project performs
    could manufacture a fresh non-answer that nothing rechecked. The shipped case:
    `second_derivation: "#"` is not blank, is not in VACUOUS_VALUES and survives
    `answered()`; `derivation_fold` then turns it into the empty string; the gate
    compared "" against a real query, found them different, and printed the
    strongest sentence this project owns over a derivation that computes nothing.
    The same hole exists for every reduction: strip comments, strip a currency
    symbol, split a table cell, fold a wrapped line.

    Reduce first. Test second. This is the one function that does it in that
    order, and the call sites that reduce anything go through it.

    A reduction is defined on TEXT, so a field that reduces is a text field, and
    a value the reduction cannot read is not an answer to it. The old escape:
    `reduce` was applied only `if isinstance(v, str)`, so `"query": 0` and
    `"second_derivation": 1` skipped the whole R7 fix and two integers bought
    "a second derivation whose text differs beyond case, whitespace and
    comments", a sentence about text over fields holding none.
    """
    v = stated(value)
    if v is None:
        return None
    if not isinstance(v, str):
        return None
    reduced = reduce(v)
    if stated(reduced) is None:
        return None
    if isinstance(reduced, str) and vacuous(reduced, allow):
        return None
    return reduced


def distinct(items, reduce=None):
    """(the items that are actually different, how many duplicates were folded).

    ONE rule for every threshold in this project, here, because `gate_numbers`
    learned it and its three siblings did not: five identical rows are one row
    written five times, and a count printed in an evidence line is what a reader
    takes as the amount of work that was checked. Two rejected alternatives that
    are the same sentence twice are one alternative; five sealed predictions that
    are the same prediction are one prediction.

    Strings are compared folded (case and whitespace), because that is what makes
    two spellings of one sentence one sentence. A caller whose duplicates differ
    by MORE than case and whitespace passes the stronger reduction it needs:
    check_adr passes derivation_fold, because "Nightly batch reconciliation" and
    "nightly batch reconciliation." are one alternative, and counting them as
    two was a false count bought with a trailing period. Everything else is
    compared by its JSON, and by repr when it has none.
    """
    seen, keys = [], set()
    reduce = reduce or fold

    def normalized(x):
        # The reduction reaches INTO containers, because it did not: dicts were
        # compared by raw json.dumps while the sibling string call sites folded,
        # so one rating written six times with six trailing punctuation marks
        # counted as six distinct ratings. A container of strings is a container
        # of the sentences they spell, under the same reduction the caller
        # chose for bare strings.
        if isinstance(x, str):
            return reduce(x)
        if isinstance(x, dict):
            return {k: normalized(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [normalized(v) for v in x]
        return x

    for it in items:
        if isinstance(it, str):
            key = reduce(it)
        else:
            try:
                key = json.dumps(normalized(it), sort_keys=True)
            except (TypeError, ValueError):
                key = repr(it)
        if key in keys:
            continue
        keys.add(key)
        seen.append(it)
    return seen, len(items) - len(seen)


_HTML_COMMENT = re.compile(r"(?s)<!--.*?-->")


def without_comments(text):
    """The text as it renders: HTML comments removed.

    ONE rule, here, because there were two populations of readers in one file:
    four functions stripped comments and four did not, so a data model whose
    whole entity list sat inside `<!-- ... -->` was "the absence of an artifact"
    to the artifacts check and "2 entities, each with a system of record" to the
    data-model check, in the same run. A comment is a note to the author; a
    section that renders as empty is empty to every check that reads meaning
    out of markdown. The one deliberate exception is the unfilled-template
    marker, which the templates ship INSIDE a comment, so the placeholder check
    reads the raw text for the marker and this rendered text for everything
    else.
    """
    return _HTML_COMMENT.sub("", text or "")


def all_vacuous(text):
    """True when a body of text is present and every substantive line of it is a placeholder.

    The text-shaped vacuity. A zero-byte artifact was already the absence of an
    artifact; a file holding only headings was too; and then a file whose every
    line under those headings said TODO cleared the same checks, because a
    placeholder is not blank. Headings and comment lines are scaffolding and are
    not counted either way: this asks whether anything was WRITTEN.
    """
    body = without_comments(text)
    lines = [l.strip() for l in body.splitlines()
             if l.strip() and not l.lstrip().startswith("#")]
    return bool(lines) and all(vacuous(l) for l in lines)


def numeric(value):
    """The number this field records, or None if it does not record one.

    A figure's value and a row count are numbers. `"pending"` and `"unknown"`
    are not, and neither is `True`: a boolean satisfied both `!= 0` and a
    truthiness test, and the receipt then read as a measurement. A number
    written as a string is still a number, so "17,570" and "17570" both count;
    an engineer exporting a receipt from a spreadsheet writes the first one and
    rejecting it would be rejecting honest work.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return None if _not_a_measurement(value) else value
    if not isinstance(value, str):
        return None
    # A leading currency symbol and thousands separators are formatting, not
    # meaning. Only the ASCII "$" is stripped: this repository is ASCII by rule,
    # and a receipt written in another currency records the number either way.
    #
    # The separators are VALIDATED before they are stripped. Stripping every
    # comma anywhere read "1,2,3" as 123 and "17,5,70" as 17570, so a mistyped
    # row count silently became the number it was supposed to be compared
    # against; and float() accepts non-ASCII digits, so a numeral in another
    # script read as a measurement in a repository that is ASCII by rule. A
    # separator is formatting only when it sits where formatting sits: groups
    # of three. Anything else is not a number this tool can claim it read, and
    # None is the answer every caller turns into a named FAIL that quotes the
    # value. The shape rule also refuses "inf" and "nan" spelled as words,
    # which the after-parse test below used to be the only guard against.
    text = value.strip().lstrip("$").rstrip("%").strip()
    if not text.isascii():
        return None
    m = _NUMBER_GROUPED.match(text)
    if m:
        text = text.replace(m.group(1), "")
    elif not _NUMBER_PLAIN.match(text):
        return None
    try:
        n = float(text)
    except ValueError:
        # Not swallowed: None is the answer, and every caller turns it into a
        # named FAIL that quotes the value it could not read as a number.
        return None
    # Tested AFTER the parse as well: "1e400" is a well-shaped spelling whose
    # VALUE is an infinity, and an infinity is not a measurement, and neither
    # is a not-a-number. json.loads also accepts bare Infinity and NaN, which
    # arrive here as floats and are refused above.
    return None if _not_a_measurement(n) else n


# The written shapes a number may take: plain (with an optional exponent), or
# separator-grouped in threes with ONE consistent separator character.
_NUMBER_GROUPED = re.compile(r"^[+-]?\d{1,3}(?:([,_])\d{3})(?:\1\d{3})*(?:\.\d+)?$")
_NUMBER_PLAIN = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?$")


def _not_a_measurement(n):
    return isinstance(n, float) and (math.isinf(n) or math.isnan(n))


def unit_of(value):
    """The unit marker a recorded figure carries: "%", "$" or "".

    numeric() strips both as formatting so "50%" and "$50" each read as the
    number 50, and a zero-drift comparison then called a rate and a currency
    amount equal. The number is the value; the unit is what it is a value OF,
    and two figures recorded in different units did not re-derive each other.
    """
    if not isinstance(value, str):
        return ""
    t = value.strip()
    if t.endswith("%"):
        return "%"
    if t.startswith("$"):
        return "$"
    return ""


def count(value):
    """The count this field records, or None if it does not record one.

    A count is a whole number of things. `numeric()` is the right test for a
    figure, which may be a rate, a ratio or a negative delta, and the wrong test
    for a row count: `-1`/`-1` compared equal and produced "1 row-count
    comparison(s) matched", and minus one rows is not a count any table has ever
    had. Neither is two and a half rows, and neither is "50%": numeric() strips
    the percent sign as formatting, which is right for a figure and wrong here,
    because a percentage is a rate and no table has a rate of rows.
    """
    if isinstance(value, str) and value.strip().endswith("%"):
        return None
    n = numeric(value)
    if n is None or n < 0 or n != int(n):
        return None
    return int(n)


def run_guarded(name, check, *args):
    """Run one check so that a crash inside it cannot delete its verdict.

    A gate that raises takes every gate after it down with it and prints no line
    for any of them, which is the absent-check failure in its purest form: the
    operator sees three verdicts where there should be four and nothing says so.
    A crashed check is a FAILED check. The exception text is the evidence.

    This guards the CONTEXT the check reads as well as the check body, because
    the arguments are passed as thunks where a caller needs that: one malformed
    ledger line raised inside the shared context object, outside this guard, and
    collapsed all eleven scorer checks into a single error line at exit 0.
    """
    try:
        verdict, evidence = check(*args)
    except Exception as e:  # sbe: allow-silent the exception is not swallowed, it becomes the FAIL evidence on the next line
        return "FAIL", ("the check itself raised %s: %s. A check that crashed examined nothing, "
                        "and a check that examined nothing must not vanish from the report; "
                        "it is reported here as a failure" % (type(e).__name__, e))
    if verdict not in ("PASS", "FAIL", "NO-DATA"):
        return "FAIL", ("%s returned the verdict %r, which is not one of PASS, FAIL, NO-DATA"
                        % (name, verdict))
    return verdict, evidence
