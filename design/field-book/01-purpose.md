# 01. Purpose brief

## Problem

An engineer handed this repository cannot tell, in one sitting, what
BrotherSBE is, which of its parts are controls and which are disciplines, or
how to run it on the project in front of them. The material exists: an
eighteen-chapter narrative book, a beginner explainer page, four role guides,
a laws reference, a limits page and a thirty-eight kilobyte README. It is
spread across four surfaces that each restate the feature list in their own
words, so the four copies are free to disagree, and nothing detects it when
they do. A reader who wants the honest answer to "what does this actually
enforce" has to reconcile them by hand.

The second half of the problem is that the material is written for a reader
who has already decided to adopt. Nothing addresses the engineer who has not:
no positioning against the alternatives they already use, no comparison they
can scan, no statement of when the tool is the wrong choice, and no worked
path from their own stack (a warehouse model, a service endpoint, a web build)
to a first useful result.

## Users

**Team engineers who have not adopted it.** They receive a repository link and
have twenty minutes. Today they open the README, hit the engineering reference
at line 48, and stop.

**Individual contributors already using it.** They know two or three commands
and re-derive the rest by grepping `src/brothersbe/cli.py`, because the
command list closest to the truth is the code.

**The platform lead deciding for a team.** They need the enforcement class of
every rule, the limits stated as limits, and the CI wiring, and they currently
assemble that from `DIGEST.md`, `LAWS-REFERENCE.md`, `docs/KNOWN-LIMITS.md`
and `docs/CI-ORDER.md` separately.

**The maintainer.** Every release, they carry the cost of the drift above,
without a signal telling them which page went stale.

## Success criteria

- A reader who has never seen BrotherSBE can state what it is, what it
  enforces mechanically, and one honest limit, after reading two pages.
- The feature list, the role list, the check and gate list with severities,
  the law list with enforcement classes, and the limits list exist in exactly
  one place, derived from the files that define them rather than retyped.
- A change to any of those source files without a regenerated book fails a
  check by name, in CI, the same way an ungated number does.
- A reader working in Snowflake, Databricks, Power BI or Azure, in a backend
  service, or in a web or app build, finds a scenario carrying the real
  commands for their case rather than a generic one.
- The artifact is published and readable without a terminal, and its source
  lives in this repository.

## Non-goals

- This does not replace the eighteen-chapter book, the role guides or the
  explainer. It becomes the entry point that routes to them, and it takes over
  ownership of the enumerations they currently duplicate.
- This does not add a documentation site generator, a theme system or a build
  toolchain. One deterministic Python module emits one self-contained HTML
  file, the way `sbe map` and `sbe program` already do.
- This does not verify that the prose is true. It verifies that generated
  sections match their sources and that prose carries a version stamp. A
  chapter that is stamped current and wrong stays wrong, and the stamp is a
  claim about when a human last read it, nothing more.
- This does not change any law, gate, check or command outside the new
  `book` subcommand.

## What breaks if this is wrong

If the generator reads a source wrongly, the booklet publishes a feature list,
a severity or a limit that the shipping tool does not match, under the
authority of a document whose whole argument is that its claims are derived
rather than asserted. That is worse than the drift it replaces, because the
current pages at least do not claim to be generated.

If the drift check is too strict, it blocks merges on documentation for
changes that did not touch a documented surface, and the first team to hit it
will disable it, taking the honest checks with it.
