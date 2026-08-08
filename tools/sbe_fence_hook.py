#!/usr/bin/env python3
"""BrotherSBE PreToolUse fence hook: the point where L13, "one writer per file",
stops being a line in a markdown registry and becomes an enforcement boundary.

WHY THIS EXISTS
  L13 (references/laws-parallel-writers.md) says a fence line is written BEFORE
  the writer starts, names the exact files that writer may touch, and is closed
  only by appending its evidence. Until this file, nothing checked it at the
  moment of the write. `sbe_score.py` scores fence HYGIENE (is the line tagged,
  is the registry stale) and `sbe_telemetry.py fence-lint` prints live fences as
  a DISPATCH AID, but both of those run beside the work, never in front of it.
  L13 says so itself: "The rest of the fence discipline is human review, because
  nothing here computes it ... queueing rather than running in parallel when two
  writers overlap in file scope (no check compares scopes)". This file compares
  scopes, at the only moment where comparing them can still stop a collision.

  Claude Code's PreToolUse hook is the mechanism. It receives the tool name and
  its input as JSON on stdin and may return a deny decision that stops the call
  before the tool runs. The exact stdin fields this file reads and the exact deny
  object it emits are quoted in docs/HOOKS.md, which is the document to update if
  that contract moves.

THE THREE RULES THIS FILE OBEYS

  1. FAIL OPEN, LOUDLY. This hook sits in front of every edit the operator makes.
     A hook that failed closed on its own bug would brick editing entirely, so
     every failure path here (no registry configured, registry absent, registry
     unreadable, registry undecodable, a fence line with no readable file scope,
     an unimportable helper, an unparseable payload, no session_id, any
     unexpected exception) ALLOWS the write and prints the reason to stderr. A
     refusal from this file always means a real ownership conflict and never
     means this file is broken.

     This is a DELIBERATE DIVERGENCE from `sbe_score.check_fence_hygiene`, which
     FAILs over an unreadable registry because a broken record is not an absent
     one. That is right for a scorer, whose output is a verdict a human reads. It
     is wrong for a gate in front of the keyboard, whose output is a refusal that
     stops work. Same evidence, opposite safe direction, both stated.

  2. STDOUT IS THE DECISION CHANNEL AND NOTHING ELSE. Claude Code parses stdout
     as JSON. Every diagnostic goes to stderr. That is why this file has exactly
     two output funnels (_out, _warn) and no bare print anywhere.

  3. ONE PARSE, NEVER A SECOND COPY. The rule for what counts as a live fence,
     for stripping HTML comments, and for discovering registries behind a denied
     directory all come from the modules that already own them (`sbe_checks.py`,
     and the shape `sbe_score.py` and `sbe_telemetry.py` read). This file holds
     no private near-copy of any of them. When a shared helper cannot be
     imported, this hook FAILS OPEN and says so, rather than enforcing with a
     parse that might have drifted from the project's own. A second copy is how
     the fence the hook refuses over and the fence the operator wrote stop being
     the same fence, and that failure would be silent.

  Path handling follows from rule 3's spirit: every target path is realpath'd and
  expressed root-relative before comparison, because comparing unresolved strings
  is bypassed by '..', by a symlink, by a relative path typed from a
  subdirectory, or by case on a case-insensitive filesystem.

IDENTITY
  BrotherSBE's fence line names its writer in plain text: "(sole writer, session
  <id>)". That is not a weakness here and no token file is needed, because the
  session id this hook compares against is the one the HARNESS puts in the hook
  payload, not one the model types. A model cannot write its own session_id field
  into a PreToolUse payload, so reading the declared id out of STATE.md and
  claiming to be it buys nothing. The residual limit (a human who edits the
  registry can hand themselves any fence) is stated in docs/HOOKS.md, because a
  registry an operator owns is a registry an operator may rewrite, and that is
  the design, not a hole.

Python 3.9, standard library only, cross-platform, no network, no subprocess.
No em or en dashes anywhere in this file, its comments, or its output.
"""
import fnmatch
import json
import os
import posixpath
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Output funnels. Two of them, on purpose: stdout carries the decision JSON and
# nothing else, stderr carries every diagnostic. Anything written to stdout that
# is not the decision object corrupts the hook protocol. Deliberately not
# `print`: the honesty meta-test's report-print lint exists because interpolated
# print sites are a channel a value can climb through, and this file has no need
# of one.
# ---------------------------------------------------------------------------

def _out(s):
    sys.stdout.write(s)
    sys.stdout.flush()


def _warn(s):
    sys.stderr.write(s if s.endswith("\n") else s + "\n")
    sys.stderr.flush()


class OpenFail(Exception):
    """Raised anywhere a decision cannot be made SAFELY.

    Always caught at the top of decide(); always produces an ALLOW plus a stderr
    line naming the reason. A named exception rather than a returned sentinel, so
    a new code path cannot forget to check the sentinel and accidentally deny."""


# ---------------------------------------------------------------------------
# Shared helpers, loaded by path.
#
# tools/ is not a package and the hook is invoked by Claude Code with an
# arbitrary cwd, so a plain `import sbe_checks` would resolve against sys.path
# and could pick up a different checkout. Deferred into a function so an import
# failure is a FAIL-OPEN printed to stderr rather than a traceback that Claude
# Code would surface as a broken hook in front of every edit.
# ---------------------------------------------------------------------------

_CHECKS = None
_CHECKS_ERROR = None


def load_checks_module():
    """Import tools/sbe_checks.py beside this file, or return None and record
    why. Never raises: an unimportable helper is a fail-open condition, handled
    by require_checks_module() at the one place that needs it."""
    global _CHECKS, _CHECKS_ERROR
    if _CHECKS is not None or _CHECKS_ERROR is not None:
        return _CHECKS
    try:
        import importlib.util
        path = os.path.join(HERE, "sbe_checks.py")
        spec = importlib.util.spec_from_file_location("sbe_checks", path)
        if spec is None or spec.loader is None:
            _CHECKS_ERROR = "no import spec for %s" % path
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules.setdefault("sbe_checks", mod)
        _CHECKS = mod
        return _CHECKS
    except Exception as e:
        # Blanket by design: any import failure at all must degrade to fail-open,
        # and the reason travels with it rather than being swallowed.
        _CHECKS_ERROR = "%s: %s" % (type(e).__name__, e)
        return None


def require_checks_module():
    """The shared helpers, or OpenFail naming why they are missing.

    There is no local substitute on purpose (rule 3). Enforcing a fence with a
    private copy of the project's comment-stripping and glob-discovery rules
    would mean the hook could refuse over a fence shape the rest of BrotherSBE
    has stopped recognizing, and nothing would say so. Refusing to enforce, out
    loud, is the honest failure."""
    mod = load_checks_module()
    if mod is None:
        raise OpenFail(
            "tools/sbe_checks.py could not be imported (%s), and this hook holds "
            "no private copy of the project's registry-reading rules on purpose, "
            "so it cannot tell which fences exist" % _CHECKS_ERROR)
    return mod


# ---------------------------------------------------------------------------
# The tool surface this hook governs.
# ---------------------------------------------------------------------------

#: Tools that write a file through a structured, parseable path argument.
#:
#: Bash is DELIBERATELY ABSENT. A shell command can write any file, and no
#: reliable parse of arbitrary shell exists, so pretending to gate it would be a
#: guarantee this file cannot keep. It is stated as a known gap in docs/HOOKS.md
#: rather than papered over here. The skill's own sentence about this hook says
#: it does not gate Bash, and that sentence stays true because of this line.
WRITE_TOOLS = frozenset((
    "Edit",
    "Write",
    "MultiEdit",
    "NotebookEdit",
    "CreateDirectory",
    "Delete",
))

#: Keys inside tool_input that carry a filesystem path, collected across the
#: built-in write tools. Unknown keys are ignored; a write tool that carries none
#: of these produces zero targets, which is a FAIL-OPEN (see decide) and never a
#: silent allow.
PATH_KEYS = ("file_path", "notebook_path", "path", "filePath", "target_file")

#: The environment variable BrotherSBE already uses to name its fence registries
#: (tools/sbe_score.py, tools/sbe_telemetry.py fence-lint, docs/SETUP.md).
#: Colon-separated glob patterns. One name, read the same way in all three.
REGISTRIES_ENV = "BROTHERSBE_REGISTRIES"

#: The per-project registry every BrotherSBE project carries, named in SKILL.md
#: step 5 and shipped as STATE.template.md.
PROJECT_REGISTRY = "STATE.md"

#: Escape hatch for a session that has deliberately decided to write across a
#: fence and does not want to edit the registry first. Set it and the hook says
#: so on stderr on every write, so the bypass is never silent.
DISABLE_ENV = "BROTHERSBE_FENCE_HOOK_OFF"

#: Overrides the session identity this hook compares against, for a manual run
#: or a test. Never invents one: an invented id would own nothing and would deny
#: the operator out of their own work.
SESSION_ENV = "BROTHERSBE_FENCE_SESSION"

#: The shortest declared session token this hook will treat as an identity. A
#: one or two character token would prefix-match half the UUIDs on the machine
#: and hand a fence to the wrong session.
MIN_SESSION_TOKEN = 4


# ---------------------------------------------------------------------------
# Registry parsing. The shape is BrotherSBE's own, read from STATE.template.md
# and enforced by L13, NOT the sibling project's SQLite claims table.
#
#   - agent: <id> (sole writer, session <id>) | tier T1 | TTL <date> |
#     objective: ... | files: a.py, b.py | output: ... | boundaries: ... |
#     termination: ... | check: ... |
#
# and a fence is CLOSED by appending LANDED or ADOPTED to it.
# ---------------------------------------------------------------------------

def is_live_fence(s):
    """A live fence line, by BrotherSBE's own rule.

    The rule is `sbe_score._is_live_fence`, which is the BROADER of the two
    parses this project ships: it accepts both markdown bullets, while the two
    copies inside `sbe_telemetry.py` accept only `- `. The broader one is the
    right one to enforce with, because the narrow parse misses a real fence
    written with an asterisk bullet, and a missed fence is an unprotected file.
    The divergence inside BrotherSBE is real and is recorded in docs/HOOKS.md.

    Read off the owning module rather than re-typed, so the rule cannot drift
    into a second spelling here."""
    if not isinstance(s, str):
        return False
    return live_fence_rule()(s.strip())


_LIVE_FENCE_FN = None


def live_fence_rule():
    """`sbe_score._is_live_fence`, loaded by path exactly once.

    sbe_score.py reads BROTHERSBE_REGISTRIES at import time to build its own
    module-level REGISTRIES list, which is harmless (this hook never reads that
    list) but is why the import is deferred and cached rather than done at the
    top of the file: it must happen after the environment is settled."""
    global _LIVE_FENCE_FN
    if _LIVE_FENCE_FN is not None:
        return _LIVE_FENCE_FN
    try:
        import importlib.util
        path = os.path.join(HERE, "sbe_score.py")
        spec = importlib.util.spec_from_file_location("sbe_score_for_fence", path)
        if spec is None or spec.loader is None:
            raise ImportError("no import spec for %s" % path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, "_is_live_fence", None)
        if not callable(fn):
            raise ImportError("sbe_score.py defines no _is_live_fence")
        _LIVE_FENCE_FN = fn
        return fn
    except Exception as e:
        raise OpenFail(
            "the live-fence rule could not be read from tools/sbe_score.py (%s: "
            "%s), and this hook holds no private copy of it on purpose, so it "
            "cannot tell which fence lines are still open"
            % (type(e).__name__, e))


def bullet_items(text):
    """The rendered registry text as whole markdown bullets, one string each.

    THIS IS THE ONE PLACE THIS HOOK READS MORE THAN THE PROJECT'S OWN CHECKS DO,
    and it is forced by the shape STATE.template.md actually ships. A fence there
    is a markdown bullet that CONTINUES onto indented lines:

        - agent: <id> (sole writer, session <id>) | tier T1 | TTL <date> |
          objective: ... |
          files: src/parser.py, tests/test_parser.py |
          ...
          LANDED 2026-01-15, evidence (verbatim, run after last edit):

    `sbe_score._is_live_fence` and `sbe_telemetry`'s two copies are applied to
    ONE STRIPPED LINE at a time. That works for what they measure, because the
    tier tag sits on the first line. It cannot work here: `files:` is on the
    third line and `LANDED` on the last, so a line-wise reader would find no file
    scope on any fence written the way the template writes them, and would find a
    closed fence still open. Both were observed against the shipped template.

    So the LIVENESS RULE is still the project's own, unmodified and imported
    rather than re-typed; only the UNIT it is applied to is the whole bullet
    instead of its first line. The consequence for the reader is stated in
    docs/HOOKS.md: a fence closed with LANDED on a continuation line is CLOSED to
    this hook and still reads as live to `sbe_score`, which is a hygiene false
    alarm in the scorer and never an unenforced fence here.

    A continuation is an indented, non-blank line that does not itself start a
    new bullet. A blank line ends the item, which is ordinary markdown."""
    items = []
    current = None
    for raw in (text or "").splitlines():
        stripped = raw.strip()
        starts_bullet = stripped.startswith(("- ", "* "))
        indented = raw[:1] in (" ", "\t")
        if starts_bullet and not (indented and current is not None):
            if current is not None:
                items.append(current)
            current = stripped
        elif current is not None and stripped and indented:
            current += " " + stripped
        else:
            if current is not None:
                items.append(current)
            current = None
    if current is not None:
        items.append(current)
    return items


#: `files: <scope> |` inside a pipe-delimited fence line, or to end of line when
#: the author left the trailing pipe off. Case-insensitive because a registry is
#: hand-written prose and "Files:" is the same declaration.
_FILES_FIELD = re.compile(r"\bfiles\s*:\s*(.*?)(?:\||$)", re.I)

#: `session <id>` as STATE.template.md writes it, and `session: <id>` because
#: that is how an operator writes it half the time. The id runs to the next
#: separator: a closing paren, a pipe, a comma, or whitespace.
_SESSION_FIELD = re.compile(r"\bsession\s*:?\s*([^\s|,()]+)", re.I)

#: `agent: <id>`, for naming the owner in the refusal.
_AGENT_FIELD = re.compile(r"\bagent\s*:?\s*([^|(]+)", re.I)


def fence_files(line):
    """The declared file scope of a fence line, as a list of raw patterns, or
    None when the line declares no readable scope.

    None is load-bearing and is NOT an empty list: a fence with no `files:` field
    fences nothing this hook can compare against, so the caller fails OPEN and
    names the line, rather than treating "no scope" as "no conflict" in silence.
    """
    m = _FILES_FIELD.search(line)
    if not m:
        return None
    raw = m.group(1).strip()
    if not raw:
        return None
    parts = [p.strip().strip("`'\"") for p in re.split(r"[,;]", raw)]
    parts = [p for p in parts if p]
    return parts or None


def fence_session(line):
    """The session id a fence line declares as its sole writer, or "" when it
    declares none. An undeclared owner is not this session, and the caller treats
    an unowned live fence as a genuine conflict, because L13's rule is one writer
    per file and a fence whose writer is anonymous is still a fence somebody else
    opened."""
    m = _SESSION_FIELD.search(line)
    if not m:
        return ""
    return m.group(1).strip().strip("`'\".,;)")


def fence_agent(line):
    """The agent id a fence line names, for the refusal message. Best effort: the
    message degrades, the refusal never does."""
    m = _AGENT_FIELD.search(line)
    if not m:
        return "(unnamed agent)"
    return m.group(1).strip().strip("`'\".,;") or "(unnamed agent)"


def same_session(declared, mine):
    """True when a fence line's declared session is this session.

    Prefix matching in BOTH directions, because a registry is hand-written: an
    operator abbreviates a UUID to its first eight characters as often as they
    paste the whole thing. The floor (MIN_SESSION_TOKEN) stops a one-character
    token from matching everything. Matching generously is the safe direction
    here: a false MATCH allows the write, which is this file's fail-open bias,
    while a false MISS would refuse the rightful owner out of their own fence."""
    if not declared or not mine:
        return False
    d = declared.strip().lower()
    m = mine.strip().lower()
    if len(d) < MIN_SESSION_TOKEN or len(m) < MIN_SESSION_TOKEN:
        return d == m
    return d == m or d.startswith(m) or m.startswith(d)


# ---------------------------------------------------------------------------
# Path canonicalization and scope comparison.
# ---------------------------------------------------------------------------

def canonical_target(root, raw, cwd=None):
    """A tool's target path as a root-relative POSIX string, symlinks resolved,
    or None when it falls outside the project root.

    os.path.realpath resolves symlinks in whatever prefix of the path already
    exists and leaves a nonexistent trailing component literal, so this behaves
    identically for Edit on an existing file and Write creating a new one.

    None means "not this project's business" (a different drive, a path above the
    root, an unusable string) and every caller treats that as allow: BrotherSBE
    fences a project, not the filesystem."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    root_real = os.path.realpath(root)
    base_dir = cwd if cwd else root_real
    try:
        base = raw if os.path.isabs(raw) else os.path.join(base_dir, raw)
        abs_real = os.path.realpath(base)
        rel = os.path.relpath(abs_real, root_real)
    except (ValueError, OSError):
        # Windows raises ValueError from relpath across drives, which is
        # definitionally outside the root.
        return None
    rel_posix = rel.replace(os.sep, "/")
    if rel_posix == ".." or rel_posix.startswith("../"):
        return None
    return posixpath.normpath(rel_posix)


def normalize_claim(pattern):
    """A declared fence path as a root-relative POSIX pattern.

    Not realpath'd: a claim may name a file that does not exist yet, and it may
    carry a wildcard, both of which realpath would mangle. Only the separators, a
    leading './', and a trailing '/' are normalized."""
    p = (pattern or "").strip().replace(os.sep, "/")
    while p.startswith("./"):
        p = p[2:]
    p = p.rstrip("/")
    if not p:
        return ""
    return posixpath.normpath(p)


def _spelling_overlap(t, c):
    """The three exact-spelling overlap rules, factored out so the case-folded
    retry in `paths_overlap` can run the identical logic on lowered strings
    instead of drifting out of sync with it."""
    if t == c:
        return True
    if t.startswith(c + "/"):
        return True
    if c.startswith(t + "/"):
        # The claim is deeper than the target: writing the parent DIRECTORY of a
        # claimed file touches the claim. Only a directory-shaped target reaches
        # this, and Delete and CreateDirectory are exactly that.
        return True
    if any(ch in c for ch in "*?["):
        if fnmatch.fnmatch(t, c) and ("**" in c or c.count("/") == t.count("/")):
            return True
    return False


def _case_insensitive_probe(path):
    """Does swapping the case of this existing path's own name still find it?

    Case (in)sensitivity is a property of the volume a path lives on, not of
    any one file on it, so probing one real entry answers the question for
    every path beneath the same mount. `path` must exist; the probe reads the
    filesystem and writes nothing. Returns False on anything it cannot
    confirm, which is this hook's fail-open bias applied to the probe itself:
    an inconclusive probe must not manufacture a deny that was not there
    before this fix.
    """
    try:
        parent, name = os.path.split(os.path.realpath(path))
        swapped = name.swapcase()
        if not name or swapped == name:
            # Nothing alphabetic to flip (a name of digits or symbols): this
            # entry cannot answer the question, so it is not asked.
            return False
        candidate = os.path.join(parent, swapped)
        return os.path.exists(candidate) and os.path.samefile(path, candidate)
    except OSError:
        return False


def _same_entry_case_insensitive(root, t, c):
    """True only when the two case-variant spellings `t` and `c` name ONE
    filesystem entry, confirmed rather than assumed.

    When both spellings exist on disk already, `os.path.samefile` over their
    real paths is definitive: matching inodes mean one file no matter what the
    strings say, which is the same proof
    `test_a_case_variant_of_a_fenced_path_is_allowed_which_is_a_limit` uses on
    itself before it trusts the fixture. When one or both do not exist yet (a
    Write about to create the target, or a fence naming a file nobody wrote),
    there is nothing to samefile, so `root` itself is probed instead: if this
    project's own volume folds case on lookup, every path under it does too."""
    full_t = os.path.join(root, t.replace("/", os.sep))
    full_c = os.path.join(root, c.replace("/", os.sep))
    try:
        if os.path.exists(full_t) and os.path.exists(full_c):
            return os.path.samefile(full_t, full_c)
    except OSError:
        return False
    return _case_insensitive_probe(root)


def paths_overlap(target, claim, root=None):
    """True when a concrete root-relative target falls inside a declared claim.

    Three ways a claim covers a target, all of them ordinary in a hand-written
    registry: the same path, a directory prefix ("tools/" covers
    "tools/sbe_gate.py"), and a glob ("docs/*.md" covers "docs/SETUP.md").
    fnmatch handles the glob case with an explicit separator guard, because
    fnmatch's '*' happily crosses '/' and a claim of "docs/*" must not silently
    swallow "docs/guides/01-quickstart.md" that its author never named.

    CASE. The exact-spelling comparison above used to be the only one, so on a
    case-insensitive filesystem (the macOS default) a fence written for
    "docs/SETUP.md" let a second writer land on "docs/setup.md": one file, two
    spellings, and only one of them was compared. When the exact comparison
    misses, this retries case-folded, but a case-folded MATCH is never trusted
    on its own, because two honestly different files named "a.md" and "A.md"
    on a case-sensitive filesystem (the Linux default) must not false-conflict.
    `root` is what makes the retry a confirmation rather than a guess: without
    it (a caller that has no filesystem to ask) the fold is skipped and the
    exact-spelling answer stands, which is this hook's fail-open bias again."""
    t = normalize_claim(target)
    c = normalize_claim(claim)
    if not t or not c:
        return False
    if _spelling_overlap(t, c):
        return True
    if root and _spelling_overlap(t.lower(), c.lower()) and _same_entry_case_insensitive(
            root, t, c):
        return True
    return False


# ---------------------------------------------------------------------------
# Reading the registries.
# ---------------------------------------------------------------------------

class Fence(object):
    """One live fence line, with everything the decision and the refusal need."""

    def __init__(self, registry, line, files, session, agent):
        self.registry = registry
        self.line = line
        self.files = files
        self.session = session
        self.agent = agent


def registry_patterns(cwd, root=None):
    """Every glob pattern that names a fence registry, in the order the rest of
    the project reads them: the project's own STATE.md first, then whatever
    BROTHERSBE_REGISTRIES declares. Mirrors `sbe_telemetry.cmd_fence_lint`, so
    the fences this hook enforces are the fences fence-lint printed to the
    operator before dispatch.

    The one addition to fence-lint's list is the PROJECT ROOT's STATE.md when it
    differs from cwd's. fence-lint is run by a human standing in the project
    root; this hook is fired by the harness on whatever cwd the session happens
    to hold, and an Edit issued from a subdirectory would otherwise find no
    registry and fail open past a fence sitting one level up. A missed registry
    is an unprotected file, so both are searched and duplicates collapse."""
    pats = [os.path.join(cwd, PROJECT_REGISTRY)]
    if root and os.path.realpath(root) != os.path.realpath(cwd):
        pats.append(os.path.join(root, PROJECT_REGISTRY))
    # SPLIT ON THE PLATFORM'S LIST SEPARATOR, NOT ON A LITERAL COLON. A Windows
    # path begins with a drive letter and a colon, so splitting `C:\work\STATE.md`
    # on ":" yields "C" and "\work\STATE.md" and the registry is never found.
    # The consequence was not a crash: the hook found no fence and ALLOWED the
    # write, so on Windows the one-writer-per-file boundary silently did not
    # bind for any registry named this way. `tools/sbe_score.py:42` already had
    # this right, which makes this drift from an existing correct pattern rather
    # than an open question, and the three tools that read this variable have to
    # agree or they disagree about what is fenced.
    pats += [p.strip() for p in os.environ.get(REGISTRIES_ENV, "").split(os.pathsep)
             if p.strip()]
    seen, out = set(), []
    for p in pats:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


class FenceSet(object):
    """Every live fence this hook could read, plus what it could not.

    Deliberately an object and not a (fences, notes) 2-tuple, for the same reason
    Decision is: this project's honesty meta-test reads a 2-tuple return as a
    possible verdict source, and neither of those things is a check verdict.
    Keeping the shapes distinct keeps that lint honest rather than buying an
    allowlist entry for a function it was never meant to cover."""

    def __init__(self, fences, notes):
        self.fences = fences
        self.notes = notes


def read_fences(cwd, root=None):
    """A FenceSet across every configured registry.

    Raises OpenFail when the registries cannot support a decision at all. The
    notes carry the per-line problems that do not by themselves stop a decision
    but that the operator has to know about, because a fence this hook could not
    read is a fence it cannot enforce."""
    checks = require_checks_module()
    fences, notes, opened, unreadable, denied_dirs = [], [], 0, [], []
    for pat in registry_patterns(cwd, root):
        # glob.glob returns FEWER paths, not an error, over a directory it cannot
        # enter, so discovery has to account for what it could not see. Same
        # shared helper, same denial axis, as the scorer and fence-lint.
        hits, denied = checks.glob_with_denials(pat)
        denied_dirs.extend(denied)
        for p in sorted(hits):
            if not os.path.isfile(p):
                # A directory, a FIFO, a socket: present and not a registry.
                # Named, never skipped in silence.
                if os.path.lexists(p):
                    unreadable.append("%s (not a regular file)" % p)
                continue
            try:
                with open(p, "rb") as f:
                    raw = f.read()
            except OSError as e:
                unreadable.append("%s (%s)" % (p, type(e).__name__))
                continue
            # errors="replace" so an undecodable registry degrades to garbled
            # text rather than to an exception. A registry that decodes to
            # garbage produces zero recognizable fence lines, which is the
            # corrupt-registry fail-open below, and it is reported as such.
            text = raw.decode("utf-8", "replace")
            opened += 1
            # Rendered, not raw: a fence line inside an HTML comment is invisible
            # to the reader of the registry, so it is invisible here too. Same
            # rule, same shared helper, as every other reader in this project.
            for s in bullet_items(checks.without_comments(text)):
                if not is_live_fence(s):
                    continue
                files = fence_files(s)
                if files is None:
                    notes.append(
                        "sbe_fence_hook: %s carries a live fence line with no readable "
                        "`files:` scope, so this hook cannot tell what it owns and did "
                        "NOT enforce it. Line: %s" % (p, s[:160]))
                    continue
                fences.append(Fence(p, s, files, fence_session(s), fence_agent(s)))
    if denied_dirs:
        # Before every other verdict, because a denied parent directory is
        # exactly how a configured registry set silently becomes smaller: the
        # files inside it never entered discovery at all, so a decision over the
        # rest would read as covering them.
        raise OpenFail(
            "%d director(y/ies) named by %s exist and cannot be entered (%s); the "
            "registry files inside never entered discovery, so any fence in them "
            "is invisible here"
            % (len(denied_dirs), REGISTRIES_ENV,
               ", ".join(sorted(set(denied_dirs))[:4])))
    if unreadable:
        raise OpenFail(
            "%d registry path(s) exist and could not be read (%s); a fence this "
            "hook cannot open is a fence it cannot enforce, and refusing on the "
            "strength of the registries it COULD read would read as covering them"
            % (len(unreadable), ", ".join(sorted(unreadable)[:4])))
    if not opened:
        raise OpenFail(
            "no fence registry was opened under %s; set %s to colon-separated "
            "glob patterns, or put a STATE.md carrying a fence registry at the "
            "project root (see STATE.template.md)" % (cwd, REGISTRIES_ENV))
    if not fences:
        # The notes ride along in the message, not just in the return value. A
        # registry whose only fence had no readable `files:` scope produces zero
        # fences AND the one note that explains why, and raising past that note
        # would print "none of them carries a live fence line" over a fence line
        # sitting right there in the file: the precise shape of a verdict
        # asserting something the tool never examined.
        raise OpenFail(
            "%d registry file(s) opened under %s and none of them carries a live "
            "fence line this hook could read, so there is no fence to enforce%s"
            % (opened, cwd,
               (". Unenforceable fence line(s) found: " + " ".join(notes))
               if notes else ""))
    return FenceSet(fences, notes)


# ---------------------------------------------------------------------------
# The decision.
# ---------------------------------------------------------------------------

def deny_payload(reason):
    """The deny object, shaped exactly as the PreToolUse contract requires:

      {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                              "permissionDecision": "deny",
                              "permissionDecisionReason": "..."}}

    Emitted on stdout with exit code 0. Exit 2 would also block, feeding stderr
    back as the reason, but it is the wrong instrument here: exit 2 means "the
    hook itself failed", and every failure THIS hook has is a fail-open."""
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}


def refusal_reason(target, fence, my_session):
    """The refusal, which must name the fence that owns the file AND an escape
    that actually works.

    All three escapes below are BrotherSBE's own declared mechanisms, not
    inventions of this file:
      1. L13: "queueing rather than running in parallel when two writers overlap
         in file scope". Report the change to the owner and let them write it.
      2. STATE.template.md: "Close a fence only by appending its evidence block:
         the exact command run and its last lines." A closed fence releases the
         path, and this hook stops refusing the moment LANDED appears on the
         line. That is the escape the test fixture demonstrates end to end.
      3. ADOPTED, the other closing marker both of this project's parsers already
         honour, for a deliberate takeover: mark the line ADOPTED and open a new
         fence naming this session as sole writer.
    """
    owner = fence.session or "(no session declared on the fence line)"
    return (
        "BrotherSBE fence (L13, one writer per file): %s is inside the file scope "
        "of a LIVE fence in %s, opened by agent %s as sole writer for session %s. "
        "This session is %s, so it is not the writer for that path.\n"
        "The fence line, verbatim:\n"
        "  %s\n"
        "Do not write across a fence. Any of these releases it, and nothing else "
        "does:\n"
        "  1. Report the change to the fence owner and let that writer make it. "
        "L13 says overlapping writers queue, they do not run in parallel.\n"
        "  2. If that work is finished, CLOSE the fence where it lives, in %s, by "
        "appending its evidence block to that line: the marker LANDED, the exact "
        "command run, and its last lines. This hook stops refusing %s the moment "
        "that line reads LANDED.\n"
        "  3. To take the fence over deliberately, append ADOPTED to that line and "
        "write a new fence line naming this session (%s) as sole writer, before "
        "you edit anything."
        % (target, fence.registry, fence.agent, owner, my_session,
           fence.line[:400], fence.registry, target, my_session))


def extract_targets(tool_input):
    """Every path a write tool's input names, in input order, de-duplicated.

    Walks nested lists of dicts too, so a MultiEdit-shaped payload whose per-edit
    entries carry their own file_path is not silently reduced to the top-level
    path. Bounded depth and width: a hook that recursed without limit on a
    hostile payload would hang in front of every edit."""
    out, seen = [], set()

    def visit(node, depth):
        if depth > 6:
            return
        if isinstance(node, dict):
            for k in PATH_KEYS:
                v = node.get(k)
                if isinstance(v, str) and v.strip() and v not in seen:
                    seen.add(v)
                    out.append(v)
            for v in node.values():
                if isinstance(v, (dict, list)):
                    visit(v, depth + 1)
        elif isinstance(node, list):
            for v in node[:64]:
                visit(v, depth + 1)

    visit(tool_input, 0)
    return out


class Decision(object):
    """The hook's answer.

    Deliberately an object and not a (verdict, evidence) 2-tuple: this project's
    honesty meta-test reads a 2-tuple return as a possible verdict source, and
    this file produces a permission decision, which is a different thing from a
    check verdict. Keeping the shapes distinct keeps that lint honest rather than
    buying an allowlist entry for a function it was never meant to cover.

    `payload` is None for ALLOW and for FAIL-OPEN, deliberately the same value,
    so no failure path can produce a deny by accident."""

    def __init__(self, payload, notes):
        self.payload = payload
        self.notes = notes


def decide(payload):
    """Return a Decision. `payload` is the parsed PreToolUse hook JSON."""
    notes = []
    try:
        if not isinstance(payload, dict):
            raise OpenFail("hook payload was not a JSON object")
        tool_name = payload.get("tool_name")
        if not isinstance(tool_name, str) or tool_name not in WRITE_TOOLS:
            # Not a file-writing tool. Silent, not loud: this is the common case
            # (every Read, Grep, Bash and TodoWrite lands here) and a stderr line
            # per call would be noise the operator learns to ignore. Bash is here
            # by design, not by omission: see WRITE_TOOLS.
            return Decision(None, [])
        if os.environ.get(DISABLE_ENV, "").strip() not in ("", "0"):
            return Decision(None, [
                "sbe_fence_hook: %s is set, so the fence was NOT checked and this "
                "write is allowed. Unset it to restore L13 enforcement."
                % DISABLE_ENV])

        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            raise OpenFail("tool_input for %s was not a JSON object" % tool_name)

        raw_targets = extract_targets(tool_input)
        if not raw_targets:
            raise OpenFail(
                "no target path found in tool_input for %s (keys present: %s)"
                % (tool_name,
                   ", ".join(sorted(str(k) for k in tool_input)) or "none"))

        my_session = os.environ.get(SESSION_ENV, "").strip()
        if not my_session:
            sid = payload.get("session_id")
            my_session = sid.strip() if isinstance(sid, str) else ""
        if not my_session:
            raise OpenFail(
                "the hook payload carried no session_id and %s is unset, so this "
                "session has no identity to compare against a fence line's "
                "declared writer" % SESSION_ENV)

        cwd = payload.get("cwd")
        cwd = cwd.strip() if isinstance(cwd, str) and cwd.strip() else os.getcwd()
        root = payload.get("project_dir")
        root = root.strip() if isinstance(root, str) and root.strip() else cwd

        found = read_fences(cwd, root)
        notes.extend(found.notes)

        for raw in raw_targets:
            rel = canonical_target(root, raw, cwd)
            if rel is None:
                # Outside the project root. BrotherSBE fences a project, not the
                # machine.
                continue
            for fence in found.fences:
                if same_session(fence.session, my_session):
                    continue
                if any(paths_overlap(rel, claim, root) for claim in fence.files):
                    return Decision(
                        deny_payload(refusal_reason(rel, fence, my_session)), notes)
        return Decision(None, notes)
    except OpenFail as e:
        notes.append(
            "sbe_fence_hook: FAILING OPEN, the write is allowed and the fence was "
            "NOT checked. Reason: %s" % e)
        return Decision(None, notes)
    except Exception as e:
        # The blanket catch is the point, not laziness: an unforeseen bug in this
        # file must never become a refusal in front of the operator's editing.
        # Type and message, no traceback, so the stderr line stays one readable
        # sentence and the failure is still named rather than swallowed.
        notes.append(
            "sbe_fence_hook: FAILING OPEN after an unexpected error, the write is "
            "allowed and the fence was NOT checked. Reason: %s: %s"
            % (type(e).__name__, e))
        return Decision(None, notes)


# ---------------------------------------------------------------------------
# Entry points.
# ---------------------------------------------------------------------------

class StdinPayload(object):
    """The parsed hook payload, or the reason there is none.

    An object rather than a (payload, error) pair, for the reason stated on
    Decision and FenceSet: a 2-tuple return in this project reads as a possible
    check verdict, and this is a parse result."""

    def __init__(self, payload, error):
        self.payload = payload
        self.error = error


def read_stdin_json():
    """A StdinPayload. Never raises: unreadable stdin is a fail-open, not a
    crash in front of the operator's editing."""
    try:
        raw = sys.stdin.read()
    except Exception as e:
        return StdinPayload(
            None, "stdin could not be read (%s: %s)" % (type(e).__name__, e))
    if not raw or not raw.strip():
        return StdinPayload(None, "stdin was empty")
    try:
        return StdinPayload(json.loads(raw), None)
    except ValueError as e:
        return StdinPayload(
            None, "stdin was not valid JSON (%s: %s)" % (type(e).__name__, e))


def cmd_hook(argv):
    parsed = read_stdin_json()
    if parsed.error is not None:
        _warn("sbe_fence_hook: FAILING OPEN, the write is allowed and the fence "
              "was NOT checked. Reason: %s" % parsed.error)
        return 0
    decision = decide(parsed.payload)
    for n in decision.notes:
        _warn(n)
    if decision.payload is not None:
        _out(json.dumps(decision.payload))
    return 0


def cmd_fences(argv):
    """Diagnostics: what this hook can see right now, and what it cannot.

    Everything on stderr and nothing on stdout, because stdout is the decision
    channel and a diagnostic there would corrupt the protocol if anyone wired
    this subcommand into the hook slot by mistake."""
    if argv and argv[0].startswith("-"):
        # A flag is not a directory: `fences --bogus` used to be read as a
        # directory named --bogus and reported "no fence is enforceable",
        # exit 0, which is a silent misread of the invocation.
        _warn(FENCE_HOOK_USAGE)
        _warn("sbe_fence_hook fences: unrecognized flag %r; refusing rather than "
              "reading it as a directory" % argv[0])
        return 2
    cwd = argv[0] if argv else os.getcwd()
    _warn("registry patterns: %s" % ", ".join(registry_patterns(cwd)))
    try:
        found = read_fences(cwd)
    except OpenFail as e:
        _warn("no fence is enforceable here, so every write would be ALLOWED. "
              "Reason: %s" % e)
        return 0
    for n in found.notes:
        _warn(n)
    for f in found.fences:
        _warn("LIVE %s | agent %s | session %s | files %s"
              % (os.path.basename(f.registry), f.agent, f.session or "(none)",
                 ", ".join(f.files)))
    _warn("%d live fence line(s) enforceable from %s" % (len(found.fences), cwd))
    return 0


_COMMANDS = {
    "hook": cmd_hook,
    "fences": cmd_fences,
}

FENCE_HOOK_USAGE = (
    "usage: sbe_fence_hook.py [hook|fences [directory]]\n"
    "  hook (or no subcommand): the Claude Code PreToolUse hook; reads one JSON\n"
    "    payload from stdin, prints its decision to stdout, and FAILS OPEN.\n"
    "  fences [directory]: diagnostics on stderr, the live fences enforceable\n"
    "    from the directory (default: the current one).\n"
    "  flags:\n"
    "    -h, --help        print this and exit 0 without reading stdin"
)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if any(a in ("-h", "--help") for a in argv):
        # Help is not an error and exits 0 without reading stdin. It goes to
        # stderr like every other diagnostic here, because stdout is the
        # decision channel and a usage text there would corrupt the protocol
        # if this ever ran in the hook slot with a stray flag.
        _warn(FENCE_HOOK_USAGE)
        return 0
    if argv and argv[0] in _COMMANDS:
        return _COMMANDS[argv[0]](argv[1:])
    if argv and not argv[0].startswith("-"):
        _warn("sbe_fence_hook: unknown command %r; expected one of: %s"
              % (argv[0], ", ".join(sorted(_COMMANDS))))
        return 2
    # No subcommand is the HOOK invocation, because that is how Claude Code calls
    # it: a bare command with a JSON payload on stdin.
    return cmd_hook(argv)


if __name__ == "__main__":
    sys.exit(main())
