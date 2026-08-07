#!/usr/bin/env python3
"""Scores one benchmark run from the run's own artifacts. Never from judgment.

Run: python3 benchmarks/score_run.py --run benchmarks/runs/<run-id>
     python3 benchmarks/score_run.py --run <dir> --out <file.json>

WHAT THIS GUARDS. Six of the seven measures the founder named can be faked
by a person who watched the session and remembers it charitably. This script
refuses to accept memory as input: every measure is computed from a file the
run left behind, and a measure whose file is absent, unreadable, unparseable
or silent on the question reports NO-DATA carrying the reason. It never
reports zero for a measure it could not compute, because zero is a claim
("nothing happened") and absence is not.

The honesty law this inherits from the rest of the project, stated once:
NO-DATA is never a PASS and never a block. This script exits 0 whenever it
produced a scored record, however many of that record's measures read
NO-DATA. It exits nonzero only when it could not read the run at all, which
is a refusal rather than a verdict.

THE ONE MEASURE THAT NEEDS GROUND TRUTH. defects_missed is computable only
because benchmarks/defects.json declared, before any run, what was there to
find. A finding matches a defect when it names the same repo-relative path
and a line within the defect's declared window. Nothing about the WORDING of
a finding is scored: wording is judgment, and a benchmark that scores
judgment is a benchmark whose numbers move when the reader changes.

WHAT THIS DOES NOT DO. It does not decide whether a block was justified. The
run's own blocks.json carries that judgment, made by a named person, per
block; a block with no judgment recorded makes false_blocks NO-DATA for the
whole run rather than quietly counting as justified.
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DEFECTS = os.path.join(HERE, "defects.json")
SCENARIOS = os.path.join(HERE, "scenarios.json")

NO_DATA = "NO-DATA"
VALUE = "VALUE"

MEASURE_IDS = ("defects_found", "defects_missed", "wall_clock_seconds",
               "tokens_total", "corrections", "false_blocks", "reviewer_findings")


def read_json(path):
    """Returns (data, problem). data is None whenever problem is set.

    Every boundary call in this file goes through here so there is exactly
    one place where "the file was not there", "the file could not be opened"
    and "the file was not JSON" are turned into sentences. A caller that
    wants to distinguish absent from broken checks os.path.lexists itself,
    which never blocks; this helper never raises.
    """
    if not os.path.lexists(path):
        return None, "%s is absent" % os.path.basename(path)
    if os.path.isdir(path):
        return None, "%s is a directory, not a JSON file" % os.path.basename(path)
    try:
        with open(path, "r") as handle:
            raw = handle.read()
    except OSError as exc:
        return None, "%s exists and could not be read (%s)" % (os.path.basename(path),
                                                               type(exc).__name__)
    try:
        return json.loads(raw), ""
    except ValueError as exc:
        return None, "%s did not parse as JSON (%s)" % (os.path.basename(path), exc)


def measure(verdict, value, reason):
    return {"verdict": verdict, "value": value, "reason": reason}


def no_data(reason):
    """The only way this file produces an uncomputed measure. value is null,
    never 0: a caller that renders `value or 0` would turn an absence into a
    claim, and a null makes that mistake visible instead of plausible."""
    return measure(NO_DATA, None, reason)


def _int_field(blob, name, source):
    """Returns (value, problem) for a field that must be a non-negative int."""
    if not isinstance(blob, dict):
        return None, "%s is not a JSON object" % source
    if name not in blob:
        return None, "%s does not carry %r" % (source, name)
    raw = blob[name]
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None, "%s carries %r as %r, which is not a whole number" % (source, name, raw)
    if raw < 0:
        return None, "%s carries %r as %d, which is negative" % (source, name, raw)
    return raw, ""


def _parse_time(text, label):
    """ISO-8601 with no timezone handling beyond what Python 3.9 gives us.

    The failure path ASSIGNS rather than returning out of the except block,
    and it binds the exception. The first draft wrote `except ValueError:`
    then `return None, <reason>`, which tools/sbe_score.py's unwaivable lint
    correctly reads as the except-then-return-None shape that drops a record:
    the reason travelled in a second tuple slot the pattern cannot see. The
    shape below carries the same information and reads as what it is.
    """
    if not isinstance(text, str) or not text.strip():
        return None, "%s is missing or empty" % label
    stamp, why = None, ""
    try:
        stamp = datetime.datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        why = "%s (%r) is not an ISO-8601 timestamp (%s)" % (label, text, exc)
    return stamp, why


def load_ground_truth(defects_path=DEFECTS, scenarios_path=SCENARIOS):
    """Returns (defects_by_id, scenarios_by_id, problem)."""
    data, problem = read_json(defects_path)
    if problem:
        return {}, {}, "ground truth unreadable: %s" % problem
    defects = data.get("defects") if isinstance(data, dict) else None
    if not isinstance(defects, list) or not defects:
        return {}, {}, ("ground truth %s declares no defects; an empty set would score every "
                        "run as missing nothing" % os.path.basename(defects_path))
    by_id = {}
    for entry in defects:
        if isinstance(entry, dict) and entry.get("id"):
            by_id[entry["id"]] = entry
    if not by_id:
        return {}, {}, "ground truth declares defects with no id, so nothing can be matched"
    data, problem = read_json(scenarios_path)
    if problem:
        return by_id, {}, "scenario definitions unreadable: %s" % problem
    scenarios = data.get("scenarios") if isinstance(data, dict) else None
    if not isinstance(scenarios, list) or not scenarios:
        return by_id, {}, "scenario definitions declare no scenarios"
    scen_by_id = {}
    for entry in scenarios:
        if isinstance(entry, dict) and entry.get("id"):
            scen_by_id[entry["id"]] = entry
    return by_id, scen_by_id, ""


def normalise_path(text):
    """Repo-relative, forward slashes, no leading ./ or / so two spellings of
    the same file are one identity.

    What this does NOT do, stated because the first draft's docstring claimed
    it did: it never strips a fixture root out of an absolute path. A finding
    recorded as /home/op/bench-S1/ops/alerts.yaml normalises to
    home/op/bench-S1/ops/alerts.yaml, matches no declared defect, and lands in
    unmatched_findings saying so. Guessing which leading segments were
    somebody's scratch directory is exactly the kind of silent repair that
    would let a wrong path score as a right one, so the runbooks tell the
    operator to record paths relative to the fixture root instead.
    """
    if not isinstance(text, str):
        return ""
    path = text.strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path.lstrip("/")


def match_findings(findings, defects):
    """Returns (matched_ids, unmatched_findings).

    The whole matching rule, in one place: same normalised path, and a line
    within the defect's declared window. A finding carrying no usable line
    cannot be matched, and is returned unmatched rather than credited.
    """
    matched, unmatched = set(), []
    for finding in findings:
        if not isinstance(finding, dict):
            unmatched.append({"raw": finding, "why": "finding is not a JSON object"})
            continue
        path = normalise_path(finding.get("file"))
        line = finding.get("line")
        if not path:
            unmatched.append({"raw": finding, "why": "finding names no file"})
            continue
        if isinstance(line, bool) or not isinstance(line, int):
            unmatched.append({"raw": finding, "why": "finding names no whole-number line"})
            continue
        hit = None
        for defect in defects:
            if normalise_path(defect.get("file")) != path:
                continue
            window = defect.get("line_window")
            if isinstance(window, bool) or not isinstance(window, int) or window < 0:
                window = 0
            if abs(line - defect.get("line", -10 ** 9)) <= window:
                hit = defect.get("id")
                break
        if hit:
            matched.add(hit)
        else:
            unmatched.append({"raw": finding,
                              "why": "no declared defect sits at %s:%d" % (path, line)})
    return matched, unmatched


def score_defects(run_dir, scenario_id, defects_by_id, scenarios_by_id):
    """Returns (found_measure, missed_measure, detail)."""
    detail = {"scenario_defect_ids": [], "matched_ids": [], "missed_ids": [],
              "unmatched_findings": []}
    if not scenario_id:
        reason = ("the run does not name a scenario, so there is no declared defect set to "
                  "score against")
        return no_data(reason), no_data(reason), detail
    scenario = scenarios_by_id.get(scenario_id)
    if scenario is None:
        reason = ("the run names scenario %r, which benchmarks/scenarios.json does not "
                  "declare" % scenario_id)
        return no_data(reason), no_data(reason), detail
    ids = [i for i in scenario.get("defect_ids", []) if i in defects_by_id]
    detail["scenario_defect_ids"] = ids
    if not ids:
        reason = ("scenario %s declares no defect that the ground truth also declares, so "
                  "nothing was planted to find" % scenario_id)
        return no_data(reason), no_data(reason), detail
    blob, problem = read_json(os.path.join(run_dir, "findings.json"))
    if problem:
        reason = ("findings.json could not be read (%s), so what the run reported is unknown; "
                  "this is an absence, not a run that found nothing" % problem)
        return no_data(reason), no_data(reason), detail
    findings = blob.get("findings") if isinstance(blob, dict) else None
    if not isinstance(findings, list):
        reason = "findings.json carries no `findings` list, so what the run reported is unknown"
        return no_data(reason), no_data(reason), detail
    scenario_defects = [defects_by_id[i] for i in ids]
    matched, unmatched = match_findings(findings, scenario_defects)
    missed = [i for i in ids if i not in matched]
    detail["matched_ids"] = sorted(matched)
    detail["missed_ids"] = missed
    detail["unmatched_findings"] = unmatched
    # An EMPTY findings list is data, not an absence: the run existed, it
    # reported nothing, and every planted defect is therefore missed. That is
    # the whole reason the defects were planted in advance.
    found = measure(VALUE, len(matched),
                    "%d of %d planted defect(s) in %s were named at their declared location "
                    "(%s)" % (len(matched), len(ids), scenario_id,
                              ", ".join(sorted(matched)) or "none"))
    missed_m = measure(VALUE, len(missed),
                       "%d planted defect(s) in %s were not named at their declared location "
                       "(%s)" % (len(missed), scenario_id, ", ".join(missed) or "none"))
    return found, missed_m, detail


def score_wall_clock(run_dir):
    blob, problem = read_json(os.path.join(run_dir, "timing.json"))
    if problem:
        return no_data("timing.json could not be read (%s), so no elapsed time exists to "
                       "report" % problem)
    if not isinstance(blob, dict):
        return no_data("timing.json is not a JSON object")
    started, why = _parse_time(blob.get("started_at"), "started_at")
    if why:
        return no_data("timing.json %s" % why)
    ended, why = _parse_time(blob.get("ended_at"), "ended_at")
    if why:
        return no_data("timing.json %s" % why)
    seconds = (ended - started).total_seconds()
    if seconds < 0:
        return no_data("timing.json ends before it starts (%s to %s), so the elapsed time is "
                       "not a duration" % (blob.get("started_at"), blob.get("ended_at")))
    return measure(VALUE, int(round(seconds)),
                   "%s to %s" % (blob.get("started_at"), blob.get("ended_at")))


def score_tokens(run_dir):
    path = os.path.join(run_dir, "tokens.json")
    blob, problem = read_json(path)
    if problem:
        return no_data("tokens.json could not be read (%s); a run whose token use nobody "
                       "captured has no token number" % problem)
    inp, why_in = _int_field(blob, "input", "tokens.json")
    out, why_out = _int_field(blob, "output", "tokens.json")
    if why_in and why_out:
        return no_data("tokens.json carries neither input nor output (%s; %s)" % (why_in, why_out))
    if why_in or why_out:
        return no_data("tokens.json carries only half the total (%s), and a half is not a "
                       "total" % (why_in or why_out))
    return measure(VALUE, inp + out, "%d input plus %d output" % (inp, out))


def _counted_list(run_dir, filename, key, label):
    """The shape three measures share: a list whose LENGTH is the measure."""
    blob, problem = read_json(os.path.join(run_dir, filename))
    if problem:
        return no_data("%s could not be read (%s), so the number of %s is unknown; that is "
                       "not the same as none" % (filename, problem, label))
    items = blob.get(key) if isinstance(blob, dict) else None
    if not isinstance(items, list):
        return no_data("%s carries no %r list, so the number of %s is unknown"
                       % (filename, key, label))
    return measure(VALUE, len(items), "%d %s recorded in %s" % (len(items), label, filename))


def score_corrections(run_dir):
    return _counted_list(run_dir, "corrections.json", "corrections",
                         "operator correction(s)")


def score_reviewer_findings(run_dir):
    return _counted_list(run_dir, "reviewer.json", "findings", "reviewer finding(s)")


def score_false_blocks(run_dir):
    """A block the run raised that a named person judged unjustified.

    A block carrying no `justified` key is UNJUDGED. One unjudged block makes
    the whole measure NO-DATA: counting it as justified would flatter the
    estate that raised it, and counting it as false would flatter every other
    column, so neither is available and the honest answer is that nobody
    judged it yet.
    """
    blob, problem = read_json(os.path.join(run_dir, "blocks.json"))
    if problem:
        return no_data("blocks.json could not be read (%s), so the number of false blocks is "
                       "unknown; an estate that blocked nothing still has to say so" % problem)
    blocks = blob.get("blocks") if isinstance(blob, dict) else None
    if not isinstance(blocks, list):
        return no_data("blocks.json carries no `blocks` list, so the number of false blocks "
                       "is unknown")
    unjudged, false_count = [], 0
    for index, block in enumerate(blocks):
        if not isinstance(block, dict) or not isinstance(block.get("justified"), bool):
            unjudged.append(str(index))
            continue
        if not block["justified"]:
            false_count += 1
    if unjudged:
        return no_data("%d of %d block(s) in blocks.json carry no boolean `justified` "
                       "judgment (index %s), so no false-block count covers them"
                       % (len(unjudged), len(blocks), ", ".join(unjudged)))
    return measure(VALUE, false_count,
                   "%d of %d recorded block(s) were judged unjustified" % (false_count, len(blocks)))


def score(run_dir, defects_by_id=None, scenarios_by_id=None):
    """Returns (record, problem). A problem means the run could not be read
    at all; a record with NO-DATA measures is a successful scoring."""
    if not os.path.isdir(run_dir):
        return None, "run directory %s does not exist or is not a directory" % run_dir
    if defects_by_id is None or scenarios_by_id is None:
        defects_by_id, scenarios_by_id, problem = load_ground_truth()
        if problem:
            return None, problem
    meta, meta_problem = read_json(os.path.join(run_dir, "run.json"))
    if meta_problem or not isinstance(meta, dict):
        meta, meta_note = {}, (meta_problem or "run.json is not a JSON object")
    else:
        meta_note = ""
    provenance = meta.get("provenance")
    provenance = provenance.strip() if isinstance(provenance, str) else ""
    record = {
        "schema": "sbe-bench-scored/1",
        "run_id": meta.get("run_id") or os.path.basename(os.path.abspath(run_dir)),
        "scenario": meta.get("scenario") or "",
        "estate": meta.get("estate") or "",
        "provenance": provenance,
        "provenance_note": ("" if provenance else
                            "run.json names nobody who ran this row%s"
                            % (": " + meta_note if meta_note else "")),
        "run_dir": os.path.abspath(run_dir),
        "measures": {},
        "detail": {},
    }
    found, missed, detail = score_defects(run_dir, record["scenario"],
                                          defects_by_id, scenarios_by_id)
    record["measures"]["defects_found"] = found
    record["measures"]["defects_missed"] = missed
    record["measures"]["wall_clock_seconds"] = score_wall_clock(run_dir)
    record["measures"]["tokens_total"] = score_tokens(run_dir)
    record["measures"]["corrections"] = score_corrections(run_dir)
    record["measures"]["false_blocks"] = score_false_blocks(run_dir)
    record["measures"]["reviewer_findings"] = score_reviewer_findings(run_dir)
    record["detail"]["defects"] = detail
    return record, ""


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Score one benchmark run from its own artifacts.")
    parser.add_argument("--run", required=True, help="the run directory to score")
    parser.add_argument("--out", help="write the scored record here instead of stdout")
    args = parser.parse_args(argv)
    record, problem = score(args.run)
    if problem:
        sys.stderr.write("score_run: REFUSED, %s\n" % problem)
        return 2
    text = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.out:
        try:
            with open(args.out, "w") as handle:
                handle.write(text)
        except OSError as exc:
            sys.stderr.write("score_run: could not write %s (%s)\n"
                             % (args.out, type(exc).__name__))
            return 2
        sys.stderr.write("score_run: wrote %s\n" % args.out)
    else:
        sys.stdout.write(text)
    absent = [name for name in MEASURE_IDS
              if record["measures"][name]["verdict"] == NO_DATA]
    sys.stderr.write("score_run: %d of %d measure(s) read NO-DATA (%s). NO-DATA is not zero "
                     "and does not block.\n"
                     % (len(absent), len(MEASURE_IDS), ", ".join(absent) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
