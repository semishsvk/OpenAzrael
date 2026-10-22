extends SceneTree

const EvidenceBus := preload("res://scripts/validation/pppv_evidence_bus.gd")

const REQUIRED_ROOMS := [
    "res://assets/rooms/R1.glb",
    "res://assets/rooms/R7.glb",
    "res://assets/rooms/R8.glb"
]

var failures: Array[String] = []
var check_count := 0
var pppv_evidence = EvidenceBus.new()

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

func _floor_at(
    scene: Node3D,
    player: CharacterBody3D,
    xz: Vector3,
    reference_y: float
) -> Dictionary:
    var query := PhysicsRayQueryParameters3D.create(
        Vector3(xz.x, reference_y + 40.0, xz.z),
        Vector3(xz.x, reference_y - 100.0, xz.z),
        1
    )
    query.exclude = [player.get_rid()]
    return scene.get_world_3d().direct_space_state.intersect_ray(query)

func _observe_portal_spawn(
    scene: Node3D,
    manager,
    player: CharacterBody3D,
    room_id: String,
    view_name: String,
    prefix: String
) -> Dictionary:
    manager.transition_cooldown = 999.0
    manager.load_room(room_id, false)
    await _settle(2)
    manager.call("_spawn_at_portal", room_id, view_name)

    var spawn_position := player.global_position
    await physics_frame
    var floor_hit := _floor_at(
        scene, player, spawn_position, spawn_position.y
    )
    _check(prefix + "_floor_support_present", not floor_hit.is_empty())
    if floor_hit.is_empty():
        return {
            "status": "NO_SUPPORT",
            "spawn_position": spawn_position,
            "floor_y": spawn_position.y
        }

    var floor_y := float((floor_hit["position"] as Vector3).y)
    var min_y := player.global_position.y
    var floor_frames := 0
    var fell_through := false
    for _i in range(45):
        await physics_frame
        min_y = minf(min_y, player.global_position.y)
        if player.is_on_floor():
            floor_frames += 1
        if player.global_position.y < floor_y - 4.0:
            fell_through = true
            break

    _check(prefix + "_natural_spawn_no_fall_through", not fell_through)
    _check(prefix + "_natural_spawn_reaches_floor", player.is_on_floor())
    _check(
        prefix + "_natural_spawn_floor_height",
        absf(player.global_position.y - floor_y) < 2.0
    )
    _check(
        prefix + "_natural_spawn_floor_contact",
        floor_frames >= 8
    )
    return {
        "status": "PASS" if not fell_through else "FAIL",
        "spawn_position": spawn_position,
        "floor_y": floor_y,
        "min_y": min_y,
        "floor_contact_frames": floor_frames
    }

func _exercise_input_walk(
    scene: Node3D,
    player: CharacterBody3D,
    action: StringName,
    frames: int,
    reference_floor_y: float
) -> Dictionary:
    _release_move_actions()
    var start := player.global_position
    var min_y := start.y
    var on_floor_frames := 0
    var support_y := reference_floor_y
    var support_missing_frames := 0
    var max_below_support := 0.0
    var fell_through := false

    Input.action_press(action, 1.0)
    for _i in range(frames):
        await physics_frame
        min_y = minf(min_y, player.global_position.y)
        if player.is_on_floor():
            on_floor_frames += 1

        # Track the expected local support independently of the player's Y.
        # This keeps a legitimate slope/step from looking like a fall, while a
        # capsule that crosses below the same floor surface fails immediately.
        var support_hit: Dictionary = _floor_at(
            scene, player, player.global_position, support_y
        )
        if support_hit.is_empty() or absf(float((support_hit["normal"] as Vector3).y)) < 0.5:
            support_missing_frames += 1
        else:
            support_y = float((support_hit["position"] as Vector3).y)
            var below_support := support_y - player.global_position.y
            max_below_support = maxf(max_below_support, below_support)
            if below_support > 2.5:
                fell_through = true
                break

    Input.action_release(action)
    await physics_frame
    return {
        "distance": _horizontal_distance(start, player.global_position),
        "min_y": min_y,
        "floor_contact_ratio": float(on_floor_frames) / float(maxi(frames, 1)),
        "support_missing_frames": support_missing_frames,
        "max_below_support": max_below_support,
        "fell_through": fell_through
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
    # Let normal deceleration/gravity/floor snap resolve the landing after the
    # target horizontal progress is reached. Discrete stair descent naturally
    # contains airborne frames; the meaningful oracle is a stable supported
    # landing without dropping below the lower floor.
    for _settle_i in range(12):
        await physics_frame
        min_y = minf(min_y, player.global_position.y)
        max_y = maxf(max_y, player.global_position.y)
    var moved := player.global_position - start
    return {
        "progress": Vector3(moved.x, 0.0, moved.z).dot(flat),
        "min_y": min_y,
        "max_y": max_y,
        "final_y": player.global_position.y,
        "final_on_floor": player.is_on_floor(),
        "floor_contact_ratio": float(on_floor_frames) / float(maxi(used_frames, 1))
    }

func _exercise_r1_floor(scene: Node3D, manager, player: CharacterBody3D) -> void:
    # Candidate 2 failed immediately after the real portal spawn. Do not
    # normalize the player onto a raycasted floor here: the spawn itself is now
    # part of the regression contract.
    var spawn_result := await _observe_portal_spawn(
        scene, manager, player, "R1", "spaview", "R1_spaview"
    )
    if String(spawn_result.get("status", "")) == "NO_SUPPORT":
        return
    var floor_y := float(spawn_result["floor_y"])

    # Preserve the canonical portal heading and exercise the same Input actions
    # used during manual gameplay. No teleport occurs while either walk runs.
    var origin := player.global_position
    var rotation_before := player.rotation
    var forward_walk := await _exercise_input_walk(
        scene, player, &"move_forward", 90, floor_y
    )

    player.global_position = origin
    player.rotation = rotation_before
    player.velocity = Vector3.ZERO
    await _settle_physics(8)
    var back_walk := await _exercise_input_walk(
        scene, player, &"move_back", 90, floor_y
    )

    pppv_evidence.record_player_action("r1_forward", "input", {"input_action": "move_forward"})
    pppv_evidence.record("collision_support", {
        "action_id": "r1_forward",
        "continuous": int(forward_walk["support_missing_frames"]) <= 3,
        "fell_through": bool(forward_walk["fell_through"]),
    }, "R1")
    pppv_evidence.record("movement", {
        "action_id": "r1_forward",
        "progress_ok": float(forward_walk["distance"]) >= 12.0,
        "distance": float(forward_walk["distance"]),
    }, "R1")
    pppv_evidence.record_player_action("r1_back", "input", {"input_action": "move_back"})
    pppv_evidence.record("collision_support", {
        "action_id": "r1_back",
        "continuous": int(back_walk["support_missing_frames"]) <= 3,
        "fell_through": bool(back_walk["fell_through"]),
    }, "R1")
    pppv_evidence.record("movement", {
        "action_id": "r1_back",
        "progress_ok": float(back_walk["distance"]) >= 12.0,
        "distance": float(back_walk["distance"]),
    }, "R1")

    _check("R1_forward_walk_no_fall_through", not bool(forward_walk["fell_through"]))
    _check("R1_back_walk_no_fall_through", not bool(back_walk["fell_through"]))
    _check("R1_forward_walk_support_continuous", int(forward_walk["support_missing_frames"]) <= 3)
    _check("R1_back_walk_support_continuous", int(back_walk["support_missing_frames"]) <= 3)
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

func _exercise_r8_stair_mesh(
    scene: Node3D,
    manager,
    player: CharacterBody3D,
    mesh_name: String,
    check_prefix: String,
    minimum_levels: int,
    minimum_rise: float,
    minimum_run: float
) -> void:
    var node := _find_named(manager.current_room, mesh_name)
    _check(check_prefix + "_mesh_present", node is MeshInstance3D)
    if not (node is MeshInstance3D):
        return

    var levels := _stair_tread_levels(node as MeshInstance3D)
    _check(check_prefix + "_multiple_treads", levels.size() >= minimum_levels)
    if levels.size() < minimum_levels:
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

    _check(check_prefix + "_rise", stair_rise >= minimum_rise)
    _check(check_prefix + "_run", stair_run >= minimum_run)

    # Probe actual collision immediately before and after the tread run.
    # This makes the test begin/end on the room's real landing surfaces.
    var lower_probe_point := low_center - up_dir * 24.0
    var lower_hit: Dictionary = _floor_at(
        scene, player, lower_probe_point, float(low["y"])
    )
    _check(check_prefix + "_lower_landing_present", not lower_hit.is_empty())
    if lower_hit.is_empty():
        return
    var lower_floor_y := float((lower_hit["position"] as Vector3).y)

    var upper_probe_point := high_center + up_dir * 14.0
    var upper_hit: Dictionary = _floor_at(
        scene, player, upper_probe_point, float(high["y"])
    )
    _check(check_prefix + "_upper_landing_present", not upper_hit.is_empty())
    if upper_hit.is_empty():
        return
    var upper_floor_y := float((upper_hit["position"] as Vector3).y)

    var ascent_distance := _horizontal_distance(
        lower_probe_point, upper_probe_point
    )
    _check(check_prefix + "_full_path_nontrivial", ascent_distance > stair_run)

    # Walk from the lower real landing through every riser to the upper landing.
    player.global_position = Vector3(
        lower_probe_point.x, lower_floor_y + 4.0, lower_probe_point.z
    )
    player.velocity = Vector3.ZERO
    await _settle_physics(12)
    _check(check_prefix + "_lower_landing_floor_contact", player.is_on_floor())
    pppv_evidence.record_player_action("ascend", "input", {
        "input_action": "move_forward",
        "mesh": mesh_name,
    })
    var ascent := await _walk_toward_progress(
        player,
        up_dir,
        ascent_distance * 0.98,
        240,
        lower_floor_y - 6.0
    )
    pppv_evidence.record("stair_traversal", {
        "action_id": "ascend",
        "mesh": mesh_name,
        "direction": "ascending",
        "progress_ok": float(ascent["progress"]) >= ascent_distance * 0.94,
        "height_ok": float(ascent["max_y"]) >= upper_floor_y - 3.0,
        "fell_through": float(ascent["min_y"]) < lower_floor_y - 6.0,
    }, "R8")
    _check(check_prefix + "_up_progress", float(ascent["progress"]) >= ascent_distance * 0.94)
    _check(check_prefix + "_up_height", float(ascent["max_y"]) >= upper_floor_y - 3.0)
    _check(check_prefix + "_up_no_fall_through", float(ascent["min_y"]) >= lower_floor_y - 6.0)
    _check(check_prefix + "_up_floor_contact", float(ascent["floor_contact_ratio"]) >= 0.40)

    # Descending is independently required: floor snap/support may fail on the
    # way down even when step-up has been fixed.
    player.global_position = Vector3(
        upper_probe_point.x, upper_floor_y + 4.0, upper_probe_point.z
    )
    player.velocity = Vector3.ZERO
    await _settle_physics(12)
    _check(check_prefix + "_upper_landing_floor_contact", player.is_on_floor())
    pppv_evidence.record_player_action("descend", "input", {
        "input_action": "move_forward",
        "mesh": mesh_name,
    })
    var descent := await _walk_toward_progress(
        player,
        -up_dir,
        ascent_distance * 0.98,
        240,
        lower_floor_y - 6.0
    )
    pppv_evidence.record("stair_traversal", {
        "action_id": "descend",
        "mesh": mesh_name,
        "direction": "descending",
        "progress_ok": float(descent["progress"]) >= ascent_distance * 0.94,
        "height_ok": float(descent["final_y"]) <= lower_floor_y + 1.0,
        "fell_through": float(descent["min_y"]) < lower_floor_y - 6.0,
    }, "R8")
    _check(check_prefix + "_down_progress", float(descent["progress"]) >= ascent_distance * 0.94)
    _check(check_prefix + "_down_height", float(descent["final_y"]) <= lower_floor_y + 1.0)
    _check(check_prefix + "_down_no_fall_through", float(descent["min_y"]) >= lower_floor_y - 6.0)
    _check(check_prefix + "_down_floor_contact", bool(descent["final_on_floor"]))

func _exercise_r8_stairs(scene: Node3D, manager, player: CharacterBody3D) -> void:
    if player.has_method("clear_step_debug"):
        player.call("clear_step_debug")
    manager.transition_cooldown = 999.0
    manager.load_room("R8", false)
    await _settle(2)

    # Real asset audit shows two meshes with horizontal tread sequences:
    # step011 = 4 lower steps (~5.1 rise each), stairs__STAIR2 = 8 main
    # staircase levels (~12.6 rise each). Cover both because the latter is the
    # stronger production step-up regression. Decorative/vertical step04,
    # step05 and stairs__BAPSTAIR are intentionally not treated as treads.
    await _exercise_r8_stair_mesh(
        scene, manager, player,
        "step011__mesh", "R8_step011",
        4, 14.0, 28.0
    )
    await _exercise_r8_stair_mesh(
        scene, manager, player,
        "stairs__STAIR2", "R8_main_stairs",
        8, 80.0, 120.0
    )

func _finish(scene: Node = null, status_override: String = "") -> void:
    _release_move_actions()
    var status := status_override
    if status.is_empty():
        status = "PASS" if failures.is_empty() else "FAIL"
    var step_debug: Array = []
    if scene != null:
        var debug_player := scene.get_node_or_null("Player")
        if debug_player != null and debug_player.has_method("step_debug_snapshot"):
            step_debug = debug_player.call("step_debug_snapshot")
    var result := {
        "schema": "openazrael.kg001.physical_traversal",
        "version": 117,
        "status": status,
        "checks": check_count,
        "failed": failures,
        "step_debug": step_debug,
        "pppv_evidence": pppv_evidence.bundle(),
        "scope": "natural portal-spawn support in R1/R7/R8 plus real production CharacterBody3D traversal using gameplay Input actions over the canonical R1 floor and both imported R8 tread sequences (step011 and stairs__STAIR2), including ascent and descent; no floor-normalizing test teleport"
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

    # Validate every portal-view spawn used by the demo loop before active
    # traversal. R1/spaview is also the manual Candidate start.
    await _observe_portal_spawn(
        scene, manager, player as CharacterBody3D,
        "R1", "entcori", "R1_entcori"
    )
    await _observe_portal_spawn(
        scene, manager, player as CharacterBody3D,
        "R7", "view", "R7_view"
    )
    await _observe_portal_spawn(
        scene, manager, player as CharacterBody3D,
        "R8", "Object14", "R8_Object14"
    )
    await _exercise_r1_floor(scene, manager, player as CharacterBody3D)
    await _exercise_r8_stairs(scene, manager, player as CharacterBody3D)
    _finish(scene)
