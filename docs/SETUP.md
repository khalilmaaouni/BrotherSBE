# BrotherSBE: setup

Install is a few minutes. Turning the gates from advisory into blocking is real CI work, and this document is honest about which is which.

## Prerequisites

- Claude Code (BrotherSBE is a Claude Code skill).
- Python 3 on PATH (the tools use the standard library only, no third-party packages, no network).
- Git (the approval gate reads commit trailers and signatures).

## 1. Clone the skill

```
git clone https://github.com/khalilmaaouni/BrotherSBE ~/.claude/skills/brothersbe
```

Standalone: it works with nothing else installed. See [PARITY.md](../PARITY.md) for what it shares with BrotherModeUp.

## 2. Point the vault at a folder you choose

```
export BROTHERSBE_VAULT="$HOME/BrotherSBEVault"   # put this in your shell profile
```

Everything the skill writes (telemetry, correction candidates, session logs) goes there, and nowhere else. Copy the starter memory from `memory-template/` into that folder the first time.

## 3. Wire the hooks

Into `~/.claude/settings.json`, or a project `.claude/settings.json`. The harness fires these, not the model, which is the point: the save-before-you-die rule cannot be run by the actor that is dying.

```json
{
  "hooks": {
    "SessionStart": [
      {"hooks": [{"type": "command",
        "command": "sh ~/.claude/skills/brothersbe/tools/sbe_sessionstart.sh"}]}
    ],
    "SessionEnd": [
      {"hooks": [{"type": "command",
        "command": "python3 ~/.claude/skills/brothersbe/tools/sbe_telemetry.py outcomes-append"}]}
    ],
    "PreCompact": [
      {"hooks": [
        {"type": "command",
         "command": "sh ~/.claude/skills/brothersbe/tools/sbe_autosave.sh precompact"},
        {"type": "command",
         "command": "python3 ~/.claude/skills/brothersbe/tools/sbe_telemetry.py precompact-brief"}
      ]}
    ]
  }
}
```

What each does: SessionStart injects the active-laws digest plus mechanical nags. SessionEnd appends one idempotent telemetry line and scans your short messages for correction candidates (secret-redacted, owner-only). PreCompact does two things: it snapshots the whole worktree to a private git ref so a token-death is recoverable, and it writes the brief that survives the compaction. Both commands are in the block above; a setup carrying only the first loses the brief. Every hook exits 0 and never blocks a session. Opt-outs are in [SECURITY.md](../SECURITY.md).

## 4. Prove it works, in 60 seconds

Section 1 cloned the repo and left you wherever you were, so enter the clone first;
every command from here down is relative to it.

```
cd ~/.claude/skills/brothersbe
python3 evals/run_evals.py
```

One line per real failure class, each caught by the check that owns it, ending "509 passed, 0 regressions." That is the whole trust claim, executable. Then see the gates on a directory:

```
python3 tools/sbe_gate.py .            # all four gates, advisory
python3 tools/sbe_gate.py numbers .    # one class
python3 tools/sbe_gate.py --strict .   # enforcing: exits nonzero on any FAIL
```

## 5. Turn the gates from advisory into blocking (the real step)

Cloning the skill gives you the tools. It does not stop a bad merge until you wire `--strict` into the CI of the repository you want guarded. A ready workflow ships at `.github/workflows/brothersbe-gates.yml`; copy it into the guarded repo (and make `tools/` reachable there, by vendoring it or adding a clone step). It runs on every pull request:

```yaml
      - name: Hard gates (numbers, migration, approval, ran) block on failure
        run: python3 tools/sbe_gate.py --strict .
      # A waiver is not a pass. `.sbe-exempt` lets a template library or a finished
      # project stop blocking every unrelated merge, and the exit code cannot tell
      # you one was used, so this step surfaces every WAIVED line as an annotation
      # and in the job summary. A human sees it, or it is not a control. Add
      # --strict-waivers here if you want an exemption to block outright.
      - name: Design checks (dossier completeness) block on failure
        run: |
          set -o pipefail
          python3 tools/sbe_design.py --strict . | tee design-checks.out
      # The pattern is `^  >> `, the prefix sbe_design.py puts on a waived line, and
      # not the word WAIVED. The banner the tool prints on every run ends "WAIVED
      # is not a pass either", so `grep -q 'WAIVED'` was unconditionally true: every
      # clean run told the reviewer that a .sbe-exempt had waived one or more design
      # checks and that nothing opened a file for them, over a run in which every
      # check opened its files. An assurance signal that always fires carries no
      # information, and this one asserted something false, which trains a reviewer
      # to ignore the single control that makes WAIVED visible in CI at all.
      - name: Surface design waivers (a waiver is not a pass)
        if: always()
        run: |
          if grep -qE '^  >> ' design-checks.out; then
            grep -E '^  >> ' design-checks.out | while read -r line; do
              echo "::warning title=BrotherSBE design waiver::$line"
            done
            {
              echo '### BrotherSBE design waivers'
              echo 'A `.sbe-exempt` waived one or more design checks. Nothing opened a file for them.'
              echo '```'
              grep -E '^  >> |^WAIVERS: ' design-checks.out
              echo '```'
            } >> "$GITHUB_STEP_SUMMARY"
          fi
      - name: Silent-failure lints and code-graded checks block on failure
        run: python3 tools/sbe_score.py --strict --strict-soft .
      # The gates above are only worth what their tests are worth. These two ran
      # on nobody's merge path until now, which made them documentation rather
      # than a gate: a fixture no merge runs cannot stop anything.
      - name: Regression evals (every gate against the defect it exists to catch)
        run: python3 evals/run_evals.py
      - name: Honesty meta-test (no check may PASS over evidence it never examined)
        run: |
          python3 evals/test_no_data_class.py
          python3 evals/test_no_data_class.py --quiet --seed 1 --seed 2 --seed 3
      - name: Tool tests (redaction, permissions, identity, autosave)
        run: python3 tools/test_sbe.py
```

Seven steps, not three. The first blocks on a failed hard gate (a number with no re-run, an untested migration reverse, an unsigned money-path change, an unrun check). The second blocks on an incomplete dossier (a missing artifact, an ADR with no rejected alternatives, an entity with no system of record, a diagram node nothing defines, a dossier that is still the shipped template). The third blocks on a silent-failure lint. Three more run the regression evals, the honesty meta-test and the tool tests, because a gate whose fixtures nobody runs is a gate nobody knows still works. The waiver step (third of the seven) surfaces any design waiver as an annotation and in the job summary, because a waiver examined nothing and the exit code cannot tell you it happened. Advisory mode tells a session; only this CI wiring stops a merge, and that is by design.

Two settings decide whether those steps can see anything.

**`SBE_DOSSIER_ROOT`.** The design step is given the checkout root, and from there it walks for every directory holding a `00-intake.json` or any of `01` through `07`, which is what lets it reach a dossier in `design/<project>/` and what stops a deleted intake file from hiding one. Left empty, finding none is NO-DATA and the step passes, because a change that needs no dossier should not be blocked for not having one, and a T0 change needs none. Set it to where your dossiers live once the repository is supposed to carry one, and a declared root holding none becomes a FAIL. One caveat worth knowing before you set it: a repository that mixes T0 work with dossier work should leave it empty, because a declared root plus a legitimately dossier-free change is a FAIL by design. A directory holding dossier-shaped files that are not live design work (a template library, a finished project) carries a `.sbe-exempt` file whose contents say why, printed on every run:

```yaml
env:
  SBE_DOSSIER_ROOT: design
```

**Signer keys, for the approval gate.** The gate accepts a signed `Approved-by:` trailer only if the host running it actually verified the signature. A stock runner has no public keys imported, so `git` reports that it cannot check the signature, and the gate calls that NO-DATA rather than an approval. That is deliberate: a gate that accepted an unverifiable signature would trust a key nobody on the team recognises while rejecting a known key that had merely expired. Two working configurations:

```yaml
# either import the approvers' public keys into the job
- run: gpg --import <<< "${{ secrets.SBE_APPROVER_PUBKEYS }}"
# or use the keyless path, a Reviewed-in: <review id> trailer on the commit
```

Doing neither is legal and honest: approvals then report NO-DATA in CI, and the binding is enforced wherever your review platform enforces it. Note which of the two paths you are on. The signature path is forgery-resistant: an agent without the private key cannot produce it. The `Reviewed-in:` path is not, because nothing resolves the id and the agent writes the commit message. The gate says so in its own evidence on every run. If you want that path to be a control rather than a pointer, add a step that queries your review platform for the id and fails when it does not exist.

## What you get, and what you do not

You get a colleague that arrives with its checks already run and is bound by law to write UNVERIFIED next to anything that has not cleared them (the label is the agent's to write; no tool applies it), plus a memory that improves through reviewed pull requests. You do not get autonomy, an oracle, or enforcement without the CI step above. Those omissions are the point: see [DESIGN.md](DESIGN.md), "7. The register, and what it refuses".
