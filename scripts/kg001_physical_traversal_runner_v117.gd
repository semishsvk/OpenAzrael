extends SceneTree

const REQUIRED_ROOMS := [
    "res://assets/rooms/R1.glb",
    "res://assets/rooms/R7.glb",
    "res://assets/rooms/R8.glb"
]

var failures: Array[String] = []
var check_count := 0

func _initialize() -> void:
    call_deferred("_run")

func _check(name: String, condition: bool) -> void:
    check_count += 1
    if not condition:
        failures.append(name)

func _settle(frames: int = 3) -> void:
    for _i in range(frames):
        await process_frame

func _settle_physics(frames: int = 3) -> void:
    for _i in range(frames):
        await physics_frame

func _release_move_actions() -> void:
    for action in ["move_forward", "move_back", "move_left", "move_right"]:
        Input.action_release(action)

func _horizontal_distance(a: Vector3, b: Vector3) -> float:
    return Vector2(a.x - b.x, a.z - b.z).length()

func _floor_probe(scene: Node3D, player: CharacterBody3D) -> Dictionary:
    await _settle_physics(2)
    var origin := player.global_position
    var query := PhysicsRayQueryParameters3D.create(
        origin + Vector3.UP,
        origin + Vector3.DOWN * 1000.0,
        1
    )
    query.exclude = [player.get_rid()]
    return scene.get_world_3d().direct_space_state.intersect_ray(query)

func _exercise_input_walk(
    player: CharacterBody3D,
    action: StringName,
    frames: int,
    reference_floor_y: float
) -> Dictionary:
    _release_move_actions()
    var start := player.global_position
    var min_y := start.y
    var on_floor_frames := 0
    Input.action_press(action, 1.0)
    for _i in range(frames):
        await physics_frame
        min_y = minf(min_y, player.global_position.y)
        if player.is_on_floor():
            on_floor_frames += 1
    Input.action_release(action)
    await physics_frame
    return {
        "distance": _horizontal_distance(start, player.global_position),
        "min_y": min_y,
        "floor_contact_ratio": float(on_floor_frames) / float(maxi(frames, 1)),
        "fell_through": min_y < reference_floor_y - 4.0
    }

func _find_named(node: Node, wanted: String) -> Node:
    if String(node.name) == wanted:
        return node
    for child in node.get_children():
        var found := _find_named(child, wanted)
        if found != null:
            return found
    return null

func _stair_tread_levels(mesh_instance: MeshInstance3D) -> Array[Dictionary]:
    var groups: Array[Dictionary] = []
    if mesh_instance.mesh == null:
        return groups

    for surface in range(mesh_instance.mesh.get_surface_count()):
        var arrays := mesh_instance.mesh.surface_get_arrays(surface)
        var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
        var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
        var triangle_count := int(indices.size() / 3) if not indices.is_empty() else int(vertices.size() / 3)

        for tri in range(triangle_count):
            var ia := indices[tri * 3] if not indices.is_empty() else tri * 3
            var ib := indices[tri * 3 + 1] if not indices.is_empty() else tri * 3 + 1
            var ic := indices[tri * 3 + 2] if not indices.is_empty() else tri * 3 + 2
            var a := mesh_instance.global_transform * vertices[ia]
            var b := mesh_instance.global_transform * vertices[ib]
            var c := mesh_instance.global_transform * vertices[ic]
            var cross := (b - a).cross(c - a)
            var area := cross.length() * 0.5
            if area <= 0.001:
                continue

            # Issue #6 proved source winding is not a safe semantic oracle.
            # Treat either horizontal winding as a tread candidate.
            var normal := cross.normalized()
            if absf(normal.y) < 0.75:
                continue

            var centroid := (a + b + c) / 3.0
            var group_index := -1
            for i in range(groups.size()):
                if absf(float(groups[i]["y"]) - centroid.y) <= 0.35:
                    group_index = i
                    break

            if group_index < 0:
                groups.append({
                    "y": centroid.y,
                    "area": area,
                    "weighted_center": centroid * area
                })
            else:
                groups[group_index]["area"] = float(groups[group_index]["area"]) + area
                groups[group_index]["weighted_center"] = (
                    groups[group_index]["weighted_center"] + centroid * area
                )

    for group in groups:
        group["center"] = group["weighted_center"] / float(group["area"])
    groups.sort_custom(
        func(a: Dictionary, b: Dictionary) -> bool:
            return float(a["y"]) < float(b["y"])
    )

    # step011 contains a broad structural underside below the actual treads.
    # Reject it by area, not by triangle winding.
    if groups.size() >= 5:
        var largest_area := -1.0
        var largest_index := -1
        for i in range(groups.size()):
            if float(groups[i]["area"]) > largest_area:
                largest_area = float(groups[i]["area"])
                largest_index = i
        if largest_index == 0:
            groups.remove_at(0)
    return groups

func _walk_toward_progress(
    player: CharacterBody3D,
    direction: Vector3,
    target_progress: float,
    max_frames: int,
    lower_bound_y: float
) -> Dictionary:
    var flat := Vector3(direction.x, 0.0, direction.z).normalized()
    if flat.length_squared() < 0.001:
        return {
            "progress": 0.0,
            "min_y": player.global_position.y,
            "max_y": player.global_position.y,
            "floor_contact_ratio": 0.0
        }

    player.rotation.y = atan2(-flat.x, -flat.z)
    player.velocity = Vector3.ZERO
    _release_move_actions()
    var start := player.global_position
    var min_y := start.y
    var max_y := start.y
    var on_floor_frames := 0
    var used_frames := 0

    Input.action_press("move_forward", 1.0)
    for i in range(max_frames):
        await physics_frame
        used_frames = i + 1
        min_y = minf(min_y, player.global_position.y)
        max_y = maxf(max_y, player.global_position.y)
        if player.is_on_floor():
            on_floor_frames += 1

        var delta := player.global_position - start
        var progress := Vector3(delta.x, 0.0, delta.z).dot(flat)
        if progress >= target_progress:
            break
        if min_y < lower_bound_y:
            break

    Input.action_release("move_forward")
    await physics_frame
    var moved := player.global_position - start
    return {
        "progress": Vector3(moved.x, 0.0, moved.z).dot(flat),
        "min_y": min_y,
        "max_y": max_y,
        "floor_contact_ratio": float(on_floor_frames) / float(maxi(used_frames, 1))
    }

func _exercise_r1_floor(scene: Node3D, manager, player: CharacterBody3D) -> void:
    manager.transition_cooldown = 999.0
    manager.load_room("R1", false)
    await _settle(2)
    manager.call("_spawn_at_portal", "R1", "spaview")
    await _settle_physics(2)

    var floor_hit: Dictionary = await _floor_probe(scene, player)
    _check("R1_floor_probe_hit", not floor_hit.is_empty())
    if floor_hit.is_empty():
        return

    var floor_y := float((floor_hit["position"] as Vector3).y)
    player.global_position = Vector3(
        player.global_position.x,
        floor_y + 4.0,
        player.global_position.z
    )
    player.velocity = Vector3.ZERO
    await _settle_physics(30)
    _check("R1_initial_floor_contact", player.is_on_floor())
    _check("R1_initial_floor_height", absf(player.global_position.y - floor_y) < 2.0)

    # Preserve the canonical portal heading and exercise the same Input actions
    # used during manual gameplay. No teleport occurs while either walk runs.
    var origin := player.global_position
    var rotation_before := player.rotation
    var forward_walk := await _exercise_input_walk(
        player, &"move_forward", 90, floor_y
    )

    player.global_position = origin
    player.rotation = rotation_before
    player.velocity = Vector3.ZERO
    await _settle_physics(8)
    var back_walk := await _exercise_input_walk(
        player, &"move_back", 90, floor_y
    )

    _check("R1_forward_walk_no_fall_through", not bool(forward_walk["fell_through"]))
    _check("R1_back_walk_no_fall_through", not bool(back_walk["fell_through"]))
    _check(
        "R1_walk_has_real_horizontal_progress",
        maxf(float(forward_walk["distance"]), float(back_walk["distance"])) >= 12.0
    )
    _check(
        "R1_walk_retains_floor_contact",
        maxf(
            float(forward_walk["floor_contact_ratio"]),
            float(back_walk["floor_contact_ratio"])
        ) >= 0.65
    )

func _exercise_r8_stairs(manager, player: CharacterBody3D) -> void:
    manager.transition_cooldown = 999.0
    manager.load_room("R8", false)
    await _settle(2)

    var node := _find_named(manager.current_room, "step011__mesh")
    if node == null:
        node = _find_named(manager.current_room, "step011")
    _check("R8_real_stair_mesh_present", node is MeshInstance3D)
    if not (node is MeshInstance3D):
        return

    var levels := _stair_tread_levels(node as MeshInstance3D)
    _check("R8_real_stair_has_multiple_treads", levels.size() >= 4)
    if levels.size() < 4:
        return

    var low: Dictionary = levels[0]
    var high: Dictionary = levels[levels.size() - 1]
    var low_center: Vector3 = low["center"]
    var high_center: Vector3 = high["center"]
    var up_dir := Vector3(
        high_center.x - low_center.x,
        0.0,
        high_center.z - low_center.z
    ).normalized()
    var stair_run := _horizontal_distance(low_center, high_center)
    var stair_rise := float(high["y"]) - float(low["y"])

    _check("R8_real_stair_rise_positive", stair_rise > 10.0)
    _check("R8_real_stair_run_nontrivial", stair_run > 20.0)

    # Start on the lowest real tread, then let production player.gd and
    # CharacterBody3D collision solve every intermediate riser.
    player.global_position = Vector3(
        low_center.x, float(low["y"]) + 4.0, low_center.z
    )
    player.velocity = Vector3.ZERO
    await _settle_physics(12)
    var ascent := await _walk_toward_progress(
        player,
        up_dir,
        stair_run * 0.80,
        150,
        float(low["y"]) - 6.0
    )
    _check("R8_stairs_up_progress", float(ascent["progress"]) >= stair_run * 0.70)
    _check("R8_stairs_up_height", float(ascent["max_y"]) >= float(high["y"]) - 3.0)
    _check("R8_stairs_up_no_fall_through", float(ascent["min_y"]) >= float(low["y"]) - 6.0)
    _check("R8_stairs_up_floor_contact", float(ascent["floor_contact_ratio"]) >= 0.45)

    # Descending is a separate regression because insufficient floor snap can
    # make a body lose support even when ascending has been fixed.
    player.global_position = Vector3(
        high_center.x, float(high["y"]) + 4.0, high_center.z
    )
    player.velocity = Vector3.ZERO
    await _settle_physics(12)
    var descent := await _walk_toward_progress(
        player,
        -up_dir,
        stair_run * 0.80,
        150,
        float(low["y"]) - 6.0
    )
    _check("R8_stairs_down_progress", float(descent["progress"]) >= stair_run * 0.70)
    _check("R8_stairs_down_height", float(descent["min_y"]) <= float(low["y"]) + 3.0)
    _check("R8_stairs_down_no_fall_through", float(descent["min_y"]) >= float(low["y"]) - 6.0)
    _check("R8_stairs_down_floor_contact", float(descent["floor_contact_ratio"]) >= 0.45)

func _finish(scene: Node = null, status_override: String = "") -> void:
    _release_move_actions()
    var status := status_override
    if status.is_empty():
        status = "PASS" if failures.is_empty() else "FAIL"
    var result := {
        "schema": "openazrael.kg001.physical_traversal",
        "version": 117,
        "status": status,
        "checks": check_count,
        "failed": failures,
        "scope": "real production CharacterBody3D traversal using gameplay Input actions over the canonical R1 floor and imported R8 step011 staircase; no movement-result teleport shortcut"
    }
    print("OPENAZRAEL_KG001_PHYSICAL_V117 " + JSON.stringify(result))
    if scene != null:
        scene.queue_free()
    quit(0 if status == "PASS" else (2 if status.begins_with("BLOCKED") else 1))

func _run() -> void:
    var missing: Array[String] = []
    for path in REQUIRED_ROOMS:
        if not ResourceLoader.exists(path):
            missing.append(path)
    if not missing.is_empty():
        print("OPENAZRAEL_KG001_PHYSICAL_V117 " + JSON.stringify({
            "schema": "openazrael.kg001.physical_traversal",
            "version": 117,
            "status": "BLOCKED_MISSING_ASSETS",
            "missing": missing
        }))
        quit(2)
        return

    var packed = load("res://main.tscn")
    if packed == null:
        failures.append("main_scene_load")
        _finish()
        return

    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle(3)

    var manager = scene.get_node_or_null("RoomManager")
    var player = scene.get_node_or_null("Player")
    _check("room_manager_present", manager != null)
    _check("production_player_present", player is CharacterBody3D)
    if manager == null or not (player is CharacterBody3D):
        _finish(scene)
        return

    await _exercise_r1_floor(scene, manager, player as CharacterBody3D)
    await _exercise_r8_stairs(manager, player as CharacterBody3D)
    _finish(scene)
