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
from sbe_checks import (Check, run_guarded, answered, vacuous, all_vacuous, distinct, Pruner,
                        evidence_problem, numeric, without_comments)

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

# Four checks compared an age with <= or > and none of them had a floor, so a
# single future-dated row defeated every staleness rule in this file at once:
# `review-cadence` printed "last review: -1620.2d ago" and called it a PASS, the
# genuinely stale review in the same ledger was masked because max() picked the
# future row, and a registry file touched with a future mtime was fresh forever.
# A timestamp in the future is not a fresh record, it is a BROKEN record, and this
# project's own rule for a broken record is that it FAILs and names itself.
AGE_IS_BROKEN = ("a timestamp in the future is not an age; a record dated after now is a broken "
                 "record, and staleness measured against it would be measured against nothing")


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
        self.exists = os.path.lexists(path)
        self.rows = []
        self.errors = []
        # The ACCESS axis, before any open(): a ledger path that is a chmod 000
        # file, a directory, or a FIFO is present and unreadable, and "no
        # outcomes.jsonl, so nothing was opened" printed over it is a false
        # sentence (a FIFO also hangs the open forever). Present-and-unreadable
        # is a broken record, which FAILs by the rule two lines down.
        problem = evidence_problem(path)
        if problem:
            self.errors.append("%s is %s" % (path, problem))
            return
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
            # check counted them as one session. A session_id of "TODO" or "-" is
            # the same merge with a value that reads as deliberate, so it goes
            # through answered() rather than stated(). All of these are broken
            # records, and this is where a broken record is named.
            if "session_id" in obj and answered(obj.get("session_id")) is None:
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
            r for r in self.sessions
            if 0 <= (age_days(r.get("ts", "")) if age_days(r.get("ts", "")) is not None else 99) <= 7])

    @property
    def undated(self):
        """Session rows whose timestamp no age can be computed from.

        `ctx.recent` maps an unreadable timestamp to the sentinel 99, which
        means "old", so 99 rows with garbage timestamps silently left the
        7-day window and "1/1 sessions >= 90% warm-read; below floor: none"
        was printed over a ledger 99 of whose 100 rows nothing had measured.
        check_correction_latency already knew this ("an age that could not be
        computed is not an age of zero"); its siblings now read the same rule.
        """
        return self._once("undated", lambda: [
            r for r in self.sessions if age_days(r.get("ts") or "") is None])

    @property
    def future(self):
        """Rows dated after now. An age below zero is not an age; see AGE_IS_BROKEN."""
        return self._once("future", lambda: [
            r for r in self.sessions
            if (age_days(r.get("ts", "")) or 0) < 0])

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
    if ctx.undated:
        return "FAIL", ("%d session row(s) carry no readable timestamp (%s), so their age was "
                        "never measured and coverage cannot be counted over them"
                        % (len(ctx.undated),
                           ", ".join(repr(r.get("ts")) for r in ctx.undated[:4])))
    if ctx.future:
        return "FAIL", ("%d session row(s) are dated in the future (%s): %s"
                        % (len(ctx.future), ", ".join(repr(r.get("ts")) for r in ctx.future[:4]),
                           AGE_IS_BROKEN))
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
    if ctx.undated:
        return "FAIL", ("%d session row(s) carry no readable timestamp (%s), so they fell out of "
                        "the 7-day window unmeasured, and a ratio over the rest would read as "
                        "covering them" % (len(ctx.undated),
                                           ", ".join(repr(r.get("ts")) for r in ctx.undated[:4])))
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
    unmeasured = len(ctx.recent) - measured
    return ("PASS" if not flagged else "FAIL",
            "%d/%d sessions >= %.0f%% warm-read; below floor: %s%s"
            % (measured - len(flagged), measured, CACHE_RATIO_FLOOR, flagged or "none",
               "" if not unmeasured else
               "; %d recent session(s) carry no cache fields and were not measured, so this "
               "ratio does not cover them" % unmeasured))


def check_vault_log_per_active_day(ctx):
    bad = ctx.ledger.problem("session logs per active day")
    if bad:
        return bad
    if not ctx.days:
        return "NO-DATA", ("no active days in the last 7d, so no day was checked for a session log; "
                           "'no missing logs' over zero days is not compliance")
    # filename date OR mtime date counts, so a dated backfill note clears an old miss
    log_days, blank, logs = set(), [], 0
    for f in glob.glob(SESSIONS_GLOB):
        # ACCESS first: a chmod 000 log, a directory wearing a log's name, or a
        # FIFO is not a log this check read, and opening a FIFO would hang here.
        if evidence_problem(f):
            blank.append("%s (%s)" % (os.path.basename(f), evidence_problem(f)))
            continue
        try:
            # A zero-byte file, a file holding only its own headings, and a file
            # whose every line under those headings says TODO are all not a
            # session log. Counting any of them let `touch` satisfy the day and
            # the check then reported "0 days without any log" over a file with
            # nothing written in it.
            body = open(f, errors="replace").read()
            # The rendered body: a log whose whole content sits inside an HTML
            # comment renders as nothing, and its comment lines used to count
            # as content here while all_vacuous stripped them two lines up.
            rendered = without_comments(body)
            if all_vacuous(body) or not [l for l in rendered.splitlines()
                                         if l.strip() and not l.lstrip().startswith("#")]:
                blank.append(os.path.basename(f))
                continue
        except OSError:
            blank.append(os.path.basename(f))
            continue
        logs += 1
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", os.path.basename(f))
        if m:
            log_days.add(m.group(1))
        try:
            # The UTC date, because the active days it is compared against come
            # from UTC timestamps: a local-time date here made a log written near
            # midnight cover the wrong day in some timezones and no day in others.
            log_days.add(datetime.datetime.fromtimestamp(
                os.path.getmtime(f), datetime.timezone.utc).date().isoformat())
        except OSError:
            continue
    missing = sorted(d for d in ctx.days if d not in log_days)
    note = ("; %d file(s) in the session folders hold nothing readable and were not counted as "
            "logs (%s)" % (len(blank), ", ".join(sorted(blank)[:4]))) if blank else ""
    # The count printed is the count of LOG FILES, not of dates. One file used to
    # contribute up to two entries to a set of dates (its filename date and its
    # mtime date) and the sentence printed that set's size as "2 dated session
    # log(s)" over a folder holding one file.
    return ("PASS" if not missing else "FAIL",
            "%d active day(s) checked against %d session log file(s) with content (a log covers "
            "its filename date and its last-modified date); days without any log: %s%s"
            % (len(ctx.days), logs, missing or "none", note))


def _registry_lines(ctx, max_age_days=None):
    """(lines, read, old, unreadable, ahead) across the configured registries.

    `ahead` names registry files whose mtime is in the future. Without it, one
    `touch -t 203001010000` made a file fresh forever: every fence in it was
    younger than two days by arithmetic and the hygiene check said so.

    `old` and `unreadable` used to be one list, consumed only on the NO-DATA
    branch, so a chmod 000 on the registry files holding the violations shrank
    the set in silence and turned two FAILs into two PASSes whose sentences said
    "untagged in: none". Skipping a file for AGE is a deliberate filter; failing
    to OPEN a file that is sitting there is the ACCESS axis, and the callers turn
    it into a FAIL, because a registry this check cannot read is a broken record
    and never a smaller registry.
    """
    lines, read, old, unreadable, ahead = [], 0, [], [], []
    for p in ctx.registries:
        problem = evidence_problem(p)
        if problem:
            unreadable.append("%s (%s)" % (os.path.basename(p), problem))
            continue
        try:
            age = (datetime.datetime.now().timestamp() - os.path.getmtime(p)) / 86400
        except OSError as e:
            unreadable.append("%s (%s)" % (os.path.basename(p), type(e).__name__))
            continue
        if age < 0:
            ahead.append(os.path.basename(p))
            continue
        if max_age_days is not None and age > max_age_days:
            old.append(os.path.basename(p))
            continue
        try:
            # Rendered: a fence line inside an HTML comment is invisible to the
            # reader of the registry, so it is invisible to the fence checks.
            body = without_comments(open(p, errors="replace").read()).splitlines()
        except OSError as e:
            unreadable.append("%s (%s)" % (os.path.basename(p), type(e).__name__))
            continue
        read += 1
        for line in body:
            lines.append((p, age, line.strip()))
    return lines, read, old, unreadable, ahead


def _is_live_fence(s):
    # Both markdown bullets: `*` and `-` render identically, and this project's
    # own entity rule accepts both, so an operator whose registry uses asterisk
    # bullets used to get permanently green fence discipline over untagged live
    # fences.
    return (s.startswith(("- ", "* ")) and "agent" in s.lower()
            and "LANDED" not in s and "ADOPTED" not in s)


def check_fence_hygiene(ctx):
    if not ctx.registries:
        return "NO-DATA", "set BROTHERSBE_REGISTRIES to enable; nothing was opened"
    lines, read, old, unreadable, ahead = _registry_lines(ctx)
    if ahead:
        return "FAIL", ("%d registry file(s) carry a modification time in the future (%s): %s"
                        % (len(ahead), ", ".join(sorted(ahead)[:4]), AGE_IS_BROKEN))
    if unreadable:
        # Never a smaller registry: the verdict this check would print over the
        # remaining files reads as covering the whole configured set.
        return "FAIL", ("%d of %d configured registry file(s) exist and could not be read (%s); a "
                        "registry this check cannot open is a broken record, not an absent one, and "
                        "a staleness verdict over the rest would read as covering it"
                        % (len(unreadable), len(ctx.registries), ", ".join(sorted(unreadable)[:4])))
    if not read:
        return "NO-DATA", ("%d registry path(s) configured, none readable, so no fence line was "
                           "examined" % len(ctx.registries))
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
    ahead = [c for c in ctx.corrections.rows if age_days(c.get("ts", "")) < 0]
    if ahead:
        return "FAIL", ("%d of %d correction candidate(s) are dated in the future (%s): %s"
                        % (len(ahead), len(ctx.corrections.rows),
                           ", ".join(repr(c.get("ts")) for c in ahead[:4]), AGE_IS_BROKEN))
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
    lines, read, old, unreadable, ahead = _registry_lines(ctx, max_age_days=7)
    if ahead:
        return "FAIL", ("%d registry file(s) carry a modification time in the future (%s): %s"
                        % (len(ahead), ", ".join(sorted(ahead)[:4]), AGE_IS_BROKEN))
    if unreadable:
        return "FAIL", ("%d of %d configured registry file(s) exist and could not be read (%s); a "
                        "registry this check cannot open is a broken record, not an absent one, and "
                        "a tier-tag verdict over the rest would read as covering it"
                        % (len(unreadable), len(ctx.registries), ", ".join(sorted(unreadable)[:4])))
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
    problem = evidence_problem(OPERATOR_MODEL)
    if problem:
        return "FAIL", ("%s is %s; a prediction ledger that exists and cannot be read is a broken "
                        "record, not an absent one" % (OPERATOR_MODEL, problem))
    if not os.path.isfile(OPERATOR_MODEL):
        return "NO-DATA", "no %s, so no prediction ledger was opened" % OPERATOR_MODEL
    p = prediction_counts()
    if p["sealed"] == 0:
        return "NO-DATA", "%s holds no sealed predictions" % OPERATOR_MODEL
    return ("PASS" if p["sealed"] >= 5 else "FAIL",
            "%d sealed (target >= 5)%s" % (p["sealed"], p.get("note", "")))


def check_felt_outcome_ratings(ctx):
    if ctx.ratings.errors:
        return ctx.ratings.problem("felt-outcome ratings")
    # The shared rule, not isinstance: `isinstance(NaN, float)` and
    # `isinstance(True, int)` are both True, so a NaN score and a boolean score
    # each counted as a rating, and six NaNs cleared "6 distinct ratings".
    # numeric() refuses NaN, infinity and booleans in one place.
    rated = [x for x in ctx.ratings.rows if numeric(x.get("score")) is not None]
    if not rated:
        return "NO-DATA", "no scored ratings in %s" % RATINGS
    # The shared dedupe rule, on the rating's CONTENT. The writer stamps a
    # fresh timestamp on every row, so deduplicating whole rows could never
    # fold anything: six copies of one 5/5 rating of one task, differing only
    # in microseconds, cleared "6 distinct ratings". What makes two ratings
    # one rating is the same score of the same task with the same note.
    content = [{k: v for k, v in x.items() if k not in ("ts", "session_id")} for x in rated]
    unique, dupes = distinct(content)
    return ("PASS" if len(unique) >= 6 else "FAIL",
            "%d distinct ratings (target >= 6 for alignment 10)%s"
            % (len(unique), "" if not dupes else
               "; %d rating(s) identical apart from their timestamps counted once" % dupes))


def check_review_cadence(ctx):
    if ctx.reviews.errors:
        return ctx.reviews.problem("review cadence")
    ahead = [x for x in ctx.reviews.rows if (age_days(x.get("ts", "")) or 0) < 0]
    if ahead:
        # Checked BEFORE max(), because max() picks the future row and a genuinely
        # stale review sitting in the same ledger is masked by it.
        return "FAIL", ("%d review row(s) are dated in the future (%s): %s"
                        % (len(ahead), ", ".join(repr(x.get("ts")) for x in ahead[:4]),
                           AGE_IS_BROKEN))
    last = max((x.get("ts", "") for x in ctx.reviews.rows), default=None)
    a = age_days(last) if last else None
    if a is None:
        return "NO-DATA", "no review recorded in %s" % REVIEWS
    return ("PASS" if a <= 7 else "FAIL", "last review: %.1fd ago" % a)


# BrotherSBE silent-failure lints: patterns that hide an error so a wrong result
# passes for a right one. Scoped to the caller's worktree, opt-in via a path arg
# or the SBE_LINT_ROOT env var, so the tool never scans unrelated trees. Language
# builtins and heuristics only, no network, no third-party deps.
#
# The conflict-skipping upsert used to be written as
# `\.execute\([^)]*\).*ON\s+CONFLICT.*DO\s+NOTHING`, which required a Python
# `.execute(` on the same line. `.sql` is the FIRST non-Python extension L11 says
# this lint scans and warehouse work is one of the seven work profiles this skill
# claims, so the one lint aimed at that profile could not fire on that profile's
# files: the statement in a .sql file, the same statement split over two lines,
# and the Python form that puts the SQL in a variable were all invisible. It now
# reads the SQL wherever it is written and in whatever host language, and stops
# at the statement's semicolon so that a legitimate `ON CONFLICT ... DO UPDATE`
# in the same file is not swept in with it.
LINT_PATTERNS = [
    (re.compile(r"except\s*:"), "bare except (catches everything, hides the real error)"),
    (re.compile(r"except\s+\w[\w.]*\s*:\s*(#.*)?$\s*pass", re.M), "except-then-pass (swallows the error)"),
    # Two patterns for one class, because the single pattern that shipped needed a
    # Python `.execute(` on the same line, and `.sql` is the FIRST non-Python
    # extension L11 says this lint scans. The one lint aimed at warehouse work
    # could not fire on a warehouse file: `INSERT ... ON CONFLICT (id) DO NOTHING;`
    # in a .sql file, the same statement split over two lines, and the Python form
    # that puts the SQL in a variable were all invisible. The second pattern reads
    # the SQL wherever it is written, across newlines, and needs no host language.
    # No character budget between the two halves: `[^;]{0,300}?` gave up after
    # 300 characters, so one long INSERT ... ON CONFLICT ... DO NOTHING statement
    # was reported clean while the law said the pattern "stops at the statement's
    # semicolon". `[^;]` already stops there, which is the whole bound this needs.
    (re.compile(r"(?is)\bon\s+conflict\b[^;]*?\bdo\s+nothing\b"), "conflict-skipping upsert without a logged skip count"),
    # Fire-and-forget subprocess only: the call starts a statement (result discarded)
    # and carries no check=True. An assigned result (out = subprocess.run(...)) can be
    # inspected, so it is not a silent swallow and is not flagged.
    # The lookahead reads the whole call, not up to the first `)`. `[^)]*` ended
    # at the closing paren of a NESTED call, so
    # `subprocess.run(shlex.split(cmd), check=True)` was reported as a swallowed
    # exit code: a lint firing on correct code is how a gate gets switched off.
    # Two levels of nesting are matched, which covers the forms people write; a
    # third would still be a false positive and the `# sbe: allow-silent` escape
    # is the honest answer to that, in the diff where a reader sees it.
    (re.compile(r"^[ \t]*subprocess\.(run|call|Popen)\("
                r"(?!(?:[^()]|\((?:[^()]|\([^()]*\))*\))*check\s*=\s*True)", re.M),
     "discarded subprocess result without check=True (exit code is swallowed)"),
    (re.compile(r"try\s*!"), "force-try (Swift try! discards the error)"),
]

SCANNABLE = (".py", ".sql", ".swift", ".rb", ".js", ".ts", ".go")
EXEMPTION = "sbe: allow-silent"
# How many of a list this evidence line prints before it says how many it did not.
NAMED_IN_EVIDENCE = 5


def _first_named(items, sep="; ", n=NAMED_IN_EVIDENCE):
    """The first n items, and how many were not named.

    L11's OUTPUT says each hit names its file and line. Six hits printed five and
    the sixth vanished out of a sentence that reads as the whole list, which is
    the truncated-set defect this project keeps finding one level lower.
    """
    shown = sep.join(items[:n])
    return shown if len(items) <= n else shown + "%sand %d more not named" % (sep, len(items) - n)


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
    roots = []
    for a in sys.argv[1:]:
        if a.startswith("-"):
            continue
        if os.path.isdir(a):
            roots.append(a)
            root = a
        else:
            return "FAIL", ("%r is not a directory, so the lint root was never scanned; a mistyped path "
                            "must not read as a clean scan" % a)
    if len(roots) > 1:
        # The last one used to win in silence: the first directory was never
        # scanned and never mentioned, while the sentence named only the
        # survivor. A mistyped path FAILs loudly two lines up; a second valid
        # path is refused just as loudly.
        return "FAIL", ("%d lint roots given (%s) and only one can be scanned per run; the extra "
                        "one(s) would be silently unexamined, so this run refuses instead"
                        % (len(roots), ", ".join(roots)))
    if not root:
        return "NO-DATA", ("no lint root: pass a directory or set SBE_LINT_ROOT. Nothing was opened, "
                           "so there is nothing to call clean")
    if not os.path.isdir(root):
        return "FAIL", "SBE_LINT_ROOT=%s is not a directory, so nothing was scanned" % root
    hits, exempt, self_skipped, empties, unopened = [], [], [], [], []
    scanned, with_matches, all_exempt, empty_files = 0, 0, 0, 0
    pruner = Pruner()
    # onerror: a chmod 000 directory under the lint root used to vanish from the
    # walk, from the count, and from the sentence, so one chmod was a silent
    # bypass of the gate this project calls unwaivable. It is now a FAIL below.
    for dp, dns, fns in os.walk(root, onerror=pruner.onerror):
        # Shared with the other two walkers, and by CONTENT rather than by name:
        # a virtualenv named .venv-whisper put third-party code through THIS gate,
        # which is the one gate a .sbe-exempt cannot waive, and then pruning by
        # name meant renaming a directory hid a repository's own source from it.
        dns[:] = pruner(dp, dns)
        for fn in sorted(fns):
            path_here = os.path.join(dp, fn)
            # The linter declares the patterns as strings, so it must not match
            # itself. By PATH, not by basename: comparing basenames skipped any
            # file called sbe_score.py in the CALLER's tree, so a user's own file
            # with that name was never opened and "1 file(s) scanned, clean" was
            # printed over a directory holding two, one of which carried a bare
            # `except: pass`. And the skip is reported, because a completeness
            # sentence over a set the tool truncated in silence is the class this
            # gate exists to catch.
            if os.path.abspath(path_here) == os.path.abspath(__file__):
                self_skipped.append(os.path.relpath(path_here, root))
                continue
            if not fn.endswith(SCANNABLE):
                continue
            path = path_here
            # The ACCESS axis: a chmod 000 source file used to fall out of the
            # lint, out of the count, and out of the sentence via a bare
            # `continue`, so one chmod silently bypassed the gate this project
            # calls unwaivable. A source file that exists and cannot be read is
            # named and FAILs below; a FIFO or device is refused without open(),
            # which would block forever.
            problem = evidence_problem(path)
            if problem:
                unopened.append("%s (%s)" % (os.path.relpath(path, root), problem))
                continue
            try:
                lines = open(path, errors="replace").read().splitlines()
            except OSError as e:
                unopened.append("%s (%s)" % (os.path.relpath(path, root), type(e).__name__))
                continue
            scanned += 1
            src = "\n".join(lines)
            # A file with the right extension holding nothing, or holding only a
            # placeholder token, carries no source to examine. Reporting either
            # as "clean" is the same sentence as a PASS over an empty manifest.
            if not src.strip() or all_vacuous(src) or vacuous(src):
                empty_files += 1
                empties.append(os.path.relpath(path, root))
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
                    # The reason is the exemption. L11 writes the marker as
                    # `# sbe: allow-silent <reason>` and the reason was
                    # decoration: a bare marker suppressed the finding, which is
                    # an off switch rather than a reviewed exception, and it is
                    # the one gate a .sbe-exempt cannot waive. Read with the
                    # shared answered(), so `# sbe: allow-silent tbd` is refused
                    # here for the same reason "tbd" is refused as a snapshot id.
                    #
                    # Only the FIRST and LAST line of the span count. The upsert
                    # pattern crosses newlines, so its span could enclose an
                    # unrelated hit, and a reason written about THAT hit waived
                    # this one too: one marker, two swallows. The natural places
                    # to write the marker are the line the match starts on and
                    # the line it ends on, and those are the two that are about
                    # this match.
                    edges = span[:1] + (span[-1:] if len(span) > 1 else [])
                    marked = [l for l in edges if EXEMPTION in l]
                    reason = next((r for r in (answered(l.split(EXEMPTION, 1)[1]) for l in marked)
                                   if r), None)
                    # A reason is a justification a human can review, so it is
                    # held to a floor: "x", "ok" and "0" waived hits, and so did
                    # a reason that was just the marker pasted again.
                    if reason and (EXEMPTION in reason or len(reason) < 8
                                   or len(reason.split()) < 2):
                        reason = None
                    if marked and reason:
                        file_exempt += 1
                        exempt.append("%s:%d" % (os.path.relpath(path, root), first + 1))
                        continue
                    file_hits += 1
                    hits.append("%s:%d %s%s"
                                % (os.path.relpath(path, root), first + 1, desc,
                                   "" if not marked else
                                   " (an `%s` marker with no reason after it waives nothing; write "
                                   "what makes this swallow legal)" % EXEMPTION))
            if file_hits or file_exempt:
                with_matches += 1
                if not file_hits:
                    all_exempt += 1
    # Everything this scan did NOT open, on every verdict it prints. A pruned
    # directory and a self-skipped file are both files a "clean" sentence would
    # otherwise be claiming over.
    note = pruner.note(lambda f: f.endswith(SCANNABLE))
    if self_skipped:
        note += ("; this tool's own source was not scanned (%s), because it declares these "
                 "patterns as strings and would match itself"
                 % ", ".join(sorted(self_skipped)))
    # Evidence the lint was refused access to beats every other verdict: a
    # verdict over the files it could open would read as covering the tree, and
    # one chmod must never turn a FAIL into a PASS or into an absence.
    if unopened or pruner.denied:
        refused = sorted(set(unopened)) + sorted(set(pruner.denied))
        return "FAIL", ("%d file(s) or director(y/ies) under %s exist and could not be read (%s); "
                        "source this lint cannot open is source this verdict cannot cover, so it "
                        "cannot call the tree clean; %d file(s) were scanned%s"
                        % (len(refused), root, _first_named(refused, "; "), scanned, note))
    if not scanned:
        return "NO-DATA", ("lint root %s holds no scannable source (%s), so nothing was opened%s"
                           % (root, " ".join(SCANNABLE), note))
    if empty_files == scanned:
        # Files with the right extensions and nothing in them were opened and
        # reported "clean", which is the same sentence as a PASS over an empty
        # manifest. A scan of empty files examined no source.
        return "NO-DATA", ("%d file(s) scanned under %s and every one of them is empty or holds "
                           "nothing but a placeholder, so no line of source was examined and there "
                           "is nothing to call clean%s" % (scanned, root, note))
    # A file with nothing in it is not source anybody examined, and in a MIXED run
    # it was counted inside "N file(s) scanned, clean" with nothing saying so. The
    # all-empty run already had its own verdict; this is the same sentence for the
    # rest of the runs.
    if empties:
        note += ("; %d of the %d file(s) scanned hold nothing to examine (%s), so the count above is "
                 "not a count of files with source in them"
                 % (len(empties), scanned, _first_named(empties, ", ")))
    if hits:
        return "FAIL", ("%d hit(s) in %d file(s) scanned: %s%s"
                        % (len(hits), scanned, _first_named(hits), note))
    if exempt and all_exempt == scanned:
        return "NO-DATA", ("%d file(s) scanned under %s and every match in every one of them was "
                           "suppressed by an inline `%s` comment (%s); a scan whose every finding was "
                           "waived examined nothing it was allowed to report, so it is not clean%s"
                           % (scanned, root, EXEMPTION, _first_named(exempt, ", "), note))
    if exempt:
        # The clean-file count is the whole argument for PASS here rather than the
        # NO-DATA one branch up: source WAS examined and found clean somewhere.
        # It was left to the reader to work out from a truncated list of waived
        # lines, and SKILL.md's sentence about this repository's own run had it
        # wrong in both numbers for as long as nothing printed it.
        return "PASS", ("%d file(s) scanned under %s, 0 unexempted hit(s), %d suppressed by an inline "
                        "`%s` comment (%s), %d file(s) holding no match at all%s"
                        % (scanned, root, len(exempt), EXEMPTION, _first_named(exempt, ", "),
                           scanned - with_matches, note))
    return "PASS", "%d file(s) scanned under %s, clean%s" % (scanned, root, note)


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
# Five DISTINCT predictions. The fixture used to be one prediction across five
# dates, which certified the dedupe bypass as the worked example of correct
# evidence: the threshold counts predictions, not rows.
_PREDICTIONS = ("# Operator model\n## Prediction ledger\n"
                "date | prediction | seal | scored on | hit\n"
                "2026-07-01 | the queue depth stays under 1k | seal-1 | review | yes\n"
                "2026-07-02 | the backlog drains by Friday | seal-2 | review | yes\n"
                "2026-07-03 | the cache ratio holds above 90 | seal-3 | review | no\n"
                "2026-07-04 | the retry storm does not recur | seal-4 | review | yes\n"
                "2026-07-05 | the export lands before 09:00 | seal-5 | review | yes\n")

CHECKS = {
    "ledger-coverage": Check(
        check_ledger_coverage, reads=(LEDGER,), kind="jsonl", severity="soft",
        full_fixture={"files": {_rel(LEDGER): [{"session_id": "sess-0001", "ts": "%(now)s"}]}}),
    "schema-2-uniform": Check(
        check_schema_uniform, reads=(LEDGER,), kind="jsonl", severity="soft",
        full_fixture={"files": {_rel(LEDGER): [{"schema": 2, "session_id": "sess-0001"}]}}),
    "cache-economy": Check(
        check_cache_economy, reads=(LEDGER,), kind="jsonl", severity="soft",
        full_fixture={"files": {_rel(LEDGER): [{"session_id": "sess-0001", "ts": "%(now)s",
                                                "cache_read": 95, "cache_write": 5}]}}),
    "vault-log-per-active-day": Check(
        check_vault_log_per_active_day, reads=(LEDGER,), kind="jsonl", severity="soft",
        full_fixture={"files": {_rel(LEDGER): [{"session_id": "sess-0001", "ts": "%(now)s"}],
                                "10-Projects/demo/Sessions/%(today)s-session.md":
                                    "# Session log\nWhat happened today.\n"}}),
    "fence-hygiene": Check(check_fence_hygiene, reads=("BROTHERSBE_REGISTRIES",), kind="tree", severity="soft",
                           empty_fixture={"files": {"STATE.md": ""}, "value": "%(dir)s/*.md"},
                           full_fixture=_FENCE_REGISTRY),
    "correction-latency": Check(
        check_correction_latency, reads=(CORRECTIONS,), kind="jsonl", severity="soft",
        full_fixture={"files": {_rel(CORRECTIONS): [{"ts": "%(now)s"}]}}),
    "budget-vs-tier": Check(check_budget_vs_tier, reads=("BROTHERSBE_REGISTRIES",), kind="tree", severity="soft",
                            empty_fixture={"files": {"STATE.md": ""}, "value": "%(dir)s/*.md"},
                            full_fixture=_FENCE_REGISTRY),
    "prediction-seals": Check(check_prediction_seals, reads=(OPERATOR_MODEL,), kind="text", severity="soft",
                              full_fixture={"files": {_rel(OPERATOR_MODEL): _PREDICTIONS}}),
    "felt-outcome-ratings": Check(
        check_felt_outcome_ratings, reads=(RATINGS,), kind="jsonl", severity="soft",
        # Six DISTINCT rows. The fixture used to be one row repeated six times,
        # which is exactly the defect the shared dedupe rule closed: it certified
        # a threshold by writing the same rating out six times.
        full_fixture={"files": {_rel(RATINGS): [{"score": s} for s in (5, 4, 3, 2, 1, 0)]}}),
    "review-cadence": Check(
        check_review_cadence, reads=(REVIEWS,), kind="jsonl", severity="soft",
        full_fixture={"files": {_rel(REVIEWS): [{"ts": "%(now)s"}]}}),
    "silent-failure-lints": Check(silent_failure_lints, reads=("SBE_LINT_ROOT",), kind="tree", severity="gate",
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
        print("%-*s  %-7s  %s [severity: %s]" % (width, n, v, e, CHECKS[n].severity))
    print("\n%d checks: %d PASS, %d FAIL, %d NO-DATA. LLM judge scores only the residue."
          % (len(results), sum(1 for _, v, _ in results if v == "PASS"), fails,
             sum(1 for _, v, _ in results if v == "NO-DATA")))
    # Two modes, same checks: the local hook stays advisory (exit 0, never blocks a
    # session), but strict runs exit nonzero so CI can block a merge. Which FAILs
    # block is the severity each check declared at write time, printed on its
    # verdict line: `--strict` blocks on gate severity (here, the lints), and soft
    # severity blocks only under the opt-in `--strict-soft` (which implies
    # --strict), so a graded practice check cannot stop a merge unless the
    # repository asked for exactly that. The shipped workflow passes both flags.
    gate_fails = sum(1 for n, v, _ in results if v == "FAIL" and CHECKS[n].severity == "gate")
    soft_fails = fails - gate_fails
    strict_soft = "--strict-soft" in sys.argv
    strict = "--strict" in sys.argv or strict_soft
    if strict and gate_fails:
        print("STRICT: %d gate-severity check(s) failed; exiting nonzero to fail the CI gate." % gate_fails)
        sys.exit(1)
    if strict_soft and soft_fails:
        print("STRICT-SOFT: %d soft-severity check(s) failed; exiting nonzero because "
              "--strict-soft opts graded checks into blocking." % soft_fails)
        sys.exit(1)
    if strict and soft_fails:
        print("NOTE: %d soft-severity check(s) failed. --strict blocks on gate severity only; "
              "add --strict-soft to block on these too." % soft_fails)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # A broken checker must not silently waive the gate. In strict mode a crash
        # blocks, exactly as in sbe_gate.py; advisory mode still never blocks a session.
        print("sbe_score: error %r" % (e,))
        sys.exit(1 if ("--strict" in sys.argv or "--strict-soft" in sys.argv) else 0)
