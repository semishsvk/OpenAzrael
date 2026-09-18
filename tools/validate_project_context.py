#!/usr/bin/env python3
from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(p):
 p=ROOT/p
 if not p.exists(): errors.append(f"missing: {p.relative_to(ROOT)}")
for p in ["OPENAZRAEL_CONTEXT.md","docs/PROJECT_STATE.md","docs/LAST_SESSION.md","docs/DECISIONS.md","docs/BACKUP_VERSIONING_POLICY.md","docs/GIT_BASELINE.md","data/project_context.json","data/evidence/evidence_registry.json","data/backup/source_fingerprints.json","WORLD_RUNTIME_SERIALIZATION_V106.md","PUZZLES_ALTERNATIVE_OPEN_PATHS_V105.md","data/world_runtime_serialization_v106.json"]: req(p)
try:
 c=json.loads((ROOT/"data/project_context.json").read_text())
 if c.get("checkpoint")!="v106-context-v12": errors.append("checkpoint drift")
 if c.get("current_forensics",{}).get("world_runtime_loader")!="VERIFIED": errors.append("WORLD loader status drift")
except Exception as e: errors.append(f"context json: {e}")
try:
 d=json.loads((ROOT/"data/world_runtime_serialization_v106.json").read_text())
 txt=json.dumps(d)
 if "96425" not in txt: errors.append("v106 EOF-size evidence missing")
except Exception as e: errors.append(f"v106 evidence json: {e}")
for marker in ["data/audio/original_audio/","data/*.DAT","assets/audio/","assets/rooms/","assets/textures/classic/"]:
 if marker not in (ROOT/".gitignore").read_text(): errors.append(f"gitignore safety missing: {marker}")
if errors:
 print("OpenAzrael context validation: FAIL")
 [print(" -",x) for x in errors]
 sys.exit(1)
print("OpenAzrael context validation: PASS")
print(" checkpoint: v106-context-v12")
