#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_CHECKPOINT="v113-context-v21"
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
    if c.get("quality",{}).get("kg001_overall_status")!="AWAITING_RUNTIME_OR_MANUAL":
        errors.append("KG-001 v112 overall status drift")
    if c.get("quality",{}).get("kg001_final_tag_allowed") is not False:
        errors.append("KG-001 tag unexpectedly allowed")
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
