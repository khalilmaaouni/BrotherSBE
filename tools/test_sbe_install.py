import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve(path):
    """The same resolution install.sh itself performs for an EXPLICIT
    --target (`cd "$path" && pwd`, run from whatever directory the script's
    own process already sits in), so a test comparing against install.sh's
    printed target is comparing like with like rather than a raw tempfile
    path against a symlink-resolved one (macOS routes /var through
    /private/var, so the two are not always textually equal)."""
    out = subprocess.run(["sh", "-c", 'cd "$1" && pwd', "sh", path],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def _resolve_as_process_cwd(path):
    """What `pwd` gives a BRAND NEW process whose own working directory was
    set to `path` before it started (Python's subprocess `cwd=`, standing in
    for a person literally running `cd path && sh install.sh`). This can
    differ from `_resolve()` above: a fresh process's starting `$PWD` comes
    from the OS's own getcwd(), which macOS already resolves through the
    /var -> /private/var symlink, while a `cd` issued mid-script onto an
    explicit string does not re-resolve it. install.sh's no-argument path
    (`INVOKED_FROM=$(pwd)`, nothing else has cd'ed yet) hits the first case,
    so this is the helper that scenario's test needs, not `_resolve()`."""
    out = subprocess.run(["sh", "-c", "pwd"], cwd=path,
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


class TestInstallScript(unittest.TestCase):
    def _run(self, *argv, **kw):
        env = dict(os.environ)
        env.update(kw.get("env", {}))
        out = subprocess.run(["sh", os.path.join(ROOT, "install.sh")] + list(argv),
                             capture_output=True, text=True, env=env, timeout=120)
        return out.returncode, out.stdout, out.stderr

    def _stub_bin(self, tmp, *names):
        """A directory holding an executable stub per name, so this test states
        its own preconditions instead of inheriting the machine's. The dry run
        checks for `claude`, which a CI runner does not carry and a developer
        laptop does: asserting exit 0 unconditionally passed here and failed
        there, which is a test measuring the machine rather than the script."""
        for name in names:
            path = os.path.join(tmp, name)
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write("#!/bin/sh\nexit 0\n")
            os.chmod(path, 0o755)
        return tmp + os.pathsep + os.environ.get("PATH", "")

    def _scratch_target(self, tmp, name="project"):
        """A directory that is NOT the BrotherSBE clone, so a dry run against
        it exercises the ordinary path rather than the distribution-directory
        refusal every test in this class used to trip over by accident (any
        invocation with no --target resolves to wherever the test process's
        cwd happens to be, which is ROOT when this file is run the obvious
        way, `python3 tools/test_sbe_install.py` from a checkout)."""
        path = os.path.join(tmp, name)
        os.makedirs(path)
        return path

    def test_dry_run_names_every_step_and_writes_nothing(self):
        before = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                capture_output=True, text=True).stdout
        tmp = tempfile.mkdtemp()
        try:
            scratch = self._scratch_target(tmp)
            code, stdout, _ = self._run(
                "--dry-run", "--target", scratch,
                env={"PATH": self._stub_bin(tmp, "claude")})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        after = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True).stdout
        self.assertEqual(code, 0, stdout)
        self.assertEqual(before, after, "dry-run changed the tree")
        for step in ("git", "python3", "claude", "team profile", "doctor"):
            self.assertIn(step, stdout)

    def test_a_dry_run_without_the_claude_cli_refuses_by_name(self):
        """The other half of the pair above, and the behaviour a CI runner
        actually meets: with no `claude` on PATH the dry run refuses, names
        which prerequisite is missing, and says how to fix it. Proven here
        rather than left to whichever machine happens to run the suite."""
        tmp = tempfile.mkdtemp()
        try:
            scratch = self._scratch_target(tmp)
            self._stub_bin(tmp, "git", "python3")
            # tmp plus the system directories ONLY: appending the caller's PATH
            # would hand the script the real `claude` on a developer laptop and
            # the assertion would measure the machine again, which is the exact
            # defect this pair exists to close.
            code, stdout, _ = self._run(
                "--dry-run", "--target", scratch,
                env={"PATH": tmp + os.pathsep + "/usr/bin:/bin"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(code, 1, stdout)
        self.assertIn("MISSING claude", stdout)

    def test_a_missing_prerequisite_is_named_with_its_remedy(self):
        tmp = tempfile.mkdtemp()
        try:
            scratch = self._scratch_target(tmp)
            code, stdout, _ = self._run(
                "--dry-run", "--target", scratch,
                env={"PATH": "/usr/bin:/bin", "SBE_INSTALL_REQUIRE": "definitely-absent-tool"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(code, 1)
        self.assertIn("MISSING definitely-absent-tool", stdout)

    def test_the_team_profile_parses_and_names_its_keys(self):
        with io.open(os.path.join(ROOT, ".sbe", "team-profile.json"),
                     encoding="utf-8") as fh:
            profile = json.load(fh)
        for key in ("dossierRoot", "vaultPathPattern", "ci", "codeGuideDepth",
                    "schemaVersion"):
            self.assertIn(key, profile)

    # -- DEFECT 1: install.sh must never initialize the BrotherSBE clone
    #    itself when it is not told to on purpose. ------------------------

    def test_dry_run_with_no_target_resolves_to_the_invoking_directory(self):
        """No --target: the resolved target is wherever install.sh was
        invoked FROM (captured as INVOKED_FROM before any cd), not this
        script's own location. Run from a scratch directory rather than
        ROOT so the assertion is about invocation-directory resolution, not
        entangled with the distribution-directory refusal proven below."""
        tmp = tempfile.mkdtemp()
        try:
            scratch = self._scratch_target(tmp)
            expected = _resolve_as_process_cwd(scratch)
            env = dict(os.environ)
            env["PATH"] = self._stub_bin(tmp, "claude")
            out = subprocess.run(["sh", os.path.join(ROOT, "install.sh"), "--dry-run"],
                                 capture_output=True, text=True, env=env, cwd=scratch,
                                 timeout=120)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("resolved target: %s" % expected, out.stdout)

    def test_the_distribution_directory_is_refused_without_developer_self_test(self):
        code, stdout, _ = self._run("--dry-run", "--target", ROOT)
        self.assertEqual(code, 1, stdout)
        self.assertIn("REFUSED", stdout)
        self.assertIn(_resolve(ROOT), stdout)
        self.assertIn("--developer-self-test", stdout)

    def test_the_distribution_directory_refusal_is_bypassed_with_developer_self_test(self):
        before = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                capture_output=True, text=True).stdout
        tmp = tempfile.mkdtemp()
        try:
            code, stdout, _ = self._run(
                "--dry-run", "--target", ROOT, "--developer-self-test",
                env={"PATH": self._stub_bin(tmp, "claude")})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        after = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True).stdout
        self.assertEqual(code, 0, stdout)
        self.assertNotIn("REFUSED", stdout)
        self.assertEqual(before, after, "dry-run changed the tree")

    def test_target_containing_a_space_resolves_correctly(self):
        # Stubbed `claude` for the same reason the every-step test above stubs
        # it: this test measures target resolution, not the machine's toolchain,
        # and a CI runner carries no Claude CLI. Without the stub the dry run
        # refuses at the prerequisite step and exit 0 here measured the machine.
        tmp = tempfile.mkdtemp()
        try:
            scratch = self._scratch_target(tmp, name="my project name")
            expected = _resolve(scratch)
            code, stdout, _ = self._run(
                "--dry-run", "--target", scratch,
                env={"PATH": self._stub_bin(tmp, "claude")})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(code, 0, stdout)
        self.assertIn("resolved target: %s" % expected, stdout)

    def test_target_containing_non_ascii_characters_resolves_correctly(self):
        # Same stub, same reason as the space test above.
        tmp = tempfile.mkdtemp()
        try:
            scratch = self._scratch_target(tmp, name=u"projet-café-安装")
            expected = _resolve(scratch)
            code, stdout, _ = self._run(
                "--dry-run", "--target", scratch,
                env={"PATH": self._stub_bin(tmp, "claude")})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(code, 0, stdout)
        self.assertIn("resolved target: %s" % expected, stdout)

    def test_script_dir_containing_a_space_resolves_correctly(self):
        """The SCRIPT_DIR side of the space coverage the target-side test
        above already has: a full copy of the distribution living at a path
        with a space in it must still find its own `.claude-plugin/plugin.json`
        (install_plugin() reads it unconditionally, even under --dry-run,
        before the dry-run check inside that function) and report a clean,
        no-op dry run from there. Copies the whole tree rather than just
        install.sh because that unconditional read, plus the team-profile
        fallback apply_team_profile() documents (`.sbe/team-profile.json`
        "from $TARGET when it carries one, otherwise this installation's own
        copy at $SCRIPT_DIR"), means SCRIPT_DIR has to be a real distribution,
        not a single relocated script."""
        tmp = tempfile.mkdtemp()
        try:
            dist = os.path.join(tmp, "brother sbe dist")
            shutil.copytree(ROOT, dist, ignore=shutil.ignore_patterns(".git"))
            scratch = self._scratch_target(tmp, name="project")
            expected = _resolve(scratch)
            env = dict(os.environ)
            env["PATH"] = self._stub_bin(tmp, "claude")
            out = subprocess.run(
                ["sh", os.path.join(dist, "install.sh"), "--dry-run", "--target", scratch],
                capture_output=True, text=True, env=env, timeout=120)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("resolved target: %s" % expected, out.stdout)
        for step in ("git", "python3", "claude", "team profile", "doctor"):
            self.assertIn(step, out.stdout)

    def test_a_missing_target_directory_is_named_with_its_remedy(self):
        tmp = tempfile.mkdtemp()
        try:
            missing = os.path.join(tmp, "does-not-exist")
            code, stdout, _ = self._run("--dry-run", "--target", missing)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(code, 2, stdout)
        self.assertIn("MISSING target", stdout)
        self.assertIn(missing, stdout)


#: A fence line in exactly the shape STATE.template.md prescribes, and exactly
#: the shape tools/test_sbe_fence_hook.py's own FENCE_LINE uses, copied rather
#: than imported so this file stays runnable standalone the same way every
#: other file in tools/ is. TTL is a real future date, because the hook reads
#: the SAME liveness rule (tools/sbe_score.py's _is_live_fence) a stale TTL
#: here would fail, silently turning the "denied" half of the hook-firing
#: test below into an unintended "allowed".
_FENCE_OWNER_SESSION = "owner-session-1111-2222"
_FENCE_LINE = (
    "- agent: doc-writer (sole writer, session %s) | tier T1 | TTL 2026-12-31 |\n"
    "  objective: rewrite the setup guide |\n"
    "  files: docs/SETUP.md, tools/sbe_gate.py |\n"
    "  output: one commit |\n" % _FENCE_OWNER_SESSION)
_FENCE_REGISTRY_BODY = (
    "# STATE\n\n"
    "## Fence registry\n\n"
    + _FENCE_LINE +
    "\n## Decisions\n"
)


class TestSandboxedRealInstall(unittest.TestCase):
    """CR-03's remaining real-install gaps, closed against a SANDBOXED real
    (non-dry-run) `install.sh`: install proof grading the TARGET (DEFECT 3,
    install.sh's own `run_doctor`), the plugin-activation handoff to `claude`
    actually happening in order, and the installed layout's own hooks.json
    actually firing the fence hook as a subprocess.

    Every test here runs install.sh for real, which means install_plugin()
    runs too and would otherwise reach the network (`git ls-remote` on every
    real run, per install.sh:174, then either `git clone` or `git -C ... pull`).
    Sandboxed with the two levers install.sh exposes and nothing else: a
    stubbed `claude` (never a real Claude Code session; records its own
    argv so the ACTIVATION HANDOFF can be checked without faking one) and a
    `git` that answers the network-touching subcommands locally and execs the
    real `git` for everything else, so bin/sbe doctor's own `git rev-parse`
    and `git config` calls, run against $TARGET, are answered for real. HOME
    is overridden into this test's own tempdir so the clone-fallback
    destination (`$HOME/.claude/skills/brothersbe`) never touches a real
    machine's actual ~/.claude/skills."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- sandbox construction -------------------------------------------

    def _stub_claude(self, bindir, log_path):
        """Records every invocation as one block of newline-separated argv
        items terminated by a `--END--` marker line, rather than a single
        space-joined line, so a future argument containing a space cannot be
        misread as two arguments."""
        path = os.path.join(bindir, "claude")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$@\" >> \"$SBE_TEST_CLAUDE_LOG\"\n"
                "printf -- '--END--\\n' >> \"$SBE_TEST_CLAUDE_LOG\"\n"
                "exit 0\n")
        os.chmod(path, 0o755)
        return log_path

    def _stub_git(self, bindir, real_git, clone_source):
        """Answers install.sh's three network-touching calls locally:
        `ls-remote` empty (no tag published, so install.sh takes the clone
        fallback rather than the marketplace-direct branch), `clone` as a
        real local recursive copy of `clone_source` into the requested
        destination (so the destination ends up a genuine installed layout,
        with hooks/hooks.json and everything else, for the hook-firing test
        to run against), and `-C ... pull` as a no-op (the already-cloned
        update path, unreached in a single fresh run). Every other
        subcommand execs the REAL git binary, so the git calls install.sh
        itself does NOT make -- bin/sbe doctor's own `git rev-parse` and
        `git config`, run against $TARGET -- are answered for real."""
        path = os.path.join(bindir, "git")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(
                "#!/bin/sh\n"
                "case \"$1\" in\n"
                "    ls-remote)\n"
                "        exit 0\n"
                "        ;;\n"
                "    clone)\n"
                "        dest=$3\n"
                "        mkdir -p \"$dest\"\n"
                "        cp -R \"$SBE_TEST_GIT_CLONE_SOURCE\"/. \"$dest\"/\n"
                "        rm -rf \"$dest/.git\"\n"
                "        exit 0\n"
                "        ;;\n"
                "    -C)\n"
                "        exit 0\n"
                "        ;;\n"
                "    *)\n"
                "        exec \"%s\" \"$@\"\n"
                "        ;;\n"
                "esac\n" % real_git)
        os.chmod(path, 0o755)

    def _sandbox(self):
        bindir = os.path.join(self.tmp, "bin")
        os.makedirs(bindir)
        home = os.path.join(self.tmp, "home")
        os.makedirs(home)
        claude_log = os.path.join(self.tmp, "claude.log")
        real_git = shutil.which("git", path="/usr/bin:/bin") or shutil.which("git")
        self.assertIsNotNone(real_git, "this test needs a real git reachable to pass "
                             "through the calls the stub does not answer itself")
        self._stub_claude(bindir, claude_log)
        self._stub_git(bindir, real_git, ROOT)
        return bindir, home, claude_log

    def _scratch_target(self, name="project", email="target-doctor-check@fixture.test",
                        username="Target Doctor Check"):
        target = os.path.join(self.tmp, name)
        os.makedirs(target)
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)
        subprocess.run(["git", "config", "user.email", email], cwd=target, check=True)
        subprocess.run(["git", "config", "user.name", username], cwd=target, check=True)
        return target

    def _real_install(self, target):
        """A real (non-dry-run) install.sh, fully sandboxed: no network
        reachable, nothing written outside self.tmp or the sandboxed HOME.
        Returns (returncode, stdout, stderr, claude_log_path, clone_dest)."""
        bindir, home, claude_log = self._sandbox()
        env = dict(os.environ)
        for stray in ("SBE_INSTALL_REQUIRE",):
            env.pop(stray, None)
        env["PATH"] = bindir + os.pathsep + "/usr/bin:/bin"
        env["HOME"] = home
        env["SBE_TEST_CLAUDE_LOG"] = claude_log
        env["SBE_TEST_GIT_CLONE_SOURCE"] = ROOT
        out = subprocess.run(["sh", os.path.join(ROOT, "install.sh"), "--target", target],
                             capture_output=True, text=True, env=env, timeout=180)
        clone_dest = os.path.join(home, ".claude", "skills", "brothersbe")
        return out.returncode, out.stdout, out.stderr, claude_log, clone_dest

    def _claude_invocations(self, claude_log):
        if not os.path.exists(claude_log):
            return []
        with io.open(claude_log, encoding="utf-8") as fh:
            text = fh.read()
        return [b.splitlines() for b in text.split("--END--\n") if b.strip()]

    def _repo_status(self):
        return subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                              capture_output=True, text=True).stdout

    # -- item 1: install proof grades the TARGET, never this clone ------

    def test_install_proof_grades_the_target_not_this_clone(self):
        before = self._repo_status()
        target = self._scratch_target()
        code, stdout, stderr, _, _ = self._real_install(target)
        after = self._repo_status()
        self.assertEqual(code, 0, stdout + stderr)
        self.assertEqual(before, after, "a real install must never change this clone's own tree")
        self.assertIn(
            "git config reports name \"Target Doctor Check\" and email "
            "\"target-doctor-check@fixture.test\"", stdout,
            "the doctor step must describe the TARGET's own git identity, "
            "not this clone's: %s" % stdout)
        self.assertIn(
            "install: PASS, sbe doctor agrees (graded %s)" % _resolve(target), stdout,
            "the closing line must name what was graded: %s" % stdout)
        self.assertIn(
            "all present in %s/tools" % ROOT, stdout,
            "tool presence must still resolve against this installation's own tools/, "
            "not the target, even while the doctor's other checks describe the "
            "target: %s" % stdout)

    # -- item 4: plugin activation is a real handoff to `claude`, in order --

    def test_plugin_activation_invokes_claude_marketplace_add_then_install(self):
        before = self._repo_status()
        target = self._scratch_target(name="activation-project")
        code, stdout, stderr, claude_log, clone_dest = self._real_install(target)
        after = self._repo_status()
        self.assertEqual(code, 0, stdout + stderr)
        self.assertEqual(before, after, "a real install must never change this clone's own tree")
        invocations = self._claude_invocations(claude_log)
        self.assertEqual(len(invocations), 2,
                         "expected exactly two claude invocations, in order: %s" % invocations)
        self.assertEqual(invocations[0], ["plugin", "marketplace", "add", clone_dest],
                         invocations)
        self.assertEqual(invocations[1], ["plugin", "install", "brothersbe@brothersbe"],
                         invocations)

    # -- item 2: the installed layout's own hooks.json fires the fence hook -

    def _run_installed_pretooluse_hook(self, clone_dest, payload):
        hooks_path = os.path.join(clone_dest, "hooks", "hooks.json")
        with io.open(hooks_path, encoding="utf-8") as fh:
            hooks = json.load(fh)
        # The FENCE hook specifically, by name. This used to take whichever
        # command came last, which was the fence hook only for as long as it
        # was the last PreToolUse entry in the file. BR-1014 added a Bash
        # matcher after it, and "the last one" silently became a guard that
        # ignores Write payloads, so this replayed the fence contract against
        # a tool that never sees it and read the empty allow as a broken hook.
        command = None
        for entry in hooks["hooks"]["PreToolUse"]:
            for h in entry.get("hooks", []):
                if h.get("type") == "command" and "sbe_fence_hook.py" in h.get("command", ""):
                    command = h["command"]
        self.assertIsNotNone(command,
                             "no PreToolUse hook running sbe_fence_hook.py in the installed "
                             "hooks.json")
        self.assertIn(
            "${CLAUDE_PLUGIN_ROOT}", command,
            "the installed hooks.json must still carry the plugin-root placeholder for "
            "this test to prove the substitution rather than a hardcoded path: %s" % command)
        env = dict(os.environ)
        for stray in ("BROTHERSBE_REGISTRIES", "BROTHERSBE_FENCE_SESSION",
                      "BROTHERSBE_FENCE_HOOK_OFF"):
            env.pop(stray, None)
        env["CLAUDE_PLUGIN_ROOT"] = clone_dest
        return subprocess.run(["sh", "-c", command], input=json.dumps(payload),
                              capture_output=True, text=True, timeout=60, env=env)

    def test_installed_layout_hook_firing(self):
        _, _, _, _, clone_dest = self._real_install(self._scratch_target(name="hook-source"))
        self.assertTrue(os.path.exists(os.path.join(clone_dest, "hooks", "hooks.json")),
                        "the installed layout must carry hooks/hooks.json")

        project = os.path.join(self.tmp, "hook-project")
        os.makedirs(os.path.join(project, "docs"))
        with io.open(os.path.join(project, "docs", "SETUP.md"), "w", encoding="utf-8") as fh:
            fh.write("setup\n")
        with io.open(os.path.join(project, "README.md"), "w", encoding="utf-8") as fh:
            fh.write("readme\n")
        with io.open(os.path.join(project, "STATE.md"), "w", encoding="utf-8") as fh:
            fh.write(_FENCE_REGISTRY_BODY)

        fenced_payload = {"tool_name": "Write",
                          "tool_input": {"file_path": os.path.join(project, "docs", "SETUP.md"),
                                        "content": "x"},
                          "session_id": "intruder-session-3333-4444",
                          "cwd": project, "project_dir": project}
        r = self._run_installed_pretooluse_hook(clone_dest, fenced_payload)
        self.assertEqual(r.returncode, 0, r.stderr)
        obj = json.loads(r.stdout)
        out = obj["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny",
                         "a payload naming a file another session's live fence owns must "
                         "be denied: %s" % r.stdout)

        unowned_payload = dict(fenced_payload)
        unowned_payload["tool_input"] = {"file_path": os.path.join(project, "README.md"),
                                         "content": "x"}
        r2 = self._run_installed_pretooluse_hook(clone_dest, unowned_payload)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(r2.stdout, "",
                         "a file no fence line claims must be a silent allow: %s" % r2.stdout)

    def test_installed_layout_wires_the_bash_and_stop_write_boundary(self):
        """BR-1014's two new hook paths survive installation.

        This is a WIRING assertion, not a behavioral one: it proves the
        installed hooks.json names the Bash matcher and the Stop event and
        that both scripts arrived, which is what an upgrade or a rollback can
        silently break. Exercising the whole flow through a real Claude Code
        plugin load is spec fixture 13 and is run locally at release; this
        does not claim to be that."""
        _, _, _, _, clone_dest = self._real_install(self._scratch_target(name="boundary"))
        with io.open(os.path.join(clone_dest, "hooks", "hooks.json"), encoding="utf-8") as fh:
            hooks = json.load(fh)
        bash_commands = [h.get("command", "")
                         for entry in hooks["hooks"]["PreToolUse"]
                         if "Bash" in (entry.get("matcher") or "")
                         for h in entry.get("hooks", [])]
        self.assertTrue(any("sbe_bash_write_guard.py" in c for c in bash_commands),
                        "no PreToolUse hook matches Bash: %s" % bash_commands)
        stop_commands = [h.get("command", "")
                         for entry in hooks["hooks"].get("Stop", [])
                         for h in entry.get("hooks", [])]
        self.assertTrue(any("sbe_session_reconcile.py" in c for c in stop_commands),
                        "no Stop hook runs the reconciler: %s" % stop_commands)
        for rel in ("tools/sbe_bash_write_guard.py", "tools/sbe_session_reconcile.py",
                    "tools/sbe_session_baseline.py"):
            self.assertTrue(os.path.exists(os.path.join(clone_dest, rel)),
                            "%s did not survive installation" % rel)


class TestTeamProfileApplication(unittest.TestCase):
    """DEFECT 2: `.sbe/team-profile.json` must actually reach the generated
    config, an unsupported field must be rejected by name rather than
    dropped, and the whole thing must stay idempotent. Exercised through
    `bin/sbe init` directly (never through install.sh's own --apply, which
    also runs install_plugin and can reach the network) against scratch git
    repositories created fresh per test, never against this product
    checkout."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _scratch_repo(self, name="repo"):
        path = os.path.join(self.tmp, name)
        os.makedirs(path)
        subprocess.run(["git", "init", "-q"], cwd=path, check=True)
        return path

    def _sbe(self, *argv):
        out = subprocess.run(["python3", os.path.join(ROOT, "bin", "sbe")] + list(argv),
                             capture_output=True, text=True, timeout=60)
        return out.returncode, out.stdout, out.stderr

    def _sbe_json(self, *argv):
        code, out, err = self._sbe(*argv)
        data = None
        if out.strip():
            try:
                data = json.loads(out)
            except ValueError:
                data = None
        return code, data, out + err

    def test_apply_installs_into_a_separate_scratch_repository_only(self):
        target = self._scratch_repo()
        before = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                capture_output=True, text=True).stdout
        code, data, text = self._sbe_json("init", target, "--apply", "--json")
        after = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True).stdout
        self.assertEqual(code, 0, text)
        self.assertEqual(before, after, "sbe init --apply changed the product checkout")
        self.assertTrue(os.path.exists(os.path.join(target, ".brothersbe", "config.json")), text)

    def test_profile_values_actually_appear_in_the_generated_config(self):
        target = self._scratch_repo()
        with io.open(os.path.join(ROOT, ".sbe", "team-profile.json"), encoding="utf-8") as fh:
            profile = json.load(fh)
        code, data, text = self._sbe_json("init", target, "--apply", "--json")
        self.assertEqual(code, 0, text)
        with io.open(os.path.join(target, ".brothersbe", "config.json"), encoding="utf-8") as fh:
            config = json.load(fh)
        for key in ("dossierRoot", "vaultPathPattern", "ci", "codeGuideDepth", "schemaVersion"):
            self.assertEqual(config[key], profile[key],
                             "config.json[%r] does not carry the team profile value: %s"
                             % (key, text))
        self.assertEqual(data["teamProfile"]["source"], "distribution", text)

    def test_a_target_owned_profile_overrides_the_distribution_copy(self):
        target = self._scratch_repo()
        os.makedirs(os.path.join(target, ".sbe"))
        with io.open(os.path.join(target, ".sbe", "team-profile.json"), "w",
                     encoding="utf-8") as fh:
            json.dump({"dossierRoot": "docs/design", "vaultPathPattern": "~/Other",
                      "ci": "consumer", "codeGuideDepth": "maintainer",
                      "schemaVersion": "1.0"}, fh)
        code, data, text = self._sbe_json("init", target, "--apply", "--json")
        self.assertEqual(code, 0, text)
        self.assertEqual(data["teamProfile"]["source"], "target repository", text)
        with io.open(os.path.join(target, ".brothersbe", "config.json"), encoding="utf-8") as fh:
            config = json.load(fh)
        self.assertEqual(config["dossierRoot"], "docs/design", text)
        self.assertEqual(config["vaultPathPattern"], "~/Other", text)

    def test_a_non_default_dossier_root_creates_the_matching_directory_and_receipt(self):
        """Regression test: a profile naming a dossierRoot other than
        "design" used to still create design/.gitkeep (the module-level
        DOSSIER_MARKER constant, hardcoded, ignoring the profile) while
        config.json claimed the profile's root, and the receipt's
        uninstallInstructions kept naming design/.gitkeep too, contradicting
        the config the very same run had just written. All three -- the
        config field, the directory actually created, and the receipt --
        must name the SAME resolved root."""
        target = self._scratch_repo()
        os.makedirs(os.path.join(target, ".sbe"))
        with io.open(os.path.join(target, ".sbe", "team-profile.json"), "w",
                     encoding="utf-8") as fh:
            json.dump({"dossierRoot": "blueprints", "vaultPathPattern": "~/X",
                      "ci": "consumer", "codeGuideDepth": "maintainer",
                      "schemaVersion": "1.0"}, fh)
        code, data, text = self._sbe_json("init", target, "--apply", "--json")
        self.assertEqual(code, 0, text)

        with io.open(os.path.join(target, ".brothersbe", "config.json"), encoding="utf-8") as fh:
            config = json.load(fh)
        self.assertEqual(config["dossierRoot"], "blueprints", text)

        self.assertTrue(os.path.exists(os.path.join(target, "blueprints", ".gitkeep")),
                        "config.json names dossierRoot=blueprints but blueprints/.gitkeep "
                        "was not created: %s" % text)
        self.assertFalse(os.path.exists(os.path.join(target, "design")),
                         "the default design/ directory must not appear when the profile "
                         "names a different dossierRoot: %s" % text)

        with io.open(os.path.join(target, ".brothersbe", "install-receipt.json"),
                     encoding="utf-8") as fh:
            receipt = json.load(fh)
        self.assertIn("blueprints/.gitkeep", receipt["writtenPaths"], text)
        self.assertNotIn("design/.gitkeep", receipt["writtenPaths"], text)
        self.assertIn("rm -f blueprints/.gitkeep", receipt["uninstallInstructions"], text)

        # Idempotence still holds for a non-default root: a second --apply
        # is a no-op, the same guarantee the default case already carries.
        code2, data2, text2 = self._sbe_json("init", target, "--apply", "--json")
        self.assertEqual(code2, 0, text2)
        self.assertTrue(data2["skippedAsNoop"], text2)
        self.assertEqual(data2["written"], [], text2)

    def test_an_unsupported_profile_field_is_rejected_by_name(self):
        target = self._scratch_repo()
        os.makedirs(os.path.join(target, ".sbe"))
        with io.open(os.path.join(target, ".sbe", "team-profile.json"), "w",
                     encoding="utf-8") as fh:
            json.dump({"dossierRoot": "design", "schemaVersion": "1.0",
                      "notARealField": "surprise"}, fh)
        code, data, text = self._sbe_json("init", target, "--apply", "--json")
        self.assertEqual(code, 0, text)
        self.assertIn("notARealField", data["teamProfile"]["rejected"], text)
        self.assertNotIn("notARealField", data["teamProfile"]["applied"], text)
        self.assertTrue(any("notARealField" in w for w in data["warnings"]),
                        "the rejection must be surfaced in warnings, not only in "
                        "teamProfile: %s" % text)
        with io.open(os.path.join(target, ".brothersbe", "config.json"), encoding="utf-8") as fh:
            config_text = fh.read()
        self.assertNotIn("notARealField", config_text,
                         "a rejected field must never reach the written config: %s" % text)

    def test_apply_twice_is_idempotent_and_the_second_run_writes_nothing(self):
        target = self._scratch_repo()
        code1, data1, text1 = self._sbe_json("init", target, "--apply", "--json")
        self.assertEqual(code1, 0, text1)
        self.assertFalse(data1["skippedAsNoop"], text1)
        self.assertTrue(data1["written"], text1)

        def snapshot():
            found = {}
            for base, _dirs, files in os.walk(target):
                if os.sep + ".git" in base + os.sep:
                    continue
                for name in files:
                    full = os.path.join(base, name)
                    with io.open(full, "rb") as fh:
                        found[os.path.relpath(full, target)] = fh.read()
            return found

        before = snapshot()
        code2, data2, text2 = self._sbe_json("init", target, "--apply", "--json")
        after = snapshot()
        self.assertEqual(code2, 0, text2)
        self.assertTrue(data2["skippedAsNoop"], text2)
        self.assertEqual(data2["written"], [], text2)
        self.assertEqual(before, after, "a no-op second apply rewrote something on disk")

    def test_refuses_when_target_is_not_a_git_repository(self):
        plain = os.path.join(self.tmp, "plain")
        os.makedirs(plain)
        code, out, err = self._sbe("init", plain, "--apply")
        self.assertNotEqual(code, 0, out + err)
        self.assertIn("git repository", (out + err).lower())

    def test_a_target_path_containing_a_space_installs_correctly(self):
        target = self._scratch_repo(name="my project name")
        code, data, text = self._sbe_json("init", target, "--apply", "--json")
        self.assertEqual(code, 0, text)
        self.assertTrue(os.path.exists(os.path.join(target, ".brothersbe", "config.json")), text)

    def test_a_target_path_containing_non_ascii_characters_installs_correctly(self):
        target = self._scratch_repo(name=u"projet-café-安装")
        code, data, text = self._sbe_json("init", target, "--apply", "--json")
        self.assertEqual(code, 0, text)
        self.assertTrue(os.path.exists(os.path.join(target, ".brothersbe", "config.json")), text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
