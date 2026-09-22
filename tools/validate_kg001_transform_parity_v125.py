#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
runner=(ROOT/"scripts/kg001_transform_parity_runner_v125.gd").read_text(encoding="utf-8")
contract=json.loads((ROOT/"data/tests/kg001_transform_parity_contract_v125.json").read_text(encoding="utf-8"))
checks={
 "schema":contract.get("schema")=="openazrael.kg001.transform_parity_contract" and contract.get("version")==125,
 "all_rooms":contract.get("scope")==["R1","R7","R8"],
 "transform":all(x in runner for x in ("transform_values","TRANSFORM_TOL","_transform")),
 "bounds":all(x in runner for x in ("bounds_values","BOUNDS_TOL","_bounds")),
 "fresh_state":"state.reset_all()" in runner,
 "no_reposition":all(x not in runner for x in ("global_position =","rotation =","scale =")),
 "marker":"OPENAZRAEL_KG001_TRANSFORM_V125" in runner,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.transform_contract_validation","version":125,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","runtime_status":"NOT_EXECUTED","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
