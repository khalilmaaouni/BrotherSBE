#!/usr/bin/env python3
"""BrotherSBE intake: five objective questions in, one tier out.

The tier decides how much dossier a task gets, which is the mechanism behind
"brief always": a one line fix produces nothing, a new system produces the full
set. The rule is a decision table, not a judgment, so two engineers classifying
the same task land on the same tier.
"""
import json, os, sys

QUESTIONS = [
    ("changes_contract", "Does this change a data model, an API contract, or a file interface others depend on? (y/n) "),
    ("crosses_boundary", "Does it cross a service, system, or team boundary? (y/n) "),
    ("reversible_under_hour", "Is it reversible in under an hour? (y/n) "),
    ("touches_sensitive", "Does it touch money, partner data, personal data, or production state? (y/n) "),
    ("consumers", "How many downstream consumers break if it is wrong? (none/some/many) "),
]

TIERS = ("T0", "T1", "T2", "T3")


def compute_tier(a):
    """Named inputs, one output. Highest matching rule wins."""
    if a.get("touches_sensitive") or not a.get("reversible_under_hour"):
        return "T3"
    if a.get("changes_contract") or a.get("consumers") == "many":
        return "T2"
    if a.get("crosses_boundary") or a.get("consumers") == "some":
        return "T1"
    return "T0"


REQUIRED = {"T0": [], "T1": ["01"], "T2": ["01", "02", "03", "05", "06", "07"],
            "T3": ["01", "02", "03", "04", "05", "06", "07"]}


def required_artifacts(tier):
    return REQUIRED.get(tier, [])


def main():
    answers = {}
    for key, prompt in QUESTIONS:
        raw = input(prompt).strip().lower()
        answers[key] = raw if key == "consumers" else raw.startswith("y")
    tier = compute_tier(answers)
    out = {"answers": answers, "tier": tier, "override": None, "override_reason": None}
    path = os.path.join(".", "00-intake.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print("tier %s (artifacts required: %s) written to %s"
          % (tier, ", ".join(required_artifacts(tier)) or "none", path))
    sys.exit(0)


if __name__ == "__main__":
    main()
