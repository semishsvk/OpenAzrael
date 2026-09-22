#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_texture_orientation_contract_v133.json").read_text(encoding="utf-8"))
exporter=(ROOT/"tools/texture_pipeline/export_xaf_glb_v8.py").read_text(encoding="utf-8")
audit=(ROOT/"tools/audit_demo_texture_orientation_v133.py").read_text(encoding="utf-8")
checks={
 "schema":contract.get("schema")=="openazrael.kg001.texture_orientation_contract" and contract.get("version")==133,
 "counts":contract.get("expected_classic_texture_count")==86 and contract.get("expected_used_texture_count")==75 and contract.get("expected_textured_primitive_count")==176,
 "unused_count":len(contract.get("expected_unused_textures",[]))==11,
 "correction_policy":all(token in exporter for token in ('"KEYHOLE#"','"BAPMSG"',"UV_CORRECTIONS","FLIP_V_V133_TAPESTRY_MESSAGE")),
 "no_global_flip":"stem in UV_CORRECTIONS" in exporter,
 "full_binding_audit":all(token in audit for token in ("embedded_texture_mismatch","uv_count_ok","uv_finite","textured_primitive_count")),
 "semantic_sentinels":all(token in audit for token in ("doorcor2__1KEYHOLE","tapestry2a__mesh","BAPBACK1","BAPLEFT1","BAPRGHT1","BAPFRNT1")),
 "gltf_upper_left":contract.get("gltf_texture_origin")=="upper_left",
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.texture_orientation_contract_validation","version":133,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","asset_status":"NOT_EXECUTED","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
