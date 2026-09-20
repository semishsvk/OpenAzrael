# OpenAzrael Artifact Index

## Current canonical checkpoint
- `v116-context-v31` — technical base v116 plus current context/Git/quality/architecture/documentation-consistency layer.

## KG-001 independent audit hardening v117 / context v31
- `.github/workflows/kg001-source-safe.yml`
- `tools/requirements-kg001-source-safe.txt`
- `data/tests/kg001_toolchain_contract_v117.json`
- `tools/validate_kg001_toolchain_v117.py`
- `tools/write_kg001_build_manifest.py`
- `export_presets.cfg` — `Windows Candidate 2`
- `tools/validate_kg001_export_preset_v117.py`
- `scripts/kg001_visual_capture_v117.gd`
- `tools/validate_kg001_visual_capture_v117.py`
- `data/tests/kg001_visual_capture_contract_v117.json`
- `tools/run_kg001_candidate2_windows_v117.ps1` — thin local Windows restore → canonical runner → optional promotion → export wrapper
- `tools/validate_candidate2_windows_wrapper_v117.py`
- run-scoped Candidate provenance implemented in `scripts/candidate_diagnostics_v116.gd`
- Issue #6 regression matrix: canonical R1/R7/R8 floor probes
- Issue #9 hardening: PCM non-silence + Master-bus capture
- Issue #11 hardening: used indexed palette key + fail-closed ambiguity + MASK hidden-RGB edge bleed
- PR #12 remains draft pending restored-asset runtime, graphical capture and G10

## KG-001 test-build hardening v118
- `tools/validate_kg001_candidate2_asset_set_v118.py` — complete restored-asset gate
- `tools/write_kg001_build_manifest.py` — schema v2 asset + runtime-source/export identity fingerprints
- `tools/promote_kg001_candidate_results_v118.py` — shared post-clean/post-export evidence promotion
- `data/tests/kg001_test_build_contract_v118.json`
- `tools/validate_kg001_test_build_contract_v118.py`
- `tools/run_kg001_candidate2_windows_v117.ps1` — clean export, exported-EXE startup smoke, package hashes and test-build receipt
- runtime receipt: ignored `.tmp/kg001/kg001_test_build_receipt_v118.json`
- distribution sidecar: ignored `exports/OpenAzrael-KG001-Candidate2-v116.test-build.json`
- `READY_FOR_G10_MANUAL_TEST` never closes Issues #6/#9/#11 and never authorizes `demo-known-good-001`

## KG-001 Candidate 2 test-build hardening v118
- `tools/validate_kg001_candidate2_asset_set_v118.py` — complete restored asset gate: 3 rooms / 8 runtime WAV / 86 Classic / 10 indexed-key # textures
- `tools/write_kg001_build_manifest.py` — build manifest schema v2 with runtime-source and acceptance-contract fingerprints
- `tools/validate_kg001_build_manifest_v118.py`
- `data/tests/kg001_test_build_contract_v118.json`
- `tools/validate_kg001_test_build_contract_v118.py`
- `tools/promote_kg001_candidate_results_v118.py` — shared post-observation/post-export tracked evidence promotion
- `tools/run_kg001_candidate2_windows_v117.ps1` — canonical Windows restore → fresh-checkout+visual → export → EXE startup smoke → receipt → optional promotion
- runtime receipt: ignored `.tmp/kg001/kg001_test_build_receipt_v118.json`
- distribution sidecar: ignored `exports/OpenAzrael-KG001-Candidate2-v116.test-build.json`
- `READY_FOR_G10_MANUAL_TEST` never closes release blockers or authorizes `demo-known-good-001`

## Bug reporting / diagnostics
- `docs/BUG_REPORTING.md`
- `.github/ISSUE_TEMPLATE/bug_report.yml`
- F11 implementation in `scripts/candidate_diagnostics_v116.gd`
- source contract in `tools/validate_candidate_diagnostics_v116.py`

## Localization architecture
- `docs/LOCALIZATION_ARCHITECTURE.md`
- `docs/DECISIONS.md` ADR-024
- implementation deliberately deferred until after the first clean Candidate 2 runtime/manual validation

## KG-001 Candidate 2 diagnostics v116
- `docs/KG001_CANDIDATE_DIAGNOSTICS_V116.md`
- `scripts/candidate_diagnostics_v116.gd`
- `scripts/kg001_trigger_debug_v116.gd`
- `tools/validate_candidate_diagnostics_v116.py`
- `data/tests/kg001_candidate_diagnostics_contract_v116.json`
- integrated into `tools/run_kg001_candidate_v112.py`

## WORLD action-record lifecycle v115
- `WORLD_ACTION_RECORD_LIFECYCLE_V115.md`
- `tools/analyze_world_action_lifecycle_v115.py`
- `tools/validate_world_action_lifecycle_v115.py`
- `data/world_action_lifecycle_v115.json`

## WORLD section-6 serializer v114
- `WORLD_SOUND_SERIALIZER_V114.md`
- `tools/analyze_world_sound_serializer_v114.py`
- `tools/validate_world_sound_serializer_v114.py`
- `data/world_sound_serializer_v114.json`

## WORLD sound-record fields v113
- `WORLD_SOUND_RECORD_FIELDS_V113.md`
- `tools/analyze_world_sound_record_fields_v113.py`
- `tools/validate_world_sound_record_fields_v113.py`
- `data/world_sound_record_fields_v113.json`

## KG-001 v112 candidate workflow
- `docs/KG001_CANDIDATE_RUNNER_V112.md`
- `tools/run_kg001_candidate_v112.py`
- `tools/validate_kg001_candidate_v112.py`
- `data/tests/kg001_candidate_runner_contract_v112.json`
- `tools/kg001_status_v112.py`
- `data/tests/kg001_status_v112.json`
- `docs/KG001_MANUAL_SANITY_CHECKLIST.md`
- `data/tests/kg001_manual_sanity_template.json`

## KG-001 v111 full demo/status
- `docs/KG001_FULL_DEMO_V111.md`
- `scripts/kg001_full_demo_runner_v111.gd`
- `tools/validate_kg001_full_demo_v111.py`
- `data/tests/kg001_full_demo_contract_v111.json`
- `tools/kg001_status_v111.py`
- `data/tests/kg001_status_v111.json`
- `docs/KG001_STATUS_V111.md`

## Major legacy color-key regression — Issue #11
- `tools/texture_pipeline/legacy_colorkey.py`
- `tools/texture_pipeline/azf_decode_v14.py`
- `tools/texture_pipeline/export_xaf_glb_v8.py`
- `tools/validate_kg001_texture_colorkey_v116.py`
- `data/tests/kg001_texture_colorkey_contract_v116.json`
- Candidate restore integration in `tools/restore_candidate_assets.py`
- known R1 regressions: KEYHOLE# and TONG6 -> MINETON#
- broader original transparency/blending semantics remain HOLD
- GitHub Issue #11 remains open pending corrected asset/runtime/manual visual retest

## Major physical-audio regression — Issue #9
- `scripts/kg001_audio_runtime_runner_v116.gd`
- `tools/validate_kg001_audio_runtime_v116.py`
- `data/tests/kg001_audio_runtime_contract_v116.json`
- source-safe `data/audio/legacy_world_ir.json`
- reproducible local restore: `tools/restore_candidate_assets.py` and `tools/prepare_candidate_audio.py`
- recovered ambient count contract: R1=2, R7=3, R8=2
- GitHub Issue #9 remains open pending Candidate 2 runtime/manual audibility retest

## Critical collision regression — Issue #6
- source fix in `scripts/room_manager.gd`: two-sided legacy `ConcavePolygonShape3D` collision
- physical regression in `scripts/kg001_room_trigger_runner_v110.gd`
- source validator coverage in `tools/validate_kg001_room_trigger_v110.py`
- GitHub Issue #6 remains open pending corrected-build runtime/manual retest

## KG-001 v110 room/trigger
- `docs/KG001_ROOM_TRIGGER_V110.md`
- `scripts/kg001_room_trigger_runner_v110.gd`
- `tools/validate_kg001_room_trigger_v110.py`
- `data/tests/kg001_room_trigger_contract_v110.json`

## KG-001 v109 headless
- `docs/KG001_HEADLESS_V109.md`
- `scripts/kg001_headless_runner_v109.gd`
- `tools/validate_kg001_headless_v109.py`
- `data/tests/kg001_headless_contract_v109.json`

## KG-001 v108 state-space
- `docs/KG001_STATE_SPACE_V108.md`
- `tools/kg001_state_space_v108.py`
- `data/tests/kg001_state_space_v108.json`

## Quality / known-good baseline
- `docs/KG001_ACCEPTANCE_PLAN.md`
- `data/kg001_acceptance_contract.json`
- `tools/validate_kg001_contract.py`
- `docs/TEST_MATRIX.md`

## Runtime IR / demo logic
- `data/gameplay_event_graph_v87.json` / `GAMEPLAY_EVENT_GRAPH_V87.md` / `tools/audit_gameplay_event_graph_v87.py`
- `data/xaf_trigger_evidence.json` / `tools/extract_xaf_triggers.py` / `tools/validate_demo_runtime_ir.py`

## Current forensic anchors
- `WORLD_ACTION_RECORD_LIFECYCLE_V115.md` / `tools/analyze_world_action_lifecycle_v115.py`
- `WORLD_SOUND_SERIALIZER_V114.md` / `tools/analyze_world_sound_serializer_v114.py`
- `WORLD_SOUND_RECORD_FIELDS_V113.md` / `tools/analyze_world_sound_record_fields_v113.py`
- `WORLD_PUZZLE_SOUND_BRIDGE_V107.md` / `tools/analyze_world_puzzle_sound_bridge_v107.py`
- `WORLD_RUNTIME_SERIALIZATION_V106.md` / `tools/analyze_world_runtime_serialization_v106.py`
- `PUZZLES_ALTERNATIVE_OPEN_PATHS_V105.md`
- `PUZZLES_DIRECT_FOPEN_CLASSIFICATION_V104.md`
- `PUZZLES_FILEIO_CENSUS_V103.md`
- `PUZZLES_RECORD_GRAMMAR_V90.md`
- `GAMEPLAY_EVENT_GRAPH_V87.md`
- `AUDIO_CLASSIC_RENDERER_ACTIVATION_V86.md`
- `AUDIO_ONE_COMMAND_PARITY_V84.md`
- `docs/DEMO_COORDINATE_CLOSURE_V67.md`
- `docs/GRAPHICS_PIPELINE_V44.md`

The full derived v107 forensic JSON remains outside Git under the repository-safety policy because it contains reproducible commercial-derived record bytes.

## Repository/backup
- `docs/BACKUP_VERSIONING_POLICY.md`
- `docs/GITHUB_SYNC_SCOPE.md`
- `docs/GIT_BASELINE.md`
- `data/backup/source_fingerprints.json`
