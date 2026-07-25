#!/usr/bin/env python3
"""BrotherSBE weekly code-graded checks (Anthropic eval guidance: many small
code-graded checks; LLM judgment only for the residue). Reads the telemetry
ledger and fence registries; prints PASS / FAIL / NO-DATA per check with the
evidence inline. Advisory by default (exit 0); `--strict` exits nonzero on any
FAIL, and on a crash, so CI can block. Honest outputs only: a check without data
says NO-DATA, never PASS.

Every check is registered in CHECKS with a declaration of the evidence it opens
(see sbe_checks.py). Three of these checks used to read `PASS if not <empty list>`,
so a fresh checkout with an empty ledger printed "0 pre-schema-2 lines remain PASS"
and two more like it: the project's headline law inverted inside the project's own
scorer, in its default state. A corpus with no rows supports no verdict about
compliance, so those checks now say NO-DATA and name the file they found nothing in.
"""
import json, os, sys, glob, datetime, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbe_telemetry import (VAULT, LEDGER, RATINGS, REVIEWS, CORRECTIONS, SESSIONS_GLOB,
                          OPERATOR_MODEL, age_days, fld, OUT_KEYS, prediction_counts,
                          real_sessions)
from sbe_checks import Check, run_guarded, stated

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


class Ledger:
    """A JSONL evidence file, read so that its three states stay distinguishable.

    sbe_telemetry.read_jsonl skips a line it cannot parse, which is right for the
    hook write path (one corrupt line must not lose the rest) and wrong for a
    check: a ledger of unparseable lines read as a ledger of zero lines, and zero
    lines read as compliance. Here, absent is NO-DATA, present-and-empty is
    NO-DATA naming the file, and present-and-unreadable is a FAIL, because a
    broken record is a broken claim and not an absence.
    """

    def __init__(self, path):
        self.path = path
        self.exists = os.path.isfile(path)
        self.rows = []
        self.errors = []
        if not self.exists:
            return
        try:
            raw_lines = open(path, errors="replace").read().splitlines()
        except OSError as e:
            self.errors.append("%s cannot be read (%s)" % (path, type(e).__name__))
            return
        for i, raw in enumerate(raw_lines, 1):
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except ValueError:
                self.errors.append("%s:%d is not valid JSON" % (os.path.basename(path), i))
                continue
            if not isinstance(obj, dict):
                self.errors.append("%s:%d is a JSON %s, not an object"
                                   % (os.path.basename(path), i, type(obj).__name__))
                continue
            # A session_id is the key every session-shaped row is deduplicated
            # by. A row whose session_id is an object or a list is unhashable and
            # raised inside the shared context, outside the per-check guard, which
            # collapsed all eleven checks into one error line at exit 0. A row
            # whose session_id is "" or " " is worse than that: it is hashable, so
            # it silently merged with every other blank-id row and the coverage
            # check counted them as one session. Both are broken records, and this
            # is where a broken record is named.
            if "session_id" in obj and stated(obj.get("session_id")) is None:
                self.errors.append("%s:%d records session_id %r, which is not a session identifier"
                                   % (os.path.basename(path), i, obj.get("session_id")))
                continue
            if "session_id" in obj and not isinstance(obj["session_id"], str):
                self.errors.append("%s:%d records session_id of type %s, not a string"
                                   % (os.path.basename(path), i, type(obj["session_id"]).__name__))
                continue
            self.rows.append(obj)

    def problem(self, what):
        """(verdict, evidence) when this ledger cannot support a verdict, else None."""
        if self.errors:
            return "FAIL", ("%s cannot be scored: %s. A ledger that cannot be read is a broken "
                            "record, not an absent one" % (what, "; ".join(self.errors[:4])))
        if not self.exists:
            return "NO-DATA", ("no %s, so nothing was opened and there is no %s to report on"
                               % (self.path, what))
        if not self.rows:
            return "NO-DATA", ("%s exists and holds no lines, so %s was measured over zero rows; "
                               "a corpus with nothing in it supports no verdict" % (self.path, what))
        return None


class Ctx:
    """Everything the checks read, resolved LAZILY, so a check takes an argument
    instead of reaching for a module global. The meta-test builds one of these
    against a throwaway vault.

    Lazy on purpose, and this is the whole point of the class. Reading every
    evidence file in __init__ put the read outside the per-check guard: one
    malformed ledger line raised while the context was being built, so eleven
    verdict lines became a single error line and advisory mode exited 0. That is
    the absent-check defect in its purest form, in the file whose docstring says
    it was closed. Now each field is opened on first use, inside the guard of the
    check that asked for it, so a broken ledger FAILs the four checks that read
    the ledger and the other seven still run and still print.
    """

    def __init__(self):
        self._cache = {}

    def _once(self, key, build):
        if key not in self._cache:
            self._cache[key] = build()
        return self._cache[key]

    @property
    def ledger(self):
        return self._once("ledger", lambda: Ledger(LEDGER))

    @property
    def ratings(self):
        return self._once("ratings", lambda: Ledger(RATINGS))

    @property
    def reviews(self):
        return self._once("reviews", lambda: Ledger(REVIEWS))

    @property
    def corrections(self):
        return self._once("corrections", lambda: Ledger(CORRECTIONS))

    @property
    def registries(self):
        return REGISTRIES

    @property
    def sessions(self):
        return self._once("sessions", lambda: real_sessions(self.ledger.rows))

    @property
    def recent(self):
        return self._once("recent", lambda: [
            r for r in self.sessions if (age_days(r.get("ts", "")) or 99) <= 7])

    @property
    def days(self):
        def build():
            out = {}
            for r in self.recent:
                out[r.get("ts", "")[:10]] = out.get(r.get("ts", "")[:10], 0) + 1
            return out
        return self._once("days", build)


# --------------------------------------------------------------------------
# The checks. One function each, (verdict, evidence) out, no printing.
# --------------------------------------------------------------------------

def check_ledger_coverage(ctx):
    bad = ctx.ledger.problem("session coverage")
    if bad:
        return bad
    if not ctx.recent:
        return "NO-DATA", ("%d ledger line(s), none in the last 7d, so coverage was measured over "
                           "zero recent sessions" % len(ctx.ledger.rows))
    return "PASS", "%d sessions across %d active days last 7d" % (len(ctx.recent), len(ctx.days))


def check_schema_uniform(ctx):
    bad = ctx.ledger.problem("schema uniformity")
    if bad:
        return bad
    old = [r for r in ctx.ledger.rows if r.get("schema") != 2]
    if old:
        return "FAIL", "%d of %d lines are pre-schema-2" % (len(old), len(ctx.ledger.rows))
    return "PASS", "%d ledger line(s) read, 0 pre-schema-2 lines remain" % len(ctx.ledger.rows)


def check_cache_economy(ctx):
    bad = ctx.ledger.problem("cache economy")
    if bad:
        return bad
    flagged, measured, unusable = [], 0, []
    for r in ctx.recent:
        cr, cw = r.get("cache_read", 0), r.get("cache_write", 0)
        # A cache counter is a number. Left unchecked, "" and None reached the
        # arithmetic and the check died inside the guard, which is honest but
        # unreadable; a value that is not a count is a broken field and says so.
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in (cr, cw)):
            unusable.append("%s (%r/%r)" % (r.get("session_id", "?")[:8], cr, cw))
            continue
        if cr + cw > 0:
            measured += 1
            ratio = 100.0 * cr / (cr + cw)
            if ratio < CACHE_RATIO_FLOOR:
                flagged.append("%s %.0f%%" % (r.get("session_id", "?")[:8], ratio))
    if unusable:
        return "FAIL", ("%d session(s) record cache fields that are not counts (%s), so the warm-read "
                        "ratio could not be computed over them"
                        % (len(unusable), ", ".join(unusable[:4])))
    if not measured:
        return "NO-DATA", "no sessions with cache fields last 7d"
    return ("PASS" if not flagged else "FAIL",
            "%d/%d sessions >= %.0f%% warm-read; below floor: %s"
            % (measured - len(flagged), measured, CACHE_RATIO_FLOOR, flagged or "none"))


def check_vault_log_per_active_day(ctx):
    bad = ctx.ledger.problem("session logs per active day")
    if bad:
        return bad
    if not ctx.days:
        return "NO-DATA", ("no active days in the last 7d, so no day was checked for a session log; "
                           "'no missing logs' over zero days is not compliance")
    # filename date OR mtime date counts, so a dated backfill note clears an old miss
    log_days, blank = set(), []
    for f in glob.glob(SESSIONS_GLOB):
        try:
            # A zero-byte file, and a file holding only its own headings, is not a
            # session log. Counting either as one let `touch` satisfy the day and
            # the check then reported "0 days without any log" over a file with
            # nothing written in it.
            body = open(f, errors="replace").read()
            if not [l for l in body.splitlines()
                    if l.strip() and not l.lstrip().startswith("#")]:
                blank.append(os.path.basename(f))
                continue
        except OSError:
            blank.append(os.path.basename(f))
            continue
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", os.path.basename(f))
        if m:
            log_days.add(m.group(1))
        try:
            log_days.add(datetime.date.fromtimestamp(os.path.getmtime(f)).isoformat())
        except OSError:
            continue
    missing = sorted(d for d in ctx.days if d not in log_days)
    note = ("; %d file(s) in the session folders hold nothing and were not counted as logs (%s)"
            % (len(blank), ", ".join(sorted(blank)[:4]))) if blank else ""
    return ("PASS" if not missing else "FAIL",
            "%d active day(s) checked against %d dated session log(s) with content; days without "
            "any log: %s%s" % (len(ctx.days), len(log_days), missing or "none", note))


def _registry_lines(ctx, max_age_days=None):
    """(lines, read, skipped) across the configured registries."""
    lines, read, skipped = [], 0, []
    for p in ctx.registries:
        try:
            age = (datetime.datetime.now().timestamp() - os.path.getmtime(p)) / 86400
        except OSError:
            skipped.append(os.path.basename(p))
            continue
        if max_age_days is not None and age > max_age_days:
            skipped.append(os.path.basename(p))
            continue
        try:
            body = open(p, errors="replace").read().splitlines()
        except OSError:
            skipped.append(os.path.basename(p))
            continue
        read += 1
        for line in body:
            lines.append((p, age, line.strip()))
    return lines, read, skipped


def _is_live_fence(s):
    return s.startswith("- ") and "agent" in s.lower() and "LANDED" not in s and "ADOPTED" not in s


def check_fence_hygiene(ctx):
    if not ctx.registries:
        return "NO-DATA", "set BROTHERSBE_REGISTRIES to enable; nothing was opened"
    lines, read, skipped = _registry_lines(ctx)
    if not read:
        return "NO-DATA", ("%d registry path(s) configured, none readable (%s), so no fence line was "
                           "examined" % (len(ctx.registries), ", ".join(skipped[:4])))
    stale = sorted({os.path.basename(p) for p, age, s in lines if _is_live_fence(s) and age > 2})
    fences = sum(1 for _, _, s in lines if _is_live_fence(s))
    if not fences:
        return "NO-DATA", ("%d registry file(s) read, none carrying a fence line, so staleness was "
                           "measured over zero fences" % read)
    return ("PASS" if not stale else "FAIL",
            "%d fence line(s) in %d registry file(s); live-looking fences older than 2d in: %s"
            % (fences, read, stale or "none"))


def check_correction_latency(ctx):
    bad = ctx.corrections.problem("correction latency")
    if bad:
        return bad
    # `age_days(...) or 0` read an unreadable timestamp as an age of zero, so a
    # correction with "" or no ts at all counted as fresh and the check reported
    # "0 older than 7d" over rows whose age nothing had measured. An age that
    # could not be computed is not an age of zero.
    undated = [c for c in ctx.corrections.rows if age_days(c.get("ts") or "") is None]
    if undated:
        return "FAIL", ("%d of %d correction candidate(s) carry no readable timestamp (%s), so their "
                        "latency was never measured and this check cannot report on it"
                        % (len(undated), len(ctx.corrections.rows),
                           ", ".join(repr(c.get("ts")) for c in undated[:4])))
    old = [c for c in ctx.corrections.rows if age_days(c.get("ts", "")) > 7]
    return ("PASS" if not old else "FAIL",
            "%d candidate(s) total, %d older than 7d unprocessed"
            % (len(ctx.corrections.rows), len(old)))


def check_budget_vs_tier(ctx):
    """Every recent live fence line carries its declared tier.

    This used to append the skill's OWN STATE.md to the registry list on every
    run, so pointing the scorer at an unrelated empty directory printed a green
    fence-discipline line sourced from the author's machine. It reads the
    configured registries and nothing else.
    """
    if not ctx.registries:
        return "NO-DATA", ("set BROTHERSBE_REGISTRIES to enable; no registry was opened, so no fence "
                           "line was checked for a tier tag")
    lines, read, skipped = _registry_lines(ctx, max_age_days=7)
    if not read:
        return "NO-DATA", ("%d registry path(s) configured, none touched in the last 7d or none "
                           "readable, so no fence line was checked" % len(ctx.registries))
    tagged, untagged = 0, []
    for p, _, s in lines:
        if not _is_live_fence(s):
            continue
        if re.search(r"\btier T[123]\b", s):
            tagged += 1
        else:
            untagged.append(os.path.basename(p))
    if tagged + len(untagged) == 0:
        return "NO-DATA", "no fence lines in the %d registry file(s) touched last 7d" % read
    return ("PASS" if not untagged else "FAIL",
            "%d recent fence line(s) tier-tagged across %d registry file(s), untagged in: %s"
            % (tagged, read, sorted(set(untagged)) or "none"))


def check_prediction_seals(ctx):
    if not os.path.isfile(OPERATOR_MODEL):
        return "NO-DATA", "no %s, so no prediction ledger was opened" % OPERATOR_MODEL
    p = prediction_counts()
    if p["sealed"] == 0:
        return "NO-DATA", "%s holds no sealed predictions" % OPERATOR_MODEL
    return ("PASS" if p["sealed"] >= 5 else "FAIL", "%d sealed (target >= 5)" % p["sealed"])


def check_felt_outcome_ratings(ctx):
    if ctx.ratings.errors:
        return ctx.ratings.problem("felt-outcome ratings")
    rated = [x for x in ctx.ratings.rows if isinstance(x.get("score"), (int, float))]
    if not rated:
        return "NO-DATA", "no scored ratings in %s" % RATINGS
    return ("PASS" if len(rated) >= 6 else "FAIL",
            "%d ratings (target >= 6 for alignment 10)" % len(rated))


def check_review_cadence(ctx):
    if ctx.reviews.errors:
        return ctx.reviews.problem("review cadence")
    last = max((x.get("ts", "") for x in ctx.reviews.rows), default=None)
    a = age_days(last) if last else None
    if a is None:
        return "NO-DATA", "no review recorded in %s" % REVIEWS
    return ("PASS" if a <= 7 else "FAIL", "last review: %.1fd ago" % a)


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
EXEMPTION = "sbe: allow-silent"


def silent_failure_lints(ctx=None):
    """Scan operator source for error-swallowing patterns, returning (verdict, evidence).

    Opt-in via a dir arg or SBE_LINT_ROOT. A line carrying `# sbe: allow-silent
    <reason>` is exempt: the exemption is VISIBLE in the diff and auditable, which
    is the override philosophy applied to lints (a swallow is legal only when a
    human named why). The linter's own file is skipped, because a file that defines
    these patterns as strings would match itself.

    Three verdicts, not two. A run that opened no file cannot have found anything,
    so it reports NO-DATA naming the reason and the evidence says what was scanned
    rather than the word "clean", which asserts the opposite of what happened. A
    file whose every match was exempted was examined and found nothing of its own,
    so when that is true of every file scanned the verdict is NO-DATA too, and the
    exemption count is in the evidence either way: "clean" over a set of suppressed
    hits is the same sentence as a PASS over an empty manifest. A positional
    argument that is not a directory is a broken invocation and FAILs: silently
    ignoring a mistyped path was how a permanently green lint that had never opened
    a file stayed invisible."""
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
    hits, exempt = [], []
    scanned, with_matches, all_exempt, empty_files = 0, 0, 0, 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in (".git", "node_modules", "__pycache__", ".venv", "venv")]
        for fn in sorted(fns):
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
            if not src.strip():
                empty_files += 1
            file_hits, file_exempt = 0, 0
            for pat, desc in LINT_PATTERNS:
                for m in pat.finditer(src):
                    first = src[:m.start()].count("\n")
                    last = first + src[m.start():m.end()].count("\n")
                    # The exemption may sit on any line the match spans: on an
                    # except-then-pass, the natural place to write it is the
                    # `pass` line, and reading only the first line of the match
                    # made the documented escape hatch look broken.
                    span = lines[first:last + 1]
                    if any(EXEMPTION in l for l in span):
                        file_exempt += 1
                        exempt.append("%s:%d" % (os.path.relpath(path, root), first + 1))
                        continue
                    file_hits += 1
                    hits.append("%s:%d %s" % (os.path.relpath(path, root), first + 1, desc))
            if file_hits or file_exempt:
                with_matches += 1
                if not file_hits:
                    all_exempt += 1
    if not scanned:
        return "NO-DATA", ("lint root %s holds no scannable source (%s), so nothing was opened"
                           % (root, " ".join(SCANNABLE)))
    if empty_files == scanned:
        # Files with the right extensions and nothing in them were opened and
        # reported "clean", which is the same sentence as a PASS over an empty
        # manifest. A scan of empty files examined no source.
        return "NO-DATA", ("%d file(s) scanned under %s and every one of them is empty, so no line of "
                           "source was examined and there is nothing to call clean"
                           % (scanned, root))
    if hits:
        return "FAIL", "%d hit(s) in %d file(s) scanned: %s" % (len(hits), scanned, "; ".join(hits[:5]))
    if exempt and all_exempt == scanned:
        return "NO-DATA", ("%d file(s) scanned under %s and every match in every one of them was "
                           "suppressed by an inline `%s` comment (%s); a scan whose every finding was "
                           "waived examined nothing it was allowed to report, so it is not clean"
                           % (scanned, root, EXEMPTION, ", ".join(exempt[:5])))
    if exempt:
        return "PASS", ("%d file(s) scanned under %s, 0 unexempted hit(s), %d suppressed by an inline "
                        "`%s` comment (%s)"
                        % (scanned, root, len(exempt), EXEMPTION, ", ".join(exempt[:5])))
    return "PASS", "%d file(s) scanned under %s, clean" % (scanned, root)


def _rel(p):
    """A registry path as the honesty test can rebuild it under a throwaway vault."""
    return os.path.relpath(p, VAULT)


# One minimal worked fixture per check, holding only the fields that check's PASS
# sentence asserts over. Minimal is the point: every leaf here is a leaf the
# honesty test may empty, and a PASS that survives an emptied leaf is a sentence
# claiming something nothing read. %(now)s, %(today)s and %(dir)s are substituted
# by the test when it writes the fixture into its throwaway vault.
_FENCE_REGISTRY = {"files": {"STATE.md": "# State\n## Fences\n"
                                         "- agent: builder | tier T2 | objective: ship the refund gate\n"},
                   "env": {"BROTHERSBE_REGISTRIES": "%(dir)s/*.md"}}
_PREDICTIONS = ("# Operator model\n## Prediction ledger\n"
                "date | prediction | seal | scored on | hit\n"
                + "".join("2026-07-0%d | the queue depth stays under 1k | seal-%d | review | yes\n"
                          % (i, i) for i in range(1, 6)))

CHECKS = {
    "ledger-coverage": Check(
        check_ledger_coverage, reads=(LEDGER,), kind="jsonl",
        full_fixture={"files": {_rel(LEDGER): [{"session_id": "sess-0001", "ts": "%(now)s"}]}}),
    "schema-2-uniform": Check(
        check_schema_uniform, reads=(LEDGER,), kind="jsonl",
        full_fixture={"files": {_rel(LEDGER): [{"schema": 2, "session_id": "sess-0001"}]}}),
    "cache-economy": Check(
        check_cache_economy, reads=(LEDGER,), kind="jsonl",
        full_fixture={"files": {_rel(LEDGER): [{"session_id": "sess-0001", "ts": "%(now)s",
                                                "cache_read": 95, "cache_write": 5}]}}),
    "vault-log-per-active-day": Check(
        check_vault_log_per_active_day, reads=(LEDGER,), kind="jsonl",
        full_fixture={"files": {_rel(LEDGER): [{"session_id": "sess-0001", "ts": "%(now)s"}],
                                "10-Projects/demo/Sessions/%(today)s-session.md":
                                    "# Session log\nWhat happened today.\n"}}),
    "fence-hygiene": Check(check_fence_hygiene, reads=("BROTHERSBE_REGISTRIES",), kind="tree",
                           empty_fixture={"files": {"STATE.md": ""}, "value": "%(dir)s/*.md"},
                           full_fixture=_FENCE_REGISTRY),
    "correction-latency": Check(
        check_correction_latency, reads=(CORRECTIONS,), kind="jsonl",
        full_fixture={"files": {_rel(CORRECTIONS): [{"ts": "%(now)s"}]}}),
    "budget-vs-tier": Check(check_budget_vs_tier, reads=("BROTHERSBE_REGISTRIES",), kind="tree",
                            empty_fixture={"files": {"STATE.md": ""}, "value": "%(dir)s/*.md"},
                            full_fixture=_FENCE_REGISTRY),
    "prediction-seals": Check(check_prediction_seals, reads=(OPERATOR_MODEL,), kind="text",
                              full_fixture={"files": {_rel(OPERATOR_MODEL): _PREDICTIONS}}),
    "felt-outcome-ratings": Check(
        check_felt_outcome_ratings, reads=(RATINGS,), kind="jsonl",
        full_fixture={"files": {_rel(RATINGS): [{"score": 5} for _ in range(6)]}}),
    "review-cadence": Check(
        check_review_cadence, reads=(REVIEWS,), kind="jsonl",
        full_fixture={"files": {_rel(REVIEWS): [{"ts": "%(now)s"}]}}),
    "silent-failure-lints": Check(silent_failure_lints, reads=("SBE_LINT_ROOT",), kind="tree",
                                  empty_fixture={"files": {"notes.txt": "no scannable source here\n"},
                                                 "value": "%(dir)s"},
                                  full_fixture={"files": {"src/ok.py": "def f():\n    return 1\n"},
                                                "env": {"SBE_LINT_ROOT": "%(dir)s/src"}}),
}


def main():
    # Building the context is itself guarded. It used to sit outside run_guarded,
    # so a context that could not be built took every check with it. A check whose
    # context cannot be built is a FAILED check, one line each, and the checks that
    # do not need the broken part still run.
    try:
        ctx = Ctx()
        ctx_error = ""
    except Exception as e:  # sbe: allow-silent the exception becomes the FAIL evidence on every check below, and is not swallowed
        ctx, ctx_error = None, ("the evidence context could not be built: %s: %s. A check whose "
                                "context could not be built examined nothing, and is reported here "
                                "as a failure rather than disappearing"
                                % (type(e).__name__, e))
    results = [(name,) + (("FAIL", ctx_error) if ctx is None
                          else run_guarded(name, CHECKS[name], ctx))
               for name in CHECKS]
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
