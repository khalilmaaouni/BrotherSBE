"""One truthful, blocker-first answer to "where does this change stand", so an
engineer never has to assemble it from six commands by hand. Adoption friction
is an assurance defect: a control nobody runs protects nothing.

THE KILL CRITERION THIS MODULE IS BUILT AROUND, quoted from the wave 8 spec
because it is the whole point: if a truthful summary cannot be produced
without this file running the suites (`tools/test_sbe_*.py`,
`evals/run_evals.py`) or becoming a second gate runner (`sbe_design.py`,
`sbe_gate.py`, `sbe_score.py`), it stops and says so rather than run them.
Nothing in this file starts a subprocess and nothing in it computes a NEW
verdict over source code. It reads state other commands already recorded:
`sbe evidence` receipts, the `sbe task` registry, an intake file, a
disposition file, and the diff itself (read the same way `sbe impact` already
reads it, by importing that module rather than re-typing the git plumbing).
A design, gate or score FAIL surfaced here is read out of an EXISTING,
already-verified evidence receipt someone generated with `sbe evidence run`;
a check this project owns but nobody ran a receipt for is reported under
MISSING EVIDENCE, never invented as a FAIL this module discovered on its own.

WHERE THIS MODULE LOOKS, stated because a store this module does not check is
a store whose absence must never read as clean:

  intake            <root>/00-intake.json
  disposition       <root>/disposition.json
  evidence store    <root>/.sbe/evidence/  (recursively, every *.json)
  task registry     <root>/.sbe/tasks.json

These are flat, single-dossier conventions, the same ones `tools/
test_sbe_impact.py`'s own fixtures already write to. A dossier nested under
`design/<change>/` is not discovered by this wave; that is a stated limit,
not a silent gap, and it means a repository that only ever writes those files
under a dossier subdirectory sees every section read NO-DATA here even
though the files exist elsewhere on disk.

ACTIVE CONFLICTS reuses wave 5's overlap scan by calling `tasks.load_registry`,
`tasks.open_tasks` and `tasks.claims_overlap` directly, the same three
functions `sbe task check` itself calls; there is no second copy of the
overlap rule in this file.

HOW A DESIGN/GATE/SCORE FAIL IS RECOGNIZED, stated as the heuristic it is:
a receipt whose `sbe evidence verify` verdict is PASS (the receipt itself is
trustworthy: sealed, current, every covered file intact) is inspected for
which of design/gate/score its `argv` names, by substring match on the
recorded command line (`verify` counts as all three, `review` counts as
gate and score, and each of `design`/`gate`/`score` counts for itself). A
receipt whose recorded `exitCode` is nonzero is a MERGE BLOCKER: the run was
made, it failed, and evidence of that failure already exists. A receipt this
module cannot classify into any kind still counts toward MERGE BLOCKERS or
the clean-evidence tally by its exit code; it just cannot clear a MISSING
EVIDENCE entry for a kind it does not name. A receipt whose own verify() is
NO-DATA (advisory: a dirty tree at generation time, or no covered file) is
neither a broken claim nor clean evidence, and is not otherwise pinned in a
section; it is counted in the evidence scope note.

Python floor is 3.9: no match statements, no `X | Y` annotations. Standard
library only. Maturity: INTERNAL-EVAL, exercised on this repository's
fixtures and on no other estate.
"""
import io
import json
import os
import time

from . import SCHEMA_VERSION, version
from . import evidence as evidence_mod
from . import impact as impact_mod
from . import tasks as tasks_mod
from . import work as work_mod
from .impact import DiffUnavailable, _git  # noqa: E402  (the same private helper evidence.py reuses)

#: The three checks `sbe verify` runs, and the command line that would record
#: evidence for each. Named here once so MISSING EVIDENCE and the receipt
#: classifier read from the same table.
CHECK_KINDS = (
    ("design", "design completeness check", "bin/sbe design --strict <dossier>"),
    ("gate", "hard gate", "bin/sbe gate <dossier>"),
    ("score", "scored surface", "bin/sbe score --strict <dossier>"),
)

INTAKE_REL = "00-intake.json"
DISPOSITION_REL = "disposition.json"

SECTION_NAMES = ("BROKEN CLAIMS", "MERGE BLOCKERS", "ACTIVE CONFLICTS", "MISSING EVIDENCE",
                 "COMPLETED EVIDENCE")


def _iso(epoch):
    """ISO 8601 in UTC, to the second, with an explicit Z: the same spelling
    the evidence receipts and the task registry use."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _git_head(root):
    """The current HEAD sha in `root`, or None when git cannot answer for it.

    None is a real answer, never guessed at: every caller that needs a head
    commit to compare against treats None as NO-DATA for that comparison
    rather than skipping the comparison in silence.
    """
    try:
        code, out, _err = _git(["rev-parse", "HEAD"], root)
    except OSError:
        return None  # sbe: allow-silent every caller renders None as NO-DATA with a reason, per this docstring; a machine with no git gets an honest absence, not a crash
    return out.strip() if code == 0 and out.strip() else None


def _receipt_kinds(receipt):
    """Which of design/gate/score this receipt's recorded argv names.

    Substring match on the joined, lowered argv, stated as a heuristic in the
    module docstring: `verify` covers all three (it runs all three), `review`
    covers gate and score (it runs those two), and each of design/gate/score
    covers itself. A receipt whose command names none of these clears no
    MISSING EVIDENCE entry, which is the honest outcome for a command this
    module cannot read as one of the three named checks.
    """
    argv = " ".join(str(a) for a in (receipt.get("argv") or [])).lower()
    kinds = set()
    if "verify" in argv:
        kinds |= set(("design", "gate", "score"))
    if "review" in argv:
        kinds |= set(("gate", "score"))
    for kind, _label, _cmd in CHECK_KINDS:
        if kind in argv:
            kinds.add(kind)
    return kinds


def _scan_evidence(root, evidence_dir):
    """Every *.json under the evidence store, verified and classified.

    Returns a dict: `broken` (BROKEN CLAIMS items), `clean` (the receipts
    that verify PASS with a zero exit code), `failing` (MERGE BLOCKERS items,
    a verified receipt recording a nonzero exit code), `kindsCovered` (the
    set of design/gate/score kinds ANY verified receipt, passing or failing,
    names), `count`, `inspected` (whether the store existed to look at) and
    `note` (the scope sentence every caller prints, either way).
    """
    broken, clean, failing = [], [], []
    kinds_covered = set()
    if not os.path.isdir(evidence_dir):
        return {"broken": broken, "clean": clean, "failing": failing,
                "kindsCovered": kinds_covered, "count": 0, "inspected": False,
                "note": "no evidence store found at %s" % evidence_dir}
    paths = []
    for dirpath, _dirnames, filenames in os.walk(evidence_dir):
        for name in filenames:
            if name.endswith(".json"):
                paths.append(os.path.join(dirpath, name))
    paths.sort()
    for full in paths:
        rel = os.path.relpath(full, root)
        result = evidence_mod.verify(full, cwd=root)
        verdict = result["verdict"]
        if verdict == "FAIL":
            broken.append({
                "finding": "receipt %s fails verify: %s" % (rel, "; ".join(result["reasons"])),
                "remedy": "the receipt no longer proves anything; re-run the command through "
                          "`sbe evidence run` to produce a fresh one",
            })
            continue
        if verdict == "NO-DATA":
            # Advisory (a dirty tree at generation, or no covered file): not a
            # broken claim, and not clean evidence either. Counted in the note
            # only, per the module docstring, never silently dropped.
            continue
        receipt = result["receipt"] or {}
        kinds_covered |= _receipt_kinds(receipt)
        trust = result["trust"]
        exit_code = receipt.get("exitCode")
        argv_text = " ".join(str(a) for a in (receipt.get("argv") or []))
        if exit_code == 0:
            head = _git_head(root)
            clean.append({
                "finding": "receipt %s verifies as sound evidence, trust %s (command: %s; "
                          "scope: this receipt's covered files against HEAD %s, nothing "
                          "beyond them)"
                          % (rel, trust, argv_text or "not recorded",
                             head[:7] if head else "unknown"),
                "remedy": "no action; this receipt is sound evidence",
                "path": rel, "trust": trust,
            })
        else:
            failing.append({
                "finding": "receipt %s verifies as trustworthy but records exit code %s for "
                          "`%s`, trust %s" % (rel, exit_code, argv_text or "(argv not recorded)",
                                              trust),
                "remedy": "fix the underlying failure and re-run to produce a new passing "
                         "receipt; see %s" % rel,
                "path": rel,
                "coveredFiles": [cf.get("path") for cf in (receipt.get("coveredFiles") or [])
                                if isinstance(cf, dict) and cf.get("path")],
            })
    note = (("%d receipt(s) found under %s" % (len(paths), evidence_dir)) if paths
           else "evidence store %s exists and holds no receipt" % evidence_dir)
    return {"broken": broken, "clean": clean, "failing": failing,
            "kindsCovered": kinds_covered, "count": len(paths), "inspected": True, "note": note}


def _scan_tasks(root, reg_path):
    """The task registry read for ACTIVE CONFLICTS and FORCED closes.

    The overlap scan is `tasks.claims_overlap` over `tasks.open_tasks`, the
    exact functions `sbe task check` runs; nothing here re-derives the
    overlap rule. A registry that exists and cannot be read is named as such,
    never read as zero conflicts, because an unreadable registry still
    records somebody's open fences (see `tasks.RegistryUnusable`).
    """
    conflicts, forced = [], []
    if not os.path.exists(reg_path):
        return {"conflicts": conflicts, "forced": forced, "inspected": False,
                "note": "no task registry found at %s" % reg_path, "openCount": 0}
    try:
        data = tasks_mod.load_registry(root)
    except tasks_mod.RegistryUnusable as exc:
        return {"conflicts": conflicts, "forced": forced, "inspected": False,
                "note": "task registry at %s could not be read: %s" % (reg_path, exc),
                "openCount": None}
    live = tasks_mod.open_tasks(data)
    seen_pairs = set()
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            for pa in a.get("ownedPaths") or []:
                for pb in b.get("ownedPaths") or []:
                    if tasks_mod.claims_overlap(pa, pb, root):
                        key = (a["id"], pa, b["id"], pb)
                        if key in seen_pairs:
                            continue
                        seen_pairs.add(key)
                        conflicts.append({
                            "finding": "task %s owns %r and task %s owns %r; two open "
                                      "writers overlap" % (a["id"], pa, b["id"], pb),
                            "remedy": "queue the writers: task %s and task %s both claim "
                                     "overlapping scope, one must close or narrow its owned "
                                     "paths before both proceed" % (a["id"], b["id"]),
                        })
    for t in data.get("tasks", []):
        if t.get("status") == "closed" and "forced" in t:
            f = t.get("forced") or {}
            forced.append({
                "finding": "task %s was closed FORCED by %s (%s)"
                          % (t.get("id"), f.get("who"), f.get("why")),
                "remedy": "review the forced disposition on task %s before merging, or "
                         "address the named violations: %s"
                         % (t.get("id"), ", ".join(f.get("violations") or []) or "(none)"),
            })
    note = ("%d open task(s) among %d total, read from %s"
           % (len(live), len(data.get("tasks", [])), reg_path))
    return {"conflicts": conflicts, "forced": forced, "inspected": True, "note": note,
            "openCount": len(live)}


def _scope_sentence(scope):
    """The sentence every positive or empty line carries, naming exactly
    which stores this run read. Every positive statement names its inspected
    scope; this is the one sentence that names it."""
    si = scope.get("storesInspected", {})
    parts = [
        "intake %s" % (si.get("intake") or "absent"),
        "disposition %s" % (si.get("disposition") or "absent"),
        "evidence store %s" % (si.get("evidenceDir") or "absent"),
        "task registry %s" % (si.get("taskRegistry") or "absent"),
        "diff %s" % (scope.get("diffRange") or ("NO-DATA: %s" % scope.get("diffProblem")
                                                if scope.get("diffProblem") else "NO-DATA")),
    ]
    return "scope: " + "; ".join(parts)


def _section_line(items, inspected, detail):
    """The empty-state line for one section: NO-DATA when nothing was there
    to inspect, a clean-scope line when something was inspected and found
    nothing to report."""
    if items:
        return None
    return ("NO-DATA. scope: %s" % detail) if not inspected else ("clean. scope: %s" % detail)


def _next_action(sections, scope):
    for name, items in zip(SECTION_NAMES, sections):
        if items:
            return "%s (%s) %s" % (items[0]["remedy"], name, _scope_sentence(scope))
    return "nothing blocking here that this tool can see. %s" % _scope_sentence(scope)


def build_report(path, base=None, now=None):
    """The whole `sbe status` verdict: six sections, blocker-first, plus the
    scope this run actually read. Raises nothing; every failure to read a
    store becomes a NO-DATA note in that store's section instead."""
    root = os.path.abspath(path)
    now = time.time() if now is None else now

    broken_claims, merge_blockers, active_conflicts = [], [], []
    missing_evidence, sound_evidence = [], []

    intake_path = os.path.join(root, INTAKE_REL)
    disposition_path = os.path.join(root, DISPOSITION_REL)
    evidence_dir = os.path.join(root, tasks_mod.DEFAULT_EVIDENCE_DIR)
    reg_path = tasks_mod.registry_path(root)

    head_sha = _git_head(root)
    scope = {
        "root": root,
        "base": base,
        "headCommit": head_sha,
        "storesInspected": {
            "intake": intake_path if os.path.exists(intake_path) else None,
            "disposition": disposition_path if os.path.exists(disposition_path) else None,
            "evidenceDir": evidence_dir if os.path.isdir(evidence_dir) else None,
            "taskRegistry": reg_path if os.path.exists(reg_path) else None,
        },
        "diffRange": None,
        "diffProblem": None,
    }

    # ---- Evidence store: BROKEN CLAIMS, the sound receipts, and the
    # exit-code-failing receipts that belong under MERGE BLOCKERS. ----
    ev = _scan_evidence(root, evidence_dir)
    broken_claims.extend(ev["broken"])
    sound_evidence.extend(ev["clean"])
    merge_blockers.extend(ev["failing"])

    # ---- Disposition staleness: BROKEN CLAIMS. ----
    if os.path.exists(disposition_path) and head_sha:
        _live, disp_note = impact_mod.read_disposition(disposition_path, head_sha)
        if disp_note:
            broken_claims.append({
                "finding": "disposition file %s: %s" % (disposition_path, disp_note),
                "remedy": "record a fresh disposition against head %s naming who decided "
                         "and why" % head_sha[:12],
            })

    # ---- Task registry: ACTIVE CONFLICTS and FORCED closes. ----
    tk = _scan_tasks(root, reg_path)
    active_conflicts.extend(tk["conflicts"])
    merge_blockers.extend(tk["forced"])

    # ---- Intake vs diff reconciliation, read exactly as `sbe impact` reads
    # it: this is analysis of a diff and two small JSON files, never a
    # subprocess and never a new gate run. ----
    human_tier, _answers, intake_problem = impact_mod.read_intake(intake_path)
    idata = None
    try:
        idata = impact_mod.report(
            root, base=base, head="HEAD",
            intake_path=intake_path if os.path.exists(intake_path) else None,
            disposition_path=disposition_path if os.path.exists(disposition_path) else None)
        scope["diffRange"] = idata["scope"]
    except DiffUnavailable as exc:
        scope["diffProblem"] = str(exc)

    if intake_problem and human_tier is None and os.path.exists(intake_path):
        merge_blockers.append({
            "finding": "intake at %s cannot be read: %s" % (intake_path, intake_problem),
            "remedy": "fix 00-intake.json so its five answers parse in the accepted "
                     "vocabulary, then re-run status",
        })
    if idata is not None:
        for d in idata["disagreements"]:
            if d["disposition"] != "missing":
                continue
            merge_blockers.append({
                "finding": "intake declared %s but the diff shows %s (detector %s on %s, no "
                          "disposition)" % (human_tier, idata["proposedTier"], d["detector"],
                                            d["file"]),
                "remedy": "record a disposition for %s naming who decided and why, against "
                         "head %s, or revise the declared tier"
                         % (d["detector"], (head_sha or idata.get("headCommit") or "?")[:12]),
            })

    # ---- MISSING EVIDENCE: only when a tier is known and owes something. ----
    if human_tier not in (None, "T0"):
        for kind, label, cmdline in CHECK_KINDS:
            if kind not in ev["kindsCovered"]:
                missing_evidence.append({
                    "finding": "no evidence receipt records a %s run, and declared tier %s "
                              "owes one" % (label, human_tier),
                    "remedy": "run `%s` through `sbe evidence run` to record it" % cmdline,
                })

    sections = (broken_claims, merge_blockers, active_conflicts, missing_evidence,
               sound_evidence)
    next_action = _next_action(sections, scope)

    notes = {
        "brokenClaims": _section_line(
            broken_claims, ev["inspected"] or os.path.exists(disposition_path),
            "%s; disposition %s" % (ev["note"], "present" if os.path.exists(disposition_path)
                                    else "absent")),
        "mergeBlockers": _section_line(
            merge_blockers,
            os.path.exists(intake_path) or tk["inspected"] or ev["count"] > 0
            or idata is not None,
            "intake %s (tier %s); %s; %s"
            % (intake_path if os.path.exists(intake_path) else "absent",
               human_tier or "unknown", tk["note"],
               idata["scope"] if idata is not None else
               ("diff NO-DATA: %s" % scope["diffProblem"]))),
        "activeConflicts": _section_line(active_conflicts, tk["inspected"], tk["note"]),
        "missingEvidence": _section_line(
            missing_evidence, os.path.exists(intake_path) and human_tier is not None,
            "declared tier %s from %s" % (human_tier or "unknown",
                                          intake_path if os.path.exists(intake_path)
                                          else "no intake file")),
        "soundEvidence": _section_line(sound_evidence, ev["inspected"], ev["note"]),
    }

    return {
        "schemaVersion": SCHEMA_VERSION,
        "tool": "sbe status",
        "toolVersion": version(),
        "generatedAt": _iso(now),
        "root": root,
        "scope": scope,
        "brokenClaims": broken_claims,
        "mergeBlockers": merge_blockers,
        "activeConflicts": active_conflicts,
        "missingEvidence": missing_evidence,
        "soundEvidence": sound_evidence,
        "notes": notes,
        "nextAction": next_action,
    }


def any_blocking(data):
    """True when any of sections 1-4 (never section 5) carries an item; the
    exit-code rule, in one place so the CLI and any future caller agree."""
    return bool(data["brokenClaims"] or data["mergeBlockers"] or data["activeConflicts"]
               or data["missingEvidence"])


def render_text(data):
    out = ["sbe status: %s" % data["root"]]
    section_pairs = (
        ("BROKEN CLAIMS", data["brokenClaims"], data["notes"]["brokenClaims"]),
        ("MERGE BLOCKERS", data["mergeBlockers"], data["notes"]["mergeBlockers"]),
        ("ACTIVE CONFLICTS", data["activeConflicts"], data["notes"]["activeConflicts"]),
        ("MISSING EVIDENCE", data["missingEvidence"], data["notes"]["missingEvidence"]),
        ("COMPLETED EVIDENCE", data["soundEvidence"], data["notes"]["soundEvidence"]),
    )
    for name, items, empty_note in section_pairs:
        out.append("")
        out.append("%s:" % name)
        if items:
            for item in items:
                out.append("  - %s" % item["finding"])
        else:
            out.append("  %s" % empty_note)
    out.append("")
    out.append("NEXT ACTION: %s" % data["nextAction"])
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# The team view: every active change in one blocker-first report.
# Spec: docs/specs/2026-07-30-sbe-status-team.md. Zero network by design:
# approval facts come only from a saved 10-approval.json, and their staleness
# against the current head is DERIVED and labeled so. Findings carry a
# `basis` honesty field: observed (read this run), derived (computed from
# observed values), unavailable (a source that could not be read, which keeps
# its severity slot visible instead of vanishing).
# ---------------------------------------------------------------------------

TEAM_SEVERITIES = {
    1: "broken claims", 2: "merge blockers", 3: "scope conflicts",
    4: "stale evidence", 5: "missing approvals", 6: "convergence failures",
    7: "active tasks", 8: "ready tasks", 9: "completed changes",
    10: "next action",
}


def _finding(change, severity, verdict, evidence, commit, owner, next_action, basis,
             detail):
    return {"change": change, "severity": severity, "verdict": verdict,
            "evidence": evidence, "commit": commit, "owner": owner,
            "nextAction": next_action, "basis": basis, "detail": detail}


def _design_roots(root):
    """(roots, refusals). `roots` is every directory (relative to `root`) safe
    to walk for dossiers: the default "design" plus any designRoots entry from
    .sbe/team-profile.json that resolves INSIDE the repository root. An entry
    that would resolve outside the root (a ".." escape, or an absolute path
    elsewhere on disk) is never added to `roots` and never walked; it comes
    back in `refusals`, by its own literal spelling, so the caller can surface
    a visible refusal instead of a silent skip or a directory traversal."""
    roots = ["design"]
    refusals = []
    profile = os.path.join(root, ".sbe", "team-profile.json")
    if os.path.isfile(profile):
        try:
            extra = json.loads(io.open(profile, encoding="utf-8").read())
        except (ValueError, OSError):
            extra = None  # sbe: allow-silent  (not silent: the profile is optional
            #        config; a broken one leaves the default root and discovery
            #        still runs, and is not itself a containment problem)
        root_abs = os.path.abspath(root)
        for entry in ((extra.get("designRoots", []) or []) if extra else []):
            if not isinstance(entry, str) or not entry.strip():
                continue
            candidate = os.path.abspath(os.path.join(root, entry))
            if candidate == root_abs or candidate.startswith(root_abs + os.sep):
                if entry not in roots:
                    roots.append(entry)
            else:
                refusals.append(entry)
    return roots, refusals


def _team_changes(root):
    """([(name, dossier path)], refusals): every dossier discovered under a
    safe root, plus any designRoots entry `_design_roots` refused."""
    changes = []
    roots, refusals = _design_roots(root)
    for rel in roots:
        base_dir = os.path.join(root, rel)
        if not os.path.isdir(base_dir):
            continue
        for name in sorted(os.listdir(base_dir)):
            doss = os.path.join(base_dir, name)
            if os.path.isfile(os.path.join(doss, "00-intake.json")):
                changes.append((name, doss))
    return changes, refusals


def _read_json_or_none(path):
    try:
        return json.loads(io.open(path, encoding="utf-8").read())
    except (ValueError, OSError):
        return None


def _closed_clean(records):
    """True when at least one record for a task id is closed, and not FORCED.
    A FORCED close records a disposition, never a completion; see
    `work._dependency_problem`, whose rule this mirrors rather than retypes."""
    return any(r.get("status") == "closed" and not r.get("forced") for r in records)


def build_team_report(path):
    """{"root", "headCommit", "changes": [names], "findings": [...]}, findings
    sorted most severe first, deterministically."""
    root = os.path.abspath(path)
    head = _git_head(root)
    findings = []
    changes, root_refusals = _team_changes(root)

    for entry in root_refusals:
        findings.append(_finding(
            "(team-profile.json)", 3, "FAIL", entry, head, None,
            "point designRoots entry %r in .sbe/team-profile.json at a directory "
            "inside this repository, or remove the entry" % entry,
            "unavailable",
            "designRoots entry %r resolves outside the repository root and was "
            "REFUSED: it is not walked for dossiers, and no dossier under it is "
            "discovered" % entry))

    registry_tasks, registry_problem, registry_data = [], None, None
    try:
        registry_data = tasks_mod.load_registry(root)
        registry_tasks = registry_data.get("tasks", [])
    except tasks_mod.RegistryUnusable as exc:
        registry_problem = str(exc)

    evidence_dir = os.path.join(root, tasks_mod.DEFAULT_EVIDENCE_DIR)
    ev = _scan_evidence(root, evidence_dir)

    open_by_change = {}
    plan_owns_by_change = {}
    for name, doss in changes:
        change_start = len(findings)
        plan = _read_json_or_none(os.path.join(doss, "08-plan.json"))
        plan_ids = set()
        plan_owns = set()
        commands = 0
        if plan:
            for task in plan.get("tasks", []):
                plan_ids.add(task.get("id"))
                commands += len(task.get("verificationCommands", []))
                for p in task.get("owns") or []:
                    if isinstance(p, str) and p.strip():
                        plan_owns.add(p)
        plan_owns_by_change[name] = plan_owns

        if registry_problem:
            findings.append(_finding(
                name, 3, "NO-DATA", tasks_mod.registry_path(root), head, None,
                "restore the registry file; its contents still record open fences",
                "unavailable",
                "the task registry could not be read (%s), so scope conflicts for this "
                "change are unknowable and this slot stays visible" % registry_problem))
            records = []
        else:
            records = [r for r in registry_tasks if r.get("id") in plan_ids] if plan else []
        open_records = [r for r in records if r.get("status") == "open"]
        open_by_change[name] = open_records

        for rec in records:
            if "forced" in str(rec.get("status", "")) or rec.get("forced"):
                findings.append(_finding(
                    name, 7, "FAIL", "task %s" % rec.get("id"), head,
                    rec.get("agent"),
                    "a FORCED close never satisfies a dependent; redo the task cleanly "
                    "or record why it stands",
                    "observed",
                    "task %s was closed FORCED by %s and stays loud everywhere it "
                    "appears" % (rec.get("id"), rec.get("agent"))))

        for rec in open_records:
            findings.append(_finding(
                name, 7, "NO-DATA", "task %s" % rec.get("id"), head, rec.get("agent"),
                "finish or check the task with sbe work", "observed",
                "task %s is open, held by %s" % (rec.get("id"), rec.get("agent"))))

            # Severity 2: a receipt-free MERGE BLOCKER this run can actually
            # see for itself, an open task whose tree already violates its own
            # declaration, read by the SAME postcondition `sbe task close`
            # would refuse against; no second copy of that rule lives here.
            base_commit = rec.get("baseCommit")
            if not base_commit:
                findings.append(_finding(
                    name, 2, "NO-DATA", "task %s" % rec.get("id"), head, rec.get("agent"),
                    "record a baseCommit on task %s so its declared scope can be "
                    "checked against what actually changed" % rec.get("id"),
                    "unavailable",
                    "task %s carries no baseCommit, so its postcondition against "
                    "declared ownership cannot be computed" % rec.get("id")))
            else:
                try:
                    post = tasks_mod.postcondition(root, rec, evidence_dir)
                except tasks_mod.DiffUnavailable as exc:
                    findings.append(_finding(
                        name, 2, "NO-DATA", "task %s" % rec.get("id"), head,
                        rec.get("agent"),
                        "restore the declared worktree or base commit for task %s so "
                        "its scope can be checked" % rec.get("id"),
                        "unavailable",
                        "the postcondition for task %s could not be computed: %s"
                        % (rec.get("id"), exc)))
                else:
                    bad = list(post["violations"]) + list(post.get("receiptViolations")
                                                          or [])
                    if bad:
                        findings.append(_finding(
                            name, 2, "FAIL", "task %s" % rec.get("id"), head,
                            rec.get("agent"),
                            "task %s changed %s outside its declared ownership; narrow "
                            "the change or widen the declaration before closing"
                            % (rec.get("id"), ", ".join(bad)),
                            "observed",
                            "task %s's tree carries change(s) outside its declared "
                            "ownedPaths: %s" % (rec.get("id"), ", ".join(bad))))

        if not plan:
            findings.append(_finding(
                name, 8, "NO-DATA", os.path.join(doss, "08-plan.json"), head, None,
                "run sbe plan %s --write to derive the task graph" % doss,
                "observed",
                "no plan exists for this change yet, so there are no tasks to ready: "
                "a starting state to move past, not a ready task and not an error"))
        else:
            conv = _read_json_or_none(os.path.join(doss, "09-convergence.json"))
            if conv is None:
                findings.append(_finding(
                    name, 6, "NO-DATA", os.path.join(doss, "09-convergence.json"),
                    head, None,
                    "run sbe converge %s --base <sha> --head <sha>" % doss,
                    "observed",
                    "a plan exists and no convergence report does; unexamined is not "
                    "PASS"))
            else:
                final = conv.get("final")
                bound = conv.get("head")
                if head and bound and bound != head:
                    findings.append(_finding(
                        name, 4, "FAIL", "09-convergence.json", bound, None,
                        "re-run sbe converge against the current head", "derived",
                        "the convergence report binds to %s but the repository head is "
                        "%s: stale" % (bound[:12], head[:12])))
                elif final in ("FAIL", "REVIEW-REQUIRED"):
                    findings.append(_finding(
                        name, 6, final, "09-convergence.json", bound, None,
                        "amend the dossier or the implementation, then regenerate plan, "
                        "evidence and convergence", "observed",
                        "convergence recorded %s" % final))

            approval = _read_json_or_none(os.path.join(doss, "10-approval.json"))
            if approval is None:
                findings.append(_finding(
                    name, 5, "NO-DATA", os.path.join(doss, "10-approval.json"), head,
                    None,
                    "run sbe pr verify and save its --json output as 10-approval.json",
                    "observed",
                    "no approval report is saved for this change; absence is a fact, "
                    "not an accusation"))
            else:
                bound = approval.get("headSha")
                if head and bound and bound != head:
                    findings.append(_finding(
                        name, 4, "FAIL", "10-approval.json", bound, None,
                        "re-run sbe pr verify against the current head", "derived",
                        "the approval report binds to %s but the repository head is %s: "
                        "stale approval" % (bound[:12], head[:12])))
                elif approval.get("final") != "PASS":
                    findings.append(_finding(
                        name, 5, str(approval.get("final")), "10-approval.json", bound,
                        None, "resolve the failing controls on the pull request",
                        "observed",
                        "the saved approval report's FINAL is %s" % approval.get("final")))

            if commands and not ev["clean"] and not ev["broken"]:
                findings.append(_finding(
                    name, 5, "NO-DATA", evidence_dir, head, None,
                    "run the plan's verification commands under sbe evidence run",
                    "observed",
                    "%d verification command(s) planned and no receipt exists yet"
                    % commands))

            # Severities 8 and 9 need the registry to be readable to mean
            # anything; when it is not, the severity-3 unavailable finding
            # above already says so, and neither "ready" nor "completed" is
            # guessed at from data this run could not read.
            if not registry_problem:
                plan_tasks = plan.get("tasks", [])
                records_by_id = {}
                for r in records:
                    records_by_id.setdefault(r.get("id"), []).append(r)

                for task in plan_tasks:
                    tid = task.get("id")
                    task_records = records_by_id.get(tid, [])
                    if task_records:
                        continue  # already started or done: not a "ready" candidate
                    deps = [d for d in (task.get("dependsOn") or []) if isinstance(d, str)]
                    blockers = [work_mod._dependency_problem(registry_data, d)
                               for d in deps]
                    blockers = [b for b in blockers if b]
                    if not blockers:
                        findings.append(_finding(
                            name, 8, "NO-DATA", "task %s" % tid, head, None,
                            "run sbe work start %s --plan %s to begin it"
                            % (tid, os.path.join(doss, "08-plan.json")),
                            "derived",
                            "task %s's dependencies are all closed clean and it carries "
                            "no registry record yet: ready to start" % tid))

                if plan_tasks and all(_closed_clean(records_by_id.get(t.get("id"), []))
                                      for t in plan_tasks):
                    findings.append(_finding(
                        name, 9, "PASS", os.path.join(doss, "08-plan.json"), head, None,
                        "nothing left to do for this change; open a PR and run sbe pr "
                        "verify",
                        "derived",
                        "every task in the plan is closed clean in the registry"))

        # Severity 10: exactly one next action per change, always, derived
        # from that change's own highest-severity finding recorded above (the
        # lowest severity number is the most severe). A change with nothing
        # recorded above still gets one, so the rule never has an exception.
        this_change = findings[change_start:]
        if this_change:
            # Tie-break exactly like the report's own final sort (severity,
            # evidence, detail), so "highest severity" means the same finding
            # a human reading the rendered output would see first, not
            # whichever happened to be appended first during collection.
            top = min(this_change,
                      key=lambda f: (f["severity"], f["evidence"] or "", f["detail"]))
            findings.append(_finding(
                name, 10, top["verdict"], top["evidence"], top["commit"], top["owner"],
                top["nextAction"], "derived",
                "next action for %s, derived from its highest-severity finding "
                "(severity %d, %s): %s"
                % (name, top["severity"], TEAM_SEVERITIES[top["severity"]],
                   top["nextAction"])))
        else:
            findings.append(_finding(
                name, 10, "NO-DATA", None, head, None,
                "nothing is recorded for this change yet", "derived",
                "no finding was recorded for %s at any severity, so there is nothing "
                "to derive a next action from" % name))

    for item in ev["broken"]:
        findings.append(_finding(
            "(shared evidence store)", 1, "FAIL", item.get("finding", "receipt"),
            head, None, item.get("remedy", "regenerate the receipt"), "observed",
            item.get("finding", "a receipt failed verification")))

    for item in ev["failing"]:
        covered = set(item.get("coveredFiles") or [])
        attributed = None
        for name, _doss in changes:
            if covered & plan_owns_by_change.get(name, set()):
                attributed = name
                break
        findings.append(_finding(
            attributed or "(shared evidence store)", 2, "FAIL",
            item.get("path", "receipt"), head, None,
            item.get("remedy", "regenerate the receipt"), "observed",
            item.get("finding", "a receipt recorded a nonzero exit code")))

    names = [n for n, _d in changes]
    # Scope conflicts are computed over ALL open registry records, pairwise,
    # because the registry is one global fence table while plan task ids are
    # per-change (every derived plan starts at T01): attributing first and
    # comparing after would let two changes' fences collide invisibly.
    open_all = [] if registry_problem else [r for r in registry_tasks
                                            if r.get("status") == "open"]
    for i, ra in enumerate(open_all):
        for rb in open_all[i + 1:]:
            shared = sorted(set(ra.get("ownedPaths", []))
                            & set(rb.get("ownedPaths", [])))
            holders = {n for n, recs in open_by_change.items()
                       for r in recs if r is ra or r is rb}
            change_label = ", ".join(sorted(holders)) or "(registry)"
            for pth in shared:
                findings.append(_finding(
                    change_label, 3, "FAIL", pth, head,
                    "%s and %s" % (ra.get("agent"), rb.get("agent")),
                    "serialize the two tasks or split the path", "observed",
                    "open task %s (%s) and open task %s (%s) both own %s"
                    % (ra.get("id"), ra.get("agent"), rb.get("id"),
                       rb.get("agent"), pth)))

    findings.sort(key=lambda f: (f["severity"], f["change"], f["evidence"] or "",
                                 f["detail"]))
    return {"tool": "sbe status --team", "root": root, "headCommit": head,
            "changes": names, "findings": findings,
            "basisLegend": "observed: read this run; derived: computed from observed "
                           "values; unavailable: a source that could not be read and "
                           "stays visible"}


def team_blocking(data):
    return any(1 <= f["severity"] <= 6 for f in data["findings"])


def render_team(data):
    out = ["sbe status --team: %s" % data["root"],
           "head %s, %d change(s): %s"
           % ((data["headCommit"] or "unresolved")[:12], len(data["changes"]),
              ", ".join(data["changes"]) or "none discovered under design/")]
    current = None
    for f in data["findings"]:
        if f["severity"] != current:
            current = f["severity"]
            out.append("")
            out.append("%d. %s" % (current, TEAM_SEVERITIES[current].upper()))
        owner = (" [%s]" % f["owner"]) if f["owner"] else ""
        out.append("  %-10s %-16s %s%s" % (f["change"][:10], f["verdict"], f["detail"],
                                           owner))
        out.append("             next action: %s" % f["nextAction"])
    if not data["findings"]:
        out.append("")
        out.append("no findings: no dossier under design/ has anything recorded to read")
    return "\n".join(out) + "\n"
