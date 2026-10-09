extends SceneTree
const Bridge = preload("res://scripts/r7_transform_bridge_v356.gd")
var failed: Array[String] = []
var checks := 0
func check(label: String, ok: bool) -> void:
    checks += 1
    if not ok: failed.append(label)
func _initialize() -> void: call_deferred("run_test")
func run_test() -> void:
    var room = load("res://assets/rooms/R7.glb").instantiate()
    root.add_child(room)
    var bridge = Bridge.new()
    root.add_child(bridge)
    check("bind", bridge.bind_room(room))
    check("queue", bridge.queue_action(1145,0x17,1,1.0,5))
    check("queue_move", bridge.queue_action(1148,0x18,0,1.0,10))
    bridge.tick()
    check("tick_count", bridge.applied_count == 2)
    check("queue_remaining", bridge.scheduler.pending.size() == 2)
    var snap = bridge.snapshot()
    bridge.flush()
    check("flushed", bridge.scheduler.pending.is_empty())
    check("applied_total", bridge.applied_count == 15)
    check("restore", bridge.restore_snapshot(snap))
    check("restore_count", bridge.applied_count == 2)
    check("restore_pending", bridge.scheduler.pending.size() == 2)
    check("restore_idempotent", bridge.restore_snapshot(snap) and bridge.applied_count == 2)
    bridge.flush()
    check("replay_total", bridge.applied_count == 15)
    check("replay_empty", bridge.scheduler.pending.is_empty())
    bridge.queue_free()
    room.queue_free()
    var result = {"status":"PASS" if failed.is_empty() else "FAIL","checks":checks,"failed":failed,"scope":"isolated scheduler/executor bridge, no gameplay or original fidelity assertion"}
    print("OPENAZRAEL_C8_BRIDGE_V356 " + JSON.stringify(result))
    quit(0 if failed.is_empty() else 1)