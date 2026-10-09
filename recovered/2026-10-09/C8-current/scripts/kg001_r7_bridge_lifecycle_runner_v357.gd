extends SceneTree
var failed: Array[String] = []
var checks := 0
func check(label: String, ok: bool) -> void:
    checks += 1
    if not ok: failed.append(label)
func _initialize() -> void: call_deferred("run_test")
func run_test() -> void:
    var scene = load("res://main.tscn").instantiate()
    root.add_child(scene)
    for i in range(3): await process_frame
    var manager = scene.get_node("RoomManager")
    manager.load_room("R7",false)
    for i in range(3): await process_frame
    var bridge = manager.current_room.get_node_or_null("R7TransformBridge")
    check("bridge_present",bridge != null)
    if bridge != null:
        check("ten_bound",bridge.executor.nodes.size() == 10)
        check("initial_queue_empty",bridge.scheduler.pending.is_empty())
        check("initial_no_transform",bridge.applied_count == 0)
    manager.load_room("R1",false)
    for i in range(3): await process_frame
    check("returned_R1",manager.current_room_id == "R1")
    manager.load_room("R7",false)
    for i in range(3): await process_frame
    var again = manager.current_room.get_node_or_null("R7TransformBridge")
    check("bridge_recreated",again != null)
    if again != null:
        check("rebound_ten",again.executor.nodes.size() == 10)
        check("reload_empty_queue",again.scheduler.pending.is_empty())
    scene.queue_free()
    for i in range(3): await process_frame
    var result = {"status":"PASS" if failed.is_empty() else "FAIL","checks":checks,"failed":failed,"scope":"production R7 passive bridge lifecycle, not original transform fidelity"}
    print("OPENAZRAEL_C8_R7_BRIDGE_V357 " + JSON.stringify(result))
    quit(0 if failed.is_empty() else 1)