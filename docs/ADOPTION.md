# Adopting BrotherSBE into a repository

`sbe adopt` proposes what a repository is missing; it never applies a
protection GitHub controls, because nothing here holds a GitHub token or
admin rights, and it never claims otherwise. This page is the honest
checklist: what `sbe adopt` can do for you, and what only you (or your repo
admin) can click.

## What `sbe adopt` does

```bash
bin/sbe adopt .                 # dry run: prints every proposal as a diff, writes nothing
bin/sbe adopt . --apply         # writes what was proposed; never overwrites an existing file
bin/sbe adopt . --apply --force # overwrites an existing file that differs from the proposal
bin/sbe adopt . --json          # machine-readable
```

It detects the stack (languages by extension, a migrations directory, dbt
models, API contract files, existing CI workflows) by walking the tree, the
same way `skills/adopt/SKILL.md` already documents: **detected from files,
not asked**. From that it proposes two files:

- `.brothersbe/policy.json`: a **provisional** repository policy. BrotherSBE's
  wave 3 (the repository policy file and its own JSON schema) has not shipped
  as this page is written; what `sbe adopt` proposes is a smaller shape built
  from what it can already detect, and the file says so on its own `note`
  field. A detected migrations directory or dbt project adds a matching
  `migrations` or `dbtModels` entry under `protectedPaths`; neither appears
  when neither is detected.
- `.github/CODEOWNERS`: generated straight from that same `protectedPaths`
  map (never a second hand-typed list, so the two cannot drift apart),
  covering the six categories the adoption kit is asked to protect: the
  plugin manifest, the hooks, BrotherSBE's own policy and config, where the
  evidence schema is declared in code, product and consumer CI, and release
  identity files. Every line carries the placeholder `@REPLACE-ME`: this tool
  has no repository membership to read a real username or team from, and
  typing one in would be a guess dressed up as a proposal. **Replace it
  before this file protects anything.**

Both proposals are **deterministic**: the same tree produces the same
content every time, with no timestamp or run id inside either file. That is
what lets `--apply` run twice safely: the second run finds every proposal
already matches what is on disk and writes nothing, and says so.

## What `sbe adopt` reports, and the line it will never cross

The adoption report also names three protections it was asked to check:
branch protection, required status checks, and whether review from a code
owner is *required* (not just possible). **All three are settings on
GitHub's code review platform, not on a filesystem.** A `git clone` cannot
read them, this tool holds no GitHub credentials, and it asks for none. So
every one of those three always reports `UNVERIFIABLE-HERE`, naming what
reading it for real would take (a GitHub token with repo scope, plus admin
rights on the repository): **never `PRESENT`, no matter what is or is not
in the tree.** That is the one rule this whole command is built around, and
`tools/test_sbe_adopt.py::TestAdoptionReportNeverClaimsPresent` pins it as a
kill criterion: a report that ever claims one of those three PRESENT from a
local read is worse than the refusal `sbe adopt` used to print instead of a
command at all.

A CODEOWNERS file *existing in the tree* is a different, locally-checkable
fact, and is reported separately under `localFacts` (`PRESENT`/`ABSENT`) so
it is never read as proof that GitHub is actually configured to require that
review.

## What only a human with admin rights can do

`sbe adopt` cannot turn any of these on. Each is a real GitHub setting, named
here with its exact path so nobody has to search for it:

1. **Require a pull request before merging.** Settings > Branches > Branch
   protection rules > add a rule for your default branch > "Require a pull
   request before merging".
2. **Require status checks to pass before merging**, and select the
   "BrotherSBE gates" job (and, once your branch protection scope covers it,
   the consumer-checks job) as **required**. The same screen, "Require status
   checks to pass before merging". Adding the workflow file does not do this
   by itself: `docs/KNOWN-LIMITS.md` states the same limit as "The CI workflow
   guards nothing until you copy it" (L16), and both shipped workflows repeat
   it in their own header comments.
3. **Require review from Code Owners.** Same screen, "Require review from
   Code Owners", once `.github/CODEOWNERS` exists and every `@REPLACE-ME` has
   been replaced with a real user or team.
4. **Restrict who can push to the protected branch**, if you want to prevent
   a direct push around the pull request entirely.

## `sbe init`

`sbe adopt` proposes policy and CODEOWNERS; `sbe init` installs BrotherSBE's
own local footprint. See `docs/CLI.md` ("sbe init") for its config file,
dossier directory, optional consumer CI copy, and the installation receipt
with exact uninstall instructions.

## Limits, stated where the behavior is

Full text: `docs/KNOWN-LIMITS.md` ("The adoption kit proposes, and verifies
only what a filesystem can answer").
