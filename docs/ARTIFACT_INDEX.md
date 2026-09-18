# OpenAzrael Artifact Index

## Current canonical checkpoint
- `v113-context-v21` — technical base v113 plus current context/Git/quality layer.

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
