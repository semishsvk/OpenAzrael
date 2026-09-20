extends SceneTree

const REQUIRED_ROOMS := [
    "res://assets/rooms/R1.glb",
    "res://assets/rooms/R7.glb",
    "res://assets/rooms/R8.glb"
]
const TRANSITIONS := [
    ["R1", "zxcoriR5", "R7"],
    ["R1", "zxcoriR2", "R8"],
    ["R7", "zxwell2R6", "R1"],
    ["R8", "zxorrery", "R1"]
]
const FLOOR_SUPPORT_PROBES := [
    ["R1", "spaview"],
    ["R7", "view"],
    ["R8", "Object14"]
]

var failures: Array[String] = []

func _initialize() -> void:
    call_deferred("_run")

func _check(name: String, condition: bool) -> void:
    if not condition:
        failures.append(name)

func _v3(value: Array) -> Vector3:
    return Vector3(float(value[0]), float(value[1]), float(value[2]))

func _place_on_trigger(manager, player, room_id: String, trigger_name: String) -> bool:
    var record: Dictionary = manager.call("_trigger_record", room_id, trigger_name)
    if record.is_empty():
        return false
    player.global_position = _v3(record["centroid"])
    manager.transition_cooldown = 0.0
    return true

func _settle(frames: int = 3) -> void:
    for _i in range(frames):
        await process_frame

func _settle_physics(frames: int = 3) -> void:
    for _i in range(frames):
        await physics_frame

func _collect_concave_shapes(node: Node, out: Array[CollisionShape3D]) -> void:
    if node is CollisionShape3D:
        var cs := node as CollisionShape3D
        if cs.shape is ConcavePolygonShape3D:
            out.append(cs)
    for child in node.get_children():
        _collect_concave_shapes(child, out)

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

func _release_move_actions() -> void:
    for action in ["move_forward", "move_back", "move_left", "move_right"]:
        Input.action_release(action)

func _horizontal_distance(a: Vector3, b: Vector3) -> float:
    return Vector2(a.x - b.x, a.z - b.z).length()

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
    groups.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return float(a["y"]) < float(b["y"]))

    # The legacy step011 mesh includes one broad underside plane below the
    # actual tread tops. Exclude that structural underside by area rather than
    # relying on source winding; imported winding is exactly what Issue #6
    # previously proved cannot be trusted.
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
        return {"progress":0.0, "min_y":player.global_position.y, "max_y":player.global_position.y, "floor_contact_ratio":0.0}
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

func _exercise_real_r8_stairs(manager, player: CharacterBody3D) -> void:
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

    player.global_position = Vector3(low_center.x, float(low["y"]) + 4.0, low_center.z)
    player.velocity = Vector3.ZERO
    await _settle_physics(12)
    var ascent := await _walk_toward_progress(
        player,
        up_dir,
        stair_run * 0.80,
        150,
        float(low["y"]) - 6.0
    )
    _check("R8_real_stairs_up_progress", float(ascent["progress"]) >= stair_run * 0.70)
    _check("R8_real_stairs_up_height", float(ascent["max_y"]) >= float(high["y"]) - 3.0)
    _check("R8_real_stairs_up_no_fall_through", float(ascent["min_y"]) >= float(low["y"]) - 6.0)
    _check("R8_real_stairs_up_floor_contact", float(ascent["floor_contact_ratio"]) >= 0.45)

    player.global_position = Vector3(high_center.x, float(high["y"]) + 4.0, high_center.z)
    player.velocity = Vector3.ZERO
    await _settle_physics(12)
    var descent := await _walk_toward_progress(
        player,
        -up_dir,
        stair_run * 0.80,
        150,
        float(low["y"]) - 6.0
    )
    _check("R8_real_stairs_down_progress", float(descent["progress"]) >= stair_run * 0.70)
    _check("R8_real_stairs_down_height", float(descent["min_y"]) <= float(low["y"]) + 3.0)
    _check("R8_real_stairs_down_no_fall_through", float(descent["min_y"]) >= float(low["y"]) - 6.0)
    _check("R8_real_stairs_down_floor_contact", float(descent["floor_contact_ratio"]) >= 0.45)

func _run() -> void:
    var missing: Array[String] = []
    for path in REQUIRED_ROOMS:
        if not ResourceLoader.exists(path):
            missing.append(path)
    if not missing.is_empty():
        print("OPENAZRAEL_KG001_V110 " + JSON.stringify({
            "schema":"openazrael.kg001.room_trigger",
            "version":110,
            "status":"BLOCKED_MISSING_ASSETS",
            "missing":missing
        }))
        quit(2)
        return

    var events = root.get_node_or_null("LegacyEvents")
    var state = root.get_node_or_null("DemoState")
    if events == null or state == null:
        print("OPENAZRAEL_KG001_V110 " + JSON.stringify({"version":110,"status":"FAIL","error":"required autoload missing"}))
        quit(1)
        return

    events.set_capture_only(true)
    state.reset_all()

    var packed = load("res://main.tscn")
    if packed == null:
        print("OPENAZRAEL_KG001_V110 " + JSON.stringify({"version":110,"status":"FAIL","error":"cannot load main.tscn"}))
        quit(1)
        return
    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle()

    var manager = scene.get_node("RoomManager")
    var player = scene.get_node("Player")
    _check("initial_room_R1", manager.current_room_id == "R1")

    # Issue #6 regression: the root cause is imported legacy trimesh winding,
    # not an R1-only condition. Exercise the actual player capsule at the
    # canonical entry view of every demo room before testing transitions.
    for probe in FLOOR_SUPPORT_PROBES:
        var probe_room := String(probe[0])
        var probe_view := String(probe[1])
        manager.transition_cooldown = 999.0
        manager.load_room(probe_room, false)
        await _settle(2)
        manager.call("_spawn_at_portal", probe_room, probe_view)
        await _settle_physics(2)

        if probe_room == "R8":
            var support = manager.call("_find_node", "Object01")
            var support_mesh = manager.call("_first_mesh", support)
            _check("R8_entrance_support_remains_hidden", support_mesh != null and not support_mesh.visible)
            _check("R8_entrance_support_has_collision", support_mesh != null and support_mesh.has_node("Collision_Object01"))

        var concave_shapes: Array[CollisionShape3D] = []
        _collect_concave_shapes(manager.current_room, concave_shapes)
        _check(probe_room + "_concave_world_collision_present", not concave_shapes.is_empty())
        for i in range(concave_shapes.size()):
            var concave := concave_shapes[i].shape as ConcavePolygonShape3D
            _check("%s_concave_backface_%d" % [probe_room, i], concave.backface_collision)

        var floor_hit: Dictionary = await _floor_probe(scene, player)
        _check(probe_room + "_floor_probe_hit", not floor_hit.is_empty())
        if not floor_hit.is_empty():
            var floor_position: Vector3 = floor_hit["position"]
            player.global_position = Vector3(
                player.global_position.x,
                # A small drop leaves the real capsule below the low tunnel
                # ceiling; +60 could embed it in the roof or land on its top.
                floor_position.y + 4.0,
                player.global_position.z
            )
            player.velocity = Vector3.ZERO
            await _settle_physics(30)
            _check(probe_room + "_player_is_on_floor", player.is_on_floor())
            _check(probe_room + "_player_reached_probed_floor", absf(player.global_position.y - floor_position.y) < 2.0)
            _check(
                probe_room + "_player_did_not_fall_through",
                player.global_position.y >= floor_position.y - 2.0
            )

            # Candidate 2 escaped the old regression because it only stood
            # still at one raycast point. In R1, drive the production Player
            # through the exact Input actions used by gameplay, in both
            # directions along the canonical portal heading.
            if probe_room == "R1":
                var walk_origin := player.global_position
                var walk_rotation := player.rotation
                var forward_walk := await _exercise_input_walk(
                    player, &"move_forward", 90, floor_position.y
                )
                player.global_position = walk_origin
                player.rotation = walk_rotation
                player.velocity = Vector3.ZERO
                await _settle_physics(8)
                var back_walk := await _exercise_input_walk(
                    player, &"move_back", 90, floor_position.y
                )
                _check("R1_real_walk_forward_no_fall_through", not bool(forward_walk["fell_through"]))
                _check("R1_real_walk_back_no_fall_through", not bool(back_walk["fell_through"]))
                _check(
                    "R1_real_walk_has_horizontal_progress",
                    maxf(float(forward_walk["distance"]), float(back_walk["distance"])) >= 12.0
                )
                _check(
                    "R1_real_walk_floor_contact",
                    maxf(
                        float(forward_walk["floor_contact_ratio"]),
                        float(back_walk["floor_contact_ratio"])
                    ) >= 0.65
                )

    # Exercise the real imported R8 stair mesh with the real CharacterBody3D,
    # collision layer/mask, production player.gd and Input actions. The tread
    # profile is measured from step011 at runtime; no guessed staircase proxy
    # or teleport-to-top shortcut is accepted.
    await _exercise_real_r8_stairs(manager, player)

    # Geometric boundary oracle: every transition trigger centroid is inside,
    # while a point beyond both X/Z maxima is outside.
    for spec in TRANSITIONS:
        var room_id := String(spec[0])
        var trigger_name := String(spec[1])
        manager.load_room(room_id, false)
        await _settle(1)
        var record: Dictionary = manager.call("_trigger_record", room_id, trigger_name)
        _check("trigger_record_" + room_id + "_" + trigger_name, not record.is_empty())
        if not record.is_empty():
            var center := _v3(record["centroid"])
            var mx := _v3(record["bounds"][1])
            var outside := Vector3(mx.x + 2.0, center.y, mx.z + 2.0)
            _check("inside_" + room_id + "_" + trigger_name, bool(manager.call("_inside_trigger", center, record)))
            _check("outside_" + room_id + "_" + trigger_name, not bool(manager.call("_inside_trigger", outside, record)))

    # Live transition sequence with both R1 negative gates.
    manager.load_room("R1", false)
    await _settle(1)
    state.acquire("well_key")

    _check("place_locked_R1_R7", _place_on_trigger(manager, player, "R1", "zxcoriR5"))
    await _settle()
    _check("locked_R1_R7_stays_R1", manager.current_room_id == "R1")

    state.set_flag("R1Door1Open")
    manager.transition_cooldown = 0.0
    await _settle()
    _check("open_R1_R7_enters_R7", manager.current_room_id == "R7")

    _check("place_R7_R1", _place_on_trigger(manager, player, "R7", "zxwell2R6"))
    await _settle()
    _check("R7_R1_enters_R1", manager.current_room_id == "R1")

    _check("place_locked_R1_R8", _place_on_trigger(manager, player, "R1", "zxcoriR2"))
    await _settle()
    _check("locked_R1_R8_stays_R1", manager.current_room_id == "R1")

    state.set_flag("R1Door2Open")
    manager.transition_cooldown = 0.0
    await _settle()
    _check("open_R1_R8_enters_R8", manager.current_room_id == "R8")

    _check("place_R8_R1", _place_on_trigger(manager, player, "R8", "zxorrery"))
    await _settle()
    _check("R8_R1_enters_R1", manager.current_room_id == "R1")
    _check("persistent_inventory_survives_rooms", state.has("well_key"))

    var result := {
        "schema":"openazrael.kg001.room_trigger",
        "version":110,
        "status":"PASS" if failures.is_empty() else "FAIL",
        "failed":failures,
        "scope":"G04/G05 room transitions plus real CharacterBody3D traversal: active Input-driven R1 floor walking, R1/R7/R8 floor support, and measured imported R8 step011 stair ascent/descent"
    }
    print("OPENAZRAEL_KG001_V110 " + JSON.stringify(result))
    scene.queue_free()
    quit(0 if failures.is_empty() else 1)
