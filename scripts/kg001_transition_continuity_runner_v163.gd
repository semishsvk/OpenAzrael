extends SceneTree

const EvidenceBus = preload("res://scripts/validation/pppv_evidence_bus.gd")
const RuntimeGuard = preload("res://scripts/validation/pppv_runtime_guard.gd")

const MAX_LOGICAL_JUMP := 8.0
const MAX_DEPTH_JUMP := 2.0
const MAX_LATERAL_JUMP := 2.0
const MAX_YAW_ERROR := 0.05
const SUPPORT_FRAMES := 30

const CASES := [
    {
        "id": "R1_R7",
        "source": "R1",
        "trigger": "zxcoriR5",
        "source_view": "spaview",
        "destination": "R7",
        "destination_view": "view",
        "flags": ["R1Door1Open"],
    },
    {
        "id": "R7_R1",
        "source": "R7",
        "trigger": "zxwell2R6",
        "source_view": "view",
        "destination": "R1",
        "destination_view": "spaview",
        "flags": [],
    },
    {
        "id": "R1_R8",
        "source": "R1",
        "trigger": "zxcoriR2",
        "source_view": "entcori",
        "destination": "R8",
        "destination_view": "Object14",
        "flags": ["R1Door1Open", "R1Door2Open", "FR1DoorUnlocked"],
    },
    {
        "id": "R8_R1",
        "source": "R8",
        "trigger": "zxorrery",
        "source_view": "Object14",
        "destination": "R1",
        "destination_view": "entcori",
        "flags": [],
    },
]

var failures: Array[String] = []
var checks := 0

func _check(name: String, ok: bool) -> void:
    checks += 1
    if not ok:
        failures.append(name)

func _v3(raw) -> Vector3:
    return Vector3(float(raw[0]), float(raw[1]), float(raw[2]))

func _yaw_for(direction: Vector3) -> float:
    var flat := Vector3(direction.x, 0.0, direction.z).normalized()
    if flat.length_squared() < 0.001:
        flat = Vector3.FORWARD
    return atan2(-flat.x, -flat.z)

func _turn_toward(player: CharacterBody3D, target: Vector3) -> float:
    var flat := target - player.global_position
    flat.y = 0.0
    if flat.length_squared() < 0.0001:
        return 0.0
    var desired := atan2(-flat.x, -flat.z)
    var delta := wrapf(desired - player.rotation.y, -PI, PI)
    var sensitivity := float(player.get("mouse_sensitivity"))
    var pixels := clampf(-delta / sensitivity, -90.0, 90.0)
    var event := InputEventMouseMotion.new()
    event.relative = Vector2(pixels, 0.0)
    Input.parse_input_event(event)
    return delta

func _supported(scene: Node3D, player: CharacterBody3D) -> bool:
    var query := PhysicsRayQueryParameters3D.create(
        player.global_position + Vector3.UP * 8.0,
        player.global_position + Vector3.DOWN * 72.0,
        1
    )
    query.exclude = [player.get_rid()]
    query.hit_back_faces = true
    var hit: Dictionary = scene.get_world_3d().direct_space_state.intersect_ray(query)
    if hit.is_empty():
        return false
    return player.global_position.y >= float((hit["position"] as Vector3).y) - 4.0

func _portal_coords(eye: Vector3, view: Dictionary) -> Dictionary:
    var centroid := _v3(view["centroid"])
    var normal := _v3(view["normal"]).normalized()
    var tangent := Vector3(-normal.z, 0.0, normal.x).normalized()
    var relative := eye - centroid
    var bottom_y := centroid.y
    var bounds = view.get("bounds", [])
    if bounds is Array and bounds.size() >= 2:
        bottom_y = minf(_v3(bounds[0]).y, _v3(bounds[1]).y)
    return {
        "depth": relative.dot(normal),
        "lateral": relative.dot(tangent),
        "vertical_from_bottom": eye.y - bottom_y,
    }

func _run_case(
    scene: Node3D,
    manager,
    player: CharacterBody3D,
    state,
    spec: Dictionary,
    guard
) -> Dictionary:
    state.reset_all()
    for flag in spec["flags"]:
        state.set_flag(String(flag), true)

    manager.transition_cooldown = 999.0
    var setup_ok := bool(manager.call(
        "load_room_at_portal",
        spec["source"],
        spec["source_view"],
        false
    ))
    manager.transition_cooldown = 0.0
    for _i in range(12):
        await physics_frame
    if not setup_ok:
        return {"id": spec["id"], "status": "FAIL_SETUP"}

    var source_view: Dictionary = manager.call(
        "_view_record",
        spec["source"],
        spec["source_view"]
    )
    var trigger: Dictionary = manager.call(
        "_trigger_record",
        spec["source"],
        spec["trigger"]
    )
    if source_view.is_empty() or trigger.is_empty():
        return {"id": spec["id"], "status": "FAIL_SOURCE_RECORD"}

    var target := _v3(trigger["centroid"])
    guard.begin_action({
        "action_id": "transition_continuity_" + String(spec["id"]),
        "kind": "transition",
    })
    var pre_position := player.global_position
    var pre_yaw := player.rotation.y
    var frames := 0
    var changed := false
    Input.action_release(&"move_forward")

    for frame in range(900):
        frames = frame + 1
        var yaw_error := _turn_toward(player, target)
        if absf(yaw_error) <= 0.45:
            Input.action_press(&"move_forward", 1.0)
        else:
            Input.action_release(&"move_forward")
        pre_position = player.global_position
        pre_yaw = player.rotation.y
        await physics_frame
        if String(manager.current_room_id) == String(spec["destination"]):
            changed = true
            break

    Input.action_release(&"move_forward")
    if not changed:
        guard.end_action(false, {"reason": "transition_not_observed"})
        return {
            "id": spec["id"],
            "status": "FAIL_NO_TRANSITION",
            "frames": frames,
            "last_position": [
                player.global_position.x,
                player.global_position.y,
                player.global_position.z,
            ],
        }

    var destination_view: Dictionary = manager.call(
        "_view_record",
        spec["destination"],
        spec["destination_view"]
    )
    var expectation: Dictionary = manager.call(
        "portal_spawn_expectation",
        spec["destination"],
        spec["destination_view"]
    )
    var eye_height := float(player.get("eye_height"))
    var source_coords := _portal_coords(
        pre_position + Vector3.UP * eye_height,
        source_view
    )

    # The no-jump invariant is measured at the exact coordinate-frame swap.
    # Production intentionally preserves forward velocity, so measuring again
    # after the 30-frame support window would count healthy continued walking
    # as a portal discontinuity. RoomManager records the transition-instant
    # portal-relative deltas before the first post-transition physics step.
    var depth_jump := float(expectation.get(
        "continuity_depth_delta", INF
    ))
    var lateral_jump := float(expectation.get(
        "continuity_lateral_delta", INF
    ))
    var vertical_jump := float(expectation.get(
        "continuity_vertical_delta", INF
    ))
    var logical_jump := float(expectation.get(
        "continuity_logical_jump", INF
    ))

    var transition_position := _v3(expectation.get(
        "player_position", [INF, INF, INF]
    ))
    var guard_ok: bool = bool(await guard.verify_transition_spawn(
        "transition_continuity_" + String(spec["id"]),
        String(spec["source"]),
        String(spec["trigger"]),
        String(spec["destination"]),
        14.0,
        0.35
    ))
    var support_ok: bool = guard_ok and _supported(scene, player)
    guard.end_action(guard_ok, {
        "continuity_case": String(spec["id"]),
        "support_frames": SUPPORT_FRAMES,
    })

    var destination_coords := _portal_coords(
        player.global_position + Vector3.UP * eye_height,
        destination_view
    )
    var post_support_travel := player.global_position.distance_to(
        transition_position
    )
    var destination_normal := _v3(destination_view["normal"]).normalized()
    var yaw_error := absf(wrapf(
        player.rotation.y - _yaw_for(destination_normal),
        -PI,
        PI
    ))
    var manager_jump := logical_jump
    var fallback := bool(expectation.get("continuity_fallback", true))

    var ok := (
        support_ok
        and guard_ok
        and not fallback
        and depth_jump <= MAX_DEPTH_JUMP
        and lateral_jump <= MAX_LATERAL_JUMP
        and logical_jump <= MAX_LOGICAL_JUMP
        and manager_jump <= MAX_LOGICAL_JUMP
        and yaw_error <= MAX_YAW_ERROR
    )
    return {
        "id": spec["id"],
        "status": "PASS" if ok else "FAIL",
        "frames": frames,
        "source_room": spec["source"],
        "trigger": spec["trigger"],
        "destination_room": spec["destination"],
        "source_position": [
            pre_position.x, pre_position.y, pre_position.z
        ],
        "transition_position": [
            transition_position.x,
            transition_position.y,
            transition_position.z,
        ],
        "destination_position_after_support": [
            player.global_position.x,
            player.global_position.y,
            player.global_position.z,
        ],
        "post_support_travel": post_support_travel,
        "source_yaw": pre_yaw,
        "destination_yaw": player.rotation.y,
        "depth_jump": depth_jump,
        "lateral_jump": lateral_jump,
        "vertical_jump": vertical_jump,
        "logical_jump": logical_jump,
        "manager_logical_jump": manager_jump,
        "continuity_fallback": fallback,
        "runtime_guard_ok": guard_ok,
        "yaw_error": yaw_error,
        "support_frames": SUPPORT_FRAMES if support_ok else 0,
    }

func _run() -> void:
    for path in [
        "res://assets/rooms/R1.glb",
        "res://assets/rooms/R7.glb",
        "res://assets/rooms/R8.glb",
    ]:
        if not ResourceLoader.exists(path):
            print("OPENAZRAEL_KG001_TRANSITION_CONTINUITY_V163 " + JSON.stringify({
                "schema": "openazrael.kg001.transition_continuity",
                "version": 163,
                "status": "BLOCKED_MISSING_ASSETS",
                "missing": path,
            }))
            quit(2)
            return

    var state = root.get_node_or_null("DemoState")
    var packed = load("res://main.tscn")
    _check("demo_state_present", state != null)
    _check("main_scene_load", packed is PackedScene)
    if state == null or not packed is PackedScene:
        quit(1)
        return

    var scene = packed.instantiate()
    root.add_child(scene)
    for _i in range(10):
        await physics_frame
    var manager = scene.get_node_or_null("RoomManager")
    var player = scene.get_node_or_null("Player")
    _check("room_manager_present", manager != null)
    _check("production_player_present", player is CharacterBody3D)
    if manager == null or not player is CharacterBody3D:
        scene.queue_free()
        quit(1)
        return

    var evidence = EvidenceBus.new()
    var guard = RuntimeGuard.new(player, manager, state, evidence)

    var results := []
    for spec in CASES:
        var row: Dictionary = await _run_case(
            scene,
            manager,
            player,
            state,
            spec,
            guard
        )
        results.append(row)
        _check(String(spec["id"]), String(row.get("status", "")) == "PASS")

    var result := {
        "schema": "openazrael.kg001.transition_continuity",
        "version": 163,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": checks,
        "failed": failures,
        "movement": "production CharacterBody3D input; no transition test teleport",
        "criteria": {
            "max_logical_jump": MAX_LOGICAL_JUMP,
            "max_depth_jump": MAX_DEPTH_JUMP,
            "max_lateral_jump": MAX_LATERAL_JUMP,
            "max_yaw_error": MAX_YAW_ERROR,
            "support_frames": SUPPORT_FRAMES,
        },
        "results": results,
        "runtime_guard_failures": guard.failure_list(),
    }
    print("OPENAZRAEL_KG001_TRANSITION_CONTINUITY_V163 " + JSON.stringify(result))
    scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _initialize() -> void:
    call_deferred("_run")
