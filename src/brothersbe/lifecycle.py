"""LANE C1 (B-003): the one reducer that decides "what should happen next"
for a change, so every surface that answers that question agrees BY
CONSTRUCTION instead of by coincidence.

Reproduced before this module existed: `status.py` carried at least two
independent derivations of "the next action" (`build_report`'s blocker-first
`_next_action`, reading only sections 1-4, and `build_team_report`'s
severity-10 finding, picking the minimum RAW team-severity number among
every OTHER finding recorded for a change), and `skills/next/SKILL.md`
carried a THIRD, hand-written priority ladder in prose that re-derived the
same judgement from the same JSON a different way. A temp-dir reproduction
built a single dossier whose only outstanding obligation was review (every
other check clear, its one task closed) and got three different answers:
plain `sbe status` said "nothing blocking here" (it never looked at task or
review state at all), `sbe status --team`'s own severity-10 said "nothing
left to do, open a PR" (severity 9, "completed changes", sorts numerically
below severity 11, "review record", even though review had not run), and
`/brothersbe:next`'s prose ladder said "run review" (its own rung order
puts review before "everything green", unlike team's raw severity numbers).

This module owns the ONE priority ladder now. `status.py`'s `build_report`
and `build_team_report` both build a list of CANDIDATES -- one dict per
outstanding fact worth acting on, each naming a `rung` from the table below
-- and call `reduce_next_action` to pick the single most urgent one. Neither
function invents its own tie-break or its own idea of which comes first.

LOOP B: a FOURTH hand-rolled ladder was found in `handover.py`'s own
`_derive_next_action` (a private `for kind in ("convergence", "approval",
"review"): ...` sequence, checked in that fixed order regardless of this
module's own rungs, followed by its own separate dirty-worktree, receipt,
active-task and ready-task checks). It is now folded in the same way:
`handover.py`'s `_handover_candidates` builds a candidate list, calling
`status.py`'s own `_change_ladder_candidates` directly for the facts that
function already owns (active task, ready task, review, and approval's
NO-DATA/absent verdict, gated on every task being closed clean), and
`status.py`'s own `_approval_ladder_candidate` a second time, unconditionally,
for a recorded approval FAILURE or staleness (ROUND 2: never gated the way
the NO-DATA verdict is, mirroring `status_mod._superseded_by_shared_ladder`'s
identical rule) -- rather than re-deriving any of those judgements a second,
weaker way -- and reduces through `reduce_next_action` exactly like every
other surface here.

Python floor is 3.9: no match statements, no `X | Y` annotations. Standard
library only. This module reads nothing and writes nothing; it is a pure
function over facts its callers already gathered, by the same "never a
second gate runner" law `status.py`'s own module docstring states for
itself.
"""

#: Canonical rung order, most urgent first. The INTEGER VALUES matter only
#: as a sort key (lower sorts first, i.e. wins); the gaps between them are
#: deliberate room to insert a future rung without renumbering every
#: existing one. This is the ONE list every surface's "next action" is
#: picked from -- see `reduce_next_action`.
RUNG_BROKEN_CLAIM = 0
RUNG_MERGE_BLOCKER = 10
RUNG_ACTIVE_CONFLICT = 20
RUNG_STALE_RECORD = 30
RUNG_MISSING_APPROVAL = 40
RUNG_CONVERGENCE_FAILURE = 50
#: LOOP B: `handover.py`'s own candidate for a dirty, uncommitted worktree at
#: the moment a handover is prepared. No fact in `status.py`'s own ladder
#: corresponds to this: a plain `sbe status` never inspects working-tree
#: cleanliness, so this rung is not borrowed from an existing team severity
#: the way `handover.py`'s convergence, approval and review candidates are
#: (see `TEAM_SEVERITY_TO_RUNG`). Placed between convergence failure and
#: missing evidence: uncommitted state risks losing work outright, which
#: `handover.py` has always treated as more urgent than a stale evidence
#: receipt but less urgent than a broken or missing convergence/approval
#: gate (see that module's `_handover_candidates`).
RUNG_UNCOMMITTED_STATE = 52
RUNG_MISSING_EVIDENCE = 55
RUNG_ACTIVE_TASK = 60
RUNG_READY_TASK = 70
RUNG_REVIEW_NOT_CLEARED = 80
RUNG_FINISH = 90

#: (rung, actionId, label). `actionId` is the stable, machine-matchable slug
#: a skill or script can branch on without parsing prose; `label` is the
#: short human name for the same rung. Every candidate's `rung` must be one
#: of these, or `candidate()` refuses it: a rung this table has not been
#: taught about is a programming error in the caller, never a silent
#: fallback to something unrelated.
_RUNGS = (
    (RUNG_BROKEN_CLAIM, "resolve-broken-claim", "broken claim"),
    (RUNG_MERGE_BLOCKER, "resolve-merge-blocker", "merge blocker"),
    (RUNG_ACTIVE_CONFLICT, "resolve-active-conflict", "active conflict"),
    (RUNG_STALE_RECORD, "refresh-stale-record", "stale record"),
    (RUNG_MISSING_APPROVAL, "resolve-missing-approval", "missing approval"),
    (RUNG_CONVERGENCE_FAILURE, "resolve-convergence-failure", "convergence failure"),
    (RUNG_UNCOMMITTED_STATE, "resolve-uncommitted-state", "uncommitted state"),
    (RUNG_MISSING_EVIDENCE, "provide-missing-evidence", "missing evidence"),
    (RUNG_ACTIVE_TASK, "continue-active-task", "active task"),
    (RUNG_READY_TASK, "start-ready-task", "ready task"),
    (RUNG_REVIEW_NOT_CLEARED, "run-review", "review not cleared"),
    (RUNG_FINISH, "finish", "nothing outstanding"),
)
ACTION_ID = dict((rung, action_id) for rung, action_id, _label in _RUNGS)
LABEL = dict((rung, label) for rung, _action_id, label in _RUNGS)

#: `status.py`'s `TEAM_SEVERITIES` (team severity number -> this module's
#: rung), so `build_team_report`'s severity-10 finding is picked through the
#: SAME table `build_report`'s own candidates draw from, rather than a raw
#: integer comparison over severity numbers that were never assigned with
#: "which one wins" in mind.
#:
#: Severity 9 ("completed changes") maps to `RUNG_FINISH`, AFTER severity 11
#: ("review record", `RUNG_REVIEW_NOT_CLEARED`) in this order, even though
#: 9 < 11 as a bare integer. That inversion is deliberate and is the fix
#: this lane exists for: team's raw severity numbering puts "review record"
#: outside 1..6 for an unrelated reason (LT-302's own note in `status.py`,
#: so a missing review never blocks a merge), and picking a next action by
#: raw severity comparison let "nothing left to do, open a pull request"
#: (9) outrank "run review" (11) whenever a change's tasks were all closed
#: clean and review had simply never run -- recommending a merge before
#: anyone had reviewed it. Being reviewed and cleared is a PRECONDITION for
#: "nothing outstanding", not a sibling fact that happens to sort later.
#:
#: Severity 1, 2 and 3 (broken claims, merge blockers, scope conflicts) map
#: onto the identical concepts `build_report`'s own BROKEN CLAIMS, MERGE
#: BLOCKERS and ACTIVE CONFLICTS sections already use those rungs for.
TEAM_SEVERITY_TO_RUNG = {
    1: RUNG_BROKEN_CLAIM,
    2: RUNG_MERGE_BLOCKER,
    3: RUNG_ACTIVE_CONFLICT,
    4: RUNG_STALE_RECORD,
    5: RUNG_MISSING_APPROVAL,
    6: RUNG_CONVERGENCE_FAILURE,
    7: RUNG_ACTIVE_TASK,
    8: RUNG_READY_TASK,
    9: RUNG_FINISH,
    11: RUNG_REVIEW_NOT_CLEARED,
}


def candidate(rung, reason):
    """One outstanding fact worth acting on: `rung` (one of the constants
    above) and `reason` (the recommended action, as text). Extra keys can be
    added to the returned dict by the caller after the fact (team attaches
    its own `verdict`/`evidence`/`commit`/`owner` this way, by starting from
    an existing finding dict and adding `rung` to a copy of it, rather than
    calling this function at all -- see `build_team_report`); the two
    required keys are always present.
    """
    if rung not in ACTION_ID:
        raise ValueError("unknown rung %r; add it to lifecycle._RUNGS first" % (rung,))
    return {"rung": rung, "reason": reason}


def reduce_next_action(candidates):
    """The one reducer. `candidates`: a non-empty iterable of dicts, each
    carrying at least `rung` (one of the constants above) and `reason` (the
    text naming what to do). Extra keys on a candidate are carried through
    unmodified on the winner, so a caller that stashed more than rung/reason
    on its candidates (team's finding fields) can read them straight off the
    dict this function returns rather than looking the winner up a second
    time by identity or by matching text.

    Ties (more than one candidate at the lowest rung present) are broken by
    ORDER: the first such candidate in `candidates` wins. This function
    never re-sorts and never invents its own tie-break -- the caller is
    responsible for handing candidates to this function already in its own
    priority order among equals (`build_team_report` sorts by `(rung,
    evidence, detail)` before calling this, mirroring exactly the tie-break
    this file used before this module existed, so that refactor changed no
    team output), so a change to a tie-break rule stays owned by ONE call
    site, not duplicated here.

    Returns a dict: every key the winning candidate carried, PLUS
    `actionId` (the stable slug), `label` (the human name for the winning
    rung) and `basis` (always `"derived"`: picking the most urgent of
    several already-recorded facts is itself a derivation, never a fact
    freshly observed by this function).

    Raises `ValueError` on an empty `candidates`: every caller must supply
    at least a fallback candidate (its own "nothing outstanding" wording,
    at `RUNG_FINISH`) rather than have this function invent placeholder
    text of its own -- the exact phrasing of "nothing blocking" belongs to
    the caller that has always owned it, not a second copy of it here.
    """
    items = list(candidates)
    if not items:
        raise ValueError(
            "reduce_next_action requires at least one candidate; the caller must always "
            "supply its own fallback (RUNG_FINISH) rather than have this function invent "
            "placeholder text")
    best_rung = min(item["rung"] for item in items)
    winner = next(item for item in items if item["rung"] == best_rung)
    result = dict(winner)
    result["actionId"] = ACTION_ID[best_rung]
    result["label"] = LABEL[best_rung]
    result["basis"] = "derived"
    return result
