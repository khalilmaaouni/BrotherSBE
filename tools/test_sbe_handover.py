"""Adversarial fixtures for `sbe handover` (LT-301: `12-handover.json`, an
explicit human handover that is complete only after a named human receiver
acknowledges). Covers the spec's own acceptance list plus every one of
LT-303's eleven engine-layer adversarial cases: receiver equals outgoing
owner, receiver equals a worker agent identity, changed HEAD, a dirty
untracked file named, missing evidence named, missing required access
refused and named, rejected then re-prepared with both records' own history
honest, two receivers racing (the winner wins once, the loser's refusal
names the winner), overwrite refused across commits, a task changing after
preparation (frozen when HEAD holds, staleness when a commit carries the
change), and Unicode/case-fold identity ambiguity (gmail's dot fold, an
NFC/NFD normalization pair, and an uppercase/lowercase domain).

Every fixture builds its own throwaway git repository with a dossier under
design/, seeded through the real `sbe plan --write` wherever a task graph is
needed, so the handover is always read over artifacts the real tools
produced, exactly the technique `tools/test_sbe_status_team.py` already
uses (mirrored here rather than re-invented).
"""
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unicodedata
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SBE = os.path.join(HERE, "..", "bin", "sbe")

INTAKE = {
    "answers": {"changes_contract": "n", "crosses_boundary": "n",
                "reversible_under_hour": "y", "touches_sensitive": "n",
                "consumers": "none"},
    "tier": "T1", "override": None, "override_reason": None,
}

ADR_TEMPLATE = """# ADR
## Context
x
## Decision
Serve the change from `%s`.
## Consequences
ok
"""

VERIFICATION = """| Claim this design makes | The check that proves it | When it runs |
|---|---|---|
| it answers | `python3 -c pass` | CI |
"""


def _run(argv, cwd=None, env=None):
    out = subprocess.run(argv, capture_output=True, text=True, cwd=cwd, env=env,
                         stdin=subprocess.DEVNULL, timeout=120)
    # Three values, not two: a two-value return reads as a possible
    # (verdict, evidence) pair to the honesty meta-test, which refuses any
    # such function sitting outside a check registry.
    return out.returncode, out.stdout + out.stderr, out.stderr


class HandoverScenario(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sbe-handover-")
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(self.repo)
        self.git("init", "-q")
        self.git("config", "user.email", "outgoing@example.com")
        self.git("config", "user.name", "Outgoing Owner")
        io.open(os.path.join(self.repo, "seed.txt"), "w").write("seed\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "seed")

    def tearDown(self):
        # A lock sidecar this process still holds open (a scenario that
        # asserted mid-lock state) would make rmtree fail on some platforms;
        # nothing here holds one across a test boundary, but the permission
        # reset mirrors test_sbe_status_team.py's own defensive tearDown.
        reg = os.path.join(self.repo, ".sbe", "tasks.json")
        if os.path.exists(reg):
            os.chmod(reg, stat.S_IRUSR | stat.S_IWUSR)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args):
        code, text, _err = _run(["git", "-C", self.repo] + list(args))
        self.assertEqual(code, 0, "git %s failed: %s" % (args, text))
        return text

    def sbe(self, *args, **kwargs):
        cwd = kwargs.pop("cwd", self.repo)
        return _run([sys.executable, SBE] + list(args), cwd=cwd)

    def handover(self, *args):
        return self.sbe("handover", *args)

    def commit_all(self, msg):
        self.git("add", "-A")
        self.git("commit", "-qm", msg)
        return self.git("rev-parse", "HEAD").strip()

    def head(self):
        return self.git("rev-parse", "HEAD").strip()

    def _change(self, name, src_rel):
        """A real dossier with a real `08-plan.json`, seeded through `sbe
        plan --write`, mirroring `TeamScenario._change` in
        test_sbe_status_team.py exactly."""
        doss = os.path.join(self.repo, "design", name)
        os.makedirs(doss)
        io.open(os.path.join(doss, "00-intake.json"), "w").write(json.dumps(INTAKE, indent=2))
        io.open(os.path.join(doss, "03-adr.md"), "w").write(ADR_TEMPLATE % src_rel)
        io.open(os.path.join(doss, "07-verification.md"), "w").write(VERIFICATION)
        src = os.path.join(self.repo, src_rel)
        parent = os.path.dirname(src)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        io.open(src, "w").write("x = 1\n")
        code, text, _ = self.sbe("plan", doss, "--write", "--cwd", self.repo)
        self.assertEqual(code, 0, "plan --write for %s: %s" % (name, text))
        return doss

    def _bare_dossier(self, name):
        doss = os.path.join(self.repo, "design", name)
        os.makedirs(doss)
        io.open(os.path.join(doss, "00-intake.json"), "w").write(json.dumps(INTAKE, indent=2))
        return doss

    def _registry(self):
        reg_dir = os.path.join(self.repo, ".sbe")
        if not os.path.isdir(reg_dir):
            os.makedirs(reg_dir)
        reg = os.path.join(reg_dir, "tasks.json")
        data = {"schemaVersion": "1.0", "tasks": []}
        if os.path.exists(reg):
            data = json.loads(io.open(reg).read())
        return reg, data

    def _open_record(self, task_id, owns, agent="alice", base_commit=None, worktree=None):
        reg, data = self._registry()
        data["tasks"].append({
            "id": task_id, "agent": agent, "role": "writer", "worktree": worktree,
            "ownedPaths": owns, "readOnlyPaths": [], "baseCommit": base_commit,
            "expiry": None, "status": "open", "verifyCommand": "python3 -c pass",
            "evidenceId": None, "openedAt": "2026-07-30T00:00:00Z", "closedAt": None,
        })
        io.open(reg, "w").write(json.dumps(data, indent=2))

    def _closed_record(self, task_id, owns, agent="alice", base_commit=None, forced=False):
        reg, data = self._registry()
        record = {
            "id": task_id, "agent": agent, "role": "writer", "worktree": None,
            "ownedPaths": owns, "readOnlyPaths": [], "baseCommit": base_commit,
            "expiry": None, "status": "closed", "verifyCommand": "python3 -c pass",
            "evidenceId": None, "openedAt": "2026-07-30T00:00:00Z",
            "closedAt": "2026-07-30T01:00:00Z",
        }
        if forced:
            record["forced"] = {"who": "bob", "why": "test"}
        data["tasks"].append(record)
        io.open(reg, "w").write(json.dumps(data, indent=2))

    def _receipt(self, out_rel, covers, cwd=None, fail=False):
        cwd = cwd or self.repo
        cmd = [sys.executable, "-c", "import sys; sys.exit(%d)" % (1 if fail else 0)]
        code, text, _ = self.sbe("evidence", "run", "--out", out_rel, "--cwd", cwd,
                                 "--covers", covers, "--", *cmd)
        return code, text

    def _read_handover(self, doss):
        path = os.path.join(doss, "12-handover.json")
        return json.loads(io.open(path, encoding="utf-8").read())

    def _handover_path(self, doss):
        return os.path.join(doss, "12-handover.json")

    def _prepared(self, name="chg-a", src="src/a.py", outgoing="alice@example.com",
                  receiver="bob@example.com"):
        """A committed dossier with a fresh, successfully prepared handover:
        the common starting point most acknowledge/reject/staleness/overwrite
        scenarios need, so each of those states only what it adds on top."""
        doss = self._change(name, src)
        self.commit_all("dossier")
        code, text, _ = self.handover("prepare", doss, "--outgoing", outgoing,
                                      "--receiver", receiver)
        self.assertEqual(code, 0, text)
        return doss


# ---------------------------------------------------------------------------
# Schema and derivation
# ---------------------------------------------------------------------------

class TestSchemaAndDerivation(HandoverScenario):
    SCHEMA_FIELDS = ("schemaVersion", "headSha", "change", "preparedBy", "preparedAt",
                     "outgoingOwner", "intendedReceiver", "status", "done", "inFlight",
                     "notStarted", "openQuestions", "decisions", "evidence", "activeTasks",
                     "worktrees", "requiredAccess", "nextAction", "acknowledgment")

    def test_prepare_writes_every_schema_field_verbatim_and_nothing_else(self):
        doss = self._prepared()
        data = self._read_handover(doss)
        self.assertEqual(set(data.keys()), set(self.SCHEMA_FIELDS),
                         "the written record must carry exactly the spec's fields: %s"
                         % sorted(data.keys()))
        self.assertEqual(data["schemaVersion"], "1.0")
        self.assertEqual(data["status"], "prepared")
        self.assertIsNone(data["acknowledgment"])
        self.assertEqual(data["headSha"], self.head())
        self.assertIsInstance(data["nextAction"], str)
        self.assertTrue(data["nextAction"].strip(), "nextAction must be one action, always "
                                                     "present")

    def test_prepare_binds_to_current_head(self):
        doss = self._change("chg-a", "src/a.py")
        head = self.commit_all("dossier")
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "bob@example.com")
        self.assertEqual(code, 0, text)
        data = self._read_handover(doss)
        self.assertEqual(data["headSha"], head)

    def test_a_missing_plan_derives_empty_task_lists_not_a_crash(self):
        doss = self._bare_dossier("chg-bare")
        self.commit_all("dossier")
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "bob@example.com")
        self.assertEqual(code, 0, text)
        data = self._read_handover(doss)
        self.assertEqual(data["done"], [])
        self.assertEqual(data["inFlight"], [])
        self.assertEqual(data["notStarted"], [])

    def test_done_in_flight_not_started_come_from_the_plan_and_the_registry(self):
        doss = self._change("chg-a", "src/a.py")
        self.commit_all("dossier")
        code, text, _ = self.sbe("evidence", "run", "--out",
                                 os.path.join(self.repo, ".sbe", "evidence", "r.json"),
                                 "--cwd", self.repo, "--covers", "src/a.py",
                                 "--", sys.executable, "-c", "pass")
        self.assertEqual(code, 0, text)
        self._closed_record("T01", ["src/a.py"], agent="alice")
        self._open_record("T02", [], agent="carol")
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "dave@example.com")
        self.assertEqual(code, 0, text)
        data = self._read_handover(doss)
        done_ids = {t["id"] for t in data["done"]}
        flight_ids = {t["id"] for t in data["inFlight"]}
        self.assertIn("T01", done_ids, data)
        self.assertIn("T02", flight_ids, data)
        active_ids = {t["id"] for t in data["activeTasks"]}
        self.assertIn("T02", active_ids, "active task ownership must list the open task: %s"
                                         % data["activeTasks"])
        owner = next(t for t in data["activeTasks"] if t["id"] == "T02")
        self.assertEqual(owner["agent"], "carol")

    def test_a_forced_close_never_counts_as_done(self):
        doss = self._change("chg-a", "src/a.py")
        self.commit_all("dossier")
        self._closed_record("T01", ["src/a.py"], agent="alice", forced=True)
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "dave@example.com")
        self.assertEqual(code, 0, text)
        data = self._read_handover(doss)
        done_ids = {t["id"] for t in data["done"]}
        self.assertNotIn("T01", done_ids, "a FORCED close is a disposition, never a "
                                          "completion: %s" % data["done"])
        not_started_ids = {t["id"] for t in data["notStarted"]}
        self.assertIn("T01", not_started_ids, data)

    def test_missing_evidence_is_named_not_silently_dropped(self):
        doss = self._prepared()
        data = self._read_handover(doss)
        store = [e for e in data["evidence"] if e["kind"] == "receipt-store"]
        self.assertTrue(store, data["evidence"])
        self.assertEqual(store[0]["status"], "absent")
        self.assertIn("no evidence store found", store[0]["detail"])
        conv = [e for e in data["evidence"] if e["kind"] == "convergence"]
        self.assertEqual(conv[0]["status"], "absent")
        appr = [e for e in data["evidence"] if e["kind"] == "approval"]
        self.assertEqual(appr[0]["status"], "absent")
        rev = [e for e in data["evidence"] if e["kind"] == "review"]
        self.assertEqual(rev[0]["status"], "absent")

    def test_stale_evidence_receipt_is_named(self):
        doss = self._change("chg-a", "src/a.py")
        self.commit_all("dossier")
        out = os.path.join(self.repo, ".sbe", "evidence", "a.json")
        code, text = self._receipt(out, "src/a.py")
        self.assertEqual(code, 0, text)
        # Move HEAD without touching src/a.py: the receipt's own headCommit
        # binding is now stale even though its covered file is untouched.
        io.open(os.path.join(self.repo, "unrelated.txt"), "w").write("x\n")
        self.commit_all("unrelated commit")
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "bob@example.com")
        self.assertEqual(code, 0, text)
        data = self._read_handover(doss)
        receipts = [e for e in data["evidence"] if e["kind"] == "receipt"]
        self.assertTrue(receipts, data["evidence"])
        self.assertTrue(any(e["status"] == "stale" for e in receipts),
                        "a receipt bound to a commit that moved must be named stale: %s"
                        % receipts)

    def test_dirty_untracked_file_is_named_in_worktrees(self):
        doss = self._change("chg-a", "src/a.py")
        self.commit_all("dossier")
        io.open(os.path.join(self.repo, "src", "untracked_extra.py"), "w").write("z = 1\n")
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "bob@example.com")
        self.assertEqual(code, 0, text)
        data = self._read_handover(doss)
        root_entry = data["worktrees"][0]
        self.assertTrue(root_entry["dirty"], data["worktrees"])
        self.assertIn("src/untracked_extra.py", root_entry["files"], root_entry)

    def test_a_clean_tree_reports_no_dirty_worktree_from_its_own_handover_file(self):
        # The handover file (and its lock sidecar) is always about to be
        # written by this very run; it must never make its own worktree
        # entry read as dirty.
        doss = self._prepared()
        data = self._read_handover(doss)
        root_entry = data["worktrees"][0]
        self.assertFalse(root_entry["dirty"],
                         "preparing a handover must not report itself as dirty state: %s"
                         % root_entry)
        for f in root_entry["files"]:
            self.assertNotIn("12-handover.json", f, root_entry)


# ---------------------------------------------------------------------------
# Overwrite refusal
# ---------------------------------------------------------------------------

class TestOverwriteRefusal(HandoverScenario):
    def test_prepare_refuses_silent_overwrite_bound_to_another_commit(self):
        doss = self._prepared()
        head1 = self._read_handover(doss)["headSha"]
        io.open(os.path.join(self.repo, "src", "a.py"), "a").write("y = 2\n")
        head2 = self.commit_all("more work")
        self.assertNotEqual(head1, head2)
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "bob@example.com")
        self.assertNotEqual(code, 0, "a still-prepared handover bound to another commit "
                                     "must not be silently overwritten: %s" % text)
        self.assertIn("refused", text)
        data = self._read_handover(doss)
        self.assertEqual(data["headSha"], head1, "the original binding must survive the "
                                                  "refused overwrite attempt")

    def test_prepare_at_the_same_head_is_a_permitted_refresh(self):
        doss = self._prepared()
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "carol@example.com")
        self.assertEqual(code, 0, "re-preparing at the SAME head must succeed: %s" % text)
        data = self._read_handover(doss)
        self.assertEqual(data["intendedReceiver"], "carol@example.com")

    def test_rejected_then_reprepared(self):
        doss = self._prepared()
        code, text, _ = self.handover("reject", doss, "--receiver", "bob@example.com",
                                      "--reason", "not ready")
        self.assertEqual(code, 0, text)
        io.open(os.path.join(self.repo, "src", "a.py"), "a").write("y = 2\n")
        self.commit_all("addressed the rejection")
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "bob@example.com")
        self.assertEqual(code, 0, "a rejected handover must be freely re-preparable, even "
                                  "at a new commit: %s" % text)
        data = self._read_handover(doss)
        self.assertEqual(data["status"], "prepared")
        self.assertIsNone(data["acknowledgment"])

    def test_reject_reprepare_reject_again_keeps_each_cycles_reason_honest(self):
        """LT-303: 'rejected then re-prepared' with BOTH resulting records
        checked, not just the second. The first reject's own reason must
        read back exactly as recorded before a re-prepare replaces the file
        on disk, and a SECOND reject on the fresh record must carry its own
        text, never the first cycle's reason silently surviving into the
        new one (the whole record is replaced wholesale by prepare, so a
        leftover value here would mean two unrelated decisions were
        conflated, not that either record was individually honest)."""
        doss = self._prepared()
        code, text, _ = self.handover("reject", doss, "--receiver", "bob@example.com",
                                      "--reason", "not ready")
        self.assertEqual(code, 0, text)
        first = self._read_handover(doss)
        self.assertEqual(first["status"], "rejected")
        self.assertEqual(first["acknowledgment"]["reason"], "not ready", first)
        self.assertEqual(first["outgoingOwner"], "alice@example.com", first)

        io.open(os.path.join(self.repo, "src", "a.py"), "a").write("y = 2\n")
        self.commit_all("addressed the first rejection")
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "carol@example.com")
        self.assertEqual(code, 0, text)
        second_prepared = self._read_handover(doss)
        self.assertEqual(second_prepared["status"], "prepared")
        self.assertIsNone(second_prepared["acknowledgment"], "the fresh record must not carry "
                          "the first cycle's rejection forward: %s" % second_prepared)

        code, text, _ = self.handover("reject", doss, "--receiver", "carol@example.com",
                                      "--reason", "still broken")
        self.assertEqual(code, 0, text)
        second = self._read_handover(doss)
        self.assertEqual(second["status"], "rejected")
        self.assertEqual(second["acknowledgment"]["reason"], "still broken",
                         "the second cycle's own reason must be recorded, not the first "
                         "cycle's 'not ready' silently carried forward: %s" % second)
        self.assertNotEqual(second["acknowledgment"]["reason"], first["acknowledgment"]["reason"])
        self.assertEqual(second["outgoingOwner"], "alice@example.com",
                         "ownership on record must stay the true outgoing owner across both "
                         "honest reject cycles")

    def test_prepare_refuses_to_overwrite_an_acknowledged_handover(self):
        doss = self._prepared()
        code, text, _ = self.handover("acknowledge", doss, "--receiver", "bob@example.com")
        self.assertEqual(code, 0, text)
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "carol@example.com")
        self.assertNotEqual(code, 0, "an acknowledged handover is a completed acceptance "
                                     "record and must never be silently overwritten: %s"
                                     % text)
        data = self._read_handover(doss)
        self.assertEqual(data["status"], "acknowledged")
        self.assertEqual(data["intendedReceiver"], "bob@example.com")


# ---------------------------------------------------------------------------
# Identity: self-handover, agent identities, Unicode/case-fold ambiguity.
# ---------------------------------------------------------------------------

class TestIdentity(HandoverScenario):
    def test_prepare_refuses_every_forged_shape_of_self_handover(self):
        """One dossier, several (outgoing, receiver) pairs that all read as
        ONE person: a literal match, a gmail dot-fold (two mailbox spellings
        of one inbox), and an initial against a full name. Each must refuse
        at prepare with no file written; a genuinely different receiver
        (the last pair) must succeed, proving the guard does not over-fire."""
        doss = self._change("chg-a", "src/a.py")
        self.commit_all("dossier")
        forged_pairs = [
            ("alice@example.com", "alice@example.com"),
            ("alice.author@gmail.com", "aliceauthor@gmail.com"),
            ("Dana Author", "D. Author"),
        ]
        for outgoing, receiver in forged_pairs:
            code, text, _ = self.handover("prepare", doss, "--outgoing", outgoing,
                                          "--receiver", receiver)
            self.assertNotEqual(code, 0, "%r vs %r must refuse as one identity: %s"
                                         % (outgoing, receiver, text))
            self.assertIn("same identity", text)
            self.assertFalse(os.path.exists(self._handover_path(doss)))
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "bob@example.com")
        self.assertEqual(code, 0, "a genuinely different receiver must be accepted: %s" % text)

    def test_receiver_equal_to_outgoing_owner_is_refused_at_acknowledge(self):
        # The receiver at acknowledge time need not match --receiver at
        # prepare time (intendedReceiver is a hint, never enforced identity):
        # this proves the guard is the OUTGOING owner comparison, independent
        # of whatever was typed at prepare.
        doss = self._prepared(outgoing="Alice Author <alice@example.com>")
        code, text, _ = self.handover("acknowledge", doss,
                                      "--receiver", "ALICE AUTHOR <ALICE@EXAMPLE.COM>")
        self.assertNotEqual(code, 0, "case alone must not make a second person: %s" % text)
        self.assertIn("same identity", text)
        data = self._read_handover(doss)
        self.assertEqual(data["status"], "prepared", "a refused acknowledge must not "
                                                      "change status")

    def test_receiver_equal_to_a_worker_agent_identity_is_refused_at_acknowledge(self):
        # The registry is read live at acknowledge time, not frozen at
        # prepare, so the agent record can be seeded after prepare too.
        doss = self._prepared()
        self._closed_record("T01", ["src/a.py"], agent="Agent Zed")
        code, text, _ = self.handover("acknowledge", doss, "--receiver", "agent zed")
        self.assertNotEqual(code, 0, "an agent identity, even case-folded and from a "
                                     "CLOSED record, must never acknowledge as the human "
                                     "receiver: %s" % text)
        self.assertIn("agent", text.lower())

    def test_nfc_and_nfd_spellings_of_one_name_read_as_the_same_identity(self):
        """LT-303: Unicode normalization ambiguity. 'José García' composed
        (NFC, one code point per accented letter) and decomposed (NFD, a base
        letter plus a combining accent) are two different byte sequences for
        the SAME rendered name; the identity comparison this module reuses
        from sbe_gate must not read a decomposition choice as a second
        person."""
        doss = self._change("chg-a", "src/a.py")
        self.commit_all("dossier")
        nfc_name = unicodedata.normalize("NFC", "José García")
        nfd_name = unicodedata.normalize("NFD", nfc_name)
        self.assertNotEqual(nfc_name, nfd_name, "the fixture must exercise two distinct byte "
                                                 "spellings of the name, or it proves nothing")
        code, text, _ = self.handover("prepare", doss, "--outgoing", nfc_name,
                                      "--receiver", nfd_name)
        self.assertNotEqual(code, 0, "an NFC and an NFD spelling of one name must read as "
                                     "one identity: %s" % text)
        self.assertIn("same identity", text)
        self.assertFalse(os.path.exists(self._handover_path(doss)))

    def test_uppercase_and_lowercase_domain_of_one_mailbox_read_as_the_same_identity(self):
        """LT-303's uppercase/lowercase DOMAIN case, isolated from the local
        part and from any name text: the earlier forged-shape test only ever
        varied case across a whole name-and-email string at once, which
        leaves a domain-only casefold bug free to hide behind the local
        part's own match. alice@example.com and alice@EXAMPLE.COM name one
        mailbox, not two people."""
        doss = self._change("chg-b", "src/b.py")
        self.commit_all("dossier")
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "alice@EXAMPLE.COM")
        self.assertNotEqual(code, 0, "a domain differing only in case must not make a "
                                     "second mailbox: %s" % text)
        self.assertIn("same identity", text)
        self.assertFalse(os.path.exists(self._handover_path(doss)))


# ---------------------------------------------------------------------------
# Staleness
# ---------------------------------------------------------------------------

class TestStaleness(HandoverScenario):
    def test_changed_head_makes_show_report_stale(self):
        doss = self._prepared()
        io.open(os.path.join(self.repo, "src", "a.py"), "a").write("y = 2\n")
        self.commit_all("moved on")
        code, text, _ = self.handover("show", doss, "--json")
        self.assertEqual(code, 0, text)
        data = json.loads(text[text.index("{"):])
        self.assertTrue(data["stale"], text)

    def test_changed_head_refuses_acknowledgment(self):
        doss = self._prepared()
        io.open(os.path.join(self.repo, "src", "a.py"), "a").write("y = 2\n")
        self.commit_all("moved on")
        code, text, _ = self.handover("acknowledge", doss, "--receiver", "bob@example.com")
        self.assertNotEqual(code, 0, "a stale handover must refuse acknowledgment: %s" % text)
        self.assertIn("STALE", text)
        data = self._read_handover(doss)
        self.assertEqual(data["status"], "prepared", "a refused, stale acknowledge must not "
                                                      "move ownership")


# ---------------------------------------------------------------------------
# Acknowledge / reject
# ---------------------------------------------------------------------------

class TestAcknowledgeReject(HandoverScenario):
    def test_written_only_transfer_is_incomplete(self):
        doss = self._prepared()
        data = self._read_handover(doss)
        self.assertEqual(data["status"], "prepared")
        self.assertIsNone(data["acknowledgment"], "a written-only handover carries no "
                                                   "acknowledgment: transfer is incomplete")

    def test_verbal_only_transfer_leaves_no_data(self):
        doss = self._change("chg-a", "src/a.py")
        self.commit_all("dossier")
        code, text, _ = self.handover("show", doss)
        self.assertEqual(code, 0, text)
        self.assertIn("NO-DATA", text, "no artifact exists, so a verbal-only 'I handed it "
                                       "off' reads as NO-DATA, never a completed transfer")

    def test_prepared_plus_acknowledged_is_complete(self):
        doss = self._prepared()
        head = self._read_handover(doss)["headSha"]
        code, text, _ = self.handover("acknowledge", doss, "--receiver", "bob@example.com")
        self.assertEqual(code, 0, text)
        data = self._read_handover(doss)
        self.assertEqual(data["status"], "acknowledged")
        ack = data["acknowledgment"]
        self.assertEqual(ack["outcome"], "accepted")
        self.assertEqual(ack["receiver"], "bob@example.com")
        self.assertEqual(ack["headSha"], head)
        self.assertTrue(ack["at"])

    def test_rejection_keeps_ownership_and_records_the_reason(self):
        doss = self._prepared()
        code, text, _ = self.handover("reject", doss, "--receiver", "bob@example.com",
                                      "--reason", "missing tests")
        self.assertEqual(code, 0, text)
        data = self._read_handover(doss)
        self.assertEqual(data["status"], "rejected")
        self.assertEqual(data["outgoingOwner"], "alice@example.com",
                         "the outgoing owner must remain on record as the owner")
        self.assertEqual(data["acknowledgment"]["reason"], "missing tests")

    def test_rejected_handover_remains_visible(self):
        doss = self._prepared()
        self.handover("reject", doss, "--receiver", "bob@example.com", "--reason", "no")
        code, text, _ = self.handover("show", doss)
        self.assertEqual(code, 0, text)
        self.assertIn("rejected", text)

    def test_missing_required_access_prevents_acceptance_and_names_it(self):
        doss = self._prepared()
        path = self._handover_path(doss)
        data = self._read_handover(doss)
        data["requiredAccess"] = ["staging logs"]
        io.open(path, "w").write(json.dumps(data, indent=2, sort_keys=True))
        code, text, _ = self.handover("acknowledge", doss, "--receiver", "bob@example.com")
        self.assertNotEqual(code, 0, "outstanding required access must block acceptance: %s"
                                     % text)
        self.assertIn("staging logs", text)
        data = self._read_handover(doss)
        self.assertEqual(data["status"], "prepared")
        code, text, _ = self.handover("reject", doss, "--receiver", "bob@example.com",
                                      "--reason", "cannot get access")
        self.assertEqual(code, 0, "required access must not block a REJECTION: %s" % text)

    def test_agent_cannot_acknowledge_as_the_human_receiver(self):
        doss = self._prepared()
        self._open_record("T01", [], agent="build-bot")
        code, text, _ = self.handover("acknowledge", doss, "--receiver", "build-bot")
        self.assertNotEqual(code, 0, text)

    def test_no_task_owner_is_changed_until_acknowledgment_succeeds(self):
        doss = self._change("chg-a", "src/a.py")
        self.commit_all("dossier")
        self._open_record("T01", ["src/a.py"], agent="carol")
        reg_path = os.path.join(self.repo, ".sbe", "tasks.json")
        before = io.open(reg_path).read()
        self.handover("prepare", doss, "--outgoing", "alice@example.com",
                      "--receiver", "bob@example.com")
        after_prepare = io.open(reg_path).read()
        self.assertEqual(before, after_prepare, "prepare must never write the task registry")
        self.handover("acknowledge", doss, "--receiver", "bob@example.com")
        after_ack = io.open(reg_path).read()
        self.assertEqual(before, after_ack, "acknowledge must never write the task "
                                            "registry either: LT-301 only records the "
                                            "handover, never reassigns a task")

    def test_receiver_and_reason_are_required_and_refuse_blank(self):
        doss = self._prepared()
        code, text, _ = self.handover("acknowledge", doss, "--receiver", "   ")
        self.assertNotEqual(code, 0, text)
        code, text, _ = self.handover("reject", doss, "--receiver", "bob@example.com",
                                      "--reason", "  ")
        self.assertNotEqual(code, 0, text)

    def test_two_receivers_racing_to_acknowledge_only_one_wins(self):
        doss = self._prepared()
        results = {}

        def go(name, receiver):
            code, text, _ = self.handover("acknowledge", doss, "--receiver", receiver)
            results[name] = (code, text)

        t1 = threading.Thread(target=go, args=("x", "bob@example.com"))
        t2 = threading.Thread(target=go, args=("y", "carol@example.com"))
        t1.start(); t2.start()
        t1.join(60); t2.join(60)

        codes = [results["x"][0], results["y"][0]]
        self.assertEqual(sorted(codes), [0, 1] if 1 in codes else sorted(codes),
                         "exactly one of two racing acknowledgments must win: %s" % results)
        winners = [n for n, (c, _t) in results.items() if c == 0]
        losers = [n for n, (c, _t) in results.items() if c != 0]
        self.assertEqual(len(winners), 1, results)
        self.assertEqual(len(losers), 1, results)
        # The file itself must never be torn: it parses, and its recorded
        # acknowledgment names exactly the winner's receiver.
        data = self._read_handover(doss)
        self.assertEqual(data["status"], "acknowledged")
        winner_receiver = "bob@example.com" if winners[0] == "x" else "carol@example.com"
        self.assertEqual(data["acknowledgment"]["receiver"], winner_receiver, data)

    def test_losing_racer_is_refused_naming_the_winning_receiver(self):
        """Winning once (the test above) is not the whole guarantee: the
        LOSER's own refusal must name who won, not just fail blind, so a
        receiver who loses the race can see who to talk to instead of a bare
        error code."""
        doss = self._prepared()
        results = {}

        def go(name, receiver):
            code, text, _ = self.handover("acknowledge", doss, "--receiver", receiver)
            results[name] = (code, text)

        t1 = threading.Thread(target=go, args=("x", "bob@example.com"))
        t2 = threading.Thread(target=go, args=("y", "carol@example.com"))
        t1.start(); t2.start()
        t1.join(60); t2.join(60)

        winner = next(n for n, (c, _t) in results.items() if c == 0)
        loser = next(n for n, (c, _t) in results.items() if c != 0)
        winner_receiver = "bob@example.com" if winner == "x" else "carol@example.com"
        loser_code, loser_text = results[loser]
        self.assertNotEqual(loser_code, 0, results)
        self.assertIn("already carries status", loser_text, loser_text)
        self.assertIn(winner_receiver, loser_text,
                     "the loser's refusal must name the winning receiver, not fail blind: %s"
                     % loser_text)


# ---------------------------------------------------------------------------
# Frozen snapshot: a prepared record is not silently re-derived on read.
# ---------------------------------------------------------------------------

class TestFrozenSnapshot(HandoverScenario):
    def test_task_changed_after_preparation_leaves_the_record_frozen(self):
        doss = self._change("chg-a", "src/a.py")
        self.commit_all("dossier")
        self._open_record("T01", ["src/a.py"], agent="carol")
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "bob@example.com")
        self.assertEqual(code, 0, text)
        before = self._read_handover(doss)
        self.assertIn("T01", {t["id"] for t in before["inFlight"]})

        # The task closes AFTER prepare ran, with no new commit: HEAD is
        # unchanged, so this handover is not stale, and its snapshot must
        # stay exactly what prepare wrote.
        reg, data = self._registry()
        for t in data["tasks"]:
            if t["id"] == "T01":
                t["status"] = "closed"
                t["closedAt"] = "2026-07-30T02:00:00Z"
        io.open(reg, "w").write(json.dumps(data, indent=2))

        code, text, _ = self.handover("show", doss, "--json")
        self.assertEqual(code, 0, text)
        after = json.loads(text[text.index("{"):])
        self.assertFalse(after["stale"], "HEAD did not move; this handover is not stale")
        self.assertIn("T01", {t["id"] for t in after["record"]["inFlight"]},
                     "a prepared record is a frozen snapshot: a task closing afterward "
                     "with no new commit must not silently rewrite it")
        self.assertEqual(after["record"], before, "show must return exactly what was "
                                                   "written, never a live re-derivation")

    def test_task_changed_together_with_a_new_commit_does_surface_as_staleness(self):
        """The frozen-snapshot test above holds when HEAD does not move: this
        is its complement. When a task's state changes AS PART OF a new
        commit, the ordinary way a task closure actually reaches a shared
        repository, that drift must surface, through the staleness this
        module already computes fresh at every read rather than a second,
        task-specific delta mechanism."""
        doss = self._change("chg-a", "src/a.py")
        self.commit_all("dossier")
        self._open_record("T01", ["src/a.py"], agent="carol")
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "bob@example.com")
        self.assertEqual(code, 0, text)

        reg, data = self._registry()
        for t in data["tasks"]:
            if t["id"] == "T01":
                t["status"] = "closed"
                t["closedAt"] = "2026-07-30T02:00:00Z"
        io.open(reg, "w").write(json.dumps(data, indent=2))
        io.open(os.path.join(self.repo, "src", "a.py"), "a").write("y = 2\n")
        self.commit_all("closed T01 and moved on")

        code, text, _ = self.handover("show", doss, "--json")
        self.assertEqual(code, 0, text)
        after = json.loads(text[text.index("{"):])
        self.assertTrue(after["stale"], "a task changing alongside a new commit must surface "
                                        "as staleness: %s" % after)


if __name__ == "__main__":
    unittest.main()
