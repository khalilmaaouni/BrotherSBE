# Security

## Reporting a vulnerability

Open a GitHub issue describing the problem and how to reproduce it. If the issue
would expose someone's data by being public, say so in one line without the
details and ask for a private channel first.

## What this software does with your data

BrotherSBE makes no network calls. It has no analytics, no account, and no
server. Everything it writes goes to your vault folder, which you choose with
`BROTHERSBE_VAULT` (default `~/BrotherSBEVault`). You can verify both claims
yourself; the tools are standard-library Python and shell: 13,923 lines measured
2026-07-29 by `wc -l tools/*.py tools/*.sh`, a figure stated here rather than
left for you to discover, and a test in `tools/test_sbe.py` fails if it drifts
more than 15 percent, so the auditability claim degrades loudly instead of
quietly. This finds every network call:

```bash
grep -rnE "urllib|requests|socket|http|curl|wget|subprocess" tools/
```

What to expect from that grep, so the check is usable rather than reassuring:
none of the hits is a network call. The exact count moves with the code and is
deliberately not stated here (an earlier revision pinned a number and it
rotted); the PROPERTY is what matters, and every hit is one of three benign
shapes: `subprocess` running local `git`, the words "socket" or "http"
inside a refusal message or comment, or a fake credential inside a redaction
TEST FIXTURE (`tools/test_sbe.py` carries a literal `curl ... Bearer ...`
string precisely to prove such strings get masked). A hit that actually
imports `urllib` or `requests`, or opens an `http` URL or a network `socket`,
is a violation of this document; report it. The property itself is
drift-tested: `tools/test_sbe.py` parses every tool and fails if any imports
`urllib`, `requests`, `socket` or `http`, or if a shell tool invokes `curl`
or `wget`.

## Capture is off by default, per category

A default installation captures no transcript text and no correction excerpt.
Nothing is read out of a session transcript until a category that needs it is
switched on, and each category is switched on separately:

| Category | Switch | What turning it on stores |
|---|---|---|
| `metrics` | `BROTHERSBE_TELEMETRY_METRICS=1` | the per-session row in `outcomes.jsonl` |
| `transcript` | `BROTHERSBE_TELEMETRY_TRANSCRIPT=1` | transcript text in the resume brief |
| `corrections` | `BROTHERSBE_TELEMETRY_CORRECTIONS=1` | excerpts of your own messages |

With a category off, the tool says so on the line where it would have reported a
capture, naming the switch. The resume brief is still written with a category
off, and the section that would have held the text says it was withheld and by
which switch, so a resumed session finds a document rather than a missing file.

`metrics` is opt-in as well, even though it stores no message text: the row
carries the basename of the working directory, and a directory basename can be a
client's name.

**The organization override.** Set `BROTHERSBE_TELEMETRY_DISABLE=1`, or put
`capture = off` in `/etc/brothersbe/telemetry-policy.conf` (override the path
with `BROTHERSBE_TELEMETRY_POLICY`). Either one forces every category off and no
local switch can turn one back on. The file is the half a user's own shell
cannot unset, and on a managed machine it lives where an ordinary user cannot
write. A policy file that exists and cannot be read, or that carries a directive
this version does not recognize, fails closed: capture is off and the reason
names the file and the line. Its limit, stated plainly: this is a policy control
on a cooperating machine, not an enforcement boundary. Anyone who can edit that
file, or run a patched copy of the script, is past it.

## Seeing, exporting and deleting what is stored

```bash
python3 tools/sbe_telemetry.py data-show          # every file, its records, its mode
python3 tools/sbe_telemetry.py data-export --out bundle.json   # owner-only copy
python3 tools/sbe_telemetry.py data-purge         # names what would go
python3 tools/sbe_telemetry.py data-purge --yes   # deletes it, then re-checks the disk
```

All three read one inventory, so a file `data-show` lists is a file
`data-export` copies and `data-purge` removes. `data-purge` re-checks the
filesystem after each removal and reports anything that survived, rather than
reporting success from its own intention. `purge-corrections` still exists and
still does only the corrections file:

```bash
python3 tools/sbe_telemetry.py purge-corrections        # shows what is there
python3 tools/sbe_telemetry.py purge-corrections --yes  # deletes it
```

`data-show` reports this vault only. A backup, a mirror or a sync client may
hold copies of any of it, and nothing here can see those.

## Data dictionary

Every field that can be stored, with the switch that has to be on for it to
exist. Everything below lives under `$BROTHERSBE_VAULT/99-System/telemetry/`.

`outcomes.jsonl` (one JSON object per recorded session, category `metrics`):

| Field | What it holds |
|---|---|
| `schema` | ledger schema version, currently 2 |
| `ts` | when the row was written, ISO 8601 UTC |
| `session_id` | the harness's session id |
| `project` | the BASENAME of the working directory, which can be a client name |
| `end_reason` | the reason the harness gave for the session ending |
| `gen_ai.usage.output_tokens` | output tokens summed over the session's messages |
| `gen_ai.usage.input_tokens` | input tokens summed over the session's messages |
| `sub_out_tokens` | output tokens summed over subagent transcripts |
| `cache_write`, `cache_read` | cache creation and cache read input tokens |
| `api_msgs`, `human_msgs` | count of assistant messages, count of operator messages |
| `tool_calls`, `agent_spawns`, `workflow_calls` | counts of tool uses by kind |
| `subagent_files` | how many subagent transcript files were read |
| `models` | the model names the session used |
| `duration_h` | first to last message timestamp, in hours, idle included |
| `token_basis` | always `as-flushed`, because the transcript can lag the last turn |

No message text, no prompt, no file content, and no file path appears in a
metrics row.

`corrections.jsonl` (category `corrections`, owner-only 0600):

| Field | What it holds |
|---|---|
| `ts` | when the excerpt was written |
| `session_id` | the session it came from |
| `project` | the basename of the working directory |
| `text` | up to 400 characters **of your own message**, secret-redacted |
| `redactions` | how many substrings were masked, present only when some were |

At most five excerpts per session, only from operator messages the correction
pattern matched, only from the main transcript.

`last-resume-<project>-<hash>.md` (category `transcript`, owner-only 0600): the
last operator message (600 characters), up to four recent assistant text blocks
(300 characters each), up to ten recent tool descriptors (a command line
truncated to 100 characters, or a file path), and the last write-ahead intent
line. Every one of those is secret-redacted before it is written.

Written by explicit commands rather than by capture: `ratings.jsonl` (the score,
task and note you typed), `reviews.jsonl` (a timestamp and note), and
`intent-<project>-<hash>.log` (the intent lines you typed, one per line).
`installed-skill-version` holds one git sha. `autosave.log` and
`autosave-exclusions.log` hold snapshot events and excluded PATHS with reasons,
never excluded content.

Secret-shaped substrings (API keys, tokens, `password=`, private keys,
national-ID and card shapes) are redacted before anything above is written.
Redaction is best-effort pattern matching, not a guarantee. Keep the vault out
of version control (the shipped `memory-template/.gitignore` excludes it).

To disable capture entirely without touching the switches, remove the
`SessionEnd` hook. You lose the automatic capture half of the learning loop;
everything else keeps working.

## The autosave makes no network call either

`tools/sbe_autosave.sh` runs on the PreCompact hook (right before Claude Code
compacts context, which is what happens when you run low on tokens). It snapshots
your entire working tree, including untracked files, into a private git ref
`refs/brothersbe/autosave/<worktree-id>` (one ref per worktree, so two worktrees
of one repository cannot overwrite each other's snapshots), using a throwaway
index so your real branch, index,
and working tree are never touched. It runs git **locally only and never pushes**,
so the zero-network property above still holds with autosave enabled. Recover a
snapshot with:

```bash
sh tools/sbe_autosave.sh recover
```

An optional continuous mode (`sbe_autosave.sh tick`, off unless you set
`BROTHERSBE_AUTOSAVE`) also snapshots every N tool calls, for a crash that is not
a compaction. To disable autosave entirely, remove the PreCompact hook.

### What the autosave will not put in a git object

A snapshot is a permanent git object, so every candidate file's CONTENT is read
BEFORE `git add` runs, which is the moment a blob would be created. A file is
kept out when its content matches a secret shape, when it is larger than
`BROTHERSBE_AUTOSAVE_MAX_BYTES` (1 MiB by default, so it was never scanned),
when it is binary (this scanner cannot read one for secret shapes), or when its
name is one of the secret-shaped names. Every exclusion is written to
`99-System/telemetry/autosave-exclusions.log` with its reason, as a path and a
reason only, never the matched content. `sbe_autosave.sh recover` points at that
record, because what a snapshot does NOT hold matters at recovery time.

Two statements that belong together. A file name pattern was never a control
over secrets: a credential lives in a normally named source file at least as
often as in a file called `.env`, and this project shipped a version whose
comment claimed otherwise. And the content scan that replaced that claim is
pattern matching too, so a secret in a shape it does not know still enters the
snapshot. An excluded file is left out of the snapshot entirely, so an unsaved
edit to it is preserved nowhere.

In a repository you declare production (`BROTHERSBE_REPO_CLASS=production`, or a
`.brothersbe-production` file at the top of the checkout), autosave is opt-in: it
snapshots nothing until `BROTHERSBE_AUTOSAVE_PRODUCTION=1` is set, and the skip
line names both the marker it read and the switch that would enable it.

`docs/THREAT_MODEL.md` covers this and fourteen other threats, including the
ones nothing here stops.

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

The repository ships a SHA256 manifest (`CHECKSUMS.sha256`, generated by
`scripts/checksums.sh`) and a checker for it:

```bash
cd ~/.claude/skills/brothersbe && scripts/verify-install.sh
```

One expectation to set before you run it: any file YOU created inside the
install is reported as EXTRA and fails the check, including the demo dossier
the README walkthrough creates (`design/my-project`). That is the checker
doing its job, not an intrusion: it cannot tell your scratch file from a
planted one, so it names both. Delete what you created (`rm -rf
design/my-project`) and re-run, and keep real work outside this clone.

It verifies both directions: every file the manifest names matches on disk,
and every file on disk appears in the manifest, so a planted extra file fails
rather than riding along unexamined. What a PASSED does NOT prove: that the
manifest itself is authentic. Take the manifest from the release you trust
(the tag's git history), not from the same channel as the code you are
checking. [docs/RELEASE.md](docs/RELEASE.md) is the cut and pin runbook, and
it states plainly which of its steps have never been executed.

Commits are unsigned. If your organization pins to commits rather than tags,
record the hash yourself:

```bash
git -C ~/.claude/skills/brothersbe rev-parse HEAD
```
