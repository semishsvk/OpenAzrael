#!/usr/bin/env python3
"""Extract narrowly verified complementary R7 WORLD condition branches."""
import hashlib,json,struct,sys
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from analyze_world_puzzle_sound_bridge_v107 import parse_section6_blobs
CORPUS=Path(os.environ.get("OPENAZRAEL_CORPUS","F:/OpenRemaster/sources/materialized/openazrael_demo_atdemo_v1/bf0c87f731bb4e87/layer2/ATDEMO"))
SOURCE=CORPUS/"WORLD.DAT"
EXPECTED_SHA="f055948e302fa2f6ba364f7ebd3b4bc45f20ef4445af4946c63e4e313a084ae9"
TARGETS={8:44,16:46}
OUTPUT=ROOT/"data/runtime_generated/well_condition_gates_v362.json"
def derive(data):
    assert hashlib.sha256(data).hexdigest()==EXPECTED_SHA
    blobs=parse_section6_blobs(data)["blobs"]
    out=[]
    for r in blobs:
        if r["kind"]!="blob37" or r["top_index"]!=4 or r["node_index"] not in TARGETS:
            continue
        raw=r["raw"]
        opcode=raw[0];idx=struct.unpack_from("<H",raw,1)[0]
        assert opcode in (4,10) and idx==TARGETS[r["node_index"]]
        assert r["object_field"]==17 and r["object_index"] in (0,1)
        predicate="nonzero" if opcode==4 else "zero"
        out.append({"node":r["node_index"],"slot":r["object_index"],"condition_opcode":opcode,
                    "condition_index":idx,"predicate":predicate,"source_offset":r["offset"]})
    assert len(out)==4
    for node in TARGETS:
        records=[v for v in out if v["node"]==node]
        assert [(v["slot"],v["condition_opcode"]) for v in records]==[(0,4),(1,10)]
    return out
def main():
    data=SOURCE.read_bytes()
    rows=derive(data)
    result={"schema":"openazrael.c8.well_condition_gates.v362","source_sha256":EXPECTED_SHA,
            "status":"SOURCE_CONDITION_BRANCHES_VERIFIED_GAMEPLAY_MAPPING_HOLD","records":rows,
            "unverified":["state_index_to_named_flag","event_activation_order","runtime_condition_state_capture","visual_audio_fidelity"]}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"status":"STRUCTURAL_PASS_FIDELITY_HOLD","records":len(rows),
           "condition_indices":list(TARGETS.values()),"out":str(OUTPUT)}))
if __name__=="__main__":main()