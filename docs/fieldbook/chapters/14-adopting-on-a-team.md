---
slug: adopting-on-a-team
title: Adopting it on a team
part: "6"
verified-against: 1.0.0-rc.28
---

# Adopting it on a team

## The rollout that works

**One repository. One lane of work. Two weeks advisory, then strict.**

Do not roll this across an estate before one team has an opinion. A control
that arrives everywhere at once, before anyone has felt it help, gets
switched off everywhere at once the first time it is inconvenient.

### Week 0: inspect before you trust

```bash
sbe adopt .
```

Dry run by default. It reports what it would install and changes nothing.
Read that output before anything else happens.

```bash
sbe adopt . --apply
```

### Week 1: advisory

Copy the CI workflow into your repository and run it **without** `--strict`.
It prints verdicts and exits zero. The team sees what would have blocked,
without anything blocking.

This week exists to find the checks that are noisy on your codebase, not to
enforce anything.

### Week 2: agree the two rules out loud

Before `--strict` goes on, the team agrees two sentences:

1. **A FAIL blocks. A NO-DATA does not.** Nobody argues with a NO-DATA; it is
   information, not an accusation.
2. **Nobody edits the workflow to make red go away.** If a gate is wrong, it
   gets fixed or exempted visibly, in a diff, with a reason.

That second sentence is the entire control. It is why a session instruction can
never waive a hard gate: `--strict` moves only by a human editing the workflow
file, where a reviewer sees it.

### Week 3: strict

Turn it on. Expect one uncomfortable pull request. That is the system working.

## What you must supply yourself

Stated here because assuming otherwise is the most likely way this
disappoints you.

- **CODEOWNERS and branch protection.** Neither ships. The approval gate
  verifies a declared approval and cannot notice a change that declared none.
- **Signing keys in CI.** The one approval path that PASSes needs the signers'
  public keys available to CI. Without them the verdict is NO-DATA.
- **A registry of your real checks.** `sbe evidence run --check <id>` resolves
  the command from a registry. Until your reconciliations are registered, the
  gate can only prove that *a* command ran.
- **A review habit.** The learning loop turns through reviewed pull requests
  and nothing else.

## How a lesson becomes a rule

This is the part that makes it a team tool rather than a personal one, and it
is deliberately slow.

A lesson from an incident, a repeated correction or a measured outcome is
proposed with `/brothersbe:learn`. It becomes a shared rule only through a
reviewed pull request into the shared lessons file. Local telemetry never
leaves the machine, and no colleague's tool changes behaviour because of
something that happened on yours.

Automatic cross-team learning sounds better and is worse: it means a
colleague's tool starts refusing things tomorrow for reasons nobody reviewed.

## The weekly review

One meeting, thirty minutes, reading what the machinery recorded rather than
what people remember.

- What FAILed, and was the gate right?
- What was NO-DATA repeatedly? Repeated NO-DATA on the same check means the
  evidence is not being produced, and that is a workflow problem, not a tool
  problem.
- Which exemptions are still alive? They are counted and named rather than
  quietly subtracted.
- Which verdicts named a falsification that was actually executed, and which
  were reasoning alone? Reasoning alone is NO-DATA, not a finding.

## The one writer rule

When more than one agent or person is working a shared tree: one writer per
file. Fence the path, then dispatch, in a registry, tier-tagged, and close the
fence with an inline evidence block.

The mechanical part is narrower than it sounds, and the project says so: fence
hygiene is checked only over registries named in an environment variable, and
only for fence lines containing the word "agent". The rest is discipline.

## What good looks like at month three

- Most changes are T0 and owe nothing. If everything is T2, somebody is
  answering the intake wrongly.
- Nobody discusses whether something is done. They read the receipt.
- ADRs get cited in arguments, and occasionally a flip condition has actually
  been met, which is the system paying for itself.
- The honest limits are known by the team, so nobody over-trusts a gate at the
  moment it matters.

## Keeping this book true

This book regenerates from the repository:

```bash
sbe book              # regenerate every derived table
sbe book --check      # does any bound source disagree with the book
```

Under `--strict` in CI, a bound source that moved without a regenerate is a
FAIL naming the section and the file. A prose chapter whose `verified-against`
stamp is older than the current version is NO-DATA: it reports that nobody has
reread it, and it never claims the prose is wrong, because no tool can compute
that.

Run `sbe book` at every loop close, and commit the result.
