# 07. Verification

Every claim this design makes, the check that proves it, and when that check
runs. A claim with no check is listed as such rather than omitted.

| Claim | Check that proves it | When it runs | Verdict when evidence is absent |
|---|---|---|---|
| The commands section matches the CLI command table | `test_sbe_fieldbook.py::test_commands_renderer_recovers_every_cli_command`, which parses the table independently of the renderer and asserts set equality | Every suite run, CI | FAIL if the parse throws; NO-DATA if the table yields zero commands |
| The roles section matches `agents/` | `test_roles_renderer_names_every_agent_file` compares rendered rows against `os.listdir` | Every suite run, CI | NO-DATA naming the empty directory |
| Every check row carries the severity declared in the registry | `test_checks_renderer_reports_declared_severity` reads the registry directly | Every suite run, CI | FAIL carrying the exception |
| Every law row carries its enforcement class | `test_laws_renderer_preserves_enforcement_class` asserts each rendered row ends in a bracketed class present in `DIGEST.md` | Every suite run, CI | NO-DATA if no law line parses |
| The limits section names every limit heading | `test_limits_renderer_names_every_heading` compares against a regex sweep of `docs/KNOWN-LIMITS.md` | Every suite run, CI | NO-DATA naming the file |
| Drift in a bound source is detected | `test_check_fails_when_a_bound_source_moves` mutates a copied source in a temporary tree and asserts a FAIL naming that path | Every suite run, CI | n/a, the test constructs the evidence |
| A stale prose stamp is reported and does not block | `test_stale_stamp_is_no_data_and_exit_zero_under_strict` | Every suite run, CI | n/a |
| Regeneration is deterministic | `test_two_runs_produce_byte_identical_output` renders twice into two temporary trees and compares bytes | Every suite run, CI | n/a |
| The HTML is self-contained and offline | `test_html_requests_no_external_host` asserts no `http://`, `https://` or protocol-relative `src`/`href` on an asset attribute in the emitted HTML | Every suite run, CI | n/a |
| The book carries no em or en dash | `test_no_em_or_en_dash_in_chapters` sweeps every chapter file | Every suite run, CI | n/a |
| Nothing outside the generated markers is rewritten | `test_author_prose_survives_a_regenerate` writes a sentinel outside the markers, regenerates, and asserts the sentinel is byte-identical | Every suite run, CI | n/a |
| The published artifact matches the committed HTML | Nothing. Publication is a manual step and no check compares the published copy to the repository copy | Never | **UNVERIFIED**, and stated as such in the book itself |
| The prose is accurate | Nothing. A `verified-against` stamp records that a human read the chapter at a version; it does not record that they were right | Never | **NO-DATA**, by design, and the book says so |
| The scenarios run on a real Snowflake, Databricks, Power BI or Azure estate | Nothing in this repository. The commands shown are the BrotherSBE commands, which are covered; the vendor-side SQL and pipeline snippets are illustrative and are labelled **UNVERIFIED** where they are not executed here | Never | **UNVERIFIED** at the point of the claim, not in a footnote |

## What runs where

- **In a session**: `sbe book --check` prints its verdicts and exits 0, the
  advisory posture every check in this repository uses locally.
- **In CI**: `sbe book --check --strict` exits nonzero on any FAIL. NO-DATA
  never decides the exit code, consistent with `evals/run_evals.py`.
- **At loop close**: `sbe book` regenerates, and the diff of
  `docs/fieldbook/bindings.json` shows which sections moved.

## The gates this change owes

The intake computed T2, which requires artifacts 01, 02, 03, 05, 06 and 07 and
does not require the technology map. Of the four hard gates:

- **numbers**: not applicable. This change ships no figure that reaches a
  decision.
- **migration**: not applicable. No schema and no destructive data operation.
- **approval**: this repository's merged pull requests carry no independent
  review, which `docs/KNOWN-LIMITS.md` already discloses. This change does not
  improve that, and L9 reports NO-DATA here for the same reason it does
  everywhere else in this repository.
- **ran**: applies. The test module named above must execute with exit 0 and a
  nonzero duration before this design is called done.
