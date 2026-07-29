"""Install BrotherSBE's local footprint into a target repository: a config
file, a dossier directory, an optional copy of the consumer CI, and a receipt
naming exactly what was written and how to remove it.

Idempotent is the whole point. `sbe init --apply` run twice must change
nothing the second time, and say so, because an install step that silently
does something different on a rerun is a step nobody can trust in a script.
That works here because every proposal is DETERMINISTIC content (no
timestamp, no run id) compared byte for byte against what is already on
disk: the second run finds every proposal already matches and writes
nothing, and the receipt -- the one artifact that legitimately does carry a
timestamp -- is then left untouched rather than rewritten with a new one,
because nothing happened this run for it to describe.

`--dry-run` (the default, wired in cli.py) shows every intended mutation as a
diff and writes nothing; `--apply` writes. Refuses outside a git repository,
naming the reason, because there is nowhere for the config, the dossier
directory or the receipt to be versioned, and installing outside version
control is not this command's job to guess is wanted.
"""
import io
import json
import os
import subprocess
import time

from . import SCHEMA_VERSION, repo_root, version

CONFIG_PATH = ".brothersbe/config.json"
DOSSIER_MARKER = "design/.gitkeep"
RECEIPT_PATH = ".brothersbe/install-receipt.json"
GITIGNORE_PATH = ".gitignore"
#: One line above the ignore entry, explaining why it is there before a
#: reader has to go looking: the receipt records this machine's absolute
#: install path, a local, personal fact that has no business being tracked.
GITIGNORE_COMMENT = ("# sbe init: the install receipt below records this machine's absolute "
                     "path, so it stays out of git")
CONSUMER_WORKFLOW_PATH = ".github/workflows/consumer-check.yml"
CONSUMER_ACTION_PATH = ".github/actions/sbe-consumer/action.yml"

#: Where this installation's own copies of the consumer CI templates live,
#: relative to `repo_root()`. Read at plan time rather than duplicated as a
#: string constant in this module, so editing the shipped workflow or action
#: is the only place that content has to change.
_CONSUMER_WORKFLOW_SOURCE = ".github/workflows/consumer-check.yml"
_CONSUMER_ACTION_SOURCE = ".github/actions/sbe-consumer/action.yml"


class NotAGitRepository(Exception):
    """Raised rather than returning a silent no-op: an install with nowhere
    to be versioned is a different finding from an install that is already
    done, and folding them together would hide the reason from whoever reads
    the refusal."""


def _git(args, cwd):
    out = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True)
    return out.returncode, out.stdout, out.stderr


def _iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def refusal_reason(root):
    """None, or the reason `sbe init` must refuse this root outright."""
    code, out, err = _git(["rev-parse", "--is-inside-work-tree"], root)
    if code != 0 or out.strip() != "true":
        return ("%s is not inside a git repository (%s); sbe init refuses because there is "
                "nowhere for the config, the dossier directory or the install receipt to be "
                "versioned, and installing outside version control is not this command's "
                "job to guess is wanted"
                % (root, (err or out).strip() or "git could not answer"))
    return None


def _config_content():
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "tool": "sbe init",
        "toolVersion": version(),
        "dossierRoot": "design",
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _read_template(rel):
    """The content of one of this installation's own shipped files, or
    (None, reason) when it cannot be read. Read from `repo_root()`, the
    BrotherSBE installation running this command, which may be a different
    directory from the repository being initialized.
    """
    full = os.path.join(repo_root(), rel)
    try:
        with io.open(full, encoding="utf-8") as fh:
            return fh.read(), None
    except (IOError, OSError) as exc:
        return None, ("this installation carries no readable %s (%s), so the consumer CI "
                      "copy cannot be proposed" % (rel, exc))


def _gitignore_content(root):
    """The full `.gitignore` body this run proposes: whatever is already on
    disk, untouched, plus the receipt line and its comment appended when
    that line is not already present.

    Appending rather than owning the file is what makes this proposal
    compare identical, like every other one, against exactly what is
    already there: once the line exists this returns the file back
    unchanged, so a rerun reports it identical instead of proposing a
    second copy. It is also why `apply()` never lists `.gitignore` in the
    receipt's own written set -- this command only ever adds one line to a
    file it does not own, and an uninstall instruction to delete that file
    would take every other line in it too.
    """
    full = os.path.join(root, GITIGNORE_PATH)
    try:
        with io.open(full, encoding="utf-8") as fh:
            existing = fh.read()
    except (IOError, OSError):
        existing = None
    if existing is not None and RECEIPT_PATH in existing.splitlines():
        return existing
    prefix = existing or ""
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    return prefix + GITIGNORE_COMMENT + "\n" + RECEIPT_PATH + "\n"


def plan(root, with_consumer_ci=False):
    """The mutations `sbe init` would make, each compared against what is
    already on disk. Read-only: never writes, so `--dry-run` can call this
    directly.
    """
    mutations = [(CONFIG_PATH, _config_content()), (DOSSIER_MARKER, ""),
                (GITIGNORE_PATH, _gitignore_content(root))]
    warnings = []
    if with_consumer_ci:
        for rel, source in ((CONSUMER_WORKFLOW_PATH, _CONSUMER_WORKFLOW_SOURCE),
                            (CONSUMER_ACTION_PATH, _CONSUMER_ACTION_SOURCE)):
            content, problem = _read_template(source)
            if problem:
                warnings.append(problem)
            else:
                mutations.append((rel, content))

    proposals = []
    for rel, content in mutations:
        full = os.path.join(root, rel)
        exists = os.path.exists(full)
        existing = None
        if exists and os.path.isfile(full):
            try:
                with io.open(full, encoding="utf-8") as fh:
                    existing = fh.read()
            except (IOError, OSError, UnicodeDecodeError):
                existing = None
        identical = exists and existing == content
        proposals.append({"path": rel, "content": content, "exists": exists,
                          "identical": identical})
    return proposals, warnings


def _read_receipt(full):
    if not os.path.exists(full):
        return None
    try:
        with io.open(full, encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, IOError, OSError):
        return None


def apply(root, with_consumer_ci=False):
    """Write every non-identical proposal, then write or refresh the
    install receipt naming every artifact path this installation has
    written (across this call and any prior one the existing receipt
    recorded). Raises `NotAGitRepository` rather than writing anything when
    `root` is not inside a git repository.

    Returns a dict: `written` (the artifact paths actually written this
    call, plus the receipt path when the receipt itself changed), `skippedAsNoop`
    (True when nothing needed writing), `receipt` (the receipt content,
    whether freshly written or the one already on disk), `warnings` (why an
    optional proposal, like the consumer CI copy, could not be made).

    `.gitignore` is written like any other proposal when the receipt line is
    missing (so it shows up in `written`), but it never enters the receipt's
    `writtenPaths` or `uninstallInstructions`: this command appended one line
    to a file it does not own, and telling someone to `rm -f .gitignore`
    would delete every other line a real project keeps in that file.
    """
    reason = refusal_reason(root)
    if reason:
        raise NotAGitRepository(reason)

    proposals, warnings = plan(root, with_consumer_ci)
    written = []
    for item in proposals:
        if item["identical"]:
            continue
        full = os.path.join(root, item["path"])
        directory = os.path.dirname(full)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)
        with io.open(full, "w", encoding="utf-8") as fh:
            fh.write(item["content"])
        written.append(item["path"])

    receipt_full = os.path.join(root, RECEIPT_PATH)
    if not written:
        return {"written": [], "skippedAsNoop": True, "receipt": _read_receipt(receipt_full),
                "warnings": warnings}

    prior = _read_receipt(receipt_full) or {}
    prior_paths = list(prior.get("writtenPaths", []))
    # .gitignore is excluded here on purpose: it is a write this call made,
    # but not a file this installation owns, so it never enters the set an
    # uninstall instruction is generated from. See the docstring above.
    receipt_candidates = [p for p in written if p != GITIGNORE_PATH]
    all_written = prior_paths + [p for p in receipt_candidates if p not in prior_paths]
    # The receipt is itself a written file, so it names itself in the set it
    # records: uninstall instructions that omit the receipt are not exact.
    if RECEIPT_PATH not in all_written:
        all_written.append(RECEIPT_PATH)
    receipt = {
        "schemaVersion": SCHEMA_VERSION,
        "tool": "sbe init",
        "toolVersion": version(),
        "installedAt": _iso(time.time()),
        "installedInto": os.path.abspath(root),
        "writtenPaths": all_written,
        "uninstallInstructions": ["rm -f %s" % p for p in all_written],
    }
    directory = os.path.dirname(receipt_full)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with io.open(receipt_full, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    return {"written": written + [RECEIPT_PATH], "skippedAsNoop": False, "receipt": receipt,
           "warnings": warnings}
