#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_CHECKPOINT="v108-context-v16"
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
    "data/evidence/evidence_registry.json",
    "data/backup/source_fingerprints.json",
    "WORLD_RUNTIME_SERIALIZATION_V106.md",
    "WORLD_PUZZLE_SOUND_BRIDGE_V107.md",
    "PUZZLES_ALTERNATIVE_OPEN_PATHS_V105.md",
    "data/world_runtime_serialization_v106.json",
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
