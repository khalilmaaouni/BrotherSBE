# Active write fences (one writer per file, L13)

| Stream | Agent | Scope | State |
|---|---|---|---|
| baseline | orchestrator (Fable) | release-control/baseline/** | open |
| ledger | worktree agent 1 (sonnet) | release-control/{registries,schemas,generated}/**, release-control/README.md, tools/sbe_release_control.py, tools/test_sbe_release_control.py | open |
| validation-kits | worktree agent 2 (sonnet) | release-control/validation-kits/** | open |
| release-pipeline | worktree agent 3 (sonnet) | .github/workflows/release.yml, scripts/release-archive.sh, tools/sbe_release_bundle.py, tools/test_sbe_release_bundle.py, docs/RELEASE-PIPELINE.md | open |
| shared/generated | integrator only | CHANGELOG.md, CHECKSUMS.sha256, VERSION, manifests, .github/workflows/brothersbe-gates.yml | reserved |

Audit workflow agents are read-only by prompt (six lenses, no write scope).
