# Publish checklist (founder-gated)

This repository is complete, clean, and local only. Publishing is a deliberate,
founder-triggered step. Nothing here is pushed.

## Preconditions, all currently met
- Single clean commit, object store pruned: zero private or client terms in any
  git blob (verified by forensic sweep).
- Green: `python3 tools/test_sbe.py` and `python3 evals/run_evals.py` both pass.
- Self-consistent: `python3 tools/sbe_gate.py --strict .` and
  `python3 tools/sbe_score.py --strict .` both exit 0 (the skill passes its own gates).
- MIT license, only Khalil Maaouni named.
- Design artifacts (whitepaper, section drafts, audit reports, build log) live in
  the private vault, never in this repo.

## The publish step (when the founder chooses)
1. Create a new PUBLIC GitHub repo named BrotherSBE under the founder's account.
2. Add it as the remote and push via GitHub Desktop (the standing release tool),
   the founder authorizing the push at the GUI. Credentials are never automated.
3. Confirm the pushed tree matches: no `sections/`, `verify/`, `WHITEPAPER.md`,
   `STATE.md`, or `.docx` (they are gitignored and were never re-added).

## After publish
- Optionally publish the whitepaper separately as the rationale document; it names
  the sibling BrotherModeUp, which is already public, and carries no client data.
