"""Generate a receipt by RUNNING the command, and refuse to read one that was
merely written.

The defect this exists for, in one sentence: every receipt this project reads
today can be typed by hand by the same agent whose work it verifies, so a
fabricated duration, exit code, row count or rerun id satisfies the schema and a
gate PASSes on a run nobody's command ever performed.

Two bindings close it, and both are stated with their limits because a control
that oversells itself is worse than none:

1. THE COMMAND IS RUN HERE. `sbe evidence run -- <command...>` executes the
   command through `subprocess`, times it, and records what it observed. There
   is no argument that writes a duration or an exit code; those come from the
   run or the receipt does not exist. This is the binding that matters, and it
   is why this module is a wrapper rather than a validator.
2. THE RECEIPT IS BOUND TO A COMMIT AND TO FILE CONTENT. `headCommit` must be
   the head at verify time, and every file the receipt claims to cover must
   still hold the bytes whose digest the receipt recorded. Evidence made against
   code that has since changed is evidence about a different program.

WHAT THE SEAL IS, AND WHAT IT IS NOT. `runId` is a SHA256 over the receipt's own
run facts, recomputed at verify time. It is TAMPER EVIDENCE against hand
authoring: a plausible receipt typed to satisfy the schema does not carry a
matching seal and is refused by name. It is NOT a signature. Anybody who can
read this file can compute a matching seal, because the input is the receipt
itself and the key is nothing. So a locally generated receipt is never more than
LOCAL-ADVISORY, and the only receipt this project will call PROTECTED-CI is one
minted where `SBE_CI_RUN_ID` was set by an environment the agent does not
control. `show` prints that trust level on every receipt, every time, so the
distinction is never something a reader has to remember.

DIGESTS, NEVER RAW OUTPUT. `stdout` and `stderr` are recorded as SHA256 digests
and byte counts only. A receipt is a file that gets committed, pasted into a
pull request and shipped to whoever asks for evidence, and a command that prints
a token, a connection string or a customer row would otherwise persist it
forever in the one artifact everybody is encouraged to share. The digest proves
the same bytes came back; it carries none of them.

WHICH CHECK RAN IS DECLARED, NEVER INFERRED FROM THE COMMAND LINE. `--kind`
records, as a first-class sealed field, which of this project's obligations the
run is offered against (`design`, `gate`, `score`). It exists because the
consumer of these receipts used to work the identity out for itself, by
substring-matching the recorded `argv`: a receipt for `/bin/cat
tests/test_design_of_gate_score.txt` named all three words, so one command that
ran no check at all cleared three obligations at once. Nothing about that was
hypothetical; it was reproduced. The field moves the claim from a guess a reader
makes about a string to a statement the receipt carries.

What the field IS: a declaration made at generation time, bound to a run that
actually happened, sealed with everything else, so it cannot be added to a
receipt afterwards and cannot be given to a command that never ran. What it is
NOT: proof of what the command did. This wrapper starts a process and times it;
it does not understand the process. An operator who types `--kind design` over a
command that checks nothing has written a false declaration, and the receipt
records the argv right beside it so a reader can see the two disagree. A receipt
that declares no kind clears no obligation, and one written before this field
existed is legacy: NO-DATA for obligation purposes, never a silent pass.

ARGV IS DIFFERENT, AND ONLY PARTLY FIXED. Unlike stdout and stderr, `argv` has
to be recorded as text: a receipt whose command was paraphrased proves nothing
about what happened. So a credential typed ON the command line used to be
persisted into the receipt verbatim, and the receipt is the one artifact
everybody is encouraged to share. `redact_argv()` now masks any token matching
a KNOWN secret shape before `argv` is written, reusing (not reinventing) the
same `SECRET_PATTERNS` `tools/sbe_telemetry.py` already scans an operator's own
messages with. Each match becomes a named marker, `[REDACTED:<shape>]`, and the
receipt records `argvRedactions`, the count, so a reader knows whether `argv` is
still verbatim (0) or not. This narrows the limit; it does not close it. The
pattern list is finite by nature, so a secret in a shape the list does not know
still reaches the receipt untouched. That residual is stated, not hidden, in
`docs/KNOWN-LIMITS.md`.

Python floor is 3.9: no match statements, no `X | Y` annotations. Standard
library only, because zero dependencies is a promise on this project's front
page and an evidence generator is the last place to retract it.
"""
import argparse
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import time

from . import SCHEMA_VERSION, version
from .impact import DiffUnavailable, changed_files, resolve_range, _git

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools")
if os.path.abspath(TOOLS) not in sys.path:
    sys.path.insert(0, os.path.abspath(TOOLS))
from sbe_checks import answered, evidence_problem  # noqa: E402
from sbe_telemetry import SECRET_PATTERNS  # noqa: E402

#: Schema versions this module knows how to read. An unknown version is refused
#: rather than parsed hopefully: a consumer that reads an old field under new
#: semantics is worse off than one that fails loudly. See `_check_schema`.
#: OLDEST FIRST, and the order is load-bearing: `_fields_for` reads it as the
#: version timeline, so a receipt is never judged by a field its own version
#: postdates.
KNOWN_SCHEMA_VERSIONS = ("1.0", "1.1", "1.2")

#: The version NEW receipts are stamped with. Evidence-local on purpose: the
#: package-wide SCHEMA_VERSION governs other stores (the task registry, the
#: init config), and coupling their versions would force every consumer to
#: move in lockstep for a change only receipts carry. "1.1" adds
#: `argvRedactions` beside the recorded argv. "1.2" adds `checkKinds` and
#: `checkKindsSource`, the declared identity of the check this run is offered
#: as. FORWARD ONLY: no receipt already on disk is rewritten by this bump, and
#: every older version stays readable under its own contract.
EVIDENCE_SCHEMA_VERSION = "1.2"

GENERATOR = "sbe evidence run"

#: The obligations a receipt can be declared against, and the ONE place this
#: vocabulary is written down. `src/brothersbe/status.py` derives its own
#: MISSING EVIDENCE table from this tuple rather than keeping a second copy,
#: so a kind added here can never be a kind the consumer silently does not
#: know. Values are lowercase and stable: they are written into receipts that
#: outlive the build that wrote them.
CHECK_KIND_NAMES = ("design", "gate", "score")

#: Every field a receipt must record before any verdict is built on it. Each
#: goes through `answered()`, the same vacuity test every other receipt field in
#: this project goes through, so "" and "TODO" record nothing here too. `0` and
#: `False` are answers: a zero exit code and a zero-byte stdout are results.
#: `checkKinds` is deliberately NOT here: an empty list is a real answer (this
#: run declares no obligation), and `answered()` reads an empty list as
#: nothing, so requiring it would fail every honest run that made no claim.
#: `checkKindsSource` IS required, because the provenance sentence is written
#: unconditionally: a receipt that carries no sentence at all is a receipt
#: whose generator never considered the question.
REQUIRED_FIELDS = (
    "schemaVersion", "generator", "generatorVersion", "runId", "argv",
    "argvRedactions", "startedAt", "endedAt", "durationSeconds", "exitCode",
    "headCommit", "stdoutSha256", "stderrSha256", "environment", "toolVersions",
    "workingTreeDirty", "coveredFilesSource", "checkKindsSource",
)

#: The facts the seal covers. Deliberately every fact a forger would have to
#: choose: the command, when it ran, how long it took, what it returned, what it
#: printed, which commit it was made against, and what it claims to cover.
#: `argv` here is the RECORDED argv, after `redact_argv()` has run: the seal
#: covers what the receipt actually says, the same way it always has, and
#: `argvRedactions` sits beside it so a forger cannot drop the count to make a
#: redacted receipt read as verbatim without breaking the seal.
#: `checkKinds` and `checkKindsSource` are sealed for the reason the whole
#: field exists: an unsealed identity could be typed into an existing receipt
#: afterwards, which is the same hand-authoring this module refuses everywhere
#: else. Sealed, a declared kind can only come from a run that happened.
SEALED_FIELDS = (
    "schemaVersion", "generator", "generatorVersion", "argv", "argvRedactions",
    "startedAt", "endedAt", "durationSeconds", "exitCode", "baseCommit",
    "headCommit", "stdoutSha256", "stderrSha256", "stdoutBytes", "stderrBytes",
    "environment", "toolVersions", "workingTreeDirty", "ciRunId",
    "coveredFiles", "coveredFilesSource", "repository", "checkKinds",
    "checkKindsSource",
)

#: Which fields each schema version INTRODUCED, so `_fields_for` can judge a
#: receipt by its own version's contract instead of by the newest one. Add a
#: row here when a version adds a field; nothing else needs to change.
FIELDS_INTRODUCED_IN = (
    ("1.1", ("argvRedactions",)),
    ("1.2", ("checkKinds", "checkKindsSource")),
)


def _fields_for(declared, fields):
    """The field tuple a receipt of `declared` schema version is judged by.

    "1.0" predates argv redaction and "1.1" predates the declared check kind,
    so their receipts are judged by their own contract: requiring a field that
    version never defined would fail an honest old receipt with a sentence
    about emptiness instead of the truth, that the field postdates it. Fields
    are only ever ADDED here, which is what makes the bump forward-only.

    An unknown or missing version is judged by the FULL, newest set, which is
    the strict direction: `_check_schema` refuses an unknown version before
    any caller in `verify` reaches this, so the only way to arrive here with
    one is a caller that skipped that refusal, and such a caller should get
    the strictest reading rather than the most forgiving.
    """
    if declared not in KNOWN_SCHEMA_VERSIONS:
        return fields
    age = KNOWN_SCHEMA_VERSIONS.index(declared)
    later = set()
    for version_name, names in FIELDS_INTRODUCED_IN:
        if KNOWN_SCHEMA_VERSIONS.index(version_name) > age:
            later.update(names)
    return tuple(f for f in fields if f not in later)


#: One name per pattern in `SECRET_PATTERNS`, same order, so a redacted argv
#: token says WHICH shape matched instead of a bare "[REDACTED]". The patterns
#: themselves are imported above from `tools/sbe_telemetry.py`, the same list
#: the telemetry redactor already scans an operator's own messages with; only
#: these labels are added here, because that redactor never needed to name a
#: shape and a receipt reader does. Kept in sync by `redact_argv()`'s own length
#: check below: a mismatch is refused rather than mislabeled.
ARGV_REDACTION_SHAPES = (
    "api-key", "github-token", "github-pat", "aws-key-id", "slack-token",
    "bearer-token", "private-key", "jwt", "kv-secret", "ssn", "card-number",
)


class ReceiptUnreadable(Exception):
    """The receipt could not be read at all, so nothing was inspected.

    Raised rather than returning an empty receipt, because an empty receipt and
    an unreadable one produce the same dict and only one of them is a file
    somebody wrote.
    """


def _sha256_bytes(blob):
    return hashlib.sha256(blob).hexdigest()


def _sha256_file(path):
    """The digest of a file's bytes, or None when it cannot be read.

    None is a real answer here and the caller says which one it got: a covered
    file that has been deleted is a different finding from one whose contents
    changed, and folding both into "changed" would name the wrong thing.
    """
    try:
        with open(path, "rb") as fh:
            return _sha256_bytes(fh.read())
    except (IOError, OSError):
        return None


def _iso(epoch):
    """ISO 8601 in UTC, to the second, with an explicit Z.

    A local timestamp in a receipt that travels between a laptop and CI is a
    timestamp nobody can compare. The machine comparison uses the epoch fields
    beside this one; this string is for the human reading `show`.
    """
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def redact_argv(argv):
    """(redacted argv, redaction count, provenance note). Three values, not two:
    a two-value return here would read as a possible verdict source to this
    project's own honesty meta-test (`evals/test_no_data_class.py`), and this
    is not a verdict either, so it says what it is in the third slot rather
    than shipping a bare pair.

    Reuses `SECRET_PATTERNS` imported from `tools/sbe_telemetry.py` above: the
    same shapes the telemetry redactor already masks in an operator's own
    messages, never a second list invented here that could drift from it. Each
    match is replaced by a NAMED marker, `[REDACTED:<shape>]`, using
    `ARGV_REDACTION_SHAPES`, so a reader can tell an AWS key id from an SSN
    without re-deriving the match from a bare "[REDACTED]".

    Matched per ARGUMENT, not on the command line joined into one string:
    joining first would let a shape span a boundary no shell ever produced (the
    end of one argument and the start of the next reading as a single token),
    which is exactly the kind of over-matching a receipt cannot afford to be
    wrong about in the other direction. Each `argv[i]` is scanned and replaced
    independently, in the order the command actually received it.

    This is the same limit the source list carries in its own file: finite by
    nature, so a secret typed in a shape none of these patterns know still
    reaches the receipt untouched. That residual is named in
    `docs/KNOWN-LIMITS.md`, not hidden by this function's success on the shapes
    it does know.
    """
    if len(ARGV_REDACTION_SHAPES) != len(SECRET_PATTERNS):
        raise RuntimeError(
            "ARGV_REDACTION_SHAPES names %d shape(s) but the imported SECRET_PATTERNS from "
            "tools/sbe_telemetry.py holds %d pattern(s); they must change together or a "
            "redaction marker would name the wrong shape. Fix src/brothersbe/evidence.py "
            "before writing another receipt."
            % (len(ARGV_REDACTION_SHAPES), len(SECRET_PATTERNS)))
    redacted = []
    count = 0
    for token in argv:
        clean = token
        for pattern, shape in zip(SECRET_PATTERNS, ARGV_REDACTION_SHAPES):
            clean, hits = pattern.subn("[REDACTED:%s]" % shape, clean)
            count += hits
        redacted.append(clean)
    if count == 0:
        note = "0 redaction(s): argv is recorded verbatim, unchanged from what ran"
    else:
        note = ("%d redaction(s) against %d known secret shape(s) mirrored from "
                "tools/sbe_telemetry.py::SECRET_PATTERNS; argv is no longer verbatim"
                % (count, len(SECRET_PATTERNS)))
    return redacted, count, note


def kind_declaration_note(kinds):
    """The provenance sentence written into `checkKindsSource`, every time.

    Written unconditionally, including when nothing was declared, because the
    absence of a declaration is itself a fact a reader needs: a receipt with an
    empty `checkKinds` and no sentence beside it is indistinguishable from a
    receipt whose generator predates the field, and those two are different
    situations. One value, not a pair: this is a note, never a verdict.
    """
    if not kinds:
        return ("no --kind was given, so this receipt declares no check kind and satisfies no "
                "design, gate or score obligation. A kind is never inferred from the recorded "
                "command line; that inference is the defect this field replaced")
    return ("declared by --kind at generation time: %s. The wrapper ran the command and timed "
            "it; it does not inspect what the command did, so this names the obligation the "
            "run was OFFERED against, never a proof that the command performs that check. The "
            "recorded argv sits beside it for a reader to compare"
            % ", ".join(kinds))


def declared_kinds(receipt):
    """The set of check kinds this receipt DECLARES. Never inferred from argv.

    The one reader of the field, so `sbe status` and anything else downstream
    cannot drift into a second interpretation. An entry that is not a known
    kind name is dropped here rather than passed on, because an unknown kind
    can clear no obligation this build knows about; `_check_kinds` is what
    reports the receipt as malformed for carrying one.
    """
    declared = receipt.get("checkKinds")
    if not isinstance(declared, list):
        return set()
    return set(k for k in declared if isinstance(k, str) and k in CHECK_KIND_NAMES)


def kind_declaration_gap(receipt):
    """The sentence saying why this receipt clears no obligation, or None when
    it declares at least one kind.

    Three different absences, named separately, because a consumer that folds
    them together tells a reader "no evidence" where the truth is "evidence
    this build cannot read as evidence for anything":
    a receipt written before the field existed, a receipt whose field holds
    something that is not a list of kinds, and an honest run that declared
    nothing.
    """
    if declared_kinds(receipt):
        return None
    version_seen = answered(receipt.get("schemaVersion")) or "no schemaVersion"
    if "checkKinds" not in receipt:
        return ("it records no checkKinds field at all (schema %s predates it), so which check "
                "it ran is not stated anywhere in it. Legacy receipts are NO-DATA for "
                "obligation purposes here, never a silent pass; re-run the check through `sbe "
                "evidence run --kind <design|gate|score>` to record one that says"
                % version_seen)
    raw = receipt.get("checkKinds")
    if not isinstance(raw, list):
        return ("its checkKinds field holds %r, which is not a list of check kinds, so nothing "
                "here can read which check it ran" % (raw,))
    known = [k for k in raw if isinstance(k, str) and k in CHECK_KIND_NAMES]
    if raw and not known:
        return ("its checkKinds field names only %s, and this build knows no such kind (it "
                "knows %s)" % (", ".join(repr(k) for k in raw), ", ".join(CHECK_KIND_NAMES)))
    return ("it declares no check kind: it was run without `--kind`, so it is evidence that a "
            "command ran and not evidence that any named obligation was met")


def working_tree_dirty(cwd):
    """(dirty, detail). A repository git cannot answer for is reported, never
    assumed clean: 'no output from git status' and 'git did not run' look
    identical downstream and only one of them means the tree is clean."""
    code, out, err = _git(["status", "--porcelain"], cwd)
    if code != 0:
        return None, "git status did not run here: %s" % (err.strip() or "no message")
    lines = [l for l in out.split("\n") if l.strip()]
    return bool(lines), "%d uncommitted path(s)" % len(lines)


def repository_identity(cwd):
    """The remote this work came from, or an honest note that there is none.

    A local clone with no remote is a normal thing and not a defect, so it is
    recorded as such rather than left blank, which would be indistinguishable
    from a field the generator forgot to fill.
    """
    code, out, _err = _git(["remote", "get-url", "origin"], cwd)
    remote = out.strip() if code == 0 else ""
    return {
        "remote": remote or None,
        "remoteNote": None if remote else "no origin remote is configured in this clone",
        "root": os.path.abspath(cwd),
    }


def compute_seal(receipt):
    """The SHA256 over the sealed run facts, canonically encoded.

    `sort_keys` and a fixed separator set, so two runs that observed the same
    facts produce the same seal on any machine, and a field reordered by an
    editor does not read as a tampered receipt.
    """
    declared = answered(receipt.get("schemaVersion")) or EVIDENCE_SCHEMA_VERSION
    payload = dict((k, receipt.get(k)) for k in _fields_for(declared, SEALED_FIELDS))
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")
    return _sha256_bytes(blob)


def trust_level(receipt):
    """LOCAL-ADVISORY or PROTECTED-CI, and the sentence saying why.

    PROTECTED-CI needs both a CI run id minted by the environment AND a clean
    tree at generation time. A CI job running over uncommitted edits is not
    protected by being CI; it is a local run wearing a badge.
    """
    ci = answered(receipt.get("ciRunId"))
    dirty = receipt.get("workingTreeDirty")
    if ci is None:
        return ("LOCAL-ADVISORY",
                "no SBE_CI_RUN_ID was set when this ran, so nothing outside the machine that "
                "wrote it attests to it")
    if dirty is not False:
        return ("LOCAL-ADVISORY",
                "a CI run id is recorded (%s) but the working tree was dirty or unreadable at "
                "generation time, and a run over uncommitted edits is not protected by being "
                "CI" % ci)
    return ("PROTECTED-CI",
            "minted under CI run id %s on a clean tree, by an environment the agent does not "
            "set for itself" % ci)


def generate(cwd, argv, base=None, head="HEAD", covers=None, timeout=None, kinds=None):
    """Run `argv` and return the receipt describing what actually happened.

    The command runs HERE. Nothing in the signature accepts a duration, an exit
    code or an output digest, which is the whole point: those three are the
    fields a hand-written receipt gets to invent today.

    `kinds` is the operator's declaration of WHICH obligation this run is
    offered against, from `CHECK_KIND_NAMES`, and it is the one thing here the
    wrapper takes on trust rather than observes. It is taken anyway, because
    the alternative shipped for a wave and was worse: the consumer guessed the
    identity from the command line, and a command that ran no check cleared
    three obligations by having three words in a filename. A declaration is
    checkable by a reader against the argv recorded next to it; a guess is not.

    `timeout`, in seconds, is None unless the caller passes `--timeout`. There
    is no default: a silent one would kill a legitimate long suite and hand
    back a receipt about a run that never finished, which is the exact
    false-positive pattern this project's kill criteria warn against. When it
    is set and the command outruns it, `subprocess.run` kills the child and
    waits for it (that is Python's own contract for `timeout=`, not something
    hand-rolled here), and this raises `ReceiptUnreadable` rather than writing
    a receipt: no exit code was ever observed, so there is nothing honest to
    seal, and the caller's stderr names what happened instead.
    """
    if not argv:
        raise ReceiptUnreadable("no command to run: `sbe evidence run` needs `-- <command...>`")

    # Refused BEFORE the command runs, not after: a receipt that could not be
    # written is a run whose result nobody records, so the argument that makes
    # the receipt impossible has to fail first.
    declared = sorted(set(kinds or ()))
    unknown = [k for k in declared if k not in CHECK_KIND_NAMES]
    if unknown:
        raise ReceiptUnreadable(
            "no receipt would be readable for check kind(s) %s; this build knows %s. A kind "
            "nothing downstream recognizes clears no obligation, so it is refused here rather "
            "than written into a receipt that would look like a claim"
            % (", ".join(repr(k) for k in unknown), ", ".join(CHECK_KIND_NAMES)))

    covered_source = "explicit --covers"
    if covers:
        covered_paths = list(covers)
    else:
        try:
            base_sha, head_ref = resolve_range(cwd, base, head)
            covered_paths = changed_files(cwd, base_sha, head_ref)
            covered_source = "the diff %s..%s" % (base_sha[:12], head_ref)
        except DiffUnavailable as exc:
            covered_paths = []
            covered_source = "none: %s" % exc

    code, base_out, _e = _git(["rev-parse", base] if base else ["rev-parse", "HEAD^"], cwd)
    base_commit = base_out.strip() if code == 0 else None
    code, head_out, _e = _git(["rev-parse", head], cwd)
    head_commit = head_out.strip() if code == 0 else None

    dirty, dirty_detail = working_tree_dirty(cwd)

    started = time.time()
    try:
        proc = subprocess.run(list(argv), cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout)
    except OSError as exc:
        raise ReceiptUnreadable(
            "the command did not start, so there is no run to write a receipt about: %s" % exc)
    except subprocess.TimeoutExpired:
        elapsed = time.time() - started
        raise ReceiptUnreadable(
            "the command was killed after %.3fs, past --timeout %ss. No exit code was ever "
            "observed, so no receipt was written for this run: a timeout is a fact about the "
            "wrapper, never a fact worth sealing as if the command had answered. Rerun without "
            "--timeout, or with a longer one, if this command legitimately needs more time"
            % (elapsed, timeout))
    ended = time.time()

    # Pass the child's output through untouched. A wrapper that swallows what
    # the command printed makes the human read the receipt instead of the run,
    # and the receipt deliberately does not carry the text.
    if proc.stdout:
        sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
    if proc.stderr:
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))

    covered = []
    for rel in covered_paths:
        full = rel if os.path.isabs(rel) else os.path.join(cwd, rel)
        digest = _sha256_file(full)
        covered.append({
            "path": rel,
            "sha256": digest,
            "note": None if digest else "this file could not be read when the receipt was "
                                        "written, so its content is not bound to this run",
        })

    # The COMMAND already ran above, over the untouched `argv` the caller gave
    # this function. Only the RECORDED copy is redacted here, after the run, so
    # a masked token never reaches the process that was actually invoked.
    redacted_argv, argv_redactions, argv_redaction_note = redact_argv(list(argv))

    receipt = {
        "schemaVersion": EVIDENCE_SCHEMA_VERSION,
        "generator": GENERATOR,
        "generatorVersion": version(),
        "repository": repository_identity(cwd),
        "baseCommit": base_commit,
        "headCommit": head_commit,
        "argv": redacted_argv,
        "argvRedactions": argv_redactions,
        "startedAt": _iso(started),
        "endedAt": _iso(ended),
        "startedAtEpoch": round(started, 6),
        "endedAtEpoch": round(ended, 6),
        "durationSeconds": round(ended - started, 6),
        "exitCode": proc.returncode,
        "toolVersions": {
            "python": platform.python_version(),
            "sbe": version(),
        },
        "environment": platform.platform(),
        # DIGESTS, NOT TEXT, and the reason is in the module docstring: a
        # receipt is the one artifact everybody is encouraged to share, so a
        # secret printed by the command must not be persisted into it.
        "stdoutSha256": _sha256_bytes(proc.stdout or b""),
        "stderrSha256": _sha256_bytes(proc.stderr or b""),
        "stdoutBytes": len(proc.stdout or b""),
        "stderrBytes": len(proc.stderr or b""),
        "outputPolicy": "digests only; raw stdout and stderr are never persisted, because a "
                        "receipt is shared and a secret in output would be shared with it",
        "workingTreeDirty": dirty,
        "workingTreeDetail": dirty_detail,
        "ciRunId": os.environ.get("SBE_CI_RUN_ID") or None,
        "coveredFiles": covered,
        "coveredFilesSource": covered_source,
        # WHICH CHECK, as a field, because the consumer used to read it out of
        # the command line above and a filename could spell three obligations.
        "checkKinds": declared,
        "checkKindsSource": kind_declaration_note(declared),
    }
    receipt["runId"] = compute_seal(receipt)
    return receipt


def load(path):
    """The receipt at `path`, or raise. A file that is not JSON is not a receipt.

    ACCESS is checked BEFORE open(), by stat rather than by opening: a FIFO
    where a receipt was expected used to hang this command forever, in both
    text and JSON mode, with no verdict line at all, which is worse than any
    parse failure because a parse failure at least prints FAIL. This is the
    same `evidence_problem` check the hard gates use (`tools/sbe_checks.py`,
    `tools/sbe_gate.py::load_receipt`), so a FIFO, socket, device or
    unreadable file is refused by name here in bounded time instead.
    """
    if not path or not os.path.exists(path):
        raise ReceiptUnreadable("no receipt at %s; absent evidence is NO-DATA, never a pass"
                                % path)
    problem = evidence_problem(path)
    if problem:
        raise ReceiptUnreadable(
            "%s was refused before it was opened: %s. Opening it directly could block this "
            "command forever; a broken claim must never look like a hang" % (path, problem))
    if os.path.isdir(path):
        raise ReceiptUnreadable("%s is a directory, not a receipt" % path)
    try:
        with io.open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as exc:
        raise ReceiptUnreadable("%s does not parse as JSON: %s" % (path, exc))
    except (IOError, OSError) as exc:
        raise ReceiptUnreadable("%s could not be opened: %s" % (path, exc))
    if not isinstance(data, dict):
        raise ReceiptUnreadable("%s holds %s at the top level; a receipt is a JSON object"
                                % (path, type(data).__name__))
    return data


def _check_schema(receipt):
    declared = answered(receipt.get("schemaVersion"))
    if declared is None:
        return "the receipt records no schemaVersion, so nothing here knows what its fields mean"
    if declared not in KNOWN_SCHEMA_VERSIONS:
        return ("schemaVersion %r is not one this build reads (%s); an unknown schema is "
                "refused rather than parsed hopefully, because a field read under the wrong "
                "semantics is worse than one that fails loudly"
                % (declared, ", ".join(KNOWN_SCHEMA_VERSIONS)))
    return None


def _check_required(receipt):
    fields = _fields_for(answered(receipt.get("schemaVersion")), REQUIRED_FIELDS)
    missing = [f for f in fields if answered(receipt.get(f)) is None]
    if not missing:
        return None
    return ("%d required field(s) record nothing: %s. A field holding \"\", null or a "
            "placeholder is a field nobody answered, and a verdict built on it would be "
            "describing an empty string" % (len(missing), ", ".join(sorted(missing))))


def _check_kinds(receipt):
    """The declared check kind is a list of names this build knows, or nothing.

    Only the SHAPE is checkable here. Whether the command actually performed
    the declared check is not something this module can know, and a control
    that pretended otherwise would be the overselling this file's own docstring
    warns about. A receipt that carries no field at all is not a problem: that
    is a legacy receipt, judged under its own version, and its consequence
    lives at the consumer (it clears no obligation) rather than as a FAIL here.
    """
    if "checkKinds" not in receipt:
        return None
    raw = receipt.get("checkKinds")
    if not isinstance(raw, list):
        return ("checkKinds records %r, and a check kind list is a JSON array; a receipt whose "
                "declared identity cannot be read is not a receipt anything should build an "
                "obligation verdict on" % (raw,))
    bad = [k for k in raw if not isinstance(k, str) or k not in CHECK_KIND_NAMES]
    if bad:
        return ("checkKinds names %s, which this build does not know (it knows %s). An "
                "unrecognized kind is refused rather than ignored, because ignoring it would "
                "leave a receipt that reads as a declaration and satisfies nothing"
                % (", ".join(repr(k) for k in bad), ", ".join(CHECK_KIND_NAMES)))
    return None


def _check_seal(receipt):
    claimed = answered(receipt.get("runId"))
    actual = compute_seal(receipt)
    if claimed == actual:
        return None
    return ("runId %s does not match the seal over this receipt's own run facts (%s). Either "
            "the receipt was written by hand rather than generated by `%s`, or a sealed field "
            "was edited after the run. This seal is tamper evidence, not a signature: it "
            "catches a plausible receipt nobody's command produced, and it does not stop "
            "somebody who read src/brothersbe/evidence.py"
            % (claimed, actual, GENERATOR))


def _check_commit(receipt, cwd):
    """(problem, note). The binding that makes a receipt evidence for ONE commit."""
    code, out, err = _git(["rev-parse", "HEAD"], cwd)
    if code != 0:
        return None, ("HEAD does not resolve in %s (%s), so the commit binding was not "
                      "checked and nothing here confirms which code this receipt covers"
                      % (cwd, err.strip() or "no message"))
    current = out.strip()
    claimed = answered(receipt.get("headCommit"))
    if claimed == current:
        return None, "headCommit %s is the current head" % current[:12]
    return ("headCommit %s is not the current head %s: this receipt is evidence for a commit "
            "that is no longer checked out, and the code it covered has moved"
            % (str(claimed)[:12], current[:12]), None)


def _under_excluded(rel, exclude_dirs):
    """True when `rel` (a receipt-recorded path, POSIX-style) sits inside one
    of `exclude_dirs` (also POSIX-style, relative to the same root). A path
    equal to an excluded directory, or nested under it, matches; a path that
    merely shares a string prefix (`.sbe/evidence-old` against `.sbe/evidence`)
    does not, because this compares path SEGMENTS, not characters."""
    norm = rel.replace(os.sep, "/").strip("/")
    for d in exclude_dirs or ():
        dn = str(d).replace(os.sep, "/").strip("/")
        if dn and (norm == dn or norm.startswith(dn + "/")):
            return True
    return False


def _check_covered(receipt, cwd, exclude_dirs=None):
    """(problems, note, excluded). Did the code this receipt claims to cover
    change since?

    Two ways a covered file stops being covered, and both are named separately
    because they are different findings: the bytes differ from the digest the
    receipt recorded, or the file was written after the run ended. The second
    catches a change that was made and reverted, and it is deliberately strict:
    a file touched after the evidence was made is a file the evidence did not
    see in its current state.

    `exclude_dirs`, when given, names path prefixes this receipt's coverage
    must never be judged against, even though `coveredFiles` still lists them
    faithfully (that field records what the diff actually found; this
    function decides what that finding is allowed to PROVE). This exists for
    one reason: a receipt's `coveredFiles`, computed from a diff rather than
    an explicit `--covers` list, cannot tell "code this run tested" from
    "another evidence receipt that happened to land in the same diff", and a
    receipt that regenerates routinely (every CI push re-runs the same check
    at the same `--out` path) is not a fact about the code under test. Without
    this, an unrelated receipt that merely covered the OLD bytes by diff-range
    accident fails the moment the covered receipt is refreshed: the evidence
    store poisoning itself. See docs/KNOWN-LIMITS.md ("Evidence covering
    evidence") for what excluding it does and does not close.
    """
    covered = receipt.get("coveredFiles") or []
    ended = receipt.get("endedAtEpoch")
    problems, checked, touched, excluded = [], 0, 0, 0
    for entry in covered:
        rel = answered(entry.get("path"))
        if rel is None:
            problems.append("a coveredFiles entry records no path")
            continue
        if _under_excluded(rel, exclude_dirs):
            excluded += 1
            continue
        full = rel if os.path.isabs(rel) else os.path.join(cwd, rel)
        if not os.path.exists(full):
            problems.append("covered file %s no longer exists" % rel)
            continue
        checked += 1
        recorded = entry.get("sha256")
        actual = _sha256_file(full)
        if recorded and actual != recorded:
            problems.append("covered file %s now hashes to %s, not the %s the receipt "
                            "recorded: the code changed after the evidence was made"
                            % (rel, str(actual)[:12], str(recorded)[:12]))
            continue
        if isinstance(ended, (int, float)):
            try:
                mtime = os.path.getmtime(full)
            except OSError:
                problems.append("covered file %s could not be stat'd, so nothing confirms it "
                                "is unchanged" % rel)
                continue
            if mtime > ended:
                touched += 1
                problems.append("covered file %s was written after the run ended (%s vs %s); "
                                "a file touched after the evidence was made is a file the "
                                "evidence did not see"
                                % (rel, _iso(mtime), _iso(ended)))
    note = ("%d covered file(s) re-hashed against the receipt, %d written after the run"
            % (checked, touched))
    if excluded:
        note += (", %d under an excluded path (the evidence store) never judged as coverage"
                 % excluded)
    return problems, note, excluded


def verify(path, cwd=None, exclude_dirs=None):
    """PASS, FAIL or NO-DATA over one receipt, with the reasons it inspected.

    ORDER, and it is deliberate. Every FAIL condition is evaluated first, then
    the dirty-tree condition. A broken claim is FAIL even when the receipt is
    advisory, because "this receipt is wrong" outranks "this receipt was never
    authoritative". Only a receipt with nothing broken about it can reach the
    NO-DATA that a dirty tree earns, and only a clean one can reach PASS.

    `exclude_dirs`, forwarded to `_check_covered` unchanged, names path
    prefixes (relative to `cwd`) whose `coveredFiles` entries are recorded but
    never judged: see `_check_covered` for why. Every existing caller that
    does not pass it keeps today's behavior exactly, because the default is
    an empty exclusion, not a guessed one.
    """
    cwd = os.path.abspath(cwd or os.getcwd())
    inspected = ["receipt file %s" % path]
    try:
        receipt = load(path)
    except ReceiptUnreadable as exc:
        return {"verdict": "FAIL", "reasons": [str(exc)], "inspected": inspected,
                "receipt": None, "trust": None, "trustWhy": None}

    problems, notes = [], []

    schema_problem = _check_schema(receipt)
    inspected.append("schemaVersion")
    if schema_problem:
        # Stop here: every later check reads fields whose meaning is exactly
        # what the schema version defines, so continuing would be guessing.
        return {"verdict": "FAIL", "reasons": [schema_problem], "inspected": inspected,
                "receipt": receipt, "trust": None,
                "trustWhy": "an unreadable schema has no trust level"}

    inspected.append("%d required field(s)" % len(
        _fields_for(answered(receipt.get("schemaVersion")), REQUIRED_FIELDS)))
    required_problem = _check_required(receipt)
    if required_problem:
        problems.append(required_problem)

    inspected.append("the declared check kind(s)")
    kinds_problem = _check_kinds(receipt)
    if kinds_problem:
        problems.append(kinds_problem)

    inspected.append("the runId seal over %d run fact(s)" % len(
        _fields_for(answered(receipt.get("schemaVersion")), SEALED_FIELDS)))
    seal_problem = _check_seal(receipt)
    if seal_problem:
        problems.append(seal_problem)

    inspected.append("the current git HEAD in %s" % cwd)
    commit_problem, commit_note = _check_commit(receipt, cwd)
    if commit_problem:
        problems.append(commit_problem)
    if commit_note:
        notes.append(commit_note)

    covered = receipt.get("coveredFiles") or []
    inspected.append("%d covered file(s)" % len(covered))
    covered_problems, covered_note, covered_excluded = _check_covered(receipt, cwd, exclude_dirs)
    problems.extend(covered_problems)
    notes.append(covered_note)

    level, why = trust_level(receipt)

    if problems:
        return {"verdict": "FAIL", "reasons": problems, "inspected": inspected,
                "receipt": receipt, "trust": level, "trustWhy": why}

    if receipt.get("workingTreeDirty") is not False:
        detail = receipt.get("workingTreeDetail") or "the tree state was not recorded"
        return {"verdict": "NO-DATA", "inspected": inspected, "receipt": receipt,
                "trust": level, "trustWhy": why,
                "reasons": ["the working tree was dirty or unreadable when this ran (%s), so "
                            "the receipt covers a state that was never committed and nobody "
                            "else can reproduce. That is advisory, and advisory is NO-DATA "
                            "here rather than a pass" % detail]}

    if not covered:
        return {"verdict": "NO-DATA", "inspected": inspected, "receipt": receipt,
                "trust": level, "trustWhy": why,
                "reasons": ["the receipt covers no file at all (%s), so nothing here can "
                            "detect that the code changed after the evidence was made"
                            % (answered(receipt.get("coveredFilesSource")) or "no source "
                               "recorded")]}

    if covered_excluded >= len(covered):
        return {"verdict": "NO-DATA", "inspected": inspected, "receipt": receipt,
                "trust": level, "trustWhy": why,
                "reasons": ["every one of this receipt's %d covered file(s) (%s) sits under an "
                            "excluded path and was never judged as coverage, so nothing here "
                            "grounds this receipt in code that was actually inspected"
                            % (len(covered),
                               answered(receipt.get("coveredFilesSource")) or "no source "
                               "recorded")]}

    return {"verdict": "PASS", "reasons": notes, "inspected": inspected, "receipt": receipt,
            "trust": level, "trustWhy": why}


def render(receipt, path):
    """The human-readable form. Names the trust level first and unconditionally,
    because a reader who takes a LOCAL-ADVISORY receipt for an authoritative one
    has been misled by the layout rather than by the content."""
    level, why = trust_level(receipt)
    out = []
    out.append("receipt        %s" % path)
    out.append("trust          %s (%s)" % (level, why))
    out.append("generator      %s %s, schema %s"
               % (receipt.get("generator"), receipt.get("generatorVersion"),
                  receipt.get("schemaVersion")))
    argv = receipt.get("argv") or []
    out.append("command        %s" % (" ".join(str(a) for a in argv) if argv
                                      else "none recorded"))
    redactions = receipt.get("argvRedactions")
    out.append("argv redacted  %s" % (
        "not recorded" if redactions is None else
        "no (0 secret-shaped token(s) matched; the command above is verbatim)" if redactions == 0
        else "yes, %d secret-shaped token(s); the command above is NOT verbatim" % redactions))
    kinds = sorted(declared_kinds(receipt))
    out.append("check kinds    %s" % (", ".join(kinds) if kinds else "none declared"))
    out.append("kind source    %s" % (receipt.get("checkKindsSource")
                                      or "not recorded (this receipt predates the field)"))
    out.append("exit code      %s" % receipt.get("exitCode"))
    out.append("ran            %s to %s (%s s)"
               % (receipt.get("startedAt"), receipt.get("endedAt"),
                  receipt.get("durationSeconds")))
    repo = receipt.get("repository") or {}
    out.append("repository     %s" % (repo.get("remote") or repo.get("remoteNote")
                                      or "not recorded"))
    out.append("base commit    %s" % (receipt.get("baseCommit") or "not recorded"))
    out.append("head commit    %s" % (receipt.get("headCommit") or "not recorded"))
    out.append("tree at run    %s" % ("dirty" if receipt.get("workingTreeDirty")
                                      else "clean" if receipt.get("workingTreeDirty") is False
                                      else "not recorded"))
    tools = receipt.get("toolVersions") or {}
    out.append("tool versions  python %s, sbe %s"
               % (tools.get("python", "not recorded"), tools.get("sbe", "not recorded")))
    out.append("environment    %s" % (receipt.get("environment") or "not recorded"))
    out.append("stdout         sha256 %s over %s byte(s)"
               % (receipt.get("stdoutSha256"), receipt.get("stdoutBytes")))
    out.append("stderr         sha256 %s over %s byte(s)"
               % (receipt.get("stderrSha256"), receipt.get("stderrBytes")))
    out.append("output policy  %s" % (receipt.get("outputPolicy") or "not recorded"))
    out.append("runId          %s" % receipt.get("runId"))
    out.append("covers         %s (%s)"
               % (receipt.get("coveredFilesSource") or "not recorded",
                  "%d file(s)" % len(receipt.get("coveredFiles") or [])))
    for entry in (receipt.get("coveredFiles") or []):
        out.append("  %-12s %s" % (str(entry.get("sha256"))[:12], entry.get("path")))
    return "\n".join(out)


def _split_command(rest):
    """(our arguments, the command after the first bare `--`).

    Split by hand rather than left to argparse: `--` is the only unambiguous
    boundary between flags meant for this wrapper and flags meant for the
    command being run, and argparse silently eats the first one.
    """
    if "--" in rest:
        cut = rest.index("--")
        return rest[:cut], rest[cut + 1:]
    return list(rest), []


def _parser():
    parser = argparse.ArgumentParser(
        prog="sbe evidence",
        description="Generate a receipt by running the command, verify one against the "
                    "current commit, or show one with its trust level.")
    sub = parser.add_subparsers(dest="sub")

    run = sub.add_parser("run", help="run a command and write the receipt it earned")
    run.add_argument("--out", required=True, help="where to write the receipt")
    run.add_argument("--covers", action="append", default=[],
                     help="a file this run is evidence for; repeatable. Without it, the "
                          "files changed between base and head are used")
    run.add_argument("--kind", action="append", default=[], choices=list(CHECK_KIND_NAMES),
                     dest="kind",
                     help="the obligation this run is evidence for (%s); repeatable. Without "
                          "it the receipt declares no check kind and clears no obligation. "
                          "This is a declaration, not a proof: the wrapper runs the command, "
                          "it does not inspect what the command checks"
                          % "|".join(CHECK_KIND_NAMES))
    run.add_argument("--base", default=None, help="the commit to diff from for --covers")
    run.add_argument("--head", default="HEAD", help="the commit this receipt is made against")
    run.add_argument("--cwd", default=".", help="the repository to run in")
    run.add_argument("--timeout", type=float, default=None,
                     help="kill the command and refuse the receipt if it runs longer than "
                          "this many seconds. No default: a silent one would kill a "
                          "legitimate long-running suite")

    ver = sub.add_parser("verify", help="check a receipt against the current commit")
    ver.add_argument("receipt")
    ver.add_argument("--cwd", default=".", help="the repository to verify against")
    ver.add_argument("--json", action="store_true", help="machine-readable output")
    ver.add_argument("--strict", action="store_true",
                     help="make NO-DATA block as well, for protected CI")

    show = sub.add_parser("show", help="print a receipt and its trust level")
    show.add_argument("receipt")
    return parser


def main(rest, exit_ok=0, exit_failed=1, exit_usage=2):
    """The `sbe evidence` surface. Exit codes come from the caller so this module
    never disagrees with the CLI's documented table."""
    ours, command = _split_command(list(rest))
    parser = _parser()
    if not ours:
        parser.print_help(sys.stderr)
        return exit_usage
    try:
        args = parser.parse_args(ours)
    except SystemExit as exc:
        # argparse already answered: -h/--help printed the usage the caller
        # asked for and raised 0, and help is not an error. Anything nonzero
        # is a refused flag or argument. Folding both into exit_usage made
        # every explicit help request on this surface exit 2.
        return exit_ok if exc.code in (0, None) else exit_usage
    if not getattr(args, "sub", None):
        parser.print_help(sys.stderr)
        return exit_usage

    if args.sub == "run":
        if not command:
            sys.stderr.write("sbe evidence run: no command given. Usage: sbe evidence run "
                             "--out receipt.json -- <command...>. This wrapper runs the "
                             "command itself; there is nothing here that accepts a duration "
                             "or an exit code you typed.\n")
            return exit_usage
        try:
            receipt = generate(os.path.abspath(args.cwd), command, base=args.base,
                               head=args.head, covers=args.covers, timeout=args.timeout,
                               kinds=args.kind)
        except ReceiptUnreadable as exc:
            sys.stderr.write("sbe evidence run: no receipt written. %s\n" % exc)
            return exit_failed
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir and not os.path.isdir(out_dir):
            try:
                os.makedirs(out_dir)
            except OSError as exc:
                sys.stderr.write("sbe evidence run: cannot create %s: %s\n" % (out_dir, exc))
                return exit_usage
        try:
            with io.open(args.out, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        except (IOError, OSError) as exc:
            sys.stderr.write("sbe evidence run: the command ran but the receipt could not be "
                             "written to %s: %s. Treat the run as unrecorded.\n"
                             % (args.out, exc))
            return exit_failed
        level, why = trust_level(receipt)
        sys.stdout.write(
            "\nsbe evidence run: receipt written to %s. Trust %s (%s). Command exited %d in "
            "%.3fs, over %d covered file(s) from %s. Declared check kind(s): %s. stdout and "
            "stderr are recorded as digests only. argv held %d secret-shaped token(s) and "
            "%s.\n"
            % (args.out, level, why, receipt["exitCode"], receipt["durationSeconds"],
               len(receipt["coveredFiles"]), receipt["coveredFilesSource"],
               ", ".join(receipt["checkKinds"]) or "none, so this receipt clears no design, "
                                                  "gate or score obligation",
               receipt["argvRedactions"],
               "was recorded verbatim" if receipt["argvRedactions"] == 0
               else "was redacted before it was written"))
        # The wrapper's own exit code is the COMMAND's, so a failing command
        # cannot be laundered into a passing evidence step by the fact that a
        # receipt got written about it.
        return exit_failed if receipt["exitCode"] != 0 else exit_ok

    if args.sub == "verify":
        result = verify(args.receipt, cwd=os.path.abspath(args.cwd))
        if args.json:
            sys.stdout.write(json.dumps({
                "tool": "sbe evidence verify",
                "toolVersion": version(),
                "schemaVersion": EVIDENCE_SCHEMA_VERSION,
                "receipt": args.receipt,
                "verdict": result["verdict"],
                "trust": result["trust"],
                "trustWhy": result["trustWhy"],
                "inspected": result["inspected"],
                "reasons": result["reasons"],
            }, indent=2, sort_keys=True) + "\n")
        else:
            sys.stdout.write("%-8s %s\n" % (result["verdict"], args.receipt))
            sys.stdout.write("  inspected: %s\n" % "; ".join(result["inspected"]))
            if result["trust"]:
                sys.stdout.write("  trust:     %s (%s)\n" % (result["trust"],
                                                             result["trustWhy"]))
            for reason in result["reasons"]:
                sys.stdout.write("  %s\n" % reason)
        if result["verdict"] == "FAIL":
            return exit_failed
        if result["verdict"] == "NO-DATA" and args.strict:
            return exit_failed
        return exit_ok

    if args.sub == "show":
        try:
            receipt = load(args.receipt)
        except ReceiptUnreadable as exc:
            sys.stderr.write("sbe evidence show: %s\n" % exc)
            return exit_failed
        sys.stdout.write(render(receipt, args.receipt) + "\n")
        sys.stdout.write("\nsbe evidence show prints what the receipt SAYS. It checks nothing: "
                         "run `sbe evidence verify` for a verdict.\n")
        return exit_ok

    parser.print_help(sys.stderr)
    return exit_usage
