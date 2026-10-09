#!/usr/bin/env python3
"""Source-pinned Well Room action census. Structural evidence only."""
from pathlib import Path
import sys,struct,hashlib,json,collections
sys.path.insert(0,str(Path(__file__).resolve().parent))
from analyze_world_puzzle_sound_bridge_v107 import parse_section6_blobs
EXPECTED="f055948e302fa2f6ba364f7ebd3b4bc45f20ef4445af4946c63e4e313a084ae9"
def inspect(path):
 data=Path(path).read_bytes()
 if hashlib.sha256(data).hexdigest()!=EXPECTED:raise ValueError("WORLD.DAT SHA mismatch")
 rows=[]
 for x in parse_section6_blobs(data)["blobs"]:
  if x["kind"]!="blob27" or x["raw"][0] not in (23,24):continue
  b=x["raw"];op=b[0]
  row={"offset":x["offset"],"group":x["top_index"],"node":x["node_index"],"slot":x["object_index"],"opcode":op,"object_id":struct.unpack_from("<H",b,1)[0],"comparison":struct.unpack_from("<H",b,3)[0],"axis_code":b[9],"duration_candidate":struct.unpack_from("<H",b,10)[0],"tail_hex":b[12:].hex()}
  if op==23:
   row["operand_s16"]=struct.unpack_from("<h",b,5)[0]
   row["reserved_s16"]=struct.unpack_from("<h",b,7)[0]
  else:row["operand_f32"]=struct.unpack_from("<f",b,5)[0]
  rows.append(row)
 focus=[r for r in rows if r["group"]==4]
 assert len(rows)==32 and len(focus)==24
 assert collections.Counter(r["opcode"] for r in focus)=={23:16,24:8}
 assert all(r["comparison"]==1 for r in focus)
 return {"schema":"openazrael.well_world_actions.v317","source_sha256":EXPECTED,"status":"STRUCTURAL_PASS_FIDELITY_HOLD","records":focus,"global_counts":{"0x17":sum(r["opcode"]==23 for r in rows),"0x18":sum(r["opcode"]==24 for r in rows)},"unverified":["object_name_binding","operand_axis","transform_semantics","timing","audio","persistence","original_runtime_replay"]}
if __name__=="__main__":
 root=Path("F:/OpenRemaster/sources/materialized/openazrael_demo_atdemo_v1/bf0c87f731bb4e87/layer2/ATDEMO")
 report=inspect(root/"WORLD.DAT")
 out=Path(".tmp/well_actions_v317.json");out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps({"status":report["status"],"records":len(report["records"]),"global_counts":report["global_counts"]}))