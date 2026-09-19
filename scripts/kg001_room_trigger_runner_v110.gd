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

    # Issue #6 regression: legacy room trimeshes must collide from either face.
    # This catches reversed/inconsistent source triangle winding before gameplay.
    var concave_shapes: Array[CollisionShape3D] = []
    _collect_concave_shapes(manager.current_room, concave_shapes)
    _check("R1_concave_world_collision_present", not concave_shapes.is_empty())
    for i in range(concave_shapes.size()):
        var concave := concave_shapes[i].shape as ConcavePolygonShape3D
        _check("R1_concave_backface_%d" % i, concave.backface_collision)

    # Physical floor-support regression: locate the floor below the authored R1
    # spawn, drop the real player capsule onto it, and require grounded support.
    manager.transition_cooldown = 999.0
    var floor_hit: Dictionary = await _floor_probe(scene, player)
    _check("R1_floor_probe_hit", not floor_hit.is_empty())
    if not floor_hit.is_empty():
        var floor_position: Vector3 = floor_hit["position"]
        player.global_position = Vector3(player.global_position.x, floor_position.y + 60.0, player.global_position.z)
        player.velocity = Vector3.ZERO
        await _settle_physics(120)
        _check("R1_player_is_on_floor", player.is_on_floor())
        _check("R1_player_did_not_fall_through", player.global_position.y >= floor_position.y - 2.0)

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
        "scope":"G04/G05 room transitions, physical trigger bounds, and Issue #6 R1 floor-support regression with restored local R1/R7/R8 assets"
    }
    print("OPENAZRAEL_KG001_V110 " + JSON.stringify(result))
    scene.queue_free()
    quit(0 if failures.is_empty() else 1)
