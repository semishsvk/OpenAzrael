#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"data/tests/kg001_eugene_model_front_contract_v188.json"
M=ROOT/"scripts/eugene_movement_v172.gd"
def main():
 c=json.loads(C.read_text()); m=M.read_text()
 checks={
 "contract":c.get("version")==188 and c.get("status")=="SOURCE_GEOMETRY_VERIFIED",
 "axis":c["conclusion"]["model_front_local_axis"]=="+X",
 "bilateral":c["evidence"]["bilateral_axis"]["local_axis"]=="+Z",
 "vertical":c["evidence"]["vertical_axis"]["local_axis"]=="+Y",
 "longitudinal":c["evidence"]["longitudinal_sign"]["local_axis"]=="+X",
 "runtime_binding":'model_front_calibration := "SOURCE_XAF_V188_LOCAL_PLUS_X_ROOT_TRANSFORM"' in m,
 "no_arbitrary_yaw":"Do not add arbitrary 90/180 degree yaw correction." in c["conclusion"]["calibration_policy"]
 }
 failed=[k for k,v in checks.items() if not v]
 print(json.dumps({"schema":"openazrael.kg001.eugene_model_front_validation","version":188,"status":"SOURCE_MODEL_FRONT_PASS" if not failed else "FAIL","checks":checks,"failed":failed,"runtime_status":"NOT_EXECUTED"},indent=2))
 return 1 if failed else 0
if __name__=="__main__":sys.exit(main())
