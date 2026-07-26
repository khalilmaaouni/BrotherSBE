#!/usr/bin/env python3
"""The honesty meta-test: no check in this project may report PASS over evidence
it never examined.

This exists because fixing the instances did not fix the CLASS, twice. Six named
cases of "a PASS whose evidence asserts something the tool never inspected" were
fixed by hand; a re-review found the identical defect alive in four more places
inside the same two files; a third review found it alive in six more. A seventh
hand fix would have been the same mistake a seventh time.

The reason it kept surviving is precise and worth stating, because it is the
whole design of this file. Every earlier round modelled absent evidence as an
absent FILE. The surviving holes were absent VALUES. A manifest that exists,
parses, carries every required key and holds "" in all of them sailed through,
and the check then printed "zero drift" over two empty strings. So this test does
not enumerate shapes of missing files. It takes the WORKING example each check
declares and hollows it out, mechanically, in every way a value can be empty:

  a  a completely empty directory                      -> NO-DATA, never PASS
  a2 a dossier-shaped directory with a zero-byte anchor, so that a check whose
     tool has a no-target fallback is genuinely INVOKED at least once
  b  evidence that exists and declares zero items      -> the declared empty state
  c  valid JSON of the wrong shape (list, string, ...) -> FAIL, a verdict line is
                                                          still printed, and no
                                                          traceback escapes
  d  malformed JSON                                    -> FAIL
  full the declared full_fixture                       -> PASS, which is what
                                                          proves the check ran at
                                                          all and that the fixture
                                                          is a real positive
  e  every value in it replaced by ""                  -> never PASS
  f  every value replaced by whitespace                -> never PASS
  g  every value replaced by null                      -> never PASS
  e/f/g are also applied to every SUBTREE and every single LEAF of the fixture,
     one at a time. Emptying the whole receipt is the easy case and no shipped
     defect had that shape: the live ones were a single emptied pair inside an
     otherwise complete receipt (`rerun.primary` and `rerun.secondary`, or
     `row_counts.before` and `row_counts.after_reverse`), which is exactly the
     subtree sweep, and a single whitespace value (`rehearsal_run_id: " "`),
     which is exactly the leaf sweep.
  h  every item in a list replaced by an empty object  -> never PASS
  j  every list emptied                                -> never PASS
  i  the files exist with the right names and are zero bytes -> never PASS
  s  for a markdown artifact: every heading kept, the body under one heading
     dropped, one heading at a time. This is the text-shaped version of "the keys
     are all there and the values are all empty".
  t  every BOOLEAN leaf replaced by a well-formed word meaning the OPPOSITE
     ("no"/"false" for a true, "yes"/"true" for a false) -> never PASS. The one
     axis here that is not emptiness at all: see OPPOSITE_WORDS below.

Booleans are preserved by the whole-fixture and subtree sweeps and emptied only
by the leaf sweep, on purpose. In a receipt a boolean is the CLAIM ("the reverse
ran against a restore") and a string or a number is the EVIDENCE for it. Emptying
the evidence while leaving the claim standing is the precise shape a fabricated
receipt has, and it is the shape three rounds of review kept finding.

Registries are DISCOVERED, not listed. Every Python module anywhere under
tools/ is imported, at any depth, and every module-level dict of Checks in it is
a registry. A registry this test does not know how to invoke is a FAILURE, not a
skip, so a fourth tool added next year, or a package added under an existing one,
cannot be silently uncovered. A source-level lint additionally requires that
every function anywhere in tools/ that can return the literal verdict "PASS" is
registered in one of those registries, so a verdict-producing code path cannot
live outside the walk.

Run: python3 evals/test_no_data_class.py
     python3 evals/test_no_data_class.py --tools <dir>
     python3 evals/test_no_data_class.py --quiet     (summary and failures only)

The second form runs the SAME scenarios against a different copy of the tools,
which is how the before-list was measured against the tree that shipped these
defects: the scenarios and the expected verdicts are data held here, the code
under test is whatever --tools points at. A test that can only be run against the
fixed code proves nothing about what it caught.
"""
import ast, copy, datetime, json, os, subprocess, sys, tempfile
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.abspath(os.path.join(HERE, "..", "tools"))
sys.path.insert(0, TOOLS_DIR)

# The registries (the declarations) always come from this working tree. The code
# actually invoked can be pointed elsewhere, which is how the before-list is
# measured against the tree that shipped the defects.
RUN_DIR = TOOLS_DIR
if "--tools" in sys.argv:
    RUN_DIR = os.path.abspath(sys.argv[sys.argv.index("--tools") + 1])
QUIET = "--quiet" in sys.argv

from sbe_checks import Check, Pruner  # noqa: E402

_telemetry = SourceFileLoader("sbe_telemetry",
                              os.path.join(TOOLS_DIR, "sbe_telemetry.py")).load_module()

# The evidence sentence sbe_design.py prints for a check it did NOT open a file
# for, because no dossier was found. It is matched here so a scenario cannot be
# counted as covering a check that never ran. The phrase is load-bearing: see the
# comment beside it in tools/sbe_design.py.
NOT_INVOKED = "so this check opened no file"

EMPTY_VALUES = [("e", "empty-string", ""), ("f", "whitespace", "   "), ("g", "null", None)]
# Round four of the same defect, as a scenario shape. The value is PRESENT, it is
# NON-EMPTY, and it records nothing: `snapshot_id: "TODO"` with both rerun values
# `"pending"` produced "1 figure(s) each with a pinned, independently re-derived,
# zero-drift check" and `--strict` exit 0. `stated()` is not a test for this and
# nothing anywhere was asking "is this field an ANSWER".
#
# Three tokens, not the whole vacuity list, and each is here for a different
# reason a substitution can go wrong: TODO is upper case (so a case-sensitive
# membership test fails this scenario), n/a carries punctuation (so a naive
# isalnum-style normalisation fails it), and "-" is a single character that a
# length check would wave through. Every token in sbe_checks.VACUOUS_VALUES is
# covered by construction, because they all resolve through one predicate; these
# three prove the predicate is actually being CALLED, which is what a scenario
# can prove and a list cannot.
VACUOUS_VALUES = [("v", "todo", "TODO"), ("v", "n-a", "n/a"), ("v", "dash", "-"),
                  # The copula remnant: "is still unknown" is not blank, is not
                  # a whole-string token, and the one-shot copula stripper left
                  # "still unknown", which is not in a list that holds
                  # "unknown". This token proves the vacuity test re-reads its
                  # own reduction's output to a fixpoint.
                  ("v", "copula-remnant", "is still unknown")]

# Values that are numbers and still record no measurement. json.load accepts a
# bare NaN, `NaN <= 0` is False, and a hand-rolled duration check accepted one
# while its sentence asserted "a nonzero duration": the evidence sentence was
# false even where the verdict logic was arguably defensible. Swept like the
# empty values, over every leaf and subtree, but only through JSON-shaped
# fixtures: NaN has no text form a markdown artifact would carry.
NOT_MEASUREMENTS = [("m", "nan", float("nan"))]

# Round six, and the first axis about ORDER rather than about content. Every
# sweep above replaces a value with one that says nothing WHEN READ RAW. These
# replace it with one that says nothing only AFTER the tool reduces it, which is
# the shape the whole sweep was blind to because the tools tested for vacuity
# first and reduced afterwards. `second_derivation: "#"` is not blank, is not a
# vacuity token, survives answered(), and folds to the empty string, and the gate
# then compared "" against a real query, found them different, and printed "a
# second derivation whose text differs beyond case, whitespace and comments,
# re-run to zero drift" over a derivation that computes nothing. Every reduction
# this project performs (strip comments, strip a currency symbol, parse a number)
# can manufacture the same hole, so the order is now a scenario and not a habit.
#
# These carry no letter and no digit, so they are a non-answer under any reading
# and can be swept per leaf. The word-bearing case is below, and can only be
# swept whole, because "-- rerun by hand" is a perfectly good LABEL and only a
# derivation-shaped field reduces it to nothing.
REDUCES_TO_NOTHING = [("n", "hash-comment", "#"), ("n", "block-comment", "/* */"),
                      ("n", "punctuation", ";")]
# Applied to the whole fixture at once, for the same reason.
COMMENT_ONLY = [("n", "sql-comment-with-words", "-- rerun on 2026-07-26 by hand, same query"),
                ("n", "not-a-measurement", "inf"),
                # A number where text belongs: `"query": 0` skipped the whole
                # reduce-then-test fix, because the reduction was applied only
                # to strings, and two integers bought "a second derivation whose
                # text differs beyond case, whitespace and comments". Whole
                # fixture only: 0 is an honest answer for many single leaves (a
                # zero exit code), so a per-leaf sweep of it would assert
                # falsehoods.
                ("n", "number-in-a-text-field", 0)]

# Round five, and the first one that is not about emptiness at all. Every sweep
# above replaces a value with a value that says NOTHING. This one replaces a
# boolean with a well-formed word that says the OPPOSITE, which is the shape the
# whole sweep was blind to: the intake asks its questions as "(y/n)", read the
# answers for Python truthiness, and so an answer of "no" to "is this reversible
# in under an hour" computed the LOWEST tier, T0 required no artifact, every
# design check reported NO-DATA, and the re-derivation that exists to catch a
# hand-edited tier recomputed the same wrong tier from the same unread string and
# agreed with the file. Nothing in this test could have caught that, because
# every scenario it generated was a form of blank.
#
# The rule: a boolean in a worked positive example is a CLAIM. Replacing it with
# a word meaning the opposite of that claim must not leave the verdict at PASS.
# The same-meaning direction is deliberately NOT swept here: the gates hold that
# only the JSON boolean true is the claim (SKILL.md L14), so "yes" correctly
# fails there while it correctly reads as a yes in the intake, and one sweep
# cannot assert both. That direction is covered by named cases in
# evals/run_evals.py instead.
OPPOSITE_WORDS = {True: ("no", "false"), False: ("yes", "true")}


# ---------------------------------------------------------------------------
# Registry discovery
# ---------------------------------------------------------------------------

def tool_sources():
    """Every Python file ANYWHERE under tools/, as a path relative to it.

    NOT `sbe_*.py`. The prefix filter was a hole and it was proved: a registry
    shipped as `tools/quality.py` holding a check whose body was
    `return "PASS", "quality is fine (examined nothing at all)"` was invisible
    to the registry walk AND to the source lint, and this file printed
    "20 checks discovered ... 0 failure(s)" over twenty-one checks and exited 0.
    Discovery must not depend on what somebody named a file.

    And then it depended on what somebody named a DIRECTORY. `os.listdir` is one
    level deep, so the same shadow check moved into `tools/quality/extra.py` was
    invisible to both mechanisms again, while the summary line still read
    "20 checks discovered ... 0 failure(s)" over twenty-one. Adding a package is
    the ordinary way a tools directory grows, and the printed coverage count is
    exactly what made the gap silent. This walks.
    """
    out = []
    pruner = Pruner()
    # onerror: os.walk swallows a refused directory by default, so one chmod 000
    # under tools/ dropped a module from the walk, the count fell from 8 to 7,
    # and the guarantee sentence returned to "0 failure(s)" over a tree this test
    # could not see into. A directory the walk cannot enter is a failure below.
    for dp, dns, fns in os.walk(TOOLS_DIR, onerror=pruner.onerror):
        dns[:] = pruner(dp, dns)
        for fn in fns:
            if fn.endswith(".py"):
                out.append(os.path.relpath(os.path.join(dp, fn), TOOLS_DIR))
    hidden, uninspected = pruner.hidden(lambda f: f.endswith(".py"))
    if hidden or uninspected:
        # A pruned directory holding Python, or one the inspection budget never
        # reached, is a directory this test's coverage claim does not cover, and
        # the claim is printed on every run. Naming it in the sources list would
        # import somebody else's code; naming it here is how the count stops
        # being a completeness sentence over a truncated set. main() turns this
        # into a failure.
        PRUNED_WITH_SOURCE.extend(hidden)
        PRUNED_WITH_SOURCE.extend(uninspected)
    DENIED_DIRS.extend(pruner.denied)
    return sorted(out)


PRUNED_WITH_SOURCE = []
DENIED_DIRS = []


def load_tool_modules():
    """Import every tool module. An import that fails is a FAILURE, not a skip.

    Returns (modules, failures). A module this test cannot import is a module
    whose registries it cannot walk, which is the same blindness as a registry
    it cannot invoke, so it is reported by name rather than passed over.
    """
    mods, failures = {}, []
    for fn in tool_sources():
        if os.path.basename(fn) == "sbe_checks.py":
            # Reloading it would rebind sbe_checks.Check to a second, unequal
            # class, and every isinstance(x, Check) below would then be false
            # against registries that had already imported the first one. This is
            # the ONE exclusion, it is named, and the file holds no registry: the
            # lint below still reads it, so a check hiding there is still caught.
            continue
        try:
            # The module name carries the subdirectory, so tools/a/x.py and
            # tools/b/x.py are two modules here rather than one shadowing the other.
            modname = fn[:-3].replace(os.sep, ".")
            mods[fn] = SourceFileLoader(modname, os.path.join(TOOLS_DIR, fn)).load_module()
        except Exception as e:
            failures.append("tools/%s could not be imported (%s: %s), so any registry in it went "
                            "unwalked. A module this test cannot reach is a failure, never a skip"
                            % (fn, type(e).__name__, e))
    return mods, failures


def discover_registries(mods):
    """Every module-level dict holding Checks, plus the ones that hold something else.

    A dict with any Check in it is a registry; a registry with a bare function in
    it is a defect, because this test cannot cover what does not declare its
    evidence. Nothing here is written down by hand.
    """
    found, defects = [], []
    for fn, mod in mods.items():
        for attr, val in sorted(vars(mod).items()):
            if attr.startswith("_") or not isinstance(val, dict) or not val:
                continue
            if not any(isinstance(v, Check) for v in val.values()):
                continue
            bad = sorted(k for k, v in val.items() if not isinstance(v, Check))
            if bad:
                defects.append("%s: %s.%s holds %s registered as bare values, not Checks "
                               "declaring their evidence, so this test cannot cover them"
                               % (fn, fn[:-3], attr, ", ".join(bad)))
            found.append((fn, attr, val))
    return found, defects


def _pass_valued_names(tree):
    """Names bound to the string "PASS" anywhere in a module.

    The lint matched the literal spelling only, so `VERDICT_OK = "PASS"` at
    module level and `return VERDICT_OK, "shadow gate: examined nothing"` in the
    body walked straight through it, and the run still printed 0 failures. A
    verdict is a verdict whatever it was spelled through.
    """
    names = set()
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        direct = isinstance(value, ast.Constant) and value.value == "PASS"
        # `_ok = lambda: "PASS"` binds a name to the verdict as surely as
        # `_ok = "PASS"` does, and a Lambda is not a FunctionDef so the walk below
        # never inspects one. The name is a verdict name either way.
        if isinstance(value, ast.Lambda) and any(
                isinstance(n, ast.Constant) and _spells_pass(n.value) for n in ast.walk(value)):
            direct = True
        # A container holding the verdict counts too, because the name is then a
        # verdict table and `TABLE["ok"]` is a way of spelling "PASS".
        container = isinstance(value, (ast.Dict, ast.List, ast.Tuple, ast.Set)) and any(
            isinstance(n, ast.Constant) and n.value == "PASS" for n in ast.walk(value))
        if not (direct or container):
            continue
        for t in targets:
            if isinstance(t, ast.Name):
                names.add(t.id)
    return names


def _folded_str(node):
    """The string this expression evaluates to, or None if it is not a constant one.

    Only string constants and `+` between them. `"PA" + "SS"` is deliberate
    obfuscation and weighted lightly, but the lint that claims to find every path
    that can return PASS has to be able to say so, and folding two constants is
    cheaper than arguing about whether anyone would write it.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _folded_str(node.left), _folded_str(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def _spells_pass(text):
    return isinstance(text, str) and text.strip().casefold() == "pass"


def _mentions_pass(node, pass_names):
    """True when the verdict PASS is reachable anywhere inside this expression.

    Deliberately generous. Enumerating node types one at a time is the
    hand-fix-the-instance loop this project exists to break, and it lost five
    times over: an f-string is a JoinedStr and not a Constant, a name bound by
    `from sbe_checks import VERDICTS` is bound by no Assign, a lambda is not a
    FunctionDef, and `"pass".upper()` and `"".join(["PA", "SS"])` are Calls. So
    this asks the opposite question: is there ANY constant, name or call in here
    through which the string could arrive.
    """
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and _spells_pass(n.value):
            return True
        if isinstance(n, ast.Name) and n.id in pass_names:
            return True
        if isinstance(n, ast.Attribute) and n.attr in ("upper", "casefold", "lower", "title",
                                                       "strip", "format", "join", "replace"):
            # A string method applied to something that spells pass in any case.
            if any(isinstance(c, ast.Constant) and _spells_pass(c.value)
                   for c in ast.walk(n)):
                return True
    return False


def _returns_pass(head, pass_names):
    """True when this expression can be the verdict PASS."""
    if head is None:
        return False
    if isinstance(head, ast.Constant) and head.value == "PASS":
        return True
    if isinstance(head, ast.Name) and head.id in pass_names:
        return True
    if _folded_str(head) == "PASS":
        return True
    return _mentions_pass(head, pass_names)


# Functions in tools/ that return a 2-tuple and are NOT verdict producers. The
# lint below is INVERTED: a 2-tuple return whose head this lint cannot prove is
# always one of FAIL or NO-DATA counts as a possible verdict, because proving a
# negative about an expression is the only way to stop playing whack-a-mole with
# spellings of "PASS". Everything genuinely not a verdict is named here with the
# reason, and the list is printed on every run, so the exemption is reviewable
# rather than a silent gap.
NOT_A_VERDICT = {
    ("sbe_checks.py", "run_guarded"): "the shared runner; it returns whatever the check it wrapped "
                                      "returned, and every check it can wrap is itself registered",
    ("sbe_checks.py", "distinct"): "returns (items, duplicate count), not a verdict",
    ("sbe_checks.py", "hidden"): "returns (pruned trees holding wanted files, trees the inspection "
                                 "budget left uninspected), not a verdict",
    ("sbe_checks.py", "answered_as"): "returns a reduced value, never a verdict",
    ("sbe_gate.py", "load_receipt"): "returns (parsed receipt, parse error), not a verdict",
    ("sbe_gate.py", "_items"): "returns (item list, why it is empty), not a verdict",
    ("sbe_gate.py", "find"): "returns (paths found, pruning note), not a verdict",
    ("sbe_gate.py", "git_trailers"): "returns (commit body, signature state, identities), not a verdict",
    ("sbe_gate.py", "_identity_parts"): "returns (canonical emails, name word-sets), not a verdict",
    ("sbe_design.py", "_entity_bullets"): "returns (the entity set, whether a heading declared it), "
                                          "not a verdict",
    ("sbe_intake.py", "read_answers"): "returns (answers read, answers refused), not a verdict",
    ("sbe_score.py", "_rel"): "returns a path",
    ("sbe_decide.py", "load_table"): "returns (parsed table, load error), not a verdict",
    ("sbe_telemetry.py", "redact"): "returns (masked text, how many masks), not a verdict",
    ("sbe_telemetry.py", "prediction_counts"): "returns a count table",
}


def pass_returning_functions(mods=None):
    """Source-level: every function whose 2-tuple return could be the verdict PASS.

    A registry walk covers what is registered. This covers what EXISTS, so a
    verdict-producing path that was never registered is caught by name rather
    than by being quietly outside the walk. Over every .py file in tools/, not
    over `sbe_*.py`: see tool_sources().

    Round six inverted it. The lint used to look FOR the string PASS and five
    ordinary spellings walked past it, including the exact file and body this
    file's own docstring cites as its proof case. It now looks for a
    (verdict, evidence) shape and demands that the head be PROVABLY never PASS:
    a constant FAIL or NO-DATA, or a conditional between them. Anything else,
    including anything it cannot read, is a candidate, and the way out is the
    named allowlist above rather than another node type.

    Returns [(file, function, why it was flagged)].
    """
    out = []
    for fn in tool_sources():
        # Guarded for the same reason load_tool_modules guards its import: a
        # module this lint cannot parse (a newer syntax on an older Python, an
        # unreadable file) is a module whose verdict paths it cannot see, which
        # is a named failure and never a traceback or a skip.
        try:
            tree = ast.parse(open(os.path.join(TOOLS_DIR, fn)).read(), filename=fn)
        except (SyntaxError, OSError, ValueError) as e:
            out.append((fn, "<module>", "could not be parsed (%s: %s), so any verdict-producing "
                                        "function in it is invisible to this lint" % (type(e).__name__, e)))
            continue
        pass_names = _pass_valued_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = node.name
            if (fn, name) in NOT_A_VERDICT:
                continue
            returns = []
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and sub.value is not None:
                    returns.append(sub.value)
            for value in returns:
                head = None
                if isinstance(value, ast.Tuple) and len(value.elts) == 2:
                    head = value.elts[0]
                elif isinstance(value, ast.Name) and value.id in pass_names:
                    head = value
                elif isinstance(value, ast.Lambda):
                    continue
                if head is None:
                    continue
                if _returns_pass(head, pass_names):
                    out.append((fn, name, "returns the verdict PASS"))
                    break
                if not _provably_not_pass(head, pass_names):
                    out.append((fn, name, "returns a (verdict, evidence) pair whose verdict this "
                                          "lint cannot prove is never PASS"))
                    break
    return sorted(set(out))


def _provably_not_pass(head, pass_names):
    """True only when this head is certainly one of the non-PASS verdicts.

    A string constant that is FAIL or NO-DATA, or a conditional or boolean
    expression built out of nothing but those. Everything else is a candidate,
    which is the safe direction: a false alarm costs one line in an allowlist and
    a miss costs the guarantee this whole file exists to make.
    """
    if isinstance(head, ast.Constant):
        return head.value in ("FAIL", "NO-DATA")
    if isinstance(head, (ast.IfExp, ast.BoolOp)):
        parts = ([head.body, head.orelse] if isinstance(head, ast.IfExp) else list(head.values))
        return all(_provably_not_pass(p, pass_names) for p in parts)
    return False


# ---------------------------------------------------------------------------
# Fixture substitution and hollowing
# ---------------------------------------------------------------------------

def subst(value, d):
    # One clock. %(today)s is the UTC date so that it agrees with the UTC
    # timestamp in %(now)s: deriving them from different clocks made a fixture
    # fail for nine hours a day in one timezone and pass in another.
    utc = datetime.datetime.now(datetime.timezone.utc)
    table = {"dir": d, "now": utc.isoformat().replace("+00:00", "Z"),
             "today": utc.date().isoformat()}
    if isinstance(value, str):
        for k, v in table.items():
            value = value.replace("%(" + k + ")s", v)
        return value
    if isinstance(value, dict):
        return {subst(k, d): subst(v, d) for k, v in value.items()}
    if isinstance(value, list):
        return [subst(v, d) for v in value]
    return value


def leaf_paths(obj, prefix=()):
    """Every path to a scalar inside the fixture."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            for p in leaf_paths(v, prefix + (k,)):
                yield p
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for p in leaf_paths(v, prefix + (i,)):
                yield p
    else:
        yield prefix


def container_paths(obj, prefix=()):
    """Every path to a dict or list inside the fixture, root last."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            for p in container_paths(v, prefix + (k,)):
                yield p
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for p in container_paths(v, prefix + (i,)):
                yield p
    if isinstance(obj, (dict, list)):
        yield prefix


def render(path):
    out = ""
    for part in path:
        out += ("[%d]" % part) if isinstance(part, int) else (("." if out else "") + str(part))
    return out or "<root>"


def at(obj, path):
    for part in path:
        obj = obj[part]
    return obj


def replace_at(obj, path, new):
    if not path:
        return new
    out = copy.deepcopy(obj)
    node = out
    for part in path[:-1]:
        node = node[part]
    node[path[-1]] = new
    return out


def hollowed(node, value, keep_booleans):
    if isinstance(node, dict):
        return {k: hollowed(v, value, keep_booleans) for k, v in node.items()}
    if isinstance(node, list):
        return [hollowed(v, value, keep_booleans) for v in node]
    if keep_booleans and isinstance(node, bool):
        return node
    return value


def heading_sections(text):
    """(heading title, line indices of its body) for a markdown document."""
    out, current = [], None
    for i, line in enumerate(text.splitlines()):
        if line.lstrip().startswith("#"):
            current = (line.strip("# ").strip(), [])
            out.append(current)
        elif current is not None:
            current[1].append(i)
    return [(title, body) for title, body in out if body]


def drop_section(text, title):
    lines = text.splitlines()
    keep, current = [], None
    for line in lines:
        if line.lstrip().startswith("#"):
            current = line.strip("# ").strip()
            keep.append(line)
            continue
        if current == title:
            continue
        keep.append(line)
    return "\n".join(keep) + "\n"


# ---------------------------------------------------------------------------
# Tool adapters: how a registry is invoked from the command line
# ---------------------------------------------------------------------------

def run(script, args, env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    # Timeboxed, because the ACCESS scenarios place FIFOs where receipts are
    # expected and a tool that opens one blocks forever. A suite that can hang
    # proves nothing; a tool that did not finish is reported as producing no
    # verdict at all, which is the defect the timeout exists to expose.
    try:
        return subprocess.run([sys.executable, os.path.join(RUN_DIR, script)] + args,
                              capture_output=True, text=True, env=env, timeout=90)
    except subprocess.TimeoutExpired as e:
        return subprocess.CompletedProcess(
            e.cmd, 124, stdout=(e.output or ""),
            stderr="the tool did not finish within 90s; a check that hangs prints no verdict "
                   "in either mode, which is worse than a crash")


def verdict_and_evidence(stdout, name):
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == name:
            return parts[1], line
    return "NO-VERDICT-LINE", ""


class DirTool:
    """sbe_gate.py and sbe_design.py: evidence is a file in the target directory."""

    def __init__(self, script, env=None, has_fallback=False):
        self.script = script
        self.env = env or {}
        # True only for a tool that can answer WITHOUT running the check (the
        # design tool's no-dossier fallback). The invoked heuristic below greps
        # for that fallback's load-bearing phrase, and for a tool that has no
        # such fallback the grep is constant-true and measures nothing, so the
        # accounting is only claimed where it means something.
        self.has_fallback = has_fallback

    def root(self, d):
        return d

    def place(self, d, relpath, content):
        write_file(os.path.join(d, relpath), content)

    def invoke(self, d, name, extra_env):
        env = dict(self.env)
        env.update(extra_env)
        return run(self.script, [name, d], env)

    def relpath(self, p):
        return p


class ScoreTool:
    """sbe_score.py: evidence lives under the vault, or behind an env var."""

    has_fallback = False    # every scorer check runs unconditionally; see DirTool

    def __init__(self, script):
        self.script = script
        self.env = {}

    def root(self, d):
        return d

    def place(self, d, relpath, content):
        write_file(os.path.join(d, relpath), content)

    def invoke(self, d, name, extra_env):
        env = {"BROTHERSBE_VAULT": d, "BROTHERSBE_REGISTRIES": "", "SBE_LINT_ROOT": ""}
        env.update(extra_env)
        return run(self.script, [], env)

    def relpath(self, p):
        # The registry stores absolute paths resolved against the default vault;
        # the test re-roots them into a throwaway one.
        return os.path.relpath(p, _telemetry.VAULT) if os.path.isabs(p) else p


ADAPTERS = {
    ("sbe_gate.py", "GATES"): DirTool("sbe_gate.py"),
    ("sbe_design.py", "CHECKS"): DirTool("sbe_design.py", env={"SBE_DOSSIER_ROOT": ""},
                                         has_fallback=True),
    ("sbe_score.py", "CHECKS"): ScoreTool("sbe_score.py"),
}


def write_file(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if isinstance(content, dict):
        body = json.dumps(content)
    elif isinstance(content, list):
        body = "".join(json.dumps(row) + "\n" for row in content)
    else:
        body = content
    with open(path, "w") as f:
        f.write(body)


# ---------------------------------------------------------------------------
# Scenario generation
# ---------------------------------------------------------------------------

WRONG_SHAPES = [
    ("c-json-is-a-list", "[{\"figures\": []}]"),
    ("c-json-is-a-string", "\"a string\""),
    ("c-json-is-a-number", "42"),
]
MALFORMED = ("d-malformed-json", "{not json\n")
WRONG_SHAPE_LINES = [
    ("c-jsonl-line-is-a-string", "\"a string\"\n"),
    ("c-jsonl-line-is-a-list", "[1, 2, 3]\n"),
]


class Scenario:
    """One run: files to write, env to set, the verdict that would be a defect."""

    def __init__(self, sid, label, files, env=None, expect=None, forbid_pass=True,
                 expect_invoked=True, setup=None):
        self.sid = sid
        self.label = label
        self.files = files
        self.env = env or {}
        self.expect = expect          # an exact verdict, or None for "anything but PASS"
        self.forbid_pass = forbid_pass
        self.expect_invoked = expect_invoked
        # A callable run against the scenario directory after the files are
        # written: the ACCESS scenarios use it to chmod evidence to 000, replace
        # it with a broken symlink or a FIFO, or plant a symlink loop. The
        # runner restores read access before the temp directory is cleaned up.
        self.setup = setup
        # True when the fixture's declared git state must be applied: the "full"
        # scenario always applies it; an access scenario that asserts the full
        # verdict (loop-beside-evidence) needs the same commit or it would be
        # asserting the wrong baseline.
        self.use_git = False


def legacy_cases(tool, check):
    """The four original shapes: absent file, declared-empty, wrong type, malformed."""
    out = [Scenario("a-empty-directory", "a", {}, expect="NO-DATA",
                    expect_invoked=(tool.script != "sbe_design.py"))]
    if tool.script == "sbe_design.py":
        # A directory that IS a dossier, so the tool cannot answer from its
        # no-target fallback and the check itself has to produce the verdict.
        out.append(Scenario("a2-dossier-with-a-zero-byte-intake", "a2",
                            {"00-intake.json": ""}))
    if check.kind == "tree":
        fx = check.empty_fixture or {}
        out.append(Scenario("b-declares-nothing", "b", fx.get("files", {}),
                            env={check.reads[0]: fx.get("value", "%(dir)s")},
                            expect=check.empty_expect))
        return out
    path = tool.relpath(check.reads[0])
    if check.kind == "json":
        body = json.dumps({check.item_key: []}) if check.item_key else "{}"
    elif check.kind == "jsonl":
        body = ""
    elif check.kind == "git":
        body = check.empty_fixture or ""
    else:
        body = ""
    out.append(Scenario("b-declares-nothing", "b", {path: body}, expect=check.empty_expect))
    if check.kind == "json":
        for cid, content in WRONG_SHAPES:
            out.append(Scenario(cid, "c", {path: content}, expect="FAIL"))
        out.append(Scenario(MALFORMED[0], "d", {path: MALFORMED[1]}, expect="FAIL"))
    elif check.kind == "jsonl":
        for cid, content in WRONG_SHAPE_LINES:
            out.append(Scenario(cid, "c", {path: content}, expect="FAIL"))
        out.append(Scenario(MALFORMED[0], "d", {path: MALFORMED[1] + "\n"}, expect="FAIL"))
    return out


def hollow_cases(tool, check):
    """The empty-VALUE sweep, derived from the check's own worked example."""
    fx = check.full_fixture
    if fx is None:
        return []
    files, env = fx["files"], fx.get("env", {})
    out = [Scenario("full", "full", files, env=env, expect=check.full_expect,
                    forbid_pass=(check.full_expect != "PASS"))]

    def variant(sid, label, rel, content):
        # A hollowing that changed nothing is not a scenario. Emptying a subtree
        # whose only leaf is a preserved boolean reproduces the fixture exactly,
        # and asserting "this must not PASS" about the untouched positive example
        # would be asserting the opposite of the sanity case two lines above.
        if content == files[rel]:
            return
        merged = dict(files)
        merged[rel] = content
        out.append(Scenario(sid, label, merged, env=env))

    for rel, content in files.items():
        if isinstance(content, (dict, list)):
            for tag, vname, value in COMMENT_ONLY:
                variant("%s::*|%s" % (rel, vname), tag, rel,
                        hollowed(content, value, keep_booleans=True))
            for tag, vname, value in (EMPTY_VALUES + VACUOUS_VALUES + REDUCES_TO_NOTHING
                                      + NOT_MEASUREMENTS):
                variant("%s::*|%s" % (rel, vname), tag, rel,
                        hollowed(content, value, keep_booleans=True))
                for path in container_paths(content):
                    if not path:
                        continue
                    variant("%s::%s/*|%s" % (rel, render(path), vname), tag, rel,
                            replace_at(content, path,
                                       hollowed(at(content, path), value, keep_booleans=True)))
                for path in leaf_paths(content):
                    variant("%s::%s|%s" % (rel, render(path), vname), tag, rel,
                            replace_at(content, path, value))
            for path in leaf_paths(content):
                leaf = at(content, path)
                if not isinstance(leaf, bool):
                    continue
                for word in OPPOSITE_WORDS[leaf]:
                    variant("%s::%s|says-%s" % (rel, render(path), word), "t", rel,
                            replace_at(content, path, word))
            for path in container_paths(content):
                if not isinstance(at(content, path), list):
                    continue
                items = at(content, path)
                variant("%s::%s=[{}]" % (rel, render(path)), "h", rel,
                        replace_at(content, path, [{} for _ in items]))
                variant("%s::%s=[]" % (rel, render(path)), "j", rel,
                        replace_at(content, path, []))
        else:
            variant("%s::whitespace" % rel, "f", rel, "   \n")
            for _tag, vname, value in VACUOUS_VALUES:
                # The text-shaped vacuity: an artifact whose whole body is the
                # word TODO is present, non-empty, and says nothing.
                variant("%s::vacuous-%s" % (rel, vname), "v", rel, "%s\n" % value)
                # And the same one level in: every heading kept, every body
                # replaced by a placeholder rather than emptied. This is the
                # markdown shape of "the keys are all there and the values all
                # say TODO".
                if heading_sections(content):
                    filled = "".join("%s\n%s\n" % (l, value) for l in content.splitlines()
                                     if l.lstrip().startswith("#"))
                    variant("%s::every-section-%s" % (rel, vname), "v", rel, filled)
            for title, _body in heading_sections(content):
                variant("%s##%s" % (rel, title), "s", rel, drop_section(content, title))
            # The comment-shaped hollowing, which no sweep had: an author does
            # not empty a section, they comment it out, and a section that
            # renders as empty was scaffolding to four readers and content to
            # four others in the same file. Whole file first, then one heading's
            # body at a time. Markdown only: an HTML comment is a markdown
            # notion, and a source file holding one is just text to the lint.
            if rel.endswith(".md"):
                variant("%s::commented-out" % rel, "k", rel,
                        "<!-- moved to the wiki\n%s\n-->\n" % content)
                for title, _body in heading_sections(content):
                    gutted = drop_section(content, title).replace(
                        "# %s" % title,
                        "# %s\n<!-- the %s section moved to the wiki -->" % (title, title), 1)
                    # The "|" keeps the sid's exemption key identical to the
                    # dropped-section sweep's: a declared optional leaf covers
                    # the same section whichever way it was emptied.
                    variant("%s##%s|commented" % (rel, title), "k", rel, gutted)
        variant("%s::zero-bytes" % rel, "i", rel, "")

    # (i) in its purest form: every file the check DECLARES it reads exists with
    # the right name and holds nothing at all.
    named = {tool.relpath(p): "" for p in check.reads if os.sep in p or p.endswith(
        (".json", ".jsonl", ".md", ".txt")) or p == "APPROVAL"}
    if named:
        out.append(Scenario("declared-reads::zero-bytes", "i", named, env=env))
    return out


# The ACCESS axis. Seven rounds of scenarios probed what the evidence SAYS: this
# is the first set that probes whether the tool could OPEN it. The suite held
# zero occurrences of chmod, symlink or mkfifo in 4200 lines of test code, so no
# scenario had ever distinguished a check that read clean evidence from a check
# that read nothing: a chmod 000 source file vanished from a lint count, chmod
# 000 registry files turned two FAILs into two PASSes saying "none", and a FIFO
# hung all three tools with no verdict, in both modes, forever.
ACCESS_APPLIES = os.name == "posix" and os.geteuid() != 0

def _chmod_000(rel):
    def setup(d):
        os.chmod(os.path.join(d, rel), 0)
    return setup


def _broken_symlink(rel):
    def setup(d):
        p = os.path.join(d, rel)
        os.remove(p)
        os.symlink(os.path.join(d, "no-such-target"), p)
    return setup


def _symlink_loop(rel):
    def setup(d):
        p = os.path.join(d, rel)
        os.remove(p)
        os.symlink(os.path.basename(p), p)      # a link that resolves to itself
    return setup


def _fifo(rel):
    def setup(d):
        p = os.path.join(d, rel)
        os.remove(p)
        os.mkfifo(p)
    return setup


def _loop_beside(d):
    os.symlink(".", os.path.join(d, "selfloop-dir"))


def restore_access(top):
    """Give everything under the scenario directory its read bits back.

    tempfile.TemporaryDirectory cannot delete a chmod 000 entry, so a scenario
    that took access away gives it back before cleanup. Top-down, so a 000
    directory is reopened before the walk needs to enter it.
    """
    try:
        os.chmod(top, 0o755)
    except OSError:
        return
    for dp, dns, fns in os.walk(top):
        for n in dns + fns:
            p = os.path.join(dp, n)
            if os.path.islink(p):
                continue
            try:
                os.chmod(p, 0o755 if n in dns else 0o644)
            except OSError:  # sbe: allow-silent cleanup only; the temp dir is deleted right after and an entry this cannot reopen fails loudly there
                pass


def access_cases(tool, check):
    """Evidence that exists and cannot be opened must never read as clean or absent.

    Four shapes per check, each derived from the check's own worked example: the
    evidence file unreadable (chmod 000), replaced by a broken symlink, replaced
    by a symlink loop, and replaced by a FIFO (which blocks any open() forever,
    so it also proves the tool terminates). A fifth plants a self-referential
    directory symlink beside intact evidence and demands the walk terminates
    without changing the verdict. Not applicable when running as root (chmod
    cannot take access away from root) and declared so rather than skipped.
    """
    fx = check.full_fixture
    if not ACCESS_APPLIES or fx is None:
        return []
    files, env = fx["files"], fx.get("env", {})
    declared = tool.relpath(check.reads[0])
    target = declared if declared in files else sorted(files)[0]
    out = [
        Scenario("access::%s|chmod-000" % target, "x", files, env=env,
                 setup=_chmod_000(target)),
        Scenario("access::%s|broken-symlink" % target, "x", files, env=env,
                 setup=_broken_symlink(target)),
        Scenario("access::%s|symlink-loop" % target, "x", files, env=env,
                 setup=_symlink_loop(target)),
        Scenario("access::%s|fifo" % target, "x", files, env=env,
                 setup=_fifo(target)),
        # Evidence intact, a loop planted beside it: the walk must terminate and
        # the verdict must be exactly what the worked example produces.
        Scenario("access::loop-beside-evidence", "x", files, env=env,
                 setup=_loop_beside, expect=check.full_expect,
                 forbid_pass=(check.full_expect != "PASS")),
    ]
    out[-1].use_git = True
    return out


# ---------------------------------------------------------------------------

def counts():
    """(checks, registries, scenarios) without running anything.

    Exists so a doc that prints this test's summary line can be checked against
    it mechanically. Three shipped docs printed an eval count the suite had not
    produced for a whole wave, which is the same defect as a stale evidence
    string: a number asserted where nothing recomputed it.
    """
    mods, _failed = load_tool_modules()
    registries, _ = discover_registries(mods)
    checks = scenarios = regs = 0
    for fn, attr, reg in registries:
        tool = ADAPTERS.get((fn, attr))
        if tool is None:
            continue
        regs += 1
        for _name, check in reg.items():
            checks += 1
            scenarios += (len(legacy_cases(tool, check)) + len(hollow_cases(tool, check))
                          + len(access_cases(tool, check)))
    return checks, regs, scenarios


def main():
    mods, import_failures = load_tool_modules()
    del PRUNED_WITH_SOURCE[len(set(PRUNED_WITH_SOURCE)):]
    registries, defects = discover_registries(mods)
    failures = list(import_failures) + list(defects)
    checked = ran = 0
    notapplicable, exemptions, unregistered = [], [], []

    print("BROTHERSBE HONESTY META-TEST: no check may report PASS over evidence it never examined")
    print("tools under test: %s" % RUN_DIR)

    # Registries are discovered. One this test cannot invoke is a failure, never a skip.
    known = {}
    for fn, attr, reg in registries:
        adapter = ADAPTERS.get((fn, attr))
        if adapter is None:
            failures.append("%s.%s is a registry of %d Check(s) that this test does not know how "
                            "to invoke. Add an adapter in ADAPTERS; a registry nobody walks is a "
                            "check nobody covers" % (fn, attr, len(reg)))
            continue
        known[(fn, attr)] = (adapter, reg)

    # Every function anywhere in tools/ that can return PASS must be registered.
    registered_fns = {c.fn for _, _, reg in registries for c in reg.values()
                      if isinstance(c, Check)}
    registered_pairs = {(getattr(f, "__module__", "") + ".py", f.__name__) for f in registered_fns}
    for fn, name, why in pass_returning_functions(mods):
        if (fn, name) not in registered_pairs:
            unregistered.append("%s:%s (%s)" % (fn, name, why))
    if unregistered:
        failures.append("function(s) that can return the verdict PASS but sit in no registry, so "
                        "no scenario in this file reaches them: %s" % ", ".join(unregistered))
    for path in sorted(set(PRUNED_WITH_SOURCE)):
        failures.append("%s was pruned from the walk and holds Python source, so any registry or "
                        "verdict-producing function in it is outside this test's coverage while "
                        "the summary line below still counts as if it were not" % path)
    for path in sorted(set(DENIED_DIRS)):
        failures.append("%s could not be entered (permission or I/O error), so any registry or "
                        "verdict-producing function in it is outside this test's coverage while "
                        "the summary line below still counts as if it were not" % path)
    if not ACCESS_APPLIES:
        notapplicable.append("the ACCESS scenarios (chmod, broken symlink, symlink loop, FIFO) do "
                             "not apply on this host: running as root, or not POSIX, so taking "
                             "read access away is not possible; declared rather than skipped")

    for (fn, attr), (tool, reg) in sorted(known.items()):
        print("\n%s.%s  (%d checks discovered)" % (fn, attr, len(reg)))
        for name, check in reg.items():
            checked += 1
            if check.kind not in ("json", "jsonl"):
                notapplicable.append("%s %s: evidence is %s, so the wrong-shape and malformed-JSON "
                                     "cases do not apply" % (fn, name, check.kind))
            if check.full_fixture is None:
                notapplicable.append("%s %s: no positive fixture to hollow, declared reason: %s"
                                     % (fn, name, check.no_full_fixture))
            if check.full_expect != "PASS":
                notapplicable.append("%s %s: its worked example asserts %s rather than PASS, "
                                     "declared reason: %s"
                                     % (fn, name, check.full_expect, check.full_expect_reason))
            for path, why in sorted(check.optional_leaves.items()):
                exemptions.append("%s %s [%s]: %s" % (fn, name, path, why))
            scenarios = (legacy_cases(tool, check) + hollow_cases(tool, check)
                         + access_cases(tool, check))
            invoked_count = 0
            saw_full = False
            for sc in scenarios:
                with tempfile.TemporaryDirectory() as d:
                    for rel, content in subst(sc.files, d).items():
                        tool.place(d, rel, content)
                    git = ((check.full_fixture or {}).get("git")
                           if (sc.label == "full" or sc.use_git) else None)
                    if git:
                        git_commit(d, git["message"])
                    if sc.setup:
                        sc.setup(d)
                    out = tool.invoke(d, name, subst(sc.env, d))
                    ran += 1
                    restore_access(d)
                got, line = verdict_and_evidence(out.stdout, name)
                # The invoked heuristic greps for the design tool's no-target
                # fallback phrase. For a tool with no such fallback the grep is
                # constant-true and would measure nothing, so it is only applied,
                # and only reported, where a fallback exists to fall into.
                invoked = (NOT_INVOKED not in line) if tool.has_fallback else True
                invoked_count += invoked
                saw_full = saw_full or (sc.label == "full" and got == check.full_expect)
                bad = []
                exempt = check.optional_leaves.get(sc.sid.split("|")[0])
                if got == "PASS" and sc.forbid_pass and not exempt:
                    bad.append("a PASS over evidence that declares nothing is the defect this "
                               "whole project exists to prevent")
                elif sc.expect and got != sc.expect and not (exempt and got == "PASS"):
                    bad.append("want %s got %s" % (sc.expect, got))
                elif got not in ("PASS", "FAIL", "NO-DATA"):
                    bad.append("no verdict line for this check at all (%s)" % got)
                if "Traceback" in out.stderr:
                    bad.append("a traceback escaped to stderr")
                if out.returncode == 124:
                    bad.append("the tool hung: %s" % out.stderr)
                elif out.returncode != 0:
                    bad.append("advisory mode exited %d" % out.returncode)
                if sc.expect_invoked and tool.has_fallback and not invoked:
                    bad.append("the scenario never reached the check: the tool answered from its "
                               "no-target fallback")
                mark = "ok" if not bad else ("FAILED: " + "; ".join(bad))
                if exempt and got == "PASS":
                    mark = "ok (declared exemption)"
                if bad:
                    failures.append("%s %s [%s] %s" % (fn, name, sc.sid, "; ".join(bad)))
                if not QUIET or bad:
                    print("  %-26s %-3s %-52s %-9s %s"
                          % (name, sc.label, sc.sid[:52], got, mark))
            if check.full_fixture is not None and not saw_full:
                failures.append("%s %s: the declared full_fixture did not produce %s, so nothing "
                                "here proves the check body ran or that its worked example is a "
                                "real one" % (fn, name, check.full_expect))
            if tool.has_fallback:
                print("  %-26s %s" % (name, "-> %d/%d scenarios reached the check body"
                                      % (invoked_count, len(scenarios))))
            else:
                print("  %-26s %s" % (name, "-> invocation accounting n/a: this tool runs every "
                                            "check unconditionally, so there is no fallback to "
                                            "fall into"))

    print("\ndeclared not-applicable (printed, never skipped silently):")
    for n in notapplicable:
        print("  %s" % n)
    print("\ndeclared exemptions from the empty-value sweep (each states its reason):")
    for e in exemptions or ["none"]:
        print("  %s" % e)
    print("\n%d checks discovered from %d registries in %d module(s), %d scenarios run, %d failure(s)."
          % (checked, len(known), len(mods), ran, len(failures)))
    for f in failures:
        print("  FAIL %s" % f)
    sys.exit(1 if failures else 0)


def git_commit(d, message):
    for cmd in (["init", "-q"], ["config", "user.email", "e@e"], ["config", "user.name", "T"]):
        subprocess.run(["git", "-C", d] + cmd, check=True, capture_output=True)
    subprocess.run(["git", "-C", d, "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", d, "commit", "-qm", message], check=True, capture_output=True)


if __name__ == "__main__":
    main()
