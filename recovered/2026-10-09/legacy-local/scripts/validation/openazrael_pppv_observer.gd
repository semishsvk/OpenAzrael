extends RefCounted
class_name OpenAzraelPPPVObserver

var evidence: PPPVEvidenceBus
var state: Node
var legacy_events: Node
var diagnostics: Node

var _inventory_snapshot: Dictionary = {}
var _flags_snapshot: Dictionary = {}
var _puzzle_snapshot: Dictionary = {}

func _init(
    evidence_bus: PPPVEvidenceBus,
    demo_state: Node,
    legacy_event_runner: Node,
    candidate_diagnostics: Node = null
) -> void:
    evidence = evidence_bus
    state = demo_state
    legacy_events = legacy_event_runner
    diagnostics = candidate_diagnostics

func _state_dict(property_name: String) -> Dictionary:
    var value = state.get(property_name)
    return value.duplicate(true) if value is Dictionary else {}

func _connect_once(source: Object, signal_name: String, callback: Callable) -> void:
    if source == null or not source.has_signal(signal_name):
        return
    if not source.is_connected(signal_name, callback):
        source.connect(signal_name, callback)

func attach() -> void:
    _inventory_snapshot = _state_dict("inventory")
    _flags_snapshot = _state_dict("flags")
    _puzzle_snapshot = _state_dict("puzzle_nodes")

    _connect_once(state, "inventory_changed", Callable(self, "_on_inventory_changed"))
    _connect_once(state, "flag_changed", Callable(self, "_on_flag_changed"))
    _connect_once(
        state,
        "puzzle_node_changed",
        Callable(self, "_on_puzzle_node_changed")
    )
    _connect_once(
        legacy_events,
        "logical_audio_event",
        Callable(self, "_on_logical_audio")
    )
    _connect_once(
        diagnostics,
        "event_recorded",
        Callable(self, "_on_candidate_event")
    )

func attach_interaction(interaction: Node) -> void:
    if interaction == null:
        return
    _connect_once(
        interaction,
        "demo_action_step",
        Callable(self, "_on_demo_action_step")
    )

func snapshot_state(
    inventory_keys: Array[String] = [],
    flag_keys: Array[String] = [],
    puzzle_keys: Array[String] = []
) -> Dictionary:
    var current_inventory := _state_dict("inventory")
    var current_flags := _state_dict("flags")
    var current_puzzle := _state_dict("puzzle_nodes")

    var inventory: Dictionary = {}
    var flags: Dictionary = {}
    var puzzle: Dictionary = {}

    var inventory_all: Array = current_inventory.keys()
    for key in inventory_keys:
        if not inventory_all.has(key):
            inventory_all.append(key)
    inventory_all.sort()
    for raw_key in inventory_all:
        var key := String(raw_key)
        inventory[key] = bool(state.call("has", key))

    var flag_all: Array = current_flags.keys()
    for key in flag_keys:
        if not flag_all.has(key):
            flag_all.append(key)
    flag_all.sort()
    for raw_key in flag_all:
        var key := String(raw_key)
        flags[key] = bool(state.call("flag", key))

    var puzzle_all: Array = current_puzzle.keys()
    for key in puzzle_keys:
        if not puzzle_all.has(key):
            puzzle_all.append(key)
    puzzle_all.sort()
    for raw_key in puzzle_all:
        var key := String(raw_key)
        puzzle[key] = bool(state.call("puzzle_node", key))

    return {
        "inventory": inventory,
        "flags": flags,
        "puzzle": puzzle,
        "values": _state_dict("values")
    }

func _on_inventory_changed() -> void:
    var current := _state_dict("inventory")
    var keys: Array = _inventory_snapshot.keys()
    for key in current.keys():
        if not keys.has(key):
            keys.append(key)
    keys.sort()

    for raw_key in keys:
        var key := String(raw_key)
        var before := _inventory_snapshot.has(key)
        var after := current.has(key)
        if before != after:
            evidence.record("state_change", {
                "path": "inventory." + key,
                "before": before,
                "after": after
            })
    _inventory_snapshot = current

func _on_flag_changed(flag: String, value: bool) -> void:
    var before := bool(_flags_snapshot.get(flag, false))
    evidence.record("state_change", {
        "path": "flags." + flag,
        "before": before,
        "after": value
    })
    _flags_snapshot[flag] = value

func _on_puzzle_node_changed(node_name: String, value: bool) -> void:
    var before := bool(_puzzle_snapshot.get(node_name, false))
    evidence.record("state_change", {
        "path": "puzzle." + node_name,
        "before": before,
        "after": value
    })
    _puzzle_snapshot[node_name] = value

func _on_logical_audio(filename: String) -> void:
    evidence.record_audio(filename)

func _on_demo_action_step(step: String) -> void:
    evidence.record_demo_action_step(step)

func _on_candidate_event(entry: Dictionary) -> void:
    var kind := String(entry.get("kind", ""))
    var data = entry.get("data", {})
    if not data is Dictionary:
        data = {}

    match kind:
        "interaction":
            evidence.record("trigger", {
                "target": String(data.get("target", "")),
                "activated": true,
                "mechanism": "interaction_dispatch"
            })
        "trigger_enter":
            evidence.record("trigger", {
                "room": String(data.get("room", "")),
                "target": String(data.get("trigger", "")),
                "activated": true,
                "edge": "ENTER",
                "mechanism": "world_trigger"
            })
        "trigger_exit":
            evidence.record("trigger", {
                "room": String(data.get("room", "")),
                "target": String(data.get("trigger", "")),
                "activated": false,
                "edge": "EXIT",
                "mechanism": "world_trigger"
            })
        "room_transition":
            evidence.record("room_transition", data.duplicate(true))
        "character_animation_request":
            evidence.record("character_animation_request", data.duplicate(true))
        "conversation_request":
            evidence.record("conversation_request", data.duplicate(true))
