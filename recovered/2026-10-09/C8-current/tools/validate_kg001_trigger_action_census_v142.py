#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

def load_json(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

contract = load_json("data/tests/kg001_trigger_action_census_contract_v142.json")
trigger_ir = load_json("data/trigger_event_ir_v137.json")
xaf = load_json("data/xaf_trigger_evidence.json")
graphs = load_json("data/gameplay_event_graph_v87.json").get("graphs", {})
manager = (ROOT / "scripts/room_manager.gd").read_text(encoding="utf-8")
trigger_runner = (ROOT / "scripts/kg001_trigger_event_runner_v137.gd").read_text(encoding="utf-8")
r8_pppv = (ROOT / "tools/openazrael_adapters/r8_pppv.py").read_text(encoding="utf-8")
transition_pppv = (ROOT / "tools/openazrael_adapters/transition_pppv.py").read_text(encoding="utf-8")
all_transitions = (ROOT / "scripts/kg001_all_transition_runner_v141.gd").read_text(encoding="utf-8")
v110 = load_json("data/tests/kg001_room_trigger_runtime_v110.json")
v111 = load_json("data/tests/kg001_full_demo_runtime_v111.json")

def key(room, trigger):
    return f"{room}/{trigger}"

ir_rows = []
for room, rows in trigger_ir.get("rooms", {}).items():
    for row in rows:
        ir_rows.append((room, row))

xaf_rows = []
for room in ("R1", "R7", "R8"):
    for row in xaf.get("rooms", {}).get(room, {}).get("triggers", []):
        xaf_rows.append((room, row))

ir_names = {key(room, str(row.get("trigger", ""))) for room, row in ir_rows}
xaf_names = {key(room, str(row.get("name", ""))) for room, row in xaf_rows}
class_counts = Counter(str(row.get("class", "")) for _, row in ir_rows)

expected_holds = set(contract.get("research_holds", {}))
actual_holds = {
    key(room, str(row.get("trigger", "")))
    for room, row in ir_rows
    if str(row.get("class", "")) in {"UNKNOWN_HOLD", "hazard_HOLD"}
}
active = {
    key(room, str(row.get("trigger", ""))): row
    for room, row in ir_rows
    if str(row.get("class", "")) == "activation_enter"
}
conditions = {
    key(room, str(row.get("trigger", ""))): row
    for room, row in ir_rows
    if str(row.get("class", "")) == "condition_zone"
}

transition_set = {
    f"{row['source_room']}/{row['trigger']}->{row['destination_room']}"
    for row in xaf.get("demo_transitions", [])
}

checks = {
    "contract_schema": (
        contract.get("schema") == "openazrael.kg001.trigger_action_census_contract"
        and contract.get("version") == 142
    ),
    "all_29_xaf_triggers_classified_exactly_once": (
        len(ir_rows) == len(xaf_rows) == contract.get("expected_total_triggers") == 29
        and ir_names == xaf_names
    ),
    "class_counts_exact": dict(class_counts) == contract.get("expected_class_counts"),
    "only_niamh_is_automatic_entry": set(active) == {"R7/zxactghost"},
    "only_zxplate_is_condition_zone": set(conditions) == {"R8/zxplate"},
    "hold_inventory_exact": actual_holds == expected_holds,
    "holds_have_no_event_graph": all(
        not str(row.get("event_graph", ""))
        for _, row in ir_rows
        if str(row.get("class", "")) in {"UNKNOWN_HOLD", "hazard_HOLD"}
    ),
    "transition_set_exact": transition_set == set(contract.get("transitions", [])),
}

niamh = active.get("R7/zxactghost", {})
niamh_graph = graphs.get(str(niamh.get("event_graph", "")), {})
niamh_ops = [str(row.get("op", "")) for row in niamh_graph.get("actions", [])]
checks.update({
    "niamh_graph_bound": (
        niamh.get("event_graph") == "R7_NIAMH_ACTIVATE"
        and niamh.get("one_shot_flag") == "R7NiamhActivated"
    ),
    "niamh_required_ops_exact": set(niamh_ops) == {
        "set_flag", "set_puzzle_node",
        "request_character_animation", "request_conversation"
    },
    "niamh_production_dispatch": all(token in manager for token in (
        'trigger_class == "activation_enter" and entered',
        "LegacyEvents.run(graph_id)",
        "one_shot_already_fired",
    )),
    "niamh_source_animation_fail_closed": all(token in manager for token in (
        "HOLD_SOURCE_CLIP_MISSING",
        "assets/characters/%s/%s.tres",
        "no fallback animation will be synthesized",
    )),
    "niamh_runtime_runner_observes_dispatch": all(token in trigger_runner for token in (
        "R7_niamh_activation_flag",
        "R7_niamh_animation_request_observed",
        "R7_niamh_one_shot_flag_stable",
        "BLOCKED_SOURCE_ANIMATION",
    )),
})

checks.update({
    "zxplate_does_not_autofire": (
        "condition_zone" in trigger_ir["rooms"]["R8"][5].get("class", "")
        and 'trigger_class == "activation_enter"' in manager
        and 'trigger_class == "condition_zone"' not in manager
    ),
    "zxplate_pppv_physical_entry": all(token in r8_pppv for token in (
        'scenario_id="openazrael.r8.optical_sequence"',
        '"goal_trigger": "zxplate"',
        'execution_mode=ExecutionMode.INTERACTION_PROBE',
        'target="Interact_R8Bible"',
        '"path": "puzzle.R8LensLook"',
        '"path": "puzzle.R8RaiseTimer"',
        '"path": "puzzle.DoorR8"',
        '"asset": "S121.WAV"',
        '"asset": "799SECDR.WAV"',
        '"observation_id": "r8_lens_motion"',
        '"observation_id": "r8_secret_door_motion"',
        '"observation_id": "r8_shield_visibility"',
    )),
    "four_transition_pppv_paths": all(token in transition_pppv for token in (
        'trigger="zxcoriR5"',
        'trigger="zxwell2R6"',
        'trigger="zxcoriR2"',
        'trigger="zxorrery"',
        "teleport_allowed_during_action",
        "destination_spawn_validation_required",
    )),
    "v141_real_input_transition_chain": all(token in all_transitions for token in (
        "production CharacterBody3D Input via PPPVNavigator",
        '"zxcoriR5"',
        '"zxwell2R6"',
        '"zxcoriR2"',
        '"zxorrery"',
        "no target teleport",
    )),
    "historical_v110_transition_pass": (
        v110.get("status") == "PASS"
        and bool(v110.get("_commit_sha"))
    ),
    "historical_v111_optical_pass": (
        v111.get("status") == "PASS"
        and "R8RaiseTimer" in str(v111.get("_output_tail", ""))
        and "DoorR8" in str(v111.get("_output_tail", ""))
        and bool(v111.get("_commit_sha"))
    ),
    "r1_entry_hud_source_bound": (
        "R1/zxentry" not in expected_holds
        and contract.get("partial_source_gates", {}).get("R1/zxentry", {}).get("non_hud_side_effects") == "NOT_FULLY_ATTESTED"
        and next((row for room,row in ir_rows if room == "R1" and row.get("trigger") == "zxentry"), {}).get("class") == "hud_startup"
        and load_json("data/ui/legacy_hud_startup_v215.json").get("startup_message_ids") == [86,138,136,137,139]
        and load_json("data/ui/legacy_hud_startup_v215.json").get("different_source_buffer_pixels") == 0
        and load_json("data/ui/legacy_hud_startup_v215.json").get("fixed_source_hz_claimed") is False
    ),
    "r7_death_stays_hold": (
        {"R7/death", "R7/zydeath", "R7/zxdeath"} <= expected_holds
        and "R7WellDeathAZ" in " ".join(
            contract["research_holds"]["R7/death"].get("evidence", [])
        )
    ),
    "hold_dispatch_is_diagnostic_only": all(token in manager for token in (
        'trigger_class in ["UNKNOWN_HOLD", "hazard_HOLD"]',
        '"HOLD_NO_GUESSED_SIDE_EFFECT"',
    )),
})

failed = [name for name, ok in checks.items() if not ok]
result = {
    "schema": "openazrael.kg001.trigger_action_census_validation",
    "version": 142,
    "status": "SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "runtime_status": "CURRENT_SHA_RUNTIME_PENDING",
    "trigger_count": len(ir_rows),
    "class_counts": dict(class_counts),
    "automatic_actions": sorted(active),
    "condition_actions": sorted(conditions),
    "transitions": sorted(transition_set),
    "research_holds": sorted(actual_holds),
    "checks": checks,
    "failed": failed,
    "boundary": (
        "Source validation proves classification and executable code/test paths. "
        "Candidate promotion still requires asset-backed Godot execution at the exact build SHA; "
        "Niamh animation additionally requires the original/restored Conv source clip."
    ),
}
print(json.dumps(result, indent=2))
sys.exit(1 if failed else 0)
