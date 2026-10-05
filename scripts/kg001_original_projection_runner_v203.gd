extends SceneTree

func _initialize() -> void:
    call_deferred("_run")

func _run() -> void:
    var scene = load("res://main.tscn").instantiate()
    root.add_child(scene)
    await create_timer(3.0).timeout
    var camera: Camera3D = scene.get_node("Player/Camera3D") as Camera3D
    var probe = scene.get_node("Player/Camera3D/InteractionProbe")
    var contract = JSON.parse_string(FileAccess.get_file_as_string("res://data/tests/kg001_original_projection_contract_v203.json"))
    var scale_factor := minf(float(root.size.x) / float(contract.logical_canvas[0]), float(root.size.y) / float(contract.logical_canvas[1]))
    var expected_center := Vector2(float(root.size.x) * 0.5, float(root.size.y) * 0.5 + (float(contract.projection_center[1]) - 240.0) * scale_factor)
    var forward: Vector3 = -camera.global_basis.z
    var point: Vector3 = camera.global_position + forward * 100.0
    var rendered_center := camera.unproject_position(point)
    var rendered_right := camera.unproject_position(point + Vector3.RIGHT)
    var rendered_up := camera.unproject_position(point + Vector3.UP)
    var center_ray: Vector3 = probe.call("project_view_direction", expected_center)
    var cursor_ray: Vector3 = probe.call("project_view_direction", Vector2(root.size) * 0.5)
    var right_ray: Vector3 = probe.call("project_view_direction", expected_center + Vector2(60, 0))
    var pixels_per_unit := float(contract.focal_pixels) * scale_factor / 100.0
    var checks := {
        "production_frustum_enabled": camera.projection == Camera3D.PROJECTION_FRUSTUM,
        "source_near_plane": is_equal_approx(camera.near, float(contract.near)),
        "source_far_plane": is_equal_approx(camera.far, float(contract.far)),
        "source_projection_center": rendered_center.distance_to(expected_center) < 0.01,
        "source_horizontal_focal_scale": absf(rendered_right.x - rendered_center.x - pixels_per_unit) < 0.01,
        "source_vertical_focal_scale": absf(rendered_center.y - rendered_up.y - pixels_per_unit) < 0.01,
        "projection_center_ray_matches_forward": center_ray.dot(forward) > 0.99999,
        "cursor_center_uses_off_axis_ray": cursor_ray.y < -0.1,
        "source_screen_right_ray": right_ray.x > 0.0,
    }
    var textured_surfaces := 0
    var nearest_sampling := true
    var sampling_failures: Array[String] = []
    for node in scene.get_node("RoomManager").find_children("*", "MeshInstance3D", true, false):
        var mesh_node := node as MeshInstance3D
        if mesh_node.mesh == null: continue
        for surface in range(mesh_node.mesh.get_surface_count()):
            var material = mesh_node.get_active_material(surface)
            if material is BaseMaterial3D and material.albedo_texture != null:
                textured_surfaces += 1
                if material.texture_filter != BaseMaterial3D.TEXTURE_FILTER_NEAREST:
                    sampling_failures.append(str(mesh_node.get_path()) + ":filter=" + str(material.texture_filter))
                nearest_sampling = nearest_sampling and material.texture_filter == BaseMaterial3D.TEXTURE_FILTER_NEAREST
    checks["source_indexed_texture_sampling"] = textured_surfaces > 0 and nearest_sampling
    var failed: Array[String] = []
    for key in checks:
        if not checks[key]: failed.append(String(key))
    var result := {"schema":"openazrael.kg001.original_projection_runtime", "version":203, "status":"PASS" if failed.is_empty() else "FAIL", "checks":checks, "failed":failed, "rendered_center":[rendered_center.x,rendered_center.y], "expected_center":[expected_center.x,expected_center.y], "cursor_center_ray":[cursor_ray.x,cursor_ray.y,cursor_ray.z], "no_camera_pose_injection":true, "scope":"source projection and interaction ray; photometric fidelity remains separate", "sampling_failures":sampling_failures, "textured_surfaces":textured_surfaces}
    var file := FileAccess.open("res://.tmp/kg001_c6_final_audit/original_projection_runtime_v203.json", FileAccess.WRITE)
    file.store_string(JSON.stringify(result, "  "))
    print("ORIGINAL_PROJECTION_V203 ", JSON.stringify(result))
    scene.queue_free()
    quit(0 if failed.is_empty() else 1)
