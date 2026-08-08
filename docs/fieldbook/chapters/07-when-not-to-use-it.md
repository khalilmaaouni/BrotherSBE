---
slug: when-not-to-use-it
title: When not to use it
part: "3"
verified-against: 1.0.0-rc.28
---

# When not to use it

A tool that claims to fit everything fits nothing. Here is where this one is
the wrong choice, stated plainly so you find out now rather than in month two.

## Do not adopt it for

**Pure frontend work with no data or service behind it.** A component library,
a marketing site, a design system. The gates are about numbers, migrations,
approvals and executed checks, and none of those bite. You will get T0 on
everything and wonder what it was for. Use a design and accessibility toolchain
instead.

**A codebase nobody is going to keep.** A spike, a hackathon, a throwaway
proof. The whole method is an investment in decisions being findable later. If
there is no later, skip it.

**A team that will not review a pull request.** The team learning loop moves
only through a reviewed PR into a shared lessons file, by design, so no
colleague's tool changes behaviour silently. Without a review habit, that loop
does not turn and you are left with the solo experience, which is fine but is
less than half of it.

**Somewhere you need it to run your production changes.** It never gets apply
rights on production state. It drafts the exact command with its rollback and
hands it to a human. If what you wanted was an agent that deploys, this refuses
on purpose.

**As a substitute for branch protection.** The approval gate verifies a
declared approval. It does not notice a change that declared nothing. If your
real requirement is "nobody merges without a reviewer", that is CODEOWNERS and
branch protection on your own repository, and no plugin can supply it.

## Adopt it when

- Wrong output would be **silent**: a figure nobody re-derives, a pipeline that
  drops rows, a migration whose reverse was never run.
- More than one consumer depends on a shape you are about to change.
- The work involves a warehouse, a service contract, a schema migration,
  personal or partner data, or money.
- You have agents writing engineering work and no mechanical way to tell
  whether what they produced is true.
- Decisions on your team keep getting re-litigated because nobody wrote down
  what was rejected and why.

## The honest cost

On a T0 change, close to zero: five questions and nothing owed.

On a T2 or T3 change, real. Six or seven artifacts, and each one is a piece of
thinking somebody has to do. The argument is not that this is free. It is that
you were going to pay for those decisions anyway, and paying at design time is
cheaper than paying at incident time.

If your changes are almost never T2 or T3, you probably do not need this, and
that is a legitimate answer.
