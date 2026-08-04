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
        tmp = tempfile.mkdtemp()
        try:
            scratch = self._scratch_target(tmp, name="my project name")
            expected = _resolve(scratch)
            code, stdout, _ = self._run("--dry-run", "--target", scratch)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(code, 0, stdout)
        self.assertIn("resolved target: %s" % expected, stdout)

    def test_target_containing_non_ascii_characters_resolves_correctly(self):
        tmp = tempfile.mkdtemp()
        try:
            scratch = self._scratch_target(tmp, name=u"projet-café-安装")
            expected = _resolve(scratch)
            code, stdout, _ = self._run("--dry-run", "--target", scratch)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(code, 0, stdout)
        self.assertIn("resolved target: %s" % expected, stdout)

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
