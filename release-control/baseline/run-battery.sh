#!/bin/sh
# Baseline battery for the release program: the exact suite list wired in
# .github/workflows/brothersbe-gates.yml, run unmodified on the audited
# commit, every output preserved. Exit codes recorded per step; the run
# never stops early, mirroring fail-fast: false.
OUT="$(dirname "$0")/battery"
mkdir -p "$OUT"
SUMMARY="$OUT/summary.txt"
: > "$SUMMARY"
export SBE_DOSSIER_ROOT=''

run_step() {
  name="$1"; shift
  echo "== $name =="
  "$@" > "$OUT/$name.out" 2>&1
  code=$?
  echo "$name exit=$code" >> "$SUMMARY"
  echo "$name exit=$code"
}

run_step 01-hard-gates       python3 tools/sbe_gate.py --strict design
run_step 02-design-checks    python3 tools/sbe_design.py --strict .
run_step 03-score-lints      python3 tools/sbe_score.py --strict --strict-soft .
run_step 04-regression-evals python3 evals/run_evals.py
run_step 05-honesty-meta     python3 evals/test_no_data_class.py
run_step 05b-honesty-seeded  python3 evals/test_no_data_class.py --quiet --seed 1 --seed 2 --seed 3
run_step 06-tool-tests       python3 tools/test_sbe.py
run_step 07-fence-hook       python3 tools/test_sbe_fence_hook.py
run_step 08-impact           python3 tools/test_sbe_impact.py
run_step 09-adopt-init       python3 tools/test_sbe_adopt.py
run_step 10-book-estate      python3 tools/test_sbe_book.py
run_step 11-bypass           python3 tools/test_sbe_bypass.py
run_step 12-converge         python3 tools/test_sbe_converge.py
run_step 13-decisions        python3 tools/test_sbe_decisions.py
run_step 14-evidence         python3 tools/test_sbe_evidence.py
run_step 15-install          python3 tools/test_sbe_install.py
run_step 16-plan             python3 tools/test_sbe_plan.py
run_step 17-prverify         python3 tools/test_sbe_prverify.py
run_step 18-status           python3 tools/test_sbe_status.py
run_step 19-status-team      python3 tools/test_sbe_status_team.py
run_step 20-tasks            python3 tools/test_sbe_tasks.py
run_step 21-work             python3 tools/test_sbe_work.py
run_step 22-install-artifact sh scripts/test-install-artifact.sh
run_step 23-upgrade-rollback sh scripts/test-upgrade-rollback.sh

echo "BATTERY-COMPLETE" >> "$SUMMARY"
cat "$SUMMARY"
