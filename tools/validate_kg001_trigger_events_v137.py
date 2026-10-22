#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def main():
    evidence = load_json("data/xaf_trigger_evidence.json")
    ir = load_json("data/trigger_event_ir_v137.json")
    graphs = load_json("data/gameplay_event_graph_v87.json")
    contract = load_json("data/tests/kg001_trigger_event_contract_v137.json")
    room_manager = (ROOT / "scripts/room_manager.gd").read_text(encoding="utf-8")
    event_runner = (ROOT / "scripts/legacy_event_runner_v87.gd").read_text(encoding="utf-8")

    checks = {}
    checks["schema"] = (
        ir.get("schema") == "openazrael.trigger_event_ir"
        and ir.get("version") == 137
        and contract.get("schema") == "openazrael.kg001.trigger_event_contract"
        and contract.get("version") == 137
    )

    evidence_names = {
        room: [str(row["name"]) for row in evidence["rooms"][room]["triggers"]]
        for room in ("R1", "R7", "R8")
    }
    ir_rows = {room: ir["rooms"].get(room, []) for room in ("R1", "R7", "R8")}
    ir_names = {room: [str(row.get("trigger", "")) for row in ir_rows[room]] for room in ir_rows}

    checks["counts"] = (
        {room: len(evidence_names[room]) for room in evidence_names}
        == contract["expected_trigger_counts"]
        and sum(len(v) for v in evidence_names.values()) == contract["expected_total_triggers"]
    )
    checks["exact_trigger_coverage"] = all(
        len(ir_names[room]) == len(set(ir_names[room]))
        and set(ir_names[room]) == set(evidence_names[room])
        for room in evidence_names
    )

    allowed = {
        "transition", "activation_enter", "condition_zone", "state_visual",
        "helper_geometry", "support_collision", "UNKNOWN_HOLD", "hazard_HOLD"
    }
    checks["classes_explicit"] = all(
        str(row.get("class", "")) in allowed
        for rows in ir_rows.values() for row in rows
    )

    transition_pairs = {
        f'{row["source_room"]}/{row["trigger"]}'
        for row in evidence["demo_transitions"]
    }
    classified_transitions = {
        f"{room}/{row['trigger']}"
        for room, rows in ir_rows.items()
        for row in rows if row.get("class") == "transition"
    }
    checks["transitions_exact"] = (
        transition_pairs == set(contract["transition_triggers"])
        and classified_transitions == transition_pairs
    )

    by_key = {
        f"{room}/{row['trigger']}": row
        for room, rows in ir_rows.items() for row in rows
    }
    ghost = by_key.get("R7/zxactghost", {})
    checks["ghost_binding"] = (
        ghost.get("class") == "activation_enter"
        and ghost.get("event_graph") == "R7_NIAMH_ACTIVATE"
        and ghost.get("one_shot_flag") == "R7NiamhActivated"
        and ghost.get("animation_requirement", {}).get("character") == "Niamh"
        and ghost.get("animation_requirement", {}).get("family") == "NOLOOP1"
        and ghost.get("animation_requirement", {}).get("next_family") == "REST"
        and ghost.get("animation_requirement", {}).get("target_object") == "nibody"
        and ghost.get("animation_requirement", {}).get("fallback") == "NONE"
    )

    graph = graphs.get("graphs", {}).get("R7_NIAMH_ACTIVATE", {})
    actions = graph.get("actions", [])
    ops = [str(a.get("op", "")) for a in actions]
    anim = next((a for a in actions if a.get("op") == "request_character_animation"), {})
    convo = next((a for a in actions if a.get("op") == "request_conversation"), {})
    checks["ghost_graph"] = (
        {"set_flag", "set_puzzle_node", "request_character_animation", "request_conversation"}.issubset(set(ops))
        and anim.get("character") == "Niamh"
        and anim.get("family") == "NOLOOP1"
        and anim.get("next_family") == "REST"
        and anim.get("target_object") == "nibody"
        and anim.get("source_required") is True
        and convo.get("character") == "Niamh"
        and convo.get("source_required") is True
        and not any("line" in a or "text" in a for a in actions)
    )

    plate = by_key.get("R8/zxplate", {})
    checks["condition_zone_not_autofire"] = (
        plate.get("class") == "condition_zone"
        and "r8_bible_interaction.gd" in str(plate.get("authority", ""))
        and not plate.get("event_graph")
    )

    active = [
        (room, row)
        for room, rows in ir_rows.items()
        for row in rows
        if row.get("class") == "activation_enter"
    ]
    checks["active_bindings_have_graphs"] = all(
        row.get("event_graph") in graphs.get("graphs", {})
        for _room, row in active
    )

    checks["runtime_dispatcher"] = all(marker in room_manager for marker in [
        'TRIGGER_EVENT_IR_PATH := "res://data/trigger_event_ir_v137.json"',
        "func _trigger_binding(",
        "func _dispatch_trigger_edge(",
        'trigger_class == "activation_enter"',
        "LegacyEvents.run(graph_id)",
        "_dispatch_trigger_edge(trigger_name, inside)",
        "if had_state:",
    ])
    setup_start = room_manager.find("func _setup_r7_character_state()")
    setup_end = room_manager.find("\nfunc ", setup_start + 1)
    setup_body = room_manager[setup_start:setup_end if setup_end >= 0 else len(room_manager)]
    visibility_ops = {"hide", "show", "add_room", "remove_room", "set_visible"}
    graph_visibility_ops = [
        op for op in ops if op in visibility_ops
    ]
    checks["niamh_visibility_state"] = (
        setup_start >= 0
        and 'var niamh_body := _find_node("nibody")' in setup_body
        and "niamh_body.visible = true" in setup_body
        and 'DemoState.flag("R7NiamhActivated")' not in setup_body
        and not graph_visibility_ops
        and "target.visible = true" in room_manager
    )
    checks["animation_source_only"] = (
        "func _on_character_animation_requested(" in room_manager
        and 'has_animation(StringName(family))' in room_manager
        and 'animation_player.play(StringName(family))' in room_manager
        and "HOLD_SOURCE_CLIP_MISSING" in room_manager
        and "create_tween()" not in room_manager[room_manager.find("func _on_character_animation_requested("):room_manager.find("func _setup_r7_switchboard()")]
    )
    checks["event_runner_requests"] = all(marker in event_runner for marker in [
        "signal character_animation_requested(request: Dictionary)",
        "signal conversation_requested(request: Dictionary)",
        '"request_character_animation":',
        "character_animation_requested.emit(action.duplicate(true))",
        '"request_conversation":',
        "conversation_requested.emit(action.duplicate(true))",
    ])
    checks["fail_closed_holds"] = (
        ir.get("policy", {}).get("unknown_semantics_fail_closed") is True
        and ir.get("policy", {}).get("guessed_animation_fallback_forbidden") is True
        and all(
            "event_graph" not in row
            for rows in ir_rows.values() for row in rows
            if row.get("class") in ("UNKNOWN_HOLD", "hazard_HOLD")
        )
    )

    failed = [name for name, ok in checks.items() if not ok]
    out = {
        "schema": "openazrael.kg001.trigger_event_contract_validation",
        "version": 137,
        "status": "SOURCE_CONTRACT_PASS" if not failed else "FAIL",
        "runtime_status": "NOT_EXECUTED",
        "trigger_count": sum(len(v) for v in evidence_names.values()),
        "classified_count": sum(len(v) for v in ir_names.values()),
        "checks": checks,
        "failed": failed,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not failed else 1

if __name__ == "__main__":
    raise SystemExit(main())
