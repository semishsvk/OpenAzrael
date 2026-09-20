#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_CHECKPOINT="v116-context-v31"
errors=[]

def req(p):
    p=ROOT/p
    if not p.exists():
        errors.append(f"missing: {p.relative_to(ROOT)}")

for p in [
    "OPENAZRAEL_CONTEXT.md",
    "docs/PROJECT_STATE.md",
    "docs/LAST_SESSION.md",
    "docs/DECISIONS.md",
    "docs/BACKUP_VERSIONING_POLICY.md",
    "docs/GIT_BASELINE.md",
    "docs/KG001_ACCEPTANCE_PLAN.md",
    "data/project_context.json",
    "data/kg001_acceptance_contract.json",
    "data/gameplay_event_graph_v87.json",
    "data/xaf_trigger_evidence.json",
    "GAMEPLAY_EVENT_GRAPH_V87.md",
    "tools/validate_demo_runtime_ir.py",
    "tools/kg001_state_space_v108.py",
    "data/tests/kg001_state_space_v108.json",
    "docs/KG001_STATE_SPACE_V108.md",
    "scripts/kg001_headless_runner_v109.gd",
    "tools/validate_kg001_headless_v109.py",
    "data/tests/kg001_headless_contract_v109.json",
    "docs/KG001_HEADLESS_V109.md",
    "scripts/kg001_room_trigger_runner_v110.gd",
    "tools/validate_kg001_room_trigger_v110.py",
    "data/tests/kg001_room_trigger_contract_v110.json",
    "docs/KG001_ROOM_TRIGGER_V110.md",
    "scripts/kg001_full_demo_runner_v111.gd",
    "tools/validate_kg001_full_demo_v111.py",
    "data/tests/kg001_full_demo_contract_v111.json",
    "tools/kg001_status_v111.py",
    "data/tests/kg001_status_v111.json",
    "docs/KG001_FULL_DEMO_V111.md",
    "docs/KG001_STATUS_V111.md",
    "tools/run_kg001_candidate_v112.py",
    "tools/validate_kg001_candidate_v112.py",
    "data/tests/kg001_candidate_runner_contract_v112.json",
    "tools/kg001_status_v112.py",
    "data/tests/kg001_status_v112.json",
    "docs/KG001_CANDIDATE_RUNNER_V112.md",
    "docs/KG001_MANUAL_SANITY_CHECKLIST.md",
    "data/tests/kg001_manual_sanity_template.json",
    "data/evidence/evidence_registry.json",
    "data/backup/source_fingerprints.json",
    "PUZZLES_FILEIO_CENSUS_V103.md",
    "WORLD_RUNTIME_SERIALIZATION_V106.md",
    "WORLD_PUZZLE_SOUND_BRIDGE_V107.md",
    "PUZZLES_ALTERNATIVE_OPEN_PATHS_V105.md",
    "data/world_runtime_serialization_v106.json",
    "WORLD_SOUND_RECORD_FIELDS_V113.md",
    "tools/analyze_world_sound_record_fields_v113.py",
    "tools/validate_world_sound_record_fields_v113.py",
    "data/world_sound_record_fields_v113.json",
    "WORLD_SOUND_SERIALIZER_V114.md",
    "tools/analyze_world_sound_serializer_v114.py",
    "tools/validate_world_sound_serializer_v114.py",
    "data/world_sound_serializer_v114.json",
    "WORLD_ACTION_RECORD_LIFECYCLE_V115.md",
    "tools/analyze_world_action_lifecycle_v115.py",
    "tools/validate_world_action_lifecycle_v115.py",
    "data/world_action_lifecycle_v115.json",
    "docs/LOCALIZATION_ARCHITECTURE.md",
    "docs/KG001_CANDIDATE_DIAGNOSTICS_V116.md",
    "scripts/candidate_diagnostics_v116.gd",
    "scripts/kg001_trigger_debug_v116.gd",
    "tools/validate_candidate_diagnostics_v116.py",
    "data/tests/kg001_candidate_diagnostics_contract_v116.json",
    "scripts/kg001_audio_runtime_runner_v116.gd",
    "tools/validate_kg001_audio_runtime_v116.py",
    "data/tests/kg001_audio_runtime_contract_v116.json",
    "tools/texture_pipeline/legacy_colorkey.py",
    "tools/validate_kg001_texture_colorkey_v116.py",
    "data/tests/kg001_texture_colorkey_contract_v116.json",
    "data/audio/legacy_world_ir.json",
    "tools/restore_candidate_assets.py",
    "tools/prepare_candidate_audio.py",
    "docs/BUG_REPORTING.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/workflows/kg001-source-safe.yml",
    "export_presets.cfg",
    "tools/requirements-kg001-source-safe.txt",
    "tools/validate_kg001_toolchain_v117.py",
    "data/tests/kg001_toolchain_contract_v117.json",
    "tools/write_kg001_build_manifest.py",
    "tools/validate_kg001_export_preset_v117.py",
    "scripts/kg001_visual_capture_v117.gd",
    "tools/validate_kg001_visual_capture_v117.py",
    "data/tests/kg001_visual_capture_contract_v117.json",
    "tools/validate_source_safe_asset_loading_v117.py",
    "tools/run_kg001_candidate2_windows_v117.ps1",
    "tools/validate_candidate2_windows_wrapper_v117.py",
    "tools/validate_kg001_candidate2_asset_set_v118.py",
    "tools/promote_kg001_candidate_results_v118.py",
    "data/tests/kg001_test_build_contract_v118.json",
    "tools/validate_kg001_test_build_contract_v118.py",
    "tools/validate_kg001_build_manifest_v118.py",
    "tools/validate_kg001_candidate2_asset_set_v118.py",
    "tools/promote_kg001_candidate_results_v118.py",
    "data/tests/kg001_test_build_contract_v118.json",
    "tools/validate_kg001_test_build_contract_v118.py",
]:
    req(p)

try:
    c=json.loads((ROOT/"data/project_context.json").read_text(encoding="utf-8"))
    if c.get("checkpoint")!=EXPECTED_CHECKPOINT:
        errors.append("checkpoint drift")
    if c.get("current_forensics",{}).get("world_runtime_loader")!="VERIFIED":
        errors.append("WORLD loader status drift")
    if c.get("current_forensics",{}).get("puzzles_world_sound_exact_correspondence")!="VERIFIED":
        errors.append("v107 sound bridge status drift")
    if c.get("quality",{}).get("kg001_acceptance_plan")!="ACCEPTED":
        errors.append("KG-001 acceptance status drift")
    if c.get("quality",{}).get("kg001_state_model")!="SOURCE_MODEL_PASS":
        errors.append("KG-001 v108 state-model status drift")
    if c.get("quality",{}).get("kg001_headless_source_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 v109 headless source-contract drift")
    if c.get("quality",{}).get("kg001_headless_runtime")!="NOT_EXECUTED":
        errors.append("KG-001 v109 runtime status drift")
    if c.get("quality",{}).get("kg001_room_trigger_source_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 v110 room/trigger source-contract drift")
    if c.get("quality",{}).get("kg001_room_trigger_runtime")!="NOT_EXECUTED":
        errors.append("KG-001 v110 runtime status drift")
    if c.get("quality",{}).get("kg001_full_demo_source_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 v111 full-demo source-contract drift")
    if c.get("quality",{}).get("kg001_full_demo_runtime")!="NOT_EXECUTED":
        errors.append("KG-001 v111 runtime status drift")
    if c.get("quality",{}).get("kg001_candidate_runner")!="SOURCE_CONTRACT_READY":
        errors.append("KG-001 v112 candidate runner drift")
    if c.get("quality",{}).get("kg001_status_engine")!="EVIDENCE_DRIVEN_V112":
        errors.append("KG-001 v112 status-engine drift")
    if c.get("quality",{}).get("kg001_overall_status")!="BLOCKED_ISSUES_6_9_11_RETEST":
        errors.append("KG-001 v112 overall status drift")
    if c.get("quality",{}).get("kg001_final_tag_allowed") is not False:
        errors.append("KG-001 tag unexpectedly allowed")
    if c.get("quality",{}).get("kg001_collision_issue_6")!="SOURCE_FIX_READY_RUNTIME_RETEST_REQUIRED":
        errors.append("KG-001 Issue #6 collision status drift")
    if c.get("quality",{}).get("kg001_release_blocked_by_issue_6") is not True:
        errors.append("KG-001 Issue #6 release blocker drift")
    if c.get("quality",{}).get("kg001_audio_issue_9")!="SOURCE_FIX_READY_RUNTIME_RETEST_REQUIRED":
        errors.append("KG-001 Issue #9 audio status drift")
    if c.get("quality",{}).get("kg001_release_blocked_by_issue_9") is not True:
        errors.append("KG-001 Issue #9 release blocker drift")
    if c.get("quality",{}).get("kg001_physical_audio_source_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 physical audio source-contract drift")
    if c.get("quality",{}).get("kg001_texture_issue_11")!="SOURCE_FIX_READY_RUNTIME_RETEST_REQUIRED":
        errors.append("KG-001 Issue #11 texture status drift")
    if c.get("quality",{}).get("kg001_release_blocked_by_issue_11") is not True:
        errors.append("KG-001 Issue #11 release blocker drift")
    if c.get("quality",{}).get("kg001_legacy_colorkey_source_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 legacy color-key source-contract drift")
    if c.get("quality",{}).get("kg001_legacy_colorkey_expected_hash_textures")!=10:
        errors.append("KG-001 legacy color-key texture-class drift")
    if "COMPLETE_ORIGINAL_RENDERER_TRANSPARENCY_SEMANTICS" not in c.get("hard_holds",[]):
        errors.append("legacy transparency HOLD boundary missing")
    if c.get("quality",{}).get("kg001_candidate_build_runtime")!="V31_NOT_EXECUTED":
        errors.append("KG-001 Candidate 2 runtime boundary drift")
    if c.get("quality",{}).get("documentation_consistency")!="PASS_V31":
        errors.append("documentation consistency drift")
    if c.get("quality",{}).get("documentation_runtime_claim_boundary")!="NO_RUNTIME_PROMOTION":
        errors.append("documentation/runtime boundary drift")
    if c.get("quality",{}).get("kg001_bug_reporting")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 bug-reporting source-contract drift")
    if c.get("quality",{}).get("kg001_candidate_debug_keys",{}).get("F11")!="bug_report_capture":
        errors.append("KG-001 F11 bug-report key drift")
    if c.get("quality",{}).get("kg001_bug_report_source_safe") is not True:
        errors.append("KG-001 bug-report source-safety drift")
    q=c.get("quality",{})
    if q.get("kg001_independent_audit_source_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 independent-audit source-contract drift")
    if q.get("kg001_pinned_toolchain_contract")!="PINNED_V117":
        errors.append("KG-001 pinned toolchain contract drift")
    if q.get("kg001_build_manifest_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 build-manifest contract drift")
    if q.get("kg001_candidate_run_provenance")!="RUN_SCOPED_V1":
        errors.append("KG-001 run-scoped provenance drift")
    if q.get("kg001_floor_regression_rooms")!=["R1","R7","R8"]:
        errors.append("KG-001 three-room floor regression drift")
    if q.get("kg001_audio_pcm_non_silence_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 PCM non-silence contract drift")
    if q.get("kg001_audio_master_capture_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 Master-bus capture contract drift")
    if q.get("kg001_texture_colorkey_detection")!="USED_INDEXED_PALETTE_ENTRY":
        errors.append("KG-001 indexed color-key detection drift")
    if q.get("kg001_texture_colorkey_ambiguity_policy")!="FAIL_CLOSED":
        errors.append("KG-001 indexed color-key ambiguity policy drift")
    if q.get("kg001_texture_mask_edge_bleed_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 MASK edge-bleed contract drift")
    if q.get("kg001_visual_capture_source_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 visual-capture source-contract drift")
    if q.get("kg001_visual_capture_runtime")!="NOT_EXECUTED":
        errors.append("KG-001 visual-capture runtime boundary drift")
    if q.get("kg001_windows_export_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 Windows export contract drift")
    if q.get("kg001_source_safe_ci_workflow")!=".github/workflows/kg001-source-safe.yml":
        errors.append("KG-001 source-safe CI workflow drift")
    if q.get("kg001_candidate2_asset_set_contract")!="SOURCE_CONTRACT_PASS_V118":
        errors.append("KG-001 v118 asset-set contract drift")
    if q.get("kg001_candidate2_asset_set_runtime")!="NOT_EXECUTED":
        errors.append("KG-001 v118 asset-set runtime boundary drift")
    if q.get("kg001_candidate2_expected_room_assets")!=3:
        errors.append("KG-001 v118 room-asset count drift")
    if q.get("kg001_candidate2_expected_runtime_audio_assets")!=8:
        errors.append("KG-001 v118 runtime-audio count drift")
    if q.get("kg001_candidate2_expected_classic_textures")!=86:
        errors.append("KG-001 v118 Classic texture count drift")
    if q.get("kg001_build_manifest_version")!=2:
        errors.append("KG-001 build-manifest schema drift")
    if q.get("kg001_test_build_contract")!="SOURCE_CONTRACT_PASS_V118":
        errors.append("KG-001 v118 test-build contract status drift")
    if q.get("kg001_test_build_runtime")!="NOT_EXECUTED":
        errors.append("KG-001 v118 test-build runtime boundary drift")
    if q.get("kg001_test_build_ready_status")!="READY_FOR_G10_MANUAL_TEST":
        errors.append("KG-001 v118 test-build ready status drift")
    if q.get("kg001_release_blockers_close_automatically") is not False:
        errors.append("KG-001 v118 release-blocker automation drift")
    if q.get("kg001_test_build_known_good_tag_allowed") is not False:
        errors.append("KG-001 v118 test-build known-good boundary drift")
    if q.get("kg001_candidate2_asset_set_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 complete asset-set contract drift")
    if q.get("kg001_candidate2_asset_set_runtime")!="NOT_EXECUTED":
        errors.append("KG-001 asset-set runtime boundary drift")
    if q.get("kg001_build_manifest_schema")!="V2_RUNTIME_SOURCE_BOUND":
        errors.append("KG-001 build-manifest v2 identity drift")
    if q.get("kg001_exported_startup_smoke_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 exported startup-smoke contract drift")
    if q.get("kg001_test_build_contract")!="SOURCE_CONTRACT_PASS_V118":
        errors.append("KG-001 test-build contract drift")
    if q.get("kg001_test_build_status")!="NOT_EXECUTED":
        errors.append("KG-001 test-build runtime boundary drift")
    if q.get("kg001_test_build_receipt_status")!="NOT_EXECUTED":
        errors.append("KG-001 test-build receipt boundary drift")
    if q.get("kg001_evidence_promotion_order")!="AFTER_EXPORT_STARTUP_SMOKE_ON_WINDOWS_WRAPPER":
        errors.append("KG-001 evidence-promotion ordering drift")
    audit=c.get("kg001_v117_audit",{})
    if audit.get("status")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 v117 audit status drift")
    if audit.get("draft_pr")!=12:
        errors.append("KG-001 v117 audit PR drift")
    if audit.get("pinned_godot")!="4.7.2.stable.official.ed1daf0bf":
        errors.append("KG-001 v117 Godot pin drift")
    if audit.get("visual_capture_runtime")!="NOT_EXECUTED":
        errors.append("KG-001 v117 visual runtime boundary drift")
    loc=c.get("localization",{})
    if loc.get("status")!="ARCHITECTURE_APPROVED_IMPLEMENTATION_DEFERRED":
        errors.append("localization architecture status drift")
    if loc.get("key_strategy")!="STABLE_SEMANTIC_IDS":
        errors.append("localization key strategy drift")
    if loc.get("authoring_format")!="GETTEXT_POT_PO":
        errors.append("localization authoring-format drift")
    if loc.get("distribution_format")!="EXTERNAL_VERSIONED_PCK":
        errors.append("localization distribution-format drift")
    if loc.get("runtime_fallback")!="EN":
        errors.append("localization fallback drift")
    if loc.get("resource_pack_replace_core") is not False:
        errors.append("localization core-replacement safety drift")
except Exception as e:
    errors.append(f"context json: {e}")

try:
    d=json.loads((ROOT/"data/world_runtime_serialization_v106.json").read_text(encoding="utf-8"))
    world=d.get("world",{})
    if (
        d.get("schema")!="openazrael.world_runtime_serialization_summary"
        or d.get("version")!=106
        or d.get("status")!="PASS"
        or world.get("file_size_bytes")!=96425
        or world.get("reconstructed_consumed_bytes")!=96425
        or world.get("exact_eof") is not True
        or world.get("top_level_section_counts")!=[1303,12,37,3,101,8,15]
    ):
        errors.append("v106 source-safe serialization summary drift")
except Exception as e:
    errors.append(f"v106 evidence json: {e}")

try:
    k=json.loads((ROOT/"data/kg001_acceptance_contract.json").read_text(encoding="utf-8"))
    if k.get("target_tag")!="demo-known-good-001":
        errors.append("KG-001 target tag drift")
    gates=k.get("gates",[])
    if [g.get("id") for g in gates] != [f"G{i:02d}" for i in range(11)]:
        errors.append("KG-001 gate set drift")
    if not all(g.get("required") is True for g in gates):
        errors.append("KG-001 required-gate drift")
except Exception as e:
    errors.append(f"KG-001 contract: {e}")

try:
    t=json.loads((ROOT/"data/tests/kg001_texture_colorkey_contract_v116.json").read_text(encoding="utf-8"))
    expected=t.get("expected_demo_hash_textures",[])
    if t.get("status")!="SOURCE_CONTRACT_PASS" or len(expected)!=10:
        errors.append("KG-001 texture color-key contract drift")
    policy=t.get("policy",{})
    if policy.get("runtime_material")!="MASK" or policy.get("alpha_cutoff")!=0.5:
        errors.append("KG-001 texture material policy drift")
    if t.get("evidence_boundary","").find("HOLD")<0:
        errors.append("KG-001 texture evidence boundary drift")
    if policy.get("indexed_detection")!="USED_INDEXED_PALETTE_ENTRY":
        errors.append("KG-001 texture indexed-detection policy drift")
    if policy.get("ambiguity_policy")!="FAIL_CLOSED_IF_MULTIPLE_USED_KEY_INDICES":
        errors.append("KG-001 texture ambiguity policy drift")
except Exception as e:
    errors.append(f"KG-001 texture contract: {e}")

try:
    tc=json.loads((ROOT/"data/tests/kg001_toolchain_contract_v117.json").read_text(encoding="utf-8"))
    if tc.get("status")!="PINNED" or tc.get("python")!="3.11.11":
        errors.append("KG-001 toolchain contract drift")
    if tc.get("godot",{}).get("version")!="4.7.2.stable.official.ed1daf0bf":
        errors.append("KG-001 Godot toolchain pin drift")
except Exception as e:
    errors.append(f"KG-001 toolchain contract: {e}")

try:
    tb=json.loads((ROOT/"data/tests/kg001_test_build_contract_v118.json").read_text(encoding="utf-8"))
    if tb.get("status")!="SOURCE_CONTRACT_PASS" or tb.get("version")!=118:
        errors.append("KG-001 v118 test-build contract drift")
    if tb.get("ready_status")!="READY_FOR_G10_MANUAL_TEST":
        errors.append("KG-001 v118 test-build ready-status drift")
    if tb.get("release_blockers_close_automatically") is not False:
        errors.append("KG-001 v118 release-blocker boundary drift")
    if tb.get("demo_known_good_tag_allowed") is not False:
        errors.append("KG-001 v118 known-good boundary drift")
except Exception as e:
    errors.append(f"KG-001 v118 test-build contract: {e}")

try:
    vc=json.loads((ROOT/"data/tests/kg001_visual_capture_contract_v117.json").read_text(encoding="utf-8"))
    if vc.get("status")!="SOURCE_CONTRACT_PASS" or vc.get("runtime_status")!="NOT_EXECUTED":
        errors.append("KG-001 visual-capture contract drift")
    if [(x.get("room"),x.get("view")) for x in vc.get("captures",[])] != [
        ("R1","spaview"),("R7","view"),("R8","Object14")
    ]:
        errors.append("KG-001 canonical visual capture set drift")
except Exception as e:
    errors.append(f"KG-001 visual-capture contract: {e}")

try:
    tb=json.loads((ROOT/"data/tests/kg001_test_build_contract_v118.json").read_text(encoding="utf-8"))
    if (
        tb.get("status")!="SOURCE_CONTRACT_PASS"
        or tb.get("version")!=118
        or tb.get("ready_status")!="READY_FOR_G10_MANUAL_TEST"
        or tb.get("demo_known_good_tag_allowed") is not False
        or tb.get("release_blockers_close_automatically") is not False
    ):
        errors.append("KG-001 test-build v118 contract drift")
except Exception as e:
    errors.append(f"KG-001 test-build contract: {e}")

workflow=(ROOT/".github/workflows/kg001-source-safe.yml").read_text(encoding="utf-8")
for marker in [
    "SCRIPT ERROR:",
    "ERROR: Failed to load script",
    "ERROR: Failed to create an autoload",
    "openazrael-godot-parse.log",
]:
    if marker not in workflow:
        errors.append(f"Godot parse-log CI guard missing: {marker}")

gitignore=(ROOT/".gitignore").read_text(encoding="utf-8")
for marker in [
    "data/audio/original_audio/",
    "data/*.DAT",
    "assets/audio/",
    "assets/rooms/",
    "assets/textures/classic/",
    "data/*.textured.v44.manifest.json",
    "data/audio/*.legacy.json",
    "data/graphics_pipeline_validation_v44.json",
    "*.gd.uid",
    "data/generated/",
]:
    if marker not in gitignore:
        errors.append(f"gitignore safety missing: {marker}")

if errors:
    print("OpenAzrael context validation: FAIL")
    for x in errors:
        print(" -",x)
    sys.exit(1)

print("OpenAzrael context validation: PASS")
print(" checkpoint:",EXPECTED_CHECKPOINT)
print(" KG-001 contract: ACCEPTED")
