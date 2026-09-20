# OpenAzrael Artifact Index

## Current canonical checkpoint
- `v116-context-v30` — technical base v116 plus current context/Git/quality/architecture/documentation-consistency layer.

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
