#!/usr/bin/env python3
"""The honesty meta-test: no check in this project may report PASS over evidence
it never examined.

This exists because fixing the instances did not fix the CLASS. Six named cases
of "a PASS whose evidence asserts something the tool never inspected" were fixed
by hand, and a re-review found the identical defect alive in four more places
inside the same two files that wave edited. A seventh hand fix would have been
the same mistake a seventh time.

So this test does not carry a list of checks. It ENUMERATES the registries in
sbe_gate.py, sbe_design.py and sbe_score.py, and it refuses to run if any entry
in them is a bare function instead of a Check declaring its evidence. A check
added next year is covered the moment it is registered, because it cannot be
registered without saying what it reads and what its empty state is. Adding a
check that lies is now a two-step act of deliberation rather than an oversight.

Four cases per check, run through the real command line entry points, because a
verdict that only exists when you call the function directly is not the verdict
an operator sees:

  a  a completely empty directory                     -> NO-DATA, never PASS
  b  evidence that exists and declares zero items     -> the declared empty state,
                                                         which may never be PASS
  c  valid JSON of the wrong shape (list, string,
     number)                                          -> FAIL, a verdict line is
                                                         still printed, and no
                                                         traceback escapes
  d  malformed JSON                                   -> FAIL

Case c is two assertions, not one. A tool that crashes prints no verdict line
for the crashing check or for any check after it, and in advisory mode exits 0:
the gate does not fail, it disappears, which is the defect in its purest form.

Cases c and d apply to checks whose evidence is JSON. A check reading markdown, a
source tree or a commit trailer says so through its declared kind, and this test
PRINTS that as a declared not-applicable rather than skipping it quietly, so the
coverage claim at the bottom is checkable.

Run: python3 evals/test_no_data_class.py
     python3 evals/test_no_data_class.py --tools <dir>

The second form runs the SAME scenarios against a different copy of the tools,
which is how the before-list was measured against the tree that shipped these
defects: the scenarios and the expected verdicts are data held here, the code
under test is whatever --tools points at. A test that can only be run against the
fixed code proves nothing about what it caught.
"""
import json, os, subprocess, sys, tempfile
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(HERE, "..", "tools")
sys.path.insert(0, os.path.abspath(TOOLS_DIR))

# The registries (the declarations) always come from this working tree. The code
# actually invoked can be pointed elsewhere, which is how the before-list is
# measured against the tree that shipped the defects.
RUN_DIR = os.path.abspath(TOOLS_DIR)
if "--tools" in sys.argv:
    RUN_DIR = os.path.abspath(sys.argv[sys.argv.index("--tools") + 1])

from sbe_checks import Check  # noqa: E402

_gate = SourceFileLoader("sbe_gate", os.path.join(TOOLS_DIR, "sbe_gate.py")).load_module()
_design = SourceFileLoader("sbe_design", os.path.join(TOOLS_DIR, "sbe_design.py")).load_module()
_score = SourceFileLoader("sbe_score", os.path.join(TOOLS_DIR, "sbe_score.py")).load_module()
_telemetry = SourceFileLoader("sbe_telemetry", os.path.join(TOOLS_DIR, "sbe_telemetry.py")).load_module()

# Valid JSON that is not a receipt. Each of these used to reach a .get() call and
# raise, taking the rest of the run down with it.
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


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def run(script, args, env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    return subprocess.run([sys.executable, os.path.join(RUN_DIR, script)] + args,
                          capture_output=True, text=True, env=env)


def verdict_of(stdout, name):
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == name:
            return parts[1]
    return "NO-VERDICT-LINE"


class DirTool:
    """sbe_gate.py and sbe_design.py: evidence is a file in the target directory."""

    def __init__(self, script, registry, env=None):
        self.script = script
        self.registry = registry
        self.env = env or {}

    def place(self, d, check, relpath, content):
        write(os.path.join(d, relpath), content)

    def invoke(self, d, name, extra_env):
        env = dict(self.env)
        env.update(extra_env)
        return run(self.script, [name, d], env)

    def evidence_path(self, check):
        return check.reads[0]


class ScoreTool:
    """sbe_score.py: evidence lives under the vault, or behind an env var."""

    def __init__(self, script, registry):
        self.script = script
        self.registry = registry
        self.env = {}

    def place(self, d, check, relpath, content):
        write(os.path.join(d, relpath), content)

    def invoke(self, d, name, extra_env):
        env = {"BROTHERSBE_VAULT": d, "BROTHERSBE_REGISTRIES": "", "SBE_LINT_ROOT": ""}
        env.update(extra_env)
        return run(self.script, [], env)

    def evidence_path(self, check):
        # The registry stores absolute paths resolved against the default vault;
        # the test re-roots them into a throwaway one.
        return os.path.relpath(check.reads[0], _telemetry.VAULT)


TOOLS = [
    DirTool("sbe_gate.py", _gate.GATES),
    DirTool("sbe_design.py", _design.CHECKS, env={"SBE_DOSSIER_ROOT": ""}),
    ScoreTool("sbe_score.py", _score.CHECKS),
]


def cases_for(tool, check):
    """(case id, expected verdict, files to write, extra env) per check."""
    out = [("a-empty-directory", "NO-DATA", {}, {})]
    if check.kind == "tree":
        fx = check.empty_fixture or {}
        files = fx.get("files", {})
        out.append(("b-declares-nothing", check.empty_expect, files,
                    {check.reads[0]: fx.get("value", "%(dir)s")}))
        return out
    path = tool.evidence_path(check)
    if check.kind == "json":
        body = json.dumps({check.item_key: []}) if check.item_key else "{}"
    elif check.kind == "jsonl":
        body = ""
    elif check.kind == "git":
        body = check.empty_fixture or ""
    else:                       # text
        body = ""
    out.append(("b-declares-nothing", check.empty_expect, {path: body}, {}))
    if check.kind == "json":
        for cid, content in WRONG_SHAPES:
            out.append((cid, "FAIL", {path: content}, {}))
        out.append((MALFORMED[0], "FAIL", {path: MALFORMED[1]}, {}))
    elif check.kind == "jsonl":
        for cid, content in WRONG_SHAPE_LINES:
            out.append((cid, "FAIL", {path: content}, {}))
        out.append((MALFORMED[0], "FAIL", {path: MALFORMED[1] + "\n"}, {}))
    return out


def main():
    failures, checked, ran = [], 0, 0
    notapplicable = []
    print("BROTHERSBE HONESTY META-TEST: no check may report PASS over evidence it never examined")
    for tool in TOOLS:
        print("\n%s  (%d checks in its registry)" % (tool.script, len(tool.registry)))
        for name, check in tool.registry.items():
            if not isinstance(check, Check):
                failures.append("%s: %s is registered as a bare %s, not a Check declaring its "
                                "evidence, so this test cannot cover it"
                                % (tool.script, name, type(check).__name__))
                print("  %-26s REGISTRY DEFECT: not a Check" % name)
                continue
            checked += 1
            if check.kind not in ("json", "jsonl"):
                notapplicable.append("%s %s: evidence is %s, so the wrong-shape and malformed-JSON "
                                     "cases do not apply" % (tool.script, name, check.kind))
            for cid, expect, files, env in cases_for(tool, check):
                with tempfile.TemporaryDirectory() as d:
                    for rel, content in files.items():
                        tool.place(d, check, rel, content)
                    env = {k: (v % {"dir": d} if "%(dir)s" in v else v) for k, v in env.items()}
                    out = tool.invoke(d, name, env)
                    ran += 1
                got = verdict_of(out.stdout, name)
                bad = []
                if got != expect:
                    bad.append("want %s got %s" % (expect, got))
                if got == "PASS":
                    bad.append("a PASS over evidence that declares nothing is the defect this "
                               "whole project exists to prevent")
                if "Traceback" in out.stderr:
                    bad.append("a traceback escaped to stderr")
                if out.returncode != 0:
                    bad.append("advisory mode exited %d" % out.returncode)
                mark = "ok"
                if bad:
                    mark = "FAILED: " + "; ".join(bad)
                    failures.append("%s %s [%s] %s" % (tool.script, name, cid, "; ".join(bad)))
                print("  %-26s %-26s %-9s %s" % (name, cid, got, mark))
    print("\ndeclared not-applicable (printed, never skipped silently):")
    for n in notapplicable:
        print("  %s" % n)
    print("\n%d checks enumerated from %d registries, %d scenarios run, %d failure(s)."
          % (checked, len(TOOLS), ran, len(failures)))
    for f in failures:
        print("  FAIL %s" % f)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
