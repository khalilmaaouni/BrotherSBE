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
import time

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

    THIS IS THE DEFAULT DELEGATE and it is used by every command that does not
    write a decision package. It never sees the child's output at all: the
    child's stdout IS this process's stdout. `delegate_teed` below is the only
    other one, it is used only on `verify`, `gate` and `score`, and the two are
    kept apart on purpose. Two delegates nobody can tell apart is how the
    streaming promise in the paragraph above gets quietly retracted.
    """
    path = _tool(tool_name)
    if not os.path.exists(path):
        sys.stderr.write("sbe: %s is missing from this installation; the command cannot "
                         "run and is not reporting a result\n" % path)
        return EXIT_USAGE
    return subprocess.call([sys.executable, path] + list(argv))


def delegate_teed(tool_name, argv):
    """Run a tool in tools/ and hand back ONE dict with keys `code` and `lines`:
    its exit code untouched, and a copy of the stdout lines it printed.

    Not a two-value tuple, deliberately: a pair-shaped return reads as a
    possible `(verdict, evidence)` pair to the honesty meta-test in
    `evals/test_no_data_class.py`, and this function is not a check.

    WHICH DELEGATE IS USED WHERE, AND WHY. `_delegate` above is the default and
    stays the default. This one is used ONLY where a decision package has to be
    written: `verify`, `gate` and `score`. A package quotes the verdict line the
    run printed, and the only place that line exists is the child's own output,
    so those three paths have to see it go by.

    IT STILL STREAMS, and that is the point of a tee rather than a capture:
    every line is written to `sys.stdout` and flushed AS IT ARRIVES, before the
    copy is kept, so somebody watching a long gate run sees exactly what they
    would have seen without the tee, at the same moment. A `subprocess.run(...,
    capture_output=True)` here would have been three lines shorter and would
    have held the whole report back until the tool exited.

    stderr is not touched: it is inherited, so a tool's errors reach the
    terminal directly and interleave the way they always did.
    """
    path = _tool(tool_name)
    if not os.path.exists(path):
        sys.stderr.write("sbe: %s is missing from this installation; the command cannot "
                         "run and is not reporting a result\n" % path)
        return {"code": EXIT_USAGE, "lines": []}
    lines = []
    child = subprocess.Popen([sys.executable, path] + list(argv),
                             stdout=subprocess.PIPE, universal_newlines=True)
    for line in child.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        lines.append(line.rstrip("\n"))
    child.stdout.close()
    return {"code": child.wait(), "lines": lines}


#: The flag that suppresses the automatic decision package. It is spelled once,
#: here, and stripped from the argv before the tool behind the command sees it,
#: because the tools refuse a flag they do not know rather than running past it.
NO_DECISIONS_FLAG = "--no-decisions"


def _split_decisions_flag(argv):
    """Take `--no-decisions` out of an argv, as ONE dict with keys `argv` (what
    the tool behind the command should actually be run with) and `suppressed`
    (whether the flag was there)."""
    kept = [a for a in argv if a != NO_DECISIONS_FLAG]
    return {"argv": kept, "suppressed": len(kept) != len(argv)}


def _checked_directory(argv):
    """The directory the delegated tool examined, read off the argv it was
    given, as a single path.

    The scanning tools take at most one directory and default to the current
    one, so this reads the argv the same way they do: the first argument that
    is not a flag and IS a directory wins, and with none, the current
    directory. Reading it here rather than asking the tool keeps this file from
    growing a second copy of anybody's argument parsing.
    """
    for arg in argv:
        if not arg.startswith("-") and os.path.isdir(arg):
            return os.path.abspath(arg)
    return os.path.abspath(".")


def _record_decisions(command, argv, lines, suppressed):
    """Write one decision package per FAIL and per WAIVED line the run printed,
    and SAY on stdout what was written, or why nothing was.

    THIS FUNCTION CANNOT MOVE A VERDICT OR AN EXIT CODE, and that is a
    structural property rather than a promise. It returns nothing at all, so
    there is no value for a caller to fold into an exit code; every caller
    returns the delegated tool's own code, computed before this is called; and
    every failure raised inside it, of any class, is caught here, printed here
    in full with the name of its exception class, and stops here. A gate that
    FAILED still FAILS with a broken decisions directory; a gate that passed is
    not failed by one either. The failure is never swallowed, because a
    bookkeeping failure nobody was told about would be worse than the missing
    package: the sentence printed on the way out says what was not recorded.
    """
    if suppressed:
        sys.stdout.write(
            "\nsbe %s: %s was passed, so no decision package was written for the verdict "
            "lines above. The verdicts themselves are unchanged; what is missing is the "
            "durable record of them, and this line is here so that absence is never "
            "silent.\n" % (command, NO_DECISIONS_FLAG))
        return
    try:
        from . import decisions as decisions_mod
    except ImportError as exc:
        sys.stdout.write(
            "\nsbe %s: no decision package was written: this installation carries no "
            "brothersbe.decisions (%s). The verdicts above stand and this command's exit "
            "code is unchanged.\n" % (command, exc))
        return
    target = _checked_directory(argv)
    try:
        written = decisions_mod.record_from_run(target, "\n".join(lines), target)
    except Exception as exc:
        # Deliberately every class, not only DecisionUnwritable. The rule this
        # obeys is that writing a package must never change what a gate
        # decided, and an exception class nobody anticipated would change it by
        # escaping. It is reported, in full, with its class named, so it is
        # visible rather than swallowed.
        sys.stdout.write(
            "\nsbe %s: no decision package was written: %s: %s. The verdicts above stand "
            "and this command's exit code is unchanged.\n"
            % (command, type(exc).__name__, exc))
        return
    if written:
        sys.stdout.write("\nsbe %s: %d decision package(s) written, one per FAIL and per "
                         "WAIVED line above:\n" % (command, len(written)))
        for path in written:
            sys.stdout.write("  %s\n" % path)
    else:
        sys.stdout.write(
            "\nsbe %s: 0 decision package(s) written: no FAIL and no WAIVED line was "
            "printed above. A package records a decision somebody has to carry, and a "
            "PASS or a NO-DATA is not one.\n" % command)


#: LT-202: normalized findings inside `11-review.json`. This sub-schema has
#: its OWN version tag, `findingsSchemaVersion`, deliberately separate from
#: the package-wide `SCHEMA_VERSION` above: that constant is shared by every
#: record type this package writes (plan, decisions, review, ...), and
#: bumping it to signal a change scoped to one field of one record would move
#: every other record type's stated version too, for a change none of them
#: made. `_FINDINGS_SCHEMA_VERSION` is the explicit migration path a review
#: record's OWN structured findings carry, read back by
#: `status._read_structured_findings`.
_FINDINGS_SCHEMA_VERSION = "1.0"

#: LANE B-006: the append-only file `_archive_prior_review` writes every
#: superseded `11-review.json` into, beside it, before a new `--write`
#: replaces it. Named once, here, so this write side and the read side
#: (`status._read_review_history`, which names the identical literal in its
#: own `_REVIEW_HISTORY_FILENAME`) cannot drift into two different ideas of
#: where history lives; the two modules do not import each other (neither
#: does today, for `11-review.json` itself, which every write and read site
#: in both files already names as its own literal), so this stays a literal
#: kept in step by name rather than a shared import.
_REVIEW_HISTORY_FILENAME = "11-review-history.jsonl"

_FINDING_CONFIDENCE = ("high", "medium", "low")
_FINDING_INTRODUCED = ("yes", "no", "unknown")
#: "arbitration" is deliberately absent: it is the one status a caller can
#: never supply, only ever the outcome deduplication assigns itself when two
#: sources contradict (see `_merge_finding_group`).
_FINDING_STATUS = ("open", "fixed", "accepted", "rejected")
_FINDING_REQUIRED_FIELDS = ("reviewer", "category", "severity", "confidence",
                            "introducedByChange", "failure")
_SEVERITY_RANK = {"critical": 3, "major": 2, "minor": 1, "info": 0}
_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}


def _finding_slug(text):
    """A lowercase, hyphen-joined, ASCII slug of `text`, truncated to 40
    characters: this project's own definition of a finding's "failure
    class" for fingerprinting (see `_finding_fingerprint`), and also used to
    fold a category or a conceptId into the same fingerprint alphabet. Pure
    and deterministic: the same `text` always slugs to the same string, in
    any process, so two findings describing the same failure in slightly
    different words (case, punctuation, surrounding space) still land on one
    fingerprint rather than minting a silent duplicate."""
    out = []
    prev_dash = True
    for ch in (text or "").strip().lower():
        if ch.isalnum() and ord(ch) < 128:
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")[:40].rstrip("-") or "unlabeled"


def _finding_normalize_path(path):
    """The path half of a `location`, normalized so `./src/a.py` and
    `src/a.py` fingerprint identically: backslashes folded to `/` (a
    Windows-authored findings file should not silently mint a second
    fingerprint for the same file this project only ever names with forward
    slashes), and a leading `./` dropped."""
    p = (path or "").strip().replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    return p


def _finding_split_location(location):
    """(normalized path, line-or-symbol) from a `"path:line"` or
    `"path:symbol"` string. Splits on the LAST colon, so a path that itself
    carries one (an absolute path is never produced by this project's own
    tools, but a hand-written findings file could still supply one) still
    separates correctly. A location with no colon at all is the whole
    string as a path with an empty line-or-symbol."""
    text = (location or "").strip()
    if ":" in text:
        path, _sep, tail = text.rpartition(":")
        return _finding_normalize_path(path), tail.strip()
    return _finding_normalize_path(text), ""


def _finding_fingerprint(category, location, failure):
    """The deterministic fingerprint LT-202 requires: category, the
    normalized path, the line or symbol, and a slug of the failure text (its
    failure class), joined with `:`. A pure function of exactly those three
    inputs, so the same (category, location, failure) always produces the
    same fingerprint, regardless of what order findings arrive in or how
    many times this runs; that is what makes identical-fingerprint
    deduplication in `_group_key` well defined rather than order-dependent."""
    path, line = _finding_split_location(location)
    return "%s:%s:%s:%s" % (_finding_slug(category), path or "unknown",
                            line or "-", _finding_slug(failure))


def _validate_raw_finding(entry, index):
    """A list of reasons `entry` (the `index`-th item of a `--findings-json`
    array) is not a trustworthy LT-202 finding, or `[]` when it is. Every
    reason names its own index, so a caller with many findings and one typo
    is told exactly which entry to fix rather than "something is wrong"."""
    if not isinstance(entry, dict):
        return ["finding[%d]: is not a JSON object" % index]
    errors = []

    def bad(msg):
        errors.append("finding[%d]: %s" % (index, msg))

    for field in _FINDING_REQUIRED_FIELDS:
        value = entry.get(field)
        if not isinstance(value, str) or not value.strip():
            bad("missing or empty required field %r" % field)
    concept_id = entry.get("conceptId")
    locations = entry.get("locations")
    location = entry.get("location")
    if concept_id:
        if not (isinstance(locations, list) and locations
               and all(isinstance(l, str) and l.strip() for l in locations)):
            bad("a conceptId finding needs a non-empty 'locations' list of strings, "
               "one per line the conceptual issue touches")
    elif not isinstance(location, str) or not location.strip():
        bad("missing or empty required field 'location' (or supply 'conceptId' with "
           "'locations' for one issue spanning several lines)")
    confidence = entry.get("confidence")
    if confidence not in _FINDING_CONFIDENCE:
        bad("confidence must be one of %s, got %r" % (_FINDING_CONFIDENCE, confidence))
    introduced = entry.get("introducedByChange")
    if introduced not in _FINDING_INTRODUCED:
        bad("introducedByChange must be one of %s, got %r"
           % (_FINDING_INTRODUCED, introduced))
    status = entry.get("status", "open")
    if status not in _FINDING_STATUS:
        bad("status must be one of %s, got %r ('arbitration' is reserved: this "
           "installation assigns it during deduplication and never accepts it as "
           "input)" % (_FINDING_STATUS, status))
    evidence = entry.get("evidence", [])
    if not isinstance(evidence, list) or not all(isinstance(e, str) for e in evidence):
        bad("evidence must be a list of strings")
    verification = entry.get("verification")
    if verification is not None and not isinstance(verification, str):
        bad("verification must be a string or null")
    disposition = entry.get("disposition")
    if disposition is not None and not isinstance(disposition, dict):
        bad("disposition must be an object or null")
    disposition = disposition or {}
    if status == "accepted":
        by, reason, scope = (disposition.get("by"), disposition.get("reason"),
                             disposition.get("scope"))
        if not (isinstance(by, str) and by.strip()):
            bad("status 'accepted' needs disposition.by naming the human accepting "
               "the risk")
        if not (isinstance(reason, str) and reason.strip()):
            bad("status 'accepted' needs disposition.reason")
        if not (isinstance(scope, str) and scope.strip()):
            bad("status 'accepted' needs disposition.scope")
        reviewer = entry.get("reviewer")
        if (isinstance(by, str) and isinstance(reviewer, str)
                and by.strip().lower() == reviewer.strip().lower()):
            bad("a reviewer can never accept its own risk: disposition.by (%r) is the "
               "same identity as this finding's own reviewer" % by)
    elif status == "rejected":
        refuting = disposition.get("evidence")
        ok = (isinstance(refuting, str) and refuting.strip()) or (
            isinstance(refuting, list) and refuting
            and all(isinstance(e, str) and e.strip() for e in refuting))
        if not ok:
            bad("status 'rejected' needs disposition.evidence (the refuting evidence), "
               "a string or a non-empty list of strings")
    elif status == "fixed":
        receipt = disposition.get("receipt")
        disp_verification = disposition.get("verification")
        has_proof = (
            (isinstance(verification, str) and verification.strip())
            or (isinstance(disp_verification, str) and disp_verification.strip())
            or (isinstance(receipt, str) and receipt.strip()))
        if not has_proof:
            bad("status 'fixed' needs a verification command (top-level "
               "'verification' or disposition.verification) or a linked receipt "
               "(disposition.receipt): no finding marks itself fixed without proof")
    return errors


def _finding_is_blocking(introduced, severity, confidence, verification):
    """LT-202's blocking rules as one predicate, so they are answered once
    rather than re-derived at every call site:

    - a finding pre-existing before this change (`introducedByChange` is not
      "yes") is never a change blocker: pre-existing issues are reported
      separately from change blockers;
    - `confidence == "low"` never blocks, at any severity: a low-confidence
      finding cannot block a merge. Taken here at its most conservative, for
      every low-confidence finding rather than only ones this schema could
      prove came from a model, because no field on a finding records
      per-finding human/model provenance to check the narrower reading
      against, and a schema cannot enforce a distinction it cannot observe;
    - only `severity == "critical"` can ever block; every other severity is
      an improvement to raise, never a blocker, in this schema;
    - a critical finding blocks only with `confidence == "high"` OR a
      non-empty `verification` command standing in for LT-202's "mechanical
      proof": a critical blocker requires high confidence or mechanical
      proof, and neither one alone downgrades it to a mere improvement, it
      stays recorded, just not blocking.
    """
    if introduced != "yes":
        return False
    if confidence == "low":
        return False
    if (severity or "").strip().lower() != "critical":
        return False
    return confidence == "high" or bool(verification and str(verification).strip())


def _finding_group_key(entry):
    """The key two raw findings must share to be deduplicated into one: an
    explicit `conceptId` (for one conceptual issue spanning several lines,
    grouped with its category so two different categories never collide on
    the same conceptId string) when given, else the LT-202 fingerprint
    itself (identical fingerprint -> one finding, LT-202's first
    deduplication rule)."""
    category = entry.get("category") or ""
    concept_id = entry.get("conceptId")
    if concept_id:
        return ("concept", _finding_slug(category), _finding_slug(concept_id))
    return ("fingerprint", _finding_fingerprint(category, entry.get("location") or "",
                                                entry.get("failure") or ""))


def _merge_finding_group(entries):
    """One structured LT-202 finding folded from `entries` (every raw
    finding that shared one `_finding_group_key`), applying every
    deduplication rule in order:

    - `sources` names every reviewer that reported it, `reviewer` staying
      the first for backward compatibility with a plain single-source
      reader;
    - a severity disagreement keeps the highest severity and sets
      `severityDisagreement` rather than silently picking one;
    - confidence is the HIGHEST any single source already claimed on its
      own, never boosted past that by how many sources agree: two "low"
      sources never become "medium" by vote count alone;
    - `introducedByChange` reads "yes" if any source says so (a possible
      regression is never hidden by a source that called it pre-existing),
      else "unknown" if any source is unsure, else "no";
    - a conceptId group's `locations` names every line; a fingerprint group
      keeps its own one location, still reachable through `locations` as a
      one-item list, so a reader never has to branch on which case it is;
    - a status disagreement that mixes two or more of fixed/accepted/
      rejected is never auto-merged: `status` becomes "arbitration" and
      `contradiction` carries each source's own status, evidence and
      disposition, in the same Finding/Evidence-for/Evidence-against shape
      `docs/CLI.md`'s adjudication protocol section documents, for a human
      or Fable to resolve. A single agreed non-open status (every source
      that stated one agrees, or only one source stated one at all) is kept
      outright: that is confirmation, not a vote-driven change.
    """
    first = entries[0]
    category = first.get("category")
    concept_id = first.get("conceptId")
    if concept_id:
        fingerprint = "%s:concept/%s" % (_finding_slug(category), _finding_slug(concept_id))
        locations = []
        for e in entries:
            for loc in e.get("locations") or []:
                if loc not in locations:
                    locations.append(loc)
        location = locations[0] if locations else ""
        failure = first.get("failure")
    else:
        location = first.get("location") or ""
        failure = first.get("failure") or ""
        fingerprint = _finding_fingerprint(category, location, failure)
        locations = [location]

    sources = []
    for e in entries:
        r = e.get("reviewer")
        if r and r not in sources:
            sources.append(r)

    severities = []
    for e in entries:
        s = e.get("severity")
        if s and s not in severities:
            severities.append(s)
    severity = max(severities, key=lambda s: _SEVERITY_RANK.get(s.strip().lower(), -1)) \
        if severities else first.get("severity")
    severity_disagreement = len(severities) > 1

    confidence = max((e.get("confidence") for e in entries),
                     key=lambda c: _CONFIDENCE_RANK.get(c, 0))

    introduced_values = set(e.get("introducedByChange") for e in entries)
    if "yes" in introduced_values:
        introduced = "yes"
    elif "unknown" in introduced_values:
        introduced = "unknown"
    else:
        introduced = "no"

    evidence = []
    for e in entries:
        for item in e.get("evidence") or []:
            if item not in evidence:
                evidence.append(item)

    verification = None
    for e in entries:
        v = e.get("verification")
        if v:
            verification = v
            break

    statuses = set((e.get("status") or "open") for e in entries)
    terminal = statuses & set(("fixed", "accepted", "rejected"))
    contradiction = None
    disposition = None
    if len(terminal) > 1:
        status = "arbitration"
        contradiction = [
            {"reviewer": e.get("reviewer"), "status": e.get("status") or "open",
             "evidence": e.get("evidence") or [], "disposition": e.get("disposition")}
            for e in entries]
    elif terminal:
        status = next(iter(terminal))
        for e in entries:
            if (e.get("status") or "open") == status and e.get("disposition"):
                disposition = e.get("disposition")
                break
    else:
        status = "open"

    # A finding pending arbitration is never a settled blocker: `blocking`
    # means "a merge gate should mechanically halt on this right now", and a
    # contradiction nobody has adjudicated yet is exactly the opposite of
    # settled. `status.py`'s own read of this field already treats
    # "arbitration" as its own, separately-reported NO-DATA case; letting
    # `blocking` also read True here would make a read-side gate FAIL a
    # change over a disagreement no human or Fable has resolved, before the
    # adjudication protocol (docs/CLI.md) ever ran.
    blocking = (status != "arbitration"
               and _finding_is_blocking(introduced, severity, confidence, verification))

    return {
        "fingerprint": fingerprint,
        "reviewer": sources[0] if sources else first.get("reviewer"),
        "sources": sources,
        "category": category,
        "severity": severity,
        "severityDisagreement": severity_disagreement,
        "confidence": confidence,
        "introducedByChange": introduced,
        "location": location,
        "locations": locations,
        "failure": failure,
        "evidence": evidence,
        "verification": verification,
        "status": status,
        "disposition": disposition,
        "blocking": blocking,
        "contradiction": contradiction,
    }


def normalize_review_findings(raw_entries):
    """(structured, errors) from `raw_entries` (the parsed JSON array a
    `--findings-json` file carries): deduplicated, LT-202-shaped findings,
    and every reason an entry could not be trusted. When `errors` is
    non-empty, `structured` is always `[]`: a caller can never write a
    record built from some valid and some rejected entries, the same "a
    refused write leaves no partial record" law `_cmd_review`'s own
    `--reviewer`/`--reviewer-type`/`--result` check already keeps.

    Deduplication groups every entry by `_finding_group_key` (identical
    fingerprint, or a shared `conceptId`) and folds each group through
    `_merge_finding_group`; see that function's docstring for the rules
    applied inside a fold. Group order is the order fingerprints (or
    conceptIds) are first seen in `raw_entries`, so the same input list
    always produces the same output order, independent of dict iteration
    order in this process.
    """
    if not isinstance(raw_entries, list):
        return [], ["findings-json: the top-level JSON value must be a list of findings"]
    errors = []
    for i, entry in enumerate(raw_entries):
        errors.extend(_validate_raw_finding(entry, i))
    if errors:
        return [], errors
    groups = {}
    order = []
    for entry in raw_entries:
        key = _finding_group_key(entry)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(entry)
    return [_merge_finding_group(groups[k]) for k in order], []


def _archive_prior_review(path, history_path):
    """Before `_record_review` opens `path` (`11-review.json`) for writing,
    preserve whatever it CURRENTLY holds by appending it, verbatim, as one
    line of the append-only `history_path` (`11-review-history.jsonl`)
    beside it. Returns True when something was archived, False when `path`
    did not exist yet: the ordinary first-ever-write case, where nothing has
    been overwritten, so nothing is appended.

    LANE B-006: a second `sbe review --write` at the same head used to
    overwrite `11-review.json` in place, silently erasing whatever verdict
    was there before, undetectable at the same head. This is the one place
    that catches a record BEFORE it is replaced: called once, immediately
    ahead of the write, from inside `_record_review`'s own try block, so any
    failure reading `path` or writing `history_path` here (a permission
    problem, for instance) is caught by that same handler and refuses the
    whole write, exactly the way a failure writing `path` itself already
    would. Nothing here swallows that failure into a quiet False: a write
    that could not be safely archived must never proceed to overwrite the
    one copy that DID exist, so an unreadable `path` raises rather than
    returning as if there were nothing to archive.

    Nothing is skipped when the existing file will not parse as JSON: the
    raw text is archived wrapped in a `{"corrupt": true, "raw": ...}` marker
    instead, so a record broken by some other means (a hand-edited file, a
    partial write from a crashed process) is still never silently lost by
    the write that follows it. `status._read_review_history` reads such an
    entry back as one more list item with no `headSha` or `result` of its
    own, which the one check that reads this file already treats as not
    participating in its same-head comparison, rather than as a reason to
    fail that check.
    """
    if not os.path.exists(path):
        return False
    raw = io.open(path, encoding="utf-8").read()  # OSError propagates: see docstring
    try:
        prior = json.loads(raw)
        entry = prior if isinstance(prior, dict) else {"corrupt": True, "raw": raw}
    except ValueError:
        entry = {"corrupt": True, "raw": raw}
    entry = dict(entry)
    entry["supersededAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with io.open(history_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return True


def _record_review(target, lines, args, structured_findings=None):
    """Write one durable review record, `11-review.json`, into the dossier at
    `target`, and SAY on stdout what was written.

    THIS FUNCTION CANNOT MOVE A VERDICT OR AN EXIT CODE, for exactly the
    reason `_record_decisions` states above and by the same construction: it
    returns nothing, the caller computed `worst` before ever calling this and
    returns that value unchanged no matter what happens here, and every
    failure raised inside it, of any class, is caught here, printed here in
    full with the name of its exception class, and stops here. A review run
    that FAILED still exits nonzero with no record written; a review that
    PASSED is not turned into a pass by one either.

    THE RECORD NEVER JUDGES ITSELF. Whether this review reads as a clean
    pass, a stale binding, or a reviewer approving their own change is worked
    out later, at read time, by `sbe status --team` (see `status.py`), from
    whatever this file actually says when that command runs; this function
    only persists what it was told, once, bound to the commit under review.

    `11-review.json` ITSELF is a POINTER, not the whole record, and every
    reader that already existed before LANE B-006 (this docstring's own
    earlier claim that a fresh review is "not an edit to the old one" was
    true of the FILE's meaning, never true of the bytes on disk: a second
    `--write` at the same head used to overwrite `path` in place with no
    trace of what it replaced) keeps reading exactly that pointer unchanged.
    What changed is what happens immediately before the overwrite:
    `_archive_prior_review` (above) preserves whatever `path` currently
    holds into the append-only `11-review-history.jsonl` beside it, so a
    verdict superseded by a later write is never gone, only superseded, and
    `sbe status --team` discloses a same-head, different-result supersession
    as its own named finding (see `status.py`'s history-disclosure block),
    itself worked out at read time, never by this write path, keeping THE
    RECORD NEVER JUDGES ITSELF true of the history too.

    `findings` is not taken as a flag: it is read back out of `lines`, the
    same stdout this run already printed, through the same
    `decisions.parse_verdict_lines` that packages FAIL and WAIVED lines into
    decision packages for `verify`. A human retyping what the tool already
    said would be a second, driftable copy of the same fact.

    `structured_findings`, when not `None`, is the LT-202 output of
    `normalize_review_findings` (already validated and deduplicated by
    `_cmd_review` before this ever runs): it is written into two ADDITIONAL
    fields, `findingsSchemaVersion` and `structuredFindings`, beside every
    field this record already carried. `findings` (the raw FAIL/WAIVED
    verdict lines above) is never replaced or renamed: LT-202's own rule is
    that a review record may preserve the original raw verdict lines beside
    the structured ones for traceability, not instead of them. `None` (the
    default, and what every call site that never passed `--findings-json`
    still gets) omits both new fields entirely, so a record written without
    `--findings-json` is byte-for-byte what CR-09 already wrote: no reader of
    an old record sees a field it does not understand.
    """
    try:
        try:
            from . import decisions as decisions_mod
        except ImportError:
            decisions_mod = None
        findings = []
        if decisions_mod is not None:
            parsed = decisions_mod.parse_verdict_lines("\n".join(lines))
            findings = [v["line"] for v in parsed["verdicts"]
                       if v["verdict"] in ("FAIL", "WAIVED")]

        git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=os.path.abspath(target),
                             capture_output=True, text=True)
        if git.returncode != 0 or not git.stdout.strip():
            sys.stdout.write(
                "\nsbe review: no review record was written: the reviewed commit could "
                "not be resolved (%s). A record with no bound commit could never be "
                "checked for staleness later, so none was written. The verdicts above "
                "stand and this command's exit code is unchanged.\n"
                % (git.stderr.strip() or "git rev-parse HEAD failed"))
            return
        head_sha = git.stdout.strip()

        record = {
            "schemaVersion": SCHEMA_VERSION,
            "tool": "sbe review",
            "dossier": os.path.abspath(target),
            "headSha": head_sha,
            "reviewer": args.reviewer,
            "reviewerType": args.reviewer_type,
            "result": args.result,
            "findings": findings,
            "acceptedRisks": list(args.accept_risk or []),
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if structured_findings is not None:
            record["findingsSchemaVersion"] = _FINDINGS_SCHEMA_VERSION
            record["structuredFindings"] = structured_findings
        path = os.path.join(os.path.abspath(target), "11-review.json")
        history_path = os.path.join(os.path.abspath(target), _REVIEW_HISTORY_FILENAME)
        # LANE B-006: archive whatever `path` currently holds BEFORE it is
        # overwritten below. Must run before the `io.open(path, "w", ...)`
        # that follows: that call truncates `path` the instant it opens, so
        # archiving after it would have nothing left to archive.
        archived = _archive_prior_review(path, history_path)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(record, indent=2, sort_keys=True) + "\n")
    except Exception as exc:
        # Deliberately every class, for the same reason `_record_decisions`
        # gives: an exception class nobody anticipated would move a verdict by
        # escaping. It is reported in full, with its class named, never
        # swallowed.
        sys.stdout.write(
            "\nsbe review: no review record was written: %s: %s. The verdicts above "
            "stand and this command's exit code is unchanged.\n"
            % (type(exc).__name__, exc))
        return
    struct_note = ""
    if structured_findings is not None:
        struct_note = ", %d structured finding(s)" % len(structured_findings)
    history_note = (", 1 prior record archived to %s" % history_path) if archived else ""
    sys.stdout.write(
        "\nsbe review: review record written, bound to head %s, %d finding(s) and %d "
        "accepted risk(s)%s%s:\n  %s\n"
        % (head_sha[:12], len(findings), len(record["acceptedRisks"]), struct_note,
           history_note, path))


def _record_tier_decision(root, data, intake_path, machine_readable):
    """Write ONE decision package when an impact run raised a tier or read a
    disposition, and say where it landed.

    THIS FUNCTION CANNOT MOVE A VERDICT OR AN EXIT CODE, for exactly the reasons
    `_record_decisions` above states and by exactly the same construction: it
    returns nothing at all, so there is no value for a caller to fold into an
    exit code; the caller invokes it as a bare statement and returns the code it
    computed from the report; and every failure raised inside it, of any class,
    is caught here, printed here with its exception class named, and stops here.
    A REVIEW-REQUIRED impact still exits 1 with a broken decisions directory.

    NOTHING IS PRINTED WHEN NOTHING WAS DECIDED. `record_tier_decision` returns
    None for a run that raised no tier and disposed of nothing, and an empty
    package, or a line announcing one, would both claim a decision that never
    happened. That is the one difference from `_record_decisions`, which is
    watching a run that always decided something.

    WHERE THE SENTENCE GOES. Under `--json`, stdout is a document a caller
    parses, so the sentence is written to stderr instead: a human line appended
    to that document would break every one of those callers. Without `--json`
    it goes to stdout beside the report it describes.
    """
    stream = sys.stderr if machine_readable else sys.stdout
    try:
        from . import decisions as decisions_mod
    except ImportError as exc:
        stream.write("\nsbe impact: no decision package was written: this installation "
                     "carries no brothersbe.decisions (%s). The verdict above stands and "
                     "this command's exit code is unchanged.\n" % exc)
        return
    dossier = os.path.dirname(os.path.abspath(intake_path)) if intake_path else None
    try:
        written = decisions_mod.record_tier_decision(root, data, dossier)
    except Exception as exc:
        # Deliberately every class, for the reason `_record_decisions` gives:
        # an exception class nobody anticipated would change a verdict by
        # escaping. It is reported in full, with its class named, never
        # swallowed.
        stream.write("\nsbe impact: no decision package was written: %s: %s. The verdict "
                     "above stands and this command's exit code is unchanged.\n"
                     % (type(exc).__name__, exc))
        return
    if written:
        stream.write("\nsbe impact: decision package written, because this run raised a tier "
                     "or read a disposition: %s\n" % written)


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


def _mint_evidence(target, delegates):
    """Mint one evidence receipt per delegate `_cmd_verify` already ran, into
    the store `sbe status` already reads (`.sbe/evidence`,
    `tasks.DEFAULT_EVIDENCE_DIR`), and say on stderr when any could not be
    written.

    `delegates` is `(tool, flags, kind)` triples: `tool` and `flags` are the
    same two `_cmd_verify` already passed to `delegate_teed` for the live,
    streamed run above (`flags` excludes the target path itself; it is added
    back here against the ABSOLUTE target, never the string the caller may
    have typed relative to some other directory, because the receipt's own
    subprocess runs with its cwd set to the target for the git binding
    `evidence.generate` performs, and a relative path would resolve against
    the wrong directory there); `kind` is the `evidence.CHECK_KIND_NAMES`
    obligation that delegate's receipt is declared against.

    CALLED BEFORE `_record_decisions`, deliberately, though both write into
    `target`. `evidence.generate` reads `git status --porcelain` to decide
    whether each receipt is clean or dirty; minting first means that read
    sees the tree exactly as the caller of `sbe verify` left it, not a tree
    `_record_decisions` has already added an uncommitted decision package
    to. `evidence.mint_default_many`, which does the actual minting, has the
    matching within-itself property: every receipt is generated before any
    of them is written, so the first receipt's own file can never be read as
    the reason the second one looks dirty. See that function's docstring for
    why both orderings matter.

    THIS FUNCTION CANNOT MOVE A VERDICT OR AN EXIT CODE, for exactly the
    reason `_record_decisions` states below and by the same construction: it
    returns nothing, the caller computed `worst` before ever calling this and
    returns that value unchanged no matter what happens here, and every
    failure raised inside it, of any class, is caught here rather than
    escaping. A gate that FAILED still FAILS with no evidence store writable;
    a gate that passed is not failed by an unwritable one either.

    EACH DELEGATE IS RUN AGAIN, through `evidence.generate` (by way of
    `mint_default_many`), which is this module's own law stated in
    `evidence.py`: a receipt has to observe an actual run, never restate one
    this function already watched happen via `delegate_teed` above. The
    three checks this covers are read-only (`sbe_gate.py`, `sbe_design.py`
    and `sbe_score.py` each promise "writes: nothing"), so the second run
    costs time, not correctness, and it is the price of minting through the
    evidence module's own writer instead of `cli.py` fabricating a receipt
    from output it already captured.

    A receipt made against a dirty target is still written, and still reads
    NO-DATA naming the dirty state when read back through `evidence.verify`
    or `sbe status`: that is the law this stage is built around, not a bug
    (see `design/lifecycle-blockers/03-adr.md`, CR-08). Nothing here softens
    that; it only runs the command and writes down what happened.
    """
    try:
        from . import evidence as evidence_mod
        from . import tasks as tasks_mod
    except ImportError as exc:
        sys.stderr.write(
            "sbe verify: no evidence was minted: this installation carries no "
            "brothersbe.evidence or brothersbe.tasks (%s). The verdict lines above stand "
            "and this command's exit code is unchanged.\n" % exc)
        return
    abs_target = os.path.abspath(target)
    evidence_dir = os.path.join(abs_target, tasks_mod.DEFAULT_EVIDENCE_DIR)
    pairs = [(kind, [sys.executable, _tool(tool)] + list(flags) + [abs_target])
            for tool, flags, kind in delegates]
    try:
        written, failures = evidence_mod.mint_default_many(abs_target, pairs, evidence_dir)
    except Exception as exc:
        # Deliberately every class, for the reason `_record_decisions` gives: an
        # exception class nobody anticipated would change verify's exit code by
        # escaping.
        sys.stderr.write(
            "sbe verify: no evidence was minted: %s: %s. The verdict lines above stand and "
            "this command's exit code is unchanged.\n" % (type(exc).__name__, exc))
        return
    if failures:
        # ONE line for however many of the three did not mint, never one line
        # per kind, so a shared root cause (an unwritable evidence store) reads
        # as one sentence rather than three near-identical ones.
        sys.stderr.write(
            "sbe verify: %d of %d evidence receipt(s) were not minted (%s). The verdict "
            "lines above stand and this command's exit code is unchanged.\n"
            % (len(failures), len(pairs),
               "; ".join("%s: %s: %s" % (k, type(e).__name__, e) for k, e in failures)))
    if written:
        sys.stdout.write(
            "\nsbe verify: %d evidence receipt(s) minted into %s, one per delegate this run "
            "already ran:\n" % (len(written), evidence_dir))
        for path in written:
            sys.stdout.write("  %s\n" % path)


def _cmd_verify(args):
    """The gates, in the order a reader wants them: design completeness first
    (an incomplete dossier makes every later verdict less meaningful), then the
    hard gates, then the scored surface.

    Also mints one evidence receipt per delegate below (design, gate, score),
    written into `.sbe/evidence` so `sbe status` has proof of this run to read
    instead of reporting MISSING EVIDENCE about a check that just happened
    (CR-08, `design/lifecycle-blockers/03-adr.md`). See `_mint_evidence` for
    why that write can never move `worst` or this command's exit code, and
    for why it runs BEFORE `_record_decisions` even though both write into
    the same target directory.
    """
    target = args.path
    if not os.path.isdir(target):
        sys.stderr.write("sbe verify: '%s' is not a directory. A mistyped path must not "
                         "read as a clean scan.\n" % target)
        return EXIT_USAGE
    worst = EXIT_OK
    lines = []
    # (tool script, its flags before the target path, the evidence kind its
    # receipt is minted under below). The target path is deliberately not
    # baked in here: the loop below appends it verbatim for the live,
    # streamed run, and `_mint_evidence` appends the absolute form for the
    # receipt run, and each needs its own copy for the reason stated there.
    delegates = (("sbe_design.py", ["--strict"], "design"),
                ("sbe_gate.py", [], "gate"),
                ("sbe_score.py", ["--strict"], "score"))
    for tool, flags, _kind in delegates:
        result = delegate_teed(tool, list(flags) + [target])
        lines.extend(result["lines"])
        if result["code"] != EXIT_OK:
            worst = EXIT_CONTROL_FAILED
    # Minting evidence BEFORE recording decisions, though both write into
    # `target`: see `_mint_evidence`'s own docstring for why the order is
    # load-bearing rather than arbitrary. Both run before the closing
    # caveat, so that caveat stays the last line a reader sees, which is the
    # promise `_closing_caveat` makes in its own docstring.
    _mint_evidence(target, delegates)
    _record_decisions("verify", [target], lines, args.no_decisions)
    _closing_caveat("verify", worst)
    return worst


def _cmd_review(args):
    """What a reviewer runs before writing a word: the scored surface including
    the soft findings, plus the hard gates. Soft findings are shown because a
    soft FAIL is still a finding; it only means the exit code does not block.

    `--write` additionally persists a durable review record, `11-review.json`,
    into the dossier: reviewer, reviewer type, verdict, the FAIL and WAIVED
    lines this run actually printed, and any accepted risks, bound to the
    commit under review. Without `--write`, `review` still only prints,
    exactly as it always did. See `_record_review`'s own docstring for why
    that write can never move `worst` or this command's exit code; the
    construction is the same one `_record_decisions` uses for `verify`.

    `--findings-json <path>` additionally normalizes and deduplicates a JSON
    array of LT-202 findings (see `normalize_review_findings`) and persists
    the result as `structuredFindings`, beside the raw verdict lines
    `--write` already records. It is read and validated HERE, before either
    delegate below ever runs: an unreadable file or a finding that fails
    validation refuses the whole command at `EXIT_USAGE`, the same "a
    refused write leaves no partial record" law the `--reviewer`/
    `--reviewer-type`/`--result` check just above already keeps, and for the
    same reason: a `sbe_score.py`/`sbe_gate.py` run neither of them needed
    would otherwise happen before the refusal, costing time for a write that
    was never going to succeed.
    """
    target = args.path
    if not os.path.isdir(target):
        sys.stderr.write("sbe review: '%s' is not a directory.\n" % target)
        return EXIT_USAGE
    structured_findings = None
    if args.write:
        missing = [flag for flag, value in (
            ("--reviewer", args.reviewer),
            ("--reviewer-type", args.reviewer_type),
            ("--result", args.result)) if not value]
        if missing:
            sys.stderr.write(
                "sbe review: --write also needs %s: a review record with an unstated "
                "field is not a record, it is a guess.\n" % ", ".join(missing))
            return EXIT_USAGE
        if args.findings_json:
            try:
                raw = json.loads(io.open(args.findings_json, encoding="utf-8").read())
            except (OSError, ValueError) as exc:
                sys.stderr.write(
                    "sbe review: --findings-json '%s' could not be read: %s: %s. No "
                    "review record was written.\n"
                    % (args.findings_json, type(exc).__name__, exc))
                return EXIT_USAGE
            structured_findings, errors = normalize_review_findings(raw)
            if errors:
                sys.stderr.write(
                    "sbe review: --findings-json rejected, no review record was "
                    "written:\n")
                for reason in errors:
                    sys.stderr.write("  %s\n" % reason)
                return EXIT_USAGE
    worst = EXIT_OK
    lines = []
    for tool, argv in (("sbe_score.py", ["--strict", "--strict-soft", target]),
                       ("sbe_gate.py", [target])):
        result = delegate_teed(tool, argv)
        lines.extend(result["lines"])
        if result["code"] != EXIT_OK:
            worst = EXIT_CONTROL_FAILED
    # Before the closing caveat, so that caveat stays the last line a reader
    # sees (the promise `_closing_caveat` makes in its own docstring), and
    # after `worst` is fully computed, so a write here can never be the thing
    # that decides what this command's exit code is.
    if args.write:
        _record_review(target, lines, args, structured_findings)
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

    # FAIL, never NO-DATA and never a silent PASS: B-010. The marketplace
    # install path never runs `sbe init`, so a beginner's first
    # `/brothersbe:start` used to land in a repository with no local
    # footprint and nothing here ever said so; Guided mode read `doctor`'s
    # overall `result` as PASS while the main capability (dossiers, gates,
    # evidence, everything `sbe design`/`sbe gate`/`sbe verify` need) could
    # not run at all. This check makes that state REQUIRED-and-missing: a
    # FAIL, exactly like `tools` and `plugin-manifest` above, so it joins
    # the same `failed` list `_cmd_doctor` already computes below and the
    # overall JSON `result` can never read PASS while the footprint is
    # absent. See `initcmd.CONFIG_PATH` for the file this checks and `sbe
    # init` for the fix (preview, then `--apply` once approved).
    from . import initcmd
    footprint = os.path.join(os.getcwd(), initcmd.CONFIG_PATH)
    if os.path.exists(footprint):
        out.append(("project-init", "PASS",
                    "%s is present; this repository carries BrotherSBE's local footprint"
                    % initcmd.CONFIG_PATH))
    else:
        out.append(("project-init", "FAIL",
                    "%s is missing: this repository has never run `sbe init`, so "
                    "BrotherSBE's main capability (dossiers, gates, evidence) cannot run "
                    "here. REQUIRED-and-missing: preview the fix with `sbe init`, then "
                    "apply it with `sbe init --apply` once you approve the preview"
                    % initcmd.CONFIG_PATH))

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
    # A bare statement, before the exit code is computed from `data` below and
    # with no value flowing out of it: a raised or disposed tier is one of the
    # four moments that write a package, and writing one may not move what this
    # command decided. See `_record_tier_decision`.
    _record_tier_decision(os.path.abspath(args.path), data, args.intake, args.json)
    if data["verdict"] in ("REVIEW-REQUIRED", "FAIL"):
        return EXIT_CONTROL_FAILED
    if data["verdict"] == "NO-DATA" and args.strict:
        # NO-DATA never decides an exit code on its own. The only NO-DATA that
        # blocks a --strict run is one where this tool actually holds something
        # nobody declared: detector hits proposing a tier above T0 with no
        # intake to reconcile them against. (An unreadable diff blocks too, in
        # the DiffUnavailable branch above.) A NO-DATA whose derived answers
        # are all at their lowest values, a docs or data only diff no detector
        # covers, exits 0: grading that absence failed every such pull request.
        if data["proposedTier"] != "T0":
            return EXIT_CONTROL_FAILED
        sys.stderr.write(
            "sbe impact: NO-DATA under --strict, exit 0. Nothing was detected and every "
            "derived answer is at its lowest value, so there is nothing here for "
            "strictness to grade. A NO-DATA carrying detector hits, or an unreadable "
            "diff, still exits 1.\n")
    return EXIT_OK


def _cmd_review_route(args):
    """Deterministic reviewer selection from a diff: no model chooses, at
    most two specialists, and zero is a legal result. See
    `brothersbe.reviewroute` for the routing table and every detector.
    """
    if not os.path.isdir(args.path):
        sys.stderr.write("sbe review-route: '%s' is not a directory. A mistyped path must "
                         "not read as a clean scan.\n" % args.path)
        return EXIT_USAGE
    from . import reviewroute as reviewroute_mod
    try:
        data = reviewroute_mod.route(args.path, base=args.base, head=args.head,
                                     work_profile=args.work_profile)
    except reviewroute_mod.DiffUnavailable as exc:
        data = reviewroute_mod.no_data_report(args.path, exc)
    if args.json:
        sys.stdout.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(reviewroute_mod.render(data))
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


def _cmd_handover(args):
    """Explicit human handover: `prepare`, `show`, `acknowledge`, `reject`.

    Not a delegation: like `evidence`, `task` and `work`, there is no tool in
    `tools/` behind it. `prepare` derives what it can from the status-team
    report, the task registry, the plan, evidence receipts, convergence,
    approval and review, binds to HEAD, and writes `12-handover.json`
    atomically; ownership stays with the outgoing owner until a named human
    receiver runs `acknowledge`.
    """
    from . import handover as handover_mod
    return handover_mod.main(args.rest, exit_ok=EXIT_OK, exit_failed=EXIT_CONTROL_FAILED,
                             exit_usage=EXIT_USAGE)


def _cmd_explain(args):
    """Browse a decision package, or regenerate one from the shipped registry.

    Not a delegation: like `evidence`, `task` and `work`, there is no tool in
    `tools/` behind it. It READS the decision store; the only file it can create
    is a NEW package under the next id, written through the one writer in
    `brothersbe.decisions`, which refuses to overwrite a package bound to a
    different commit.
    """
    from . import decisions as decisions_mod
    return decisions_mod.main(args.rest, exit_ok=EXIT_OK, exit_failed=EXIT_CONTROL_FAILED,
                              exit_usage=EXIT_USAGE)


def _cmd_lineage(args):
    """Walk the chain for one artifact, oldest to newest, one evidence pointer
    per hop.

    Not a delegation: like `explain`, there is no tool in `tools/` behind it.
    It READS the task registry, the evidence store, the decision store, the
    notes store and `git log --follow`, writes nothing, and renders every
    absent store as a NO-DATA hop rather than a shorter chain. It lives in
    `brothersbe.decisions` because a lineage is read out of the same stores
    the decision packages are written into.
    """
    from . import decisions as decisions_mod
    return decisions_mod.main(args.rest, exit_ok=EXIT_OK, exit_failed=EXIT_CONTROL_FAILED,
                              exit_usage=EXIT_USAGE, surface="lineage")


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


def _cmd_program(args):
    """Program-wide truth from the ledger, the way `status` answers it for one
    change: read from `program/PROGRAM.yaml` and `program/work-items/`, never
    computed fresh over source code. See `brothersbe.program` for the kill
    criterion and the honesty rule that a status word never becomes a
    percentage. `status` renders (or with --write regenerates STATUS.md between
    its markers); `check` exits 1 when the committed STATUS.md no longer
    matches a fresh render, so drift fails a gate instead of aging quietly.
    """
    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        sys.stderr.write("sbe program: '%s' is not a directory. A mistyped path must not "
                         "read as a clean scan.\n" % root)
        return EXIT_USAGE
    from . import program as program_mod

    if args.action == "check":
        try:
            fresh = program_mod.check_status_md(root)
        except program_mod.ProgramParseError as exc:
            sys.stderr.write("sbe program check: %s\n" % exc)
            return EXIT_CONTROL_FAILED
        if fresh:
            sys.stdout.write("program STATUS.md matches a fresh render\n")
            return EXIT_OK
        sys.stdout.write("program STATUS.md is stale or unwritable from its sources; "
                         "regenerate with: sbe program status --write\n")
        return EXIT_CONTROL_FAILED

    try:
        report = program_mod.build_program_report(root)
    except program_mod.ProgramParseError as exc:
        sys.stderr.write("sbe program: %s\n" % exc)
        return EXIT_CONTROL_FAILED
    if args.write:
        try:
            program_mod.write_status_md(root, report)
        except program_mod.ProgramParseError as exc:
            sys.stderr.write("sbe program: %s\n" % exc)
            return EXIT_CONTROL_FAILED
        sys.stdout.write("wrote %s\n" % os.path.join(root, program_mod.STATUS_MD_REL))
        return EXIT_OK
    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(program_mod.render_status_md(report) + "\n")
    return EXIT_OK


def _cmd_map(args):
    """A deterministic, offline HTML status page, built from canonical state
    only. Not a delegation: like `evidence`, `task`, `work` and `handover`,
    there is no tool in `tools/` behind it. See `brothersbe.mapgen` for the
    three sources it reads (the status module's team report, the task
    registry, dossier artifact presence) and why it never parses anyone's
    rendered prose to fill a slot.
    """
    from . import mapgen as mapgen_mod
    return mapgen_mod.main(args.rest, exit_ok=EXIT_OK, exit_failed=EXIT_CONTROL_FAILED,
                           exit_usage=EXIT_USAGE)


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


def _cmd_gate(args):
    """The hard gates, teed so the FAIL and WAIVED lines they print become
    decision packages. Still a delegation: `tools/sbe_gate.py` owns every
    verdict, this wrapper adds no check and changes no exit code."""
    split = _split_decisions_flag(args.rest)
    result = delegate_teed("sbe_gate.py", split["argv"])
    _record_decisions("gate", split["argv"], result["lines"], split["suppressed"])
    return result["code"]


def _cmd_score(args):
    """The scored surface, teed for the same reason `gate` is, and with the
    same guarantee: `tools/sbe_score.py` owns the verdicts and the exit code."""
    split = _split_decisions_flag(args.rest)
    result = delegate_teed("sbe_score.py", split["argv"])
    _record_decisions("score", split["argv"], result["lines"], split["suppressed"])
    return result["code"]


def _cmd_version(args):
    """Print the version, or, with `bump <new>`, move every declaration site
    at once (versionbump.py owns the refusals and the re-read proof)."""
    rest = list(getattr(args, "rest", []) or []) if args is not None else []
    if rest:
        from . import versionbump as versionbump_mod
        return versionbump_mod.main(rest, exit_ok=EXIT_OK, exit_failed=EXIT_CONTROL_FAILED,
                                    exit_usage=EXIT_USAGE)
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
    ("gate", "one hard gate by name, or all of them over a directory", _cmd_gate),
    ("score", "the scored surface (delegates to sbe_score.py)", _cmd_score),
    ("intake", "score the five intake questions into a tier",
     lambda a: _delegate("sbe_intake.py", a.rest)),
    ("decide", "run a decision table (delegates to sbe_decide.py)",
     lambda a: _delegate("sbe_decide.py", a.rest)),
    ("fences", "print the live fences the write hook would enforce",
     lambda a: _delegate("sbe_fence_hook.py", ["fences"] + list(a.rest))),
    ("version", "print the version, or move every version declaration site at once "
                "(version bump <new>)", _cmd_version),
    ("impact", "read the git diff and reconcile it with the declared intake tier", _cmd_impact),
    ("inspect-change", "alias of impact, the name the finalization brief uses", _cmd_impact),
    ("review-route", "deterministic reviewer selection from a diff: no model chooses, at most "
                     "two specialists, zero is a legal result, never claims a clean review",
     _cmd_review_route),
    ("plan", "derive the task plan from a dossier and validate it (delegates to sbe_plan.py)",
     lambda a: _delegate("sbe_plan.py", a.rest)),
    ("instruction-surface", "did a changed CLAUDE.md, .claude/**, .mcp.json, .claude-plugin/**, "
                            "hooks/**, agent or skill definition, CODEOWNERS or CI workflow stay "
                            "inside declared, reviewed scope (delegates to "
                            "sbe_instruction_surface.py)",
     lambda a: _delegate("sbe_instruction_surface.py", a.rest)),
    ("evidence", "run a command and write the receipt it earned, verify one, or show one",
     _cmd_evidence),
    ("task", "the write-scope registry: open, list, fence, check, and close with the "
             "diff-against-declaration postcondition", _cmd_task),
    ("work", "isolated implementation for one plan task: start, check, finish, remove, "
             "and never a merge", _cmd_work),
    ("handover", "explicit human handover: prepare, show, acknowledge, reject; ownership "
                "stays with the outgoing owner until a named human receiver acknowledges",
     _cmd_handover),
    ("converge", "does the code between two commits still match the approved dossier: "
                 "scope, contracts, data, architecture, verification", _cmd_converge),
    ("pr", "pull-request surfaces: pr verify <number> --repo owner/name checks live "
           "GitHub approval evidence, bound to the head commit", _cmd_pr),
    ("explain", "print the decision package for a decision id, or for a gate or check name, "
                "regenerating one from the shipped registry when no run has written it",
     _cmd_explain),
    ("lineage", "walk the chain for one artifact oldest to newest: binding, receipts, "
                "decisions, notes and commits, with an evidence pointer on every hop",
     _cmd_lineage),
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
    ("map", "a deterministic, offline HTML status page built from canonical state only: "
            "sbe map --out FILE",
     _cmd_map),
    ("program", "program-wide status from the ledger: gantt, finished, in flight, blocked, "
                "risks with mitigations, docs, budget; `check` fails when STATUS.md drifted",
     _cmd_program),
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
    "evidence", "task", "work", "handover", "pr", "explain", "lineage",
    "instruction-surface", "map"))


def build_parser():
    epilog = "commands:\n" + "".join(
        "  %-21s %s\n" % (name, help_) for (name, help_, _) in COMMANDS)
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
        elif name == "review-route":
            child.add_argument("path", nargs="?", default=".",
                               help="the repository or dossier to route (default: the "
                                    "current one)")
            child.add_argument("--base", default=None,
                               help="the commit or ref to diff from; without it the merge "
                                    "base with the default branch is used, exactly as in "
                                    "`sbe impact`")
            child.add_argument("--head", default="HEAD", help="the commit or ref to diff to")
            child.add_argument("--work-profile", dest="work_profile", default=None,
                               choices=("backend", "data", "infrastructure", "migration",
                                        "qa", "documentation"),
                               help="the task's declared workProfile, if any; recorded in "
                                    "the reasons for provenance and does not change which "
                                    "reviewer is selected, because the priority table "
                                    "already orders every trigger a diff can raise")
            child.add_argument("--json", action="store_true", help="machine-readable output")
        elif name in ("verify", "review"):
            child.add_argument("path", nargs="?", default=".",
                               help="the directory to check (default: the current one)")
            if name == "verify":
                # `review` does not take this flag: NO_DECISIONS_FLAG suppresses
                # the decision package `_record_decisions` writes per FAIL and
                # WAIVED line, and `review` has never called
                # `_record_decisions`. That stays true now that `review` can
                # write `11-review.json` with `--write`: a decision package
                # and a review record are two different artifacts, and
                # suppressing the first would say nothing about the second.
                child.add_argument(NO_DECISIONS_FLAG, dest="no_decisions",
                                   action="store_true",
                                   help="do not write a decision package for the FAIL and "
                                        "WAIVED lines below; the suppression is printed, "
                                        "never silent")
            else:
                child.add_argument("--write", action="store_true",
                                   help="persist a durable review record, "
                                        "11-review.json, into the dossier; requires "
                                        "--reviewer, --reviewer-type and --result. "
                                        "Without --write, review only prints, exactly "
                                        "as before")
                child.add_argument("--reviewer", default=None,
                                   help="who is reviewing (a name, login or email); "
                                        "required with --write")
                child.add_argument("--reviewer-type", dest="reviewer_type",
                                   default=None,
                                   choices=("human", "model", "independent-model"),
                                   help="what kind of reviewer this is; required with "
                                        "--write")
                child.add_argument("--result", default=None,
                                   choices=("approved", "changes-required",
                                            "unverifiable"),
                                   help="the reviewer's verdict on this change; "
                                        "required with --write")
                child.add_argument("--accept-risk", dest="accept_risk",
                                   action="append", default=[],
                                   help="a risk the reviewer is knowingly accepting "
                                        "despite a finding; repeat for more than one")
                child.add_argument("--findings-json", dest="findings_json",
                                   default=None,
                                   help="a JSON file: a list of LT-202 findings "
                                        "(reviewer, category, severity, confidence, "
                                        "introducedByChange, location, failure, and "
                                        "optionally evidence/verification/status/"
                                        "disposition/conceptId) to normalize, "
                                        "deduplicate and persist as structuredFindings "
                                        "in 11-review.json; requires --write, and a "
                                        "finding that fails validation refuses the "
                                        "whole write rather than writing a partial "
                                        "record")
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
        elif name == "program":
            child.add_argument("action", choices=("status", "check"),
                               help="status renders the program report; check exits 1 when "
                                    "the committed STATUS.md drifted from a fresh render")
            child.add_argument("path", nargs="?", default=".",
                               help="the repository holding program/ (default: the current one)")
            child.add_argument("--json", action="store_true",
                               help="machine-readable report envelope (status only)")
            child.add_argument("--write", action="store_true",
                               help="regenerate program/STATUS.md between its markers "
                                    "(status only); prose outside the markers survives")
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
