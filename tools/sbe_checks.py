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

import json, math, os, re

KINDS = ("json", "jsonl", "text", "tree", "git")

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

    def __call__(self, parent, dirnames):
        """For os.walk's `dns[:] = pruner(dp, dns)`."""
        keep = []
        for d in sorted(dirnames):
            why = skip_reason(parent, d)
            if why is None:
                keep.append(d)
            else:
                self.pruned.append((os.path.join(parent, d), why))
        return keep

    def hidden(self, wanted):
        """Pruned trees that hold a file this walk was looking for, `wanted(name)`."""
        out, budget = [], self.LIMIT
        for path, why in self.pruned:
            for _dp, _dns, fns in os.walk(path):
                budget -= 1
                if budget <= 0:
                    break
                if any(wanted(f) for f in fns):
                    out.append("%s (%s)" % (path, why))
                    break
        return sorted(set(out))

    def note(self, wanted):
        """The sentence a verdict carries when pruning removed candidate evidence."""
        h = self.hidden(wanted)
        if not h:
            return ""
        return ("; %d pruned director(y/ies) hold file(s) this check reads and were NOT examined, "
                "so this verdict does not cover them: %s" % (len(h), "; ".join(h[:4])))


VERDICTS = ("PASS", "FAIL", "NO-DATA")


class Check:
    def __init__(self, fn, reads, kind, item_key=None,
                 empty_expect="NO-DATA", empty_note="", empty_fixture=None,
                 full_fixture=None, no_full_fixture="", optional_leaves=None,
                 full_expect="PASS", full_expect_reason=""):
        if kind not in KINDS:
            raise ValueError("unknown evidence kind %r (expected one of %s)"
                             % (kind, ", ".join(KINDS)))
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
        for path, why in (optional_leaves or {}).items():
            if not why:
                raise ValueError(
                    "optional_leaves[%r] has no reason. A field exempted from the empty-value "
                    "sweep is a field nobody tests, so the exemption states why the PASS "
                    "sentence does not assert over it" % path)
        self.fn = fn
        self.reads = tuple(reads)
        self.kind = kind
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
    reject honest work.

    This is emptiness only. "TODO" is not empty and records nothing either;
    that is `answered()` below, and a field whose content the verdict sentence
    describes goes through THAT one.
    """
    if value is None:
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
_LEADING_COPULA = re.compile(r"^(?:it\s+is|is|was|are)\s+", re.I)

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
        v = " ".join(value.split()).strip(" \t.;,:!\"'`").casefold()
        if v in AFFIRMATIVE:
            return True
        if v in NEGATIVE:
            return False
    return None


def fold(text):
    """A text reduced to what it actually says: no case, no stray whitespace.

    Two derivations that differ only in case or in internal whitespace are one
    derivation. `str.strip()` was the whole comparison, so `SELECT SUM(amount)
    FROM orders` and `select  sum(amount)  from orders` were reported as an
    independent second check of each other.
    """
    return " ".join(str(text).split()).casefold()


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
    """
    if not isinstance(value, str):
        return False
    v = " ".join(value.split()).strip(" \t.;,:!\"'`")
    v = _LEADING_COPULA.sub("", v).strip().casefold()
    if v in {a.casefold() for a in allow}:
        return False
    if not v:
        return True
    # A value with no letter and no digit anywhere in it records nothing, whatever
    # the punctuation spells. The list carried "-", "--", "?" and "???" one at a
    # time and a lone "#" walked past all four of them, which is the list-of-
    # instances failure this project keeps finding one level in. This is the rule
    # those four entries were reaching for, and it holds for the ones nobody typed.
    if not any(ch.isalnum() for ch in v):
        return True
    return v in VACUOUS_VALUES


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
    """
    v = stated(value)
    if v is None:
        return None
    reduced = reduce(v) if isinstance(v, str) else v
    if stated(reduced) is None:
        return None
    if isinstance(reduced, str) and vacuous(reduced, allow):
        return None
    return reduced


def distinct(items):
    """(the items that are actually different, how many duplicates were folded).

    ONE rule for every threshold in this project, here, because `gate_numbers`
    learned it and its three siblings did not: five identical rows are one row
    written five times, and a count printed in an evidence line is what a reader
    takes as the amount of work that was checked. Two rejected alternatives that
    are the same sentence twice are one alternative; five sealed predictions that
    are the same prediction are one prediction.

    Strings are compared folded (case and whitespace), because that is what makes
    two spellings of one sentence one sentence. Everything else is compared by its
    JSON, and by repr when it has none.
    """
    seen, keys = [], set()
    for it in items:
        if isinstance(it, str):
            key = fold(it)
        else:
            try:
                key = json.dumps(it, sort_keys=True)
            except (TypeError, ValueError):
                key = repr(it)
        if key in keys:
            continue
        keys.add(key)
        seen.append(it)
    return seen, len(items) - len(seen)


def all_vacuous(text):
    """True when a body of text is present and every substantive line of it is a placeholder.

    The text-shaped vacuity. A zero-byte artifact was already the absence of an
    artifact; a file holding only headings was too; and then a file whose every
    line under those headings said TODO cleared the same checks, because a
    placeholder is not blank. Headings and comment lines are scaffolding and are
    not counted either way: this asks whether anything was WRITTEN.
    """
    body = re.sub(r"(?s)<!--.*?-->", "", text or "")
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
    text = value.strip().replace(",", "").replace("_", "").lstrip("$").rstrip("%")
    try:
        n = float(text)
    except ValueError:
        # Not swallowed: None is the answer, and every caller turns it into a
        # named FAIL that quotes the value it could not read as a number.
        return None
    # Tested AFTER the parse, which is the order this file gets wrong everywhere
    # it is not looked at: `float()` accepts "inf", "Infinity", "1e400" and "nan"
    # and json.loads accepts bare Infinity and NaN, so `{"primary": "inf",
    # "secondary": "inf"}` compared equal and bought "re-run to zero drift", and
    # `inf`/`inf` row counts bought "1 row-count comparison(s) matched". An
    # infinity is not a measurement and neither is a not-a-number.
    return None if _not_a_measurement(n) else n


def _not_a_measurement(n):
    return isinstance(n, float) and (math.isinf(n) or math.isnan(n))


def count(value):
    """The count this field records, or None if it does not record one.

    A count is a whole number of things. `numeric()` is the right test for a
    figure, which may be a rate, a ratio or a negative delta, and the wrong test
    for a row count: `-1`/`-1` compared equal and produced "1 row-count
    comparison(s) matched", and minus one rows is not a count any table has ever
    had. Neither is two and a half rows.
    """
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
