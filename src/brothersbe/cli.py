"""The `sbe` command line.

One entry point instead of nine script paths. What it is NOT, today: a
reimplementation. Every built subcommand here delegates to the tool in `tools/`
that already carries the behavior and the tests, and its exit code is that
tool's exit code. That is the whole point of the facade: the surface can change
while the thing being verified does not.

Subcommands the brief calls for but nothing implements yet are PRESENT and
REFUSE, naming the wave that will build them and exiting 3. They are not hidden
from `--help` and they do not print a plausible empty result. A command that
silently succeeds at nothing is the exact failure this project exists to stop,
and hiding it would only move the surprise to whoever reads the brief and asks
where it went.

Exit codes, stable from here:
  0  the command ran and NO control FAILED. Read that precisely: it is not the
     same as "a control passed". A run where every check reported NO-DATA also
     exits 0, because nothing failed, and nothing was examined either. The
     verdict lines say which happened; the exit code cannot.
  1  a control FAILED, or the underlying tool exited nonzero
  2  usage error: an unknown command, a missing argument, a bad path
  3  the command exists but is not built yet
"""
import argparse
import io
import json
import os
import subprocess
import sys

from . import SCHEMA_VERSION, repo_root, version

EXIT_OK = 0
EXIT_CONTROL_FAILED = 1
EXIT_USAGE = 2
EXIT_NOT_BUILT = 3


def _tool(name):
    return os.path.join(repo_root(), "tools", name)


def _delegate(tool_name, argv):
    """Run a tool in tools/ and hand back its exit code untouched.

    Streams rather than captures: the tools print evidence lines that a human or
    a CI log is meant to read, and swallowing them to re-print a summary would
    put a layer of paraphrase between the reader and the verdict.
    """
    path = _tool(tool_name)
    if not os.path.exists(path):
        sys.stderr.write("sbe: %s is missing from this installation; the command cannot "
                         "run and is not reporting a result\n" % path)
        return EXIT_USAGE
    return subprocess.call([sys.executable, path] + list(argv))


def _closing_caveat(command, code):
    """The last line a reader sees, and the one that stops an exit code from
    being over-read.

    `verify` and `review` aggregate several tools whose verdicts include NO-DATA
    and WAIVED, neither of which is a pass, and both of which leave the exit code
    at zero. Printing the caveat unconditionally is deliberate: counting the
    verdict lines here to say something more specific would mean parsing another
    tool's output format, and a miscount in this line would be worse than no
    line at all.
    """
    if code == EXIT_OK:
        sys.stdout.write(
            "\nsbe %s: exit 0 means no control FAILED. It does not mean a control passed. "
            "Read the verdict lines above: NO-DATA examined nothing and WAIVED suppressed a "
            "finding, and neither one is a pass.\n" % command)
    else:
        sys.stdout.write("\nsbe %s: exit %d, at least one control FAILED above.\n"
                         % (command, code))


def _cmd_verify(args):
    """The gates, in the order a reader wants them: design completeness first
    (an incomplete dossier makes every later verdict less meaningful), then the
    hard gates, then the scored surface."""
    target = args.path
    if not os.path.isdir(target):
        sys.stderr.write("sbe verify: '%s' is not a directory. A mistyped path must not "
                         "read as a clean scan.\n" % target)
        return EXIT_USAGE
    worst = EXIT_OK
    for tool, argv in (("sbe_design.py", ["--strict", target]),
                       ("sbe_gate.py", [target]),
                       ("sbe_score.py", ["--strict", target])):
        code = _delegate(tool, argv)
        if code != EXIT_OK:
            worst = EXIT_CONTROL_FAILED
    _closing_caveat("verify", worst)
    return worst


def _cmd_review(args):
    """What a reviewer runs before writing a word: the scored surface including
    the soft findings, plus the hard gates. Soft findings are shown because a
    soft FAIL is still a finding; it only means the exit code does not block."""
    target = args.path
    if not os.path.isdir(target):
        sys.stderr.write("sbe review: '%s' is not a directory.\n" % target)
        return EXIT_USAGE
    worst = EXIT_OK
    for tool, argv in (("sbe_score.py", ["--strict", "--strict-soft", target]),
                       ("sbe_gate.py", [target])):
        if _delegate(tool, argv) != EXIT_OK:
            worst = EXIT_CONTROL_FAILED
    _closing_caveat("review", worst)
    return worst


def _doctor_checks():
    """Every check returns (name, result, detail). NO-DATA is a real result here
    and is never folded into PASS: an environment question nobody could answer
    is not an environment that passed."""
    root = repo_root()
    out = []

    py = sys.version_info
    out.append(("python", "PASS" if py >= (3, 9) else "FAIL",
                "%d.%d.%d (floor is 3.9)" % (py[0], py[1], py[2])))

    missing = [t for t in ("sbe_gate.py", "sbe_score.py", "sbe_design.py", "sbe_intake.py",
                           "sbe_decide.py", "sbe_fence_hook.py", "sbe_telemetry.py")
               if not os.path.exists(_tool(t))]
    out.append(("tools", "PASS" if not missing else "FAIL",
                "all present in %s/tools" % root if not missing
                else "missing: %s" % ", ".join(missing)))

    manifest = os.path.join(root, ".claude-plugin", "plugin.json")
    if not os.path.exists(manifest):
        out.append(("plugin-manifest", "FAIL", "no .claude-plugin/plugin.json"))
    else:
        try:
            with io.open(manifest, encoding="utf-8") as fh:
                declared = json.load(fh).get("version")
            out.append(("plugin-manifest",
                        "PASS" if declared == version() else "FAIL",
                        "manifest %s, VERSION %s" % (declared, version())))
        except ValueError as exc:
            out.append(("plugin-manifest", "FAIL", "does not parse: %s" % exc))

    try:
        git = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                             cwd=os.getcwd(), capture_output=True, text=True)
        inside = git.returncode == 0 and git.stdout.strip() == "true"
    except OSError as exc:
        inside, git = False, None
        out.append(("git", "FAIL", "git is not runnable here: %s" % exc))
    if git is not None:
        out.append(("git", "PASS" if inside else "NO-DATA",
                    "working directory is inside a git tree" if inside
                    else "not inside a git tree, so nothing that reads a diff can run here"))

    vault = os.environ.get("BROTHERSBE_VAULT", "")
    out.append(("vault", "PASS" if vault else "NO-DATA",
                vault if vault else "BROTHERSBE_VAULT is unset, so telemetry, session logs "
                                    "and resume briefs have nowhere durable to go"))

    names_file = os.environ.get("BROTHERSBE_PRIVATE_NAMES_FILE",
                                os.path.expanduser("~/.brothersbe-private-names"))
    configured = bool(os.environ.get("BROTHERSBE_PRIVATE_NAMES")) or os.path.exists(names_file)
    out.append(("private-names", "PASS" if configured else "NO-DATA",
                "a private-name list is configured" if configured
                else "no private-name list, so the publish leak check scans nothing"))
    return out


def _cmd_doctor(args):
    checks = _doctor_checks()
    failed = [c for c in checks if c[1] == "FAIL"]
    if args.json:
        payload = {
            "tool": "sbe",
            "toolVersion": version(),
            "schemaVersion": SCHEMA_VERSION,
            "command": "doctor",
            "result": "FAIL" if failed else "PASS",
            "checks": [{"name": n, "result": r, "detail": d} for (n, r, d) in checks],
        }
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    else:
        for name, result, detail in checks:
            sys.stdout.write("%-16s %-8s %s\n" % (name, result, detail))
        sys.stdout.write("\nsbe %s, evidence schema %s. %d check(s): %d PASS, %d FAIL, "
                         "%d NO-DATA.\n"
                         % (version(), SCHEMA_VERSION, len(checks),
                            len([c for c in checks if c[1] == "PASS"]), len(failed),
                            len([c for c in checks if c[1] == "NO-DATA"])))
    return EXIT_CONTROL_FAILED if failed else EXIT_OK


def _cmd_impact(args):
    """Reconcile what the diff shows against what the human declared at intake."""
    from . import impact as impact_mod
    try:
        data = impact_mod.report(os.path.abspath(args.path), base=args.base, head=args.head,
                                 intake_path=args.intake, disposition_path=args.disposition)
    except impact_mod.DiffUnavailable as exc:
        sys.stderr.write("sbe impact: NO-DATA. %s\n" % exc)
        return EXIT_CONTROL_FAILED if args.strict else EXIT_OK
    if args.json:
        sys.stdout.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write("%s\n" % data["scope"])
        for hit in data["detected"]:
            sys.stdout.write("  DETECTED  %-22s %s (%s)\n"
                             % (hit["detector"], hit["file"], hit["why"]))
        for un in data["unmeasured"]:
            sys.stdout.write("  UNMEASURED %s%s\n"
                             % ((un["file"] + ": ") if un["file"] else "", un["reason"]))
        sys.stdout.write("\nproposed tier %s (a floor, not a ceiling), declared tier %s\n"
                         % (data["proposedTier"], data["humanTier"] or "none read"))
        if data["intakeProblem"]:
            sys.stdout.write("intake: %s\n" % data["intakeProblem"])
        for dis in data["disagreements"]:
            sys.stdout.write("  DISAGREEMENT %-22s %s [disposition: %s]\n"
                             % (dis["detector"], dis["file"], dis["disposition"]))
        sys.stdout.write("verdict: %s\n" % data["verdict"])
        if data["verdict"] == "REVIEW-REQUIRED":
            sys.stdout.write(
                "The diff shows more than the intake declared. This tool will not lower a "
                "human tier and will not raise one behind your back either: record a "
                "disposition naming the detector, the decision, the reason, who decided, and "
                "the head commit it was decided against.\n")
    if data["verdict"] in ("REVIEW-REQUIRED", "FAIL"):
        return EXIT_CONTROL_FAILED
    if data["verdict"] == "NO-DATA" and args.strict:
        return EXIT_CONTROL_FAILED
    return EXIT_OK


def _cmd_evidence(args):
    """Generate, verify and show commit-bound receipts.

    Not a delegation: there is no tool in `tools/` behind this one, because the
    defect it closes is that a receipt could be written by hand by the same
    agent whose work it verifies. The fix has to be a wrapper that runs the
    command itself, so it lives in the package.
    """
    from . import evidence as evidence_mod
    return evidence_mod.main(args.rest, exit_ok=EXIT_OK, exit_failed=EXIT_CONTROL_FAILED,
                             exit_usage=EXIT_USAGE)


def _cmd_version(args):
    sys.stdout.write("sbe %s (evidence schema %s, python %d.%d)\n"
                     % (version(), SCHEMA_VERSION, sys.version_info[0], sys.version_info[1]))
    return EXIT_OK


def _not_built(name, wave, reason):
    def run(args):
        sys.stderr.write(
            "sbe %s: NOT BUILT. %s\nThis lands in wave %s of the plugin conversion. It is "
            "listed here rather than hidden so nobody has to guess whether it exists, and it "
            "exits 3 rather than printing an empty result, because a command that succeeds at "
            "nothing is the failure this project exists to stop.\n" % (name, reason, wave))
        return EXIT_NOT_BUILT
    return run


#: The single source of truth for what this CLI offers. `--help` is generated
#: from it and a test asserts the two cannot drift apart.
COMMANDS = [
    ("doctor", "check this installation and the environment it will run in", _cmd_doctor),
    ("verify", "run the design check and the hard gates over a directory", _cmd_verify),
    ("review", "run the scored surface including soft findings, plus the gates", _cmd_review),
    ("design", "the design completeness check (delegates to sbe_design.py)",
     lambda a: _delegate("sbe_design.py", a.rest)),
    ("gate", "one hard gate by name, or all of them over a directory",
     lambda a: _delegate("sbe_gate.py", a.rest)),
    ("score", "the scored surface (delegates to sbe_score.py)",
     lambda a: _delegate("sbe_score.py", a.rest)),
    ("intake", "score the five intake questions into a tier",
     lambda a: _delegate("sbe_intake.py", a.rest)),
    ("decide", "run a decision table (delegates to sbe_decide.py)",
     lambda a: _delegate("sbe_decide.py", a.rest)),
    ("fences", "print the live fences the write hook would enforce",
     lambda a: _delegate("sbe_fence_hook.py", ["fences"] + list(a.rest))),
    ("version", "print the version and the evidence schema version", _cmd_version),
    ("impact", "read the git diff and reconcile it with the declared intake tier", _cmd_impact),
    ("inspect-change", "alias of impact, the name the finalization brief uses", _cmd_impact),
    ("plan", "generate the control plan for the detected change",
     _not_built("plan", 3, "Applicability is not computed yet, so a missing control cannot be "
                           "told apart from a control that was never required.")),
    ("evidence", "run a command and write the receipt it earned, verify one, or show one",
     _cmd_evidence),
    ("policy", "validate a repository policy file against its schema",
     _not_built("policy", 3, "The policy schema does not exist yet.")),
    ("exceptions", "list exceptions, their owners and their expiry",
     _not_built("exceptions", 4, "Exceptions are still free-form exemption files with no "
                                 "owner, approver or expiry to list.")),
    ("adopt", "inspect a repository for installation readiness, dry run by default",
     _not_built("adopt", 9, "The adoption doctor cannot yet tell a protected repository from "
                            "an unprotected one, and a readiness report that omits that is "
                            "worse than none.")),
]


def build_parser():
    epilog = "commands:\n" + "".join(
        "  %-15s %s\n" % (name, help_) for (name, help_, _) in COMMANDS)
    parser = argparse.ArgumentParser(
        prog="sbe",
        description="BrotherSBE: design first, then evidence. Absent evidence is NO-DATA and "
                    "never a pass.",
        epilog=epilog + "\nexit codes: 0 passed, 1 a control failed, 2 usage, 3 not built yet",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    sub = parser.add_subparsers(dest="command")
    for name, help_, _ in COMMANDS:
        child = sub.add_parser(name, help=help_, add_help=False)
        if name == "doctor":
            child.add_argument("--json", action="store_true",
                               help="machine-readable output carrying the tool and schema "
                                    "versions")
        elif name in ("impact", "inspect-change"):
            child.add_argument("path", nargs="?", default=".",
                               help="the repository to inspect (default: the current one)")
            child.add_argument("--base", default=None,
                               help="the commit or ref to diff from; without it the merge "
                                    "base with the default branch is used, and a repository "
                                    "with neither is reported rather than guessed at")
            child.add_argument("--head", default="HEAD", help="the commit or ref to diff to")
            child.add_argument("--intake", default=None,
                               help="path to 00-intake.json, the tier the human declared")
            child.add_argument("--disposition", default=None,
                               help="path to a recorded, commit-bound disposition file")
            child.add_argument("--json", action="store_true", help="machine-readable output")
            child.add_argument("--strict", action="store_true",
                               help="make NO-DATA block as well, for protected CI")
        elif name in ("verify", "review"):
            child.add_argument("path", nargs="?", default=".",
                               help="the directory to check (default: the current one)")
        else:
            child.add_argument("rest", nargs=argparse.REMAINDER,
                               help="arguments passed through to the underlying tool")
    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if argv and argv[0] in ("--version", "-V"):
        return _cmd_version(None)
    if not argv:
        parser.print_help()
        return EXIT_USAGE
    args = parser.parse_args(argv)
    if getattr(args, "version", False):
        return _cmd_version(args)
    for name, _help, run in COMMANDS:
        if args.command == name:
            return run(args)
    parser.print_help()
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
