#!/usr/bin/env python3
"""Build source-pinned R7 action IR; do not interpret puzzle branch semantics."""
import json,sys,hashlib
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from audit_well_actions_v317 import inspect
from analyze_world_sound_record_fields_v113 import parse_section0
CORPUS=Path(os.environ.get("OPENAZRAEL_CORPUS","F:/OpenRemaster/sources/materialized/openazrael_demo_atdemo_v1/bf0c87f731bb4e87/layer2/ATDEMO"))
SOURCE=CORPUS/"WORLD.DAT"
OUTPUT=ROOT/"data/runtime_generated/well_source_actions_v358.json"
def main():
 raw=SOURCE.read_bytes()
 sec,_=parse_section0(raw)
 audit=inspect(SOURCE)
 rows=[]
 for row in audit["records"]:
  op=row["opcode"]
  rows.append({"node":row["node"],"slot":row["slot"],"target_id":row["object_id"],"target_name":sec[row["object_id"]]["name"],"opcode":op,"operand":row["operand_s16"] if op==23 else row["operand_f32"],"axis_code":row["axis_code"],"steps":row["duration_candidate"],"source_offset":row["offset"]})
 assert len(rows)==24 and len({r["node"] for r in rows})==10
 payload={"schema":"openazrael.c8.well_actions.v358","version":1,"source_sha256":hashlib.sha256(raw).hexdigest(),"status":"SOURCE_BOUND_NOT_RUNTIME_FIDELITY","records":rows}
 OUTPUT.parent.mkdir(parents=True,exist_ok=True)
 OUTPUT.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
 reread=json.loads(OUTPUT.read_text(encoding="utf-8"))
 assert reread==payload
 print(json.dumps({"status":"PASS","records":len(rows),"source_sha256":payload["source_sha256"],"output":str(OUTPUT)}))
if __name__=="__main__":main()