# Team documentation, decision deep-dives, collaboration, and the book

Design spec, approved by the founder through question windows on 2026-07-30 (three
interview rounds, four design-section approvals, all recorded in the session transcript
and the vault). This file is the single source of truth for the six-loop program below.
Status: APPROVED DESIGN, awaiting the founder's written-spec review before planning.

## Why this exists

The founder's ask, in his words: a well structured Documentation folder per project
(business analysis, task summary, WBS, Gantt with critical path, process diagrams,
data models, dependencies, code documentation, whitepaper, and a handover humans can
finish the project from without AI); per-gate decision deep-dives an engineer can
review before deciding anything; real collaboration between the AI and the team and
within the team; one-line team install; and an illustrated book, because the team
does not yet understand the product's benefit or how to run loops and agents
coherently for backend, data, and infrastructure work.

## Decisions taken, with the founder's answers

| Decision | Answer (all via windows, 2026-07-30) |
|---|---|
| Program order | Adoption first: book and install lead |
| Office formats vs zero-dependency law | Markdown, Mermaid, CSV canonical; `sbe docs export` converts via tools present on the machine and refuses honestly when absent |
| Collaboration home | Versioned files in git, no server |
| "Release tasks to GitHub" under a logged-out gh | Issues prepared as files in an outbox, published by one command after login |
| Book form | In-repo MD chapters, one zero-dep build to a single self-contained illustrated HTML |
| Book spine | One worked estate end to end (nightly data pipeline plus backend API), cookbook appendix |
| Audience | Backend, data, and infrastructure engineers, plus BAs and PMs as first-class consumers |
| Decision packages | Written automatically at the gate, browsable and regenerable on demand |
| Alerts | Inside `sbe status`; unresolved DANGER blocks like a broken claim |
| Lineage | Ships with Feature 2, not later |
| Install | One script plus a committed team profile |
| Loop order | L1 book+install, L2 decisions+lineage, L3 docs folder+export, L4 notes+alerts, L5 outbox+execution start, L6 adapters+dogfood; confirmed |

## Feature 1: `sbe docs`, the Documentation folder

New module `src/brothersbe/docsgen.py`, wired as `docs` in the CLI COMMANDS table.

Truth sources, the ONLY inputs: `00-intake.json` and the dossier artifacts, the task
registry (`.sbe/tasks.json`), decision packages (`design/<project>/decisions/`), the
notes store, git history, and the code tree. Nothing is invented: a section whose
truth source is absent renders as NO-DATA naming what would fill it, the product's
own law applied to its documentation.

`sbe docs build [path]` writes `Documentation/`:

1. `01-business-analysis.md`: purpose, stakeholders, constraints, tier and why, from
   intake and the purpose artifact.
2. `02-task-summary.md`: every task with status, owner, scope, verification command.
3. `03-wbs.md`: hierarchical work breakdown derived from task ids and owned scopes.
4. `04-delivery.md`: Mermaid gantt from registry dates and dependencies, plus the
   computed critical path (longest path over the dependency graph, standard library),
   slack per task, and the path's members named in prose.
5. `05-process.md`: process diagrams (Mermaid flowchart) from the dossier's process
   artifacts, each step explained under its diagram.
6. `06-data-model.md`: Mermaid erDiagram from the dossier's data artifacts, the three
   lenses noted where the dossier recorded them.
7. `07-dependencies.md`: task-to-task and code-to-code dependencies (import graph for
   Python estates; declared elsewhere), each with one line of why it matters.
8. `08-code-guide.md`: per-module explanation at the depth the project declares in its
   team profile (summary, structure, entry points, the parts a maintainer touches).
9. `09-whitepaper.md`: assembled narrative: what this project is, how the solution
   works, how to run and use it, what the gates guarantee and refuse, limits.
10. `10-HANDOVER.md`: the handover pack in the proven house format: state, where
    everything is, how to know the tree is healthy (commands), mistakes made and what
    they cost, open defects, remaining scope, working rules; written so a human can
    find, fix, and finish without AI.

Every file carries a generated-from stamp (head commit plus the source files read)
and derived-by markers wherever a number appears, so the existing doc-honesty evals
guard generated documentation exactly as they guard shipped pages. Regeneration is
idempotent on an unchanged tree.

`sbe docs export [--formats docx,xlsx,pdf]` converts canonical MD and CSV using
converters found on the machine (pandoc first, others detected by name). Absent
tools produce a refusal naming the exact install, never a silent skip and never a
bundled dependency: the zero-dependency promise covers the tools; export is an
optional adapter over what the machine already has.

## Feature 2: decision packages, `sbe explain`, `sbe lineage`

New module `src/brothersbe/decisions.py`.

A decision package is written automatically when a gate FAILs, a check is WAIVED, a
tier is raised or disposed, or a forced task close records a disposition. Location:
`design/<project>/decisions/NNN-<slug>/DECISION.md` containing: the verdict line
verbatim; the evidence quoted; the deciding code as file and line spans WITH the
excerpt itself; a Mermaid flowchart of the check's logic; inputs that feed the
verdict (files, environment, registry entries); risks that could invalidate it;
what would flip it; and a review checklist an engineer walks before deciding.
Packages are versioned files, bound to the commit that produced them.

`sbe explain <gate|check|decision-id>` regenerates or browses a package on demand.
`sbe lineage <artifact>` walks the chain for any artifact: binding, covering
receipts, decisions that touched it, notes on it, commits and authors, oldest to
newest, each hop one line with its evidence pointer.

## Collaboration: `sbe note` and status alerts

New module `src/brothersbe/notes.py`. Notes are versioned files under
`.sbe/notes/<artifact-key>/NNN.md` with frontmatter: author (git identity), commit,
severity (NOTE, INSIGHT, DANGER), mentions, created, resolved-by and resolution.
`sbe note add|resolve|list`. `sbe status` gains a NOTES section listing unresolved
entries by severity with their artifacts; an unresolved DANGER is a merge blocker,
same class as a broken claim, and says who it mentions. No server, no accounts:
the team collaborates through the repository it already shares, offline-safe.

## Team install

`install.sh` at the repo root: verifies git, Python 3.9+, and Claude Code by name;
installs the plugin (marketplace when the tag is published, clone fallback);
runs `sbe init --apply` honoring `.sbe/team-profile.json` committed to the estate
(dossier root, vault path convention, CI choice, code-guide depth); finishes with
`sbe doctor` and prints PASS or exactly what is missing. One line per teammate,
identical result per machine.

## The issues outbox

`sbe issues prepare` renders the backlog (this spec's loops, the reopening list)
into `.sbe/issues-outbox/NNN-<slug>.md` files with title, body, labels, milestone.
`sbe issues push` publishes every outbox file via gh and moves it to
`.sbe/issues-outbox/published/`; without auth it refuses by name. Nothing waits on
GitHub to exist as work.

## The book: BrotherSBE for Dummies

`docs/book/`, chapters in Markdown beside the product. Spine: one worked estate,
a nightly data pipeline plus a backend API, from `install.sh` to a shipped, gated,
documented release, two engineers, a BA, and the vault coordinating. Part I
(outcomes, for BAs and PMs, no terminal required): what the product guarantees,
what the Documentation folder gives them, how to read status, WBS, Gantt, and the
whitepaper. Part II (the engineer core): the worked estate chapter by chapter,
loops when the work loops, gates when the money path appears, notes and DANGER when
the second engineer disagrees, decision packages and lineage at review time, the
vault as shared memory, coordinating without collisions. Part III: the cookbook,
task types mapped to recipes (new pipeline, schema change, incident, migration,
refactor, adopting an existing repo). Every terminal excerpt in the book is real
output re-executed by the book's own build check, the same law guide-05 already
lives under.

`python3 docs/book/build_book.py` produces `BrotherSBE-for-Dummies.html`: single
file, navigable, all diagrams rendered offline via one vendored mermaid.js asset
(a content file, not a runtime dependency; the Python build stays stdlib), printable
to PDF from any browser. `sbe docs export` covers the Word copy.

## Testing and honesty, all of it

Each module ships its own suite (`tools/test_sbe_docs.py`, `test_sbe_decisions.py`,
`test_sbe_notes.py`) with every fixture calibrated: break the control, watch red,
restore against a recorded hash. Generated-doc honesty joins the eval bed (stamps
recompute, NO-DATA sections never read as content). The book build gets a test that
every chapter lands in the HTML and renders offline, and that every pasted terminal
block re-executes to what it shows. `install.sh` is tested in a scratch HOME.
Everything ships INTERNAL-EVAL until the team's estates prove more, and the book
says exactly that.

## The program

| Loop | Contents | Est. sessions |
|---|---|---|
| L1 | Book (all three parts, worked estate as fixtures, build_book, tests) + install.sh + team profile | 1.5 to 2 |
| L2 | decisions.py: packages at the gate, explain, lineage, suite, evals | 1 |
| L3 | docsgen.py: ten artifacts, critical path math, export adapter, suite, evals | 1 to 1.5 |
| L4 | notes.py: note command, status NOTES section, DANGER blocker, suite | 0.5 to 1 |
| L5 | issues outbox + execution layer start: sbe exceptions, then plan and converge | 1 to 2 |
| L6 | adapters (dbt, JUnit, OpenAPI first) + vault-estate dogfood + consolidation measurement | 1 to 2 |

Each loop: fresh session, engine-run writers with the trap-naming briefs rule,
orchestrator verification, refute review, landed and pushed before the next.
Interleaved when unblocked by the founder: ubuntu evals diagnosis (gh login or a
Linux runtime), Windows CI leg, tag publish, PR backfill.

## Out of scope, named

No server, no accounts, no notifications infrastructure; no office-format libraries
bundled; no execution-layer completion inside this program (it starts in L5, its
own program follows); no maturity claim above INTERNAL-EVAL anywhere.
