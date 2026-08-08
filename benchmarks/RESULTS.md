# BrotherSBE comparative benchmark, status

STATUS: UNRUN. 0 of 16 row(s) have been run by a named person.

This evaluation is UNRUN. Not pending, not in progress, not estimated: no person has run any row, so every measure below reads NO-DATA and the PROVENANCE column reads UNRUN. Any release document quoting this file must say the evaluation is unrun.

Defects are planted in advance, with known file and line, by `benchmarks/fixture_repo.py` against the manifest in `benchmarks/defects.json`. Without that, `Defects missed` would be unmeasurable by construction, and any number printed for it would be fiction.

NO-DATA means the measure could not be computed from the run's own artifacts. It is not zero, it is never summed or ranked, and it neither passes nor blocks anything.

| Scenario | Estate | Defects found | Defects missed | Wall clock (s) | Tokens | Operator corrections | False blocks | Reviewer findings | PROVENANCE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1-migration | vanilla-claude-code | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S1-migration | feature-dev | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S1-migration | superpowers | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S1-migration | brothersbe | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S2-api-contract | vanilla-claude-code | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S2-api-contract | feature-dev | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S2-api-contract | superpowers | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S2-api-contract | brothersbe | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S3-data-pipeline | vanilla-claude-code | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S3-data-pipeline | feature-dev | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S3-data-pipeline | superpowers | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S3-data-pipeline | brothersbe | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S4-incident | vanilla-claude-code | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S4-incident | feature-dev | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S4-incident | superpowers | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |
| S4-incident | brothersbe | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | NO-DATA | UNRUN |

### Rows a comparison may not be built on

- S1-migration / vanilla-claude-code: no run exists, so the provenance column reads UNRUN
- S1-migration / feature-dev: no run exists, so the provenance column reads UNRUN
- S1-migration / superpowers: no run exists, so the provenance column reads UNRUN
- S1-migration / brothersbe: no run exists, so the provenance column reads UNRUN
- S2-api-contract / vanilla-claude-code: no run exists, so the provenance column reads UNRUN
- S2-api-contract / feature-dev: no run exists, so the provenance column reads UNRUN
- S2-api-contract / superpowers: no run exists, so the provenance column reads UNRUN
- S2-api-contract / brothersbe: no run exists, so the provenance column reads UNRUN
- S3-data-pipeline / vanilla-claude-code: no run exists, so the provenance column reads UNRUN
- S3-data-pipeline / feature-dev: no run exists, so the provenance column reads UNRUN
- S3-data-pipeline / superpowers: no run exists, so the provenance column reads UNRUN
- S3-data-pipeline / brothersbe: no run exists, so the provenance column reads UNRUN
- S4-incident / vanilla-claude-code: no run exists, so the provenance column reads UNRUN
- S4-incident / feature-dev: no run exists, so the provenance column reads UNRUN
- S4-incident / superpowers: no run exists, so the provenance column reads UNRUN
- S4-incident / brothersbe: no run exists, so the provenance column reads UNRUN

`python3 benchmarks/report.py --mode comparison` refuses while any of the above stands.

### How a row gets filled

1. `python3 benchmarks/fixture_repo.py --out <empty dir outside this repo>`
2. Run the scenario runbook in `benchmarks/scenarios/` against one estate, capturing the artifacts it names.
3. `python3 benchmarks/score_run.py --run <run dir> --out <run dir>/<run id>.scored.json`
4. `python3 benchmarks/report.py --scored benchmarks/runs --out benchmarks/RESULTS.md`

