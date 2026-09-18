# OpenAzrael Artifact Index

## Current canonical checkpoint
- `v107-context-v15` — technical base v107 plus current context/Git/quality layer.

## Quality / known-good baseline
- `docs/KG001_ACCEPTANCE_PLAN.md`
- `data/kg001_acceptance_contract.json`
- `tools/validate_kg001_contract.py`
- `docs/TEST_MATRIX.md`

## Runtime IR / demo logic
- `data/gameplay_event_graph_v87.json` / `GAMEPLAY_EVENT_GRAPH_V87.md` / `tools/audit_gameplay_event_graph_v87.py`
- `data/xaf_trigger_evidence.json` / `tools/extract_xaf_triggers.py` / `tools/validate_demo_runtime_ir.py`

## Current forensic anchors
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
