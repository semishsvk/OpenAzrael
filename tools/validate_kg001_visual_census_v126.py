#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
runner=(ROOT/"scripts/kg001_visual_census_runner_v126.gd").read_text(encoding="utf-8")
contract=json.loads((ROOT/"data/tests/kg001_visual_census_contract_v126.json").read_text(encoding="utf-8"))
checks={
 "schema":contract.get("schema")=="openazrael.kg001.visual_census_contract" and contract.get("version")==126,
 "graphical_required":'DisplayServer.get_name()=="headless"' in runner and "BLOCKED_GRAPHICAL_RENDER_REQUIRED" in runner,
 "direct_vs_runtime":all(x in runner for x in ("ROOM_PATHS","manager.current_room.duplicate()","_pixel_fingerprint")),
 "fixed_views":"for view_index in range(3)" in runner,
 "geometry_only":all(x in runner for x in ("SHADING_MODE_UNSHADED","material_override")),
 "png_evidence":"save_png" in runner,
 "no_ai":"AI" in contract.get("forbids",[])[0] if contract.get("forbids") else False,
 "marker":"OPENAZRAEL_KG001_VISUAL_CENSUS_V126" in runner,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.visual_census_contract_validation","version":126,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","runtime_status":"NOT_EXECUTED","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
