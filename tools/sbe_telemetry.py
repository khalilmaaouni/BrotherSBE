#!/usr/bin/env python3
"""BrotherSBE telemetry: the mechanical half of the learning loop. Schema 2.

Subcommands:
  outcomes-append   SessionEnd hook target. Reads hook JSON on stdin, parses the
                    session transcript, appends ONE atomic JSONL line to the ledger
                    (schema 2: GenAI semconv token names) and scans the MAIN
                    transcript's short operator messages for correction candidates.
  migrate           One-time ledger migration to schema 2 (idempotent, temp+rename,
                    line-count recheck; never backfills absent values).
  scorecard         Renders the 9-metric dashboard from the ledger + companion files.
  rate              Records a operator felt-outcome rating (1-5).
  review-mark       Records that a weekly review ran (feeds the overdue nag).
  startup-nags      One-line nags + yesterday's spend for SessionStart injection.
  stop-warn         Stop hook target, WARN ONLY (never blocks): systemMessage JSON
                    when a qualifying session has no vault session log today.
                    Cheap short-circuits only; never parses the transcript.
  registry-check    Flags fence-registry lines that look live in a stale file.
  fence-lint        Dispatch aid: prints live fences from the project's STATE.md
                    and the BROTHERSBE_REGISTRIES globs before a writer launches.
  prediction-audit  Counts sealed predictions in the operator model ledger.
  check-update      OFFLINE check of your installed copy: warns when an already
                    fetched update is waiting, when the copy has gone stale, and
                    once when the law itself changed under you. Reads git refs as
                    plain files: no network call, no subprocess, ever.
  intent            Write-ahead intent log. `intent "next: X, because Y"` appends
                    one line to a per-project log BEFORE a risky/long action, so a
                    death always leaves a forward-looking record (the write-ahead
                    log pattern: log the intent before the action, like a database).
                    The resume brief surfaces the last intent first.
  precompact-brief  PreCompact hook helper. Reads the hook JSON on stdin, extracts
                    the TAIL of the dying session's transcript (last instruction,
                    recent decisions, recent commands) and writes a resume brief to
                    the vault, so a resumed session recovers the THREAD, not just the
                    files the git autosave saved. Pure: reads/writes files only.
  compact-hint      SessionStart(source=compact) helper. Reads the hook JSON on
                    stdin; if the session just resumed from a compaction, prints a
                    one-line pointer to the autosave recovery command. Pure: reads
                    stdin and prints, no subprocess, no network.
  handoff           One shareable, SECRET-REDACTED markdown for handing a project
                    to a small team: overview + open items + latest session + recent
                    outcomes, assembled from the vault. Pure: reads vault files,
                    redacts, writes one file. No subprocess, no network.
  purge-corrections Deletes captured correction candidates (excerpts of your own
                    messages, secret-redacted and owner-only, but still yours to
                    delete). Shows the count first; --yes to confirm.
  speed             Wall-clock view for rubric metric 3: last 7d vs prior 7d,
                    span-hours per OUTCOMES line (labeled proxy, never invented).
  dedup             One-time cleanup of duplicate hook flushes (backup + count
                    check; keeps last flush per identical metric set).

Law: this tool NEVER blocks work. Every path exits 0. Numbers are parsed or
absent; nothing is invented. Token counts are labeled as-flushed (the transcript
may lag the final turn). Old (schema 1) and new lines are both readable: use
fld() everywhere.
"""
import json, os, sys, glob, re, datetime, hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbe_checks import distinct, evidence_problem

# ---------------------------------------------------------------------------
# Configuration. The vault is the durable memory folder every ledger lives in.
# Default: ~/BrotherSBEVault. Point BROTHERSBE_VAULT anywhere you prefer.
# Layout, created on demand by atomic_append:
#   <vault>/99-System/telemetry/outcomes.jsonl     one line per real session
#   <vault>/99-System/telemetry/ratings.jsonl      operator felt-outcome scores
#   <vault>/99-System/telemetry/reviews.jsonl      weekly review markers
#   <vault>/99-System/telemetry/corrections.jsonl  correction candidates
#   <vault>/50-Reference/operator-model.md          prediction ledger (optional)
#   <vault>/10-Projects/<name>/Sessions/*.md       human session logs
# ---------------------------------------------------------------------------
VAULT = os.environ.get("BROTHERSBE_VAULT", os.path.expanduser("~/BrotherSBEVault"))
TEL_DIR = os.path.join(VAULT, "99-System", "telemetry")
LEDGER = os.path.join(TEL_DIR, "outcomes.jsonl")
RATINGS = os.path.join(TEL_DIR, "ratings.jsonl")
REVIEWS = os.path.join(TEL_DIR, "reviews.jsonl")
CORRECTIONS = os.path.join(TEL_DIR, "corrections.jsonl")
OPERATOR_MODEL = os.path.join(VAULT, "50-Reference", "operator-model.md")
SESSIONS_GLOB = os.path.join(VAULT, "10-Projects", "*", "Sessions", "*.md")

MIN_API_MSGS = 5
MIN_TOOL_CALLS = 1
STOPWARN_MIN_BYTES = 200_000   # transcript smaller than this = trivial, stay silent
# Hook self-test end_reasons: real work never uses these. Excluded from every
# aggregate so the learning loop scores on real sessions only (weekly-review
# 2026-07-20 finding: 2 smoke-test lines polluted session counts and token sums).
TEST_END_REASONS = {"simulated-test", "chained-smoke-test", "smoke-test", "test"}

OUT_KEYS = ("gen_ai.usage.output_tokens", "out_tokens")
IN_KEYS = ("gen_ai.usage.input_tokens",)
CORRECTION_RE = re.compile(
    r"\b(no[,.]? (that|this|the)|not what i|wrong|you did not|you didn'?t|not even"
    r"|i said|stop doing|never do|always use|from now on|instead of|do better)\b",
    re.I)


def fld(rec, keys, default=0):
    for k in keys:
        if k in rec:
            return rec[k]
    return default


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_append(path, obj, mode=0o644):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = (json.dumps(obj, separators=(",", ":")) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, mode)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


def parse_transcript(path, collect_user_texts=False):
    agg = {"out": 0, "cache_w": 0, "cache_r": 0, "in": 0, "api_msgs": 0,
           "tool_calls": 0, "agent_spawns": 0, "workflow_calls": 0,
           "human_msgs": 0, "models": {}, "first_ts": None, "last_ts": None,
           "user_texts": []}
    per_msg = {}
    anon = 0
    try:
        f = open(path, "r", errors="replace")
    except OSError:
        return agg
    with f:
        for raw in f:
            try:
                o = json.loads(raw)
            except Exception:
                continue
            ts = o.get("timestamp")
            if isinstance(ts, str) and len(ts) >= 19:
                if agg["first_ts"] is None or ts < agg["first_ts"]:
                    agg["first_ts"] = ts
                if agg["last_ts"] is None or ts > agg["last_ts"]:
                    agg["last_ts"] = ts
            t = o.get("type")
            if t == "user" and not o.get("isMeta"):
                c = (o.get("message") or {}).get("content")
                txt = None
                if isinstance(c, str):
                    txt = c
                elif isinstance(c, list):
                    if not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                        txt = "\n".join(b.get("text", "") for b in c
                                        if isinstance(b, dict) and b.get("type") == "text")
                if txt and txt.strip() and "<system-reminder>" not in txt:
                    agg["human_msgs"] += 1
                    if collect_user_texts:
                        agg["user_texts"].append(txt.strip())
            if t != "assistant":
                continue
            m = o.get("message") or {}
            model = m.get("model")
            if model:
                agg["models"][model] = agg["models"].get(model, 0) + 1
            u = m.get("usage")
            if u:
                mid = m.get("id")
                if not mid:
                    mid = "anon%d" % anon
                    anon += 1
                slot = per_msg.setdefault(mid, {})
                for k in ("input_tokens", "output_tokens",
                          "cache_creation_input_tokens", "cache_read_input_tokens"):
                    v = u.get(k) or 0
                    if v > slot.get(k, 0):
                        slot[k] = v
            for b in (m.get("content") or []):
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    agg["tool_calls"] += 1
                    name = b.get("name", "")
                    if name in ("Task", "Agent"):
                        agg["agent_spawns"] += 1
                    elif name == "Workflow":
                        agg["workflow_calls"] += 1
    agg["api_msgs"] = len(per_msg)
    for s in per_msg.values():
        agg["out"] += s.get("output_tokens", 0)
        agg["in"] += s.get("input_tokens", 0)
        agg["cache_w"] += s.get("cache_creation_input_tokens", 0)
        agg["cache_r"] += s.get("cache_read_input_tokens", 0)
    return agg


# Correction candidates are excerpts of YOUR OWN messages, so they can carry
# secrets you typed. Redact secret-shaped substrings before anything is written,
# and keep the file owner-only. This is best-effort pattern matching, not a
# guarantee: treat the file as sensitive and purge it when you no longer need it
# (tools/sbe_telemetry.py purge-corrections).
SECRET_PATTERNS = [
    re.compile(r"\b(sk|rk)[-_][A-Za-z0-9_-]{12,}", re.I),           # api keys
    re.compile(r"\bgh[oprsu]_[A-Za-z0-9]{16,}"),                     # github tokens
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                            # aws key id
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}", re.I),             # slack
    re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"-----BEGIN[ A-Z]*PRIVATE KEY-----"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),      # jwt
    # key=value and key: value where the key names a secret
    # key=value, key: value, and the natural-language "the password is hunter2".
    # Over-redaction is deliberate here: a masked non-secret costs nothing, a
    # stored secret costs a lot.
    # Leading [A-Za-z0-9_]* so PROD_DB_PASSWORD= matches as well as password=.
    re.compile(r"(?i)[A-Za-z0-9_]*(?:pass(?:word|wd|phrase)?|secret|token"
               r"|api[_-]?key|access[_-]?key|private[_-]?key|credential)s?"
               r"\s*(?:[:=]|\s+(?:is|was)\s+)\s*\S+"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                          # us ssn shape
    re.compile(r"\b(?:\d[ -]?){13,16}\b"),                          # card-ish digits
]


def redact(text):
    """Mask secret-shaped substrings. Returns (clean_text, n_redactions)."""
    n = 0
    for pat in SECRET_PATTERNS:
        text, k = pat.subn("[REDACTED]", text)
        n += k
    return text, n


def scan_corrections(sid, project, user_texts):
    """Correction CANDIDATES from short operator messages in the MAIN transcript
    only (subagent transcripts quote law text and would flood this). Human filter
    at the weekly review decides what becomes law; cap 5 per session.
    Dedup guard (interim-score fix 2026-07-23): the SessionEnd hook can fire more
    than once per session; a (session_id, text) already in the file is never
    re-appended."""
    seen = {(c.get("session_id"), c.get("text")) for c in read_jsonl(CORRECTIONS)}
    found = 0
    for txt in user_texts:
        if found >= 5:
            break
        if len(txt) > 400:
            continue
        if CORRECTION_RE.search(txt):
            clean, nred = redact(txt[:400])
            if (sid, clean) in seen:
                continue
            rec = {"ts": now_iso(), "session_id": sid,
                   "project": project, "text": clean}
            if nred:
                rec["redactions"] = nred
            atomic_append(CORRECTIONS, rec, mode=0o600)
            seen.add((sid, clean))
            found += 1
    return found


def cmd_outcomes_append():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print("sbe_telemetry: no valid hook payload on stdin; nothing recorded")
        return
    tp = payload.get("transcript_path") or ""
    sid = payload.get("session_id") or "unknown"
    cwd = payload.get("cwd") or ""
    if not tp or not os.path.isfile(tp):
        print("sbe_telemetry: transcript not found; nothing recorded")
        return
    main = parse_transcript(tp, collect_user_texts=True)
    sub = {"out": 0, "files": 0}
    subroot = os.path.join(os.path.dirname(tp), sid, "subagents")
    if os.path.isdir(subroot):
        for sf in glob.glob(os.path.join(subroot, "**", "*.jsonl"), recursive=True):
            sub["files"] += 1
            sa = parse_transcript(sf)
            sub["out"] += sa["out"]
    if main["api_msgs"] < MIN_API_MSGS or main["tool_calls"] < MIN_TOOL_CALLS:
        print("sbe_telemetry: below activity floor (%d api msgs, %d tool calls); not recorded"
              % (main["api_msgs"], main["tool_calls"]))
        return
    project = os.path.basename(cwd) or cwd
    hours = 0.0
    if main["first_ts"] and main["last_ts"]:
        try:
            a = datetime.datetime.fromisoformat(main["first_ts"].replace("Z", "+00:00"))
            b = datetime.datetime.fromisoformat(main["last_ts"].replace("Z", "+00:00"))
            hours = round((b - a).total_seconds() / 3600, 2)
        except Exception:  # sbe: allow-silent a hook must never crash a session; the miss is visible as absent telemetry
            pass
    rec = {
        "schema": 2, "ts": now_iso(), "session_id": sid, "project": project,
        "end_reason": payload.get("reason") or "",
        "gen_ai.usage.output_tokens": main["out"],
        "gen_ai.usage.input_tokens": main["in"],
        "sub_out_tokens": sub["out"],
        "cache_write": main["cache_w"], "cache_read": main["cache_r"],
        "api_msgs": main["api_msgs"], "human_msgs": main["human_msgs"],
        "tool_calls": main["tool_calls"], "agent_spawns": main["agent_spawns"],
        "workflow_calls": main["workflow_calls"], "subagent_files": sub["files"],
        "models": sorted(main["models"].keys()), "duration_h": hours,
        "token_basis": "as-flushed",
    }
    # Duplicate-flush guard (interim-score fix 2026-07-23): the SessionEnd hook
    # can fire repeatedly for one session; an identical metric set (everything
    # but ts) is the same flush and is not recorded twice. A changed metric set
    # is real progress and still appends (real_sessions keeps the last flush).
    comparable = {k: v for k, v in rec.items() if k != "ts"}
    for prev in read_jsonl(LEDGER):
        if prev.get("session_id") == sid and {k: v for k, v in prev.items() if k != "ts"} == comparable:
            print("sbe_telemetry: duplicate flush for %s (identical metrics); not recorded" % sid[:8])
            return
    atomic_append(LEDGER, rec)
    ncorr = scan_corrections(sid, project, main["user_texts"])
    print("sbe_telemetry: recorded %s (%dk out, %d tools, %.1fh, %d correction candidates)"
          % (sid[:8], main["out"] // 1000, main["tool_calls"], hours, ncorr))


def cmd_migrate():
    if not os.path.isfile(LEDGER):
        print("migrate: no ledger yet")
        return
    rows = read_jsonl(LEDGER)
    n_before = len(rows)
    changed = 0
    out = []
    for r in rows:
        if r.get("schema") != 2:
            r = dict(r)
            if "out_tokens" in r:
                r["gen_ai.usage.output_tokens"] = r.pop("out_tokens")
            r["schema"] = 2
            # input tokens were never recorded pre-schema-2: stays ABSENT, never invented
            changed += 1
        out.append(r)
    # Back up before the rewrite, so the failure message below is honest.
    bak = LEDGER + ".bak-migrate" + datetime.date.today().strftime("%Y%m%d")
    if not os.path.exists(bak):
        with open(bak, "w") as f:
            for r in rows:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")
    tmp = LEDGER + ".tmp"
    with open(tmp, "w") as f:
        for r in out:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")
    os.rename(tmp, LEDGER)
    n_after = len(read_jsonl(LEDGER))
    if n_after < n_before:
        print("migrate: LINE COUNT DROPPED %d->%d, restore from backup!" % (n_before, n_after))
    else:
        print("migrate: %d lines, %d migrated to schema 2, count ok (%d)"
              % (n_before, changed, n_after))


def cmd_dedup():
    """One-time cleanup of duplicate hook flushes already in the files. Backup
    first, temp+rename, count check printed. Outcomes: drop rows whose metric
    set (everything but ts) matches an already-kept row for the same session,
    keeping the LAST occurrence (matches real_sessions semantics). Corrections:
    drop duplicate (session_id, text), keeping the first."""
    stamp = datetime.date.today().strftime("%Y%m%d")
    for path, keyfn, keep in (
        (LEDGER, lambda r: (r.get("session_id"),
                            json.dumps({k: v for k, v in r.items() if k != "ts"},
                                       sort_keys=True)), "last"),
        (CORRECTIONS, lambda r: (r.get("session_id"), r.get("text")), "first"),
    ):
        rows = read_jsonl(path)
        if not rows:
            print("dedup: %s empty or missing, skipped" % os.path.basename(path))
            continue
        if keep == "last":
            kept_rev, seen = [], set()
            for r in reversed(rows):
                k = keyfn(r)
                if k in seen:
                    continue
                seen.add(k)
                kept_rev.append(r)
            kept = list(reversed(kept_rev))
        else:
            kept, seen = [], set()
            for r in rows:
                k = keyfn(r)
                if k in seen:
                    continue
                seen.add(k)
                kept.append(r)
        if len(kept) == len(rows):
            print("dedup: %s already clean (%d lines)" % (os.path.basename(path), len(rows)))
            continue
        bak = "%s.bak-dedup%s" % (path, stamp)
        if not os.path.exists(bak):
            with open(bak, "w") as f:
                for r in rows:
                    f.write(json.dumps(r, separators=(",", ":")) + "\n")
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            for r in kept:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")
        os.rename(tmp, path)
        print("dedup: %s %d -> %d lines (%d duplicate flushes dropped; backup %s)"
              % (os.path.basename(path), len(rows), len(kept),
                 len(rows) - len(kept), os.path.basename(bak)))


def outcomes_lines_in_window(min_age_d, max_age_d):
    """Dated human lines in the vault OUTCOMES ledgers (one line per recorded
    run; the closest thing to 'shipped surface' the system records)."""
    n = 0
    today = datetime.date.today()
    for path in glob.glob(os.path.join(VAULT, "10-Projects", "*", "OUTCOMES.md")):
        for line in open(path, errors="replace"):
            m = re.match(r"^(\d{4}-\d{2}-\d{2}) \|", line)
            if not m:
                continue
            try:
                age = (today - datetime.date.fromisoformat(m.group(1))).days
            except ValueError:
                continue
            if min_age_d <= age < max_age_d:
                n += 1
    return n


def cmd_speed():
    """Rubric metric 3 feed. HONEST LABELS: duration_h is the span from first to
    last message (includes idle), and OUTCOMES lines are human-recorded runs, a
    PROXY for shipped surfaces. No proxy, no number."""
    rows = real_sessions(read_jsonl(LEDGER))
    def window(lo, hi):
        w = [r for r in rows if lo <= (age_days(r.get("ts", "")) or 999) < hi]
        return {"sessions": len(w),
                "hours": round(sum(r.get("duration_h", 0) for r in w), 1),
                "outk": sum(fld(r, OUT_KEYS) + r.get("sub_out_tokens", 0) for r in w) // 1000}
    cur, prev = window(0, 7), window(7, 14)
    cur_runs, prev_runs = outcomes_lines_in_window(0, 7), outcomes_lines_in_window(7, 14)
    print("BROTHERSBE SPEED (metric 3 feed; span-hours include idle, runs are OUTCOMES lines)")
    for label, w, runs in (("last 7d ", cur, cur_runs), ("prior 7d", prev, prev_runs)):
        per = ("%.1f span-h/run" % (w["hours"] / runs)) if runs else "no runs recorded"
        print("  %s: %d sessions, %.1f span-h, %dk out, %d recorded runs -> %s"
              % (label, w["sessions"], w["hours"], w["outk"], runs, per))
    if not (cur_runs and prev_runs):
        print("  trend: NO-DATA (both windows need recorded runs; nothing is invented)")


def read_jsonl(path):
    rows = []
    if not os.path.isfile(path):
        return rows
    for raw in open(path, errors="replace"):
        try:
            rows.append(json.loads(raw))
        except Exception:
            continue
    return rows


def real_sessions(rows):
    """One row per real session: drop hook self-tests, dedup by session_id
    (last flush wins). Both the scorecard and the startup nag use this so
    'sessions' means the same thing in every output."""
    by = {}
    for r in rows:
        if r.get("end_reason") in TEST_END_REASONS:
            continue
        by[r.get("session_id", "?")] = r
    return list(by.values())


def age_days(iso):
    try:
        t = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 86400
    except Exception:
        return None


def cmd_scorecard():
    led = read_jsonl(LEDGER)
    rows = real_sessions(led)
    ratings = read_jsonl(RATINGS)
    reviews = read_jsonl(REVIEWS)
    corrections = read_jsonl(CORRECTIONS)
    preds = prediction_counts()
    recent = [r for r in rows if (age_days(r.get("ts", "")) or 99) <= 7]
    out7 = sum(fld(r, OUT_KEYS) + r.get("sub_out_tokens", 0) for r in recent)
    cr = sum(r.get("cache_read", 0) for r in recent)
    cw = sum(r.get("cache_write", 0) for r in recent)
    ratio = (100.0 * cr / (cr + cw)) if (cr + cw) else None
    rated = [x for x in ratings if isinstance(x.get("score"), (int, float))]
    avg_rating = round(sum(x["score"] for x in rated) / len(rated), 2) if rated else None
    last_review = max((x.get("ts", "") for x in reviews), default=None)
    lr_age = age_days(last_review) if last_review else None
    print("BROTHERSBE SCORECARD  (mechanical fields computed; judgment fields scored at weekly review)")
    print("ledger: %d sessions, %d last 7d, %dk out last 7d, %d correction candidates pending"
          % (len(rows), len(recent), out7 // 1000, len(corrections)))
    print("1 self-learning : reviews=%d, last=%s, sealed predictions=%d (10: 0 gaps 14d + 2 reviews + >=5 predictions)"
          % (len(reviews), ("%.1fd" % lr_age) if lr_age is not None else "never", preds["sealed"]))
    print("2 token economy : measured=%d/%d, out 7d=%dk, budget-vs-tier: sbe_score check (10: 0 unmeasured + budgets enforced + trend down)"
          % (len(rows), len(rows), out7 // 1000))
    print("3 speed         : run 'sbe_telemetry.py speed' for the metric 3 feed; trend judged at weekly review")
    print("4 alignment     : ratings=%d avg=%s, prediction hits=%s/%s, corrections captured=%d (10: avg>=4.5 + 0 repeats 2wk)"
          % (len(rated), avg_rating, preds["hits"], preds["scored"], len(corrections)))
    print("5 memory        : canonical=%s; registry + vault hygiene judged weekly" % LEDGER)
    print("6 honesty       : floor gate; evidence blocks in fence closes judged weekly")
    print("7 coordination  : floor gate; collisions=0, baton drops=0, resume-not-respawn judged weekly")
    print("8 delivery      : shipped surfaces vs spend, check: fields on fences, judged weekly")
    print("9 cache economy : warm-read ratio 7d=%s (10: sustained >=90%% + zero broken-prefix incidents 2wk)"
          % (("%.1f%%" % ratio) if ratio is not None else "no data"))


def prediction_counts():
    """Sealed, scored and hit predictions, counting each DISTINCT row once.

    Five identical rows are one prediction written five times, and they cleared
    the "at least 5 sealed" threshold. The rule is sbe_checks.distinct(), shared
    with gate_numbers and the other two thresholds that did not have it.
    """
    out = {"sealed": 0, "scored": 0, "hits": 0, "note": ""}
    # ACCESS before open(): a FIFO at this path would hang the scorecard forever,
    # and an unreadable file would read as an absent ledger. The counts stay
    # zero and the note says why; the scorer's own check FAILs on the same test.
    problem = evidence_problem(OPERATOR_MODEL)
    if problem:
        out["note"] = "; %s is %s, so no prediction row was read" % (OPERATOR_MODEL, problem)
        return out
    if not os.path.isfile(OPERATOR_MODEL):
        return out
    in_ledger = False
    rows = []
    for line in open(OPERATOR_MODEL, errors="replace"):
        if line.startswith("## Prediction ledger"):
            in_ledger = True
            continue
        if in_ledger and line.startswith("## "):
            break
        if in_ledger and line.strip().startswith("20") and "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 5 and parts[2] not in ("n/a", ""):
                rows.append(parts)
    unique, dupes = distinct([" | ".join(p) for p in rows])
    for parts in [p.split(" | ") for p in unique]:
        out["sealed"] += 1
        if parts[4].lower().startswith(("yes", "hit", "no", "miss")):
            out["scored"] += 1
            if parts[4].lower().startswith(("yes", "hit")):
                out["hits"] += 1
    if dupes:
        out["note"] = "; %d identical ledger row(s) counted once" % dupes
    return out


def cmd_rate(argv):
    score, task, note = None, "", ""
    it = iter(argv)
    for a in it:
        if a == "--score":
            score = float(next(it, "0"))
        elif a == "--task":
            task = next(it, "")
        elif a == "--note":
            note = next(it, "")
    if score is None or not (1 <= score <= 5):
        print("usage: rate --score 1..5 --task \"...\" [--note \"...\"]")
        return
    atomic_append(RATINGS, {"ts": now_iso(), "score": score, "task": task, "note": note})
    print("sbe_telemetry: rating %.1f recorded for '%s'" % (score, task))


def cmd_review_mark(argv):
    atomic_append(REVIEWS, {"ts": now_iso(), "note": " ".join(argv)})
    print("sbe_telemetry: weekly review marked")


def cmd_startup_nags():
    reviews = read_jsonl(REVIEWS)
    last = max((x.get("ts", "") for x in reviews), default=None)
    a = age_days(last) if last else None
    if a is None:
        print("BROTHERSBE NAG: weekly review has NEVER run; run tools/WEEKLY-REVIEW.md this week.")
    elif a > 7:
        print("BROTHERSBE NAG: weekly review overdue (%.0f days); run tools/WEEKLY-REVIEW.md." % a)
    led = real_sessions(read_jsonl(LEDGER))
    y = [r for r in led if 0.0 <= (age_days(r.get("ts", "")) or 99) <= 1.0]
    if y:
        yk = sum(fld(r, OUT_KEYS) + r.get("sub_out_tokens", 0) for r in y)
        print("BROTHERSBE SPEND: last 24h %dk out tokens across %d sessions." % (yk // 1000, len(y)))
    recent = [r for r in led if (age_days(r.get("ts", "")) or 99) <= 2]
    if led and not recent:
        print("BROTHERSBE NAG: telemetry heartbeat silent 48h; check the SessionEnd hook.")
    # Session-log-per-active-day nag (interim-score fix 2026-07-23): same failure
    # mode as pre-hook token telemetry, same cure. A log counts by filename date
    # OR mtime date, so late backfills clear the nag. Today is exempt (in flight).
    log_days = set()
    for f in glob.glob(SESSIONS_GLOB):
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", os.path.basename(f))
        if m:
            log_days.add(m.group(1))
        try:
            log_days.add(datetime.date.fromtimestamp(os.path.getmtime(f)).isoformat())
        except OSError:
            continue
    today = datetime.date.today().isoformat()
    active = {r.get("ts", "")[:10] for r in led if 0 < (age_days(r.get("ts", "")) or 99) <= 3}
    missing = sorted(d for d in active if d and d not in log_days and d != today)
    if missing:
        print("BROTHERSBE NAG: active day(s) %s have no vault session log; backfill or waive with a note."
              % ", ".join(missing))


def cmd_stop_warn():
    """Stop hook, fires EVERY assistant turn machine-wide: must be near-free.
    Short-circuits in order; NEVER parses the transcript; warn at most once per
    session via a marker file; warn-only (exit 0 cannot block)."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    sid = payload.get("session_id") or ""
    tp = payload.get("transcript_path") or ""
    if not sid or not tp:
        return
    # Marker lives under the vault, not /tmp: a predictable /tmp name on a
    # shared machine is a symlink hazard, and the vault is already ours.
    marker = os.path.join(TEL_DIR, ".stopwarn-%s" % re.sub(r"[^A-Za-z0-9_-]", "", sid))
    if os.path.exists(marker):
        return
    try:
        if os.path.getsize(tp) < STOPWARN_MIN_BYTES:
            return
    except OSError:
        return
    today = datetime.date.today()
    for f in glob.glob(SESSIONS_GLOB):
        try:
            if datetime.date.fromtimestamp(os.path.getmtime(f)) == today:
                return
        except OSError:
            continue
    try:
        os.makedirs(TEL_DIR, exist_ok=True)
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        os.close(fd)
    except OSError:
        return
    print(json.dumps({"systemMessage":
        "BrotherSBE: substantial session, no vault session log written today. "
        "Write the log before closing (vault law), or note why it is not needed."}))


def cmd_registry_check(argv):
    paths = argv or []
    if not paths:
        print("registry-check: pass STATE.md paths to check")
        return
    for p in paths:
        if not os.path.isfile(p):
            print("%s: missing" % p)
            continue
        age = (datetime.datetime.now().timestamp() - os.path.getmtime(p)) / 86400
        live = []
        for line in open(p, errors="replace"):
            s = line.strip()
            if s.startswith("- ") and "agent" in s.lower() and "LANDED" not in s and "ADOPTED" not in s:
                live.append(s[:90])
        if live and age > 2:
            print("%s: %d live-looking fences in a %.1f-day-old file:" % (p, len(live), age))
            for l in live:
                print("   " + l)
        else:
            print("%s: clean (%d live-looking fences, %.1fd old)" % (p, len(live), age))


def cmd_fence_lint(argv):
    """PreToolUse dispatch aid: show live fences near cwd so no writer launches
    into an occupied file set. Cheap, read-only, exit 0 always. Reads the hook
    payload from stdin when no path argument is given."""
    cwd = argv[0] if argv else ""
    if not cwd and not sys.stdin.isatty():
        try:
            cwd = (json.load(sys.stdin) or {}).get("cwd", "")
        except Exception:
            cwd = ""
    cwd = cwd or os.getcwd()
    hits = []
    # The project's own STATE.md plus any registries the user declared via
    # BROTHERSBE_REGISTRIES (colon-separated glob patterns).
    pats = [os.path.join(cwd, "STATE.md")]
    pats += [p.strip() for p in os.environ.get("BROTHERSBE_REGISTRIES", "").split(":") if p.strip()]
    for pat in pats:
        for p in glob.glob(pat, recursive=True):
            for line in open(p, errors="replace"):
                s = line.strip()
                if s.startswith("- ") and "agent" in s.lower() and "LANDED" not in s and "ADOPTED" not in s:
                    tier = "" if re.search(r"\btier T[123]\b", s) else " [NO-TIER: declare T1/T2/T3]"
                    hits.append("%s: %s%s" % (os.path.basename(p), s[:100], tier))
    if hits:
        print("LIVE FENCES (fence-then-dispatch; overlap means queue):")
        for h in hits[:8]:
            print("  " + h)
    else:
        print("fence-lint: no live fences found under %s" % cwd)


# ---------------------------------------------------------------------------
# Update awareness. This skill is a LAW: when it changes, the change has to be
# read, not silently absorbed. So the notifier does two jobs: tell you an update
# exists, and tell you once when your installed law actually changed.
#
# HARD CONSTRAINT: no network call and no subprocess, ever. Both properties are
# audited and are claimed publicly in SECURITY.md. So this reads git refs as
# ordinary files and never runs git itself. The cost is that "an update exists"
# is only known after something else has fetched; the staleness warning covers
# the rest, by telling you when your copy is simply old.
# ---------------------------------------------------------------------------
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STALE_AFTER_DAYS = 30
VERSION_MARK = os.path.join(TEL_DIR, "installed-skill-version")


def _read_first_line(path):
    try:
        with open(path, "r", errors="replace") as f:
            return f.readline().strip()
    except OSError:
        return ""


def _git_ref(git_dir, ref):
    """Resolve a ref to a sha by reading files only: loose ref first, then
    packed-refs. Returns "" when the ref cannot be resolved."""
    sha = _read_first_line(os.path.join(git_dir, ref))
    if sha and not sha.startswith("ref:"):
        return sha
    packed = os.path.join(git_dir, "packed-refs")
    try:
        for line in open(packed, "r", errors="replace"):
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            if len(parts) == 2 and parts[1] == ref:
                return parts[0]
    except OSError:  # sbe: allow-silent optional filesystem read; absence handled by the caller
        pass
    return ""


def cmd_check_update():
    git_dir = os.path.join(SKILL_DIR, ".git")
    if not os.path.isdir(git_dir):
        return                      # not a git install; nothing to compare
    head = _read_first_line(os.path.join(git_dir, "HEAD"))
    branch = head[5:].strip() if head.startswith("ref:") else ""
    local = _git_ref(git_dir, branch) if branch else head
    if not local:
        return
    remote = ""
    if branch.startswith("refs/heads/"):
        name = branch[len("refs/heads/"):]
        remote = _git_ref(git_dir, "refs/remotes/origin/" + name)

    # (a) an update is already fetched and waiting
    if remote and remote != local:
        # Direction is not knowable without reading git objects, so the message
        # and the command are both symmetric: left-right marks which side each
        # commit is on, and works whether you are behind, ahead, or diverged.
        print("BROTHERSBE UPDATE: installed copy (%s) and fetched origin (%s) "
              "differ. See which side each commit is on, then update:"
              % (local[:7], remote[:7]))
        print("  git -C %s log --oneline --left-right %s...%s"
              % (SKILL_DIR, local[:7], remote[:7]))
        print("  git -C %s pull    # then re-read the sections that changed" % SKILL_DIR)
    else:
        # (b) no fetched update, but the copy may simply be old
        try:
            age = (datetime.datetime.now().timestamp()
                   - os.path.getmtime(os.path.join(SKILL_DIR, "SKILL.md"))) / 86400
        except OSError:
            age = 0
        if age > STALE_AFTER_DAYS:
            print("BROTHERSBE UPDATE: your copy of the law is %d days old. Check "
                  "for updates: git -C %s pull" % (age, SKILL_DIR))

    # (c) the law changed under you since the last session that looked: say so
    # ONCE, because a changed law must be read, not silently inherited.
    known = _read_first_line(VERSION_MARK)
    if known and known != local:
        print("BROTHERSBE: the skill changed since your last session (%s -> %s). "
              "Read the diff before relying on it:" % (known[:7], local[:7]))
        print("  git -C %s log --oneline %s..%s" % (SKILL_DIR, known[:7], local[:7]))
    if known != local:
        try:
            os.makedirs(TEL_DIR, exist_ok=True)
            with open(VERSION_MARK, "w") as f:
                f.write(local + "\n")
        except OSError:  # sbe: allow-silent boundary handler in a non-blocking hook; the miss surfaces as absent data, never as a false pass
            pass


def _intent_path(cwd):
    return os.path.join(TEL_DIR, "intent-%s.log" % _project_of(cwd))


def cmd_intent(argv):
    """Append one write-ahead intent line. Called by the session BEFORE a risky or
    long action so that if the session dies mid-action, the intent is already on
    disk. Pure: appends to a file, nothing else."""
    text = " ".join(argv).strip()
    if not text:
        print("usage: intent \"next: <what>, because <why>\"")
        return
    atomic_append_text(_intent_path(os.getcwd()), now_iso() + "  " + text)
    print("intent logged")


def atomic_append_text(path, line):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = (line.rstrip("\n") + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def _last_intent(cwd):
    try:
        lines = [l.rstrip("\n") for l in open(_intent_path(cwd), errors="replace") if l.strip()]
        return lines[-1] if lines else ""
    except OSError:
        return ""


def _project_of(cwd):
    # basename ALONE collides across ~/client-a/backend and ~/client-b/backend, which
    # would let one project's resume/intent files be read as another's. Suffix a short
    # hash of the absolute path so the identity is unique per repository root.
    base = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(cwd.rstrip("/"))) or "session"
    h = hashlib.sha1(os.path.abspath(cwd).encode("utf-8", "replace")).hexdigest()[:6]
    return "%s-%s" % (base, h)


def _resume_path(cwd):
    return os.path.join(TEL_DIR, "last-resume-%s.md" % _project_of(cwd))


def cmd_precompact_brief():
    """Distill the dying session into a forward-looking resume brief. The git
    autosave preserves WHAT you had (files); this preserves WHERE you were and
    WHY, which is the part a resumed model would otherwise have to re-derive.
    Mechanical extraction, not synthesis: it hands the next session the raw recent
    history so the model reconstructs the thread from complete material instead of
    a stale note. Pure python: reads the transcript file, writes one markdown file;
    no subprocess, no network."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    tp = payload.get("transcript_path") or ""
    cwd = payload.get("cwd") or os.getcwd()
    if not tp or not os.path.isfile(tp):
        return
    last_user = ""
    assistant_text = []   # recent reasoning/decision snippets
    tools = []            # recent tool actions, as short descriptors
    try:
        f = open(tp, "r", errors="replace")
    except OSError:
        return
    with f:
        for raw in f:
            try:
                o = json.loads(raw)
            except Exception:
                continue
            t = o.get("type")
            m = o.get("message") or {}
            if t == "user" and not o.get("isMeta"):
                c = m.get("content")
                txt = c if isinstance(c, str) else None
                if isinstance(c, list):
                    if not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                        txt = "\n".join(b.get("text", "") for b in c
                                        if isinstance(b, dict) and b.get("type") == "text")
                if txt and txt.strip() and "<system-reminder>" not in txt:
                    last_user = txt.strip()
            elif t == "assistant":
                for b in (m.get("content") or []):
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text" and b.get("text", "").strip():
                        assistant_text.append(b["text"].strip())
                    elif b.get("type") == "tool_use":
                        name = b.get("name", "")
                        inp = b.get("input") or {}
                        if name == "Bash":
                            desc = "Bash: " + (inp.get("command", "")[:100])
                        elif name in ("Edit", "Write", "Read"):
                            desc = name + ": " + str(inp.get("file_path", ""))
                        else:
                            desc = name
                        tools.append(desc)
    # Keep only the recent tail of each stream, and REDACT every stream: this file
    # holds your own recent words and commands, which can carry a pasted secret, a
    # token in a command, or a customer name. Same discipline as corrections.jsonl;
    # the earlier fix there had to be applied here too (a fix in one place must be
    # grepped for everywhere with the same shape).
    assistant_text = [redact(a)[0] for a in assistant_text[-4:]]
    tools = [redact(d)[0] for d in tools[-10:]]
    last_user = redact(last_user)[0]
    last_intent = redact(_last_intent(cwd))[0]
    lines = ["# Resume brief (auto-written before compaction)",
             "",
             "A compaction just erased the working context. The git autosave holds your",
             "files (refs/brothersbe/autosave); this holds the THREAD. Read it, re-read",
             "STATE.md, then continue where this leaves off.",
             "",
             "## Next intent (write-ahead: what this session was about to do)",
             (last_intent or "(no write-ahead intent was logged)"),
             "",
             "## The last thing the operator asked",
             (last_user[:600] or "(none captured)"),
             "",
             "## What was being done (recent reasoning)"]
    for a in assistant_text:
        lines.append("- " + a[:300].replace("\n", " "))
    lines.append("")
    lines.append("## Recent actions (last %d)" % len(tools))
    for d in tools:
        lines.append("- " + d)
    lines.append("")
    # Owner-only: this is sensitive recent context, like corrections.jsonl.
    try:
        os.makedirs(TEL_DIR, exist_ok=True)
        rp = _resume_path(cwd)
        fd = os.open(rp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, ("\n".join(lines) + "\n").encode())
        finally:
            os.close(fd)
    except OSError:  # sbe: allow-silent boundary handler in a non-blocking hook; the miss surfaces as absent data, never as a false pass
        pass


def cmd_compact_hint():
    """Read the SessionStart hook payload from stdin. When the session resumed
    from a context compaction (source == "compact"), the model has just lost the
    detail of what it was doing, so point it at the autosave and at STATE.md. This
    is the READ side of work-preservation; sbe_autosave.sh is the write side. Pure
    by design: this never runs git (that would break the audited no-subprocess
    property); it only prints the recovery command for the model or human to run."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if (payload or {}).get("source") != "compact":
        return
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print("BROTHERSBE: resumed after a compaction. Your files are autosaved "
          "(sh %s/tools/sbe_autosave.sh recover) and the thread is below. Read it, "
          "re-read STATE.md and git status, then continue." % skill_dir)
    # The thread: the resume brief written at the moment of death (the WHY/where),
    # which the git snapshot does not carry.
    rp = _resume_path((payload or {}).get("cwd") or os.getcwd())
    try:
        with open(rp, "r", errors="replace") as f:
            print("")
            print(f.read().strip())
    except OSError:  # sbe: allow-silent boundary handler in a non-blocking hook; the miss surfaces as absent data, never as a false pass
        pass


def _read_head(path, limit_chars=6000):
    try:
        return open(path, errors="replace").read()[:limit_chars]
    except OSError:
        return ""


def cmd_handoff(argv):
    """Assemble a single shareable markdown for the solo operator's occasional
    hand-off to a small teammate. It is teammate-facing, so EVERY section is run
    through redact() before it is written: a handoff is exactly where a stray
    secret would travel furthest. Pure python (reads vault files, writes one file);
    no subprocess, no network, preserving the audited properties."""
    projects_dir = os.path.join(VAULT, "10-Projects")
    name = argv[0] if argv else ""
    if not name:
        try:
            avail = sorted(d for d in os.listdir(projects_dir)
                           if os.path.isdir(os.path.join(projects_dir, d)))
        except OSError:
            avail = []
        print("usage: handoff <project>. available: %s" % (", ".join(avail) or "(none)"))
        return
    base = os.path.join(projects_dir, name)
    if not os.path.isdir(base):
        print("handoff: no vault project named %r under %s" % (name, projects_dir))
        return
    parts = ["# Handoff: %s" % name, "",
             "A shareable summary of this project for a teammate. Assembled from the",
             "vault and secret-redacted. It is a snapshot, not the living record.", ""]
    overview = _read_head(os.path.join(base, "Overview.md"))
    if overview:
        parts += ["## Overview", redact(overview)[0], ""]
    openitems = _read_head(os.path.join(base, "Open-Items.md"))
    if openitems:
        parts += ["## Open items", redact(openitems)[0], ""]
    # latest session log by mtime
    sessions = glob.glob(os.path.join(base, "Sessions", "*.md"))
    if sessions:
        latest = max(sessions, key=lambda f: os.path.getmtime(f))
        parts += ["## Most recent session (%s)" % os.path.basename(latest),
                  redact(_read_head(latest, 4000))[0], ""]
    # last few outcome lines
    oc = _read_head(os.path.join(base, "OUTCOMES.md"), 20000)
    if oc:
        tail = [l for l in oc.splitlines() if l.strip()][-6:]
        parts += ["## Recent outcomes", redact("\n".join(tail))[0], ""]
    out = os.path.join(os.getcwd(), "handoff-%s.md" % re.sub(r"[^A-Za-z0-9_.-]", "_", name))
    try:
        with open(out, "w") as f:
            f.write("\n".join(parts) + "\n")
        print("handoff written (secret-redacted): %s" % out)
        print("review it before sharing; it is a snapshot, redaction is best-effort.")
    except OSError as e:
        print("handoff: could not write (%r)" % (e,))


def cmd_purge_corrections(argv):
    """Delete captured correction candidates. They are excerpts of your own
    messages; purge them once the weekly review has distilled what it needs, or
    at any time. Prints exactly what it will remove before removing it."""
    rows = read_jsonl(CORRECTIONS)
    if not rows:
        print("purge-corrections: nothing to purge (%s)" % CORRECTIONS)
        return
    if "--yes" not in argv:
        print("purge-corrections: %d candidate(s) in %s" % (len(rows), CORRECTIONS))
        print("  oldest: %s   newest: %s" % (rows[0].get("ts", "?"), rows[-1].get("ts", "?")))
        print("  re-run with --yes to delete the file.")
        return
    try:
        os.remove(CORRECTIONS)
        print("purge-corrections: removed %d candidate(s) from %s" % (len(rows), CORRECTIONS))
    except OSError as e:
        print("purge-corrections: could not remove (%r)" % (e,))


def cmd_prediction_audit():
    c = prediction_counts()
    print("prediction ledger: %d sealed, %d scored, %d hits (%s)"
          % (c["sealed"], c["scored"], c["hits"], OPERATOR_MODEL))
    if c["sealed"] == 0:
        print("AUDIT FLAG: zero sealed predictions; section 14 requires sealing BEFORE recommendations.")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    argv = sys.argv[2:]
    try:
        if cmd == "outcomes-append":
            cmd_outcomes_append()
        elif cmd == "migrate":
            cmd_migrate()
        elif cmd == "scorecard":
            cmd_scorecard()
        elif cmd == "rate":
            cmd_rate(argv)
        elif cmd == "review-mark":
            cmd_review_mark(argv)
        elif cmd == "startup-nags":
            cmd_startup_nags()
        elif cmd == "stop-warn":
            cmd_stop_warn()
        elif cmd == "registry-check":
            cmd_registry_check(argv)
        elif cmd == "fence-lint":
            cmd_fence_lint(argv)
        elif cmd == "intent":
            cmd_intent(argv)
        elif cmd == "precompact-brief":
            cmd_precompact_brief()
        elif cmd == "compact-hint":
            cmd_compact_hint()
        elif cmd == "check-update":
            cmd_check_update()
        elif cmd == "handoff":
            cmd_handoff(argv)
        elif cmd == "purge-corrections":
            cmd_purge_corrections(argv)
        elif cmd == "prediction-audit":
            cmd_prediction_audit()
        elif cmd == "speed":
            cmd_speed()
        elif cmd == "dedup":
            cmd_dedup()
        else:
            print(__doc__.strip())
    except Exception as e:
        print("sbe_telemetry: swallowed error (never blocks): %r" % (e,))
    sys.exit(0)


if __name__ == "__main__":
    main()
