extends Node
const R7SnapshotValidator = preload("res://scripts/r7_snapshot_validator_v367.gd")

signal inventory_changed
signal flag_changed(flag: String, value: bool)
signal puzzle_node_changed(node_name: String, value: bool)

var inventory: Dictionary = {}
# Confirmed/persistent source-style flags where known (e.g. retail FLAGLIST.DAT).
var flags: Dictionary = {}
# Transient puzzle/event/object node states recovered from PUZZLES.DAT/OBJECTS.DAT.
# Keeping these separate avoids pretending every puzzle-node name was a persistent flag.
var puzzle_nodes: Dictionary = {}
var values: Dictionary = {}

func acquire(item_id: String) -> void:
    inventory[item_id] = true
    inventory_changed.emit()
    print("OpenAzrael acquired: ", item_id)

func remove(item_id: String) -> void:
    if inventory.erase(item_id):
        inventory_changed.emit()

func has(item_id: String) -> bool:
    return inventory.has(item_id)

func set_flag(flag: String, value: bool = true) -> void:
    flags[flag] = value
    flag_changed.emit(flag, value)
    print("OpenAzrael flag: ", flag, " = ", value)

func flag(flag: String) -> bool:
    return bool(flags.get(flag, false))

func set_puzzle_node(node_name: String, value: bool = true) -> void:
    puzzle_nodes[node_name] = value
    puzzle_node_changed.emit(node_name, value)
    print("OpenAzrael puzzle node: ", node_name, " = ", value)

func puzzle_node(node_name: String) -> bool:
    return bool(puzzle_nodes.get(node_name, false))

func set_value(key: String, value) -> void:
    values[key] = value

func value(key: String, default_value = null):
    return values.get(key, default_value)

func can_retrieve_well_key() -> bool:
    return has("rusty_tongs")

func complete_well_key_take() -> bool:
    if has("well_key"):
        return false
    acquire("well_key")
    # Internal reconstructed node; production FLAGLIST uses R7key for world state.
    set_puzzle_node("R7KeyTake")
    set_flag("R7key")
    return true

func retrieve_well_key() -> bool:
    if not can_retrieve_well_key():
        return false
    # Official demo opcode 0x09 consumes TONG6 before the default key TAKE.
    remove("rusty_tongs")
    return complete_well_key_take()

func can_unlock_demo_door() -> bool:
    return has("well_key")

func unlock_demo_door() -> bool:
    if not can_unlock_demo_door():
        return false
    set_flag("FR1DoorUnlocked")
    set_flag("R1Door2Open")
    return true

func reset_water_switchboard() -> void:
    set_value("R7SwitchStep", 0)

func switchboard_step(control_id: String) -> String:
    # README solution: right-most lever, lower-right wheel, right-most lever.
    var expected := ["well_lev02", "well_weel3", "well_lev02"]
    var step := int(value("R7SwitchStep", 0))
    if flag("R8BathDrain"):
        return "already_solved"
    if control_id == expected[step]:
        step += 1
        set_value("R7SwitchStep", step)
        if step >= expected.size():
            LegacyEvents.run("R7_WATER_SWITCHBOARD_SOLVED")
            return "solved"
        return "correct"
    set_value("R7SwitchStep", 0)
    return "reset"

func complete_demo() -> void:
    set_puzzle_node("R8TakeShield")
    set_flag("demo_complete")


# v108 KG-001 canonical persistent state identity.
# Use sorted key/value pairs rather than Dictionary insertion order.
func _canonical_pairs(source: Dictionary) -> Array:
    var keys: Array = source.keys()
    keys.sort()
    var out: Array = []
    for key in keys:
        out.append([String(key), source[key]])
    return out

func canonical_state_payload() -> Array:
    return [
        1,
        _canonical_pairs(inventory),
        _canonical_pairs(flags),
        _canonical_pairs(puzzle_nodes),
        _canonical_pairs(values)
    ]

func canonical_state_json() -> String:
    return JSON.stringify(canonical_state_payload())

func canonical_state_hash() -> String:
    var context := HashingContext.new()
    context.start(HashingContext.HASH_SHA256)
    context.update(canonical_state_json().to_utf8_buffer())
    return context.finish().hex_encode()


# v109 KG-001 save/load support for persistent DemoState.
func _dictionary_from_pairs(pairs):
    if not pairs is Array:
        return null
    var out: Dictionary = {}
    for pair in pairs:
        if not pair is Array or pair.size() != 2:
            return null
        out[String(pair[0])] = pair[1]
    return out

func reset_all() -> void:
    inventory.clear()
    flags.clear()
    puzzle_nodes.clear()
    values.clear()
    inventory_changed.emit()

func restore_canonical_state_payload(payload: Array) -> bool:
    if payload.size() != 5 or int(payload[0]) != 1:
        return false
    var restored_inventory = _dictionary_from_pairs(payload[1])
    var restored_flags = _dictionary_from_pairs(payload[2])
    var restored_puzzle_nodes = _dictionary_from_pairs(payload[3])
    var restored_values = _dictionary_from_pairs(payload[4])
    if restored_inventory == null or restored_flags == null or restored_puzzle_nodes == null or restored_values == null:
        return false
    if restored_values.has(R7SnapshotValidator.KEY):
        if not R7SnapshotValidator.valid(restored_values[R7SnapshotValidator.KEY]):
            return false
    inventory = restored_inventory
    flags = restored_flags
    puzzle_nodes = restored_puzzle_nodes
    values = restored_values
    inventory_changed.emit()
    for key in flags.keys():
        flag_changed.emit(String(key), bool(flags[key]))
    for key in puzzle_nodes.keys():
        puzzle_node_changed.emit(String(key), bool(puzzle_nodes[key]))
    return true
