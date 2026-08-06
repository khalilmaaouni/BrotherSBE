# Testing BrotherSBE

Thank you for trying this. You are testing a Claude Code plugin that acts as a
senior backend and data engineering colleague: it designs before it builds,
demands evidence before "done", and shows you one recommended next action at a
time. Your job as a tester is to use it on something real and tell us where it
confused you, slowed you down, or claimed something it should not have.

Time ask: about 30 to 60 minutes for the guided path below. Anything beyond
that is welcome but entirely optional.

## Supported platforms

- macOS and Linux: supported, and every merge to this repository runs the full
  gate battery on both.
- Windows: experimental. The Windows CI leg exists and most of the battery
  passes there, but one known failure is still open (tracked as owed item
  OWED-4 in `program/OWED.json`). If you are on Windows, we still want your
  report; expect rough edges.

You need: `git`, Python 3.9 or newer, and the
[Claude Code CLI](https://claude.com/claude-code) (`claude`) on your PATH.

## Install, two commands

```bash
claude plugin marketplace add khalilmaaouni/BrotherSBE
```

```bash
claude plugin install brothersbe@brothersbe
```

Prefer to inspect before you trust? The [README](README.md) documents the
clone-and-validate path with `claude plugin validate`; both routes end at the
same place. Check your install any time with:

```bash
python3 bin/sbe doctor
```

Uninstall cleanly with `claude plugin uninstall brothersbe`.

## Your first governed change, in about ten minutes

Open Claude Code in any project (or an empty folder) and type:

```
/brothersbe:start
```

Follow what it recommends. If you would rather walk a prepared example first,
the [sandbox guide](docs/guides/00-sandbox.md) takes you through one complete
governed change, from idea to reviewed and proven, on a throwaway repository
it builds for you. Every output block in that guide is captured from live runs
and held to it by tests.

## The structured protocol

[TEST-PROTOCOL.md](TEST-PROTOCOL.md) carries the numbered version of all of
this: a 30 minute guided run with expected outcomes and time estimates, a red
team track of ten attempts that should each be blocked, and the current
assurance limits stated plainly. Use it if you like structure. The looser
suggestions below work too.

## What to try (pick what matches how you work)

- The guided path: `/brothersbe:start`, then keep following
  `/brothersbe:next`. Does the one recommended action ever feel wrong, stale,
  or confusing? That is exactly the report we want.
- A real change in your own repository: let it size the work, write the design
  artifacts its tier asks for, and hold you to the gates. Did the ceremony
  match the size of the change?
- Break it: claim something is done without evidence, delete a file it
  generated, run it in a repository with a mess in progress. It should refuse,
  explain, or say NO-DATA plainly. A confident wrong answer is a bug we treat
  as serious.
- Read `docs/explainer/index.html` (open it in a browser) if you are newer to
  this kind of tooling, and tell us where the plain-language explanation stops
  being plain.

## Where to report

Open a GitHub issue with the tester report template:
[new issue](https://github.com/khalilmaaouni/BrotherSBE/issues/new?template=tester-report.md).
One issue per finding beats one giant issue. Include your OS, Python version,
and what you expected against what happened. The template asks for exactly
that and nothing more.

If something refuses to run at all, the output of `python3 bin/sbe doctor`
pasted into the issue saves a whole round trip.

## What is not finished yet

Being honest about limits is the product's whole point, so here they are.
Evidence produced in CI is labeled CI-CLAIMED, which means CI shaped metadata
was recorded but no protected identity was verified; cryptographic
attestation is the next fix. The repository has one human today, so
CODEOWNERS is real but a genuine second-party approval is not yet possible.
The end to end host check runs locally at release rather than on every merge.
Windows has one known failing check. The marketplace install path has no
rollback command yet. [TEST-PROTOCOL.md](TEST-PROTOCOL.md) explains each one.

## What happens with your feedback

Every report lands in the program ledger and is triaged against the roadmap in
`program/MASTER-PLAN-2026-08-06.md`. Fixes ship as normal governed changes,
gates and all. Findings from unfamiliar users are the single most valuable
input this project has right now: the whole point of the tool is that someone
who has never seen it can complete a governed change without reading internal
documentation, and only you can tell us whether that promise holds.
