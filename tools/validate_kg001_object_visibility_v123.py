#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_object_visibility_contract_v123.json").read_text(encoding="utf-8"))
runner=(ROOT/"scripts/kg001_object_visibility_runner_v123.gd").read_text(encoding="utf-8")
manager=(ROOT/"scripts/room_manager.gd").read_text(encoding="utf-8")

checks={
    "contract_schema": (
        contract.get("schema")=="openazrael.kg001.object_visibility_parity_contract"
        and contract.get("version")==123
        and contract.get("status")=="SOURCE_CONTRACT_READY_RUNTIME_PENDING"
    ),
    "all_demo_rooms": contract.get("scope")==["R1","R7","R8"],
    "critical_pickups_bound": all(token in json.dumps(contract) for token in (
        "TONG6__mesh","r1p1__mesh","r3t1__mesh","nibdyky01__mesh","r8t3__mesh","r8t4__mesh","lens__mesh"
    )),
    "exact_fresh_hidden_set": "actual_hidden == expected_hidden" in runner,
    "all_meshes_audited": all(token in runner for token in (
        "_mesh_visibility","is_visible_in_tree()","EXPECTED_MESH_COUNTS"
    )),
    "pickup_lifecycle": all(token in runner for token in (
        "tongs_no_respawn_after_consumption",
        "piece1_loose_no_respawn_after_placement",
        "piece3_loose_no_respawn",
        "piece4_loose_no_respawn",
        "parchment_no_respawn_while_held"
    )),
    "r8_state_visuals": all(token in runner for token in (
        "water_visible_before_drain","water_hidden_after_drain",
        "lens_visible_before_retrieval","installed_lens_visible_after_place",
        "shield_visible_after_door","message_visible_after_rotate"
    )),
    "source_consumed_flags": all(token in manager for token in (
        '"TONG6": "R7key"',
        '"r3t1": "R8Tap1"',
        '"r8t3": "R8Tap3"',
        '"r8t4": "R8Tap4"',
        "removed_from_authored_location"
    )),
    "clear_object_hidden": (
        '["TRANSPARANT", "CLEAR_OBJECT"]' in manager
        and "well_pzpa1__mesh" in runner
        and "well_pzpa2__mesh" in runner
    ),
    "no_direct_visual_fabrication": all(token not in runner for token in (
        "MeshInstance3D.new()","ArrayMesh.new()","BoxMesh.new()","PlaneMesh.new()"
    )),
    "result_marker": "OPENAZRAEL_KG001_OBJECT_VISIBILITY_V123" in runner,
    "runtime_boundary": "asset-backed Godot v123 PASS" in contract.get("evidence_boundary",""),
}
failed=[k for k,v in checks.items() if not v]
out={"schema":"openazrael.kg001.object_visibility_contract_validation","version":123,
     "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","runtime_status":"NOT_EXECUTED",
     "checks":checks,"failed":failed}
print(json.dumps(out,indent=2))
sys.exit(1 if failed else 0)
