#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT = Path(__file__).resolve().parents[1]
contract = json.loads((ROOT / "data/tests/kg001_eugene_spawn_contract_v171.json").read_text(encoding="utf-8"))
runner = (ROOT / "scripts/room_manager.gd").read_text(encoding="utf-8")

expected = [
    ("EugenB", "TEXTURES/EUGBLD.XAF", "EUGENB.ANI",
     [362.298431, -90.386177, -533.626587], [0.573576, 0.0, -0.819152]),
    ("Eugene", "TEXTURES/EUGENE.XAF", "EUGENE.ANI",
     [387.180725, -93.206253, -472.210327], [0.773220, 0.0, -0.634137]),
]
rows = {row.get("character"): row for row in contract.get("npcs", [])}
checks = {
    "schema": contract.get("schema") == "openazrael.kg001.eugene_spawn_contract" and contract.get("version") == 171,
    "room": contract.get("room") == "R1",
    "identity_mapping": contract.get("coordinate_mapping") == "IDENTITY_XYZ_TO_GODOT_VECTOR3",
    "dimensions": contract.get("collision") == {"height": 15.0, "width": 12.0},
    "speed_recorded": contract.get("movement", {}).get("speed") == 12.0,
    "front_calibration_not_invented": contract.get("model_front_calibration") == "HOLD_SOURCE_PROOF",
    "no_placeholder_policy": contract.get("runtime_policy", {}).get("placeholder_model") == "FORBIDDEN",
    "runtime_hook": "_setup_r1_eugene_spawns()" in runner,
    "runtime_fail_closed": "EUGENE_SOURCE_MODEL_MISSING" in runner and "ResourceLoader.exists(model_path)" in runner,
    "runtime_no_placeholder": "PrimitiveMesh" not in runner[runner.find("func _setup_r1_eugene_spawns"):runner.find("func _setup_r1_doors")],
}
for character, xaf, ani, spawn, direction in expected:
    row = rows.get(character, {})
    checks[f"{character}_source"] = row.get("source_xaf") == xaf and row.get("source_ani") == ani
    checks[f"{character}_spawn"] = row.get("spawn") == spawn
    checks[f"{character}_direction"] = row.get("direction") == direction
    checks[f"{character}_runtime_model"] = row.get("runtime_model") == f"res://assets/characters/{character}/{character}.glb"

failed = [name for name, passed in checks.items() if not passed]
print(json.dumps({
    "schema": "openazrael.kg001.eugene_spawn_contract_validation",
    "version": 171,
    "status": "SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "checks": checks,
    "failed": failed,
    "runtime_status": "NOT_EXECUTED"
}, indent=2))
sys.exit(1 if failed else 0)
