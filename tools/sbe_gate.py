#!/usr/bin/env python3
"""BrotherSBE hard gates: the four silent-failure classes made mechanical.

This is the teeth of the trust architecture. Each subcommand inspects a
deliverable directory (default: the current git worktree) for the receipts that
prove a check RAN, and reports PASS / FAIL / NO-DATA per the class. Two modes,
one truth:
  default   advisory. Prints the verdict, exits 0. A session gets told.
  --strict  enforcing. Exits nonzero on any FAIL. CI runs this. A merge gets stopped.

The classes (ratified 2026-07-24):
  numbers   Every figure that could reach a decision ships with a numbers-manifest
            whose second, independently-scripted derivation RE-RAN to zero drift
            against a PINNED snapshot (live-warehouse drift is expected; the gate
            fails loudly if no snapshot id is recorded, rather than silently).
            Pinned means a snapshot id that is an answer, independent means the
            second query differs by more than case and whitespace, and zero drift
            is a comparison of two NUMBERS. `snapshot_id: "TODO"` with both rerun
            values `"pending"` once produced "1 figure(s) each with a pinned,
            independently re-derived, zero-drift check" at exit 0.
  migration A forward and a reverse migration, both with a receipt showing they
            ran against a restored copy, the reverse receipt recording a rehearsal
            run id AS A NON-BLANK STRING, and row counts that were RECORDED and
            that match. Recorded, not merely keyed: two empty strings compare
            equal, so a gate whose only emptiness test was `is None` reported
            "1 row-count comparison(s) matched" about a pair of blanks.
            Two limits, stated because the evidence line used to overstate both:
            this gate does not resolve the rehearsal id against any job system,
            and a receipt with no row counts is NO-DATA rather than a pass,
            because the reverse restoring the rows is the half it cannot assert
            without them.
  approval  Money or partner-facing change carries a named human approval bound
            to something stronger than a typed name. Two paths, and they are NOT
            equally strong, so this says exactly what each one proves:
              Approved-by: with a signature THIS HOST verified (git %G? = G or U)
                proves a key holder signed the commit. The agent cannot produce
                this without the private key.
              Reviewed-in: <review id> proves only that a non-vacuous id was
                written into the commit message. This gate does not resolve it
                against any platform, so an agent can type one. It is a pointer
                for a human to follow, not a forgery-resistant control, and its
                verdict is NO-DATA for exactly the reason an unverifiable
                signature's is: the host cannot check either one, and two
                identical epistemic states get one verdict. Resolve it in CI (a
                job that queries your review platform for that id) if you need
                it to be a control. There is NO shape check on the id beyond
                refusing the vacuity tokens; "an id in the right shape" was a
                claim the regex \S+ never made.
            A bare typed name FAILS. A signature the host cannot check (git
            %G? = E, the normal result on a runner with no imported keys) is
            NO-DATA, never an approval: CI must import the signer's public keys,
            or the team standardises on the weaker keyless Reviewed-in: path
            knowing what it does and does not prove.
            SELF-APPROVAL FAILS. The Approved-by identity is compared against
            the commit's own author and committer (%an, %ae, %cn, %ce), because
            one person with one key authored, signed and approved a payout
            change and this gate printed its strongest sentence over it. A
            signature proves a key holder signed and cannot prove a second party
            looked, and a second party is the whole content of the word approval.
  ran       No SQL or pipeline change is done until its reconciliation query or
            test executed: a receipt with a nonzero-duration run and an exit code.

Honesty law inherited from the chassis: absent evidence is NO-DATA, never PASS.
Three states, not two, and the difference is load-bearing: a missing receipt is
NO-DATA (nothing was claimed), a receipt that exists but records zero items is
NO-DATA naming that fact (a claim of nothing is still nothing), and a receipt
that exists and cannot be parsed is a FAIL (a broken claim, not an absent one).
A gate that reported PASS over zero items would print evidence asserting work
that was never inspected, which is worse than having no gate at all.
Fabricated-receipt defense: presence is necessary but the gate also checks the
receipt is INTERNALLY CONSISTENT (a run id resolves to a nonzero duration and an
exit code, a manifest's second query differs textually from the first), because
the operating record proves pasted receipts get invented.
"""
import json, os, sys, re, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbe_checks import (Check, run_guarded, answered, answered_as, numeric, count,
                        derivation_fold, distinct, fold, Pruner, evidence_problem)

MANIFEST = "numbers-manifest.json"
MIGRATION_RECEIPT = "migration-receipt.json"
APPROVAL_FILE = "APPROVAL"
RAN_RECEIPT = "ran-receipt.json"


def load_receipt(path):
    """Parse a receipt into (object, error).

    error is non-empty when the file exists but is not a usable receipt, and the
    caller turns that into a FAIL: a receipt that cannot be read is a broken
    claim, not an absent one. Absence of the file is NO-DATA, decided elsewhere
    on purpose.

    Valid JSON of the wrong TYPE is a broken claim too, and it used to be the
    hole: `json.load` returned a list or a string happily, the gate called .get
    on it, the exception escaped to the top-level handler, every gate after it
    never ran, nothing printed a verdict for any of them, and advisory mode
    exited 0. A crash that deletes a gate is the absent-check defect wearing a
    traceback. The type is checked here, once, where the file is opened.

    ACCESS is checked BEFORE open(): a FIFO where a receipt was expected used to
    hang this tool forever in both modes, with no verdict line at all, which is
    worse than any crash because a crash at least prints a FAIL.
    """
    problem = evidence_problem(path)
    if problem:
        return None, problem
    try:
        with open(path) as f:
            obj = json.load(f)
    except (OSError, ValueError) as e:
        return None, "not readable as JSON (%s)" % type(e).__name__
    if not isinstance(obj, dict):
        return None, ("top-level JSON is %s, not an object; a receipt is a JSON object"
                      % type(obj).__name__)
    return obj, ""


def _items(d, key):
    """Return (items, note) for a receipt's item list.

    items is [] when the key is missing, is not a list, or is an empty list.
    note names the reason so the NO-DATA evidence can distinguish a genuinely
    empty receipt from a misspelled key, which otherwise look identical.
    """
    v = d.get(key)
    if isinstance(v, list) and v:
        return v, ""
    if v is None:
        other = ", ".join(sorted(k for k in d if k != key))
        return [], ("no '%s' list; top-level keys present: %s" % (key, other)
                    if other else "no '%s' key and nothing else in the file" % key)
    if not isinstance(v, list):
        return [], "'%s' is %s, not a list" % (key, type(v).__name__)
    return [], "'%s' is an empty list" % key


def find(root, name):
    """(receipt paths, a sentence naming any pruned tree that also holds one).

    The note is the second return value and every caller prints it, because a
    directory this walk refused to enter is a directory the verdict does not
    cover, and "no numbers-manifest found" over a tree that holds one is this
    project's headline defect class wearing the walker's clothes.
    """
    hits = []
    misplaced = []
    pruner = Pruner()
    # onerror: a directory this walk cannot enter must land in the note, not in
    # silence. os.walk swallows the OSError by default, so a chmod 000 directory
    # holding a receipt used to vanish from a sentence that read as complete.
    for dp, dns, fns in os.walk(root, onerror=pruner.onerror):
        # Match directory NAMES, not a substring of the path: `.git` as a
        # substring test also hid `.github/`, so the workflow that wires these
        # gates into CI was invisible to every one of them. And then not by name
        # at all: see sbe_checks.skip_reason.
        if name in dns:
            # A DIRECTORY wearing the receipt's name is not a receipt, and
            # consuming the name in silence printed "no <receipt> found" over a
            # tree holding something by that name.
            misplaced.append(os.path.join(dp, name))
        dns[:] = pruner(dp, dns)
        if name in fns:
            hits.append(os.path.join(dp, name))
    note = pruner.note(lambda f: f == name)
    if misplaced:
        note += ("; a DIRECTORY named %s sits at %s and was not read, because a receipt "
                 "is a file" % (name, ", ".join(misplaced[:2])))
    return hits, note


def _partial(nothing, checked, kind, unit):
    """Evidence for a run where some receipts held items and some declared none.

    Reporting PASS here was the headline fix surviving in a repository with more
    than one deliverable, which is the normal case: the note naming the empty
    receipt was computed, collected, and then discarded unless EVERY receipt was
    empty. One good manifest anywhere in the tree restored the old behaviour for
    all the rest. A verdict covers every receipt it walked or it names the ones
    it could not cover.
    """
    return ("NO-DATA", "%d %s verified, but %d %s present that declares none (%s); "
                       "the verdict cannot cover a receipt with nothing in it, so it says so "
                       "instead of passing over it"
            % (checked, unit, len(nothing), kind, "; ".join(nothing[:4])))


def git_trailers(root):
    """(commit body, signature state, the identities that WROTE the commit).

    The identities are the addition, and they are the whole of the self-approval
    fix. The gate read the trailer and the signature state and never asked who
    authored the commit, so one person with one key produced a commit they
    authored, signed and approved, and the gate printed the strongest sentence it
    owns over it. `%an %ae` is the author and `%cn %ce` the committer, which are
    the two identities git can prove wrote this commit on this host.
    """
    try:
        out = subprocess.run(["git", "-C", root, "log", "-1",
                              "--format=%B%n---%n%G?%n%an%n%ae%n%cn%n%ce"],
                             capture_output=True, text=True, timeout=10)
        body, _, tail = out.stdout.rpartition("\n---\n")
        parts = (tail.split("\n") + [""] * 5)[:5]
        sig = parts[0].strip()
        who, seen = [], set()
        for p in parts[1:]:
            p = p.strip()
            if p and p not in seen:
                seen.add(p)
                who.append(p)
        return body, sig, who
    except Exception:
        return "", "N", []


def _identity_tokens(text):
    """The comparable identities inside a name-and-email string.

    `Dana Author <dana@example.com>` is compared as two tokens, so a trailer that
    carries only the name still matches an author git records with both, and a
    trailer that carries only the address matches too. Case and whitespace are
    folded, because `DANA@example.com` is Dana.
    """
    out = set()
    for m in re.finditer(r"<([^>]+)>", text or ""):
        out.add(fold(m.group(1)))
    stripped = re.sub(r"<[^>]*>", " ", text or "")
    name = fold(stripped.strip(" \t,;"))
    if name:
        out.add(name)
    for m in re.finditer(r"[^\s<>,;]+@[^\s<>,;]+", text or ""):
        out.add(fold(m.group(0)))
    return {t for t in out if t}


def gate_numbers(root):
    manifests, pruned = find(root, MANIFEST)
    if not manifests:
        return "NO-DATA", ("no numbers-manifest found; if this change presents no decision figure "
                           "that is correct, else add one%s" % pruned)
    problems = []
    unreadable = []
    nothing = []
    checked = 0
    seen_figures = []
    snapshots = []
    for m in manifests:
        d, err = load_receipt(m)
        if d is None:
            unreadable.append("%s: %s" % (os.path.relpath(m, root), err))
            continue
        figs, note = _items(d, "figures")
        if not figs:
            nothing.append("%s: %s" % (os.path.relpath(m, root), note))
            continue
        for fig in figs:
            checked += 1
            # A figure listed twice was counted twice, so a manifest holding one
            # object duplicated reported "2 figure(s)". The count in the evidence
            # line is what a reader takes as the amount of work checked. The rule
            # is sbe_checks.distinct(), shared with the three sibling thresholds
            # that did not have it.
            seen_figures.append(fig)
            if not isinstance(fig, dict):
                problems.append("entry %d in %s is %s, not a figure object"
                                % (checked, os.path.relpath(m, root), type(fig).__name__))
                continue
            # Every field below goes through answered(), not through truthiness,
            # not through `is None`, and no longer through stated() either. A
            # manifest carrying "" in every field cleared this gate once and the
            # evidence line reported zero drift over two empty strings; the round
            # after that, a manifest carrying "TODO" and "pending" did the same
            # thing, because a placeholder is not blank. An empty value is an
            # absent value, and so is a value that names the absence of one.
            label = answered(fig.get("label")) or "figure %d" % checked
            if answered(fig.get("label")) is None:
                problems.append("%s in %s records no label (%r), so nothing in the report can say "
                                "which figure was checked"
                                % (label, os.path.relpath(m, root), fig.get("label")))
            if answered(fig.get("snapshot_id")) is None:
                problems.append("%s: no snapshot_id recorded (%r); a live warehouse drifts, so pin "
                                "the read. A placeholder is not a pin"
                                % (label, fig.get("snapshot_id")))
            else:
                snapshots.append(answered(fig.get("snapshot_id")))
            # REDUCED FIRST, then tested, and this order is the whole fix. The
            # previous order asked `answered()` about the raw text and folded it
            # afterwards, so a `second_derivation` of `"#"`, or of `"-- rerun on
            # 2026-07-26 by hand, same query"`, was an answer to `answered()`,
            # folded to the empty string, differed from every real query, and
            # bought "a second derivation whose text differs beyond case,
            # whitespace and comments". A derivation that computes nothing is not
            # a derivation, whichever side of the pair it sits on.
            q1 = answered_as(fig.get("query"), derivation_fold)
            q2 = answered_as(fig.get("second_derivation"), derivation_fold)
            if q1 is None:
                problems.append("%s: no query recorded that computes anything (%r); with comments, "
                                "case, whitespace and trailing punctuation removed there is nothing "
                                "left, so there is nothing for the second derivation to be "
                                "independent of" % (label, fig.get("query")))
            if q2 is None:
                problems.append("%s: no independent second derivation that computes anything (%r); "
                                "with comments, case, whitespace and trailing punctuation removed "
                                "there is nothing left, and a comment is not a derivation"
                                % (label, fig.get("second_derivation")))
            elif q1 is not None and q1 == q2:
                # Compared on `.strip()`ed text, so a second derivation that was
                # the first one lowercased, or reindented, was accepted as an
                # independent re-derivation. Two texts that differ only in case
                # or in whitespace are one text. And then two texts differing by
                # a trailing semicolon, or by `-- rerun 2026-07-25` on the end,
                # were also one text, and bought the strongest sentence this file
                # prints: a cosmetic edit is not a second derivation.
                problems.append("%s: the second derivation is the first one again (it differs only "
                                "in case, whitespace, comments or trailing punctuation, if at all), "
                                "so nothing independent re-derived this figure" % label)
            r = fig.get("rerun")
            if not isinstance(r, dict):
                problems.append("%s: rerun is %s, not an object recording the re-derivation"
                                % (label, type(r).__name__))
                continue
            primary, secondary = numeric(r.get("primary")), numeric(r.get("secondary"))
            if r.get("ran") is not True:
                # The boolean IS the claim, exactly as in gate_migration below.
                # The string "false" is truthy, and it satisfied this test while
                # asserting the opposite of what it says.
                problems.append("%s: second derivation not marked as re-run (recorded %r, and only "
                                "the value true is that claim)" % (label, r.get("ran")))
            elif primary is None or secondary is None:
                unread = ", ".join("%s=%r" % (k, r.get(k)) for k in ("primary", "secondary")
                                   if numeric(r.get(k)) is None)
                problems.append("%s: rerun marked ran but the value(s) needed to prove zero drift "
                                "were not recorded as numbers (%s). A figure is a number; two "
                                "placeholders compare equal and prove nothing, so this is a failure "
                                "and not a zero-drift pass" % (label, unread))
            elif primary != secondary:
                problems.append("%s: DRIFT primary=%s secondary=%s (zero drift required)" % (label, r["primary"], r["secondary"]))
    if unreadable:
        return "FAIL", ("manifest present but unparseable: %s; a receipt that cannot be read is a broken claim, not an absent one"
                        % ", ".join(unreadable))
    if problems:
        return "FAIL", "; ".join(problems[:6])
    if not checked:
        return "NO-DATA", ("manifest present but records no figures (%s); an empty manifest proves nothing, so it is NO-DATA, never a pass"
                           % "; ".join(nothing))
    if nothing:
        return _partial(nothing, checked, "manifest", "figure(s)")
    # The sentence says what the four tests prove and stops there. "Independently
    # re-derived" read as a claim about the METHOD, and the only thing examined is
    # that the two texts differ by more than formatting: an alias rename is a
    # textual difference and passes, and nothing here reads which tables the two
    # queries touch. Overclaiming in the PASS line is this project's own defect
    # class pointed at itself.
    unique, dupes = distinct(seen_figures)
    # One snapshot id reused across every figure is a true sentence that proves
    # nothing about several different reads, so the reuse is stated rather than
    # left for a reader to notice. It is disclosure, not a failure: reading five
    # figures out of one pinned snapshot is the ordinary honest thing.
    reused = len(snapshots) - len(set(snapshots))
    return "PASS", ("%d figure(s) each pinned to a snapshot, with a second derivation whose text "
                    "differs beyond case, whitespace and comments, re-run to zero drift%s%s%s"
                    % (len(unique),
                       "" if not dupes else
                       "; %d duplicate manifest entry/entries were counted once" % dupes,
                       "" if not reused else
                       "; %d figure(s) share a snapshot id already used by another figure (%d "
                       "distinct snapshot(s) in all), which pins them to one read rather than to "
                       "several" % (reused, len(set(snapshots))),
                       pruned))


def gate_migration(root):
    receipts, pruned = find(root, MIGRATION_RECEIPT)
    if not receipts:
        return "NO-DATA", ("no migration in this change, or no migration-receipt.json%s" % pruned)
    problems = []
    unreadable = []
    nothing = []
    checked = 0      # receipts that recorded both legs
    compared = 0     # row-count comparisons actually made
    for m in receipts:
        rel = os.path.relpath(m, root)
        d, err = load_receipt(m)
        if d is None:
            unreadable.append("%s: %s" % (rel, err))
            continue
        legs = {k: d.get(k) for k in ("forward", "reverse")}
        if all(v is None for v in legs.values()) and "row_counts" not in d:
            other = ", ".join(sorted(d)) or "nothing at all"
            nothing.append("%s: no forward and no reverse leg recorded; top-level keys present: %s"
                           % (rel, other))
            continue
        for direction in ("forward", "reverse"):
            leg = legs[direction]
            if not isinstance(leg, dict):
                problems.append("%s: %s leg is %s, not an object" % (rel, direction, type(leg).__name__))
                continue
            # The boolean IS the claim, so it has to be the boolean. A whitespace
            # string is truthy, and " " satisfied this test while asserting
            # nothing at all about a restored copy.
            if leg.get("ran_against_restore") is not True:
                problems.append("%s: %s is not marked as run against a restored copy (recorded %r, "
                                "and only the value true is that claim)"
                                % (direction, direction, leg.get("ran_against_restore")))
            if direction != "reverse":
                continue
            rid = leg.get("rehearsal_run_id")
            if answered(rid) is None:
                problems.append("reverse: no rehearsal_run_id recorded (%r). This gate checks the id "
                                "is present, is a string, is not blank and is not one of the tokens "
                                "this project refuses as a stated value; it cannot resolve it against "
                                "a job system" % (rid,))
            elif not isinstance(rid, str):
                problems.append("reverse: rehearsal_run_id is %s, not a run id string"
                                % type(rid).__name__)
        checked += 1
        # The row counts are the half that used to be asserted without being read.
        # A receipt with no row_counts had the comparison skipped and the PASS
        # evidence still said "with matching row counts": a sentence about work
        # nothing did. Absent counts are an absence (NO-DATA). Half a count is a
        # broken claim (FAIL), because recording `before` and not `after_reverse`
        # says a count was taken and then does not produce it.
        rc = d.get("row_counts")
        if rc is None:
            nothing.append("%s: both legs recorded but no row_counts, so nothing compared the rows "
                           "the reverse was supposed to restore" % rel)
        elif not isinstance(rc, dict):
            problems.append("%s: row_counts is %s, not an object" % (rel, type(rc).__name__))
        elif count(rc.get("before")) is None or count(rc.get("after_reverse")) is None:
            # `is None` was the whole emptiness test here, so a row_counts block
            # holding "" in both fields compared equal, incremented the counter,
            # and produced "1 row-count comparison(s) matched" about two empty
            # strings. Then a block holding "unknown" in both did the same thing,
            # because "unknown" is not blank. A row count is a NUMBER: that is
            # the test, it rejects every placeholder at once, and it cannot
            # reject an honest receipt, because a count nobody counted is not a
            # count that matched.
            unread = ", ".join("%s=%r" % (k, rc.get(k)) for k in ("before", "after_reverse")
                               if count(rc.get(k)) is None)
            problems.append("%s: row_counts does not record a count for %s; a blank, a placeholder, "
                            "a half-recorded pair, an infinity, a fraction and a negative are none "
                            "of them counts, and both before and after_reverse are required as "
                            "whole non-negative numbers of rows" % (rel, unread))
        else:
            compared += 1
            if count(rc["before"]) != count(rc["after_reverse"]):
                problems.append("reverse did not restore row count: before=%s after=%s"
                                % (rc["before"], rc["after_reverse"]))
    if unreadable:
        return "FAIL", ("migration receipt present but unparseable: %s; a receipt that cannot be read is a broken claim, not an absent one"
                        % ", ".join(unreadable))
    if problems:
        return "FAIL", "; ".join(problems[:6])
    if not checked:
        return "NO-DATA", ("migration receipt present but records no migration (%s); an empty receipt "
                           "proves nothing, so it is NO-DATA, never a pass" % "; ".join(nothing))
    if nothing:
        return "NO-DATA", ("%d receipt(s) with both legs run against a restore, but %d recorded no row "
                           "counts (%s); the reverse restoring the rows is the half this gate cannot "
                           "assert, so it does not"
                           % (checked, len(nothing), "; ".join(nothing[:4])))
    return "PASS", ("%d receipt(s): forward and reverse both ran against a restore, %d row-count "
                    "comparison(s) matched, and a rehearsal id string is recorded%s"
                    % (checked, compared, pruned))


def gate_approval(root):
    approvals, pruned = find(root, APPROVAL_FILE)
    body, sig, authors = git_trailers(root)
    trailer = re.search(r"^Approved-by:\s*(.+)$", body, re.M)
    # The id is whatever the team writes, not one whitespace-free token. `(\S+)$`
    # was a shape rule nothing declared: `Reviewed-in: PR 99999 on the payments
    # board` matched nothing, fell past this branch, and got FAIL with the
    # sentence "approval is a typed name with no signature or review id" printed
    # over a commit that records one. The law says there is no shape check on the
    # id beyond refusing the tokens that name the absence of one, so this reads
    # the line and lets `answered()` be the only test.
    review_id = re.search(r"^Reviewed-in:\s*(.+)$", body, re.M)
    # The APPROVAL file declares this change touches money/partner paths.
    if not approvals and not trailer:
        return "NO-DATA", ("no APPROVAL file and no Approved-by trailer; if this change touches no "
                           "money or partner path that is correct%s" % pruned)
    # Self-approval is not approval, and the gate did not look. One person, one
    # key: they authored the commit, signed the commit and wrote their own name
    # into the Approved-by trailer, and this gate printed "signed commit carries
    # Approved-by: Dana Author" over it while the line above the verdict showed
    # the same identity three times. A signature proves a key holder signed. It
    # cannot prove a SECOND party looked, and a second party is the entire content
    # of the word approval.
    if trailer:
        approver = _identity_tokens(trailer.group(1))
        wrote = set()
        for who in authors:
            wrote |= _identity_tokens(who)
        overlap = sorted(approver & wrote)
        if overlap:
            return "FAIL", ("the Approved-by identity is the identity that wrote the commit (%s); "
                            "author and committer are %s. Self-approval is not approval: a "
                            "signature proves a key holder signed, and it cannot prove a second "
                            "party reviewed. Have the approver sign, or record a Reviewed-in id "
                            "pointing at a review somebody else performed"
                            % (", ".join(overlap), ", ".join(authors) or "unrecorded"))
    # An approval was claimed: now it must be bound to a forgeable-resistant identity.
    # Only a signature that VERIFIED counts. git's %G? returns G (good) and U (good,
    # untrusted-but-valid) for a signature this host actually checked. E means the
    # signature could not be checked at all, which on a runner with no imported keys
    # is the expected result for every signed commit, including one signed by a key
    # nobody on the team recognises. Accepting E would trust the unknown while
    # rejecting a known key that had merely expired, so E is NO-DATA, not an approval.
    if trailer and sig in ("G", "U"):
        return "PASS", ("signed commit carries Approved-by: %s, and that identity is not the "
                        "commit's author or committer (%s)%s"
                        % (trailer.group(1).strip(), ", ".join(authors) or "unrecorded", pruned))
    if review_id and answered(review_id.group(1)) is not None:
        # NO-DATA, not PASS, and the argument is internal consistency rather than
        # taste. Four lines below, a signature THIS HOST COULD NOT VERIFY returns
        # NO-DATA, with the reasoning "an unverifiable signature is not an
        # approval". A Reviewed-in id is in the identical epistemic state: this
        # gate cannot resolve it either, and the agent writes the commit message.
        # Two identical states must not get two different verdicts, and while
        # this one returned PASS the strongest sentence this gate could print
        # about a money-movement change was purchasable with a single hyphen.
        # NO-DATA neither blocks nor passes, so no honest team is impeded.
        return "NO-DATA", ("commit records Reviewed-in: %s. This gate read a trailer out of a commit "
                           "message and does not resolve the id against any review platform, so it "
                           "points a human at a review rather than proving one happened. That is a "
                           "pointer, not a control: resolve the id in CI (a job that queries your "
                           "review platform) or sign the commit, and this becomes a verdict"
                           % review_id.group(1))
    if review_id:
        return "FAIL", ("the Reviewed-in trailer records %r, which names no review; an id nobody can "
                        "follow is not a pointer at anything" % review_id.group(1))
    if trailer and sig == "E":
        return "NO-DATA", ("signature present but this host could not verify it (git %G? = E): import the signer's public key "
                           "into the verifying keyring, or use a Reviewed-in: review id, which needs no keyring. "
                           "An unverifiable signature is not an approval")
    return "FAIL", "approval is a typed name with no signature or review id; a name in a text field is not a control (add a signed Approved-by trailer or a Reviewed-in review id)"


def gate_ran(root):
    receipts, pruned = find(root, RAN_RECEIPT)
    if not receipts:
        return "NO-DATA", ("no ran-receipt.json; a SQL or pipeline change is not done until its "
                           "check executed and left a receipt%s" % pruned)
    problems = []
    unreadable = []
    nothing = []
    checked = 0
    for m in receipts:
        d, err = load_receipt(m)
        if d is None:
            unreadable.append("%s: %s" % (os.path.relpath(m, root), err))
            continue
        chks, note = _items(d, "checks")
        if not chks:
            nothing.append("%s: %s" % (os.path.relpath(m, root), note))
            continue
        for chk in chks:
            checked += 1
            if not isinstance(chk, dict):
                problems.append("entry %d in %s is %s, not a check object"
                                % (checked, os.path.relpath(m, root), type(chk).__name__))
                continue
            name = answered(chk.get("name")) or "check %d" % checked
            if answered(chk.get("name")) is None:
                problems.append("%s in %s records no name (%r), so nothing in the report can say "
                                "what ran" % (name, os.path.relpath(m, root), chk.get("name")))
            # An exit code is an integer and a duration is a number. `False`
            # satisfied `!= 0` and `True` satisfied a truthiness test, so
            # {"exit_code": false, "duration_ms": true} passed as "a zero exit and
            # a nonzero duration". Booleans are neither.
            code = chk.get("exit_code")
            if code is None:
                problems.append("%s: no exit code recorded (was it actually run?)" % name)
            elif isinstance(code, bool) or not isinstance(code, int):
                problems.append("%s: exit_code is %r, which is not an exit status integer"
                                % (name, code))
            elif code != 0:
                problems.append("%s: check exited nonzero (%s)" % (name, code))
            ms = chk.get("duration_ms")
            if isinstance(ms, bool) or not isinstance(ms, (int, float)):
                problems.append("%s: duration_ms is %r, which is not a measured duration in "
                                "milliseconds" % (name, ms))
            elif numeric(ms) is None:
                # The shared rule, not a hand test: `NaN <= 0` is False and
                # json.load accepts bare NaN and Infinity, so a receipt carrying
                # either cleared this gate while its sentence asserted "a
                # nonzero duration". An infinity is not a measurement and
                # neither is a not-a-number; sbe_checks.numeric refuses both.
                problems.append("%s: duration_ms is %r, and an infinity or a not-a-number is not a "
                                "measured duration" % (name, ms))
            elif ms <= 0:
                problems.append("%s: zero or negative duration (a check that took no time did not run)" % name)
    if unreadable:
        return "FAIL", ("ran-receipt present but unparseable: %s; a receipt that cannot be read is a broken claim, not an absent one"
                        % ", ".join(unreadable))
    if problems:
        return "FAIL", "; ".join(problems[:6])
    if not checked:
        return "NO-DATA", ("ran-receipt present but records no checks (%s); a receipt with nothing in it is exactly what a run that never happened produces, so it is NO-DATA, never a pass"
                           % "; ".join(nothing))
    if nothing:
        return _partial(nothing, checked, "ran-receipt", "check(s)")
    return "PASS", ("%d recorded check(s), each with a zero exit and a nonzero duration%s"
                    % (checked, pruned))


# The registry is the contract. Each gate declares the evidence it opens, what its
# empty state is, and a worked receipt that SHOULD pass, and
# evals/test_no_data_class.py discovers exactly this dict: a gate added later is
# covered by the meta-test the moment it is registered, because it cannot be
# registered without the declaration. The full_fixture receipts below are minimal
# on purpose: every field in them is a field the PASS sentence asserts over, so
# the honesty test can empty any one of them and demand the PASS goes away.
GATES = {
    "numbers": Check(
        gate_numbers, reads=(MANIFEST,), kind="json", item_key="figures",
        full_fixture={"files": {MANIFEST: {"figures": [{
            "label": "gmv", "snapshot_id": "snap-2026-07",
            "query": "SELECT SUM(amount) FROM orders",
            "second_derivation": "SELECT SUM(qty*price) FROM order_lines",
            "rerun": {"ran": True, "primary": 17570, "secondary": 17570}}]}}}),
    "migration": Check(
        gate_migration, reads=(MIGRATION_RECEIPT,), kind="json",
        full_fixture={"files": {MIGRATION_RECEIPT: {
            "forward": {"ran_against_restore": True},
            "reverse": {"ran_against_restore": True, "rehearsal_run_id": "job-8842"},
            "row_counts": {"before": 100, "after_reverse": 100}}}}),
    "approval": Check(
        gate_approval, reads=(APPROVAL_FILE,), kind="git", empty_expect="FAIL",
        empty_fixture="",
        empty_note="the presence of an APPROVAL file IS the claim that this change touches a "
                   "money or partner path. An empty one is that claim with no identity behind "
                   "it, which is a broken claim and not an absence, so it FAILs rather than "
                   "reporting NO-DATA",
        full_fixture={"files": {APPROVAL_FILE: "touches the partner payout path\n"},
                      "git": {"message": "payout batching\n\nReviewed-in: PR-99999"}},
        full_expect="NO-DATA",
        full_expect_reason=(
            "this gate reaches PASS only on a commit whose signature THIS HOST verified, and no "
            "fixture can produce one: the honesty test has no private key and importing one would "
            "make the test prove something about the test's keyring rather than about the gate. The "
            "strongest evidence a fixture can carry is the keyless Reviewed-in trailer, whose "
            "honest verdict is NO-DATA, so that is what the worked example asserts")),
    "ran": Check(
        gate_ran, reads=(RAN_RECEIPT,), kind="json", item_key="checks",
        full_fixture={"files": {RAN_RECEIPT: {"checks": [
            {"name": "reconcile", "exit_code": 0, "duration_ms": 812}]}}}),
}


def main():
    argv = [a for a in sys.argv[1:] if a != "--strict"]
    strict = "--strict" in sys.argv
    root = "."
    which = list(GATES)
    for a in argv:
        if a in GATES:
            which = [a]
        elif os.path.isdir(a):
            root = a
    try:
        root = subprocess.run(["git", "-C", root, "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, timeout=10).stdout.strip() or root
    except Exception:  # sbe: allow-silent not a git worktree; root stays as given and every gate below still runs and still prints
        pass
    fails = 0
    print("BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass)")
    for name in which:
        # Guarded per gate: a crash inside one gate used to abort the loop, so
        # every gate after it printed nothing at all and advisory mode exited 0.
        # A gate that vanishes is worse than a gate that fails.
        verdict, ev = run_guarded(name, GATES[name], root)
        if verdict == "FAIL":
            fails += 1
        print("  %-9s %-8s %s" % (name, verdict, ev))
    if strict and fails:
        print("STRICT: %d hard gate(s) failed; exiting nonzero to block the merge." % fails)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # A broken gate must not silently pass work. In strict mode a crash blocks.
        print("sbe_gate: error %r" % (e,))
        sys.exit(1 if "--strict" in sys.argv else 0)
