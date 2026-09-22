#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
runner=(ROOT/"scripts/kg001_packaged_parity_runner_v128.gd").read_text(encoding="utf-8")
exporter=(ROOT/"tools/export_candidate3.py").read_text(encoding="utf-8")
contract=json.loads((ROOT/"data/tests/kg001_packaged_parity_contract_v128.json").read_text(encoding="utf-8"))
checks={
 "schema":contract.get("schema")=="openazrael.kg001.packaged_parity_contract" and contract.get("version")==128,
 "asset_manifest":"runtime_asset_manifest_v128.json" in runner,
 "cursor_assets_bound":'assets/ui/mice' in (ROOT/"tools/build_runtime_asset_manifest_v128.py").read_text(encoding="utf-8") and 'cursor_png_count' in (ROOT/"tools/build_runtime_asset_manifest_v128.py").read_text(encoding="utf-8"),
 "fidelity_manifest":"H.MANIFEST_PATH" in runner,
 "asset_hashes":all(x in runner for x in ("asset_bytes:","asset_sha:","_sha_bytes")),
 "geometry_material_transform":all(x in runner for x in ("_triangles","_uv","_transform","_bounds","_material","_texture")),
 "visibility":all(x in runner for x in ("fresh_hidden","fresh_required_visible")),
 "exporter_executes":("kg001_packaged_parity_runner_v128.gd" in exporter and "OPENAZRAEL_KG001_PACKAGED_PARITY_V128" in exporter),
 "marker":"OPENAZRAEL_KG001_PACKAGED_PARITY_V128" in runner,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.packaged_parity_contract_validation","version":128,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","runtime_status":"NOT_EXECUTED","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
