#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
runner=(ROOT/"scripts/kg001_material_texture_runner_v124.gd").read_text(encoding="utf-8")
gen=(ROOT/"tools/build_demo_room_fidelity_manifest_v124.py").read_text(encoding="utf-8")
contract=json.loads((ROOT/"data/tests/kg001_material_texture_contract_v124.json").read_text(encoding="utf-8"))
checks={
 "schema":contract.get("schema")=="openazrael.kg001.material_texture_parity_contract" and contract.get("version")==124,
 "source_derived_reference":all(x in gen for x in ("read_glb","accessor_array","RAW_GLTF_UPPER_LEFT","mesh_count","triangle_count")),
 "uv_fingerprint":all(x in runner for x in ("quantized_uv_sha","_uv_parity","uv_sha256")),
 "material_texture":all(x in runner for x in ("resource_name","albedo_texture","_material_name","_texture_present")),
 "colorkey":all(x in runner for x in ("legacy_colorkey","TRANSPARENCY_DISABLED")),
 "no_fabricated_geometry":all(x not in runner for x in ("MeshInstance3D.new()","ArrayMesh.new()","BoxMesh.new()")),
 "marker":"OPENAZRAEL_KG001_MATERIAL_TEXTURE_V124" in runner,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.material_texture_contract_validation","version":124,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","runtime_status":"NOT_EXECUTED","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
