#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_CHECKPOINT="v116-context-v26"
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
    "docs/HISTORY_PRE_V116.md",
    "docs/KG001_CANDIDATE_DIAGNOSTICS_V116.md",
    "scripts/candidate_diagnostics_v116.gd",
    "scripts/kg001_trigger_debug_v116.gd",
    "tools/validate_candidate_diagnostics_v116.py",
    "data/tests/kg001_candidate_diagnostics_contract_v116.json",
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
    if c.get("quality",{}).get("kg001_headless_runtime") not in ("NOT_EXECUTED", "PASS"):
        errors.append("KG-001 v109 runtime status drift")
    if c.get("quality",{}).get("kg001_room_trigger_source_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 v110 room/trigger source-contract drift")
    if c.get("quality",{}).get("kg001_room_trigger_runtime") not in ("NOT_EXECUTED", "BLOCKED_MISSING_ASSETS", "PASS"):
        errors.append("KG-001 v110 runtime status drift")
    if c.get("quality",{}).get("kg001_full_demo_source_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 v111 full-demo source-contract drift")
    if c.get("quality",{}).get("kg001_full_demo_runtime") not in ("NOT_EXECUTED", "BLOCKED_MISSING_ASSETS", "PASS"):
        errors.append("KG-001 v111 runtime status drift")
    if c.get("quality",{}).get("kg001_candidate_runner")!="SOURCE_CONTRACT_READY":
        errors.append("KG-001 v112 candidate runner drift")
    if c.get("quality",{}).get("kg001_status_engine")!="EVIDENCE_DRIVEN_V112":
        errors.append("KG-001 v112 status-engine drift")
    if c.get("quality",{}).get("kg001_overall_status")!="AWAITING_RUNTIME_OR_MANUAL":
        errors.append("KG-001 v112 overall status drift")
    if c.get("quality",{}).get("kg001_final_tag_allowed") is not False:
        errors.append("KG-001 tag unexpectedly allowed")
    runtime_records={}
    oracle=json.loads((ROOT/"data/tests/kg001_state_space_v108.json").read_text(encoding="utf-8"))
    for version,field,stem in (
        (109,"kg001_headless_runtime","headless"),
        (110,"kg001_room_trigger_runtime","room_trigger"),
        (111,"kg001_full_demo_runtime","full_demo"),
    ):
        if c.get("quality",{}).get(field) != "PASS":
            continue
        runtime=json.loads((ROOT/f"data/tests/kg001_{stem}_runtime_v{version}.json").read_text(encoding="utf-8"))
        runtime_records[f"v{version}"]=runtime
        if (runtime.get("status") != "PASS" or runtime.get("_process_returncode") != 0
                or runtime.get("failed") != []
                or runtime.get("schema") != f"openazrael.kg001.{stem}"
                or runtime.get("version") != version):
            errors.append(f"v{version} PASS requires successful recorded runtime evidence")
        if version in (109,111):
            if (runtime.get("persistent_hash") != oracle.get("shortest_success_persistent_state_sha256")
                    or runtime.get("logical_audio_events") != oracle.get("shortest_success_audio_events")):
                errors.append(f"v{version} runtime hash/audio must match the v108 oracle")
    evidence_commit=c.get("quality",{}).get("kg001_runtime_evidence_commit")
    if evidence_commit:
        fresh=json.loads((ROOT/"data/tests/kg001_fresh_checkout.json").read_text(encoding="utf-8"))
        rooms={f"assets/rooms/{room}.glb" for room in ("R1","R7","R8")}
        def room_evidence_pass(mapping):
            return isinstance(mapping,dict) and {
                key.replace("\\","/") for key,value in mapping.items() if value is True
            } == rooms
        if (fresh.get("status") != "PASS" or fresh.get("commit_sha") != evidence_commit
                or fresh.get("schema") != "openazrael.kg001.fresh_checkout" or fresh.get("version") != 112
                or fresh.get("clean_before") is not True or fresh.get("clean_after") is not True
                or fresh.get("godot_import_status") != "PASS" or fresh.get("source_validators_pass") is not True
                or fresh.get("forbidden_tracked_files") != []
                or fresh.get("runtime_status") != {"v109":"PASS","v110":"PASS","v111":"PASS"}
                or set(runtime_records) != {"v109","v110","v111"}
                or not room_evidence_pass(fresh.get("room_assets_present"))
                or not room_evidence_pass(fresh.get("room_assets_git_ignored"))):
            errors.append("recorded runtime baseline requires complete clean-checkout PASS evidence at its stated commit")
        source=json.loads((ROOT/"data/tests/kg001_source_validation_v112.json").read_text(encoding="utf-8"))
        if source.get("status") != "PASS":
            errors.append("recorded runtime baseline requires source-validation PASS evidence")
    manual_path=ROOT/"data/tests/kg001_manual_sanity.json"
    if c.get("quality",{}).get("kg001_manual_sanity") == "CHECKLIST_READY_PENDING_USER":
        if manual_path.is_file() and json.loads(manual_path.read_text(encoding="utf-8")).get("status") == "PASS":
            errors.append("manual PASS evidence conflicts with pending context; review G10 explicitly")
    if c.get("quality",{}).get("documentation_consistency")!="PASS_V26":
        errors.append("documentation consistency drift")
    if c.get("quality",{}).get("documentation_runtime_claim_boundary")!="NO_RUNTIME_PROMOTION":
        errors.append("documentation/runtime boundary drift")
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
    # The source mirror retains the canonical summary, not the excluded full
    # forensic payload. Validate the tracked summary and its machine metadata;
    # this is context integrity, not a rerun of the original-binary analysis.
    summary=(ROOT/"WORLD_RUNTIME_SERIALIZATION_V106.md").read_text(encoding="utf-8")
    forensic=c.get("current_forensics", {})
    if "96,425 / 96,425" not in summary or "[1303, 12, 37, 3, 101, 8, 15]" not in summary:
        errors.append("v106 tracked EOF/section-count summary missing")
    if forensic.get("world_exact_eof") is not True or forensic.get("world_section_counts") != [1303,12,37,3,101,8,15]:
        errors.append("v106 machine-readable EOF/section-count evidence drift")
    if "## v105" not in (ROOT/"docs/HISTORY_PRE_V116.md").read_text(encoding="utf-8"):
        errors.append("v105 tracked summary missing")
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
