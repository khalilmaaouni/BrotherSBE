import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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

    def test_dry_run_names_every_step_and_writes_nothing(self):
        before = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                capture_output=True, text=True).stdout
        tmp = tempfile.mkdtemp()
        try:
            code, stdout, _ = self._run(
                "--dry-run", env={"PATH": self._stub_bin(tmp, "claude")})
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
            self._stub_bin(tmp, "git", "python3")
            # tmp plus the system directories ONLY: appending the caller's PATH
            # would hand the script the real `claude` on a developer laptop and
            # the assertion would measure the machine again, which is the exact
            # defect this pair exists to close.
            code, stdout, _ = self._run(
                "--dry-run", env={"PATH": tmp + os.pathsep + "/usr/bin:/bin"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(code, 1, stdout)
        self.assertIn("MISSING claude", stdout)

    def test_a_missing_prerequisite_is_named_with_its_remedy(self):
        code, stdout, _ = self._run("--dry-run", env={"PATH": "/usr/bin:/bin",
                                                      "SBE_INSTALL_REQUIRE": "definitely-absent-tool"})
        self.assertEqual(code, 1)
        self.assertIn("MISSING definitely-absent-tool", stdout)

    def test_the_team_profile_parses_and_names_its_keys(self):
        with io.open(os.path.join(ROOT, ".sbe", "team-profile.json"),
                     encoding="utf-8") as fh:
            profile = json.load(fh)
        for key in ("dossierRoot", "vaultPathPattern", "ci", "codeGuideDepth",
                    "schemaVersion"):
            self.assertIn(key, profile)


if __name__ == "__main__":
    unittest.main(verbosity=2)
