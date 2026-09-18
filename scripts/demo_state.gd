extends Node

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

func retrieve_well_key() -> bool:
    if not can_retrieve_well_key():
        return false
    acquire("well_key")
    # Internal reconstructed node; production FLAGLIST uses R7key for world state.
    set_puzzle_node("R7KeyTake")
    set_flag("R7key")
    return true

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
