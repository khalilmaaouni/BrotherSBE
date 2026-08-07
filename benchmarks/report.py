#!/usr/bin/env python3
"""Renders the benchmark report, and refuses to render an unattributable one.

Run: python3 benchmarks/report.py --scored benchmarks/runs --out benchmarks/RESULTS.md
     python3 benchmarks/report.py --scored benchmarks/runs --mode comparison

WHAT THIS GUARDS. A four-column comparison is the most quotable artifact
this project could produce and the easiest to produce dishonestly. The
control is one column: PROVENANCE, naming the person who ran that row. A row
nobody will put their name to is not evidence, so this renderer REFUSES to
emit a comparison containing one. It writes nothing, says why, and exits
nonzero. There is no flag to turn that off, because a flag to turn it off is
the same artifact with an extra step.

TWO MODES, and the difference is the whole point.

  status (the default) renders the grid as it actually stands, including
  rows nobody has run. Those rows read UNRUN in the provenance column and
  NO-DATA in every measure. This is the mode the release documents quote,
  and it is what lets them say the evaluation is UNRUN rather than pending:
  an unrun row is a stated fact with a shape, not a promise.

  comparison renders the same grid as a claim about which estate did better.
  It refuses on any row whose provenance is empty (an artifact exists and
  names nobody) or UNRUN (no artifact exists at all). Both are the same
  defect from the reader's side: a number they cannot trace to a person.

NO-DATA is never a pass and never a block. A rendered measure that reads
NO-DATA is not a zero and is never summed, averaged or ranked against a
number; the renderer carries the token through to the page instead.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCENARIOS = os.path.join(HERE, "scenarios.json")

NO_DATA = "NO-DATA"
UNRUN = "UNRUN"

STATUS_UNRUN = "UNRUN"
STATUS_PARTIAL = "PARTIAL"
STATUS_COMPLETE = "COMPLETE"


def read_json(path):
    """Returns (data, problem). Mirrors score_run.read_json deliberately: the
    two tools must turn the same three boundary failures into the same three
    sentences, or a reader has to learn two vocabularies."""
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


def load_plan(scenarios_path=SCENARIOS):
    """Returns (scenarios, estates, measures, problem)."""
    data, problem = read_json(scenarios_path)
    if problem:
        return [], [], [], "scenario definitions unreadable: %s" % problem
    if not isinstance(data, dict):
        return [], [], [], "scenario definitions are not a JSON object"
    scenarios = [s for s in data.get("scenarios", []) if isinstance(s, dict) and s.get("id")]
    estates = [e for e in data.get("estates", []) if isinstance(e, dict) and e.get("id")]
    measures = [m for m in data.get("measures", []) if isinstance(m, dict) and m.get("id")]
    if not scenarios or not estates or not measures:
        return [], [], [], ("scenario definitions must declare at least one scenario, one "
                            "estate and one measure; the grid has no shape otherwise")
    return scenarios, estates, measures, ""


def collect(scored_paths):
    """Returns (records, problems). A scored file that will not parse is a
    named problem, never a row silently dropped from the grid."""
    records, problems = [], []
    for path in scored_paths:
        data, problem = read_json(path)
        if problem:
            problems.append(problem)
            continue
        if not isinstance(data, dict) or "measures" not in data:
            problems.append("%s is not a scored record (no `measures`)" % os.path.basename(path))
            continue
        records.append(data)
    return records, problems


def discover(root):
    """Every *.scored.json under `root`, sorted. Returns (paths, problem)."""
    if not os.path.isdir(root):
        return [], "%s is not a directory, so no scored record was read" % root
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            if name.endswith(".scored.json"):
                found.append(os.path.join(dirpath, name))
    return found, ""


def _cell(record, measure_id):
    """The rendered text of one measure cell. NO-DATA stays NO-DATA."""
    if record is None:
        return NO_DATA
    entry = record.get("measures", {}).get(measure_id)
    if not isinstance(entry, dict):
        return NO_DATA
    if entry.get("verdict") != "VALUE" or entry.get("value") is None:
        return NO_DATA
    return str(entry["value"])


def build_rows(records, scenarios, estates, measures):
    """One row per scenario-estate pair, in declaration order.

    A pair with no scored record gets provenance UNRUN and NO-DATA
    everywhere: the grid always shows the whole intended evaluation, so a
    reader can see what has not been done rather than only what has.
    """
    by_pair = {}
    for record in records:
        key = (record.get("scenario") or "", record.get("estate") or "")
        by_pair.setdefault(key, []).append(record)
    rows = []
    for scenario in scenarios:
        for estate in estates:
            found = by_pair.get((scenario["id"], estate["id"]), [])
            record = found[0] if found else None
            if record is None:
                provenance = UNRUN
            else:
                provenance = record.get("provenance")
                provenance = provenance.strip() if isinstance(provenance, str) else ""
            rows.append({
                "scenario": scenario["id"],
                "estate": estate["id"],
                "provenance": provenance,
                "cells": [_cell(record, m["id"]) for m in measures],
                "duplicates": max(0, len(found) - 1),
            })
    return rows


def orphan_records(records, scenarios, estates):
    """Scored records naming a scenario or estate the plan does not declare.

    They belong to no cell of the grid, so build_rows cannot place them and,
    before this existed, dropped them without a word: one typo in run.json's
    `estate` removed a real run from the report and the report then printed
    STATUS: UNRUN over a directory holding it. collect() already refuses to
    lose a record it could not PARSE; a record it could parse and could not
    place is the same loss with better formatting.
    """
    known_scenarios = set(s["id"] for s in scenarios)
    known_estates = set(e["id"] for e in estates)
    orphans = []
    for record in records:
        scenario = record.get("scenario") or ""
        estate = record.get("estate") or ""
        if scenario in known_scenarios and estate in known_estates:
            continue
        why = []
        if scenario not in known_scenarios:
            why.append("scenario %r is not declared" % scenario)
        if estate not in known_estates:
            why.append("estate %r is not declared" % estate)
        orphans.append("%s: %s in benchmarks/scenarios.json, so it sits in no cell of the grid"
                       % (record.get("run_id") or "(a scored record naming no run_id)",
                          " and ".join(why)))
    return orphans


def provenance_problems(rows):
    """Every row a comparison may not be built on, with the reason."""
    problems = []
    for row in rows:
        if row["provenance"] == UNRUN:
            problems.append("%s / %s: no run exists, so the provenance column reads UNRUN"
                            % (row["scenario"], row["estate"]))
        elif not row["provenance"]:
            problems.append("%s / %s: a run artifact exists and names nobody who ran it"
                            % (row["scenario"], row["estate"]))
    return problems


def overall_status(rows):
    named = [r for r in rows if r["provenance"] and r["provenance"] != UNRUN]
    if not named:
        return STATUS_UNRUN
    if len(named) < len(rows):
        return STATUS_PARTIAL
    return STATUS_COMPLETE


def _table(rows, measures):
    header = ["Scenario", "Estate"] + [m["label"] for m in measures] + ["PROVENANCE"]
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join([" --- "] * len(header)) + "|"]
    for row in rows:
        cells = [row["scenario"], row["estate"]] + row["cells"] + [row["provenance"] or "(empty)"]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render(records, mode="status", scenarios_path=SCENARIOS, problems=None):
    """Returns (text, refusal). Exactly one of the two is non-empty.

    A refusal returns NO text at all, on purpose: a caller that got a
    refusal plus a partly rendered table would be one copy and paste away
    from publishing the thing this function refused to publish.
    """
    if mode not in ("status", "comparison"):
        return "", "unknown mode %r (expected status or comparison)" % mode
    scenarios, estates, measures, problem = load_plan(scenarios_path)
    if problem:
        return "", problem
    rows = build_rows(records, scenarios, estates, measures)
    orphans = orphan_records(records, scenarios, estates)
    blockers = provenance_problems(rows)
    if mode == "comparison" and blockers:
        return "", ("REFUSED to render a comparison: %d of %d row(s) carry no person in the "
                    "PROVENANCE column (%s). A number nobody will put their name to is not "
                    "evidence, and there is no flag that turns this off."
                    % (len(blockers), len(rows), "; ".join(blockers)))
    if mode == "comparison" and orphans:
        return "", ("REFUSED to render a comparison: %d scored record(s) sit outside the "
                    "declared grid (%s). A comparison rendered over a set that quietly lost a "
                    "real run is a comparison of something else."
                    % (len(orphans), "; ".join(orphans)))
    status = overall_status(rows)
    named = len([r for r in rows if r["provenance"] and r["provenance"] != UNRUN])
    out = []
    out.append("# BrotherSBE comparative benchmark, %s" % ("comparison" if mode == "comparison"
                                                           else "status"))
    out.append("")
    out.append("STATUS: %s. %d of %d row(s) have been run by a named person."
               % (status, named, len(rows)))
    out.append("")
    if status == STATUS_UNRUN:
        out.append("This evaluation is UNRUN. Not pending, not in progress, not estimated: no "
                   "person has run any row, so every measure below reads NO-DATA and the "
                   "PROVENANCE column reads UNRUN. Any release document quoting this file "
                   "must say the evaluation is unrun.")
        out.append("")
    out.append("Defects are planted in advance, with known file and line, by "
               "`benchmarks/fixture_repo.py` against the manifest in `benchmarks/defects.json`. "
               "Without that, `Defects missed` would be unmeasurable by construction, and any "
               "number printed for it would be fiction.")
    out.append("")
    out.append("NO-DATA means the measure could not be computed from the run's own artifacts. "
               "It is not zero, it is never summed or ranked, and it neither passes nor blocks "
               "anything.")
    out.append("")
    out.append(_table(rows, measures))
    out.append("")
    if mode == "status" and blockers:
        out.append("### Rows a comparison may not be built on")
        out.append("")
        for line in blockers:
            out.append("- %s" % line)
        out.append("")
        out.append("`python3 benchmarks/report.py --mode comparison` refuses while any of the "
                   "above stands.")
        out.append("")
    duplicates = [r for r in rows if r["duplicates"]]
    if duplicates:
        out.append("### Pairs with more than one scored run")
        out.append("")
        for row in duplicates:
            out.append("- %s / %s: %d further scored record(s) exist and are not shown in the "
                       "table above" % (row["scenario"], row["estate"], row["duplicates"]))
        out.append("")
    if orphans:
        out.append("### Scored records that sit outside the grid")
        out.append("")
        for line in orphans:
            out.append("- %s" % line)
        out.append("")
        out.append("Each of those is a run that exists and appears in no row above. Fix the id "
                   "in its `run.json` and rescore, or the report says UNRUN over work somebody "
                   "did.")
        out.append("")
    if problems:
        out.append("### Scored records that could not be read")
        out.append("")
        for line in problems:
            out.append("- %s" % line)
        out.append("")
    out.append("### How a row gets filled")
    out.append("")
    out.append("1. `python3 benchmarks/fixture_repo.py --out <empty dir outside this repo>`")
    out.append("2. Run the scenario runbook in `benchmarks/scenarios/` against one estate, "
               "capturing the artifacts it names.")
    out.append("3. `python3 benchmarks/score_run.py --run <run dir> --out "
               "<run dir>/<run id>.scored.json`")
    out.append("4. `python3 benchmarks/report.py --scored benchmarks/runs --out "
               "benchmarks/RESULTS.md`")
    out.append("")
    return "\n".join(out) + "\n", ""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render the benchmark report.")
    parser.add_argument("--scored", default=os.path.join(HERE, "runs"),
                        help="directory searched for *.scored.json (default benchmarks/runs)")
    parser.add_argument("--mode", default="status", choices=("status", "comparison"))
    parser.add_argument("--out", help="write the report here instead of stdout")
    args = parser.parse_args(argv)
    paths, problem = discover(args.scored)
    if problem:
        sys.stderr.write("report: REFUSED, %s\n" % problem)
        return 2
    records, problems = collect(paths)
    text, refusal = render(records, mode=args.mode, problems=problems)
    if refusal:
        sys.stderr.write("report: %s\n" % refusal)
        return 2
    if args.out:
        try:
            with open(args.out, "w") as handle:
                handle.write(text)
        except OSError as exc:
            sys.stderr.write("report: could not write %s (%s)\n" % (args.out, type(exc).__name__))
            return 2
        sys.stderr.write("report: wrote %s from %d scored record(s)\n" % (args.out, len(records)))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
