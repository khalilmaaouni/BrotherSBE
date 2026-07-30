"""A structured registry of who owns what, and a diff postcondition at close
that compares what ACTUALLY changed against what was declared.

The defect this exists for, in one sentence: the write fence is a PreToolUse
hook that fails open and cannot govern Bash, because shell cannot be parsed
reliably, so a writer who edits through the shell walks past the only control
standing in front of the keyboard.

The fix is not a better parser. `sbe task open` records what a writer declared
it owns, and `sbe task close` reads the git diff and refuses to close a task
whose tree changed outside that declaration. The shell is never parsed; the
diff is simply read. This is the AFTER-THE-FACT layer of a two-layer model:
`tools/sbe_fence_hook.py` stays the advisory pre-write control and is not
touched by this module, and the overlap rule is IMPORTED from it rather than
re-typed, so the fence a hook refuses over and the fence this registry refuses
over cannot drift into two different fences.

WHAT THIS DOES NOT DO, stated here because a control that oversells itself is
worse than none:

  - It cannot see an actor who never registers. Reviewer separation and the
    ownership scan order roles INSIDE the registry; a writer who never runs
    `sbe task open` is invisible to both, and only the fence hook (advisory,
    fail-open) stands in front of that writer.
  - Concurrent writers of the REGISTRY FILE itself are out of scope. The
    rewrite is atomic (write temp, rename), so the file is never half-written,
    but two simultaneous `sbe task open` calls are last-write-wins. There is
    no lock and no daemon on purpose.
  - `expiry` is informational only. Nothing deletes a task on a clock; a stale
    open task is a line a human reads in `sbe task list`, never a record the
    tool silently drops.
  - The registry file `.sbe/tasks.json` is exempted, by exact name, from the
    changed-path comparison: opening a task writes it, so counting it would
    make an ordinary single-writer flow unable to close clean without --force,
    which is this control's own kill criterion.

Python floor is 3.9: no match statements, no `X | Y` annotations. Standard
library only. Maturity: INTERNAL-EVAL, exercised on this repository's fixtures
and on no other estate.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools")
if os.path.abspath(TOOLS) not in sys.path:
    sys.path.insert(0, os.path.abspath(TOOLS))
# The ONE overlap rule this project has, imported from the module that owns it.
# A private near-copy here is how the hook and the registry stop refusing over
# the same fence, and that failure would be silent.
from sbe_fence_hook import paths_overlap  # noqa: E402

#: Registry schema versions this module knows how to read. An unknown version
#: is refused rather than parsed hopefully, and NEVER silently reset: a
#: registry this module cannot read still records somebody's open fences.
KNOWN_REGISTRY_VERSIONS = ("1.0",)
REGISTRY_VERSION = "1.0"

#: The registry file, repo-relative, POSIX spelling. One file, no service.
REGISTRY_REL = ".sbe/tasks.json"

#: Where receipts live unless the caller says otherwise. A reviewer may not own
#: any path under this, and a reviewer whose diff touches it cannot close even
#: with --force: a reviewer who writes the receipts it reviews is the defect
#: reviewer separation exists to stop.
DEFAULT_EVIDENCE_DIR = ".sbe/evidence"

ROLES = ("writer", "reviewer")
STATUSES = ("open", "closed", "abandoned")

#: Every field a task record carries. Exactly these; "abandoned" is a legal
#: status value in the schema, and nothing in this wave writes it yet.
RECORD_FIELDS = ("id", "agent", "role", "worktree", "ownedPaths", "readOnlyPaths",
                 "baseCommit", "expiry", "status", "verifyCommand", "evidenceId",
                 "openedAt", "closedAt")

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class RegistryUnusable(Exception):
    """The registry cannot support a decision at all: not a git repository, a
    file that does not parse, or a schema version this module does not know.
    Raised rather than returning an empty registry, because an empty registry
    and an unreadable one look identical downstream and only one of them means
    nobody holds a fence."""


class DiffUnavailable(Exception):
    """The changed-path set could not be computed, so nothing was compared.
    NO-DATA, never a pass: a base commit that no longer resolves says nothing
    about scope having been kept."""


def _iso(epoch):
    """ISO 8601 in UTC, to the second, with an explicit Z, the same spelling
    the evidence receipts use."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _git(args, cwd):
    out = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True)
    return out.returncode, out.stdout, out.stderr


def repo_root_of(cwd):
    """The top level of the repository the command runs in, which is where the
    registry lives. A directory git cannot answer for is refused, never guessed
    at: a registry written outside any repository would govern nothing."""
    code, out, err = _git(["rev-parse", "--show-toplevel"], cwd)
    if code != 0 or not out.strip():
        raise RegistryUnusable("%s is not inside a git repository (%s); the registry "
                               "lives at the repository root and there is none here"
                               % (cwd, err.strip() or "no toplevel"))
    return out.strip()


def registry_path(root):
    return os.path.join(root, ".sbe", "tasks.json")


def load_registry(root):
    """The registry as a dict, or a fresh empty one when no file exists yet.

    A file that EXISTS and cannot be read is refused with the reason and is
    never reset: a corrupt registry still records somebody's open fences, and
    replacing it with a clean empty one would close every fence in it without
    anybody deciding to."""
    path = registry_path(root)
    if not os.path.exists(path):
        return {"schemaVersion": REGISTRY_VERSION, "tasks": []}
    try:
        with io.open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (ValueError, OSError) as exc:
        raise RegistryUnusable("%s does not parse (%s). Refusing, and NOT resetting it: "
                               "a corrupt registry still records somebody's open fences"
                               % (path, exc))
    if not isinstance(data, dict):
        raise RegistryUnusable("%s is not a JSON object; refusing rather than resetting"
                               % path)
    version = data.get("schemaVersion")
    if version not in KNOWN_REGISTRY_VERSIONS:
        raise RegistryUnusable("%s carries schema version %r and this tool reads %s; "
                               "refusing rather than parsing hopefully or resetting"
                               % (path, version, ", ".join(KNOWN_REGISTRY_VERSIONS)))
    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not all(isinstance(t, dict) for t in tasks):
        raise RegistryUnusable("%s: 'tasks' is not a list of records; refusing rather "
                               "than resetting" % path)
    for record in tasks:
        missing = [f for f in RECORD_FIELDS if f not in record]
        if missing:
            raise RegistryUnusable("%s: task %r is missing field(s) %s; refusing rather "
                                   "than guessing what they held"
                                   % (path, record.get("id", "(no id)"), ", ".join(missing)))
    return data


def save_registry(root, data):
    """Atomic rewrite: write a temp file in the same directory, then rename.
    The file is never half-written; two concurrent rewriters are last-write-
    wins, which is a stated limit, not a lock."""
    directory = os.path.join(root, ".sbe")
    if not os.path.isdir(directory):
        os.makedirs(directory)
    fd, tmp = tempfile.mkstemp(prefix="tasks.", suffix=".tmp", dir=directory)
    try:
        with io.open(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, registry_path(root))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def open_tasks(data):
    return [t for t in data["tasks"] if t.get("status") == "open"]


def claims_overlap(a, b, root):
    """True when two declared claims cover any common path, by the fence hook's
    own `paths_overlap` in both directions, because either claim may be the
    directory or glob that swallows the other."""
    return paths_overlap(a, b, root) or paths_overlap(b, a, root)


def _porcelain_paths(tree):
    """Changed paths from `git status --porcelain -uall`, a rename counting
    both sides. -uall lists untracked FILES rather than collapsing them to a
    directory entry, because a collapsed `dir/` would compare as a claim over
    the whole directory that nobody typed."""
    code, out, err = _git(["status", "--porcelain=v1", "-uall"], tree)
    if code != 0:
        raise DiffUnavailable("git status failed in %s: %s" % (tree, err.strip()))
    paths = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        rest = line[3:]
        for side in rest.split(" -> "):
            side = side.strip().strip('"')  # porcelain quotes unusual names
            if side:
                paths.append(side)
    return paths


def changed_paths(tree, base):
    """The union of `git diff --name-only <base>...HEAD` and the porcelain
    status: committed AND uncommitted edits count, and a rename counts both
    sides (--no-renames splits it into its delete and its add on purpose).
    The registry file itself is exempted by exact name; see the module
    docstring for why. A base that does not resolve raises, never passes."""
    code, _out, err = _git(["rev-parse", "--verify", "--quiet", base + "^{commit}"], tree)
    if code != 0:
        raise DiffUnavailable("base commit %s does not resolve in %s (%s); nothing was "
                              "compared" % (base, tree, err.strip() or "unknown ref"))
    code, out, err = _git(["diff", "--name-only", "--no-renames", "%s...HEAD" % base], tree)
    if code != 0:
        raise DiffUnavailable("git diff failed in %s: %s" % (tree, err.strip()))
    seen, ordered = set(), []
    for p in [f.strip().strip('"') for f in out.splitlines()] + _porcelain_paths(tree):
        if p and p != REGISTRY_REL and p not in seen:
            seen.add(p)
            ordered.append(p)
    return ordered


def postcondition(root, task, evidence_dir=DEFAULT_EVIDENCE_DIR):
    """The diff-against-declaration verdict for one task, as a dict.

    Every changed path outside the task's owned paths is a violation, listed by
    name. A changed path inside ownership prints as the evidence of scope kept.
    A declared read-only path that changed is a violation too, flagged as such:
    read-only means read. For a reviewer, any changed path under the evidence
    directory is a receipt violation, the one class `--force` may not waive.
    """
    tree = task.get("worktree") or root
    if task.get("worktree") and not os.path.isdir(tree):
        raise DiffUnavailable("declared worktree %s does not exist; nothing was compared"
                              % tree)
    changed = changed_paths(tree, task["baseCommit"])
    owned = task.get("ownedPaths") or []
    read_only = task.get("readOnlyPaths") or []
    in_scope, violations = [], []
    for p in changed:
        if any(paths_overlap(p, claim, tree) for claim in owned):
            in_scope.append(p)
        else:
            violations.append(p)
    read_only_writes = [p for p in violations
                        if any(paths_overlap(p, claim, tree) for claim in read_only)]
    receipt_violations = []
    if task.get("role") == "reviewer":
        receipt_violations = [p for p in changed if paths_overlap(p, evidence_dir, tree)]
    verdict = "FAIL" if (violations or receipt_violations) else "PASS"
    return {"verdict": verdict, "tree": tree, "changed": changed, "inScope": in_scope,
            "violations": violations, "readOnlyWrites": read_only_writes,
            "receiptViolations": receipt_violations}


def _find_open(data, task_id):
    for t in data["tasks"]:
        if t.get("id") == task_id and t.get("status") == "open":
            return t
    return None


def cmd_open(args, exit_ok, exit_failed, exit_usage):
    root = repo_root_of(os.path.abspath(args.cwd))
    data = load_registry(root)
    if not _SLUG_RE.match(args.id or ""):
        sys.stderr.write("sbe task open: %r is not a usable task id (letters, digits, "
                         "dot, dash, underscore)\n" % args.id)
        return exit_usage
    if args.role not in ROLES:
        sys.stderr.write("sbe task open: role must be one of %s, not %r\n"
                         % ("/".join(ROLES), args.role))
        return exit_usage
    if not _SHA_RE.match(args.base or ""):
        sys.stderr.write("sbe task open: --base must be a FULL 40-character commit sha, "
                         "not %r. A branch name means something different tomorrow, and a "
                         "postcondition against a moving base compares against nothing.\n"
                         % args.base)
        return exit_usage
    if _find_open(data, args.id):
        sys.stderr.write("sbe task open: refused. Task id %r already exists and is open; "
                         "close it or pick another id.\n" % args.id)
        return exit_usage
    owns = list(args.owns or [])
    for other in open_tasks(data):
        for mine in owns:
            for theirs in other.get("ownedPaths") or []:
                if claims_overlap(mine, theirs, root):
                    sys.stderr.write(
                        "sbe task open: refused. Owned path %r overlaps %r, owned by open "
                        "task %r (agent %s). One writer per file; queue behind it or "
                        "narrow the claim.\n"
                        % (mine, theirs, other["id"], other.get("agent", "(unnamed)")))
                    return exit_usage
    if args.role == "reviewer":
        for mine in owns:
            if claims_overlap(mine, args.evidence_dir, root):
                sys.stderr.write(
                    "sbe task open: refused. A reviewer task may not own %r: it overlaps "
                    "the evidence store %s it would review. A reviewer who writes the "
                    "receipts it reviews is the defect reviewer separation exists to "
                    "stop. This separates roles inside the registry only; it cannot stop "
                    "an actor who never registers.\n" % (mine, args.evidence_dir))
                return exit_usage
    record = {
        "id": args.id,
        "agent": args.agent,
        "role": args.role,
        "worktree": os.path.abspath(args.worktree) if args.worktree else None,
        "ownedPaths": owns,
        "readOnlyPaths": list(args.read_only or []),
        "baseCommit": args.base,
        "expiry": args.expiry,
        "status": "open",
        "verifyCommand": args.verify,
        "evidenceId": args.evidence_id,
        "openedAt": _iso(time.time()),
        "closedAt": None,
    }
    data["tasks"].append(record)
    save_registry(root, data)
    sys.stdout.write("sbe task open: %s is open. %s (%s) owns %d path(s): %s. Base %s. "
                     "Close runs the diff postcondition against exactly this "
                     "declaration.\n"
                     % (args.id, args.agent, args.role, len(owns),
                        ", ".join(owns) or "(none)", args.base[:12]))
    return exit_ok


def cmd_close(args, exit_ok, exit_failed, exit_usage):
    root = repo_root_of(os.path.abspath(args.cwd))
    data = load_registry(root)
    task = _find_open(data, args.id)
    if task is None:
        sys.stderr.write("sbe task close: no OPEN task with id %r in %s\n"
                         % (args.id, registry_path(root)))
        return exit_usage
    try:
        result = postcondition(root, task, evidence_dir=args.evidence_dir)
    except DiffUnavailable as exc:
        result = None
        sys.stdout.write("sbe task close %s: NO-DATA. %s. NO-DATA is not a pass; the "
                         "task stays open.\n" % (args.id, exc))
        if not args.force:
            return exit_failed
    if result is not None:
        for p in result["inScope"]:
            sys.stdout.write("  IN-SCOPE   %s\n" % p)
        for p in result["violations"]:
            flag = " (declared READ-ONLY, was written)" if p in result["readOnlyWrites"] \
                else ""
            sys.stdout.write("  VIOLATION  %s%s\n" % (p, flag))
        for p in result["receiptViolations"]:
            sys.stdout.write("  RECEIPT-VIOLATION %s (a reviewer wrote under the "
                             "evidence store)\n" % p)
        if result["receiptViolations"]:
            sys.stdout.write(
                "sbe task close %s: FAIL. A reviewer task's diff touches the evidence "
                "store, and --force may NOT waive this class: a reviewer who writes "
                "receipts is not reviewing them. The task stays open.\n" % args.id)
            return exit_failed
        if result["verdict"] == "PASS":
            task["status"] = "closed"
            task["closedAt"] = _iso(time.time())
            if args.evidence_id:
                task["evidenceId"] = args.evidence_id
            save_registry(root, data)
            sys.stdout.write("sbe task close %s: PASS. %d changed path(s), all inside "
                            "the declaration. Closed clean.\n"
                             % (args.id, len(result["changed"])))
            return exit_ok
        if not args.force:
            sys.stdout.write(
                "sbe task close %s: FAIL. %d changed path(s) outside the declaration, "
                "listed above by name. The shell was never parsed; the diff was read. "
                "The task stays open. Close with --force --who --why to record a "
                "disposition, never to make this clean.\n"
                % (args.id, len(result["violations"])))
            return exit_failed
    # --force from here: a recorded human decision, marked FORCED, never clean.
    if not (args.who or "").strip() or not (args.why or "").strip():
        sys.stderr.write("sbe task close: --force requires --who and --why. A forced "
                         "close with no author and no reason is an off switch, not a "
                         "decision.\n")
        return exit_usage
    task["status"] = "closed"
    task["closedAt"] = _iso(time.time())
    if args.evidence_id:
        task["evidenceId"] = args.evidence_id
    task["forced"] = {
        "who": args.who,
        "why": args.why,
        "at": _iso(time.time()),
        "verdict": result["verdict"] if result is not None else "NO-DATA",
        "violations": result["violations"] if result is not None else [],
    }
    save_registry(root, data)
    sys.stdout.write("sbe task close %s: FORCED by %s (%s). The record carries the "
                     "disposition and the violation list; this close is never read as "
                     "clean.\n" % (args.id, args.who, args.why))
    return exit_ok


def cmd_list(args, exit_ok, exit_failed, exit_usage):
    root = repo_root_of(os.path.abspath(args.cwd))
    data = load_registry(root)
    live = open_tasks(data)
    if args.json:
        sys.stdout.write(json.dumps({"schemaVersion": data["schemaVersion"],
                                     "openTasks": live}, indent=2, sort_keys=True) + "\n")
        return exit_ok
    if not live:
        sys.stdout.write("sbe task list: no open tasks in %s\n" % registry_path(root))
        return exit_ok
    for t in live:
        sys.stdout.write("%-20s %-10s %-8s base %s  owns: %s%s\n"
                         % (t["id"], t.get("agent", ""), t.get("role", ""),
                            (t.get("baseCommit") or "")[:12],
                            ", ".join(t.get("ownedPaths") or []) or "(none)",
                            ("  expiry " + t["expiry"]) if t.get("expiry") else ""))
    sys.stdout.write("%d open task(s). Expiry is informational: nothing here deletes on "
                     "a clock.\n" % len(live))
    return exit_ok


def _fence_field(value):
    """A record value made safe for a pipe-delimited fence line. A '|' inside a
    field would end the field early for every reader of the line."""
    return str(value).replace("|", "/")


def cmd_fence(args, exit_ok, exit_failed, exit_usage):
    """The markdown fence view, GENERATED from the JSON registry, one direction
    only. Printed to stdout for a human to paste into a STATE.md style
    registry; nothing in this wave reads markdown fences back into the
    registry, and the hand-written fence flow keeps working untouched."""
    root = repo_root_of(os.path.abspath(args.cwd))
    data = load_registry(root)
    lines = 0
    for t in open_tasks(data):
        owned = t.get("ownedPaths") or []
        if not owned:
            sys.stderr.write("sbe task fence: task %r owns no paths, so it renders no "
                             "fence line; a fence with no file scope fences nothing the "
                             "hook can compare against\n" % t["id"])
            continue
        sys.stdout.write(
            "- agent: %s (sole writer, task %s, role %s) | files: %s | base %s | "
            "check: %s |\n"
            % (_fence_field(t.get("agent", "(unnamed)")), _fence_field(t["id"]),
               _fence_field(t.get("role", "")),
               ", ".join(_fence_field(p) for p in owned),
               _fence_field((t.get("baseCommit") or "")[:12]),
               _fence_field(t.get("verifyCommand") or "(none)")))
        lines += 1
    if lines == 0:
        sys.stderr.write("sbe task fence: no open task renders a fence line\n")
    return exit_ok


def cmd_check(args, exit_ok, exit_failed, exit_usage):
    """The overlap scan across all open tasks, so a collision injected into the
    JSON by hand is caught the same way `open` would have caught it."""
    root = repo_root_of(os.path.abspath(args.cwd))
    data = load_registry(root)
    live = open_tasks(data)
    collisions = []
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            for pa in a.get("ownedPaths") or []:
                for pb in b.get("ownedPaths") or []:
                    if claims_overlap(pa, pb, root):
                        collisions.append((a["id"], pa, b["id"], pb))
    for a_id, pa, b_id, pb in collisions:
        sys.stdout.write("COLLISION: task %s owns %r and task %s owns %r; two open "
                         "writers overlap\n" % (a_id, pa, b_id, pb))
    if collisions:
        sys.stdout.write("sbe task check: FAIL, %d collision(s) among %d open task(s).\n"
                         % (len(collisions), len(live)))
        return exit_failed
    sys.stdout.write("sbe task check: no owned-path overlap among %d open task(s). This "
                     "scans the registry; it says nothing about writers who never "
                     "registered.\n" % len(live))
    return exit_ok


def _parser():
    parser = argparse.ArgumentParser(
        prog="sbe task",
        description="The write-scope registry: declare ownership at open, and close only "
                    "when the git diff stayed inside the declaration. After-the-fact by "
                    "design: the shell is never parsed, the diff is read.")
    sub = parser.add_subparsers(dest="sub")

    op = sub.add_parser("open", help="declare a task and the paths it owns")
    op.add_argument("--id", required=True, help="caller-supplied slug, unique among open "
                                                "tasks")
    op.add_argument("--agent", required=True, help="who is doing the work")
    op.add_argument("--role", required=True, help="writer or reviewer")
    op.add_argument("--base", required=True, help="FULL 40-char sha the diff will be "
                                                  "read from at close")
    op.add_argument("--verify", required=True, help="the command that will prove the "
                                                    "work, recorded with the task")
    op.add_argument("--owns", action="append", default=[],
                    help="a repo-relative path this task owns; repeatable")
    op.add_argument("--read-only", action="append", default=[], dest="read_only",
                    help="a repo-relative path this task reads but may not write; "
                         "repeatable")
    op.add_argument("--worktree", default=None,
                    help="absolute path of the task's own worktree; omitted means the "
                         "shared tree")
    op.add_argument("--expiry", default=None,
                    help="ISO date, informational only; nothing deletes on a clock")
    op.add_argument("--evidence-id", default=None, dest="evidence_id")
    op.add_argument("--evidence-dir", default=DEFAULT_EVIDENCE_DIR, dest="evidence_dir",
                    help="where receipts live, for the reviewer-separation refusal "
                         "(default %s)" % DEFAULT_EVIDENCE_DIR)
    op.add_argument("--cwd", default=".")

    cl = sub.add_parser("close", help="run the diff postcondition and close on PASS")
    cl.add_argument("id")
    cl.add_argument("--force", action="store_true",
                    help="close anyway, recording who and why; the close is marked "
                         "FORCED and is never read as clean")
    cl.add_argument("--who", default=None, help="required with --force")
    cl.add_argument("--why", default=None, help="required with --force")
    cl.add_argument("--evidence-id", default=None, dest="evidence_id",
                    help="attach the receipt id this close is backed by")
    cl.add_argument("--evidence-dir", default=DEFAULT_EVIDENCE_DIR, dest="evidence_dir")
    cl.add_argument("--cwd", default=".")

    ls = sub.add_parser("list", help="print open tasks")
    ls.add_argument("--json", action="store_true")
    ls.add_argument("--cwd", default=".")

    fe = sub.add_parser("fence", help="render the markdown fence view from the registry")
    fe.add_argument("--cwd", default=".")

    ck = sub.add_parser("check", help="re-run the overlap scan across all open tasks")
    ck.add_argument("--cwd", default=".")
    return parser


def main(rest, exit_ok=0, exit_failed=1, exit_usage=2):
    """The `sbe task` surface. Exit codes come from the caller so this module
    never disagrees with the CLI's documented table."""
    parser = _parser()
    if not rest:
        parser.print_help(sys.stderr)
        return exit_usage
    try:
        args = parser.parse_args(list(rest))
    except SystemExit as exc:
        # argparse already answered: -h/--help printed the usage the caller
        # asked for and raised 0, and help is not an error. Anything nonzero
        # is a refused flag or argument. Folding both into exit_usage made
        # every explicit help request on this surface exit 2.
        return exit_ok if exc.code in (0, None) else exit_usage
    handlers = {"open": cmd_open, "close": cmd_close, "list": cmd_list,
                "fence": cmd_fence, "check": cmd_check}
    handler = handlers.get(getattr(args, "sub", None))
    if handler is None:
        parser.print_help(sys.stderr)
        return exit_usage
    try:
        return handler(args, exit_ok, exit_failed, exit_usage)
    except RegistryUnusable as exc:
        sys.stderr.write("sbe task: %s\n" % exc)
        return exit_usage
