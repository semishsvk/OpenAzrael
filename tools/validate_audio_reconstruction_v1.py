#!/usr/bin/env python3
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
schema=json.loads((ROOT/"data/audio/sound_database_schema_v1.json").read_text())
graph=json.loads((ROOT/"data/audio/r1_r7_r8_acoustic_graph_v1.json").read_text())
contract=json.loads((ROOT/"data/tests/audio_reconstruction_r1_r7_r8_contract_v1.json").read_text())

errors=[]
levels=schema["confidence_levels"]
if levels != ["VERIFIED","HIGH","MEDIUM","LOW","HOLD"]:
    errors.append("confidence vocabulary changed")
rooms={r["id"] for r in graph["rooms"]}
if rooms != {"R1","R7","R8"}:
    errors.append(f"room set mismatch: {sorted(rooms)}")
portal_ids=set()
for p in graph["portals"]:
    portal_ids.add(p["id"])
    if len(p["rooms"]) != 2 or not set(p["rooms"]) <= rooms:
        errors.append(f"bad portal {p['id']}")
for r in graph["rooms"]:
    dangling=set(r["portals"])-portal_ids
    if dangling:
        errors.append(f"dangling portals in {r['id']}: {sorted(dangling)}")
if graph["runtime_modes"]["classic"]["enhancements"] is not False:
    errors.append("classic must remain non-enhanced")
if len(contract["gates"]) != 12:
    errors.append("expected A01-A12")
if [g["id"] for g in contract["gates"]] != [f"A{i:02d}" for i in range(1,13)]:
    errors.append("gate IDs must be contiguous A01-A12")
if not contract["runtime_required_before_promotion"]:
    errors.append("runtime promotion guard missing")

if errors:
    print("AUDIO RECONSTRUCTION PRE-BUILD: FAIL")
    for e in errors: print(" -",e)
    raise SystemExit(1)
print("AUDIO RECONSTRUCTION PRE-BUILD: PASS")
print(" rooms=3 portals=%d gates=12 classic_default=true enhanced_feature_flagged=true" % len(portal_ids))
