#!/usr/bin/env python3
"""Replay docs/book/[0-9][0-9]-*.md against the live tools.

Mirror of evals/replay_guide05.py, generalized from one guide to every
chapter of the book. The book's own front matter (docs/book/00-cover.md)
makes the same claim guide-05 opened with: every terminal block in these
pages is real output, produced by actually running the command, and the
book's own build check re-executes each one and rejects the page if the
tool's live output ever drifts from what is printed here. This harness is
that check, made mechanical instead of asserted by hand.

Block annotation convention (the same one guide-05 uses): a fenced ```bash
block is a command, typed exactly as shown. When the very next fenced block
is bare, meaning its opening fence carries no language tag (``` with nothing
after it, not ```json or ```markdown or ```mermaid or any other tag), that
bare block is the literal stdout the command printed, compared byte for
byte. Any other fenced block in between, of any language, breaks the pairing:
it is not compared, because it is an artifact being shown (a file's
contents, a diagram, a config), not a claim about what a command printed.
The book's chapters need no synthetic-dossier setup the way the guide's
scratch engagement does: the worked estate under docs/book/estate/ is a
real, committed, runnable fixture, so a chapter's bash blocks are executed
directly, with the repository root as the working directory, exactly as a
reader sitting at the repo root would type them.

Each chapter file is replayed as its own independent script (a fresh
process, cwd reset to the repo root), so one chapter's state never leaks
into another's and a chapter can be read, and replayed, on its own.

Run:  python3 evals/replay_book.py            (report; exit 1 if any differ)
      python3 evals/replay_book.py --write    (patch stale blocks in place,
                                                from the live output, so no
                                                maintainer ever hand-types an
                                                expected block)

Wired into evals/run_evals.py as a docs-class eval, so drift fails the gate.
Standard library only, no network; commands run against the repository as
it stands on disk (the worked estate's generated files are gitignored and
regenerated deterministically, so replay never touches anything tracked).
"""
import difflib, io, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOK_DIR = os.path.join(REPO, "docs", "book")
WRITE = "--write" in sys.argv
TIMEOUT_PER_CHAPTER = 60

# One line of live output is repository-state-dependent by design: the status
# and impact tools print the merge-base diff line ("git diff <sha>..HEAD over
# N changed file(s)"), and the sha and the count move with every commit and
# every push. A book page cannot freeze that line without lying the moment the
# repository moves, so the pages that show it say so in prose, and this
# comparison treats exactly that substring, and nothing else, as declared
# volatile. Every other byte of every block is still compared literally.
VOLATILE_LINE = re.compile(
    r"git diff [0-9a-f]{7,40}\.\.HEAD over \d+ changed file\(s\)")

# The first authenticated read of the CI logs (2026-07-31) proved three more
# machine-dependent surfaces inside otherwise-honest excerpts, each masked
# here BY SHAPE and nothing else, so every remaining byte stays compared:
# absolute filesystem paths (the author's /Users/... against a runner's
# /home/runner/...), bare commit hashes of the demo repositories the replay
# itself creates (a commit id folds in dates and identity, so no two
# machines agree), and the unittest verbose id, whose format gained the
# method name in newer interpreters while the floor this project promises
# is 3.9.
VOLATILE_PATH = re.compile(r"/(?:Users|home|private/tmp|tmp|var/folders)/[^\s:;,)'\"]+")
VOLATILE_SHA = re.compile(r"\b[0-9a-f]{12,40}\b")
VOLATILE_TESTID = re.compile(r"\((__main__\.[A-Za-z_][A-Za-z0-9_]*)\.[A-Za-z_][A-Za-z0-9_]*\)")


def stable(text):
    """Mask the declared-volatile shapes before comparison. Idempotent."""
    text = VOLATILE_LINE.sub(
        "git diff <live-base>..HEAD over <live-count> changed file(s)", text)
    text = VOLATILE_PATH.sub("<path>", text)
    text = VOLATILE_SHA.sub("<sha>", text)
    text = VOLATILE_TESTID.sub(r"(\1)", text)
    return text


def chapters():
    return sorted(n for n in os.listdir(BOOK_DIR) if re.match(r"^\d{2}-.*\.md$", n))


def extract_blocks(text):
    """Same fence-walking approach as replay_guide05.py: find every fenced
    block (```lang ... ``` or ````lang ... ```` for fences that themselves
    contain triple backticks), keeping the language tag and the line range
    so a patch can be spliced back in by line number."""
    lines = text.splitlines(keepends=True)
    blocks = []
    i = 0
    while i < len(lines):
        m = re.match(r"^(`{3,})(\w*)\s*$", lines[i])
        if m:
            fence, lang = m.group(1), m.group(2)
            j = i + 1
            content = []
            while j < len(lines) and not re.match(r"^%s\s*$" % re.escape(fence), lines[j]):
                content.append(lines[j])
                j += 1
            blocks.append({"lang": lang, "text": "".join(content), "a": i + 1, "b": j})
            i = j + 1
        else:
            i += 1
    return lines, blocks


def replay_chapter(name):
    """Returns (lines, blocks, compare, fails, patches) for one chapter file.
    compare is a list of (block_index, marker) pairs; patches is a list of
    (a, b, got) ready to splice into lines if --write is set."""
    path = os.path.join(BOOK_DIR, name)
    lines, blocks = extract_blocks(io.open(path, encoding="utf-8").read())

    script = ["#!/bin/bash", "cd %s" % REPO]
    compare, marker, prev_bash = [], 0, None
    for i, blk in enumerate(blocks):
        lang, text = blk["lang"], blk["text"]
        if lang == "bash":
            marker += 1
            script.append('echo "===MARK %d START==="' % marker)
            script.append(text.rstrip("\n"))
            script.append('echo "===MARK %d END==="' % marker)
            prev_bash = marker
            continue
        if lang == "":
            if prev_bash is not None:
                compare.append((i, prev_bash))
            prev_bash = None
            continue
        # Any other tagged block (markdown, json, mermaid, python, ...) is
        # an artifact being shown, not a command's output: it breaks the
        # pairing without itself being run or compared.
        prev_bash = None

    if marker == 0:
        return lines, blocks, [], 0, []

    sh_path = os.path.join(BOOK_DIR, ".replay-%s.sh" % name.replace("/", "_"))
    io.open(sh_path, "w").write("\n".join(script) + "\n")
    try:
        out = subprocess.run(["bash", sh_path], capture_output=True, text=True,
                             timeout=TIMEOUT_PER_CHAPTER, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        print("%s: the replay did not finish within %ds; a harness that hangs proves nothing"
              % (name, TIMEOUT_PER_CHAPTER))
        return lines, blocks, compare, len(compare), []
    finally:
        os.remove(sh_path)

    caps = {int(m.group(1)): m.group(2) for m in
            re.finditer(r"===MARK (\d+) START===\n(.*?)===MARK \1 END===\n", out.stdout, re.S)}

    fails, patches = 0, []
    for i, mk in compare:
        want, got = blocks[i]["text"], caps.get(mk, "<NO CAPTURE>")
        if stable(want) != stable(got):
            fails += 1
            print("=== %s BLOCK %d (lines %d-%d) DIFFERS ===" % (name, i, blocks[i]["a"], blocks[i]["b"]))
            for line in difflib.unified_diff(want.splitlines(), got.splitlines(),
                                             "book", "live", lineterm="", n=1):
                print(line)
            patches.append((blocks[i]["a"], blocks[i]["b"], got))
            print()
    return lines, blocks, compare, fails, patches


def main():
    total_compared, total_fails = 0, 0
    for name in chapters():
        lines, blocks, compare, fails, patches = replay_chapter(name)
        total_compared += len(compare)
        total_fails += fails
        if WRITE and patches:
            for a, b, got in sorted(patches, reverse=True):
                lines[a:b] = [l if l.endswith("\n") else l + "\n" for l in got.splitlines(True)]
            path = os.path.join(BOOK_DIR, name)
            io.open(path, "w", encoding="utf-8").write("".join(lines))
            print("%s: patched %d block(s) in place from live output" % (name, len(patches)))
    print("compared %d output blocks, %d differ" % (total_compared, total_fails))
    return 1 if (total_fails and not WRITE) else 0


if __name__ == "__main__":
    sys.exit(main())
