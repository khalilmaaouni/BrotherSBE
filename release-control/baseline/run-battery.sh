#!/bin/sh
# Baseline battery for the release program: the exact suite list wired in
# .github/workflows/brothersbe-gates.yml, run unmodified on the audited
# commit, every output preserved. Exit codes recorded per step; the run
# never stops early, mirroring fail-fast: false.
#
# Why the default output location moved off release-control/baseline/battery:
# that directory is not scratch space, it is the committed Loop 0 evidence,
# the exact unmodified battery outputs captured at the audited commit and
# covered by CHECKSUMS.sha256. A rerun that wrote back into it would quietly
# rewrite the manifest's own inputs, which is precisely what the eval named
# the-tracked-manifest-matches-the-tree-it-ships-with exists to catch, and it
# did catch it: five tracked files came back modified the first time this
# script was pointed at itself. So the frozen baseline is now read-only by
# default. A caller who wants results writes them somewhere untracked (the
# default, an mktemp'd directory, printed below so it can be found), or names
# an explicit directory of their own choosing as the first argument. The one
# path this script will not write to without being told twice is the frozen
# baseline itself, guarded below by --rewrite-baseline.

export SBE_DOSSIER_ROOT=''

REWRITE_BASELINE=0
OUT_ARG=''
for arg in "$@"; do
  case "$arg" in
    --rewrite-baseline)
      REWRITE_BASELINE=1
      ;;
    *)
      if [ -z "$OUT_ARG" ]; then
        OUT_ARG="$arg"
      fi
      ;;
  esac
done

BASELINE_DIR="$(dirname "$0")/battery"

# Resolve a path to an absolute, symlink-free form for comparison, without
# requiring the path to exist yet. POSIX-only: no realpath dependency.
abspath() {
  target="$1"
  if [ -d "$target" ]; then
    (cd "$target" && pwd -P)
    return
  fi
  parent="$(dirname "$target")"
  base="$(basename "$target")"
  if [ -d "$parent" ]; then
    printf '%s/%s\n' "$(cd "$parent" && pwd -P)" "$base"
  else
    printf '%s\n' "$target"
  fi
}

if [ -n "$OUT_ARG" ]; then
  OUT="$OUT_ARG"
else
  TMPDIR_BASE="${TMPDIR:-/tmp}"
  OUT="$(mktemp -d "$TMPDIR_BASE/brothersbe-battery.XXXXXX" 2>/dev/null)"
  if [ -z "$OUT" ]; then
    echo "ERROR: mktemp -d failed; pass an explicit output directory as the first argument." >&2
    exit 1
  fi
fi

BASELINE_ABS="$(abspath "$BASELINE_DIR")"
OUT_ABS="$(abspath "$OUT")"

if [ "$OUT_ABS" = "$BASELINE_ABS" ] && [ "$REWRITE_BASELINE" != "1" ]; then
  echo "REFUSING: output directory resolves to the frozen Loop 0 baseline ($BASELINE_DIR)." >&2
  echo "Those files are the audited, checksummed baseline shipped in CHECKSUMS.sha256." >&2
  echo "Overwriting them invalidates the manifest and regresses the-tracked-manifest-matches-the-tree-it-ships-with." >&2
  echo "Pass an explicit output directory to run the battery, or pass --rewrite-baseline if you mean to replace the frozen evidence on purpose." >&2
  exit 1
fi

echo "Battery output directory: $OUT"

mkdir -p "$OUT"
SUMMARY="$OUT/summary.txt"
: > "$SUMMARY"

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
