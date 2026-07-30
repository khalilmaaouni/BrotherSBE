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

    # WARNING, never FAIL and never a silent PASS: a fixture identity (an
    # example.com email, or the literal name "ci") authoring real commits is
    # the class of leak that goes unnoticed until someone reads the log by
    # hand, which is exactly what doctor exists to surface early instead.
    try:
        email_run = subprocess.run(["git", "config", "user.email"], cwd=os.getcwd(),
                                   capture_output=True, text=True)
        name_run = subprocess.run(["git", "config", "user.name"], cwd=os.getcwd(),
                                  capture_output=True, text=True)
    except OSError as exc:
        out.append(("identity", "NO-DATA", "git is not runnable here: %s" % exc))
    else:
        email = email_run.stdout.strip()
        name = name_run.stdout.strip()
        if not email and not name:
            out.append(("identity", "NO-DATA",
                        "git config user.email and user.name are both unset here, so the "
                        "identity that would author a commit cannot be checked"))
        elif name == "ci" or email.endswith("@example.com"):
            out.append(("identity", "WARNING",
                        "git config reports name \"%s\" and email \"%s\"; that shape is a "
                        "fixture identity, and a fixture identity authoring real commits is "
                        "a leak, not a passing environment"
                        % (name or "(unset)", email or "(unset)")))
        else:
            out.append(("identity", "PASS",
                        "git config reports name \"%s\" and email \"%s\""
                        % (name or "(unset)", email or "(unset)")))

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


def _cmd_task(args):
    """The write-scope task registry and its diff postcondition.

    Not a delegation: like `evidence`, there is no tool in `tools/` behind it.
    The fence hook cannot govern Bash because shell cannot be parsed reliably,
    so this surface records what a writer declared it owns and, at close, reads
    the git diff and refuses when the tree changed outside that declaration.
    """
    from . import tasks as tasks_mod
    return tasks_mod.main(args.rest, exit_ok=EXIT_OK, exit_failed=EXIT_CONTROL_FAILED,
                          exit_usage=EXIT_USAGE)


def _cmd_work(args):
    """Isolated implementation for one plan task, with no autonomous merge rights.

    Not a delegation: like `evidence` and `task`, there is no tool in `tools/`
    behind it. `start` opens a dedicated branch, worktree and registry record
    from a validated plan; `finish` closes only on the diff postcondition AND a
    commit-bound receipt from the evidence store.
    """
    from . import work as work_mod
    return work_mod.main(args.rest, exit_ok=EXIT_OK, exit_failed=EXIT_CONTROL_FAILED,
                         exit_usage=EXIT_USAGE)
def _cmd_pr(args):
    """Pull-request surfaces, `verify` first. Not a delegation: like `evidence`,
    `task` and `work`, there is no tool in `tools/` behind it. The read-only
    GitHub client and the four-verdict report live in `brothersbe.prverify`;
    this wrapper only routes and keeps the exit-code table in one place. No
    closing caveat is printed here: the report's FINAL line is the last word,
    and a credentials-absent run must not carry any other verdict word after it.
    """
    from . import prverify as prverify_mod
    return prverify_mod.main(args.rest, exit_ok=EXIT_OK, exit_failed=EXIT_CONTROL_FAILED,
                             exit_usage=EXIT_USAGE)


def _cmd_converge(args):
    """Compare what a range of commits did against what the dossier approved.
    Deterministic evidence only: files, operations, entities, receipts, shas.
    There is no force flag and none may be added; a legitimate deviation is
    legalized by amending the dossier, regenerating the plan and the evidence,
    and re-running this."""
    from . import converge as converge_mod
    root = os.path.abspath(args.cwd or ".")
    try:
        report = converge_mod.evaluate(args.path, root, args.base, args.head)
    except converge_mod.ConvergeUnavailable as exc:
        sys.stderr.write("sbe converge: %s\n" % exc)
        return EXIT_USAGE
    converge_mod.write_report(report, os.path.abspath(args.path))
    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(converge_mod.render(report) + "\n")
    return EXIT_OK if report["final"] == "PASS" else EXIT_CONTROL_FAILED


def _cmd_adopt(args):
    """Inspect a repository for BrotherSBE readiness. Dry run by default:
    prints every proposal as a unified diff and writes nothing. `--apply`
    writes; `--force` allows overwriting an existing file that differs from
    the proposal. See `brothersbe.adopt` for what the report can and cannot
    tell you, and why.
    """
    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        sys.stderr.write("sbe adopt: '%s' is not a directory. A mistyped path must not read "
                         "as a clean scan.\n" % root)
        return EXIT_USAGE
    from . import adopt as adopt_mod

    applied = None
    if args.apply:
        written, skipped, _planned = adopt_mod.write(root, force=args.force)
        applied = {"written": written, "skipped": skipped}
    data = adopt_mod.report(root)

    if args.json:
        payload = dict(data)
        if applied is not None:
            payload["applied"] = applied
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return EXIT_OK

    sys.stdout.write("sbe adopt: %s\n" % data["root"])
    stack = data["detectedStack"]
    langs = ", ".join("%s(%d)" % (k, v) for k, v in stack["languages"].items())
    sys.stdout.write("  languages: %s\n" % (langs or "none detected"))
    sys.stdout.write("  migrations: %s, dbt models: %s, api contracts: %s, ci workflows: %s\n"
                     % (stack["hasMigrations"], stack["hasDbtModels"],
                        stack["hasApiContracts"], stack["hasCiWorkflows"]))
    if applied is not None:
        for path in applied["written"]:
            sys.stdout.write("  WROTE     %s\n" % path)
        for item in applied["skipped"]:
            sys.stdout.write("  SKIPPED   %s: %s\n" % (item["path"], item["reason"]))
        if not applied["written"]:
            sys.stdout.write("  nothing written; every proposal already matches this tree\n")
    else:
        for prop in data["proposals"]:
            if prop["identical"]:
                sys.stdout.write("  UNCHANGED %s\n" % prop["path"])
            else:
                sys.stdout.write("  PROPOSED  %s (%s)\n"
                                 % (prop["path"], "new file" if not prop["exists"]
                                    else "would overwrite, needs --force"))
                sys.stdout.write(prop["diff"] or "")
    for prot in data["protections"]:
        sys.stdout.write("  PROTECTION %-28s %s\n" % (prot["name"], prot["status"]))
    for fact in data["localFacts"]:
        sys.stdout.write("  LOCAL      %-28s %s\n" % (fact["name"], fact["status"]))
    dropped = data.get("notProposed", {}).get("categories", {})
    for key in sorted(dropped):
        sys.stdout.write("  NOT-PROPOSED %-26s no such path under this root: %s\n"
                         % (key, ", ".join(dropped[key]["missingPaths"])))
    if applied is None:
        sys.stdout.write("\nsbe adopt: dry run, nothing written. Rerun with --apply to write, "
                         "or --apply --force to overwrite a file that already exists and "
                         "differs.\n")
    return EXIT_OK


def _cmd_status(args):
    """Blocker-first: where a change stands, read from state other commands
    already recorded. See `brothersbe.status` for exactly what it reads and
    the kill criterion that keeps it from becoming a second gate runner.
    """
    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        sys.stderr.write("sbe status: '%s' is not a directory. A mistyped path must not read "
                         "as a clean scan.\n" % root)
        return EXIT_USAGE
    from . import status as status_mod

    if args.team:
        data = status_mod.build_team_report(root)
        if args.json:
            sys.stdout.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
        else:
            sys.stdout.write(status_mod.render_team(data))
        return EXIT_CONTROL_FAILED if status_mod.team_blocking(data) else EXIT_OK

    data = status_mod.build_report(root, base=args.base)
    if args.json:
        sys.stdout.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(status_mod.render_text(data))
        code = EXIT_CONTROL_FAILED if status_mod.any_blocking(data) else EXIT_OK
        sys.stdout.write(
            "\nsbe status: exit %d. %s\n"
            % (code, "at least one of BROKEN CLAIMS, MERGE BLOCKERS, ACTIVE CONFLICTS or "
                     "MISSING EVIDENCE carries an item above." if code else
                     "none of BROKEN CLAIMS, MERGE BLOCKERS, ACTIVE CONFLICTS or MISSING "
                     "EVIDENCE carries an item. That is not the same claim as everything "
                     "being inspected: read the NO-DATA lines above for what was not."))
        return code
    return EXIT_CONTROL_FAILED if status_mod.any_blocking(data) else EXIT_OK


def _cmd_init(args):
    """Install BrotherSBE's local footprint (config, dossier directory,
    optionally a copy of the consumer CI, and a receipt) into a repository.
    Dry run by default; refuses outside a git repository. See
    `brothersbe.initcmd` for the idempotence guarantee.
    """
    from . import initcmd

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        sys.stderr.write("sbe init: '%s' is not a directory.\n" % root)
        return EXIT_USAGE

    if not args.apply:
        reason = initcmd.refusal_reason(root)
        if reason:
            sys.stderr.write("sbe init: refused. %s\n" % reason)
            if args.json:
                sys.stdout.write(json.dumps({"refused": reason}, indent=2, sort_keys=True)
                                 + "\n")
            return EXIT_USAGE
        proposals, warnings = initcmd.plan(root, with_consumer_ci=args.with_consumer_ci)
        if args.json:
            sys.stdout.write(json.dumps({"root": root, "proposals": proposals,
                                        "warnings": warnings}, indent=2, sort_keys=True) + "\n")
        else:
            sys.stdout.write("sbe init: %s\n" % root)
            for item in proposals:
                if item["identical"]:
                    sys.stdout.write("  UNCHANGED %s\n" % item["path"])
                else:
                    sys.stdout.write("  PROPOSED  %s (%s)\n"
                                     % (item["path"], "new file" if not item["exists"]
                                        else "would overwrite"))
            for warning in warnings:
                sys.stdout.write("  WARNING   %s\n" % warning)
            sys.stdout.write("\nsbe init: dry run, nothing written. Rerun with --apply to "
                             "write.\n")
        return EXIT_OK

    try:
        result = initcmd.apply(root, with_consumer_ci=args.with_consumer_ci)
    except initcmd.NotAGitRepository as exc:
        sys.stderr.write("sbe init: refused. %s\n" % exc)
        if args.json:
            sys.stdout.write(json.dumps({"refused": str(exc)}, indent=2, sort_keys=True) + "\n")
        return EXIT_USAGE

    if args.json:
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return EXIT_OK

    if result["skippedAsNoop"]:
        sys.stdout.write("sbe init: already installed; nothing written this run.\n")
    else:
        for path in result["written"]:
            sys.stdout.write("  WROTE %s\n" % path)
        receipt = result["receipt"] or {}
        sys.stdout.write("\nsbe init: installed. Uninstall with:\n")
        for line in receipt.get("uninstallInstructions", []):
            sys.stdout.write("  %s\n" % line)
    for warning in result["warnings"]:
        sys.stdout.write("  WARNING %s\n" % warning)
    return EXIT_OK


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
    ("plan", "derive the task plan from a dossier and validate it (delegates to sbe_plan.py)",
     lambda a: _delegate("sbe_plan.py", a.rest)),
    ("evidence", "run a command and write the receipt it earned, verify one, or show one",
     _cmd_evidence),
    ("task", "the write-scope registry: open, list, fence, check, and close with the "
             "diff-against-declaration postcondition", _cmd_task),
    ("work", "isolated implementation for one plan task: start, check, finish, remove, "
             "and never a merge", _cmd_work),
    ("converge", "does the code between two commits still match the approved dossier: "
                 "scope, contracts, data, architecture, verification", _cmd_converge),
    ("pr", "pull-request surfaces: pr verify <number> --repo owner/name checks live "
           "GitHub approval evidence, bound to the head commit", _cmd_pr),
    ("policy", "validate a repository policy file against its schema",
     _not_built("policy", 3, "The policy schema does not exist yet.")),
    ("exceptions", "list exceptions, their owners and their expiry",
     _not_built("exceptions", 4, "Exceptions are still free-form exemption files with no "
                                 "owner, approver or expiry to list.")),
    ("adopt", "inspect a repository for installation readiness, dry run by default",
     _cmd_adopt),
    ("status", "blocker-first summary of where a change stands, read from recorded state",
     _cmd_status),
    ("init", "install BrotherSBE's local footprint into a repository, dry run by default",
     _cmd_init),
]


#: Commands whose whole argv belongs to the surface behind them: the tool in
#: `tools/` or the package module that owns the parsing, the help text and the
#: refusals. These are dispatched BY HAND in `main`, before argparse sees their
#: arguments, because argparse's REMAINDER drops a LEADING flag: `sbe intake -h`
#: never reached the tool that could answer it, the top parser refused it as a
#: usage error, and every one of these commands exited 2 for an explicit help
#: request. Help is not an error: `-h` on these commands now reaches the owning
#: parser, which prints its own usage and exits 0, and a genuinely bad flag is
#: refused by that same parser with a nonzero exit.
PASSTHROUGH = frozenset((
    "design", "gate", "score", "intake", "decide", "fences", "plan",
    "evidence", "task", "work", "pr"))


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
        # A passthrough child keeps add_help=False because its arguments,
        # including -h, belong to the surface behind it (main dispatches those
        # by hand). Every other child lets argparse answer -h itself: print
        # that command's usage and exit 0, which is what help means.
        child = sub.add_parser(name, help=help_, add_help=name not in PASSTHROUGH)
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
        elif name == "adopt":
            child.add_argument("path", nargs="?", default=".",
                               help="the repository to inspect (default: the current one)")
            child.add_argument("--dry-run", action="store_true",
                               help="propose without writing; this is the default whether "
                                    "or not the flag is given")
            child.add_argument("--apply", action="store_true",
                               help="write the proposed files; without it, nothing is "
                                    "written")
            child.add_argument("--force", action="store_true",
                               help="overwrite an existing file that differs from the "
                                    "proposal; without it, an existing file is skipped and "
                                    "named")
            child.add_argument("--json", action="store_true", help="machine-readable output")
        elif name == "converge":
            child.add_argument("path",
                               help="the dossier directory the range is measured against")
            child.add_argument("--base", required=True,
                               help="the commit the approved design was implemented from")
            child.add_argument("--head", required=True,
                               help="the commit whose tree is being judged")
            child.add_argument("--cwd", default=".",
                               help="the repository holding both commits (default: the "
                                    "current one)")
            child.add_argument("--json", action="store_true", help="machine-readable output")
        elif name == "status":
            child.add_argument("path", nargs="?", default=".",
                               help="the repository to summarize (default: the current one)")
            child.add_argument("--team", action="store_true",
                               help="one blocker-first view across every active change "
                                    "under design/, zero network, findings labeled "
                                    "observed, derived or unavailable")
            child.add_argument("--base", default=None,
                               help="the commit or ref to diff from for the intake-vs-diff "
                                    "section; without it the merge base with the default "
                                    "branch is used, exactly as in `sbe impact`")
            child.add_argument("--json", action="store_true", help="machine-readable output")
        elif name == "init":
            child.add_argument("path", nargs="?", default=".",
                               help="the repository to install into (default: the current "
                                    "one)")
            child.add_argument("--dry-run", action="store_true",
                               help="show intended mutations without writing; this is the "
                                    "default whether or not the flag is given")
            child.add_argument("--apply", action="store_true",
                               help="write the installation; without it, nothing is written")
            child.add_argument("--with-consumer-ci", action="store_true",
                               help="also propose copying the consumer CI workflow and "
                                    "composite action; never done unless asked")
            child.add_argument("--json", action="store_true", help="machine-readable output")
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
    if argv[0] in PASSTHROUGH:
        for name, _help, run in COMMANDS:
            if name == argv[0]:
                return run(argparse.Namespace(command=name, rest=argv[1:]))
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
