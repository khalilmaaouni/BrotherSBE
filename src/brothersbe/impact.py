"""Derive what a change actually touches from its diff, and reconcile that with
what the human said at intake.

The defect this exists for, in one sentence: the tier is computed from five
answers and nothing has ever read the code, so a change that rewrites an API
contract can be classified T0 by answering "no" five times, and every gate
downstream then agrees that this change owes no evidence.

THE ONE RULE THAT MAKES THIS SAFE: this module does not implement a second tier
ladder. It converts detector hits into the SAME five intake answers the human
gives, and hands them to `sbe_intake.compute_tier`. One rule, one table, two
inputs. A tier computed here and a tier computed from a person's answers cannot
drift apart, because there is only one place where a tier is decided.

THE PROPOSED TIER IS A FLOOR, NEVER A CEILING. Two of the five intake answers
cannot be derived from a diff at all:

  - `consumers`: how many downstream things break if this is wrong. Nothing in a
    diff knows that without an ownership map the repository does not have. It is
    assumed "none", which is the value that can only make the proposal LOWER,
    and it is reported under `unmeasured` rather than quietly assumed.
  - `crosses_boundary` is inferred only where the diff shows infrastructure,
    deployment or event-contract files. A service call added inside existing code
    is not visible to a path-based detector.

So: this tool may say a change is bigger than the human claimed. It may never
say a change is smaller, and a PASS from it means "nothing in the diff
contradicts the declared tier", which is a much narrower statement than "the
declared tier is right".
"""
import io
import json
import os
import re
import subprocess
import sys

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools")
sys.path.insert(0, os.path.abspath(TOOLS))
from sbe_intake import compute_tier, UnreadableIntake  # noqa: E402

#: Detectors. Each is (id, why it matters, the intake answer it sets, path
#: pattern, optional content pattern). Path patterns are matched against the
#: forward-slash path, case-folded. Content patterns, where present, are matched
#: against the ADDED lines of the diff only, so deleting a line that mentions a
#: payment does not classify a change as touching money.
#:
#: `sets` is the intake answer this hit forces. Only these three are derivable:
#:   sensitive     -> touches_sensitive = True        (drives T3)
#:   irreversible  -> reversible_under_hour = False   (drives T3)
#:   contract      -> changes_contract = True         (drives T2)
#:   boundary      -> crosses_boundary = True         (drives T1)
DETECTORS = [
    ("openapi", "an HTTP API contract others build against", "contract",
     r"(openapi|swagger)[^/]*\.(ya?ml|json)$", None),
    ("asyncapi", "an asynchronous API contract", "contract",
     r"asyncapi[^/]*\.(ya?ml|json)$", None),
    ("protobuf", "a wire format shared across services", "contract", r"\.proto$", None),
    ("avro", "a serialization schema consumers decode with", "contract", r"\.avsc$", None),
    ("graphql", "a published query surface", "contract", r"\.(graphql|gql)$", None),
    ("event-schema", "an event contract consumers subscribe to", "contract",
     r"(^|/)(events?|schemas?)/.*\.(json|ya?ml|avsc)$", None),
    ("db-migration", "a schema change other code and queries depend on", "contract",
     r"(^|/)(migrations?|alembic|flyway|liquibase|db/migrate)/", None),
    ("sql-ddl", "data definition language, which changes a shared shape", "contract",
     r"\.sql$", r"\b(create|alter|drop)\s+(table|view|schema|index|type)\b"),
    ("dbt-model", "a warehouse model other models and reports select from", "contract",
     r"(^|/)models/.*\.(sql|ya?ml)$", None),
    ("orm-model", "the code definition of a persisted shape", "contract",
     r"(^|/)(models?|entities|schema)\.(py|rb|ts|js|go|java|kt)$", None),

    ("destructive-migration", "drops or truncates, which is not reversible in an hour",
     "irreversible", r"\.(sql|py|rb)$",
     r"\b(drop\s+(table|column|schema)|truncate\s+table|delete\s+from\s+\w+\s*;)"),

    ("payment-path", "money movement", "sensitive",
     r"(payment|billing|invoice|refund|settlement|payout|charge|pricing|rebate|discount)", None),
    ("partner-path", "a partner-facing surface", "sensitive",
     r"(partner|vendor|supplier|merchant)s?[_/-]", None),
    ("pii-path", "personal data", "sensitive",
     r"(^|/)[^/]*(pii|gdpr|personal[_-]?data|customer[_-]?data)[^/]*", None),
    ("pii-field", "a personal data field added in code or schema", "sensitive", r"\.(sql|py|rb|ts|js|go|java|kt|ya?ml|json)$",
     r"\b(ssn|social_security|passport_no|national_id|date_of_birth|dob|home_address|"
     r"phone_number|email_address|credit_card|card_number|iban|bank_account)\b"),
    ("auth-path", "who may reach what", "sensitive",
     r"(^|/)[^/]*(auth|authz|authentication|authorization|permission|rbac|oauth|session)[^/]*"
     r"\.(py|rb|ts|js|go|java|kt)$", None),
    ("production-config", "production state", "sensitive",
     r"(^|/)(prod|production)[^/]*/|\.(tfvars)$|(^|/)(terraform|k8s|kubernetes|helm|deploy"
     r"|deployment)s?/", None),
    ("secret-material", "credentials or key material", "sensitive",
     r"(^|/)[^/]*(secret|credential|keystore|\.pem|\.p12)[^/]*", None),

    ("infrastructure", "infrastructure that other systems run on", "boundary",
     r"\.(tf|tfvars)$|(^|/)(k8s|kubernetes|helm|charts?)/|(^|/)docker-compose[^/]*\.ya?ml$",
     None),
    ("ci-pipeline", "the pipeline other engineers' merges run through", "boundary",
     r"(^|/)\.github/workflows/|(^|/)\.gitlab-ci\.ya?ml$|(^|/)Jenkinsfile$", None),
    ("queue-config", "an asynchronous boundary between systems", "boundary",
     r"(kafka|rabbitmq|sqs|pubsub|kinesis)", None),
]

#: Extensions this tool has no detector for and does not pretend to read. Files
#: whose extension is not in the union of what the detectors match land in
#: `unmeasured`, because "no detector fired" and "nothing to detect" are
#: different sentences and only one of them is honest about coverage.
QUIET_EXTENSIONS = (".md", ".txt", ".rst", ".adoc", ".gitignore", ".editorconfig",
                    ".license", ".cfg", ".ini", ".toml", ".lock")


class DiffUnavailable(Exception):
    """The diff could not be resolved, so nothing was inspected.

    Raised rather than returning an empty change set, because an empty change
    set and an unreadable one produce the same JSON and only one of them means
    the change is small.
    """


def _git(args, cwd):
    out = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True)
    return out.returncode, out.stdout, out.stderr


def resolve_range(cwd, base=None, head="HEAD"):
    """(base, head) or raise. Never guesses silently.

    Order: an explicit base wins. Otherwise the merge base with the default
    branch, tried in the order a repository is likely to name it. Otherwise the
    parent commit. A repository with a single commit and no explicit base has no
    range at all, and that is reported rather than turned into "everything".
    """
    code, _out, err = _git(["rev-parse", "--is-inside-work-tree"], cwd)
    if code != 0:
        raise DiffUnavailable("not a git repository: %s" % err.strip())
    if base:
        code, _o, err = _git(["rev-parse", "--verify", base], cwd)
        if code != 0:
            raise DiffUnavailable("base %r does not resolve in this repository" % base)
        return base, head
    for candidate in ("origin/HEAD", "origin/main", "main", "origin/master", "master"):
        code, out, _e = _git(["merge-base", candidate, head], cwd)
        if code == 0 and out.strip():
            return out.strip(), head
    code, out, _e = _git(["rev-parse", "%s^" % head], cwd)
    if code == 0 and out.strip():
        return out.strip(), head
    raise DiffUnavailable(
        "no diff range: no default branch to merge-base against and %s has no parent. "
        "Pass --base explicitly. Nothing was inspected." % head)


def changed_files(cwd, base, head):
    code, out, err = _git(["diff", "--name-only", "%s..%s" % (base, head)], cwd)
    if code != 0:
        raise DiffUnavailable("git diff failed: %s" % err.strip())
    return [f for f in out.split("\n") if f.strip()]


def added_lines(cwd, base, head, path):
    """Only the ADDED lines for one file. Deleting a line that mentions a
    payment is not a change that touches money, and a content detector reading
    the whole diff would classify it as one."""
    code, out, _err = _git(["diff", "-U0", "%s..%s" % (base, head), "--", path], cwd)
    if code != 0:
        return ""
    return "\n".join(l[1:] for l in out.split("\n")
                     if l.startswith("+") and not l.startswith("+++"))


def detect(cwd, base, head, files=None):
    """(hits, unmeasured). One hit per (detector, file) pair, each naming why."""
    files = changed_files(cwd, base, head) if files is None else files
    hits, unmeasured = [], []
    for path in files:
        low = path.lower()
        matched_any = False
        for det_id, why, sets, path_pat, content_pat in DETECTORS:
            if not re.search(path_pat, low):
                continue
            if content_pat:
                body = added_lines(cwd, base, head, path).lower()
                if not re.search(content_pat, body):
                    continue
            matched_any = True
            hits.append({"detector": det_id, "file": path, "why": why, "sets": sets})
        if not matched_any:
            ext = os.path.splitext(low)[1]
            if ext not in QUIET_EXTENSIONS:
                unmeasured.append({"file": path,
                                   "reason": "no detector covers %s files; this tool did not "
                                             "read it and is not reporting it as clean"
                                             % (ext or "extensionless")})
    return hits, unmeasured


def answers_from_hits(hits):
    """The five intake answers, as the diff supports them.

    Two are floors rather than measurements, and say so in `unmeasured` upstream:
    `consumers` is assumed "none" and `crosses_boundary` is only ever inferred
    from infrastructure-shaped files. Both assumptions can only LOWER the
    proposed tier, which is the safe direction for a tool whose whole promise is
    that it never silently lowers anything.
    """
    sets = set(h["sets"] for h in hits)
    return {
        "changes_contract": "y" if "contract" in sets else "n",
        "crosses_boundary": "y" if "boundary" in sets else "n",
        "reversible_under_hour": "n" if "irreversible" in sets else "y",
        "touches_sensitive": "y" if "sensitive" in sets else "n",
        "consumers": "none",
    }


def read_intake(path):
    """(tier, answers, problem). A malformed intake is a problem, never a zero."""
    if not path or not os.path.exists(path):
        return None, None, "no intake file at %s" % path
    try:
        with io.open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as exc:
        return None, None, "intake at %s does not parse: %s" % (path, exc)
    answers = data.get("answers", data)
    try:
        return compute_tier(answers), answers, None
    except UnreadableIntake as exc:
        return None, answers, "intake at %s cannot be read: %s" % (path, exc)


def _tier_index(tier):
    return ("T0", "T1", "T2", "T3").index(tier)


def read_disposition(path, head_sha):
    """A recorded human decision about a disagreement, bound to a commit.

    Bound on purpose: a disposition written against an earlier head says nothing
    about what the diff contains now. A stale one is reported as stale and does
    NOT resolve anything, which is the same rule the evidence work applies to
    every other receipt.
    """
    if not path or not os.path.exists(path):
        return [], None
    try:
        with io.open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as exc:
        return [], "disposition at %s does not parse: %s" % (path, exc)
    records = data if isinstance(data, list) else data.get("dispositions", [])
    live, stale = [], 0
    for rec in records:
        required = ("detector", "decision", "reason", "who", "head")
        if any(not str(rec.get(k, "")).strip() for k in required):
            continue
        if rec.get("head") != head_sha:
            stale += 1
            continue
        live.append(rec)
    note = None
    if stale:
        note = ("%d disposition(s) were written against a different head commit and resolve "
                "nothing; a decision about an older diff is not a decision about this one"
                % stale)
    return live, note


def report(cwd, base=None, head="HEAD", intake_path=None, disposition_path=None):
    """The whole verdict, as a dict ready to be written as impact-report.json."""
    base_sha, head_ref = resolve_range(cwd, base, head)
    code, head_sha, _e = _git(["rev-parse", head_ref], cwd)
    head_sha = head_sha.strip() if code == 0 else head_ref

    files = changed_files(cwd, base_sha, head_ref)
    hits, unmeasured = detect(cwd, base_sha, head_ref, files)
    derived = answers_from_hits(hits)
    proposed = compute_tier(derived)
    human_tier, _human_answers, intake_problem = read_intake(intake_path)
    dispositions, disposition_note = read_disposition(disposition_path, head_sha)

    unmeasured = list(unmeasured)
    unmeasured.append({"file": None,
                       "reason": "consumers: how many downstream things break if this is "
                                 "wrong cannot be read from a diff. Assumed 'none', which can "
                                 "only lower the proposal, never raise it."})
    if disposition_note:
        unmeasured.append({"file": None, "reason": disposition_note})

    disagreements = []
    if human_tier and _tier_index(proposed) > _tier_index(human_tier):
        covered = set(d["detector"] for d in dispositions)
        for hit in hits:
            if hit["sets"] in ("contract", "sensitive", "irreversible", "boundary"):
                disagreements.append({
                    "detector": hit["detector"],
                    "file": hit["file"],
                    "why": hit["why"],
                    "disposition": "recorded" if hit["detector"] in covered else "missing",
                })

    unresolved = [d for d in disagreements if d["disposition"] == "missing"]

    if intake_problem and not human_tier:
        verdict = "FAIL" if "does not parse" in intake_problem or "cannot be read" in \
            intake_problem else "NO-DATA"
    elif not files:
        verdict = "NO-DATA"
    elif unresolved:
        verdict = "REVIEW-REQUIRED"
    elif not hits and not [u for u in unmeasured if u["file"]]:
        verdict = "NO-DATA" if not files else "PASS"
    else:
        verdict = "PASS"

    return {
        "schemaVersion": "1.0",
        "scope": "git diff %s..%s over %d changed file(s)" % (base_sha[:12], head_ref,
                                                              len(files)),
        "baseCommit": base_sha,
        "headCommit": head_sha,
        "detected": hits,
        "derivedAnswers": derived,
        "proposedTier": proposed,
        "proposedTierIsA": "floor, never a ceiling: two of the five intake answers cannot be "
                           "derived from a diff and are assumed at their lowest value",
        "humanTier": human_tier,
        "intakeProblem": intake_problem,
        "disagreements": disagreements,
        "unmeasured": unmeasured,
        "verdict": verdict,
    }
