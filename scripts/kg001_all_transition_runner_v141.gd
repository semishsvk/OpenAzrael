extends SceneTree

const EvidenceBus = preload("res://scripts/validation/pppv_evidence_bus.gd")
const Navigator = preload("res://scripts/validation/pppv_navigator.gd")
const PlayerDriver = preload("res://scripts/validation/pppv_player_driver.gd")
const RuntimeGuard = preload("res://scripts/validation/pppv_runtime_guard.gd")

const R7_WELL_TO_EXIT_ROUTE := [
    Vector3(-21.4, -47.57, 51.4),
    Vector3(-24.0, -47.57, 78.0),
    Vector3(-8.0, -41.45, 78.0),
    Vector3(25.0, -41.45, 70.0),
    Vector3(45.0, -41.45, 80.0),
    Vector3(45.0, -41.45, 60.0),
    Vector3(38.0, -41.45, 30.0),
    Vector3(30.0, -41.45, 0.0),
    Vector3(30.0, -41.45, -35.0),
    Vector3(50.0, -41.56, -55.0),
    Vector3(65.0, -41.56, -85.0),
]

const R1_ROUTE := [
    Vector3(-203.801173, -84.921990, 300.265764),
    Vector3(-168.693718, -91.949649, 281.939643),
    Vector3(-113.787899, -107.514682, 201.650247),
    Vector3(-72.816896, -114.240783, 116.816224),
    Vector3(-75.0, -114.300000, 70.0),
    Vector3(-75.0, -114.300000, 20.0),
    Vector3(-50.0, -114.300000, -20.0),
    Vector3(0.0, -115.000000, -50.0),
    Vector3(38.260757, -115.691564, -50.391974),
    Vector3(95.934301, -117.355663, -127.453640),
    Vector3(141.988445, -115.622030, -209.540090),
    Vector3(119.250000, -114.455000, -261.236000),
    Vector3(156.921000, -114.276000, -313.508000),
    Vector3(203.566000, -114.275000, -324.678000),
    Vector3(210.088000, -114.364000, -410.699000),
    Vector3(266.328000, -114.240000, -415.593000),
    Vector3(299.061000, -110.726000, -486.612000),
    Vector3(356.752000, -108.708000, -475.156000),
    Vector3(405.288000, -99.161000, -522.654000),
    Vector3(449.221720, -93.255052, -498.865461),
    Vector3(476.420000, -85.030000, -514.950000),
    Vector3(529.295811, -84.205500, -513.041569),
]

var failures: Array[String] = []
var checks := 0
var crossed: Array[String] = []
var room_sequence: Array[String] = []

func _check(name: String, ok: bool) -> void:
    checks += 1
    if not ok:
        failures.append(name)

func _settle(frames: int = 4) -> void:
    for _i in range(frames):
        await physics_frame

func _v3(raw) -> Vector3:
    if not raw is Array or raw.size() < 3:
        return Vector3.ZERO
    return Vector3(float(raw[0]), float(raw[1]), float(raw[2]))

func _transition_target(manager, room_id: String, trigger_name: String) -> Vector3:
    var rec = manager.call("_trigger_record", room_id, trigger_name)
    if not rec is Dictionary or rec.is_empty():
        return Vector3.ZERO
    return _v3(rec.get("centroid", []))

func _supported(scene: Node3D, player: CharacterBody3D) -> bool:
    var q := PhysicsRayQueryParameters3D.create(
        player.global_position + Vector3.UP * 8.0,
        player.global_position + Vector3.DOWN * 72.0,
        1
    )
    q.exclude = [player.get_rid()]
    q.hit_back_faces = true
    var hit := scene.get_world_3d().direct_space_state.intersect_ray(q)
    if hit.is_empty():
        return false
    return player.global_position.y >= float((hit["position"] as Vector3).y) - 4.0

func _approach_and_interact(
    action_id: String,
    target_name: String,
    manager,
    nav,
    driver,
    guard
) -> bool:
    guard.begin_action({"action_id": action_id, "kind": "interaction"})
    var approach: Dictionary = await nav.approach_interactable(
        action_id + "_approach", target_name, manager.current_room, 1100, 180
    )
    var ok := bool(approach.get("reached", false))
    if ok:
        var aim: Dictionary = await nav.aim_at_interactable(
            action_id + "_aim", target_name, manager.current_room, 220
        )
        ok = bool(aim.get("acquired", false))
    if ok:
        ok = await driver.interact_via_probe(action_id + "_interact", target_name)
    guard.end_action(ok, {"target": target_name})
    _check(action_id, ok)
    return ok

func _walk_waypoints(prefix: String, points: Array, nav, guard) -> bool:
    for i in range(points.size()):
        var action_id := "%s_%02d" % [prefix, i]
        guard.begin_action({"action_id": action_id, "kind": "movement"})
        var result: Dictionary = await nav.approach_world_point(
            action_id,
            points[i],
            Callable(),
            900,
            150,
            18.0
        )
        var ok := bool(result.get("reached", false))
        guard.end_action(ok, {
            "target": [points[i].x, points[i].y, points[i].z]
        })
        _check(action_id, ok)
        if not ok:
            return false
    return true

func _cross_transition(
    action_id: String,
    source_room: String,
    trigger_name: String,
    destination_room: String,
    manager,
    nav,
    guard,
    scene: Node3D,
    player: CharacterBody3D
) -> bool:
    _check(action_id + "_source_room", String(manager.current_room_id) == source_room)
    var target := _transition_target(manager, source_room, trigger_name)
    _check(action_id + "_trigger_record", target != Vector3.ZERO)
    if target == Vector3.ZERO:
        return false

    guard.begin_action({"action_id": action_id, "kind": "transition"})
    var stop := func() -> bool:
        return String(manager.current_room_id) == destination_room
    var result: Dictionary = await nav.approach_world_point(
        action_id + "_approach",
        target,
        stop,
        1400,
        220,
        5.0
    )
    for _i in range(24):
        if String(manager.current_room_id) == destination_room:
            break
        await physics_frame

    var changed := String(manager.current_room_id) == destination_room
    var supported := changed and _supported(scene, player)
    var ok := bool(result.get("reached", false)) and changed and supported
    guard.end_action(ok, {
        "source_room": source_room,
        "trigger": trigger_name,
        "destination_room": destination_room,
        "supported": supported,
    })
    _check(action_id + "_changed_room", changed)
    _check(action_id + "_destination_supported", supported)
    _check(action_id + "_runtime_guard", guard.current_action_ok())
    if ok:
        crossed.append("%s:%s->%s" % [source_room, trigger_name, destination_room])
        room_sequence.append(destination_room)
    return ok

func _finish(scene: Node = null, guard = null) -> void:
    for action in [&"move_forward", &"move_back", &"move_left", &"move_right"]:
        Input.action_release(action)
    var guard_failures: Array = guard.failure_list() if guard != null else []
    _check("all_four_transitions_crossed", crossed.size() == 4)
    _check("no_runtime_guard_failures", guard_failures.is_empty())
    var result := {
        "schema": "openazrael.kg001.all_transition_traversal",
        "version": 141,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": checks,
        "failed": failures,
        "crossed": crossed,
        "room_sequence": room_sequence,
        "runtime_guard_failures": guard_failures,
        "movement": "production CharacterBody3D Input via PPPVNavigator; no target teleport",
        "state": "production pickup/door/key interactions; no direct prerequisite state injection",
    }
    print("OPENAZRAEL_KG001_ALL_TRANSITIONS_V141 " + JSON.stringify(result))
    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _run() -> void:
    for path in [
        "res://assets/rooms/R1.glb",
        "res://assets/rooms/R7.glb",
        "res://assets/rooms/R8.glb",
    ]:
        if not ResourceLoader.exists(path):
            print("OPENAZRAEL_KG001_ALL_TRANSITIONS_V141 " + JSON.stringify({
                "schema": "openazrael.kg001.all_transition_traversal",
                "version": 141,
                "status": "BLOCKED_MISSING_ASSETS",
                "missing": path,
            }))
            quit(2)
            return

    var state = root.get_node_or_null("DemoState")
    _check("demo_state_present", state != null)
    if state == null:
        _finish()
        return
    state.reset_all()

    var packed = load("res://main.tscn")
    _check("main_scene_load", packed is PackedScene)
    if not packed is PackedScene:
        _finish()
        return

    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle(8)
    var manager = scene.get_node_or_null("RoomManager")
    var player = scene.get_node_or_null("Player")
    _check("room_manager_present", manager != null)
    _check("production_player_present", player is CharacterBody3D)
    if manager == null or not player is CharacterBody3D:
        _finish(scene)
        return

    var probe = player.get_node_or_null("Camera3D/InteractionProbe")
    _check("interaction_probe_present", probe != null)
    if probe == null:
        _finish(scene)
        return

    var evidence = EvidenceBus.new()
    var guard = RuntimeGuard.new(player, manager, state, evidence)
    var nav = Navigator.new(player, probe, evidence, guard)
    var driver = PlayerDriver.new(player, probe, evidence, guard)

    manager.transition_cooldown = 999.0
    _check(
        "initial_R1_portal_entry",
        bool(manager.call("load_room_at_portal", "R1", "spaview", false))
    )
    manager.transition_cooldown = 0.0
    await _settle(12)
    room_sequence.append("R1")
    _check("initial_R1_supported", _supported(scene, player))

    # Door 1 blocks the physical corridor from the spaview spawn toward
    # TONG6. Open it first, then traverse the validated R1 route using
    # production movement. The last route point is beyond door 2, so keep
    # it out of this pre-key traversal.
    if not await _approach_and_interact(
        "open_R1_door1", "Interact_doorcor01", manager, nav, driver, guard
    ):
        _finish(scene, guard)
        return
    _check("door1_open_flag", state.flag("R1Door1Open"))

    var r1_pre_door2: Array = []
    for i in range(R1_ROUTE.size() - 1):
        r1_pre_door2.append(R1_ROUTE[i])
    if not await _walk_waypoints("R1_to_tongs", r1_pre_door2, nav, guard):
        _finish(scene, guard)
        return

    if not await _approach_and_interact(
        "pickup_tongs", "Interact_TONG6", manager, nav, driver, guard
    ):
        _finish(scene, guard)
        return
    _check("tongs_in_inventory", state.has("rusty_tongs"))

    var r1_back_to_r7: Array = r1_pre_door2.duplicate()
    r1_back_to_r7.reverse()
    if not await _walk_waypoints("R1_back_to_R7", r1_back_to_r7, nav, guard):
        _finish(scene, guard)
        return

    if not await _cross_transition(
        "transition_R1_R7", "R1", "zxcoriR5", "R7",
        manager, nav, guard, scene, player
    ):
        _finish(scene, guard)
        return
    await _settle(30)

    if not await _approach_and_interact(
        "take_well_key", "Interact_WellKey", manager, nav, driver, guard
    ):
        _finish(scene, guard)
        return
    _check("well_key_in_inventory", state.has("well_key"))
    _check("tongs_consumed", not state.has("rusty_tongs"))

    if not await _walk_waypoints("R7_well_to_exit", R7_WELL_TO_EXIT_ROUTE, nav, guard):
        _finish(scene, guard)
        return

    if not await _cross_transition(
        "transition_R7_R1", "R7", "zxwell2R6", "R1",
        manager, nav, guard, scene, player
    ):
        _finish(scene, guard)
        return
    await _settle(30)

    if not await _walk_waypoints("R1_to_door2", r1_pre_door2, nav, guard):
        _finish(scene, guard)
        return

    if not await _approach_and_interact(
        "open_R1_door2", "Interact_doorcor2", manager, nav, driver, guard
    ):
        _finish(scene, guard)
        return
    _check("door2_open_flag", state.flag("R1Door2Open"))
    _check("door2_unlock_flag", state.flag("FR1DoorUnlocked"))

    if not await _walk_waypoints(
        "R1_through_door2", [R1_ROUTE[R1_ROUTE.size() - 1]], nav, guard
    ):
        _finish(scene, guard)
        return

    if not await _cross_transition(
        "transition_R1_R8", "R1", "zxcoriR2", "R8",
        manager, nav, guard, scene, player
    ):
        _finish(scene, guard)
        return
    await _settle(30)

    if not await _cross_transition(
        "transition_R8_R1", "R8", "zxorrery", "R1",
        manager, nav, guard, scene, player
    ):
        _finish(scene, guard)
        return
    await _settle(30)

    _check("final_room_R1", String(manager.current_room_id) == "R1")
    _check("visited_R7", "R7" in room_sequence)
    _check("visited_R8", "R8" in room_sequence)
    _check("R1_reentered_twice", room_sequence.count("R1") >= 3)
    _finish(scene, guard)

func _initialize() -> void:
    call_deferred("_run")
