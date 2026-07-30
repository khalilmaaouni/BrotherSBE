"""`sbe work`: isolated implementation, no autonomous merge rights.

Spec of record: docs/specs/2026-07-30-sbe-work-lifecycle.md. The fixtures in
tools/test_sbe_work.py and this module both read from that document, and a
disagreement between them is a defect in one of them, never a negotiation.

One writer task, one branch, one worktree. `start` validates the plan with the
landed `sbe plan` checks, refuses incomplete or forced dependencies and every
collision by name, then creates the branch and worktree and opens the registry
record through the existing tasks machinery. `check` reports and never mutates.
`finish` closes only on the registry postcondition AND a receipt from the
evidence store bound to the worktree's current commit: an agent SAYING it ran
the command is not evidence, and an absent receipt is NO-DATA prose that still
refuses closure without being a FAIL by guess. `remove` deletes the worktree of
a CLOSED task, and a dirty worktree survives unless a human records a reason.

The single source of task state is the existing registry, .sbe/tasks.json,
exactly as src/brothersbe/tasks.py defines it: this module never invents a
second state file, and 08-plan.json is never mutated here, so plan determinism
holds. Git mutations are limited to branch creation, worktree add and worktree
remove; nothing here constructs a merge, a rebase or a push, and a source-level
fixture in tools/test_sbe_work.py greps this file to hold that line.

Python floor is 3.9: no match statements, no `X | Y` annotations. Standard
library only. Maturity: INTERNAL-EVAL, exercised on this repository's fixtures
and on no other estate.
"""
import argparse
import io
import json
import os
import shlex
import shutil
import sys
import tempfile

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools")
if os.path.abspath(TOOLS) not in sys.path:
    sys.path.insert(0, os.path.abspath(TOOLS))
# The plan validation this module reuses for start rule 1 is the SAME registry
# `sbe plan` runs (tools/sbe_plan.py, landed in Loop 1), never a re-typed copy:
# two validators would drift into two definitions of a valid plan.
import sbe_plan  # noqa: E402
from sbe_checks import run_guarded  # noqa: E402

from . import evidence as evidence_mod
from . import tasks as tasks_mod
from .tasks import (DiffUnavailable, RegistryUnusable, _git, load_registry,  # noqa: F401
                    repo_root_of, save_registry)


def _load_plan_file(path):
    """{"plan": dict or None, "problem": str} for one plan file. A file that is
    absent or does not parse is named, never guessed at."""
    if not os.path.isfile(path):
        return {"plan": None, "problem": "no plan file at %s" % path}
    try:
        with io.open(path, encoding="utf-8") as fh:
            plan = json.load(fh)
    except (ValueError, OSError) as exc:
        return {"plan": None, "problem": "%s does not parse as JSON (%s)" % (path, exc)}
    if not isinstance(plan, dict) or not isinstance(plan.get("tasks"), list):
        return {"plan": None,
                "problem": "%s does not hold a plan object with a tasks list" % path}
    return {"plan": plan, "problem": ""}


def _validate_plan(plan_path):
    """Every FAILing (check name, evidence) pair from the sbe plan validation
    checks, run against THIS plan file.

    The PLAN_CHECKS registry reads 08-plan.json from a dossier directory by
    fixed name, so the dossier is copied to a tempdir and the given plan file
    is placed there under that name. The copy is read-only scaffolding: the
    real dossier and the real plan are never written, so plan determinism
    holds, and the tempdir is removed before this returns.
    """
    dossier = os.path.dirname(os.path.abspath(plan_path))
    tmp = tempfile.mkdtemp(prefix="sbe-work-plan.")
    try:
        target = os.path.join(tmp, "dossier")
        shutil.copytree(dossier, target)
        shutil.copyfile(plan_path, os.path.join(target, sbe_plan.PLAN_FILE))
        failures = []
        for name in sbe_plan.PLAN_CHECKS:
            verdict, evidence = run_guarded(name, sbe_plan.PLAN_CHECKS[name], target)
            if verdict == "FAIL":
                failures.append((name, evidence))
        return failures
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _find_task(plan, task_id):
    for task in plan.get("tasks") or []:
        if task.get("id") == task_id:
            return task
    return None


def _find_record(data, task_id):
    """The LAST registry record with this id, any status, or None. Last because
    the registry appends; the newest record is the one a human is asking about."""
    found = None
    for record in data["tasks"]:
        if record.get("id") == task_id:
            found = record
    return found


def _dependency_problem(data, dep_id):
    """The refusal sentence for one dependsOn id, or None when a record with
    that id is closed clean. A dependency closed FORCED does not count as
    clean: the force recorded a disposition, never a completion."""
    closed = None
    for record in data["tasks"]:
        if record.get("id") != dep_id:
            continue
        if record.get("status") == "open":
            return ("dependency %s is still open in the registry; it must be closed "
                    "clean before this task can start" % dep_id)
        if record.get("status") == "closed":
            closed = record
    if closed is None:
        return ("dependency %s has no closed registry record at all; a plan task is "
                "complete only when a registry record with its id is closed clean"
                % dep_id)
    if closed.get("forced"):
        forced = closed["forced"]
        return ("dependency %s was closed FORCED by %s (%s); a forced close records a "
                "disposition, not a completion, and never satisfies a dependency"
                % (dep_id, forced.get("who", "(unnamed)"), forced.get("why", "(no reason)")))
    return None


def _first_command(task):
    """The task's first recorded verification command, or None."""
    for cmd in task.get("verificationCommands") or []:
        if isinstance(cmd, str) and cmd.strip():
            return cmd
    return None


def _evidence_dir(root):
    return os.path.join(root, *tasks_mod.DEFAULT_EVIDENCE_DIR.split("/"))


def _matching_receipt(root, verify_command, head):
    """{"match": {"path", "receipt"} or None, "unreadable": [sentences]}.

    The match is the first receipt in the evidence store whose recorded argv
    joins to `verify_command` and whose headCommit is `head`. A file in the
    store that does not load as a receipt is not evidence for anything, but it
    is NAMED in `unreadable` rather than skipped silently, and the caller
    prints those names: a store full of broken files must not read like an
    empty one. Absence of a match is the caller's NO-DATA, never a guess here.
    """
    out = {"match": None, "unreadable": []}
    directory = _evidence_dir(root)
    if not os.path.isdir(directory):
        return out
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if not name.endswith(".json") or not os.path.isfile(path):
            continue
        try:
            receipt = evidence_mod.load(path)
        except evidence_mod.ReceiptUnreadable as exc:
            out["unreadable"].append("%s was not readable as a receipt: %s" % (path, exc))
            continue
        argv = [str(a) for a in (receipt.get("argv") or [])]
        # External proof, estate C: comparing a rejoined argv to the plan's RAW
        # command text can never match a quoted argument, because the shell
        # consumed the quotes before argv existed. Both sides canonicalize
        # through shlex; a command shlex cannot parse falls back to the exact
        # string compare rather than guessing.
        try:
            wanted = shlex.split(verify_command)
        except ValueError:
            wanted = None
        if wanted is None:
            if " ".join(argv) != verify_command:
                continue
        elif argv != wanted:
            continue
        if receipt.get("headCommit") != head:
            continue
        if out["match"] is None:
            out["match"] = {"path": path, "receipt": receipt}
    return out


def _close_namespace(args, force, evidence_id):
    """The argparse namespace `tasks.cmd_close` reads, built here so the close
    path is the registry's own machinery and never a re-implementation."""
    return argparse.Namespace(id=args.task_id, force=force,
                              who=getattr(args, "who", None),
                              why=getattr(args, "why", None),
                              evidence_id=evidence_id,
                              evidence_dir=tasks_mod.DEFAULT_EVIDENCE_DIR,
                              cwd=args.cwd)


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------

def cmd_start(args, exit_ok, exit_failed, exit_usage):
    root = repo_root_of(os.path.abspath(args.cwd))
    plan_path = os.path.abspath(args.plan)
    loaded = _load_plan_file(plan_path)
    if loaded["problem"]:
        sys.stderr.write("sbe work start: %s\n" % loaded["problem"])
        return exit_usage
    plan = loaded["plan"]

    # Rule 1: the plan must pass the sbe plan validation checks, and any FAIL
    # refuses start quoting the failing check by name.
    failures = _validate_plan(plan_path)
    if failures:
        for name, evidence in failures:
            sys.stdout.write("  PLAN-CHECK %-14s FAIL %s\n" % (name, evidence))
        sys.stdout.write("sbe work start: refused. The plan at %s fails %d sbe plan "
                         "validation check(s), quoted above. Work never starts from a "
                         "plan the validator rejects.\n" % (plan_path, len(failures)))
        return exit_failed

    # Rule 2: the task id must exist in the plan.
    task = _find_task(plan, args.task_id)
    if task is None:
        sys.stderr.write("sbe work start: no task %r in %s. The plan's task ids are: %s\n"
                         % (args.task_id, plan_path,
                            ", ".join(t.get("id", "(no id)")
                                      for t in plan.get("tasks") or []) or "(none)"))
        return exit_usage

    owns = [p for p in (task.get("owns") or []) if isinstance(p, str) and p.strip()]
    role = task.get("role")

    # Hard boundary: reviewer tasks stay read-only. The plan validator already
    # FAILs this shape; it is refused here independently rather than trusted
    # to have been caught upstream.
    if role == "reviewer" and owns:
        sys.stdout.write("sbe work start: refused. Task %s is a reviewer task and owns %s; "
                         "reviewer tasks stay read-only and own nothing, always. This is "
                         "refused here independently of the plan validator, which FAILs "
                         "the same shape.\n" % (args.task_id, ", ".join(owns)))
        return exit_failed

    data = load_registry(root)

    # Rule 3: every dependency must be closed clean, and FORCED is not clean.
    for dep in task.get("dependsOn") or []:
        problem = _dependency_problem(data, dep)
        if problem:
            sys.stdout.write("sbe work start: refused. %s\n" % problem)
            return exit_failed

    # Rule 4: collisions, each refused by name.
    dossier = os.path.dirname(plan_path)
    change_id = os.path.basename(dossier)
    branch = "sbe/%s/%s" % (change_id, args.task_id)
    code, _out, _err = _git(["rev-parse", "--verify", "--quiet",
                             "refs/heads/%s" % branch], root)
    if code == 0:
        sys.stdout.write("sbe work start: refused. Branch %s already exists; one task, one "
                         "branch, and this one is taken.\n" % branch)
        return exit_failed
    worktree_dir = (os.path.abspath(args.worktree_dir) if args.worktree_dir
                    else os.path.dirname(root))
    worktree = os.path.join(worktree_dir, "%s-sbe-%s" % (os.path.basename(root),
                                                         args.task_id))
    if os.path.lexists(worktree):
        sys.stdout.write("sbe work start: refused. The worktree directory %s already "
                         "exists; one task, one worktree, and this path is taken.\n"
                         % worktree)
        return exit_failed
    if tasks_mod._find_open(data, args.task_id):
        sys.stdout.write("sbe work start: refused. Task id %s already has an OPEN registry "
                         "record; close it before starting it again.\n" % args.task_id)
        return exit_failed

    # Rule 5: branch at the plan baseCommit when set and resolvable, else at
    # HEAD, stated out loud as unpinned.
    sha = None
    base = plan.get("baseCommit")
    unpinned_note = ""
    if isinstance(base, str) and base.strip():
        code, out, _err = _git(["rev-parse", "--verify", "--quiet",
                                "%s^{commit}" % base.strip()], root)
        if code == 0 and out.strip():
            sha = out.strip()
        else:
            unpinned_note = ("plan baseCommit %s does not resolve in this repository, so "
                             "the branch is created at HEAD: UNPINNED, not the commit the "
                             "plan was derived against" % base.strip()[:12])
    else:
        unpinned_note = ("the plan records no baseCommit, so the branch is created at "
                         "HEAD: UNPINNED, not a commit the plan was derived against")
    if sha is None:
        code, out, err = _git(["rev-parse", "HEAD"], root)
        if code != 0 or not out.strip():
            sys.stderr.write("sbe work start: HEAD does not resolve in %s (%s); there is "
                             "nothing to branch from\n" % (root, err.strip() or "no output"))
            return exit_failed
        sha = out.strip()
        sys.stdout.write("sbe work start: %s\n" % unpinned_note)

    code, _out, err = _git(["branch", branch, sha], root)
    if code != 0:
        sys.stderr.write("sbe work start: git could not create branch %s at %s: %s\n"
                         % (branch, sha[:12], err.strip() or "no message"))
        return exit_failed
    code, _out, err = _git(["worktree", "add", worktree, branch], root)
    if code != 0:
        sys.stderr.write("sbe work start: git could not add the worktree at %s: %s. The "
                         "branch %s was already created and is left in place.\n"
                         % (worktree, err.strip() or "no message", branch))
        return exit_failed

    # Rule 6: open the registry record through the existing tasks machinery,
    # with fields read mechanically from the plan.
    open_ns = argparse.Namespace(
        id=args.task_id, agent=args.agent, role=role, base=sha,
        verify=_first_command(task), owns=list(owns),
        read_only=[p for p in (task.get("readOnly") or [])
                   if isinstance(p, str) and p.strip()],
        worktree=worktree, expiry=None, evidence_id=None,
        evidence_dir=tasks_mod.DEFAULT_EVIDENCE_DIR, cwd=args.cwd)
    code = tasks_mod.cmd_open(open_ns, exit_ok, exit_failed, exit_usage)
    if code != exit_ok:
        rm_code, _out, rm_err = _git(["worktree", "remove", "--force", worktree], root)
        cleanup = ("the worktree was removed again" if rm_code == 0
                   else "and the worktree at %s could not be removed either (%s)"
                        % (worktree, rm_err.strip() or "no message"))
        sys.stderr.write("sbe work start: the registry refused to open the record (its "
                         "reason is above); %s, and branch %s is left in place.\n"
                         % (cleanup, branch))
        return code

    # Rule 7: the contract, in front of the engineer before any edit.
    sys.stdout.write("sbe work start %s: branch %s at %s, worktree %s, registry record "
                     "open.\n" % (args.task_id, branch, sha[:12], worktree))
    sys.stdout.write("acceptance criteria:\n")
    for criterion in task.get("acceptance") or []:
        sys.stdout.write("  - %s\n" % criterion)
    sys.stdout.write("verification commands:\n")
    commands = [c for c in task.get("verificationCommands") or []
                if isinstance(c, str) and c.strip()]
    for cmd in commands:
        sys.stdout.write("  - %s\n" % cmd)
    if not commands:
        sys.stdout.write("  (none recorded on this task)\n")
    sys.stdout.write("dossier sources:\n")
    for src in task.get("dossierSources") or []:
        sys.stdout.write("  - %s\n" % src)
    return exit_ok


# ---------------------------------------------------------------------------
# check (read-only, never mutates)
# ---------------------------------------------------------------------------

def cmd_check(args, exit_ok, exit_failed, exit_usage):
    root = repo_root_of(os.path.abspath(args.cwd))
    data = load_registry(root)
    record = _find_record(data, args.task_id)
    if record is None:
        sys.stderr.write("sbe work check: no registry record with id %r in %s\n"
                         % (args.task_id, tasks_mod.registry_path(root)))
        return exit_usage

    reasons = []
    sys.stdout.write("sbe work check %s: owner %s, role %s, status %s\n"
                     % (args.task_id, record.get("agent", "(unnamed)"),
                        record.get("role", "(none)"), record.get("status", "(none)")))
    if record.get("forced"):
        forced = record["forced"]
        sys.stdout.write("  FORCED     this record was closed FORCED by %s (%s); a forced "
                         "close is never read as clean and never satisfies a dependency\n"
                         % (forced.get("who", "(unnamed)"),
                            forced.get("why", "(no reason)")))
    if record.get("overrideDirty"):
        sys.stdout.write("  OVERRIDE   dirty removal was overridden with reason: %s\n"
                         % record["overrideDirty"])

    worktree = record.get("worktree")
    if worktree:
        exists = os.path.isdir(worktree)
        sys.stdout.write("  worktree   %s (%s)\n"
                         % (worktree, "exists" if exists else "MISSING"))
        if exists:
            code, out, _err = _git(["symbolic-ref", "--short", "HEAD"], worktree)
            sys.stdout.write("  branch     %s\n"
                             % (out.strip() if code == 0 and out.strip()
                                else "(detached or unreadable in this worktree)"))
        else:
            reasons.append("the declared worktree %s does not exist" % worktree)
    else:
        sys.stdout.write("  worktree   none recorded; the shared tree is the task's "
                         "tree\n")

    try:
        result = tasks_mod.postcondition(root, record)
    except DiffUnavailable as exc:
        sys.stdout.write("  scope      NO-DATA: %s\n" % exc)
        reasons.append("the scope postcondition could not be computed, which is NO-DATA "
                       "and never a pass")
    else:
        for path in result["inScope"]:
            sys.stdout.write("  IN-SCOPE   %s\n" % path)
        for path in result["violations"]:
            flag = (" (declared READ-ONLY, was written)"
                    if path in result["readOnlyWrites"] else "")
            sys.stdout.write("  VIOLATION  %s%s\n" % (path, flag))
        for path in result["receiptViolations"]:
            sys.stdout.write("  RECEIPT-VIOLATION %s (a reviewer wrote under the evidence "
                             "store)\n" % path)
        if result["violations"] or result["receiptViolations"]:
            reasons.append("%d changed path(s) fall outside the declaration, named above"
                           % (len(result["violations"]) + len(result["receiptViolations"])))

    sys.stdout.write("  depends    NO-DATA: dependsOn edges live in the plan and check "
                     "takes no plan file, so dependency state is not examined here\n")

    verify_command = record.get("verifyCommand")
    if isinstance(verify_command, str) and verify_command.strip():
        tree = worktree if worktree and os.path.isdir(worktree) else root
        code, out, err = _git(["rev-parse", "HEAD"], tree)
        if code != 0 or not out.strip():
            sys.stdout.write("  evidence   NO-DATA: HEAD does not resolve in %s (%s), so "
                             "no receipt can be bound to a commit\n"
                             % (tree, err.strip() or "no output"))
            reasons.append("no commit exists to bind a verification receipt to")
        else:
            head = out.strip()
            scan = _matching_receipt(root, verify_command, head)
            for note in scan["unreadable"]:
                sys.stdout.write("  evidence   %s\n" % note)
            found = scan["match"]
            if found:
                sys.stdout.write("  evidence   receipt %s records a run of %r bound to "
                                 "commit %s\n" % (found["path"], verify_command, head[:12]))
            else:
                sys.stdout.write("  evidence   NO-DATA: no receipt in %s records a run of "
                                 "%r bound to commit %s\n"
                                 % (_evidence_dir(root), verify_command, head[:12]))
                reasons.append("the verification command %r has no receipt bound to the "
                               "current commit" % verify_command)
    else:
        sys.stdout.write("  evidence   NO-DATA: the record carries no verification "
                         "command, so no receipt can answer for it\n")
        reasons.append("no verification command is recorded, so nothing can be proven "
                       "about the work")

    if record.get("status") != "open":
        reasons.append("the record is not open (status %s), so there is nothing left to "
                       "close" % record.get("status"))

    if reasons:
        sys.stdout.write("NOT CLOSABLE: %s\n" % "; ".join(reasons))
        return exit_failed
    sys.stdout.write("CLOSABLE: scope kept and a receipt is bound to the current commit\n")
    return exit_ok


# ---------------------------------------------------------------------------
# finish
# ---------------------------------------------------------------------------

def cmd_finish(args, exit_ok, exit_failed, exit_usage):
    root = repo_root_of(os.path.abspath(args.cwd))
    data = load_registry(root)
    task = tasks_mod._find_open(data, args.task_id)
    if task is None:
        sys.stderr.write("sbe work finish: no OPEN task with id %r in %s\n"
                         % (args.task_id, tasks_mod.registry_path(root)))
        return exit_usage

    evidence_id = None
    if not args.force:
        # Rule 1: the registry postcondition, out-of-scope writes named.
        try:
            result = tasks_mod.postcondition(root, task)
        except DiffUnavailable as exc:
            sys.stdout.write("sbe work finish %s: NO-DATA. %s. NO-DATA is not a pass; the "
                             "task stays open.\n" % (args.task_id, exc))
            return exit_failed
        if result["violations"] or result["receiptViolations"]:
            for path in result["violations"]:
                sys.stdout.write("  VIOLATION  %s\n" % path)
            for path in result["receiptViolations"]:
                sys.stdout.write("  RECEIPT-VIOLATION %s\n" % path)
            sys.stdout.write("sbe work finish %s: FAIL. %d changed path(s) outside the "
                             "declaration, named above; closure is refused. Close with "
                             "--force --who --why to record a disposition, never to make "
                             "this clean.\n"
                             % (args.task_id,
                                len(result["violations"]) + len(result["receiptViolations"])))
            return exit_failed

        # Rule 2: a receipt bound to the worktree's current commit, or NO-DATA.
        verify_command = task.get("verifyCommand")
        if not (isinstance(verify_command, str) and verify_command.strip()):
            sys.stdout.write("sbe work finish %s: NO-DATA. The record carries no "
                             "verification command, so no receipt can answer for the work "
                             "and closure is refused.\n" % args.task_id)
            return exit_failed
        tree = task.get("worktree") or root
        code, out, err = _git(["rev-parse", "HEAD"], tree)
        if code != 0 or not out.strip():
            sys.stdout.write("sbe work finish %s: NO-DATA. HEAD does not resolve in %s "
                             "(%s), so no receipt can be bound to a commit and closure is "
                             "refused.\n" % (args.task_id, tree, err.strip() or "no output"))
            return exit_failed
        head = out.strip()
        scan = _matching_receipt(root, verify_command, head)
        for note in scan["unreadable"]:
            sys.stdout.write("  %s\n" % note)
        found = scan["match"]
        if found is None:
            sys.stdout.write("sbe work finish %s: NO-DATA. No receipt in %s records a run "
                             "of %r bound to commit %s. An agent SAYING it ran the command "
                             "is not evidence; absent evidence is NO-DATA, never a "
                             "FAIL-by-guess, and it still refuses closure. Generate one "
                             "with: sbe evidence run --out <receipt.json> --cwd %s -- %s\n"
                             % (args.task_id, _evidence_dir(root), verify_command,
                                head[:12], tree, verify_command))
            return exit_failed
        verdict = evidence_mod.verify(found["path"], cwd=tree)
        if verdict["verdict"] != "PASS":
            for reason in verdict["reasons"]:
                sys.stdout.write("  %s\n" % reason)
            sys.stdout.write("sbe work finish %s: %s. The receipt %s matches the command "
                             "and the commit but does not verify, for the reason(s) "
                             "above; closure is refused.\n"
                             % (args.task_id, verdict["verdict"], found["path"]))
            return exit_failed
        evidence_id = found["receipt"].get("runId")

    # Rules 3 and 4: close through the registry's own machinery, which reruns
    # the postcondition, closes clean on PASS, and marks --force closes FORCED
    # loudly with who and why recorded.
    code = tasks_mod.cmd_close(_close_namespace(args, args.force, evidence_id),
                               exit_ok, exit_failed, exit_usage)
    if code == exit_ok and not args.force:
        sys.stdout.write("sbe work finish %s: closed clean with receipt %s; the plan task "
                         "is complete by the single-source rule.\n"
                         % (args.task_id, evidence_id))
    return code


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------

def cmd_remove(args, exit_ok, exit_failed, exit_usage):
    root = repo_root_of(os.path.abspath(args.cwd))
    data = load_registry(root)
    record = _find_record(data, args.task_id)
    if record is None:
        sys.stderr.write("sbe work remove: no registry record with id %r in %s\n"
                         % (args.task_id, tasks_mod.registry_path(root)))
        return exit_usage
    if record.get("status") == "open":
        sys.stdout.write("sbe work remove: refused. Task %s is still OPEN, and an open "
                         "task's worktree is never removed; finish or force-close it "
                         "first.\n" % args.task_id)
        return exit_failed
    worktree = record.get("worktree")
    if not worktree:
        sys.stdout.write("sbe work remove %s: the record declares no worktree, so there "
                         "is nothing to remove.\n" % args.task_id)
        return exit_ok
    if not os.path.isdir(worktree):
        sys.stdout.write("sbe work remove %s: the worktree %s is already gone; nothing "
                         "was removed by this run.\n" % (args.task_id, worktree))
        return exit_ok

    code, out, err = _git(["status", "--porcelain=v1", "-uall"], worktree)
    if code != 0:
        sys.stdout.write("sbe work remove %s: NO-DATA. git status failed in %s (%s), so "
                         "whether the worktree is dirty is unknown and it is not "
                         "removed.\n" % (args.task_id, worktree, err.strip() or "no message"))
        return exit_failed
    dirty = [line for line in out.splitlines() if line.strip()]

    forced_removal = False
    if dirty:
        reason = (args.override_dirty or "").strip()
        if not reason:
            sys.stdout.write("sbe work remove %s: refused. The worktree %s carries %d "
                             "uncommitted path(s), and a dirty worktree is never deleted "
                             "silently. Rerun with --override-dirty <reason> to record the "
                             "human decision on the registry record.\n"
                             % (args.task_id, worktree, len(dirty)))
            return exit_failed
        # The override is recorded BEFORE the deletion, so the human decision
        # is permanent visible history even if the removal itself fails.
        record["overrideDirty"] = reason
        save_registry(root, data)
        forced_removal = True

    argv = ["worktree", "remove", "--force", worktree] if forced_removal \
        else ["worktree", "remove", worktree]
    code, _out, err = _git(argv, root)
    if code != 0:
        sys.stderr.write("sbe work remove %s: git could not remove the worktree %s: %s\n"
                         % (args.task_id, worktree, err.strip() or "no message"))
        return exit_failed
    sys.stdout.write("sbe work remove %s: worktree %s removed%s. The task branch is left "
                     "in place: branch deletion is not a git mutation this module is "
                     "allowed to perform.\n"
                     % (args.task_id, worktree,
                        ", override recorded on the registry record" if forced_removal
                        else ""))
    return exit_ok


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def _parser():
    parser = argparse.ArgumentParser(
        prog="sbe work",
        description="Isolated implementation for one plan task: a dedicated branch and "
                    "worktree at start, a diff-and-receipt gate at finish, and no "
                    "autonomous merge rights ever.")
    sub = parser.add_subparsers(dest="sub")

    st = sub.add_parser("start", help="validate the plan, then open branch, worktree and "
                                      "registry record for one task")
    st.add_argument("task_id")
    st.add_argument("--plan", required=True, help="path to the dossier's 08-plan.json")
    st.add_argument("--worktree-dir", default=None, dest="worktree_dir",
                    help="where the worktree directory is created (default: the "
                         "repository's parent directory)")
    st.add_argument("--agent", default="unnamed", help="who is doing the work")
    st.add_argument("--cwd", default=".")

    ck = sub.add_parser("check", help="report scope, evidence and closability; never "
                                      "mutates")
    ck.add_argument("task_id")
    ck.add_argument("--cwd", default=".")

    fi = sub.add_parser("finish", help="close the task on the postcondition AND a bound "
                                       "receipt")
    fi.add_argument("task_id")
    fi.add_argument("--force", action="store_true",
                    help="close anyway; the record is marked FORCED, never clean, and a "
                         "forced close never satisfies a dependency")
    fi.add_argument("--who", default=None, help="required with --force")
    fi.add_argument("--why", default=None, help="required with --force")
    fi.add_argument("--cwd", default=".")

    rm = sub.add_parser("remove", help="delete the worktree of a CLOSED task")
    rm.add_argument("task_id")
    rm.add_argument("--override-dirty", default=None, dest="override_dirty",
                    help="remove a dirty worktree anyway; the reason is recorded on the "
                         "registry record as permanent visible history")
    rm.add_argument("--cwd", default=".")
    return parser


def main(rest, exit_ok=0, exit_failed=1, exit_usage=2):
    """The `sbe work` surface. Exit codes come from the caller so this module
    never disagrees with the CLI's documented table."""
    parser = _parser()
    if not rest:
        parser.print_help(sys.stderr)
        return exit_usage
    try:
        args = parser.parse_args(list(rest))
    except SystemExit:
        return exit_usage
    handlers = {"start": cmd_start, "check": cmd_check, "finish": cmd_finish,
                "remove": cmd_remove}
    handler = handlers.get(getattr(args, "sub", None))
    if handler is None:
        parser.print_help(sys.stderr)
        return exit_usage
    try:
        return handler(args, exit_ok, exit_failed, exit_usage)
    except RegistryUnusable as exc:
        sys.stderr.write("sbe work: %s\n" % exc)
        return exit_usage
