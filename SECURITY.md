# Security

## Reporting a vulnerability

Open a GitHub issue describing the problem and how to reproduce it. If the issue
would expose someone's data by being public, say so in one line without the
details and ask for a private channel first.

## What this software does with your data

BrotherSBE makes no network calls. It has no analytics, no account, and no
server. Everything it writes goes to your vault folder, which you choose with
`BROTHERSBE_VAULT` (default `~/BrotherSBEVault`). You can verify both claims
yourself; the tools are about 834 lines of standard-library Python and shell:

```bash
grep -rnE "urllib|requests|socket|http|curl|wget|subprocess" tools/
```

Two files inside the vault deserve attention:

- `99-System/telemetry/outcomes.jsonl` holds per-session counts (tokens, tool
  calls, duration) plus the basename of the working directory. No file contents,
  no prompts.
- `99-System/telemetry/corrections.jsonl` holds short excerpts **of your own
  messages** that look like corrections, so the weekly review can turn them into
  rules. Secret-shaped substrings (API keys, tokens, `password=`, private keys,
  national-ID and card shapes) are redacted before anything is written, and the
  file is created owner-only (0600). Redaction is best-effort pattern matching,
  not a guarantee. Treat the file as sensitive, keep it out of version control
  (the shipped `memory-template/.gitignore` excludes it), and purge it whenever
  you like:

```bash
python3 tools/sbe_telemetry.py purge-corrections        # shows what is there
python3 tools/sbe_telemetry.py purge-corrections --yes  # deletes it
```

To disable correction capture entirely, remove the `SessionEnd` hook. You lose
the automatic capture half of the learning loop; everything else keeps working.

## The autosave makes no network call either

`tools/sbe_autosave.sh` runs on the PreCompact hook (right before Claude Code
compacts context, which is what happens when you run low on tokens). It snapshots
your entire working tree, including untracked files, into a private git ref
`refs/brothersbe/autosave`, using a throwaway index so your real branch, index,
and working tree are never touched. It runs git **locally only and never pushes**,
so the zero-network property above still holds with autosave enabled. Recover a
snapshot with:

```bash
sh tools/sbe_autosave.sh recover
```

An optional continuous mode (`sbe_autosave.sh tick`, off unless you set
`BROTHERSBE_AUTOSAVE`) also snapshots every N tool calls, for a crash that is not
a compaction. To disable autosave entirely, remove the PreCompact hook.

## The update check makes no network call

`tools/sbe_telemetry.py check-update` runs at session start and tells you when your
installed copy differs from an already-fetched origin, when it has gone stale, and
once when the law itself changed under you. It does this by reading git ref files
directly. It never runs `git`, never opens a socket, and never contacts a server, so
the zero-network property above still holds with the check enabled. The cost of that
choice: it can only see an update that something else already fetched, which is why
it also warns when your copy is simply old.

To disable it, remove the `check-update` line from `tools/sbe_sessionstart.sh`.

## Scope note

This project governs how a Claude Code session behaves. It does not change what
Claude Code itself transmits to Anthropic or your chosen cloud provider. For
that, see Anthropic's own documentation on Claude Code data usage, and choose
your plan accordingly: commercial terms (Team, Enterprise, API, cloud providers)
differ materially from consumer plans.

## Verifying what you installed

This repository is unsigned and has no releases. If your organization requires
pinning, clone at a specific commit and record the hash:

```bash
git -C ~/.claude/skills/brothersbe rev-parse HEAD
```
