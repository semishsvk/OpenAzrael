extends SceneTree

const REQUIRED_ROOM := "res://assets/rooms/R1.glb"
const BUG_POINT := Vector3(-264.159088134766, -83.86095602785532, 381.168426513672)
const OBJECT02_FAR := Vector3(-276.0, -83.83532396, 410.0)
const TUNNEL03_CENTER := Vector3(-226.828524, -83.861132, 318.183653)
const WAYPOINT_TOLERANCE := 5.5
const MAX_STALL_FRAMES := 120
const MAX_LEG_FRAMES := 360

const ROUTE := [
    Vector3(-203.801173, -84.921990, 300.265764),
    Vector3(-168.693718, -91.949649, 281.939643),
    Vector3(-113.787899, -107.514682, 201.650247),
    Vector3(-72.816896, -114.240783, 116.816224),
    # Capsule-safe detour around the authored Collision_save volume.
    Vector3(-75.0, -114.30, 70.0),
    Vector3(-75.0, -114.30, 20.0),
    Vector3(-50.0, -114.30, -20.0),
    Vector3(0.0, -115.0, -50.0),
    Vector3(38.260757, -115.691564, -50.391974),
    Vector3(95.934301, -117.355663, -127.453640),
    Vector3(141.988445, -115.622030, -209.540090),
    # Capsule-safe path around the steep side face of floorbit07.
    Vector3(171.0, -112.6228, -243.0),
    Vector3(201.0, -114.2756, -273.0),
    Vector3(221.0, -114.2755, -303.0),
    Vector3(231.0, -114.2754, -333.0),
    Vector3(241.0, -114.2804, -353.0),
    Vector3(271.0, -114.2393, -383.0),
    Vector3(301.0, -114.2017, -413.0),
    Vector3(321.0, -112.9316, -433.0),
    Vector3(351.0, -111.0581, -443.0),
    Vector3(371.0, -109.9054, -453.0),
    Vector3(385.0, -108.7538, -465.0),
    Vector3(401.0, -106.3075, -481.0),
    Vector3(417.0, -102.7426, -481.0),
    Vector3(433.0, -98.01898, -489.0),
    Vector3(449.221720, -93.255052, -498.865461),
    # wall01 is authored side geometry, not a player-space waypoint. From the
    # floorbit04 corridor the production capsule reaches tunnel07 directly.
    Vector3(529.295811, -84.205500, -513.041569),
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

func _find_named(node: Node, wanted: String) -> Node:
    if String(node.name) == wanted:
        return node
    for child in node.get_children():
        var found := _find_named(child, wanted)
        if found != null:
            return found
    return null

func _floor_at(
    scene: Node3D,
    player: CharacterBody3D,
    xz: Vector3,
    reference_y: float
) -> Dictionary:
    var query := PhysicsRayQueryParameters3D.create(
        Vector3(xz.x, reference_y + 45.0, xz.z),
        Vector3(xz.x, reference_y - 120.0, xz.z),
        1
    )
    query.exclude = [player.get_rid()]
    query.hit_back_faces = true
    return scene.get_world_3d().direct_space_state.intersect_ray(query)

func _collider_name(hit: Dictionary) -> String:
    var collider = hit.get("collider")
    return String(collider.name) if collider is Node else ""

func _walk_leg(
    scene: Node3D,
    player: CharacterBody3D,
    target: Vector3,
    label: String
) -> Dictionary:
    _release_move_actions()
    player.velocity = Vector3.ZERO

    var start := player.global_position
    var support_y := start.y
    var initial_support: Dictionary = _floor_at(scene, player, start, support_y)
    if not initial_support.is_empty():
        support_y = float((initial_support["position"] as Vector3).y)

    var best_distance := Vector2(start.x - target.x, start.z - target.z).length()
    var stall_frames := 0
    var used_frames := 0
    var floor_frames := 0
    var support_missing_total := 0
    var support_missing_consecutive := 0
    var support_missing_max := 0
    var min_y := start.y
    var fell_through := false
    var reached := false
    var support_colliders: Dictionary = {}

    Input.action_press("move_forward", 1.0)
    for frame in range(MAX_LEG_FRAMES):
        var delta_xz := Vector3(
            target.x - player.global_position.x,
            0.0,
            target.z - player.global_position.z
        )
        var distance := delta_xz.length()
        if distance <= WAYPOINT_TOLERANCE:
            reached = true
            break

        if delta_xz.length_squared() > 0.0001:
            var direction := delta_xz.normalized()
            player.rotation.y = atan2(-direction.x, -direction.z)

        await physics_frame
        used_frames = frame + 1
        min_y = minf(min_y, player.global_position.y)
        if player.is_on_floor():
            floor_frames += 1

        var support_hit: Dictionary = _floor_at(
            scene, player, player.global_position, support_y
        )
        if support_hit.is_empty():
            support_missing_total += 1
            support_missing_consecutive += 1
            support_missing_max = maxi(
                support_missing_max, support_missing_consecutive
            )
        else:
            support_missing_consecutive = 0
            support_y = float((support_hit["position"] as Vector3).y)
            var name := _collider_name(support_hit)
            if not name.is_empty():
                support_colliders[name] = true
            if player.global_position.y < support_y - 4.0:
                fell_through = true
                break

        var new_distance := Vector2(
            player.global_position.x - target.x,
            player.global_position.z - target.z
        ).length()
        if new_distance < best_distance - 0.20:
            best_distance = new_distance
            stall_frames = 0
        else:
            stall_frames += 1
            if stall_frames > MAX_STALL_FRAMES:
                break

    Input.action_release("move_forward")
    await physics_frame

    var final_distance := Vector2(
        player.global_position.x - target.x,
        player.global_position.z - target.z
    ).length()
    return {
        "label": label,
        "start": [start.x, start.y, start.z],
        "target": [target.x, target.y, target.z],
        "end": [
            player.global_position.x,
            player.global_position.y,
            player.global_position.z
        ],
        "reached": reached or final_distance <= WAYPOINT_TOLERANCE,
        "final_distance": final_distance,
        "frames": used_frames,
        "floor_contact_ratio": (
            float(floor_frames) / float(maxi(used_frames, 1))
        ),
        "support_missing_total": support_missing_total,
        "support_missing_max_consecutive": support_missing_max,
        "support_colliders": support_colliders.keys(),
        "min_y": min_y,
        "fell_through": fell_through,
        "stalled": (
            not reached
            and final_distance > WAYPOINT_TOLERANCE
            and stall_frames > MAX_STALL_FRAMES
        ),
    }

func _assert_leg(prefix: String, leg: Dictionary) -> void:
    _check(prefix + "_reached", bool(leg["reached"]))
    _check(prefix + "_no_fall_through", not bool(leg["fell_through"]))
    _check(prefix + "_not_stalled", not bool(leg["stalled"]))
    _check(
        prefix + "_support_continuous",
        int(leg["support_missing_max_consecutive"]) <= 2
    )
    _check(
        prefix + "_floor_contact",
        float(leg["floor_contact_ratio"]) >= 0.35
    )

func _finish(scene: Node = null, legs: Array = []) -> void:
    _release_move_actions()
    var result := {
        "schema": "openazrael.kg001.r1_route",
        "version": 119,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": check_count,
        "failed": failures,
        "legs": legs,
        "scope": (
            "Candidate 3 R1/Object02 collision regression plus production "
            + "CharacterBody3D route traversal from spaview through audited "
            + "R1 floor waypoints toward the entcori side"
        ),
        "candidate3_bug_report": "openazrael_bugreport_1790007921_0054.zip",
    }
    print("OPENAZRAEL_KG001_R1_ROUTE_V119 " + JSON.stringify(result))
    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _run() -> void:
    if not ResourceLoader.exists(REQUIRED_ROOM):
        print("OPENAZRAEL_KG001_R1_ROUTE_V119 " + JSON.stringify({
            "schema": "openazrael.kg001.r1_route",
            "version": 119,
            "status": "BLOCKED_MISSING_ASSETS",
            "missing": [REQUIRED_ROOM]
        }))
        quit(2)
        return

    var state = root.get_node_or_null("DemoState")
    _check("demo_state_present", state != null)
    if state == null:
        _finish()
        return

    # Keep door gameplay out of this collision regression. Both authored R1
    # doors are pre-solved before room construction so their real visual and
    # child collision rotate to the open state via sync_from_state().
    state.reset_all()
    state.set_flag("R1Door1Open")
    state.acquire("well_key")
    state.set_flag("FR1DoorUnlocked")
    state.set_flag("R1Door2Open")

    var packed = load("res://main.tscn")
    _check("main_scene_load", packed != null)
    if packed == null:
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

    manager.transition_cooldown = 999.0
    manager.load_room("R1", false)
    await _settle(2)
    manager.call("_spawn_at_portal", "R1", "spaview")
    await _settle_physics(20)

    var object02 := _find_named(manager.current_room, "Object02__mesh")
    var object02_collision := _find_named(
        manager.current_room, "Collision_Object02"
    )
    _check("R1_Object02_visual_present", object02 is MeshInstance3D)
    _check(
        "R1_Object02_collision_present",
        object02_collision is StaticBody3D
    )
    if object02_collision is StaticBody3D:
        _check(
            "R1_Object02_collision_layer",
            int((object02_collision as StaticBody3D).collision_layer) == 1
        )
        _check(
            "R1_Object02_collision_mask",
            int((object02_collision as StaticBody3D).collision_mask) == 4
        )

    var bug_support: Dictionary = _floor_at(
        scene, player as CharacterBody3D, BUG_POINT, BUG_POINT.y
    )
    _check("R1_bug_point_support_present", not bug_support.is_empty())
    if not bug_support.is_empty():
        _check(
            "R1_bug_point_support_is_Object02",
            _collider_name(bug_support) == "Collision_Object02"
        )
        _check(
            "R1_bug_point_floor_height",
            absf(
                float((bug_support["position"] as Vector3).y)
                - BUG_POINT.y
            ) <= 0.75
        )

    var legs: Array = []

    var leg := await _walk_leg(
        scene, player as CharacterBody3D, BUG_POINT, "spaview_to_bug_point"
    )
    legs.append(leg)
    _assert_leg("R1_bug_leg", leg)

    leg = await _walk_leg(
        scene, player as CharacterBody3D,
        OBJECT02_FAR, "bug_point_across_Object02"
    )
    legs.append(leg)
    _assert_leg("R1_Object02_cross", leg)
    _check(
        "R1_Object02_cross_used_Object02_support",
        "Collision_Object02" in leg["support_colliders"]
    )

    leg = await _walk_leg(
        scene, player as CharacterBody3D,
        TUNNEL03_CENTER, "Object02_back_to_tunnel03"
    )
    legs.append(leg)
    _assert_leg("R1_Object02_return", leg)

    for index in range(ROUTE.size()):
        leg = await _walk_leg(
            scene,
            player as CharacterBody3D,
            ROUTE[index],
            "route_%02d" % index
        )
        legs.append(leg)
        _assert_leg("R1_route_%02d" % index, leg)
        if not bool(leg["reached"]) or bool(leg["fell_through"]):
            break

    _check(
        "R1_route_reached_tunnel07",
        Vector2(
            player.global_position.x - ROUTE[-1].x,
            player.global_position.z - ROUTE[-1].z
        ).length() <= WAYPOINT_TOLERANCE
    )

    _finish(scene, legs)
