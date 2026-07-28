# ADR: BrotherSBE ships as a Claude Code plugin

Date: 2026-07-28. Status: accepted, wave 1 of the P0 conversion.

## Context

BrotherSBE was distributed by asking each person to clone the repository into
`~/.claude/skills/brothersbe/` and hand-edit their `~/.claude/settings.json` to wire four
hooks. That is a workable shape for one author and an unworkable one for a team of twelve: no
version anyone can name, no upgrade path, no rollback, four hand-copied hook paths that break
the first time somebody clones to a different directory, and no way to say which revision an
engineer was actually running when a gate behaved oddly.

## Criteria

Named, with the value observed on this estate:

- Team size to support: 8 developers, 2 business analysts, 2 project managers, 2 QA engineers.
- Installation steps a new engineer must perform correctly: currently 2 (clone, plus a manual
  JSON edit in a file that also holds their own unrelated hooks). Target: 1, with no manual
  edit of a shared settings file.
- Existing behavior that must not change: 509 evals, 27 unit tests, 41 fence-hook tests, four
  hard gates and the silent-failure lints, all green before the change.
- Law-file paths that must keep resolving: every `references/` citation, every `tools/` path in
  the docs, every eval fixture path.
- Python floor: 3.9, the system Python on the machine that maintains this.

## Options considered

### Rejected: leave it as a cloned skill and document harder

Zero engineering cost, and it fails the first criterion outright. Nothing in a document can
give a team a version to pin, an upgrade command, or a rollback. The failure mode is not
hypothetical: two engineers on different clone dates would be running different law with no
mechanical way to notice.

### Rejected: convert to a plugin and restructure the repository at the same time

The brief that prompted this work asks for a `src/brothersbe/` package layout, which is the
right destination. Doing it in the same change as the packaging means moving `SKILL.md`,
`references/`, `tools/` and every path that cites them, while 509 evals and every documented
command point at the old locations. The criterion that kills this option is the one about
existing behavior: a conversion that lands with a broken green line cannot be told apart from
a conversion that lands with a broken product.

### Rejected: duplicate the law files into each skill directory

Claude Code loads a plugin skill from `skills/<name>/SKILL.md`, and relative links inside a
skill resolve from that skill's directory, so the obvious way to make six skills work is to
give each one its own copy of what it cites. Six copies of the law is six laws, and this
project's own rule is that a law merges or displaces rather than accreting.

## Decision

Convert the repository into a Claude Code plugin **without moving a single existing file**.

- `.claude-plugin/plugin.json` declares the plugin, and its version tracks the `VERSION` file.
- `skills/` holds six thin namespaced skills (`kickoff`, `design`, `verify`, `review`, `learn`,
  `adopt`). Each routes into the law rather than restating it.
- Shared assets stay at the plugin root and are addressed through `${CLAUDE_PLUGIN_ROOT}`,
  which is exactly the mechanism that makes a single copy reachable from six skill
  directories.
- `agents/` holds seven read-only reviewer agents, one per lens the review law already names.
- `hooks/hooks.json` ships the four hooks with self-resolving paths, so no engineer edits a
  shared settings file to install them.

## Consequences

An engineer installs one thing and gets a version they can name, upgrade and roll back. The
hook paths stop depending on where the repository was cloned. The reviewer lenses become
dispatchable agents instead of prose someone has to remember to apply.

The cost: the plugin surface and the law surface are now two things that can drift. A skill
could cite a reference file that has been renamed, or the manifest version could wander away
from the `VERSION` file, and nothing about a plugin loading successfully would reveal either.
That cost is paid with checks in `tools/test_sbe.py` rather than with care: the manifest parses
and agrees with `VERSION`, every skill and agent carries the frontmatter the loader needs,
every `${CLAUDE_PLUGIN_ROOT}` path a skill or hook cites exists on disk, and every hook command
in `hooks.json` points at a real file.

A second, smaller cost: someone who installed the old way and also installs the plugin runs
each hook twice until they remove their settings entries. `docs/MIGRATION.md` says so.

## What would flip this

If Claude Code's plugin loader ever resolved skill-relative paths from the plugin root, the
`${CLAUDE_PLUGIN_ROOT}` indirection in the skills would become unnecessary and the skills would
be simpler as plain relative links. And if this repository ever needs to ship two independently
versioned products out of one tree, the single-manifest assumption here stops holding and the
layout must be revisited.
