#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.remaster_framework.fidelity import FidelityLayer, build_forensic_report

TMP=ROOT/".tmp/kg001"
FILES={
 "geometry_v122":TMP/"kg001_geometry_v122_runtime.json",
 "visibility_v123":TMP/"kg001_visibility_v123_runtime.json",
 "material_v124":TMP/"kg001_material_v124_runtime.json",
 "texture_orientation_v133":ROOT/"data/runtime_generated/demo_texture_orientation_v133.json",
 "transform_v125":TMP/"kg001_transform_v125_runtime.json",
 "visual_v126":TMP/"kg001_visual_v126_runtime.json",
 "reachable_visibility_v127":TMP/"kg001_reachable_visibility_v127_runtime.json",
 "portal_v129":TMP/"kg001_portal_v129_runtime.json",
 "interaction_v130":TMP/"kg001_interaction_v130_runtime.json",
 "package_v128":TMP/"kg001_packaged_v128_runtime.json",
}
FIDELITY=ROOT/"data/runtime_generated/demo_room_fidelity_v124.json"

def sha(path):
 h=hashlib.sha256();h.update(path.read_bytes());return h.hexdigest()
def load_layer(layer_id,path):
 if not path.is_file(): return None
 try:payload=json.loads(path.read_text(encoding="utf-8"))
 except Exception:return FidelityLayer(layer_id,"FAIL",sha(path),{"error":"invalid_json"})
 return FidelityLayer(layer_id,str(payload.get("status","FAIL")),sha(path),{"path":str(path.relative_to(ROOT)),"schema":payload.get("schema"),"version":payload.get("version")})
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--phase",choices=("preflight","package"),default="preflight");ap.add_argument("--out",type=Path);args=ap.parse_args()
 if not FIDELITY.is_file():
  print(json.dumps({"status":"FAIL","error":"fidelity manifest missing"}));return 1
 fidelity=json.loads(FIDELITY.read_text(encoding="utf-8"))
 base=["source","geometry_v122","visibility_v123","material_v124","texture_orientation_v133","transform_v125","visual_v126","reachable_visibility_v127","portal_v129","interaction_v130"]
 required=tuple(base+(["package_v128"] if args.phase=="package" else []))
 reports={}
 for room_id in ("R1","R7","R8"):
  room=fidelity.get("rooms",{}).get(room_id,{})
  layers=[FidelityLayer("source","PASS",str(room.get("room_fingerprint","")),{"asset_sha256":room.get("asset_sha256"),"mesh_count":room.get("mesh_count"),"triangle_count":room.get("triangle_count")})]
  for layer_id in required[1:]:
   layer=load_layer(layer_id,FILES[layer_id])
   if layer is not None:layers.append(layer)
  reports[room_id]=build_forensic_report(room_id,layers,required)
 status="PASS" if all(r["status"]=="PASS" for r in reports.values()) else "FAIL"
 out={"schema":"openazrael.kg001.room_forensic_report","version":131,"phase":args.phase,"status":status,"rooms":reports}
 dest=args.out or TMP/f"room_forensic_report_v131_{args.phase}.json";dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"status":status,"phase":args.phase,"out":str(dest),"rooms":{k:v["status"] for k,v in reports.items()}},indent=2))
 return 0 if status=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
