#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse,hashlib,json,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from kg001_state_space_v108 import Model, explore

def pairs_to_dict(pairs):
    return dict(pairs)

def expected_visibility(state):
    inv=pairs_to_dict(state.inventory); flags=pairs_to_dict(state.flags); puzzle=pairs_to_dict(state.puzzle_nodes)
    out={}
    if state.room=="R1":
        out={
            "TONG6": not (bool(inv.get("rusty_tongs")) or bool(flags.get("R7key"))),
            "r1p1": not bool(inv.get("parchment_r1")),
            "r3t1": not (bool(inv.get("tapestry_piece_1")) or bool(flags.get("R8Tap1"))),
            "save": True,
        }
    elif state.room=="R7":
        out={
            "nibdyky01": not (bool(inv.get("well_key")) or bool(flags.get("R7key"))),
            "well_floor": True,
            "nibody": True,
        }
    elif state.room=="R8":
        out={
            "zxwater": not bool(flags.get("R8BathDrain")),
            "lens": not (bool(inv.get("r8_lens")) or bool(puzzle.get("R8LensPlace"))),
            "lenstop": bool(puzzle.get("R8LensPlace")),
            "lenstop01": False,
            "r8s1": bool(puzzle.get("DoorR8")) and not bool(flags.get("demo_complete")),
            "bible": True,
            "door": True,
        }
    return out

def runtime_canonical_payload(state):
    """Mirror Godot JSON numeric semantics for cross-language state hashes.

    JSON.parse_string() materializes numeric values as floats in GDScript, so a
    Python integer value such as R7SwitchStep=3 is serialized by the runtime as
    3.0. Normalize only the value payload here; boolean/state fields remain
    untouched. The original model hash is retained separately for diagnostics.
    """
    payload=state.persistent_payload()
    values=[]
    for key,value in payload[4]:
        if isinstance(value,(int,float)) and not isinstance(value,bool):
            value=float(value)
        values.append([key,value])
    return [1,payload[1],payload[2],payload[3],values]

def runtime_canonical_hash(state):
    raw=json.dumps(
        runtime_canonical_payload(state),
        separators=(",",":"),
        ensure_ascii=False
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,default=ROOT/"data/runtime_generated/kg001_state_matrix_v127.json")
    args=ap.parse_args()
    graph=json.loads((ROOT/"data/gameplay_event_graph_v87.json").read_text(encoding="utf-8"))
    triggers=json.loads((ROOT/"data/xaf_trigger_evidence.json").read_text(encoding="utf-8"))
    initial,states,*rest=explore(Model(graph,triggers))
    ordered=sorted(states,key=lambda s:(s.room,s.persistent_hash(),int(s.sequence_running),repr(s)))
    records=[]
    for index,s in enumerate(ordered):
        records.append({
            "index":index,
            "room":s.room,
            "persistent_payload":s.persistent_payload(),
            "persistent_sha256":runtime_canonical_hash(s),
            "model_persistent_sha256":s.persistent_hash(),
            "sequence_running":bool(s.sequence_running),
            "expected_visibility":expected_visibility(s),
        })
    payload={
        "schema":"openazrael.kg001.reachable_visibility_matrix",
        "version":127,
        "status":"PASS",
        "reachable_states":len(records),
        "state_model_version":108,
        "records":records,
        "boundary":"Production save/restore is used to replay only source-model reachable persistent states. Transient motion timing remains covered by dedicated integration tests.",
    }
    if len(records)!=104:
        payload["status"]="FAIL"; payload["error"]=f"expected 104 reachable states, got {len(records)}"
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"states":len(records),"out":str(args.out)},indent=2))
    return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
