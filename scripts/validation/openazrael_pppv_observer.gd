extends RefCounted
class_name OpenAzraelPPPVObserver

var evidence: PPPVEvidenceBus
var state: Node
var legacy_events: Node

var _inventory_snapshot: Dictionary = {}
var _flags_snapshot: Dictionary = {}
var _puzzle_snapshot: Dictionary = {}

func _init(
    evidence_bus: PPPVEvidenceBus,
    demo_state: Node,
    legacy_event_runner: Node
) -> void:
    evidence = evidence_bus
    state = demo_state
    legacy_events = legacy_event_runner

func attach() -> void:
    _inventory_snapshot = state.inventory.duplicate(true)
    _flags_snapshot = state.flags.duplicate(true)
    _puzzle_snapshot = state.puzzle_nodes.duplicate(true)

    if not state.inventory_changed.is_connected(_on_inventory_changed):
        state.inventory_changed.connect(_on_inventory_changed)
    if not state.flag_changed.is_connected(_on_flag_changed):
        state.flag_changed.connect(_on_flag_changed)
    if not state.puzzle_node_changed.is_connected(_on_puzzle_node_changed):
        state.puzzle_node_changed.connect(_on_puzzle_node_changed)
    if (
        legacy_events != null
        and legacy_events.has_signal("logical_audio_event")
        and not legacy_events.logical_audio_event.is_connected(_on_logical_audio)
    ):
        legacy_events.logical_audio_event.connect(_on_logical_audio)

func attach_interaction(interaction: Node) -> void:
    if interaction == null:
        return
    if interaction.has_signal("demo_action_step"):
        var callable := Callable(self, "_on_demo_action_step")
        if not interaction.is_connected("demo_action_step", callable):
            interaction.connect("demo_action_step", callable)

func snapshot_state(
    inventory_keys: Array[String] = [],
    flag_keys: Array[String] = [],
    puzzle_keys: Array[String] = []
) -> Dictionary:
    var inventory: Dictionary = {}
    var flags: Dictionary = {}
    var puzzle: Dictionary = {}

    var inventory_all: Array = state.inventory.keys()
    for key in inventory_keys:
        if not inventory_all.has(key):
            inventory_all.append(key)
    inventory_all.sort()
    for key in inventory_all:
        inventory[String(key)] = state.has(String(key))

    var flag_all: Array = state.flags.keys()
    for key in flag_keys:
        if not flag_all.has(key):
            flag_all.append(key)
    flag_all.sort()
    for key in flag_all:
        flags[String(key)] = state.flag(String(key))

    var puzzle_all: Array = state.puzzle_nodes.keys()
    for key in puzzle_keys:
        if not puzzle_all.has(key):
            puzzle_all.append(key)
    puzzle_all.sort()
    for key in puzzle_all:
        puzzle[String(key)] = state.puzzle_node(String(key))

    return {
        "inventory": inventory,
        "flags": flags,
        "puzzle": puzzle,
        "values": state.values.duplicate(true)
    }

func _on_inventory_changed() -> void:
    var keys: Array = _inventory_snapshot.keys()
    for key in state.inventory.keys():
        if not keys.has(key):
            keys.append(key)
    keys.sort()

    for raw_key in keys:
        var key := String(raw_key)
        var before := _inventory_snapshot.has(key)
        var after := state.has(key)
        if before != after:
            evidence.record("state_change", {
                "path": "inventory." + key,
                "before": before,
                "after": after
            })
    _inventory_snapshot = state.inventory.duplicate(true)

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
