#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
contract=json.loads(
    (ROOT/"data/tests/kg001_texture_orientation_contract_v133.json")
    .read_text(encoding="utf-8")
)
exporter=(ROOT/"tools/texture_pipeline/export_xaf_glb_v8.py").read_text(encoding="utf-8")
audit=(ROOT/"tools/audit_demo_texture_orientation_v133.py").read_text(encoding="utf-8")
restore=(ROOT/"tools/restore_candidate_assets.py").read_text(encoding="utf-8")
tapestry=(ROOT/"scripts/r8_tapestry_interaction.gd").read_text(encoding="utf-8")

checks={
    "schema": (
        contract.get("schema")=="openazrael.kg001.texture_orientation_contract"
        and contract.get("version")==133
    ),
    "counts": (
        contract.get("expected_classic_texture_count")==86
        and contract.get("expected_used_texture_count")==75
        and contract.get("expected_textured_primitive_count")==176
        and contract.get("expected_strong_vertical_mappings")==87
        and contract.get("expected_direct_upright_vertical_mappings")==85
    ),
    "unused_count": len(contract.get("expected_unused_textures",[]))==11,
    "global_export_adapter": all(token in exporter for token in (
        'UV_EXPORT_CORRECTION = "TRIMESH_PRE_FLIP_V_PRESERVE_XAF_GLTF"',
        "corrected[:,1]=1.0-corrected[:,1]",
        "source_uv_sha256",
        "export_input_uv_sha256",
    )),
    "no_per_texture_uv_hacks": (
        "UV_CORRECTIONS" not in exporter
        and "KEYHOLE#" not in exporter
        and "BAPMSG" not in exporter
    ),
    "restore_source_binding": all(token in restore for token in (
        "candidate4_texture_restore_v133.json",
        "source_azf_sha256",
        "source_xaf_sha256",
        "runtime_png_sha256",
        "audit_demo_texture_orientation_v133.py",
    )),
    "raw_gltf_audit": all(token in audit for token in (
        "read_glb",
        "accessor_array",
        "source_uv_sha256",
        "raw_uv_not_source_exact",
        "primitive_base_color_image",
    )),
    "semantic_sentinels": (
        all(token in audit for token in (
            "doorcor2__1KEYHOLE",
            "BAPBACK1",
            "BAPFRNT1",
            "BAPLEFT1",
            "BAPRGHT1",
            "tapestry2a__mesh",
        ))
        and "expected_variants" in audit
        and "actual_variants" in audit
        and "source_orientation_variants" in audit
    ),
    "tapestry_state_orientation": (
        'rotate_x(PI)' in tapestry
        and '"rotation:x"' in tapestry
        and '"rotation:y"' not in tapestry
    ),
    "no_required_per_texture_corrections": contract.get("required_uv_corrections")=={},
    "gltf_upper_left": contract.get("gltf_texture_origin")=="upper_left",
    "source_variants_exact": {
        (x.get("room"),x.get("node"),x.get("texture"))
        for x in contract.get("source_authored_state_variants",[])
    } == {
        ("R8","tapestry2a__mesh","BAPMSG"),
        ("R8","broken01__mesh","BAPBROK#"),
    },
}
failed=[name for name,ok in checks.items() if not ok]
print(json.dumps({
    "schema":"openazrael.kg001.texture_orientation_contract_validation",
    "version":133,
    "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "asset_status":"NOT_EXECUTED",
    "checks":checks,
    "failed":failed,
},indent=2))
sys.exit(1 if failed else 0)
