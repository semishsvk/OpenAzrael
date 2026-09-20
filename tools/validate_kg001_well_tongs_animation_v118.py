#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
runner = (ROOT / "scripts/kg001_well_tongs_animation_runner_v118.gd").read_text(encoding="utf-8")
interaction = (ROOT / "scripts/well_key_interaction.gd").read_text(encoding="utf-8")
state = (ROOT / "scripts/demo_state.gd").read_text(encoding="utf-8")
graph = json.loads((ROOT / "data/gameplay_event_graph_v87.json").read_text(encoding="utf-8"))
contract = json.loads(
    (ROOT / "data/tests/kg001_well_tongs_animation_contract_v118.json").read_text(
        encoding="utf-8"
    )
)
demo_evidence = json.loads(
    (ROOT / "data/tests/kg001_well_tongs_demo_evidence_v118.json").read_text(
        encoding="utf-8"
    )
)
fingerprints = json.loads(
    (ROOT / "data/backup/source_fingerprints.json").read_text(encoding="utf-8")
)

expected_steps = [
    "remove_room:R7Key",
    "play_sound:979TONGS.WAV",
    "add_room:R7Key",
    "remove_room:RustyTongR6",
    "remove_inventory:TONG6",
    "default_take:R7Key",
]
graph_row = graph.get("graphs", {}).get("R7_WELL_TONGS_USE", {})
runtime_fp = {
    row.get("path"): row
    for row in fingerprints.get("entries", [])
    if isinstance(row, dict)
}

checks = {
    "demo_evidence": (
        demo_evidence.get("schema") == "openazrael.kg001.well_tongs_demo_evidence"
        and demo_evidence.get("version") == 118
        and demo_evidence.get("status") == "PASS"
        and demo_evidence.get("interpretation", {}).get("invented_tween_prohibited") is True
        and demo_evidence.get("interpretation", {}).get("transform_or_rotation_action_in_compiled_group") is False
    ),
    "demo_source_hashes": (
        demo_evidence.get("sources", {}).get("PUZZLES.DAT", {}).get("sha256")
        == "b8131cf823edb184f04740d5af0a457f4d684e7b0be654b529ec7cdfde1739d1"
        and demo_evidence.get("sources", {}).get("WORLD.DAT", {}).get("sha256")
        == "f055948e302fa2f6ba364f7ebd3b4bc45f20ef4445af4946c63e4e313a084ae9"
        and demo_evidence.get("sources", {}).get("R.EXE", {}).get("sha256")
        == "381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00"
    ),
    "contract_schema": (
        contract.get("schema") == "openazrael.kg001.well_tongs_animation_contract"
        and contract.get("version") == 118
        and contract.get("status") == "SOURCE_CONTRACT_READY_RUNTIME_PENDING"
    ),
    "official_demo_action_count": (
        len(contract.get("exact_compiled_action_sequence", [])) == 5
    ),
    "official_demo_opcode_order": (
        [row.get("opcode") for row in contract.get("exact_compiled_action_sequence", [])]
        == ["0x08", "0x28", "0x07", "0x08", "0x09"]
    ),
    "original_sound_identity": (
        contract.get("sound", {}).get("filename") == "979TONGS.WAV"
        and contract.get("sound", {}).get("sha256")
        == "46f19b82e3c85ce5c4a198d745fe9ab5789a3d1a32d552748bb5b8585e0c8469"
        and abs(contract.get("sound", {}).get("duration_seconds", 0) - 0.9501133786848073) < 1e-12
    ),
    "runtime_restore_fingerprint": (
        runtime_fp.get("assets/audio/979TONGS.WAV", {}).get("size") == 20994
        and runtime_fp.get("assets/audio/979TONGS.WAV", {}).get("sha256")
        == "46f19b82e3c85ce5c4a198d745fe9ab5789a3d1a32d552748bb5b8585e0c8469"
    ),
    "event_ir_sound_edge": (
        graph_row.get("actions")
        == [{
            "op": "play_sound",
            "asset": "979TONGS.WAV",
            "semantic": "R7 well + tongs use",
            "confidence": "VERIFIED",
        }]
    ),
    "no_invented_transform_animation": (
        contract.get("dispatch_observation", {}).get("transform_or_rotation_opcode_present") is False
        and contract.get("dispatch_observation", {}).get("continuous_tween_required") is False
        and "create_tween" not in interaction
        and "AnimationPlayer" not in interaction
    ),
    "production_trace_exact_order": (
        all(f'_step("{step}")' in interaction for step in expected_steps)
    ),
    "production_calls_exact_sound_graph": (
        'LegacyEvents.run("R7_WELL_TONGS_USE")' in interaction
    ),
    "production_room_key_remove_add": (
        interaction.count("key_visual.visible = false") >= 2
        and "key_visual.visible = true" in interaction
    ),
    "production_consumes_tongs": (
        'remove("rusty_tongs")' in state
        and 'acquire("well_key")' in state
        and 'set_puzzle_node("R7KeyTake")' in state
        and 'set_flag("R7key")' in state
    ),
    "production_state_order": (
        interaction.find('DemoState.remove("rusty_tongs")')
        < interaction.find('DemoState.complete_well_key_take()')
        and interaction.find('DemoState.remove("rusty_tongs")') >= 0
        and interaction.find('DemoState.complete_well_key_take()') >= 0
        and "func complete_well_key_take()" in state
    ),
    "runner_negative_precondition": all(
        value in runner
        for value in (
            "without_tongs_no_steps",
            "without_tongs_no_key",
            "without_tongs_R7KeyTake_false",
            "without_tongs_R7key_false",
            "without_tongs_key_stays_visible",
        )
    ),
    "runner_exact_positive_sequence": (
        "const EXPECTED_STEPS := [" in runner
        and "exact_demo_action_order" in runner
        and all(f'"{step}"' in runner for step in expected_steps)
    ),
    "runner_checks_original_audio": (
        '"res://assets/audio/979TONGS.WAV"' in runner
        and "979tongs_duration_matches_demo" in runner
        and "logical_979tongs_emitted" in runner
    ),
    "runner_checks_completion": all(
        value in runner
        for value in (
            "well_key_acquired",
            "tongs_consumed",
            "R7KeyTake_set",
            "R7key_set",
            "key_absent_after_default_take",
        )
    ),
}

failed = [name for name, ok in checks.items() if not ok]
out = {
    "schema": "openazrael.kg001.well_tongs_animation_contract_validation",
    "version": 118,
    "status": "SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "runtime_status": "NOT_EXECUTED",
    "checks": checks,
    "failed": failed,
    "boundary": (
        "Source validation binds OpenAzrael to the recovered demo action stream. "
        "Only a current Godot v118 runtime PASS proves restored-asset execution."
    ),
}
print(json.dumps(out, indent=2))
sys.exit(1 if failed else 0)
