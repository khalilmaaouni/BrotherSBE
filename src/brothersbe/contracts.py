"""LP-0201: one versioned JSON contract registry for the surfaces this tool
already emits, so the CLI, skills and the future workspace read ONE schema
instead of five private shapes that can drift apart unnoticed.

WHY THIS EXISTS. Five producers (`brothersbe.tasks`, `brothersbe.status`
twice over, `brothersbe.work`, `brothersbe.handover`) each grew its own
`schemaVersion` field, its own "these are the required keys" list, and its
own refusal wording, independently, over ten release candidates. Nothing
compared them. A consumer written against `sbe status --json` today has no
single place to learn what the surface promises, or what changes when the
tool's own version moves. This module is that place: a name for each
surface, the fields it promises, the `schemaVersion` values it is known to
have written, and one `validate_*` function per surface that checks a
document against that promise without guessing at fields it does not know.

WHAT THIS DOES NOT DO, stated here because a control that oversells itself
is worse than none (the same rule `brothersbe.tasks`'s own module docstring
states):

  - It does not PARSE JSON. Every `validate_*` function takes an already
    loaded Python object (whatever `json.loads`/`json.load` handed back),
    the same way `evidence._check_schema` takes an already loaded receipt.
    A caller with raw text parses it and decides what an unparseable
    document means for itself; this module has nothing useful to add there.
  - It does not validate every nested field. The task registry's nested task
    records are checked against `tasks.RECORD_FIELDS` (and `role`/`status`
    against `tasks.ROLES`/`tasks.STATUSES`) because those are the exact
    depth `tasks.load_registry` itself already enforces; the other four
    surfaces are checked at their TOP LEVEL only (does every promised field
    exist, does `schemaVersion` name a version this registry knows). A
    `scope`, `notes`, `evidence` or `acknowledgment` sub-object one level
    down is not walked. Depth grows in a later wave, named as a gap here
    rather than silently assumed complete.
  - It does not WRITE anything, or change what any of the five producers
    already emit. `sbe status --team --json` (`status.build_team_report`)
    carries no `schemaVersion` field as of 1.0.0-rc.16, and this module does
    not add one; `validate_status_team` accepts its absence, by name, in one
    place (see the comment above `STATUS_TEAM_KNOWN_SCHEMA_VERSIONS`), and
    starts requiring it the day the producer starts writing it.
  - Unknown fields are ALLOWED, on every surface: a document that carries
    more than this registry names is forward compatible, not broken, and is
    never refused for that alone. An unknown `schemaVersion` is the opposite
    case and IS refused, by name, never parsed hopefully: a field read under
    the wrong semantics is worse than one that fails loudly (the same rule
    `evidence._check_schema` and `tasks.load_registry` already state for
    their own one surface each).

WHERE THE KNOWN VERSIONS COME FROM. Every producer that exports its own
schema-version constant is imported here rather than retyped, the same "one
overlap rule, imported from the module that owns it" discipline `tasks.py`
already uses for `paths_overlap`: `tasks.KNOWN_REGISTRY_VERSIONS` for the
task registry, the package-level `brothersbe.SCHEMA_VERSION` for `sbe
status --json` and the handover record (both literally read it), and
`handover.SCHEMA_FIELDS` for the handover record's exact field tuple. Two
producers export no constant at all: `work._brief_document` writes the
literal `"1.0"` inline, and `status.build_report`/`status.build_team_report`
build their return dicts inline with no exported field tuple. Those two
surfaces' known versions and field tuples are typed out by hand below, each
with a comment naming the exact function this registry copies, so a reader
can diff this file against that function rather than trust a claim.

CONTRACTS_SCHEMA_VERSION, an integer, is THIS registry's own version, not
any producer's. Every producer this module knows about is at major version
1 today (`tasks.REGISTRY_VERSION` reads `"1.0"`, the package `SCHEMA_VERSION`
reads `"1.0"`, the work brief and the handover record both write `"1.0"`):
this registry continues that same generation as the integer 1 rather than
starting a second count disconnected from the artifacts it describes, and
moves only when the SHAPE of the registry itself (not a producer's own
version) changes in a way an old consumer of THIS module could misread.

THE HOUSE 3-TUPLE. Every `validate_*` function returns `(verdict, evidence,
problems)`: `verdict` is one of `"PASS"`, `"FAIL"`, `"NO-DATA"` (the same
three-word vocabulary `tools/sbe_checks.py:VERDICTS` and every `sbe doctor`
check already use; never a bare boolean, because "the document was not even
given" and "the document is the wrong shape" are different findings and a
bool cannot carry both); `evidence` is one human-readable summary line, the
same job `detail` does in `cli.py`'s `_doctor_checks()` triples; `problems`
is a tuple of the individual named failures, empty on `"PASS"`, so a caller
can act on the SPECIFIC field that is wrong instead of re-parsing `evidence`.
Three values, not two, mirroring the shape `tools/fixtures/golden-scenario/
build_scenario.py`'s own `run_sbe` docstring names as this project's
standing convention for a verdict-shaped return: `NO-DATA` only ever means
"no document was given to check" (`data is None`), never "the document
exists but does not match" (`FAIL`, the shape `evals/test_no_data_class.py`'s
own `legacy_cases` already fixes for every OTHER check in this project: a
wrong-shaped JSON blob is `FAIL`, not `NO-DATA`, because absence and a
broken claim are different findings).

Python floor is 3.9: no match statements, no `X | Y` annotations. Standard
library only, no `jsonschema` dependency: every check below is an explicit,
named comparison, the same style `evidence.py`'s `_check_schema` and
`_check_required` already use for the one surface they cover.
"""
from . import SCHEMA_VERSION
from . import handover as handover_mod
from . import tasks as tasks_mod

#: This registry's own schema version. See the module docstring for why it
#: starts at 1 rather than at a number disconnected from the artifacts it
#: describes.
CONTRACTS_SCHEMA_VERSION = 1

#: The vocabulary every validator's `verdict` element is drawn from,
#: byte-identical to `tools/sbe_checks.py:VERDICTS`. Not imported from
#: there: importing it would pull `tools/` onto `sys.path` for three string
#: literals this module can simply hold, and unlike `tasks.RECORD_FIELDS` or
#: `handover.SCHEMA_FIELDS` this tuple is not owned by any one producer to
#: drift away from; every surface in this project already agrees on it.
VERDICTS = ("PASS", "FAIL", "NO-DATA")

#: `sbe status --json` (`status.build_report`'s own return dict, `src/
#: brothersbe/status.py`, the `return {...}` just above `def any_blocking`).
#: No exported field-tuple constant exists there to import; typed out by
#: hand, and this comment names the exact statement to diff against.
STATUS_FIELDS = ("schemaVersion", "tool", "toolVersion", "generatedAt", "root", "scope",
                 "brokenClaims", "mergeBlockers", "activeConflicts", "missingEvidence",
                 "soundEvidence", "notes", "nextAction", "nextActionDetail", "handover")

#: `sbe status --team --json` (`status.build_team_report`'s own return dict,
#: the `return {"tool": ...}` just above `TEAM_BLOCKING_SEVERITIES`). Also
#: hand-typed for the same reason as `STATUS_FIELDS`. Deliberately carries
#: no `"schemaVersion"` entry: the real producer writes none as of
#: 1.0.0-rc.16, and a required-field list that named one anyway would make
#: every real `sbe status --team --json` call fail THIS validator over a gap
#: that is `status.py`'s to close, not this registry's to paper over.
STATUS_TEAM_FIELDS = ("tool", "root", "headCommit", "changes", "findings", "handover",
                      "planOnly", "completedTasks", "basisLegend")

#: The work brief (`work._brief_document`'s own return dict, `src/
#: brothersbe/work.py`). Matches `CONTRACT_FIELDS` in `tools/
#: test_sbe_work_brief.py`, which already pins this exact set against the
#: real command; not imported from that test module on purpose (a test file
#: is not a dependency other code should reach into), typed out by hand
#: instead, from the same source statement that test itself reads.
WORK_BRIEF_FIELDS = ("schemaVersion", "taskId", "title", "why", "baselineCommit", "planPath",
                     "scope", "mustNotTouch", "dependencies", "acceptance",
                     "verificationCommands", "relevantPointers", "knownConstraints",
                     "stopConditions", "requiredEvidenceKind", "model",
                     "maxAttemptsPerApproach")

#: The one surface with no local `schemaVersion` at all yet. Accepted when
#: absent (see the module docstring); when PRESENT, held to the same known
#: set every OTHER surface at major version 1 already carries, so a future
#: `status.py` change that starts stamping `"schemaVersion": SCHEMA_VERSION`
#: onto the team report (matching every other producer) is already valid
#: against this registry the day it ships, with no edit here required.
STATUS_TEAM_KNOWN_SCHEMA_VERSIONS = (SCHEMA_VERSION,)

#: The work brief's own known versions. `work._brief_document` writes the
#: literal `"1.0"` inline (no exported constant to import, unlike
#: `tasks.REGISTRY_VERSION` or the package `SCHEMA_VERSION`); this tuple is
#: that same literal, named here so a second producer version, when it
#: exists, is added rather than swapped in.
WORK_BRIEF_KNOWN_SCHEMA_VERSIONS = ("1.0",)


def _missing_fields(data, required):
    """Every name in `required` that `data` does not carry, sorted. Presence
    only: a field holding `None` or `""` still counts as present here, the
    same "required means the KEY exists" reading `tasks.load_registry`'s own
    `RECORD_FIELDS` check uses. A surface that additionally wants "answered,
    not just present" is a stricter, later check, not this one."""
    return sorted(f for f in required if f not in data)


def _shape_problem(data, label):
    """None when `data` is a JSON object this module can inspect further, or
    a named problem string when it is not. `data is None` is handled by the
    caller as `NO-DATA` (nothing was given at all, an absence); everything
    that is not a `dict` but IS something is `FAIL` material here, the same
    "wrong shape is a broken claim, not an absence" rule
    `evals/test_no_data_class.py`'s own `legacy_cases` already fixes for
    every check that reads a JSON file in this project. `label` names the
    surface in the problem string; the caller passes it (each already states
    the label in its own docstring) rather than this function reading it off
    shared module state, so two `validate_*` calls in flight at once, on two
    different surfaces, can never make one borrow the other's name in its
    problem text."""
    if not isinstance(data, dict):
        return ("this %s is a JSON %s, not an object; a valid document is a JSON object "
               "at the top level" % (label, type(data).__name__))
    return None


def _verdict(problems, pass_evidence):
    """(verdict, evidence, problems) from a (possibly empty) list of named
    problem strings and the evidence line to use when there are none."""
    if not problems:
        return "PASS", pass_evidence, ()
    summary = "%d problem(s): %s" % (len(problems), "; ".join(problems))
    return "FAIL", summary, tuple(problems)


def validate_task_registry(data):
    """The task registry (`.sbe/tasks.json`, `tasks.load_registry`'s own
    file). Checks `schemaVersion` against `tasks.KNOWN_REGISTRY_VERSIONS`,
    the two top-level fields `tasks.load_registry` itself reads
    (`schemaVersion`, `tasks`), and, for every entry in `tasks` that is a
    JSON object, its fields against `tasks.RECORD_FIELDS` and its `role`/
    `status` against `tasks.ROLES`/`tasks.STATUSES`: the exact depth
    `tasks.load_registry` already enforces, imported rather than
    reimplemented so the two cannot silently disagree about what a valid
    record looks like."""
    if data is None:
        return "NO-DATA", "no task registry document was given to validate", ()
    shape = _shape_problem(data, "task registry")
    if shape:
        return "FAIL", shape, (shape,)

    problems = []
    version = data.get("schemaVersion")
    if "schemaVersion" not in data:
        problems.append("schemaVersion is missing: nothing here knows what the "
                        "remaining fields mean")
    elif version not in tasks_mod.KNOWN_REGISTRY_VERSIONS:
        problems.append("schemaVersion %r is not one this registry knows (%s); refused "
                        "rather than parsed hopefully"
                        % (version, ", ".join(tasks_mod.KNOWN_REGISTRY_VERSIONS)))

    missing = _missing_fields(data, ("schemaVersion", "tasks"))
    if missing:
        problems.append("missing required top-level field(s): %s" % ", ".join(missing))

    tasks_list = data.get("tasks")
    if "tasks" in data:
        if not isinstance(tasks_list, list):
            problems.append("'tasks' is %s, not a list of records"
                            % type(tasks_list).__name__)
        else:
            for i, record in enumerate(tasks_list):
                label = "tasks[%d]" % i
                if not isinstance(record, dict):
                    problems.append("%s is %s, not a task record object"
                                    % (label, type(record).__name__))
                    continue
                rec_id = record.get("id")
                if isinstance(rec_id, str) and rec_id:
                    label = "task %r" % rec_id
                rec_missing = _missing_fields(record, tasks_mod.RECORD_FIELDS)
                if rec_missing:
                    problems.append("%s is missing field(s): %s"
                                    % (label, ", ".join(rec_missing)))
                role = record.get("role")
                if "role" in record and role not in tasks_mod.ROLES:
                    problems.append("%s has role %r, not one of %s"
                                    % (label, role, ", ".join(tasks_mod.ROLES)))
                status = record.get("status")
                if "status" in record and status not in tasks_mod.STATUSES:
                    problems.append("%s has status %r, not one of %s"
                                    % (label, status, ", ".join(tasks_mod.STATUSES)))

    count = len(tasks_list) if isinstance(tasks_list, list) else 0
    return _verdict(problems, "schemaVersion %r, %d task record(s), every required "
                              "field present" % (version, count))


def validate_status(data):
    """`sbe status --json` (`status.build_report`'s return dict). Checks
    `schemaVersion` against the package's own `brothersbe.SCHEMA_VERSION`
    (the same constant `status.py` stamps the field with) and every field in
    `STATUS_FIELDS`."""
    if data is None:
        return "NO-DATA", "no sbe status document was given to validate", ()
    shape = _shape_problem(data, "sbe status --json document")
    if shape:
        return "FAIL", shape, (shape,)

    problems = []
    version = data.get("schemaVersion")
    if "schemaVersion" not in data:
        problems.append("schemaVersion is missing: nothing here knows what the "
                        "remaining fields mean")
    elif version != SCHEMA_VERSION:
        problems.append("schemaVersion %r is not one this build knows (%s); refused "
                        "rather than parsed hopefully" % (version, SCHEMA_VERSION))

    missing = _missing_fields(data, STATUS_FIELDS)
    if missing:
        problems.append("missing required field(s): %s" % ", ".join(missing))

    return _verdict(problems, "schemaVersion %r, every one of %d required field(s) "
                              "present" % (version, len(STATUS_FIELDS)))


def validate_status_team(data):
    """`sbe status --team --json` (`status.build_team_report`'s return
    dict). Checks every field in `STATUS_TEAM_FIELDS`. `schemaVersion` is
    OPTIONAL on this one surface, by name, per the module docstring: absent
    is accepted (the real producer writes none as of 1.0.0-rc.16); present
    but unrecognized is still refused, against
    `STATUS_TEAM_KNOWN_SCHEMA_VERSIONS`."""
    if data is None:
        return "NO-DATA", "no sbe status --team document was given to validate", ()
    shape = _shape_problem(data, "sbe status --team --json document")
    if shape:
        return "FAIL", shape, (shape,)

    problems = []
    if "schemaVersion" in data:
        version = data.get("schemaVersion")
        if version not in STATUS_TEAM_KNOWN_SCHEMA_VERSIONS:
            problems.append("schemaVersion %r is not one this build knows (%s); refused "
                            "rather than parsed hopefully"
                            % (version, ", ".join(STATUS_TEAM_KNOWN_SCHEMA_VERSIONS)))

    missing = _missing_fields(data, STATUS_TEAM_FIELDS)
    if missing:
        problems.append("missing required field(s): %s" % ", ".join(missing))

    changes = data.get("changes")
    change_count = len(changes) if isinstance(changes, list) else 0
    if "schemaVersion" in data:
        version_clause = "schemaVersion %r" % data.get("schemaVersion")
    else:
        version_clause = ("no schemaVersion field (not yet emitted by this surface, "
                          "accepted by name)")
    note = ("%s, %d change(s) named, every one of %d required field(s) present"
           % (version_clause, change_count, len(STATUS_TEAM_FIELDS)))
    return _verdict(problems, note)


def validate_work_brief(data):
    """The work brief (`sbe work brief --json`, `work._brief_document`'s
    return dict). Checks `schemaVersion` against
    `WORK_BRIEF_KNOWN_SCHEMA_VERSIONS` and every field in
    `WORK_BRIEF_FIELDS`."""
    if data is None:
        return "NO-DATA", "no work brief document was given to validate", ()
    shape = _shape_problem(data, "work brief document")
    if shape:
        return "FAIL", shape, (shape,)

    problems = []
    version = data.get("schemaVersion")
    if "schemaVersion" not in data:
        problems.append("schemaVersion is missing: nothing here knows what the "
                        "remaining fields mean")
    elif version not in WORK_BRIEF_KNOWN_SCHEMA_VERSIONS:
        problems.append("schemaVersion %r is not one this build knows (%s); refused "
                        "rather than parsed hopefully"
                        % (version, ", ".join(WORK_BRIEF_KNOWN_SCHEMA_VERSIONS)))

    missing = _missing_fields(data, WORK_BRIEF_FIELDS)
    if missing:
        problems.append("missing required field(s): %s" % ", ".join(missing))

    return _verdict(problems, "schemaVersion %r, every one of %d required field(s) "
                              "present" % (version, len(WORK_BRIEF_FIELDS)))


def validate_handover(data):
    """The handover record (`12-handover.json`, `handover.SCHEMA_FIELDS`'s
    own document). Checks `schemaVersion` against the package's own
    `brothersbe.SCHEMA_VERSION` (the same constant `handover.py` stamps the
    field with) and every field in `handover.SCHEMA_FIELDS`, imported
    rather than retyped."""
    if data is None:
        return "NO-DATA", "no handover record was given to validate", ()
    shape = _shape_problem(data, "handover record")
    if shape:
        return "FAIL", shape, (shape,)

    problems = []
    version = data.get("schemaVersion")
    if "schemaVersion" not in data:
        problems.append("schemaVersion is missing: nothing here knows what the "
                        "remaining fields mean")
    elif version != SCHEMA_VERSION:
        problems.append("schemaVersion %r is not one this build knows (%s); refused "
                        "rather than parsed hopefully" % (version, SCHEMA_VERSION))

    missing = _missing_fields(data, handover_mod.SCHEMA_FIELDS)
    if missing:
        problems.append("missing required field(s): %s" % ", ".join(missing))

    return _verdict(problems, "schemaVersion %r, every one of %d required field(s) "
                              "present" % (version, len(handover_mod.SCHEMA_FIELDS)))


#: One registry, so a caller can look up a surface by name instead of
#: importing five function names by hand. Not the only way to call this
#: module (every `validate_*` function above is public on its own), but the
#: shape LP-0201 asked for: "a versioned schema registry", not five loose
#: functions with no list naming them all.
VALIDATORS = {
    "task-registry": validate_task_registry,
    "status": validate_status,
    "status-team": validate_status_team,
    "work-brief": validate_work_brief,
    "handover": validate_handover,
}

#: Every surface name this registry knows, for a caller that wants to list
#: them (a help string, a test that walks all five) without importing
#: `VALIDATORS` and reading its keys.
SURFACES = tuple(sorted(VALIDATORS))


def validate(surface, data):
    """Dispatch to the `validate_*` function named by `surface`, one of
    `SURFACES`. An unknown `surface` is a caller error, not a document
    finding: it is refused with `ValueError`, naming the surfaces this
    registry actually knows, the same way `sbe_checks.Check.__init__`
    refuses an unknown `kind` at construction time rather than at the first
    call. Returns the house 3-tuple `(verdict, evidence, problems)`, exactly
    what the surface's own `validate_*` function returns."""
    fn = VALIDATORS.get(surface)
    if fn is None:
        raise ValueError("unknown surface %r; this registry knows %s"
                         % (surface, ", ".join(SURFACES)))
    return fn(data)
