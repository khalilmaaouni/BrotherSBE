# Publish checklist (founder-gated)

This repository is complete, clean, and local only. Publishing is a deliberate,
founder-triggered step. Nothing here is pushed.

## Preconditions, each to be re-checked at publish time

Unticked on purpose. A checklist that asserts its own preconditions are met is the
decorative kind: it is trusted instead of run. Every line below is a command or an
observation to make on the day, not a claim this document makes on its own behalf.

- [ ] Zero private or client terms in any git blob. The history is multi-commit
      (`git rev-list --all --count`), so a forensic sweep covers every commit,
      not just the tree at HEAD.
- [ ] Green: `python3 tools/test_sbe.py`, `python3 evals/run_evals.py` and
      `python3 evals/test_no_data_class.py` all pass.
- [ ] Self-consistent: `python3 tools/sbe_gate.py --strict .`,
      `python3 tools/sbe_design.py --strict .` and `python3 tools/sbe_score.py --strict .`
      all exit 0 (the skill passes its own gates).
- [ ] MIT license, only Khalil Maaouni named.
- [ ] The tracked tree is what was intended. NO `.docx` is tracked. The compiled
      whitepaper was, on the stated grounds that it had been swept, and it had not
      been: its tenth paragraph carried a review-round count, a blocking-defect
      count and a pointer at a folder that does not exist in the tracked tree, all
      of which the markdown sources had already been scrubbed of. A compiled
      artifact does not inherit a sweep performed on its source. Generate it from
      the markdown that ships and hand it over out of band. Section drafts, audit
      reports and build logs stay in the private vault and are not here.
- [ ] No internal development history in any tracked file. Review rounds, auditor
      counts, blocking-defect counts, scores and ratings are the private record of
      how this was built and are not part of what it is:
      `git ls-files -z | xargs -0 grep -inE 'audit round|blocking defect|auditors|
      review round|cold persona|round [0-9]|wave [0-9]|fix wave' | grep -v
      PUBLISH-CHECKLIST` must return nothing. The pattern list matches the rule
      above it: it grew after history-shaped comments shipped while the five
      original patterns returned green, a check narrower than its own sentence.
      This line is excluded because it names the terms it searches for, which is
      the one place in the tree where they are the checklist and not the history.
- [ ] The install command in `README.md` and `docs/SETUP.md` resolves. It points at
      a repository that does not exist until this checklist is executed, so it is
      expected to 404 beforehand and must be re-checked immediately after:
      `curl -sS -o /dev/null -w '%{http_code}\n' https://github.com/khalilmaaouni/BrotherSBE`
      must print 200 once the repo is public.
- [ ] `git ls-files docs/superpowers/` returns nothing. That directory held an
      unratified design spec and a long agent task list naming private tooling a
      reader does not have, in a repository where the thing is already built. The
      root `.gitignore` comment said "Internal review and planning notes, never
      shipped" over a rule covering `.superpowers/` only, and a directory one
      character different shipped exactly that category. Both are ignored now.
- [ ] `git status --porcelain` shows no `.superpowers/` path. That directory holds
      internal review and planning documents and is now ignored by the ROOT
      `.gitignore`; it used to be protected only by an untracked ignore file inside
      itself, which one `git add .` on a fresh clone would have defeated. Confirm
      with `git check-ignore -v .superpowers/` and `git ls-files .superpowers/`,
      which must return nothing.

## The publish step (when the founder chooses)
1. Create a new PUBLIC GitHub repo named BrotherSBE under the founder's account.
2. Add it as the remote and push via GitHub Desktop (the standing release tool),
   the founder authorizing the push at the GUI. Credentials are never automated.
3. Confirm the pushed tree matches the intended one: no `sections/`, `verify/`,
   `WHITEPAPER.md`, no `STATE.md` (gitignored, never re-added), and NO `.docx` at
   all, matching the earlier checkbox: the whitepaper is handed over out of band.

## After publish
- Optionally publish the whitepaper separately as the rationale document; it names
  the sibling BrotherModeUp, which is already public, and carries no client data.
