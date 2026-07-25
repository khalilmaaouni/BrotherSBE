#!/usr/bin/env python3
"""The registry contract every BrotherSBE check is registered under.

Why this file exists. Six named instances of one defect were fixed by hand and
the same defect was found alive in four more places inside the same files. A
check that reports PASS over evidence it never examined converts absence into
false assurance, which is the failure this whole project exists to prevent. One
more hand fix would have removed six more instances and left the class.

So a check is no longer just a function. A check is a function PLUS a mechanical
declaration of what it reads and what its empty states are:

  reads        the evidence file(s) or tree the check opens
  kind         how that evidence is shaped, which decides what "malformed" means
  item_key     for a JSON receipt holding a list, the key naming that list
  empty_expect the verdict when the evidence exists and declares nothing

empty_expect can never be PASS. The constructor refuses it. That is the class
made impossible rather than the instances made rare.

evals/test_no_data_class.py iterates the registries in sbe_gate.py,
sbe_design.py and sbe_score.py and refuses to run if any entry is a bare
function, so a check added next year is covered without anyone remembering.
"""

KINDS = ("json", "jsonl", "text", "tree", "git")


class Check:
    def __init__(self, fn, reads, kind, item_key=None,
                 empty_expect="NO-DATA", empty_note="", empty_fixture=None):
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

    def __call__(self, *a, **kw):
        return self.fn(*a, **kw)


def run_guarded(name, check, *args):
    """Run one check so that a crash inside it cannot delete its verdict.

    A gate that raises takes every gate after it down with it and prints no line
    for any of them, which is the absent-check failure in its purest form: the
    operator sees three verdicts where there should be four and nothing says so.
    A crashed check is a FAILED check. The exception text is the evidence.
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
