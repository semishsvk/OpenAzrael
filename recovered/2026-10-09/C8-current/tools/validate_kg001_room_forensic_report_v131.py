#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
tool=(ROOT/"tools/build_room_forensic_report_v131.py").read_text(encoding="utf-8")
contract=json.loads((ROOT/"data/tests/kg001_room_forensic_report_contract_v131.json").read_text(encoding="utf-8"))
expected_preflight=[
 "source","geometry_v122","visibility_v123","material_v124","texture_orientation_v133",
 "transform_v125","visual_v126","reachable_visibility_v127","portal_v129","interaction_v130",
]
expected_package=expected_preflight+["package_v128"]
checks={
 "schema":contract.get("schema")=="openazrael.kg001.room_forensic_report_contract" and contract.get("version")==131,
 "all_rooms":contract.get("rooms")==["R1","R7","R8"],
 "preflight_layers":contract.get("preflight_layers")==expected_preflight,
 "package_layers":contract.get("package_layers")==expected_package,
 "builder_has_texture_orientation":"texture_orientation_v133" in tool,
 "generic_framework":"build_forensic_report" in tool and "FidelityLayer" in tool,
 "fail_closed":'all(r["status"]=="PASS"' in tool,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.room_forensic_report_contract_validation","version":131,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
