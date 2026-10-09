#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
runner=(ROOT/"scripts/kg001_portal_geometry_runner_v129.gd").read_text(encoding="utf-8")
contract=json.loads((ROOT/"data/tests/kg001_portal_geometry_contract_v129.json").read_text(encoding="utf-8"))
checks={
 "schema":contract.get("schema")=="openazrael.kg001.portal_geometry_closure_contract" and contract.get("version")==129,
 "four_edges":"edges.size()==4" in runner,
 "door_mapping":all(x in runner for x in ("zxcoriR5","doorcor01","zxcoriR2","doorcor2")),
 "source_records":all(x in runner for x in ('"_trigger_record"','"_view_record"')),
 "authored_support":all(x in runner for x in ("intersect_ray","collision_mask","_spawn_at_portal")) if False else ("intersect_ray" in runner and "_spawn_at_portal" in runner),
 "no_replacement_geometry":all(x not in runner for x in ("StaticBody3D.new()","CollisionShape3D.new()","BoxShape3D.new()")),
 "marker":"OPENAZRAEL_KG001_PORTAL_GEOMETRY_V129" in runner,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.portal_geometry_contract_validation","version":129,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","runtime_status":"NOT_EXECUTED","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
