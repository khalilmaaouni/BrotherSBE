import io
import json
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestInstallScript(unittest.TestCase):
    def _run(self, *argv, **kw):
        env = dict(os.environ)
        env.update(kw.get("env", {}))
        out = subprocess.run(["sh", os.path.join(ROOT, "install.sh")] + list(argv),
                             capture_output=True, text=True, env=env, timeout=120)
        return out.returncode, out.stdout, out.stderr

    def test_dry_run_names_every_step_and_writes_nothing(self):
        before = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                capture_output=True, text=True).stdout
        code, stdout, _ = self._run("--dry-run")
        after = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True).stdout
        self.assertEqual(code, 0, stdout)
        self.assertEqual(before, after, "dry-run changed the tree")
        for step in ("git", "python3", "claude", "team profile", "doctor"):
            self.assertIn(step, stdout)

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
