# Release program baseline, captured 2026-08-02

Audited commit: d11975ed8e1e172e7c8502d1bea735d5245c2e0b (branch release/1.0-closeout, cut from main at the exact commit the external master review audited).

## What this directory holds

- GitHub state snapshots taken through the authenticated API before any program change: repo.json, tags.json, workflows.json, recent-runs.json, head-check-runs.json, protection.json (the BEFORE state: main was not protected).
- protection-after-2026-08-02.json: the AFTER state, captured the same evening once branch protection was enabled (required checks: consumer-checks plus both Python 3.9 gate legs; enforce_admins true; force pushes and deletions disabled). Private vulnerability reporting was enabled the same evening (API returned enabled true).
- run-battery.sh plus battery/: the full unmodified test battery, the exact suite list wired in .github/workflows/brothersbe-gates.yml, run locally on macOS with Python 3.9.6 (the documented floor), every output preserved.
- fences.md: the write fences active during the program (one writer per file).

## Baseline battery result

23 of 24 steps exit 0. Headline numbers, verbatim from the outputs:

- 04-regression-evals: "527 evals: 527 passed, 0 regressions."
- 22-install-artifact: "PASSED for HEAD (d11975e)", nothing written outside the temporary directory.
- 23-upgrade-rollback: "PASSED. v1.0.0-rc.2 -> HEAD -> v1.0.0-rc.2", each step archived fresh and verified. The external review predicted NO-DATA here (H-18); local tags exist, so the real path ran. Clean-machine CI evidence is still required before the finding closes.

The single red step, stated honestly rather than patched:

- 03-score-lints exit 1, caused solely by the soft-severity check "cache-economy" (34 of 35 sessions at or above the 90 percent warm-read floor; one session at 86 percent). That check is fed by this machine's local session ledger, and the tool's own output states these environment-fed checks are "not a statement about the code in this directory". The identical CI step was green on this same commit (run 30698715193). No code change hides this; the local-versus-CI environment difference is itself a finding for the program (a repo-scoped run should not grade the operator's personal telemetry).

## Corrections to the external review established at baseline

- C-01 observed "no independently visible CI evidence on the audited HEAD". GitHub returns 5 successful check runs on that exact commit (head-check-runs.json in this directory). The observation is contradicted; the substance behind it (required checks enforced by branch protection, evidence bundle referencing exact runs) proceeds as planned.
- H-18 predicted upgrade/rollback NO-DATA until a previous tag exists. v1.0.0-rc.1 is published on GitHub and the baseline battery exercised the upgrade and rollback path successfully (local evidence only at this point).
