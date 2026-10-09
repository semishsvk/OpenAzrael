extends SceneTree
# C8 R7 restoration contract. Does not claim original runtime animation fidelity.
const NAMES := ["well_pzpa1", "well_pzpa2", "well_pzpi1", "well_pzpi2"]
var failures: Array[String] = []
var checks := 0
func check(label: String, ok: bool) -> void:
    checks += 1
    if not ok:
        failures.append(label)
func find_node_recursive(n: Node, wanted: String) -> Node3D:
    if n.name == wanted and n is Node3D:
        return n
    for child in n.get_children():
        var found := find_node_recursive(child, wanted)
        if found != null:
            return found
    return null
func settle() -> void:
    for i in range(3):
        await process_frame
func _initialize() -> void:
    call_deferred("run_test")
func run_test() -> void:
    var state = root.get_node("DemoState")
    var packed = load("res://main.tscn")
    check("main_scene", packed is PackedScene)
    if not packed is PackedScene:
        finish()
        return
    var scene = packed.instantiate()
    root.add_child(scene)
    await settle()
    var manager = scene.get_node("RoomManager")
    state.reset_all()
    manager.load_room("R7", false)
    await settle()
    var initial: Dictionary = {}
    for name in NAMES:
        var node := find_node_recursive(manager.current_room, name)
        check("exists_" + name, node != null)
        if node != null:
            initial[name] = node.transform
    var a = find_node_recursive(manager.current_room, "well_pzpi1")
    var b = find_node_recursive(manager.current_room, "well_pzpi2")
    check("parent1", a != null and a.get_parent().name == "well_pzpa1")
    check("parent2", b != null and b.get_parent().name == "well_pzpa2")
    var payload: Array = state.canonical_state_payload().duplicate(true)
    check("restore", state.restore_canonical_state_payload(payload))
    manager.load_room("R7", false)
    await settle()
    for name in NAMES:
        var node := find_node_recursive(manager.current_room, name)
        check("reload_exists_" + name, node != null)
        if node != null and initial.has(name):
            check("reload_transform_" + name, node.transform.is_equal_approx(initial[name]))
    scene.queue_free()
    await settle()
    finish()
func finish() -> void:
    var result = {"schema":"openazrael.c8.r7_restore_baseline","status":"PASS" if failures.is_empty() else "FAIL","checks":checks,"failed":failures,"scope":"R7 static hierarchy and idempotent room reload, not dynamic animation fidelity"}
    print("OPENAZRAEL_C8_R7_BASELINE " + JSON.stringify(result))
    quit(0 if failures.is_empty() else 1)