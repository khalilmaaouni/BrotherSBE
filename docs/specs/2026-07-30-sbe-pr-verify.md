# sbe pr verify: live GitHub evidence, bound to the head commit

Status: spec of record for Loop 3 of the First-Rank Essentials program
(Release B, capability 3). The fixtures in tools/test_sbe_prverify.py and the
implementation in src/brothersbe/prverify.py both read from here.

## Command

    bin/sbe pr verify <pr-number> --repo <owner/name> [--json] [--cwd <repo>]
    (registered as subcommand "pr", first positional "verify", so later pr
    surfaces have a home)

## Machine facts this design is built on, verified 2026-07-30

gh 2.96.0 is installed on the reference machine but holds NO token, and git
on this machine has no credential helper at all. Therefore the UNAUTHENTICATED
and UNVERIFIABLE paths are the mainline paths, not edge cases: every fixture
suite must pass with zero network and zero credentials, and the live path is
an opt-in integration test.

## Token discovery, in order, first hit wins

1. GITHUB_TOKEN environment variable
2. GH_TOKEN environment variable
3. gh auth token (subprocess, may fail; a failure is not an error, it is
   absence)

No token found: every network-dependent control reports NO-DATA with the
one-line remedy (export GITHUB_TOKEN or gh auth login), the FINAL verdict is
NO-DATA, and the exit is nonzero. Missing credentials never print PASS and
never print FAIL: absence of evidence is not evidence of absence.

The token is never persisted, never printed, never written into a receipt or
a report; the report records only which discovery source supplied it, by name.

## Transport

Python 3.9 stdlib only: urllib.request against https://api.github.com, with
Authorization: Bearer only in memory, a hard timeout, and an Accept pin to
application/vnd.github+json. Every HTTP failure maps to a verdict, never a
traceback: 401/403 with a token is UNVERIFIABLE (insufficient permission,
named per control), 404 is FAIL for "PR exists" and UNVERIFIABLE downstream,
network unreachable is NO-DATA naming the network.

For fixtures: the client takes an injectable fetch function; tests inject
canned JSON responses and never open a socket. The real fetch is the only
code path that touches the network, and it is small enough to read.

## Controls, each with its own verdict line

    PR EXISTS             open PR resolves for owner/name + number
    PR HEAD               assessed commit equals the PR head sha (the head
                          sha is printed; --head <sha> may pin an expected
                          one, else the local HEAD when --cwd names a repo
                          containing it, else the control is NO-DATA prose)
    AUTHOR KNOWN          author login resolves and is not a ghost/deleted
    INDEPENDENT APPROVAL  at least one APPROVED review, in the latest-per-
                          reviewer state, whose author differs from the PR
                          author (dot-insensitive only where the host is
                          known to be dot-insensitive; logins compare exact),
                          submitted at or after the head commit's push (an
                          approval predating the current head is stale, FAIL
                          naming both timestamps), and not dismissed
    BOT APPROVAL          when the only approvals are from accounts of type
                          Bot, the control FAILs when policy requires a human
                          (policy default: human required)
    REVIEW THREADS        no review with state CHANGES_REQUESTED remains
                          latest-per-reviewer and undismissed
    CODEOWNERS            when the repository exposes required reviewers via
                          the API and a CODEOWNERS rule applies: PASS/FAIL;
                          no applicable rule found: NO-DATA, never PASS
    REQUIRED CHECKS       every required status check on the head sha
                          succeeded; required set unavailable to this token:
                          UNVERIFIABLE, never inferred from local files
    EVIDENCE FRESHNESS    when a local evidence store exists (--cwd): every
                          receipt marked as covering this change binds to the
                          head sha; a receipt bound to another commit is FAIL
                          naming both; no store or no receipts: NO-DATA
    FINAL                 FAIL if any control FAILed; else UNVERIFIABLE if
                          any control was UNVERIFIABLE; else NO-DATA if any
                          network control was NO-DATA; else PASS

UNVERIFIABLE is a fourth report-level verdict for this command only (the
check-registry law of three is untouched: these controls live in
src/brothersbe, not in a Check registry; the report states this taxonomy in
its own header). Exit 0 only when FINAL is PASS.

Every report is bound in its header to repository, PR number, and head sha,
and states its wall-clock; approval is never cached: every run re-fetches.

## Security rules (each one a fixture)

- Read-only: the client sends GET only; a non-GET anywhere is a defect.
- No token in argv, report, receipt, log, or exception text (the redaction
  helper in src/brothersbe/evidence.py redact_argv is the house pattern).
- Branch protection is never inferred from local files.
- A later commit invalidates: the head sha is fetched last and compared to
  the sha each control was evaluated against; a race is UNVERIFIABLE with
  "re-run" prose, never a silent pass.

## Essential fixtures (tools/test_sbe_prverify.py, canned responses)

stale approval after a new commit; self-approval (author == approver);
unresolved CHANGES_REQUESTED; dismissed review not counted either way;
missing CODEOWNERS rule is NO-DATA; failed required check; force-pushed head
mid-evaluation is UNVERIFIABLE; 403 with token is UNVERIFIABLE per control;
no token at all is NO-DATA with remedy and nonzero exit; bot-only approval
FAILs under default policy; token never appears in any output byte (assert
over the whole report with a canary token value).

## Opt-in live test

tools/test_sbe_prverify_live.py runs ONLY when SBE_LIVE_GH_REPO (owner/name)
and a discoverable token exist; otherwise it prints one NO-DATA line and
exits 0 as a skip that says what it did not do. It never mutates the remote.
