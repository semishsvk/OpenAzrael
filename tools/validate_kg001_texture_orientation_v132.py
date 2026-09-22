#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_texture_orientation_contract_v132.json").read_text(encoding="utf-8"))
exporter=(ROOT/"tools/texture_pipeline/export_xaf_glb_v8.py").read_text(encoding="utf-8")
checks={
 "schema":contract.get("schema")=="openazrael.kg001.texture_orientation_contract" and contract.get("version")==132,
 "counts":contract.get("expected_classic_texture_count")==86 and contract.get("expected_used_texture_count")==75 and contract.get("expected_textured_primitive_count")==176,
 "unused_count":len(contract.get("expected_unused_textures",[]))==11,
 "explicit_keyhole":'"KEYHOLE#"' in exporter and "FLIP_V" in exporter,
 "explicit_bapmsg":'"BAPMSG"' in exporter and "FLIP_V" in exporter,
 "no_global_flip":"corrected[:,1]=1.0-corrected[:,1]" in exporter and "UV_CORRECTIONS" in exporter,
 "gltf_origin":contract.get("gltf_texture_origin")=="upper_left",
 "known_variant":any(x.get("node")=="broken01__mesh" and x.get("texture")=="BAPBROK#" for x in contract.get("allowed_source_authored_orientation_variants",[])),
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.texture_orientation_contract_validation","version":132,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","runtime_status":"NOT_EXECUTED","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
