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
import os
import time

from . import SCHEMA_VERSION, version
from . import evidence as evidence_mod
from . import impact as impact_mod
from . import tasks as tasks_mod
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
