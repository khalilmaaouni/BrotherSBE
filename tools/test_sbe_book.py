import io
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESTATE = os.path.join(ROOT, "docs", "book", "estate")


class TestWorkedEstate(unittest.TestCase):
    """The book's example project is real: these are the exact commands the
    chapters paste, so a broken estate is a broken book."""

    def _run(self, *argv):
        out = subprocess.run([sys.executable] + list(argv), capture_output=True,
                             text=True, cwd=ESTATE, timeout=60)
        return out.returncode, out.stdout, out.stderr

    def test_the_pipeline_runs_and_names_its_output(self):
        code, stdout, stderr = self._run("pipeline.py", "--date", "2026-07-01")
        self.assertEqual(code, 0, stderr)
        self.assertIn("wrote 3 rows to daily_totals", stdout)

    def test_the_estate_suite_is_green(self):
        code, stdout, stderr = self._run("test_estate.py")
        self.assertEqual(code, 0, stdout + stderr)
        self.assertIn("Ran 4 tests", stdout + stderr)


class TestBookBuild(unittest.TestCase):
    def test_the_build_produces_one_offline_html_with_every_chapter(self):
        out = subprocess.run([sys.executable,
                              os.path.join(ROOT, "docs", "book", "build_book.py")],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        html_path = os.path.join(ROOT, "docs", "book", "BrotherSBE-for-Dummies.html")
        self.assertTrue(os.path.exists(html_path))
        html = io.open(html_path, encoding="utf-8").read()
        chapters = sorted(n for n in os.listdir(os.path.join(ROOT, "docs", "book"))
                          if n[:2].isdigit() and n.endswith(".md"))
        self.assertGreaterEqual(len(chapters), 12)
        for name in chapters:
            title = io.open(os.path.join(ROOT, "docs", "book", name),
                            encoding="utf-8").readline().lstrip("# ").strip()
            self.assertIn(title, html, "chapter %s missing from the build" % name)
        self.assertIn("mermaid", html)
        self.assertNotIn("src=\"http", html)
        self.assertNotIn("href=\"http", html.split("</nav>")[0])


class TestInlineCodeSpans(unittest.TestCase):
    """A book about precision may not print literal backticks at its reader.

    The converter's first version handled bold and links but not code spans,
    so 191 spans across the chapters would have rendered as raw backticks.
    This fixture is the reason that cannot come back.
    """

    def test_code_spans_become_code_elements_and_leave_no_backticks(self):
        import re
        out = subprocess.run([sys.executable,
                              os.path.join(ROOT, "docs", "book", "build_book.py")],
                             capture_output=True, text=True, timeout=180)
        self.assertEqual(out.returncode, 0, out.stderr)
        html = io.open(os.path.join(ROOT, "docs", "book",
                                    "BrotherSBE-for-Dummies.html"),
                       encoding="utf-8").read()
        body = html.split("</nav>", 1)[-1]
        body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
        body = re.sub(r"<pre.*?</pre>", "", body, flags=re.S)
        self.assertGreater(body.count("<code>"), 100,
                           "the chapters carry many code spans; none rendered")
        self.assertEqual(body.count("`"), 0,
                         "a literal backtick survived into rendered prose")


class TestDeclaredVolatileLine(unittest.TestCase):
    """The replay harness masks exactly one substring: the live merge-base
    diff line the status and impact tools print, which moves with every
    commit. These fixtures pin the mask to that substring and nothing else,
    calibrated both ways: a volatile-only difference must pass, and any
    other difference must still fail. Without the second half, the mask
    could silently widen and eat real drift."""

    def _stable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "replay_book", os.path.join(ROOT, "evals", "replay_book.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.stable

    def test_a_volatile_only_difference_compares_equal(self):
        stable = self._stable()
        book = "clean. git diff 47422a88df57..HEAD over 2 changed file(s)\nrest\n"
        live = "clean. git diff 5be26b2068da..HEAD over 0 changed file(s)\nrest\n"
        self.assertEqual(stable(book), stable(live))

    def test_any_other_difference_still_differs(self):
        stable = self._stable()
        book = "verdict: PASS\ngit diff 47422a88df57..HEAD over 2 changed file(s)\n"
        live = "verdict: NO-DATA\ngit diff 47422a88df57..HEAD over 2 changed file(s)\n"
        self.assertNotEqual(stable(book), stable(live))

    def test_a_pinned_range_is_not_masked(self):
        stable = self._stable()
        pinned = "git diff 47422a88df57..f924538 over 2 changed file(s)\n"
        self.assertEqual(stable(pinned), pinned,
                         "a range pinned to two commits is deterministic and "
                         "must stay byte-compared")


if __name__ == "__main__":
    unittest.main(verbosity=2)
