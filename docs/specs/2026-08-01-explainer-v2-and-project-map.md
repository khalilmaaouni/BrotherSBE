# Explainer v2, the help project map, and the directory packet

Design approved by the founder 2026-08-01 through question windows (example: the book's real estate; shape: one deep page with a TOC; project map: skill plus shipped template; directory: prep everything, founder clicks). Branch: feature/beginner-finalization (stacks on open PR 3).

## Workstream A: docs/explainer/index.html becomes one deep page

Constraints that do not move: one self-contained file, zero JavaScript, inline CSS only, both themes via the existing token system, zero em or en dashes, no private names, guarded by TestExplainerSelfContained (unchanged semantics), the published artifact is republished in the same step the file changes.

Copy rules: energetic but concrete, no hype vocabulary (no "powerful", "seamless", "game-changing", "unlock", "leverage"), verdict-first sentences, varied sentence length, every terminal excerpt is a real run lifted from the replay-tested book chapters and labeled as real, no volatile counters (no eval counts, no file counts); version and dates are allowed.

Structure, in order, each an anchored section with an eyebrow label; a table-of-contents nav sits after the hero (a plain anchor list, position sticky in a side column above 1100px, in-flow below):

1. Hero (keep) plus a one-sentence promise line: describe the outcome, follow one action at a time, get a result that was actually checked.
2. What it is (keep both paragraphs, tighten).
3. The story in ninety seconds: a compressed narrative of the estate project going from "nightly totals are wrong" to a merged, evidence-backed fix. Teases the full walkthrough.
4. Install in two commands (keep) plus Keeping it fresh: claude plugin update brothersbe (restart applies it), claude plugin marketplace update brothersbe to refresh the source, and the fact that BrotherSBE announces at session start when the installed version changed. State plainly the official directory listing is prepared but not yet live; the two commands are the real path today.
5. Your first project (keep the four cards).
6. The whole journey, end to end: the estate walkthrough, six stops matching the lifecycle diagram (keep the SVG): each stop gets the real command, a short real excerpt (from the excerpt pack), and one "what to notice" line. Stops: describe and size (intake, tier), design in proportion (dossier, decision table), plan and build (plan, work start and finish), prove (evidence receipt, gates), review and converge, human merge.
7. Riding the loops, practical advice: when start vs adopt; tiers are computed and can only be argued upward; two failed approaches means stop and replan, never a third identical try; NO-DATA means no evidence either way and is never a pass and never quietly a block; receipts come from running commands, never from typing results; the fence idea in plain words (only one worker edits a file at a time).
8. Really good at, honestly not good at: two columns. Good: backend and data system design before code, schema migrations with rehearsed rollback, evidence-backed review of changes and pull requests, catching silently swallowed errors, keeping a team honest about what was actually checked. Not good at: user interface and visual design work, tiny throwaway scripts where the ceremony outweighs the change (T0 exists for this: near-zero ceremony), hosts other than Claude Code today, replacing your judgment about what is worth building, working without a git repository.
9. Use cases, six cards: add an API endpoint safely; change a schema with a rollback you rehearsed; investigate a number nobody trusts; review a pull request before release; adopt a legacy repository; keep a team's status honest. Each card: two sentences plus the first command.
10. Three tutorials, each a numbered step list with real commands and expected-shape output: (1) Your first verified change, T0 to T1 on the estate pipeline; (2) A risky migration done honestly, tier rises, gates demand rehearsal evidence; (3) Reviewing a pull request with evidence, pr verify plus converge. Tutorials use the estate so a reader can literally follow along inside the cloned repository.
11. Co-writing code with it, for developers: how to take a task yourself (work start, edit, work finish), why the tool refuses to close what it cannot prove, where the file claims live, and the two habits that keep the code modern and clean: small single-purpose modules and no silently swallowed errors (the linter names them).
12. Honestly not there yet (keep, refresh: directory packet prepared awaiting submission).
13. Go deeper (keep) and footer (keep, refresh date).

## Workstream B: the help project map

New file skills/help/map-template.html: a self-contained HTML shell using the same token system as the explainer, with named placeholder slots in double braces: {{PROJECT_NAME}}, {{GENERATED_AT}}, {{STAGE_SUMMARY}}, {{STATUS_SECTIONS}}, {{PROCESS_DIAGRAM}}, {{DATA_MODEL}}, {{DECISIONS}}, {{FILE_CLAIMS}}, {{NEXT_ACTION}}, {{CODE_GUIDE}}, {{MERMAID_JS}}. HTML comments beside each slot say what fills it and what to write when the source is absent (a plain sentence naming the missing source, never invented content). The template itself ships dash-free and loads nothing external; diagram slots are pre-styled containers holding pre class="mermaid" blocks; {{MERMAID_JS}} is filled at generation time by inlining the plugin's vendored docs/book/assets/mermaid.min.js (the documented dash exception applies to that vendored content only).

skills/help/SKILL.md gains one section, The project map: when the user asks for a detailed picture (map, diagram, where are we, show me the project, full picture), build it: probe sbe status, sbe fences, the dossier directory (01-purpose, 03-adr, 05-data-model, 06-diagrams, 08-plan.json) and any decision records; fill every slot of the template at map-template.html; write the result to brothersbe-map.html at the user's project root; tell the user the exact path and that it opens in any browser and works offline. Missing sources produce the honest absent-sentence, never a guess. The mermaid in 06-diagrams.md is copied verbatim into the diagram slots; when no diagrams exist, the process slot instead carries a minimal mermaid flowchart of the six lifecycle stops with the current stop marked.

Guard: class TestHelpMapTemplate appended to tools/test_sbe.py: template exists and is over 3000 bytes; every named placeholder appears exactly once; no src, href, url( or @import resolving to http or https (anchors allowed); zero U+2013 and U+2014. Calibrated by reinjection with hash-verified restore.

## Workstream C: update visibility and the directory packet

README: the opening install section already names update and uninstall; add one sentence about the session-start version-change announcement. No other README change.

program/DIRECTORY-SUBMISSION.md, new: the verified submission process for the official Claude plugin directory, written from sources actually opened (each claim carries its URL), the prepared submission content (whatever the process requires: entry text, manifest facts, category, description), a preflight checklist against the directory's stated requirements, and the founder's exact final steps. If research finds the directory does not yet accept external submissions, the packet says so plainly and records the watch-signal instead; no invented process.

## Out of scope, named

The deterministic sbe report command (map generation as engine code), any new sbe subcommand, non-Claude host work, and the consumer-check CI fix (owned by the separate session on task_27bf8c37).
