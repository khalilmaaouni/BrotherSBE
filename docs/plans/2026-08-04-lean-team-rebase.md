# Lean team program rebase, 2026-08-04 night

LT-001 deliverable.
This
file is the repo home of the vault draft written the same night.

## Baseline

- main = d137832e825b7cc99378c441b64b9d1e91d6c3a9 (PR #12 merged 2026-08-04T13:48:12Z).
- Version 1.0.0-rc.4 across all four declaration sites.
- Release battery state: 23 of 24 steps exit 0 on this machine; the single red
  is cache-economy reading personal vault telemetry, NO-DATA anywhere else.

## Exclusion register status (every row now external, none is backlog)

- CR-01, 02, 04, 05, 09, 12, 14, 15, 16, 17: closed by the release lane (PR #10).
- CR-06, CR-08: closed by PR #11. CR-07, CR-10, CR-03: closed by PR #12.
- Release-closure extras: doc mirrors, SECURITY recount, checksums, merge,
  branch deletion, archive-tag decision, versioning: all done (PRs #10-#12,
  founder tag decision recorded: 17 pushed, 4 held).
- Human-only gates stay OPEN and are not program work: usability studies,
  marketplace acceptance, Windows verification, artifact signing, second
  independent RELEASE decision. NO-GO on a 1.0.0 tag stands.

## Interface changes since the lean plan was written

1. sbe status (single-project) discovers dossiers through the team walker when
   the flat layout is absent; flat wins when both exist; exit 1 on open
   findings. Consumers of "status always exits 0" are wrong now (the consumer
   CI action was already corrected).
2. sbe verify mints design/gate/score receipts into .sbe/evidence (generate
   all, then write all; dirty tree receipts read NO-DATA naming the dirty
   state). LT-101's "requiredEvidenceKind: ran" flows through sbe evidence run
   exactly as planned; no competing mechanism was added.
3. skills/start, next, status, verify consume sbe status --json, sbe doctor
   --json, sbe status --team --json. Rung 5 recommends verify only on a FAIL
   or a named obligation. New skills (work, handover) MUST follow this
   pattern from birth: JSON fields, never prose interpretation.
4. install.sh run_doctor grades the TARGET; test_sbe_install.py is 23 tests
   including installed-layout hook replay and activation argv proof. LT-402's
   hook work must keep those tests green.
5. tools/sbe_release_invariant.py gates distributable bytes vs VERSION;
   every LT task that touches src/, tools/, skills/, hooks/, agents/,
   scripts/, .claude-plugin/ or install.sh requires a version move in the
   same PR. Plan accordingly: batch LT waves into PRs that carry one bump.
6. The honesty sweep discovers all five registries (31 checks); any new
   registry (LT-201 reviewroute checks, LT-401 instruction surface) MUST add
   an ADAPTERS entry in evals/test_no_data_class.py in the same change.
7. The review record write path (CR-09) exists at src/brothersbe read path
   with commit binding and staleness; LT-202 extends that schema, never
   rebuilds it.

## Surviving tasks (14 implementation rows, unchanged in intent)

LT-101, 102, 103, 201, 202, 203, 301, 302, 303, 401, 402, 501, 502, 503.
File paths in the plan survive with these corrections:
- cli.py is no longer contested; LT-201 and LT-301 integrate directly.
- skills/status and skills/next already render engine JSON; LT-302.B's status
  integration extends the same fields.
- The agent-definition test surface is tools/test_sbe.py's agent audits plus
  claude plugin validate.

## Removed tasks

None removed; nothing in the lean plan duplicates the closed CR work after
the corrections above. The plan's own removed-architecture register stands.

## Execution order and dependency matrix

Chain: LT-101 -> LT-102 -> LT-103 (vertical slice 1, /brothersbe:work), then
LT-201 -> LT-202 -> LT-203 (slice 2, review), then LT-301 -> LT-302 -> LT-303
(slice 3, handover), then LT-401 -> LT-402 (trust boundary), then LT-501 ->
LT-502 -> LT-503 (consolidation). Permitted parallel pairs (plan section 16):
LT-201 design during LT-101 implementation; LT-301 design during LT-203
fixtures; LT-401 threat model during LT-301 test design; LT-501 fixtures
during LT-502 docs. Max three writers, one writer per file, checksums and
version bump last per PR wave.

## Wave-to-PR mapping (respects the release invariant)

- PR wave A: LT-101 + LT-102 + LT-103 (one rc bump).
- PR wave B: LT-201 + LT-202 + LT-203 (one rc bump).
- PR wave C: LT-301 + LT-302 + LT-303 (one rc bump).
- PR wave D: LT-401 + LT-402 (one rc bump).
- PR wave E: LT-501 + LT-502 + LT-503 (one rc bump).
Each wave: dossier-guided briefs, isolated worktrees, Fable integrates,
combined suites, manifest last, CI required checks gate the merge.

## LT-101 inventory (Haiku scout, verified 2026-08-04 night, nothing absent)

- work.py: _load_plan_file:52, _validate_plan:68, _find_task:94, _find_record:101,
  _dependency_problem:111, _first_command:136, _evidence_dir:144, _matching_receipt:148,
  cmd_start:208, cmd_check:364, cmd_finish:471, cmd_remove:557, main:666.
- tasks.py: REGISTRY_REL:84, DEFAULT_EVIDENCE_DIR:97, RECORD_FIELDS:104 (id, agent,
  role, worktree, ownedPaths, readOnlyPaths, baseCommit, expiry, status,
  verifyCommand, evidenceId, openedAt, closedAt), load_registry:153,
  save_registry:191 (tempfile + os.replace + flock), registry_path:149.
- sbe_plan.py task fields (:1012-1024): id, title, role, dependsOn, owns, readOnly,
  acceptance, verificationCommands, requiredEvidence, requiredReviewers,
  dossierSources. PLAN_CHECKS registry :766-830 (nine checks).
- Brief mapping: scope=owns, mustNotTouch=readOnly plus coordination files,
  acceptance=acceptance, verificationCommands as-is, requiredEvidenceKind from
  requiredEvidence, dependencies=dependsOn.
- Agent frontmatter template: agents/backend-reviewer.md:1-6 (name, description,
  tools list, model). Seven reviewer agents exist.
- test_sbe_work.py pins eleven classes including TestNoMergeLaw:717 (source-level
  no merge/rebase/push argv) which the new brief command must keep green.
