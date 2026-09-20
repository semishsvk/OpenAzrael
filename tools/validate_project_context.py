#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_CHECKPOINT="v116-context-v30"
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
    if c.get("quality",{}).get("kg001_candidate_build_runtime")!="V30_NOT_EXECUTED":
        errors.append("KG-001 Candidate 2 runtime boundary drift")
    if c.get("quality",{}).get("documentation_consistency")!="PASS_V30":
        errors.append("documentation consistency drift")
    if c.get("quality",{}).get("documentation_runtime_claim_boundary")!="NO_RUNTIME_PROMOTION":
        errors.append("documentation/runtime boundary drift")
    if c.get("quality",{}).get("kg001_bug_reporting")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 bug-reporting source-contract drift")
    if c.get("quality",{}).get("kg001_candidate_debug_keys",{}).get("F11")!="bug_report_capture":
        errors.append("KG-001 F11 bug-report key drift")
    if c.get("quality",{}).get("kg001_bug_report_source_safe") is not True:
        errors.append("KG-001 bug-report source-safety drift")
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
    if "96425" not in json.dumps(d):
        errors.append("v106 EOF-size evidence missing")
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

gitignore=(ROOT/".gitignore").read_text(encoding="utf-8")
for marker in [
    "data/audio/original_audio/",
    "data/*.DAT",
    "assets/audio/",
    "assets/rooms/",
    "assets/textures/classic/",
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
