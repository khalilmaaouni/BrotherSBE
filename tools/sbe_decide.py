#!/usr/bin/env python3
"""BrotherSBE decision tables: named criteria in, a recommendation with alternatives out.

The consultation gathers context; this turns it into a reproducible recommendation.
Thresholds are data in tables/, editable in a reviewed pull request, because a
threshold measured on someone else's estate is a default, not a law.
"""
import json, os, sys


def recommend(table, context):
    tally = {opt: 0 for opt in table["options"]}
    deciding = []
    for crit in table["criteria"]:
        val = context.get(crit["name"])
        if val is None:
            continue
        winners = []
        if crit["kind"] == "number":
            for opt, (lo, hi) in crit["scores"].items():
                if lo <= val <= hi:
                    winners.append(opt)
        else:
            winners = crit["scores"].get(str(val), [])
        for opt in winners:
            if opt in tally:
                tally[opt] += 1
        if winners:
            deciding.append("%s=%s favours %s" % (crit["name"], val, ", ".join(winners)))
    ranked = sorted(tally, key=lambda o: (-tally[o], table["options"].index(o)))
    return {"recommendation": ranked[0], "alternatives": ranked[1:3],
            "deciding_criteria": deciding, "flip_condition": table["flip"],
            "scores": tally}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "tables", "architecture.json")
    tables = json.load(open(path))
    key = sys.argv[2] if len(sys.argv) > 2 else "shape"
    table = tables[key]
    context = {}
    for crit in table["criteria"]:
        raw = input("%s (%s): " % (crit["name"], crit["note"])).strip()
        context[crit["name"]] = int(raw) if crit["kind"] == "number" and raw.isdigit() else raw
    r = recommend(table, context)
    print("\nRecommendation: %s" % r["recommendation"])
    print("Alternatives: %s" % ", ".join(r["alternatives"]))
    print("Decided by:")
    for d in r["deciding_criteria"]:
        print("  - %s" % d)
    print("What would flip this: %s" % r["flip_condition"])
    sys.exit(0)


if __name__ == "__main__":
    main()
