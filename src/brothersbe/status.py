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

  intake            <root>/00-intake.json, or <dossier>/00-intake.json per
                     discovered dossier when the flat file above is absent
  disposition       <root>/disposition.json, or <dossier>/disposition.json,
                     matching whichever intake was actually read
  evidence store    <root>/.sbe/evidence/  (recursively, every *.json)
  task registry     <root>/.sbe/tasks.json

The evidence store and task registry are always shared and root-level: read
once, the same way, for the whole repository, exactly as `sbe status --team`
already reads them. Intake and disposition are read flat at `<root>` FIRST,
the same single-dossier convention `tools/test_sbe_impact.py`'s own fixtures
write to, and when that flat `00-intake.json` exists this module's output is
unchanged from every earlier version of this file: the flat layout always
wins and dossier discovery never runs. Only when the flat file is ABSENT does
this module walk for dossiers, through the SAME `_design_roots`/
`_team_changes` machinery `build_team_report` below already uses (the
default `design/` root, plus any `.sbe/team-profile.json` `designRoots`
entry that resolves inside the repository; an entry that would escape the
repository is refused and named as a merge blocker, never silently walked).
Each discovered dossier's own `00-intake.json` and `disposition.json` are
then read in the flat file's place, one target per dossier, and every
finding they produce is labeled with the dossier's name so a reader always
knows which change it came from. A repository that writes neither the flat
files nor any dossier still reads NO-DATA here, exactly as before.

ACTIVE CONFLICTS reuses wave 5's overlap scan by calling `tasks.load_registry`,
`tasks.open_tasks` and `tasks.claims_overlap` directly, the same three
functions `sbe task check` itself calls; there is no second copy of the
overlap rule in this file.

HOW A DESIGN/GATE/SCORE OBLIGATION IS CLEARED, and this changed because the
old answer was a bypass. A receipt whose `sbe evidence verify` verdict is PASS
(the receipt itself is trustworthy: sealed, current, every covered file intact)
clears an obligation only when the receipt DECLARES that kind in its own
`checkKinds` field, read through `evidence.declared_kinds`, which is the single
reader of that field. Nothing here looks at the recorded command line any more.
It used to: the kind was inferred by substring-matching the joined argv, so a
receipt recording `/bin/cat tests/test_design_of_gate_score.txt` named three
obligations and cleared all three, for a command that ran no check at all. That
was reproduced, not theorized.

A receipt that declares no kind is NO-DATA for obligation purposes, never a
silent pass, and the three shapes of that (a receipt older than the field, a
field that does not parse as a kind list, and an honest run that declared
nothing) are each named where MISSING EVIDENCE is reported, so a reader is
never told "no evidence exists" when the truth is "evidence exists and says
nothing about which check it was". A receipt whose recorded `exitCode` is
nonzero is a MERGE BLOCKER whether or not it declares a kind: the run was made,
it failed, and evidence of that failure already exists. A receipt whose own
verify() is NO-DATA (advisory: a dirty tree at generation time, or no covered
file) is neither a broken claim nor clean evidence, and is not otherwise pinned
in a section; it is counted in the evidence scope note.

WHAT A DECLARED KIND IS NOT: a proof that the command performed that check.
`sbe evidence run --kind gate` binds the declaration to a run that actually
happened and seals it, so it cannot be typed into a receipt afterwards, and the
recorded argv sits beside it for a reader to compare. An operator who declares
a kind over a command that checks nothing has written a false statement rather
than exploited an inference, which is the whole of the improvement and is
stated here rather than oversold.

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

#: How each kind reads in a report, and the command line that would record
#: evidence for it. The NAMES are not defined here: they come from
#: `evidence.CHECK_KIND_NAMES`, the vocabulary receipts are written in, so this
#: module can never recognize a kind the generator cannot write or miss one it
#: can. A name with no row below still appears, under a generic label, because
#: a kind this table has not been taught about is still an obligation and
#: dropping it would be the silent gap this project refuses everywhere else.
CHECK_KIND_DETAIL = {
    "design": ("design completeness check", "bin/sbe design --strict <dossier>"),
    "gate": ("hard gate", "bin/sbe gate <dossier>"),
    "score": ("scored surface", "bin/sbe score --strict <dossier>"),
}

CHECK_KINDS = tuple(
    (kind,) + CHECK_KIND_DETAIL.get(
        kind, ("%s check" % kind, "the command that runs the %s check" % kind))
    for kind in evidence_mod.CHECK_KIND_NAMES)

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
    """Which of design/gate/score this receipt DECLARES, read from its own
    `checkKinds` field and from nothing else.

    One line of delegation on purpose: `evidence.declared_kinds` is the single
    reader of that field, so this module cannot drift into a second
    interpretation of it. What this function no longer does is the point. It
    used to substring-match the joined argv, which meant a receipt for
    `/bin/cat tests/test_design_of_gate_score.txt` cleared the design, gate and
    score obligations at once, on a command that ran no check. A receipt that
    declares nothing now clears nothing, and `_scan_evidence` records WHY so
    the absence is reported rather than assumed.
    """
    return evidence_mod.declared_kinds(receipt)


def _scan_evidence(root, evidence_dir):
    """Every *.json under the evidence store, verified and classified.

    Returns a dict: `broken` (BROKEN CLAIMS items), `clean` (the receipts
    that verify PASS with a zero exit code), `failing` (MERGE BLOCKERS items,
    a verified receipt recording a nonzero exit code), `kindsCovered` (the
    set of design/gate/score kinds ANY verified receipt, passing or failing,
    DECLARES), `kindless` (one sentence per verified receipt that declares no
    kind, so a reader is told that evidence exists and says nothing about
    which check it was, rather than left to read the absence as no evidence at
    all), `count`, `inspected` (whether the store existed to look at) and
    `note` (the scope sentence every caller prints, either way).

    Every receipt verifies with the evidence store ITSELF excluded from its
    covered files: `evidence_mod.verify` is called with `exclude_dirs` set to
    `evidence_dir`'s path relative to `root`, the same spelling `coveredFiles`
    entries use. A receipt's `coveredFiles` normally comes from a diff, not a
    hand-picked list, and that diff cannot distinguish "code this run tested" from
    "another receipt that happened to land in the same base..HEAD range". A
    receipt regenerated at a fixed `--out` path (the ordinary shape of a CI
    re-run) is not a change to the code under test, and without this
    exclusion an unrelated receipt that merely covered its OLD bytes by
    diff-range accident would FAIL the moment it refreshed: the evidence
    store poisoning itself. See docs/KNOWN-LIMITS.md ("Evidence covering
    evidence") for exactly what this closes and does not.
    """
    broken, clean, failing, kindless = [], [], [], []
    kinds_covered = set()
    if not os.path.isdir(evidence_dir):
        return {"broken": broken, "clean": clean, "failing": failing,
                "kindless": kindless,
                "kindsCovered": kinds_covered, "count": 0, "inspected": False,
                "note": "no evidence store found at %s" % evidence_dir}
    exclude_rel = os.path.relpath(evidence_dir, root)
    paths = []
    for dirpath, _dirnames, filenames in os.walk(evidence_dir):
        for name in filenames:
            if name.endswith(".json"):
                paths.append(os.path.join(dirpath, name))
    paths.sort()
    for full in paths:
        rel = os.path.relpath(full, root)
        result = evidence_mod.verify(full, cwd=root, exclude_dirs=(exclude_rel,))
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
        kinds = _receipt_kinds(receipt)
        kinds_covered |= kinds
        gap = evidence_mod.kind_declaration_gap(receipt)
        if gap:
            kindless.append("receipt %s declares no check kind: %s" % (rel, gap))
        trust = result["trust"]
        exit_code = receipt.get("exitCode")
        argv_text = " ".join(str(a) for a in (receipt.get("argv") or []))
        kinds_text = (", ".join(sorted(kinds)) if kinds
                      else "none declared, so it clears no obligation")
        if exit_code == 0:
            head = _git_head(root)
            clean.append({
                "finding": "receipt %s verifies as sound evidence, trust %s (declared check "
                          "kind(s): %s; command: %s; scope: this receipt's covered files "
                          "against HEAD %s, nothing beyond them)"
                          % (rel, trust, kinds_text, argv_text or "not recorded",
                             head[:7] if head else "unknown"),
                "remedy": "no action; this receipt is sound evidence",
                "path": rel, "trust": trust,
            })
        else:
            failing.append({
                "finding": "receipt %s verifies as trustworthy but records exit code %s for "
                          "`%s`, trust %s, declared check kind(s) %s"
                          % (rel, exit_code, argv_text or "(argv not recorded)", trust,
                             kinds_text),
                "remedy": "fix the underlying failure and re-run to produce a new passing "
                         "receipt; see %s" % rel,
                "path": rel,
                "coveredFiles": [cf.get("path") for cf in (receipt.get("coveredFiles") or [])
                                if isinstance(cf, dict) and cf.get("path")],
            })
    note = (("%d receipt(s) found under %s" % (len(paths), evidence_dir)) if paths
           else "evidence store %s exists and holds no receipt" % evidence_dir)
    if kindless:
        note += ("; %d verified receipt(s) declare no check kind and clear no obligation"
                 % len(kindless))
    return {"broken": broken, "clean": clean, "failing": failing, "kindless": kindless,
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
    scope; this is the one sentence that names it.

    The `dossiers` clause only appears when CR-06 discovery actually ran
    (the flat layout was absent and this run went looking under the design
    roots instead): `storesInspected["dossiers"]` stays `None` whenever the
    flat layout is present, so a flat repository's scope sentence is exactly
    the five-part sentence this file has always printed.
    """
    si = scope.get("storesInspected", {})
    parts = [
        "intake %s" % (si.get("intake") or "absent"),
        "disposition %s" % (si.get("disposition") or "absent"),
        "evidence store %s" % (si.get("evidenceDir") or "absent"),
        "task registry %s" % (si.get("taskRegistry") or "absent"),
    ]
    dossiers = si.get("dossiers")
    if dossiers is not None:
        parts.append("dossiers discovered: %s" % ", ".join(dossiers))
    parts.append(
        "diff %s" % (scope.get("diffRange") or ("NO-DATA: %s" % scope.get("diffProblem")
                                                if scope.get("diffProblem") else "NO-DATA")))
    return "scope: " + "; ".join(parts)


def _intake_summary_text(summaries):
    """The MERGE BLOCKERS empty-scope note's `intake ... (tier ...)` clause.

    One flat target (the ordinary layout, `summaries[0]["label"] is None`)
    keeps the exact sentence this file has always printed. One or more
    discovered dossiers are joined instead, each labeled by name, so a
    reader knows which change's intake was actually read.
    """
    if len(summaries) == 1 and summaries[0]["label"] is None:
        s = summaries[0]
        return "intake %s (tier %s)" % (s["intakePath"] if s["intakeExists"] else "absent",
                                        s["tier"] or "unknown")
    if not summaries:
        return "intake absent (tier unknown)"
    return "; ".join(
        "dossier %s intake %s (tier %s)"
        % (s["label"], s["intakePath"] if s["intakeExists"] else "absent",
           s["tier"] or "unknown")
        for s in summaries)


def _missing_evidence_summary_text(summaries):
    """The MISSING EVIDENCE empty-scope note's `declared tier ... from ...`
    clause. Same singular-versus-discovered split as `_intake_summary_text`,
    kept as a separate function because the two notes have always used
    different wording for the same underlying facts."""
    if len(summaries) == 1 and summaries[0]["label"] is None:
        s = summaries[0]
        return "declared tier %s from %s" % (
            s["tier"] or "unknown", s["intakePath"] if s["intakeExists"] else "no intake file")
    if not summaries:
        return "declared tier unknown from no intake file"
    return "; ".join(
        "dossier %s declared tier %s from %s"
        % (s["label"], s["tier"] or "unknown",
           s["intakePath"] if s["intakeExists"] else "no intake file")
        for s in summaries)


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
    store becomes a NO-DATA note in that store's section instead.

    CR-06: intake and disposition are read flat at `<root>` first, exactly as
    every earlier version of this function read them. Only when that flat
    `00-intake.json` is absent does this function discover dossiers through
    the SAME `_design_roots`/`_team_changes` walker `build_team_report`
    already uses, read each discovered dossier's own intake and disposition
    in the flat file's place, and label every finding they produce with the
    dossier's name. See the module docstring for the full statement.
    """
    root = os.path.abspath(path)
    now = time.time() if now is None else now

    broken_claims, merge_blockers, active_conflicts = [], [], []
    missing_evidence, sound_evidence = [], []

    intake_path = os.path.join(root, INTAKE_REL)
    disposition_path = os.path.join(root, DISPOSITION_REL)
    evidence_dir = os.path.join(root, tasks_mod.DEFAULT_EVIDENCE_DIR)
    reg_path = tasks_mod.registry_path(root)

    # ---- CR-06: dossier discovery, only when the flat layout is absent.
    # The flat file always wins when it exists: discovery never even runs
    # then, which is how a flat repository's output stays byte-identical to
    # every earlier version of this function. ----
    flat_present = os.path.exists(intake_path)
    dossiers, dossier_refusals = [], []
    if not flat_present:
        dossiers, dossier_refusals = _team_changes(root)
    if flat_present or not dossiers:
        targets = [(None, intake_path, disposition_path)]
    else:
        targets = [(name, os.path.join(doss, INTAKE_REL), os.path.join(doss, DISPOSITION_REL))
                  for name, doss in dossiers]

    head_sha = _git_head(root)
    scope = {
        "root": root,
        "base": base,
        "headCommit": head_sha,
        "storesInspected": {
            "intake": intake_path if flat_present else None,
            "disposition": disposition_path if os.path.exists(disposition_path) else None,
            "evidenceDir": evidence_dir if os.path.isdir(evidence_dir) else None,
            "taskRegistry": reg_path if os.path.exists(reg_path) else None,
            # None when the flat layout is present (discovery never ran) or
            # when discovery ran and found nothing; the same absence-reads-
            # as-absence shape every other store above already uses. Only
            # non-empty when at least one dossier was actually found.
            "dossiers": (sorted(name for name, _d in dossiers)
                        if (not flat_present and dossiers) else None),
        },
        "diffRange": None,
        "diffProblem": None,
    }

    # ---- Evidence store: BROKEN CLAIMS, the sound receipts, and the
    # exit-code-failing receipts that belong under MERGE BLOCKERS. Shared and
    # root-level for every target below, exactly as `sbe status --team`
    # already reads it: a receipt is never scoped to one dossier. ----
    ev = _scan_evidence(root, evidence_dir)
    broken_claims.extend(ev["broken"])
    sound_evidence.extend(ev["clean"])
    merge_blockers.extend(ev["failing"])

    # ---- Task registry: ACTIVE CONFLICTS and FORCED closes. Shared and
    # root-level, same reasoning as the evidence store above. ----
    tk = _scan_tasks(root, reg_path)
    active_conflicts.extend(tk["conflicts"])
    merge_blockers.extend(tk["forced"])

    # ---- CR-06 containment: a designRoots entry that would escape the
    # repository is refused by `_design_roots` and never walked; it is
    # surfaced here as a merge blocker, never a silent skip, the same
    # containment law `build_team_report` already applies to it. ----
    for entry in dossier_refusals:
        merge_blockers.append({
            "finding": "designRoots entry %r in .sbe/team-profile.json resolves outside "
                      "this repository root and was REFUSED: it is not walked for "
                      "dossiers, and no dossier under it is discovered" % entry,
            "remedy": "point designRoots entry %r at a directory inside this repository, "
                     "or remove the entry" % entry,
        })

    # ---- Disposition staleness, intake/diff reconciliation and MISSING
    # EVIDENCE, run once per target above: the one flat root target in the
    # ordinary layout (unchanged from every earlier version of this
    # function), or once per discovered dossier when the flat layout was
    # absent instead. ----
    summaries = []
    for label, t_intake_path, t_disposition_path in targets:
        prefix = ("dossier %s: " % label) if label else ""

        if os.path.exists(t_disposition_path) and head_sha:
            _live, disp_note = impact_mod.read_disposition(t_disposition_path, head_sha)
            if disp_note:
                broken_claims.append({
                    "finding": "%sdisposition file %s: %s"
                              % (prefix, t_disposition_path, disp_note),
                    "remedy": "record a fresh disposition against head %s naming who decided "
                             "and why" % head_sha[:12],
                })

        # Intake vs diff reconciliation, read exactly as `sbe impact` reads
        # it: this is analysis of a diff and two small JSON files, never a
        # subprocess and never a new gate run.
        human_tier, _answers, intake_problem = impact_mod.read_intake(t_intake_path)
        idata = None
        try:
            idata = impact_mod.report(
                root, base=base, head="HEAD",
                intake_path=t_intake_path if os.path.exists(t_intake_path) else None,
                disposition_path=(t_disposition_path
                                  if os.path.exists(t_disposition_path) else None))
            if scope["diffRange"] is None:
                scope["diffRange"] = idata["scope"]
        except DiffUnavailable as exc:
            if scope["diffProblem"] is None:
                scope["diffProblem"] = str(exc)

        if intake_problem and human_tier is None and os.path.exists(t_intake_path):
            merge_blockers.append({
                "finding": "%sintake at %s cannot be read: %s"
                          % (prefix, t_intake_path, intake_problem),
                "remedy": "fix 00-intake.json so its five answers parse in the accepted "
                         "vocabulary, then re-run status",
            })
        if idata is not None:
            for d in idata["disagreements"]:
                if d["disposition"] != "missing":
                    continue
                merge_blockers.append({
                    "finding": "%sintake declared %s but the diff shows %s (detector %s on "
                              "%s, no disposition)"
                              % (prefix, human_tier, idata["proposedTier"], d["detector"],
                                 d["file"]),
                    "remedy": "record a disposition for %s naming who decided and why, "
                             "against head %s, or revise the declared tier"
                             % (d["detector"],
                                (head_sha or idata.get("headCommit") or "?")[:12]),
                })

        # ---- MISSING EVIDENCE: only when a tier is known and owes
        # something. ----
        #
        # An obligation is cleared by a receipt that DECLARES its kind, never
        # by one whose command line happens to spell it. Receipts that
        # declare nothing are named in the same finding rather than left out
        # of it: a reader told "no receipt records a hard gate run" while
        # four receipts sit in the store would reasonably conclude the tool
        # cannot see them.
        if human_tier not in (None, "T0"):
            kindless_note = ""
            if ev["kindless"]:
                kindless_note = ("; %d receipt(s) in the store declare no check kind and "
                                 "clear no obligation: %s"
                                 % (len(ev["kindless"]), "; ".join(ev["kindless"])))
            for kind, klabel, cmdline in CHECK_KINDS:
                if kind not in ev["kindsCovered"]:
                    missing_evidence.append({
                        "finding": "%sno evidence receipt declares a %s run, and declared "
                                  "tier %s owes one%s"
                                  % (prefix, klabel, human_tier, kindless_note),
                        "remedy": "run `%s` through `sbe evidence run --kind %s` to record it"
                                 % (cmdline, kind),
                    })

        summaries.append({
            "label": label,
            "intakePath": t_intake_path,
            "intakeExists": os.path.exists(t_intake_path),
            "dispositionExists": os.path.exists(t_disposition_path),
            "tier": human_tier,
        })

    sections = (broken_claims, merge_blockers, active_conflicts, missing_evidence,
               sound_evidence)
    next_action = _next_action(sections, scope)

    notes = {
        "brokenClaims": _section_line(
            broken_claims,
            ev["inspected"] or any(s["dispositionExists"] for s in summaries),
            "%s; disposition %s"
            % (ev["note"], "present" if any(s["dispositionExists"] for s in summaries)
               else "absent")),
        "mergeBlockers": _section_line(
            merge_blockers,
            any(s["intakeExists"] for s in summaries) or tk["inspected"] or ev["count"] > 0
            or scope["diffRange"] is not None,
            "%s; %s; %s"
            % (_intake_summary_text(summaries), tk["note"],
               scope["diffRange"] or ("diff NO-DATA: %s" % scope["diffProblem"]))),
        "activeConflicts": _section_line(active_conflicts, tk["inspected"], tk["note"]),
        "missingEvidence": _section_line(
            missing_evidence,
            any(s["intakeExists"] and s["tier"] is not None for s in summaries),
            _missing_evidence_summary_text(summaries)),
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
# approval facts come only from a saved 10-approval.json, review facts only
# from a saved 11-review.json, and their staleness against the current head
# is DERIVED and labeled so. Findings carry a `basis` honesty field: observed
# (read this run), derived (computed from observed values), unavailable (a
# source that could not be read, which keeps its severity slot visible
# instead of vanishing).
# ---------------------------------------------------------------------------

TEAM_SEVERITIES = {
    1: "broken claims", 2: "merge blockers", 3: "scope conflicts",
    4: "stale evidence", 5: "missing approvals", 6: "convergence failures",
    7: "active tasks", 8: "ready tasks", 9: "completed changes",
    10: "next action",
    # 11, review record: deliberately OUTSIDE 1..6, so `team_blocking` below
    # never blocks a merge on this slot. A missing review is what every one
    # of this repository's nine merged pull requests would show today (human
    # review has never run here), and the repository's own law is that
    # absence is NO-DATA, never a pass and never a block (see cli.py's
    # `_record_review`): making a brand new, never-yet-produced kind of
    # record retroactively MERGE-BLOCKING the day it is introduced would
    # turn a NO-DATA fact into a block by construction, which is exactly the
    # confusion that law exists to forbid. A record that DOES exist and is
    # stale still blocks: that finding is filed at severity 4, the same
    # "stale evidence" slot approval and convergence staleness already use,
    # because staleness is not absence, it is a record disagreeing with the
    # commit in front of it, and this project already treats that as
    # blocking for the other two stores.
    11: "review record",
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


#: The fields a review record must carry for this run to trust anything it
#: says. Named once, here, so the write side (cli.py's `_record_review`) and
#: this read side cannot drift into two different ideas of "complete".
_REVIEW_REQUIRED_FIELDS = ("headSha", "reviewer", "reviewerType", "result")


def _read_review_record(path):
    """("missing", None), ("malformed", <why, as text>) or ("ok", <dict>).

    Deliberately NOT `_read_json_or_none`, which folds "the file does not
    exist" and "the file exists and will not parse" into the same None: that
    conflation is exactly right for convergence and approval above, where an
    absent report and an unreadable one are both already read as NO-DATA and
    nobody has had reason to tell them apart. A review record is held to a
    stricter, three-state law instead (see the call site): a missing record
    is NO-DATA, and a record that is present but broken, whether unparseable
    JSON or missing one of its own required fields, is FAIL, because that is
    proof somebody tried and left something nobody can trust, which is a
    worse fact than nobody having reviewed anything yet.
    """
    if not os.path.exists(path):
        return "missing", None
    try:
        data = json.loads(io.open(path, encoding="utf-8").read())
    except (ValueError, OSError) as exc:
        return "malformed", "does not parse: %s" % exc
    if not isinstance(data, dict):
        return "malformed", "the top-level JSON value is not an object"
    missing = [k for k in _REVIEW_REQUIRED_FIELDS if not data.get(k)]
    if missing:
        return "malformed", "missing required field(s): %s" % ", ".join(missing)
    return "ok", data


#: LT-202: normalized findings inside `11-review.json`. The fields a
#: `structuredFindings` entry must carry for THIS entry, specifically, to be
#: trusted, named once here so the write side (cli.py's
#: `_merge_finding_group`) and this read side cannot drift into two
#: different ideas of "complete". `fingerprint` is included even though
#: nothing here recomputes it: an entry missing its own fingerprint is
#: exactly as untrustworthy as one missing its category, because a fresh
#: `sbe review --write --findings-json` run always writes one.
_STRUCTURED_FINDING_REQUIRED_FIELDS = (
    "fingerprint", "reviewer", "category", "severity", "confidence",
    "introducedByChange", "location", "failure", "status")
_STRUCTURED_FINDING_CONFIDENCE = ("high", "medium", "low")
_STRUCTURED_FINDING_INTRODUCED = ("yes", "no", "unknown")
#: The `findingsSchemaVersion` values this installation can read. LT-202's
#: own migration path: a record naming a version outside this tuple is
#: MALFORMED rather than silently parsed as today's shape, exactly the way
#: an unrecognized `schemaVersion` would be treated anywhere else in this
#: package, and a future shape change grows this tuple rather than replacing
#: it, so an old record naming "1.0" never stops being readable.
_STRUCTURED_FINDINGS_SCHEMA_VERSIONS = ("1.0",)


def _malformed_structured_finding(index, item):
    """Every reason `item` (the `index`-th entry of a `structuredFindings`
    array already known to be a list) cannot be trusted, or `[]` when it
    can. A malformed entry is reported by its own index, the same
    specificity `_read_review_record` already holds a malformed record's
    parse error to, so "some finding is broken" never has to stand in for
    "finding 3 is broken"."""
    if not isinstance(item, dict):
        return ["structuredFindings[%d] is not an object" % index]
    reasons = []
    for field in _STRUCTURED_FINDING_REQUIRED_FIELDS:
        if not item.get(field):
            reasons.append("structuredFindings[%d] missing %r" % (index, field))
    confidence = item.get("confidence")
    if confidence is not None and confidence not in _STRUCTURED_FINDING_CONFIDENCE:
        reasons.append("structuredFindings[%d] confidence %r is not one of %s"
                       % (index, confidence, _STRUCTURED_FINDING_CONFIDENCE))
    introduced = item.get("introducedByChange")
    if introduced is not None and introduced not in _STRUCTURED_FINDING_INTRODUCED:
        reasons.append("structuredFindings[%d] introducedByChange %r is not one of %s"
                       % (index, introduced, _STRUCTURED_FINDING_INTRODUCED))
    return reasons


def _read_structured_findings(review):
    """("absent", None), ("malformed", <why, as text>) or ("ok", <list>) for
    the `structuredFindings` LT-202 can add to a review record `review` that
    has ALREADY parsed as a trustworthy dict (the caller only reaches this
    once `_read_review_record` has already returned "ok"; a record broken at
    the top level is reported through that path instead, and this one is
    never called for it, the same way `_same_identity` below is only ever
    called once an author is already known).

    "absent" is the honest, unremarkable case for every review record
    LT-202 predates, and for one an LT-202-era `sbe review --write` wrote
    without `--findings-json`: no structured findings were ever recorded,
    which is a fact, not an accusation, exactly the law
    `_read_review_record`'s own docstring already states for a missing
    11-review.json altogether; nothing here invents a finding to fill the
    silence. "malformed" covers every way a PRESENT value cannot be
    trusted: `structuredFindings` given without its own
    `findingsSchemaVersion` (the explicit migration path this sub-schema
    requires, so a reader is never left guessing which shape it is looking
    at), a `findingsSchemaVersion` this installation does not recognize, a
    `structuredFindings` value that is not a list, or any one entry failing
    `_malformed_structured_finding`. A malformed finding is FAIL here, never
    silently dropped from the list as though it were merely absent.
    """
    if "structuredFindings" not in review:
        return "absent", None
    version = review.get("findingsSchemaVersion")
    if not version:
        return "malformed", ("structuredFindings is present without "
                             "findingsSchemaVersion: a record must name which shape "
                             "its findings are in to be trusted")
    if version not in _STRUCTURED_FINDINGS_SCHEMA_VERSIONS:
        return "malformed", ("findingsSchemaVersion %r is not one this installation "
                             "recognizes (knows: %s)"
                             % (version, ", ".join(_STRUCTURED_FINDINGS_SCHEMA_VERSIONS)))
    payload = review.get("structuredFindings")
    if not isinstance(payload, list):
        return "malformed", "structuredFindings is present but is not a list"
    reasons = []
    for i, item in enumerate(payload):
        reasons.extend(_malformed_structured_finding(i, item))
    if reasons:
        return "malformed", "; ".join(reasons)
    return "ok", payload


def _commit_author(root, sha):
    """(name, email) that authored `sha` in `root`.

    Raises `OSError` when git itself could not be run at all (no `git` on
    PATH, a permission problem): that is a DIFFERENT fact from "this sha does
    not resolve", and collapsing the two into the same silent None would make
    "the tool that checks self-review is broken here" read identically to
    "this commit is not in the history", which is exactly the confusion this
    project's own law forbids. It is not caught here; the caller (this
    module's `build_team_report`) catches it once, at the one place that
    turns either failure into its own explicit, differently-worded NO-DATA
    finding, never a pass either way.

    Returns (None, None), not an exception, when git DID run and simply could
    not resolve `sha` to a commit (a wrong sha, a shallow clone, history that
    has since been rewritten): that is the ordinary "not found" case, and
    `None` is a real answer for it, not a guess.
    """
    if not sha:
        return None, None
    code, out, _err = _git(["log", "-1", "--format=%an\x1f%ae", sha], root)
    if code != 0 or not out.strip():
        return None, None
    parts = out.strip().splitlines()[0].split("\x1f")
    if len(parts) != 2 or not parts[0].strip():
        return None, None
    return parts[0].strip(), parts[1].strip()


def _same_identity(reviewer, author_name, author_email):
    """True when `reviewer`, as recorded in a review record, reads as the
    same person as a commit's (author_name, author_email), folding case and
    surrounding space the way a git identity naturally varies: a bare name, a
    bare email, or "Name <email>" typed as one string. Mirrors the judgement
    `prverify.py` already makes for GitHub approvals (an approval whose login
    equals the pull request's author login is "approving their own change");
    this is the same check made from local git history instead of a GitHub
    API, because status makes no network call, by construction.

    Called only once an author IS known (the caller reads an unknown author
    as NO-DATA and never calls this to guess through it), so an empty
    `reviewer` here can only mean a malformed record, which the caller has
    already turned away before this runs.
    """
    reviewer_folded = (reviewer or "").strip().lower()
    if not reviewer_folded:
        return False
    name_folded = (author_name or "").strip().lower()
    email_folded = (author_email or "").strip().lower()
    return (reviewer_folded == name_folded or reviewer_folded == email_folded
           or (bool(email_folded) and email_folded in reviewer_folded))


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

            # A review record, `11-review.json`, written by `sbe review
            # --write` (see cli.py). Held to a stricter three-state law than
            # convergence and approval above: those two fold "absent" and
            # "present but will not parse" into the same NO-DATA, because
            # nobody has ever had reason to tell the two apart here. A review
            # record is: absence is NO-DATA (nobody has reviewed yet, which is
            # a fact, not an accusation); a record present but unparseable, or
            # missing one of its own required fields, is FAIL (somebody tried
            # and left a record nobody can trust, which is a worse fact than
            # silence); and a record that parses is judged from what it says,
            # never from what its own "result" field claims about itself, the
            # same way a stale approval is judged from the head sha it is
            # bound to rather than from its own FINAL.
            review_path = os.path.join(doss, "11-review.json")
            review_state, review_payload = _read_review_record(review_path)
            if review_state == "missing":
                findings.append(_finding(
                    name, 11, "NO-DATA", review_path, head, None,
                    "run sbe review %s --write --reviewer <name> --reviewer-type "
                    "human|model|independent-model --result "
                    "approved|changes-required|unverifiable to record one" % doss,
                    "observed",
                    "no review record (11-review.json) is saved for this change; "
                    "absence is a fact, not an accusation"))
            elif review_state == "malformed":
                findings.append(_finding(
                    name, 11, "FAIL", review_path, head, None,
                    "regenerate 11-review.json with sbe review %s --write" % doss,
                    "observed",
                    "%s cannot be trusted (%s): a record nobody can read is not a clean "
                    "pass" % (review_path, review_payload)))
            else:
                review = review_payload
                bound = review.get("headSha")
                if head and bound and bound != head:
                    findings.append(_finding(
                        name, 4, "FAIL", "11-review.json", bound, review.get("reviewer"),
                        "re-run sbe review against the current head and --write again",
                        "derived",
                        "the review record binds to %s but the repository head is %s: "
                        "stale review" % (bound[:12], head[:12])))
                else:
                    reviewer = review.get("reviewer")
                    result = review.get("result")
                    finding_list = review.get("findings")
                    finding_count = len(finding_list) if isinstance(finding_list, list) else 0
                    risk_list = review.get("acceptedRisks")
                    risk_count = len(risk_list) if isinstance(risk_list, list) else 0
                    # Two different NO-DATA reasons, kept apart rather than
                    # collapsed into one: `git_error` is set only when git
                    # itself could not be run at all (no `git` on PATH, a
                    # permission problem), which is a different fact from
                    # "git ran and this sha does not resolve" (`author_name`
                    # staying None below). Neither is ever a pass, and each
                    # names what actually happened rather than sharing a
                    # single silent "could not check" sentence.
                    git_error = None
                    try:
                        author_name, author_email = _commit_author(root, bound)
                    except OSError as exc:
                        author_name = author_email = None
                        git_error = exc
                    if git_error is not None:
                        findings.append(_finding(
                            name, 11, "NO-DATA", review_path, bound, reviewer,
                            "install or repair git on this machine so the reviewed "
                            "commit's author can be checked", "unavailable",
                            "git could not be run to check the author of the reviewed "
                            "commit %s (%s): a self-review check this run could not "
                            "even attempt is never a pass" % ((bound or "?")[:12], git_error)))
                    elif author_name is None:
                        findings.append(_finding(
                            name, 11, "NO-DATA", review_path, bound, reviewer,
                            "fetch the reviewed commit so its author can be checked, or "
                            "re-run sbe review once it is reachable", "unavailable",
                            "git ran but could not resolve the reviewed commit %s, so "
                            "its author is unknown and this review cannot be checked "
                            "for self-review: an undetermined author is never a pass"
                            % (bound or "?")[:12]))
                    elif _same_identity(reviewer, author_name, author_email):
                        findings.append(_finding(
                            name, 11, "FAIL", review_path, bound, reviewer,
                            "get an independent reviewer to review %s and record a "
                            "fresh 11-review.json" % doss, "derived",
                            "the review record names %s as reviewer, and %s is the "
                            "author of the reviewed commit %s: an approval naming only "
                            "the author is not an approval"
                            % (reviewer, author_name, (bound or "?")[:12])))
                    elif result != "approved":
                        findings.append(_finding(
                            name, 11, str(result), review_path, bound, reviewer,
                            "resolve what the review flagged, then record a fresh "
                            "11-review.json", "observed",
                            "the saved review record's result is %s (%d finding(s), %d "
                            "accepted risk(s))" % (result, finding_count, risk_count)))
                    else:
                        findings.append(_finding(
                            name, 11, "PASS", review_path, bound, reviewer,
                            "nothing outstanding from review", "observed",
                            "the saved review record is approved by %s (%s), "
                            "independent of the commit author, with %d finding(s) and "
                            "%d accepted risk(s) recorded"
                            % (reviewer, review.get("reviewerType"), finding_count,
                               risk_count)))

                # LT-202: the normalized findings, if this record carries
                # them, read INDEPENDENTLY of the pass/fail/stale judgement
                # just above, whether or not this record is stale: a stale
                # binding is already its own severity-4 finding, and
                # whatever this record's findings actually say is still an
                # observed fact about the record on disk either way. This
                # never invents a severity outside 1..11: it stays inside
                # slot 11 (review record), the same slot the rest of this
                # block already uses, as one further finding beside it
                # rather than a new numbered section.
                # `reviewer` (the loop-scoped variable) is only ever assigned
                # inside the inner "not stale" branch above, so a STALE
                # record would leave it unbound here: this reads
                # `review.get("reviewer")` directly instead, the same way
                # the stale finding itself does at its own append call, and
                # for the same reason.
                struct_reviewer = review.get("reviewer")
                struct_state, struct_payload = _read_structured_findings(review)
                if struct_state == "absent":
                    findings.append(_finding(
                        name, 11, "NO-DATA", review_path, bound, struct_reviewer,
                        "record structured findings with sbe review %s --write "
                        "--findings-json <path> to carry fingerprinted, deduplicated "
                        "findings" % doss, "observed",
                        "this review record carries no structuredFindings: either it "
                        "predates LT-202 or --findings-json was never passed; absence "
                        "is a fact, not an accusation"))
                elif struct_state == "malformed":
                    findings.append(_finding(
                        name, 11, "FAIL", review_path, bound, struct_reviewer,
                        "regenerate 11-review.json with a valid --findings-json file",
                        "observed",
                        "structuredFindings on %s cannot be trusted (%s): a finding "
                        "nobody can read is not a clean pass"
                        % (review_path, struct_payload)))
                else:
                    blocking = [f for f in struct_payload if f.get("blocking")]
                    pre_existing = [f for f in struct_payload
                                    if f.get("introducedByChange") != "yes"]
                    arbitration = [f for f in struct_payload
                                  if f.get("status") == "arbitration"]
                    if blocking:
                        struct_verdict = "FAIL"
                        struct_next = ("resolve the blocking structured finding(s) in "
                                      "%s" % review_path)
                    elif arbitration:
                        struct_verdict = "NO-DATA"
                        struct_next = ("adjudicate the contradicting finding(s) in %s "
                                      "(see docs/CLI.md's adjudication protocol shape)"
                                      % review_path)
                    else:
                        struct_verdict = "PASS"
                        struct_next = "nothing blocking among the structured findings"
                    findings.append(_finding(
                        name, 11, struct_verdict, review_path, bound, struct_reviewer,
                        struct_next, "observed",
                        "%d structured finding(s) recorded: %d blocking, %d "
                        "pre-existing, %d pending arbitration"
                        % (len(struct_payload), len(blocking), len(pre_existing),
                           len(arbitration))))

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
