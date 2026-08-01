# Directory submission packet

Research date: 2026-08-01. Raw research with full quotes kept durably at
`~/Documents/BrotherSBE-handover/directory-research-2026-08-01.md`.
Every process claim below carries the source URL that research file cites.

## Bottom line

**Closed** for direct submission into `claude-plugins-official`, the curated
marketplace Claude Code registers automatically on first interactive start.
There is no application process; Anthropic adds plugins to it at its own
discretion.

Source: https://code.claude.com/docs/en/plugins, quoted in the research file:
"The official marketplace, `claude-plugins-official`, is curated separately.
Anthropic decides which plugins to include at its discretion. There is no
application process, and the submission form does not add plugins to the
official marketplace."

**Open** for the separate `claude-plugins-community` marketplace, the one
users add with `/plugin marketplace add anthropics/claude-plugins-community`
and install as `@claude-community`. Two web forms feed it, gated on passing
`claude plugin validate` plus Anthropic's automated safety screening, then
synced nightly into that repo's `marketplace.json`.

Source: https://code.claude.com/docs/en/plugins, section "Submit your plugin
to the community marketplace" (the anchor fragment on that link reads
`#submit-your-plugin-to-the-official-marketplace`, a stale slug the research
file flags; the visible heading and body text are unambiguous that the form
feeds community review, not official inclusion).

The repo README of `claude-plugins-official` itself (opened via
`gh api repos/anthropics/claude-plugins-official/contents/README.md`) reads,
in isolation, as if the form gets a plugin into the official marketplace. It
does not; the docs page above is the authoritative statement and the two
disagree. This is the one item worth escalating if anyone building on this
packet reaches Anthropic directly.

## What to watch

- Whether `claude-plugins-official`'s README gets corrected so it stops
  implying the submission form leads to official-marketplace inclusion.
- Whether the stale `#submit-your-plugin-to-the-official-marketplace` anchor
  on https://code.claude.com/docs/en/plugins gets fixed to match the page's
  current "community marketplace" heading.
- Whether Anthropic opens any discretionary path into `claude-plugins-official`
  itself; none is documented today (source: same docs page).

Re-run the checks in the research file (WebFetch the docs page, `gh api` the
two repo READMEs) before treating any of the above as still true; this packet
is dated 2026-08-01 and the pages it cites can change without notice.

## Preflight checklist

Sourced from https://code.claude.com/docs/en/plugins, "Share your plugins"
section, and the repo README's required directory shape (both quoted in the
research file):

- [ ] `README.md` with installation and usage instructions. BrotherSBE has
  this (this file's own repository root README.md).
- [ ] A versioning strategy chosen: explicit `version` field, or rely on git
  commit SHA. BrotherSBE uses an explicit version (`1.0.0-rc.1`, see below).
- [ ] Distributed through a plugin marketplace for installation. BrotherSBE
  already ships `.claude-plugin/marketplace.json` (see below).
- [ ] Team members test the plugin before wider distribution.
- [ ] Run `claude plugin validate ./your-plugin` locally and confirm
  `✔ Validation passed` (or `passed with warnings`, then decide whether
  `--strict` should turn those into failures) before using either
  submission form. Not run as part of this task; the founder runs it
  himself as the first of his final steps below.
- [ ] Required plugin directory shape present: `.claude-plugin/plugin.json`,
  optionally `.mcp.json`, `commands/`, `agents/`, `skills/`, and
  `README.md`. BrotherSBE has `.claude-plugin/plugin.json` and `README.md`
  at minimum; confirm the others match what the plugin actually ships
  before submitting.

## Prepared submission content

Drawn verbatim from the two manifest files already in this repository
(`.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`), not
invented for this packet.

From `.claude-plugin/plugin.json`:

| Field | Value |
|---|---|
| `name` | `brothersbe` (immutable slug once published, per the repo README quoted in the research file) |
| `description` | A senior backend and data engineering colleague. Designs systems in the order the work runs (purpose, process, architecture, data, expression, verification), produces a design dossier sized by a scored intake, and holds the result to mechanical gates where absent evidence is NO-DATA and never a pass. |
| `version` | `1.0.0-rc.1` |
| `author` | Khalil Maaouni |
| `repository` | https://github.com/khalilmaaouni/BrotherSBE |
| `license` | MIT |
| `keywords` | backend, data-engineering, design-review, evidence, verification, migrations, code-review, guided, onboarding |

From `.claude-plugin/marketplace.json` (the marketplace listing entry, a
different shape than the plugin manifest per the docs page's skill-bundle
example quoted in the research file):

| Field | Value |
|---|---|
| marketplace `name` | `brothersbe` |
| marketplace `owner` | Khalil Maaouni |
| listed plugin `source` | `./` |
| listed plugin `category` | `engineering` |
| listed plugin `keywords` | backend, data-engineering, design-review, evidence, verification, migrations, code-review |

The `description` and `version` fields match between the two files. The
`keywords` lists differ by two entries (`guided`, `onboarding` appear only in
`plugin.json`); decide before submitting whether to reconcile them into one
list, since a reviewer may read either file.

## Founder's exact final steps

This packet stops short of submitting anything; submitting a plugin means
filling in and posting a web form under Khalil's own account, which is his
action to take, not this task's.

1. Run `claude plugin validate ./` from the repository root and read the
   result. Fix anything it reports before continuing.
2. Decide which form applies: an Individual author outside a Team or
   Enterprise organization uses
   https://platform.claude.com/plugins/submit; a Team or Enterprise
   organization Owner (or someone granted directory management access) uses
   https://claude.ai/admin-settings/directory/submissions/plugins/new.
   (Source: https://code.claude.com/docs/en/plugins, quoted in the research
   file.) Neither form was opened during this research pass; both require an
   authenticated session, so their exact fields are not independently
   verified beyond this org-type gating rule.
3. Open the chosen form and copy the values from the "Prepared submission
   content" table above into whatever fields it asks for, reconciling the
   keyword-list mismatch noted above first.
4. Submit the form himself. Approved plugins are pinned to a commit SHA in
   `anthropics/claude-plugins-community` and the public catalog syncs
   nightly (source: https://code.claude.com/docs/en/plugins, quoted in the
   research file), so expect a delay before the listing appears, not
   confirmation on submit.
5. After approval, re-check this packet's "What to watch" list; if the
   official-marketplace README correction has landed by then, re-evaluate
   whether a path into `claude-plugins-official` itself has opened.
