# Testing BrotherSBE

Thank you for trying this. BrotherSBE is a Claude Code plugin that acts as a
senior backend and data engineering colleague: it designs before it builds,
demands evidence before "done", and shows you one recommended next action at a
time. Your job as a tester is to use it on something real and tell us where it
confused you, slowed you down, or claimed something it should not have.

**You work entirely inside Claude Code.** After the one-time install below,
everything is a slash command or an ordinary sentence to Claude. You never
need a terminal, and if the tool ever forces you into one, that is a finding
worth reporting on its own.

Time ask: about 30 minutes for the guided run. Anything beyond that is welcome
but entirely optional.

## Supported platforms

- macOS and Linux: supported, and every merge to this repository runs the full
  gate battery on both.
- Windows: experimental, with one known failing check. If you are on Windows,
  we still want your report; expect rough edges.

You need [Claude Code](https://claude.com/claude-code) and Python 3.9 or newer
on your machine. Claude Code itself handles the rest.

## Install, once

In your terminal, two commands (this is the only terminal step in the whole
protocol):

```bash
claude plugin marketplace add khalilmaaouni/BrotherSBE
```

```bash
claude plugin install brothersbe@brothersbe
```

Then open Claude Code in any project, or in an empty folder if you would
rather not touch real work. Everything from here happens in that session.

To confirm it loaded, type:

```
/brothersbe:help
```

You should get a plain-language map of what the plugin offers. If that command
is not recognized, restart Claude Code once; if it is still missing, that is
your first issue to file.

## The structured protocol

[TEST-PROTOCOL.md](TEST-PROTOCOL.md) is the numbered version: a 30 minute
guided run with expected outcomes and time estimates, plus a red team track of
ten attempts that should each be refused. Both tracks run inside Claude Code.
Use it if you like structure; the looser suggestions below work too.

## What to try (pick what matches how you work)

- **The guided path.** Type `/brothersbe:start`, then keep following
  `/brothersbe:next`. Does the one recommended action ever feel wrong, stale,
  or confusing?
- **A real change in your own repository.** Open Claude Code where you
  actually work and ask it to make a change you were going to make anyway.
  Let BrotherSBE size the work, ask for the design artifacts its tier
  requires, and hold you to the gates. Did the ceremony match the size of the
  change?
- **Ask for the state in plain words.** Type `/brothersbe:status`, or just ask
  Claude "where does this project stand?". You should get language you would
  use out loud, not internal identifiers.
- **Try to get away with something.** Tell Claude the work is done when no
  check has run. Ask it to skip a step. It should refuse, explain, or say
  NO-DATA plainly. A confident wrong answer is a bug we treat as serious.
- **Read the explainer** at `docs/explainer/index.html` in the repository if
  you are newer to this kind of tooling, and tell us where the plain-language
  explanation stops being plain.

## Where to report

Open a GitHub issue with the tester report template:
[new issue](https://github.com/khalilmaaouni/BrotherSBE/issues/new?template=tester-report.md).
One issue per finding beats one giant issue. Include your OS, what you asked
for, what you expected, and what happened.

If something is broken in a way you cannot describe, ask Claude in that same
session to run `/brothersbe:status` and paste what it says into the issue.

## What is not finished yet

Being honest about limits is the product's whole point, so here they are.
Evidence produced in continuous integration is labeled CI-CLAIMED, which means
CI shaped metadata was recorded but no protected identity was verified;
cryptographic attestation is the next fix. The repository has one human today,
so ownership rules are real but a genuine second-party approval is not yet
possible. The full host integration check runs at release rather than on every
merge. Windows has one known failing check. The plugin install path has no
rollback command yet. [TEST-PROTOCOL.md](TEST-PROTOCOL.md) explains each one.

## What happens with your feedback

Every report lands in the program ledger and is triaged against the roadmap in
`program/MASTER-PLAN-2026-08-06.md`. Fixes ship as normal governed changes,
gates and all. Findings from unfamiliar users are the single most valuable
input this project has right now: the whole point of the tool is that someone
who has never seen it can complete a governed change without reading internal
documentation, and only you can tell us whether that promise holds.
