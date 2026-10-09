extends SceneTree
# Experimental WORLD-derived transformations; NOT original runtime fidelity.
const Bridge = preload("res://scripts/r7_transform_bridge_v356.gd")
const Guard = preload("res://scripts/r7_action_activation_guard_v360.gd")
var failed: Array[String] = []
var checks := 0
func check(name: String, ok: bool) -> void:
    checks += 1
    if not ok:
        failed.append(name)
func _initialize() -> void:
    call_deferred("_run")
func _run() -> void:
    var room = load("res://assets/rooms/R7.glb").instantiate()
    root.add_child(room)
    var bridge = Bridge.new()
    root.add_child(bridge)
    check("bind_ten_objects", bridge.bind_room(room) and bridge.executor.nodes.size() == 10)
    check("rotation_axis0_Y", bridge.source_axis_component(0x17, 0) == 1)
    check("rotation_axis1_X", bridge.source_axis_component(0x17, 1) == 0)
    check("rotation_axis2_Z", bridge.source_axis_component(0x17, 2) == 2)
    check("translation_axis0_Z", bridge.source_axis_component(0x18, 0) == 2)
    check("translation_axis1_Y", bridge.source_axis_component(0x18, 1) == 1)
    check("translation_axis2_X", bridge.source_axis_component(0x18, 2) == 0)
    check("invalid_axis_rejected", bridge.source_axis_component(0x18, 9) == -1)
    check("invalid_opcode_rejected", bridge.source_axis_component(0x19, 2) == -1)
    for step in range(3):
        check("production_motion_held_" + str(step), not Guard.activation_allowed(step))
    check("invalid_step_rejected", not bridge.queue_experimental_source_step(99))
    if bridge.executor.nodes.size() == 10:
        var pipe: Node3D = bridge.executor.nodes[1145]
        var lever: Node3D = bridge.executor.nodes[98]
        var wheel: Node3D = bridge.executor.nodes[101]
        var pipe_child: Node3D = bridge.executor.nodes[100]
        var pipe_initial: Transform3D = pipe.transform
        var lever_initial: Transform3D = lever.transform
        var wheel_initial: Transform3D = wheel.transform
        var child_initial: Transform3D = pipe_child.transform
        check("first_action_queued", bridge.queue_experimental_source_step(0))
        check("two_pending", bridge.scheduler.pending.size() == 2)
        for i in range(5):
            bridge.tick()
        check("five_ticks", bridge.scheduler.tick_index == 5 and bridge.applied_count == 10)
        check("source_translation_x", is_equal_approx(pipe.position.x, pipe_initial.origin.x + 5.0))
        check("source_rotation_z", lever.transform.is_equal_approx(lever_initial.rotated_local(Vector3(0,0,1),deg_to_rad(-5))))
        var saved = JSON.parse_string(JSON.stringify(bridge.snapshot()))
        check("snapshot_json", saved is Dictionary)
        bridge.flush()
        check("first_flush_empty", bridge.scheduler.pending.is_empty())
        check("fifteen_ticks", bridge.scheduler.tick_index == 15 and bridge.applied_count == 30)
        check("first_final_translation", is_equal_approx(pipe.position.x, pipe_initial.origin.x + 15.0))
        var expected_lever: Transform3D = lever.transform
        check("restore_inflight", bridge.restore_snapshot(saved))
        check("restored_five_ticks", bridge.scheduler.tick_index == 5 and bridge.scheduler.pending.size() == 2)
        check("restored_transform", is_equal_approx(pipe.position.x, pipe_initial.origin.x + 5.0))
        bridge.flush()
        check("same_final_translation", is_equal_approx(pipe.position.x, pipe_initial.origin.x + 15.0))
        check("same_final_rotation", lever.transform.is_equal_approx(expected_lever))
        check("wheel_queued", bridge.queue_experimental_source_step(1))
        bridge.flush()
        check("wheel_rotated_z", wheel.transform.is_equal_approx(wheel_initial.rotated_local(Vector3(0,0,1),deg_to_rad(50))))
        check("child_rotated_z", pipe_child.transform.is_equal_approx(child_initial.rotated_local(Vector3(0,0,1),deg_to_rad(-90))))
        check("reverse_lever_queued", bridge.queue_experimental_source_step(2))
        bridge.flush()
        check("pipe_parent_returns", pipe.transform.is_equal_approx(pipe_initial))
        check("lever_returns", lever.transform.is_equal_approx(lever_initial))
        check("wheel_remains_changed", not wheel.transform.is_equal_approx(wheel_initial))
        check("child_remains_changed", not pipe_child.transform.is_equal_approx(child_initial))
        check("queue_empty", bridge.scheduler.pending.is_empty())
        var before_bad = JSON.stringify(bridge.snapshot())
        check("invalid_restore_rejected", not bridge.restore_snapshot({"version":1, "scheduler":{"version":1, "tick_index":0,"pending":[{"opcode":77,"total":5,"remaining":4}]},"executor":{"version":1, "applied":[]},"applied_count":0}))
        check("bad_restore_atomic", JSON.stringify(bridge.snapshot()) == before_bad)
    bridge.queue_free()
    room.queue_free()
    var result = {"schema":"openazrael.c8.r7_source_axis_replay.v361",
        "status":"PASS" if failed.is_empty() else "FAIL", "checks":checks, "failed":failed,
        "scope":"SOURCE_INSTRUCTION_AXIS_MAPPING_AND_EXPERIMENTAL_GODOT_LOCAL_REPLAY_ONLY",
        "fidelity_status":"HOLD"}
    print("OPENAZRAEL_C8_AXIS_REPLAY_V361 " + JSON.stringify(result))
    quit(0 if failed.is_empty() else 1)