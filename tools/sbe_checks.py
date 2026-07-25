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
  optional_leaves fields in full_fixture the PASS sentence does not assert over,
                 each with a stated reason, printed on every run

Two rounds of this fix modelled "absent evidence" as an absent FILE, and the
defect survived as absent VALUES: a receipt that exists, parses, carries every
key, and holds "" in all of them. `full_fixture` exists so that no one has to
think of that shape again. The honesty test hollows the declared fixture leaf by
leaf, subtree by subtree, and whole, in empty strings, whitespace and nulls, and
requires that none of it produces a PASS. A field nobody empties is a field
nobody tested.

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

KINDS = ("json", "jsonl", "text", "tree", "git")


class Check:
    def __init__(self, fn, reads, kind, item_key=None,
                 empty_expect="NO-DATA", empty_note="", empty_fixture=None,
                 full_fixture=None, no_full_fixture="", optional_leaves=None):
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
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (list, dict, tuple, set)) and not value:
        return None
    return value


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
