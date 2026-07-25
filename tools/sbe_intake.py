#!/usr/bin/env python3
"""BrotherSBE intake: five objective questions in, one tier out.

The tier decides how much dossier a task gets, which is the mechanism behind
"brief always": a one line fix produces nothing, a new system produces the full
set. The rule is a decision table, not a judgment, so two engineers classifying
the same task land on the same tier.

Every answer is read for MEANING, never for truthiness. This function used to
test `a.get("touches_sensitive")` directly, and the tool's own prompts teach the
answers "y" and "n", so an intake written in the vocabulary this file asks for
computed the wrong tier in both directions at once: five answers of "n" computed
T3, because the string "n" is truthy, and `consumers: "several"` computed T0,
because it matched neither "some" nor "many" and fell through to the lowest tier.
The first blocks honest work at maximum ceremony, which is how a gate gets
switched off; the second silently decides that a change owes no evidence at all,
and the re-derivation in sbe_design.py then agrees with it, because it recomputes
the same wrong answer from the same unread strings.

So the vocabulary is explicit, it is shared (sbe_checks.boolean_answer, beside
VACUOUS_VALUES, imported by everything), and a value outside it is REFUSED by
name rather than guessed at, exactly as sbe_decide.py reports an unrecognized
criterion value instead of ignoring it.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbe_checks import boolean_answer, BOOLEAN_VOCABULARY

QUESTIONS = [
    ("changes_contract", "Does this change a data model, an API contract, or a file interface others depend on? (y/n) "),
    ("crosses_boundary", "Does it cross a service, system, or team boundary? (y/n) "),
    ("reversible_under_hour", "Is it reversible in under an hour? (y/n) "),
    ("touches_sensitive", "Does it touch money, partner data, personal data, or production state? (y/n) "),
    ("consumers", "How many downstream consumers break if it is wrong? (none/some/many) "),
]

TIERS = ("T0", "T1", "T2", "T3")
# The one question that is not a yes/no. Its vocabulary is named here so the
# prompt, the refusal message and the rule all read from the same tuple.
CONSUMERS = "consumers"
CONSUMER_VALUES = ("none", "some", "many")


class UnreadableIntake(ValueError):
    """One or more answers the tier rule could not interpret, named one per line.

    Raised rather than defaulted. A tier is the size of the evidence a change
    owes, so guessing at an answer nobody can read is guessing at how much of
    this project's machinery applies, and the two guesses available (treat it as
    a yes, treat it as a no) are the two failures this class exists to prevent.
    """

    def __init__(self, problems):
        self.problems = list(problems)
        ValueError.__init__(self, "; ".join(self.problems))


def read_answers(a):
    """(values, problems): every answer as the meaning it records, or named as unreadable.

    `values` holds only the answers that were read. `problems` holds one sentence
    per answer that was not, naming the field, quoting the value received, and
    listing the vocabulary that would have been accepted, so a typo is
    distinguishable from an omission and from a lie.
    """
    values, problems = {}, []
    for key, _prompt in QUESTIONS:
        raw = (a or {}).get(key)
        if key == CONSUMERS:
            v = " ".join(str(raw).split()).casefold() if isinstance(raw, str) else raw
            if v in CONSUMER_VALUES:
                values[key] = v
            else:
                problems.append("%s=%r is not a recognized value (accepted: %s)"
                                % (key, raw, ", ".join(CONSUMER_VALUES)))
            continue
        b = boolean_answer(raw)
        if b is None:
            problems.append("%s=%r is not a recognized value (accepted: %s, or a JSON boolean)"
                            % (key, raw, ", ".join(BOOLEAN_VOCABULARY)))
        else:
            values[key] = b
    return values, problems


def compute_tier(a):
    """Named inputs, one output. Highest matching rule wins.

    Raises UnreadableIntake if any of the five answers is not in the accepted
    vocabulary. There is no lenient mode: the caller that wants to report the
    problem rather than raise calls read_answers() and prints the sentences.
    """
    v, problems = read_answers(a)
    if problems:
        raise UnreadableIntake(problems)
    if v["touches_sensitive"] or not v["reversible_under_hour"]:
        return "T3"
    if v["changes_contract"] or v[CONSUMERS] == "many":
        return "T2"
    if v["crosses_boundary"] or v[CONSUMERS] == "some":
        return "T1"
    return "T0"


REQUIRED = {"T0": [], "T1": ["01"], "T2": ["01", "02", "03", "05", "06", "07"],
            "T3": ["01", "02", "03", "04", "05", "06", "07"]}


def required_artifacts(tier):
    """The artifact numbers this tier owes. An unknown tier is refused, not zero.

    Returning [] for a tier outside TIERS made "this tier requires nothing" the
    default answer for a typo, and the one caller that stands between this
    function and a silent no-requirement is a single `if` in another file.
    """
    if tier not in REQUIRED:
        raise ValueError("unknown tier %r (expected one of %s); a tier nothing recognizes "
                         "requires nothing, which is the wrong default for a rule that "
                         "decides how much evidence a change owes" % (tier, ", ".join(TIERS)))
    return REQUIRED[tier]


def ask(key, prompt):
    """One question, re-asked until the answer is in the accepted vocabulary.

    The prompt teaches y/n and the file used to accept anything, reading only
    whether the reply began with the letter y: "nope" was a no and so was
    "yes, but only in staging". A reply this tool cannot read is refused here,
    where the person who typed it is still sitting there, rather than written to
    00-intake.json for a gate to misread three commits later.
    """
    while True:
        try:
            raw = input(prompt)
        except EOFError:
            # Not swallowed: this is the named failure path for a closed stdin,
            # which used to end in an unhandled traceback that read as a broken
            # tool rather than as "nobody answered".
            print("\nsbe_intake: stdin closed before %s was answered; nothing was written." % key)
            sys.exit(1)
        values, problems = read_answers({key: raw})
        if key in values:
            return values[key]
        print("  %s" % next(p for p in problems if p.startswith(key + "=")))


USAGE = """usage: sbe_intake.py [DIRECTORY]

Asks the five intake questions and writes 00-intake.json into DIRECTORY
(default: the current directory).

Give it the dossier directory. This tool used to take no argument at all: it
accepted one, ignored it, and wrote to wherever it was run from, and the README
shows it being run from a repository root. A stray 00-intake.json in a root is
its own dossier, and design/ below it is another, so the file lands where it
does not belong and the reader is told it worked."""


def main():
    argv = sys.argv[1:]
    if any(a in ("-h", "--help") for a in argv):
        print(USAGE)
        sys.exit(0)
    flags = [a for a in argv if a.startswith("-")]
    if flags:
        print("sbe_intake: %s is not an option.\n\n%s" % (", ".join(flags), USAGE))
        sys.exit(1)
    if len(argv) > 1:
        print("sbe_intake: one directory at a time, got %d (%s).\n\n%s"
              % (len(argv), ", ".join(argv), USAGE))
        sys.exit(1)
    where = argv[0] if argv else "."
    if not os.path.isdir(where):
        print("sbe_intake: %r is not a directory, so nothing was written. Create the dossier "
              "directory first, then run this in it.\n\n%s" % (where, USAGE))
        sys.exit(1)
    answers = {}
    for key, prompt in QUESTIONS:
        answers[key] = ask(key, prompt)
    tier = compute_tier(answers)
    out = {"answers": answers, "tier": tier, "override": None, "override_reason": None}
    path = os.path.join(where, "00-intake.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print("tier %s (artifacts required: %s) written to %s"
          % (tier, ", ".join(required_artifacts(tier)) or "none", path))
    sys.exit(0)


if __name__ == "__main__":
    main()
