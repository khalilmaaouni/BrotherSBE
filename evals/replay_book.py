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
# Overridable because wall-clock is a fact about the MACHINE, not the book:
# five concurrent sessions starved 4-second chapters past the old fixed cap,
# and a timeout counted as differing blocks that were never compared at all.
TIMEOUT_PER_CHAPTER = int(os.environ.get("SBE_REPLAY_TIMEOUT", "60"))

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
# 3.11 added fine-grained error locations: caret and tilde underline lines
# beneath a traceback frame. The floor is 3.9, whose tracebacks carry none,
# so an underline-only line is interpreter decoration, not content.
VOLATILE_CARETS = re.compile(r"^\s*[\^~]+\s*$", re.M)


def stable(text):
    """Mask the declared-volatile shapes before comparison. Idempotent."""
    text = VOLATILE_LINE.sub(
        "git diff <live-base>..HEAD over <live-count> changed file(s)", text)
    text = VOLATILE_PATH.sub("<path>", text)
    text = VOLATILE_SHA.sub("<sha>", text)
    text = VOLATILE_TESTID.sub(r"(\1)", text)
    text = VOLATILE_CARETS.sub("", text)
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


CAPABILITIES = {
    "claude": ("the Claude Code CLI on PATH",
               lambda: __import__("shutil").which("claude") is not None),
    "vault": ("a wired BrotherSBE vault (BROTHERSBE_VAULT set and present)",
              lambda: bool(os.environ.get("BROTHERSBE_VAULT"))
              and os.path.isdir(os.environ.get("BROTHERSBE_VAULT", ""))),
}

_REQUIRES = re.compile(r"<!--\s*replay:\s*chapter\s+requires\s+([a-z]+)\s*-->")


def _chapter_requirements(text):
    """Capability names the whole chapter declares. Chapter blocks share one
    shell and one state: a skipped setup block would orphan every later
    excerpt built on it, so capability is a property of the CHAPTER."""
    return _REQUIRES.findall(text)


def replay_chapter(name):
    """Returns a dict for one chapter: lines, blocks, compare, fails, patches,
    and the capability-skipped blocks, each named.
    compare is a list of (block_index, marker) pairs; patches is a list of
    (a, b, got) ready to splice into lines if --write is set."""
    path = os.path.join(BOOK_DIR, name)
    lines, blocks = extract_blocks(io.open(path, encoding="utf-8").read())

    # The harness supplies the reader's own preconditions a fresh runner
    # lacks: a git identity (a reader following the book has one configured;
    # a CI runner does not, and without it every scratch commit fails and a
    # downstream gate grades the wrong artifact) and fixed dates, which also
    # make scratch commit ids deterministic across machines.
    script = ["#!/bin/bash", "cd %s" % REPO,
              'export GIT_AUTHOR_NAME="a reader" GIT_AUTHOR_EMAIL="reader@example.invalid"',
              'export GIT_COMMITTER_NAME="a reader" GIT_COMMITTER_EMAIL="reader@example.invalid"',
              'export GIT_AUTHOR_DATE="2026-07-30T00:00:00Z" GIT_COMMITTER_DATE="2026-07-30T00:00:00Z"']
    unmet = [r for r in _chapter_requirements("".join(lines))
             if r in CAPABILITIES and not CAPABILITIES[r][1]()]
    if unmet:
        # A capability this machine lacks: the whole chapter is SKIPPED and
        # COUNTED, never silently, because a comparison that never ran must
        # not read as one that matched, and a half-run chapter would compare
        # excerpts against state their setup never built.
        n_comparable = sum(1 for j, blk2 in enumerate(blocks)
                           if blk2["lang"] == "" and j > 0
                           and blocks[j - 1]["lang"] == "bash")
        return lines, blocks, [], 0, [], [(name, n_comparable, unmet)]

    compare, marker, prev_bash = [], 0, None
    skipped = []
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
        return lines, blocks, [], 0, [], skipped

    sh_path = os.path.join(BOOK_DIR, ".replay-%s.sh" % name.replace("/", "_"))
    io.open(sh_path, "w").write("\n".join(script) + "\n")
    try:
        out = subprocess.run(["bash", sh_path], capture_output=True, text=True,
                             timeout=TIMEOUT_PER_CHAPTER, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        print("%s: the replay did not finish within %ds; a harness that hangs proves nothing"
              % (name, TIMEOUT_PER_CHAPTER))
        return lines, blocks, compare, len(compare), [], skipped
    finally:
        # missing_ok: a concurrent tidy-up sweeping .replay-*.sh litter can
        # win the race to this unlink; the script already ran, so a missing
        # temp is a fact to tolerate, not an error to raise.
        import pathlib
        pathlib.Path(sh_path).unlink(missing_ok=True)

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
    return lines, blocks, compare, fails, patches, skipped


def main():
    total_compared, total_fails = 0, 0
    all_skipped = []
    for name in chapters():
        lines, blocks, compare, fails, patches, skipped = replay_chapter(name)
        all_skipped.extend(skipped)
        total_compared += len(compare)
        total_fails += fails
        if WRITE and patches:
            for a, b, got in sorted(patches, reverse=True):
                lines[a:b] = [l if l.endswith("\n") else l + "\n" for l in got.splitlines(True)]
            path = os.path.join(BOOK_DIR, name)
            io.open(path, "w", encoding="utf-8").write("".join(lines))
            print("%s: patched %d block(s) in place from live output" % (name, len(patches)))
    for name, n_blocks, unmet in all_skipped:
        for cap in unmet:
            print("SKIPPED chapter %s (%d comparable block(s)): requires %s (%s), which "
                  "this machine lacks; comparisons that never ran are counted here, "
                  "never as matches" % (name, n_blocks, cap, CAPABILITIES[cap][0]))
    print("compared %d output blocks, %d differ" % (total_compared, total_fails))
    return 1 if (total_fails and not WRITE) else 0


if __name__ == "__main__":
    sys.exit(main())
