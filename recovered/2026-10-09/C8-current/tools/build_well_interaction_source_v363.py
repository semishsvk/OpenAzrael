#!/usr/bin/env python3
"""Complete source-ordered R7 Well Room action groups: never infer opaque state opcode semantics."""
import collections,hashlib,json,math,struct,sys
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from analyze_world_puzzle_sound_bridge_v107 import parse_section6_blobs
from analyze_world_sound_record_fields_v113 import parse_section0
CORPUS=Path(os.environ.get("OPENAZRAEL_CORPUS","F:/OpenRemaster/sources/materialized/openazrael_demo_atdemo_v1/bf0c87f731bb4e87/layer2/ATDEMO"))
SOURCE=CORPUS/"WORLD.DAT"
EXPECTED="f055948e302fa2f6ba364f7ebd3b4bc45f20ef4445af4946c63e4e313a084ae9"
NODES=(2,3,5,6,8,10,11,13,14,16)
OUTPUT=ROOT/"data/runtime_generated/well_interaction_source_v363.json"
def derive(raw):
    if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise ValueError("noncanonical WORLD.DAT")
    blobs=parse_section6_blobs(raw)["blobs"]
    names,_=parse_section0(raw)
    groups=collections.OrderedDict()
    for blob in blobs:
        if blob["top_index"]!=4 or blob["node_index"] not in NODES:continue
        key=(blob["node_index"],blob["object_index"])
        if key not in groups: groups[key]={"node":key[0],"slot":key[1],"condition":None,"actions":[]}
        group=groups[key];r=blob["raw"];opcode=r[0]
        if blob["kind"]=="blob37":
            if group["condition"] is not None:raise ValueError("duplicate condition")
            pred={4:"nonzero",10:"zero"}.get(opcode,"UNKNOWN")
            group["condition"]={"opcode":opcode,"state_index_candidate":struct.unpack_from("<H",r,1)[0],
                 "predicate":pred,"source_offset":blob["offset"]}
        elif blob["kind"]=="blob27":
            action={"opcode":opcode,"source_offset":blob["offset"],"ordinal":len(group["actions"])}
            if opcode in (0x17,0x18):
                idx=struct.unpack_from("<H",r,1)[0]
                action.update(kind="rotation" if opcode==0x17 else "translation",
                    target_id=idx,target_name=names[idx]["name"],
                    operand=struct.unpack_from("<h",r,5)[0] if opcode==0x17 else struct.unpack_from("<f",r,5)[0],
                    source_axis_code=r[9],steps=struct.unpack_from("<H",r,10)[0])
                if action["source_axis_code"] not in (0,1,2) or action["steps"] not in (5,10,15):
                    raise ValueError("unexpected transform action fields")
            elif opcode==0x28:
                token=r[1:].split(b"\0",1)[0].decode("ascii")
                if token.lower() not in ("983tunk","977turn","982push","981pull"):
                    raise ValueError("unexpected R7 mechanical sound")
                action.update(kind="sound",source_stem=token,
                    sound_file=token.upper()+".WAV",
                    location_object_index=struct.unpack_from("<H",r,13)[0],
                    room_context=struct.unpack_from("<H",r,15)[0])
            elif opcode==0x04:
                idx=struct.unpack_from("<H",r,1)[0]
                val=struct.unpack_from("<H",r,3)[0]
                action.update(kind="state_write",source_state_index=idx,
                    source_state_value=val,source_array="WORLD_SECTION4_STATE_U16")
            elif opcode==0x01:
                # Source handler 0x1B222 indexes section-3 runtime objects via
                # pointer global 0x438EC, checks +0x0C, then invokes 0x1A90C
                # and clears +0x0C. The referred callback's gameplay effect
                # remains unknown and is deliberately not executed.
                action.update(kind="opaque_state_action",
                    source_section3_index=struct.unpack_from("<H",r,1)[0],
                    source_runtime_guard_offset=12,
                    source_handler="LE_object1:0x1B222",
                    meaning="SECTION3_CALLBACK_EFFECT_HOLD")
            else:
                raise ValueError("unrecognized source R7 action opcode: "+hex(opcode))
            group["actions"].append(action)
    result=list(groups.values())
    if len(result)!=12 or set(v["node"] for v in result)!=set(NODES):
        raise ValueError("unexpected condition group population")
    if any(v["condition"] is None or len(v["actions"]) not in (3,5,7) for v in result):
        raise ValueError("unexpected group shape")
    hist=collections.Counter(a["kind"] for g in result for a in g["actions"])
    if hist!= {"rotation":16,"translation":8,"sound":12,"state_write":8,"opaque_state_action":4}:
        raise ValueError("unexpected action population "+str(hist))
    return result
def main():
    data=SOURCE.read_bytes()
    groups=derive(data)
    manifest={"schema":"openazrael.c8.well_interaction_source.v363","status":"SOURCE_ACTION_ORDER_AND_STATE_WRITE_PASS_GAMEPLAY_FIDELITY_HOLD",
        "world_sha256":EXPECTED,"groups":groups,
        "hold":["opcode_01_runtime_semantics","source_state_index_to_gameplay_flag","Godot_coordinate_conversion",
           "original_callback_cadence","original_audio_physical_timing","original_runtime_replay_diff"]}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"status":"STRUCTURAL_PASS_FIDELITY_HOLD","groups":len(groups),
          "actions":sum(len(g["actions"]) for g in groups),"out":str(OUTPUT)}))
if __name__=="__main__":main()