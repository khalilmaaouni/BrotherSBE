#!/usr/bin/env python3
"""BrotherSBE weekly code-graded checks (Anthropic eval guidance: many small
code-graded checks; LLM judgment only for the residue). Reads the telemetry
ledger and fence registries; prints PASS / FAIL / NO-DATA per check with the
evidence inline. Advisory by default (exit 0); `--strict` exits nonzero on any
FAIL, and on a crash, so CI can block. Honest outputs only: a check without data
says NO-DATA, never PASS."""
import json, os, sys, glob, datetime, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbe_telemetry import (LEDGER, RATINGS, REVIEWS, CORRECTIONS, SESSIONS_GLOB,
                          read_jsonl, age_days, fld, OUT_KEYS, prediction_counts,
                          real_sessions)

# Fence registries: the STATE.md files whose fence lines the hygiene checks
# read. Point BROTHERSBE_REGISTRIES at your own projects as colon-separated
# glob patterns, for example:
#   export BROTHERSBE_REGISTRIES="$HOME/work/*/STATE.md:$HOME/work/*/.plans/**/*STATE*.md"
# Unset, the registry checks report NO-DATA instead of guessing at paths.
REGISTRIES = []
for _pat in os.environ.get("BROTHERSBE_REGISTRIES", "").split(":"):
    if _pat.strip():
        REGISTRIES.extend(glob.glob(os.path.expanduser(_pat.strip()), recursive=True))

CACHE_RATIO_FLOOR = 90.0
results = []


def check(name, verdict, evidence):
    results.append((name, verdict, evidence))


# BrotherSBE silent-failure lints: patterns that hide an error so a wrong result
# passes for a right one. Scoped to the caller's worktree, opt-in via a path arg
# or the SBE_LINT_ROOT env var, so the tool never scans unrelated trees. Language
# builtins and heuristics only, no network, no third-party deps.
LINT_PATTERNS = [
    (re.compile(r"except\s*:"), "bare except (catches everything, hides the real error)"),
    (re.compile(r"except\s+\w[\w.]*\s*:\s*(#.*)?$\s*pass", re.M), "except-then-pass (swallows the error)"),
    (re.compile(r"\.execute\([^)]*\).*ON\s+CONFLICT.*DO\s+NOTHING", re.I), "conflict-skipping upsert without a logged skip count"),
    # Fire-and-forget subprocess only: the call starts a statement (result discarded)
    # and carries no check=True. An assigned result (out = subprocess.run(...)) can be
    # inspected, so it is not a silent swallow and is not flagged.
    (re.compile(r"^[ \t]*subprocess\.(run|call|Popen)\((?![^)]*check\s*=\s*True)", re.M), "discarded subprocess result without check=True (exit code is swallowed)"),
    (re.compile(r"try\s*!"), "force-try (Swift try! discards the error)"),
]


SCANNABLE = (".py", ".sql", ".swift", ".rb", ".js", ".ts", ".go")


def silent_failure_lints():
    """Scan operator source for error-swallowing patterns, returning (verdict, evidence).

    Opt-in via a dir arg or SBE_LINT_ROOT. A line carrying `# sbe: allow-silent
    <reason>` is exempt: the exemption is VISIBLE in the diff and auditable, which
    is the override philosophy applied to lints (a swallow is legal only when a
    human named why). The linter's own file is skipped, because a file that defines
    these patterns as strings would match itself.

    Three verdicts, not two. A run that opened no file cannot have found anything,
    so it reports NO-DATA naming the reason and the evidence says what was scanned
    rather than the word "clean", which asserts the opposite of what happened. A
    positional argument that is not a directory is a broken invocation and FAILs:
    silently ignoring a mistyped path was how a permanently green lint that had
    never opened a file stayed invisible."""
    root = os.environ.get("SBE_LINT_ROOT")
    for a in sys.argv[1:]:
        if a.startswith("-"):
            continue
        if os.path.isdir(a):
            root = a
        else:
            return "FAIL", ("%r is not a directory, so the lint root was never scanned; a mistyped path "
                            "must not read as a clean scan" % a)
    if not root:
        return "NO-DATA", ("no lint root: pass a directory or set SBE_LINT_ROOT. Nothing was opened, "
                           "so there is nothing to call clean")
    if not os.path.isdir(root):
        return "FAIL", "SBE_LINT_ROOT=%s is not a directory, so nothing was scanned" % root
    hits = []
    scanned = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in (".git", "node_modules", "__pycache__", ".venv", "venv")]
        for fn in fns:
            if fn == os.path.basename(__file__):
                continue  # the linter declares the patterns as strings; do not self-match
            if not fn.endswith(SCANNABLE):
                continue
            path = os.path.join(dp, fn)
            try:
                lines = open(path, errors="replace").read().splitlines()
            except OSError:
                continue
            scanned += 1
            src = "\n".join(lines)
            for pat, desc in LINT_PATTERNS:
                for m in pat.finditer(src):
                    ln = src[:m.start()].count("\n")
                    if "sbe: allow-silent" in lines[ln]:
                        continue  # visible, auditable exemption
                    hits.append("%s:%d %s" % (os.path.relpath(path, root), ln + 1, desc))
    if not scanned:
        return "NO-DATA", ("lint root %s holds no scannable source (%s), so nothing was opened"
                           % (root, " ".join(SCANNABLE)))
    if hits:
        return "FAIL", "%d hit(s) in %d file(s) scanned: %s" % (len(hits), scanned, "; ".join(hits[:5]))
    return "PASS", "%d file(s) scanned under %s, clean" % (scanned, root)


def main():
    led = read_jsonl(LEDGER)
    # real_sessions everywhere: scorecard, nag, and these checks must all mean
    # the same thing by "session" (weekly-review-1 law, extended here 2026-07-23)
    rows = real_sessions(led)
    recent = [r for r in rows if (age_days(r.get("ts", "")) or 99) <= 7]

    # 1. ledger coverage: lines per active day (can only measure what exists)
    days = {}
    for r in recent:
        days.setdefault(r.get("ts", "")[:10], 0)
        days[r.get("ts", "")[:10]] += 1
    check("ledger-coverage", "NO-DATA" if not recent else "PASS",
          "%d sessions across %d active days last 7d" % (len(recent), len(days)))

    # 2. schema uniformity
    old = [r for r in led if r.get("schema") != 2]
    check("schema-2-uniform", "PASS" if not old else "FAIL",
          "%d pre-schema-2 lines remain" % len(old))

    # 3. cache economy per session
    flagged = []
    measured = 0
    for r in recent:
        cr, cw = r.get("cache_read", 0), r.get("cache_write", 0)
        if cr + cw > 0:
            measured += 1
            ratio = 100.0 * cr / (cr + cw)
            if ratio < CACHE_RATIO_FLOOR:
                flagged.append("%s %.0f%%" % (r.get("session_id", "?")[:8], ratio))
    if not measured:
        check("cache-economy", "NO-DATA", "no sessions with cache fields last 7d")
    else:
        check("cache-economy", "PASS" if not flagged else "FAIL",
              "%d/%d sessions >= %.0f%% warm-read; below floor: %s"
              % (measured - len(flagged), measured, CACHE_RATIO_FLOOR, flagged or "none"))

    # 4. vault log per active day (filename date OR mtime date counts, so a
    # dated backfill note clears an old miss; interim-score fix 2026-07-23)
    log_days = set()
    for f in glob.glob(SESSIONS_GLOB):
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", os.path.basename(f))
        if m:
            log_days.add(m.group(1))
        try:
            log_days.add(datetime.date.fromtimestamp(os.path.getmtime(f)).isoformat())
        except OSError:
            continue
    missing = [d for d in days if d not in log_days]
    check("vault-log-per-active-day", "PASS" if not missing else "FAIL",
          "active days without any vault session log: %s" % (missing or "none"))

    # 5. fence hygiene across registries
    if not REGISTRIES:
        check("fence-hygiene", "NO-DATA", "set BROTHERSBE_REGISTRIES to enable")
    stale = []
    for p in REGISTRIES:
        try:
            age = (datetime.datetime.now().timestamp() - os.path.getmtime(p)) / 86400
        except OSError:
            continue
        for line in open(p, errors="replace"):
            s = line.strip()
            if s.startswith("- ") and "agent" in s.lower() and "LANDED" not in s and "ADOPTED" not in s and age > 2:
                stale.append(os.path.basename(p))
                break
    if REGISTRIES:
        check("fence-hygiene", "PASS" if not stale else "FAIL",
              "registries with live-looking fences older than 2d: %s" % (stale or "none"))

    # 6. corrections pipeline
    corr = read_jsonl(CORRECTIONS)
    old_corr = [c for c in corr if (age_days(c.get("ts", "")) or 0) > 7]
    check("correction-latency", "PASS" if not old_corr else "FAIL",
          "%d candidates total, %d older than 7d unprocessed" % (len(corr), len(old_corr)))

    # 7. budget vs declared tier: scan fence lines in registries touched the
    # last 7d (older registries predate the tier law and are not judged by it).
    # PASS needs every recent live fence line tier-tagged; the spend comparison
    # itself stays a weekly-review judgment. (interim-score fix 2026-07-23)
    tagged, untagged = 0, []
    skill_state = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "STATE.md")
    for p in REGISTRIES + [skill_state]:
        try:
            if (datetime.datetime.now().timestamp() - os.path.getmtime(p)) / 86400 > 7:
                continue
        except OSError:
            continue
        for line in open(p, errors="replace"):
            s = line.strip()
            if s.startswith("- ") and "agent" in s.lower() and "LANDED" not in s and "ADOPTED" not in s:
                if re.search(r"\btier T[123]\b", s):
                    tagged += 1
                else:
                    untagged.append(os.path.basename(p))
    if tagged + len(untagged) == 0:
        check("budget-vs-tier", "NO-DATA", "no fence lines in registries touched last 7d")
    else:
        check("budget-vs-tier", "PASS" if not untagged else "FAIL",
              "%d recent fence lines tier-tagged, untagged in: %s"
              % (tagged, sorted(set(untagged)) or "none"))

    # 8. predictions and ratings (external-evidence feeds)
    p = prediction_counts()
    rated = [x for x in read_jsonl(RATINGS) if isinstance(x.get("score"), (int, float))]
    check("prediction-seals", "PASS" if p["sealed"] >= 5 else ("NO-DATA" if p["sealed"] == 0 else "FAIL"),
          "%d sealed (target >= 5)" % p["sealed"])
    check("felt-outcome-ratings", "PASS" if len(rated) >= 6 else ("NO-DATA" if not rated else "FAIL"),
          "%d ratings (target >= 6 for alignment 10)" % len(rated))

    # 9. weekly review cadence
    reviews = read_jsonl(REVIEWS)
    last = max((x.get("ts", "") for x in reviews), default=None)
    a = age_days(last) if last else None
    check("review-cadence", "PASS" if (a is not None and a <= 7) else ("NO-DATA" if a is None else "FAIL"),
          "last review: %s" % (("%.1fd ago" % a) if a is not None else "never"))

    # 10. silent-failure lints (BrotherSBE, gate severity by ratified decision):
    # the code patterns that swallow an error so a wrong result looks like a right
    # one. Scans tracked source in the worktree; each hit names its file and line.
    check("silent-failure-lints", *silent_failure_lints())

    width = max(len(n) for n, _, _ in results)
    fails = sum(1 for _, v, _ in results if v == "FAIL")
    for n, v, e in results:
        print("%-*s  %-7s  %s" % (width, n, v, e))
    print("\n%d checks: %d PASS, %d FAIL, %d NO-DATA. LLM judge scores only the residue."
          % (len(results), sum(1 for _, v, _ in results if v == "PASS"), fails,
             sum(1 for _, v, _ in results if v == "NO-DATA")))
    # Two modes, same checks: the local hook stays advisory (exit 0, never blocks a
    # session), but `--strict` exits nonzero on any FAIL so CI can block a merge.
    # This is how "advisory" and "enforced" coexist without contradiction.
    if "--strict" in sys.argv and fails:
        print("STRICT: %d check(s) failed; exiting nonzero to fail the CI gate." % fails)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # A broken checker must not silently waive the gate. In strict mode a crash
        # blocks, exactly as in sbe_gate.py; advisory mode still never blocks a session.
        print("sbe_score: error %r" % (e,))
        sys.exit(1 if "--strict" in sys.argv else 0)
