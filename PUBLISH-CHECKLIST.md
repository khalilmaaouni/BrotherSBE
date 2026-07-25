# Publish checklist (founder-gated)

This repository is complete, clean, and local only. Publishing is a deliberate,
founder-triggered step. Nothing here is pushed.

## Preconditions, each to be re-checked at publish time

Unticked on purpose. A checklist that asserts its own preconditions are met is the
decorative kind: it is trusted instead of run. Every line below is a command or an
observation to make on the day, not a claim this document makes on its own behalf.

- [ ] Zero private or client terms in any git blob. The history is multi-commit
      (`git rev-list --all --count` reports 23 at the time of writing), so a
      forensic sweep covers every commit, not just the tree at HEAD.
- [ ] Green: `python3 tools/test_sbe.py` and `python3 evals/run_evals.py` both pass.
- [ ] Self-consistent: `python3 tools/sbe_gate.py --strict .`,
      `python3 tools/sbe_design.py --strict .` and `python3 tools/sbe_score.py --strict .`
      all exit 0 (the skill passes its own gates).
- [ ] MIT license, only Khalil Maaouni named.
- [ ] The tracked tree is what was intended. `BrotherSBE-Whitepaper.docx` IS tracked,
      deliberately: it is the rationale document, it was swept, and it carries no
      client data. Section drafts, audit reports and build logs stay in the private
      vault and are not here.
- [ ] The install command in `README.md` and `docs/SETUP.md` resolves. It points at
      a repository that does not exist until this checklist is executed, so it is
      expected to 404 beforehand and must be re-checked immediately after.

## The publish step (when the founder chooses)
1. Create a new PUBLIC GitHub repo named BrotherSBE under the founder's account.
2. Add it as the remote and push via GitHub Desktop (the standing release tool),
   the founder authorizing the push at the GUI. Credentials are never automated.
3. Confirm the pushed tree matches the intended one: no `sections/`, `verify/`,
   `WHITEPAPER.md` and no `STATE.md` (gitignored, never re-added), and exactly one
   `.docx`, the whitepaper, which is tracked on purpose.

## After publish
- Optionally publish the whitepaper separately as the rationale document; it names
  the sibling BrotherModeUp, which is already public, and carries no client data.
