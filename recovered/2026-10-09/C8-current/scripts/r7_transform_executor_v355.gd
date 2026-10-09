extends Node
# Experimental R7 transform executor: source-bound targets, coordinate fidelity HOLD.
const SOURCE_OBJECTS := {
    98: "well_lev02", 99: "well_weel2", 100: "well_pzpi1",
    101: "well_weel3", 222: "well_lev01", 223: "well_weel4",
    224: "well_pzpi2", 225: "well_weel1",
    1145: "well_pzpa1", 1148: "well_pzpa2"
}
var nodes: Dictionary = {}
var baselines: Dictionary = {}
var applied: Array[Dictionary] = []
func _find_named(root_node: Node, wanted: String) -> Node3D:
    if root_node is Node3D and String(root_node.name) == wanted:
        return root_node
    for child in root_node.get_children():
        var found := _find_named(child, wanted)
        if found != null:
            return found
    return null
func bind_room(room: Node) -> bool:
    var resolved: Dictionary = {}
    var original: Dictionary = {}
    for id in SOURCE_OBJECTS:
        var node := _find_named(room, SOURCE_OBJECTS[id])
        if node == null:
            return false
        resolved[id] = node
        original[id] = node.transform
    nodes = resolved
    baselines = original
    applied.clear()
    return true
func apply_step(action: Dictionary) -> bool:
    var id := int(action.get("target_id", -1))
    var opcode := int(action.get("opcode", -1))
    var axis_index := int(action.get("axis", -1))
    if not nodes.has(id) or axis_index < 0 or axis_index > 2:
        return false
    if not opcode in [0x17, 0x18]:
        return false
    var axis := Vector3.ZERO
    axis[axis_index] = 1.0
    var value := float(action.get("amount", 0.0))
    var node: Node3D = nodes[id]
    if opcode == 0x17:
        node.transform = node.transform.rotated_local(axis, deg_to_rad(value))
    else:
        node.position += axis * value
    applied.append(action.duplicate(true))
    return true
func reset_baseline() -> void:
    for id in baselines:
        if is_instance_valid(nodes.get(id)):
            nodes[id].transform = baselines[id]
    applied.clear()
func snapshot() -> Dictionary:
    return {"version":1, "applied":applied.duplicate(true)}
func replay_snapshot(payload: Dictionary) -> bool:
    if int(payload.get("version", -1)) != 1 or not payload.get("applied") is Array:
        return false
    for action in payload["applied"]:
        if not action is Dictionary:
            return false
        if not nodes.has(int(action.get("target_id", -1))) or not int(action.get("opcode", -1)) in [0x17,0x18] or int(action.get("axis", -1)) < 0 or int(action.get("axis", -1)) > 2:
            return false
    reset_baseline()
    for action in payload["applied"]:
        if not apply_step(action):
            return false
    return true