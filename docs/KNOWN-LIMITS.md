# Known limits

Every law already states what its machinery does not do, but those statements
live inside the digest and the law text, where the honest half of the product
is the hardest part to read. This page collects them: one heading per limit,
each naming the law it qualifies and the file where the full text lives.
Nothing here is new; a limit stated only on this page and nowhere else would
be a bug in this page.

## The spine is a discipline, not a control

"Design before verification" and "install the check before writing the work"
are [human] lines: no tool computes whether you did. Full text: `SKILL.md`
(The spine), `DIGEST.md`.

## Nothing detects that a change needed an approval (L9)

The gate verifies an approval that was declared. It cannot notice a money-path
change that declared nothing, and nothing resolves a `Reviewed-in:` id, which
is why that path reports NO-DATA rather than an approval. Full text:
`SKILL.md` L9 and `LAWS-REFERENCE.md` (the hard gates).

## The forcing conditions are read by a person (L6)

Stop-on-ambiguity, contradiction, gate collision, and disproven assumption are
[human]: the checkpoint shape is prose the session follows or does not. Full
text: `SKILL.md` L6.

## The fence checks read registries, not the world (L13)

Fence hygiene and budget-vs-tier run only over registries named in
`BROTHERSBE_REGISTRIES`, and only over fence lines containing the word
"agent". Writing the fence, comparing scopes, and resuming after a kill are
human. Full text: `SKILL.md` L13, `LAWS-REFERENCE.md`.

## Blast radius revokes nothing (L14)

"No apply rights on production state" is a working rule plus whatever access
control your estate has. Nothing here can revoke a credential your shell
already holds. Full text: `SKILL.md` L14.

## The CI workflow guards nothing until you copy it (L16)

`--strict` blocks only in a repository that wired it. No CODEOWNERS and no
branch protection ships, so nothing makes editing the workflow require a
review; that is your repository's setting. Full text: `SKILL.md` L16.

## Most of the close is human (L17)

Only the vault session log has a check, and only where `BROTHERSBE_VAULT`
points at a vault, which the shipped CI does not set: on a stock runner every
ledger check is NO-DATA at exit 0. Open items, the failures index, the
scorecard and the self-score cap are human review. Full text: `SKILL.md` L17.

## Telemetry observes, it never decides

The SessionEnd hook writes the ledger and decides nothing; no CI step reads
it. The checks fed by it are named on their own digest lines. Full text:
`DIGEST.md`, `LAWS-REFERENCE.md` (Telemetry).

## The UNVERIFIED label is the agent's to write

No tool applies it. A session that fails to label unverified output is not
caught by a check. Full text: `SKILL.md` L7 and L16, `DIGEST.md`.

## The hollowing sweep is not a proof

The meta-test hollows each check's own declared worked example, prints its
coverage, skipped cases and exemptions, and claims nothing about inputs no
fixture plants. Full text: `INVARIANTS.md` (what the register does not claim),
`evals/README.md`.

## Never run in anyone else's CI

Every green run this project cites happened in its own repository or on the
estate it was built on. No external adoption, and no second estate, is
claimed anywhere.

## Windows is untested

The shipped CI runs Linux and macOS. The two `sh` tools and the POSIX file
modes have never been exercised on Windows, and `SECURITY.md` already treats a
POSIX mode there as a courtesy.

## Every threshold was measured on one estate

`tables/`, the RUBRIC baselines, and the lint's own numbers were measured
where this project was built. Re-measure on yours; NO-DATA is a legal score.
Full text: `README.md` (What this is not), `RUBRIC.md`, `INVARIANTS.md`.
