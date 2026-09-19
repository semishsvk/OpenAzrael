# OpenAzrael Artifact Index

## Current canonical checkpoint
- `v116-context-v26` — technical base v116 plus current context/Git/quality/architecture/documentation-consistency layer.

## Localization architecture
- `docs/LOCALIZATION_ARCHITECTURE.md`
- `docs/DECISIONS.md` ADR-024
- implementation deliberately deferred until after Candidate 1 runtime/manual validation

## Texture Lab RT-POC-01
- `docs/TEXTURE_LAB_RT_POC_01.md`
- `docs/TEXTURE_LAB_LOCAL_RUNBOOK.md`
- `tools/texture_lab/oa_tex_scan.py`
- `tools/texture_lab/oa_tex_enhance.py`
- `tools/texture_lab/oa_tex_validate.py`
- `tools/texture_lab/oa_tex_compare.py`
- `tools/texture_lab/oa_tex_tile.py`
- `tools/texture_lab/oa_tex_atlas.py`
- `tools/texture_lab/oa_tex_sampling_audit.py`
- `tools/texture_lab/oa_tex_structural_drift.py`
- `tools/texture_lab/oa_tex_calibrate_drift.py`
- `tools/texture_lab/oa_tex_run_poc.py`
- `tools/texture_lab/oa_tex_restore.py`
- `tools/texture_lab/oa_tex_realesrgan_bootstrap.py`
- `tools/texture_lab/oa_tex_realesrgan_doctor.py`
- `tools/texture_lab/oa_tex_recreate.py`
- `tools/texture_lab/oa_tex_ai_bakeoff.py`
- `tools/texture_lab/oa_tex_local_preflight.py`
- `tools/texture_lab/oa_tex_stage_gate.py`
- `tools/texture_lab/oa_tex_review_report.py`
- `tools/texture_lab/oa_tex_comfy_doctor.py`
- `tools/texture_lab/oa_tex_qwen_bootstrap.py`
- `tools/texture_lab/oa_tex_qwen_preflight.py`
- `tools/texture_lab/requirements-source-safe.txt`
- `tools/texture_lab/config/enhance.json`
- `tools/texture_lab/config/rt_poc_01_selection.json`
- `data/texture_lab/rt_poc_01_sampling_review.json`
- `data/texture_lab/rt_poc_01_drift_baseline.json`
- `data/texture_lab/rt_poc_01_ai_policy_summary.json`
- `tools/texture_lab/config/ai_backends.json`
- `tools/texture_lab/config/model_registry.json`
- `tools/texture_lab/config/ai_review_policy.json`
- `tools/texture_lab/config/ai_smoke_sets.json`
- `tools/texture_lab/config/qwen_2511_contract.json`
- `tools/texture_lab/workflows/qwen_2511_openazrael_api.json`
- `tools/texture_lab/profiles/base_preserve.json`
- `tools/texture_lab/profiles/recreate_profiles.json`
- `tools/texture_lab/oa_tex_prompt.py`
- `tools/texture_lab/godot/texture_lab.gd`
- `tools/texture_lab/godot/texture_lab.tscn`
- `tools/texture_lab/validate_godot_lab.py`
- `tests/test_texture_lab_rt_poc_01.py`
- generated Classic/Enhanced/AI pixels remain excluded from Git by ADR-025

## KG-001 Candidate 1 diagnostics v116
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


## Texture Lab RT-POC-01 source checkpoint
- `data/texture_lab/rt_poc_01_source_status.json` — machine-readable boundary between source-safe/CI readiness and still-unexecuted real Real-ESRGAN, Qwen and Godot Texture Lab runtime evidence.


## Texture Lab production selection
- `data/texture_lab/production_selection.json` — empty-by-default Remastered production-selection registry; explicit selections are hash-bound to current reviewed/approved stage evidence.
- `tools/texture_lab/oa_tex_production_selection.py` — select/status/revoke tooling; never copies pixels or auto-selects a winner.


## Texture Lab runtime presentation bridge
- `tools/texture_lab/oa_tex_runtime_manifest.py` — builds Classic/Enhanced/Remastered local presentation manifests; Remastered uses only current explicit production selections and otherwise falls back to Classic.
- `tools/texture_lab/godot/texture_profile_resolver.gd` — isolated manifest-only Godot resolver used by Texture Lab profile preview; rejects unsafe paths and never reads stage/selection evidence directly.


## Texture Lab manual review evidence
- `tools/texture_lab/oa_tex_manual_review.py` — init/record/status workflow for per-texture human QA; stage approval requires a current PASS structured review.
- local records live under `.local/texture_lab/manual_reviews/rt_poc_01/` and remain outside Git because they are bound to local generated commercial-derived candidates.


## Texture Lab staged review/runtime contracts
- `tools/texture_lab/oa_tex_contract_validate.py` — cross-file CI validator for selection/policy/stages/model/backend/Qwen consistency.
- `tools/texture_lab/oa_tex_review_profile.py` — creates non-exportable stage-specific Godot review manifests and the local `review_current.json` convenience pointer.
- named AI candidates are isolated under ignored `assets/textures/ai_restored/_runs/<preset>/` / `ai_recreated/_runs/<preset>/` namespaces.
