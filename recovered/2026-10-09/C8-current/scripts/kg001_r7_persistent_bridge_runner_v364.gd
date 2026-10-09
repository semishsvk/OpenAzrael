extends SceneTree
# Production room lifecycle + existing DemoState canonical save round-trip.
# Only experimental source motion is injected; trigger and fidelity remain HOLD.
var failures: Array[String] = []
var checks := 0
const KEY := "R7SourceTransformSnapshotV364"
func check(label: String, ok: bool) -> void:
    checks += 1
    if not ok:
        failures.append(label)
func _settle() -> void:
    for i in range(3):
        await process_frame
func _initialize() -> void:
    call_deferred("_run")
func _run() -> void:
    var state = root.get_node("DemoState")
    var scene = load("res://main.tscn").instantiate()
    root.add_child(scene)
    await _settle()
    var manager = scene.get_node("RoomManager")
    state.reset_all()
    manager.load_room("R7",false)
    await _settle()
    var bridge = manager.current_room.get_node_or_null("R7TransformBridge")
    check("bridge_present",bridge != null)
    if bridge == null:
        _finish(scene)
        return
    check("empty_passive_load_has_no_snapshot",state.value(KEY,null) == null)
    check("enqueue_experimental",bridge.queue_experimental_source_step(0))
    for i in range(5):
        bridge.tick()
    var original_parent: Node3D = bridge.executor.nodes[1145]
    var snapshot_position := original_parent.transform
    check("five_ticks",bridge.scheduler.tick_index == 5)
    check("saved_snapshot_exists",state.value(KEY,null) is Dictionary)
    check("saved_snapshot_pending",state.value(KEY,{}).get("scheduler",{}).get("pending",[]).size() == 2)
    var saved_payload: Array = state.canonical_state_payload().duplicate(true)
    var saved_hash: String = state.canonical_state_hash()
    var serialized = JSON.stringify(saved_payload)
    check("serialized_roundtrip",JSON.parse_string(serialized) is Array)
    manager.load_room("R1",false)
    await _settle()
    state.reset_all()
    check("reset_clears_snapshot",state.value(KEY,null) == null)
    check("restore_demo_state",state.restore_canonical_state_payload(saved_payload))
    check("restore_state_hash",state.canonical_state_hash() == saved_hash)
    manager.load_room("R7",false)
    await _settle()
    var again = manager.current_room.get_node_or_null("R7TransformBridge")
    check("bridge_recreated",again != null)
    if again != null:
        check("restored_tick",again.scheduler.tick_index == 5)
        check("restored_pending",again.scheduler.pending.size() == 2)
        check("restored_applied_count",again.applied_count == 10)
        check("restored_transform",again.executor.nodes[1145].transform.is_equal_approx(snapshot_position))
        check("reload_does_not_change_save_hash",state.canonical_state_hash() == saved_hash)
        again.flush()
        check("completion_empty_queue",again.scheduler.pending.is_empty())
        var finished_transform: Transform3D = again.executor.nodes[1145].transform
        manager.load_room("R7",false)
        await _settle()
        var third = manager.current_room.get_node_or_null("R7TransformBridge")
        check("finished_state_reloads",third != null)
        if third != null:
            check("no_double_transform",third.executor.nodes[1145].transform.is_equal_approx(finished_transform))
            check("finished_queue_empty",third.scheduler.pending.is_empty())
    check("no_real_switchboard_solved",not state.flag("R8BathDrain"))
    check("no_real_switch_step_advanced",int(state.value("R7SwitchStep",0)) == 0)
    state.reset_all()
    _finish(scene)
func _finish(scene: Node) -> void:
    scene.queue_free()
    await _settle()
    var out = {
        "schema":"openazrael.c8.r7_persistent_bridge.v364",
        "status":"PASS" if failures.is_empty() else "FAIL",
        "checks":checks,"failed":failures,
        "fidelity_status":"HOLD",
        "scope":"experimental R7 transform queue stored in production DemoState, idempotent room restoration; source triggers remain disabled"
    }
    print("OPENAZRAEL_C8_R7_PERSIST_V364 " + JSON.stringify(out))
    quit(0 if failures.is_empty() else 1)