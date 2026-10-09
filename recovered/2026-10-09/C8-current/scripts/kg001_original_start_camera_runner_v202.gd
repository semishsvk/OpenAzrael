extends SceneTree

func _initialize() -> void:
    call_deferred("_run")

func _run() -> void:
    var scene = load("res://main.tscn").instantiate()
    root.add_child(scene)
    await create_timer(3.0).timeout
    var player = scene.get_node("Player") as CharacterBody3D
    var camera = scene.get_node("Player/Camera3D") as Camera3D
    var contract = JSON.parse_string(FileAccess.get_file_as_string("res://data/tests/kg001_original_start_camera_contract_v202.json"))
    var expected := Vector3(float(contract.position[0]), float(contract.position[1]), float(contract.position[2]))
    var observed: Vector3 = camera.global_position
    var checks := {
        "production_room_r1": scene.get_node("RoomManager").current_room_id == "R1",
        "production_start_matches_original": observed.distance_to(expected) <= float(contract.settled_position_tolerance),
        "original_eye_height": is_equal_approx(float(player.eye_height), 45.0) and is_equal_approx(camera.position.y, 45.0),
        "original_forward": (-camera.global_basis.z).dot(Vector3(0, 0, 1)) > 0.999,
        "original_screen_right": camera.global_basis.x.dot(Vector3(1, 0, 0)) > 0.999,
    }
    player.set("pitch", -0.18)
    player.call("apply_camera_pitch", -0.18)
    checks["restored_pitch_preserves_screen_right"] = camera.global_basis.x.dot(Vector3(1, 0, 0)) > 0.999
    checks["restored_pitch_matches_view_direction"] = (-camera.global_basis.z).dot(Vector3(0, sin(-0.18), cos(-0.18))) > 0.999
    player.set("pitch", 0.0)
    player.call("apply_camera_pitch", 0.0)
    var viewport_size := Vector2(root.size)
    var screen_right_ray := camera.project_ray_normal(viewport_size * 0.5 + Vector2(60, 0))
    checks["screen_right_ray_matches_original_x"] = screen_right_ray.x > 0.0
    var body_before: Vector3 = player.global_position
    Input.action_press("move_right")
    for i in range(20):
        await physics_frame
    Input.action_release("move_right")
    checks["right_movement_matches_screen_right"] = player.global_position.x > body_before.x + 0.5
    var motion := InputEventMouseMotion.new()
    motion.relative = Vector2(80, 0)
    player.call("_unhandled_input", motion)
    checks["right_head_look_matches_original_x"] = (-camera.global_basis.z).x > 0.05
    var failed: Array[String] = []
    for key in checks:
        if not checks[key]:
            failed.append(String(key))
    var result := {"schema":"openazrael.kg001.original_start_camera_runtime", "version":202, "status":"PASS" if failed.is_empty() else "FAIL", "checks":checks, "failed":failed, "observed_start":[observed.x,observed.y,observed.z], "source_start":contract.position, "camera_pose_injected_for_start_test":false, "scope":"source startup pose and controls; graphical fidelity remains separate"}
    var file := FileAccess.open("res://.tmp/kg001_c6_final_audit/original_start_camera_runtime_v202.json", FileAccess.WRITE)
    file.store_string(JSON.stringify(result, "  "))
    print("ORIGINAL_START_CAMERA_V202 ", JSON.stringify(result))
    scene.queue_free()
    quit(0 if failed.is_empty() else 1)
