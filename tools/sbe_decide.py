#!/usr/bin/env python3
"""BrotherSBE decision tables: named criteria in, a recommendation with alternatives out.

The consultation gathers context; this turns it into a reproducible recommendation.
Thresholds are data in tables/, editable in a reviewed pull request, because a
threshold measured on someone else's estate is a default, not a law.
"""
import json, os, sys


def recommend(table, context):
    """Score every criterion supplied in context against the table and rank options.

    Returns a dict with:
      recommendation: the top-ranked option, or None when verdict is NO-DATA.
      alternatives: up to two next-ranked options (fewer if the table has fewer
          options than that), or an empty list when verdict is NO-DATA. Callers
          must not assume the list has exactly two entries.
      deciding_criteria: one human-readable line per criterion that contributed.
      evidence: the number of criteria that actually contributed, i.e.
          len(deciding_criteria).
      verdict: "NO-DATA" when no criterion contributed anything (context was
          empty or every supplied value matched no criterion), "OK" otherwise.
          A recommendation backed by zero evidence is indistinguishable from a
          guess, so when verdict is NO-DATA, recommendation and alternatives
          are suppressed rather than presented as if they were well-evidenced.
      unrecognized: one line per supplied choice criterion whose value matched
          none of that criterion's known keys, naming the criterion and the
          value received, so a typo is distinguishable from an omission.
      flip_condition: table["flip"], unconditionally.
      scores: the raw tally per option.
    """
    tally = {opt: 0 for opt in table["options"]}
    deciding = []
    unrecognized = []
    for crit in table["criteria"]:
        val = context.get(crit["name"])
        if val is None:
            continue
        winners = []
        if crit["kind"] == "number":
            if not isinstance(val, (int, float)):
                unrecognized.append("%s=%s is not a recognized value" % (crit["name"], val))
                continue
            for opt, (lo, hi) in crit["scores"].items():
                if lo <= val <= hi:
                    winners.append(opt)
        else:
            key = str(val)
            if key not in crit["scores"]:
                unrecognized.append("%s=%s is not a recognized value" % (crit["name"], val))
                continue
            winners = crit["scores"][key]
        for opt in winners:
            if opt in tally:
                tally[opt] += 1
        if winners:
            deciding.append("%s=%s favours %s" % (crit["name"], val, ", ".join(winners)))
    ranked = sorted(tally, key=lambda o: (-tally[o], table["options"].index(o)))
    verdict = "OK" if deciding else "NO-DATA"
    return {"recommendation": ranked[0] if verdict == "OK" else None,
            "alternatives": ranked[1:3] if verdict == "OK" else [],
            "deciding_criteria": deciding, "evidence": len(deciding),
            "verdict": verdict, "unrecognized": unrecognized,
            "flip_condition": table["flip"], "scores": tally}


def load_table(path, key):
    """Return (table, error). Every boundary here has a named failure path: a
    missing file, a malformed file, and a table key that does not exist each
    produce a sentence naming what is available, not a raw traceback. One table
    ships (the architecture shape table); asking for a family that has no table
    yet must say so, because a traceback reads as a broken tool rather than as
    "this decision is human review until its table ships"."""
    try:
        with open(path) as f:
            tables = json.load(f)
    except OSError as e:
        return None, "cannot read table file %s: %s" % (path, e)
    except ValueError as e:
        return None, "table file %s is not valid JSON: %s" % (path, e)
    if not isinstance(tables, dict):
        return None, "table file %s does not hold a mapping of table name to table" % path
    if key not in tables:
        return None, ("no table named %r in %s. Tables that ship: %s. Decision families with no table yet "
                      "are human review, not a tool failure." % (key, path, ", ".join(sorted(tables)) or "none"))
    return tables[key], ""


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "tables", "architecture.json")
    key = sys.argv[2] if len(sys.argv) > 2 else "shape"
    table, err = load_table(path, key)
    if err:
        print("sbe_decide: %s" % err)
        sys.exit(1)
    context = {}
    for crit in table["criteria"]:
        raw = input("%s (%s): " % (crit["name"], crit["note"])).strip()
        if not raw:
            continue
        context[crit["name"]] = int(raw) if crit["kind"] == "number" and raw.isdigit() else raw
    r = recommend(table, context)
    if r["verdict"] == "NO-DATA":
        print("\nNO-DATA: no criterion was answered, so no recommendation can be made.")
    else:
        print("\nRecommendation: %s" % r["recommendation"])
        print("Alternatives: %s" % ", ".join(r["alternatives"]))
        print("Decided by:")
        for d in r["deciding_criteria"]:
            print("  - %s" % d)
        print("What would flip this: %s" % r["flip_condition"])
    if r["unrecognized"]:
        print("Unrecognized values (check for typos):")
        for u in r["unrecognized"]:
            print("  - %s" % u)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Same wrapper as the other tools: a crash names itself and exits nonzero
        # rather than printing a traceback that reads as an unusable tool.
        print("sbe_decide: error %r" % (e,))
        sys.exit(1)
