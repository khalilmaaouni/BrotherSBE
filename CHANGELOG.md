# Changelog

Newest first. Each entry names the behavior that changed and the check or test
that proves it, because a changelog line nothing can verify is a press release.
What this file does NOT record: internal working notes and measurements from
the estates this project was built on, which stay untracked by the publish
checklist's own rules.

## 1.0.0-rc.1 (unreleased)

The first named version. Before this line the only name for an install was a
commit hash, which `tools/sbe_telemetry.py check-update` compares but no human
can read a promise into.

- Autosave recovery checks the snapshot out into a NEW detached worktree and
  never writes into the live working tree; the in-place restore path is gone,
  not warned about. Proven by TestAutosaveRecover in `tools/test_sbe.py`.
- The injected digest fits the cap its own SessionStart hook comment names,
  with the long qualifications moved to `LAWS-REFERENCE.md`. Proven by
  TestDigestCap in `tools/test_sbe.py`, which reads the cap out of the hook
  comment rather than hardcoding a second number.
- Every check declares its severity (gate or soft) at write time, prints it on
  every verdict line, and the exit-code mapping is explicit: `--strict` blocks
  on gate FAILs, `--strict-soft` opts graded FAILs into blocking. Proven by
  TestStrictMode in `tools/test_sbe.py` and the severity evals in
  `evals/run_evals.py`.
- `INVARIANTS.md` states the numbered promises with their asserting tests and
  the defect-reinjection record. Proven by the eval cases it names, verified
  present on the date it states.
- Release discipline ships: `VERSION`, this changelog, `CHECKSUMS.sha256` with
  `scripts/checksums.sh` and `scripts/verify-install.sh` (both directions,
  planted extra files fail), and the cut runbook in `docs/RELEASE.md`. Proven
  by the verify-install eval in `evals/run_evals.py`.
