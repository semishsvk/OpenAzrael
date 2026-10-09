extends CharacterBody3D

@export var walk_speed := 78.0
@export var sprint_multiplier := 1.65
@export var acceleration := 9.0
@export var gravity := 150.0
@export var eye_height := 32.0
@export var mouse_sensitivity := 0.0025

# Candidate 2 traversal fix. The recovered demo geometry contains discrete
# stair risers up to ~12.6 legacy units. CharacterBody3D slide motion does not
# automatically climb a vertical riser, so use a conservative collision-tested
# step assist rather than replacing the authored stairs with a synthetic ramp.
@export var max_step_height := 14.0
@export var step_probe_distance := 14.0
@export var step_clearance := 0.35
@export var step_surface_epsilon := 0.75
@export var traversal_safe_margin := 0.25

@onready var camera: Camera3D = $Camera3D
var pitch := 0.0

# R.EXE v190: global player-state +0x18 is initialized to 500 at 0x74688.
var legacy_health := 500

func apply_legacy_damage(amount: int, source: String = "") -> int:
    if amount <= 0:
        return legacy_health
    legacy_health = maxi(0, legacy_health - amount)
    CandidateDiagnostics.record_event("player_legacy_damage", {
        "source": source,
        "amount": amount,
        "health": legacy_health,
        "status": "SOURCE_HEALTH_EFFECT_APPLIED"
    })
    if legacy_health <= 0:
        CandidateDiagnostics.record_event("player_legacy_health", {
            "source": source,
            "health": 0,
            "status": "SOURCE_DEATH_THRESHOLD_REACHED"
        })
    return legacy_health

func legacy_health_value() -> int:
    return legacy_health

const STEP_DEBUG_LIMIT := 96
var step_debug_events: Array[Dictionary] = []

func _vec3_payload(value: Vector3) -> Array[float]:
    return [value.x, value.y, value.z]

func _record_step_debug(kind: String, payload: Dictionary = {}) -> void:
    var row := payload.duplicate(true)
    row["kind"] = kind
    row["player_position"] = _vec3_payload(global_position)
    step_debug_events.append(row)
    while step_debug_events.size() > STEP_DEBUG_LIMIT:
        step_debug_events.pop_front()

func clear_step_debug() -> void:
    step_debug_events.clear()

func step_debug_snapshot() -> Array[Dictionary]:
    var out: Array[Dictionary] = []
    for row in step_debug_events:
        out.append(row.duplicate(true))
    return out

func _ready() -> void:
    # Original demo keeps a free HUD cursor and uses held RMB for head look.
    # Headless PPPV keeps captured-style synthetic mouse motion unchanged.
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if DisplayServer.get_name() == "headless" else Input.MOUSE_MODE_VISIBLE
    # Keep support while descending the same discrete stair profiles that the
    # step-up helper can climb. Godot floor snapping only acts downward; it
    # therefore complements rather than replaces explicit step-up handling.
    floor_snap_length = max_step_height + 2.0
    safe_margin = traversal_safe_margin

func teleport_eye_to(eye_pos: Vector3, forward: Vector3) -> void:
    # RoomManager can place the player before this sibling's _ready runs.
    if camera == null:
        camera = get_node("Camera3D") as Camera3D
    global_position = eye_pos - Vector3.UP * eye_height
    velocity = Vector3.ZERO
    var f := Vector3(forward.x, 0.0, forward.z).normalized()
    if f.length_squared() < 0.001:
        f = Vector3.FORWARD
    rotation.y = atan2(-f.x, -f.z)
    pitch = clamp(asin(clamp(forward.normalized().y, -1.0, 1.0)), -1.35, 1.35)
    camera.rotation.x = pitch

func _unhandled_input(event: InputEvent) -> void:
    var allow_head_look := (
        DisplayServer.get_name() == "headless"
        or Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT)
    )
    if event is InputEventMouseMotion and allow_head_look:
        rotation.y -= event.relative.x * mouse_sensitivity
        pitch = clamp(pitch - event.relative.y * mouse_sensitivity, -1.35, 1.35)
        camera.rotation.x = pitch

func _step_floor_probe(direction: Vector3, horizontal_motion: Vector3) -> Dictionary:
    # Legacy tread winding is inconsistent and the two R8 stair profiles have
    # very different tread depths. Probe near-to-far and select the smallest
    # valid positive rise instead of trusting one long ray 14+ units ahead.
    var motion_distance := horizontal_motion.length()
    var probe_distances: Array[float] = [
        maxf(2.0, motion_distance + 1.0),
        maxf(4.0, motion_distance + 4.0),
        maxf(8.0, motion_distance + 8.0),
        maxf(step_probe_distance, motion_distance + 2.0),
    ]
    var best_hit: Dictionary = {}
    var best_step_height := 1.0e20

    for probe_distance in probe_distances:
        var probe_xz := global_position + direction * probe_distance
        var ray_from := Vector3(
            probe_xz.x,
            global_position.y + max_step_height + 2.0,
            probe_xz.z
        )
        var ray_to := Vector3(
            probe_xz.x,
            global_position.y - 2.0,
            probe_xz.z
        )
        var query := PhysicsRayQueryParameters3D.create(
            ray_from,
            ray_to,
            collision_mask
        )
        query.exclude = [get_rid()]
        query.hit_back_faces = true
        var hit := get_world_3d().direct_space_state.intersect_ray(query)
        if hit.is_empty():
            _record_step_debug("probe_miss", {
                "probe_distance": probe_distance,
                "ray_from": _vec3_payload(ray_from),
                "ray_to": _vec3_payload(ray_to),
            })
            continue

        var normal := hit.get("normal", Vector3.ZERO) as Vector3
        var hit_position := hit.get("position", global_position) as Vector3
        var step_height := hit_position.y - global_position.y
        var collider = hit.get("collider")
        _record_step_debug("probe_hit", {
            "probe_distance": probe_distance,
            "hit_position": _vec3_payload(hit_position),
            "normal": _vec3_payload(normal),
            "face_index": int(hit.get("face_index", -1)),
            "collider": String(collider.name) if collider is Node else "",
            "step_height": step_height,
        })

        # create_trimesh_shape(backface_collision=true) deliberately accepts
        # either legacy winding. The production tread oracle must do the same.
        if absf(normal.y) < cos(floor_max_angle):
            continue
        if step_height <= step_surface_epsilon or step_height > max_step_height + 0.05:
            continue
        if step_height < best_step_height:
            best_step_height = step_height
            best_hit = hit.duplicate(true)
            best_hit["_step_height"] = step_height
            best_hit["_probe_distance"] = probe_distance

    return best_hit

func _try_step_up(horizontal_motion: Vector3) -> bool:
    if not is_on_floor() or horizontal_motion.length_squared() < 0.000001:
        return false

    # Only engage stair assist when normal horizontal movement is actually
    # blocked. This prevents nearby higher floors/props from pulling the player
    # upward while walking freely.
    if not test_move(
        global_transform,
        horizontal_motion,
        null,
        traversal_safe_margin,
        false
    ):
        return false

    var direction := horizontal_motion.normalized()
    var floor_hit := _step_floor_probe(direction, horizontal_motion)
    if floor_hit.is_empty():
        _record_step_debug("step_reject_no_tread", {
            "horizontal_motion": _vec3_payload(horizontal_motion),
        })
        return false

    var normal := floor_hit.get("normal", Vector3.ZERO) as Vector3
    if absf(normal.y) < cos(floor_max_angle):
        _record_step_debug("step_reject_normal", {
            "normal": _vec3_payload(normal),
        })
        return false

    var step_height := float(floor_hit.get("_step_height", 0.0))
    if step_height <= step_surface_epsilon or step_height > max_step_height + 0.05:
        _record_step_debug("step_reject_height", {
            "step_height": step_height,
        })
        return false

    var lift := Vector3.UP * (step_height + step_clearance)

    # Do not teleport through a low ceiling or over an obstacle that remains
    # blocking at the raised height. Both parts are collision-tested before the
    # body transform is changed.
    if test_move(
        global_transform,
        lift,
        null,
        traversal_safe_margin,
        false
    ):
        _record_step_debug("step_reject_lift_blocked", {
            "step_height": step_height,
            "probe_distance": float(floor_hit.get("_probe_distance", 0.0)),
        })
        return false

    var raised := global_transform
    raised.origin += lift
    var settle_motion := direction * maxf(horizontal_motion.length(), 2.0)
    if test_move(
        raised,
        settle_motion,
        null,
        traversal_safe_margin,
        false
    ):
        _record_step_debug("step_reject_forward_blocked", {
            "step_height": step_height,
            "probe_distance": float(floor_hit.get("_probe_distance", 0.0)),
        })
        return false

    global_position += lift
    global_position += settle_motion
    velocity.y = 0.0
    apply_floor_snap()
    _record_step_debug("step_success", {
        "step_height": step_height,
        "probe_distance": float(floor_hit.get("_probe_distance", 0.0)),
        "normal": _vec3_payload(normal),
    })
    return true

func _physics_process(delta: float) -> void:
    var input2 := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
    var dir := (global_transform.basis * Vector3(input2.x, 0.0, input2.y))
    dir.y = 0.0
    dir = dir.normalized()
    var speed := walk_speed * (sprint_multiplier if Input.is_key_pressed(KEY_SHIFT) else 1.0)
    var target := dir * speed
    velocity.x = move_toward(velocity.x, target.x, acceleration * speed * delta)
    velocity.z = move_toward(velocity.z, target.z, acceleration * speed * delta)

    var horizontal_motion := Vector3(velocity.x, 0.0, velocity.z) * delta
    var stepped_up := _try_step_up(horizontal_motion)

    if stepped_up:
        velocity.y = 0.0
        var saved_horizontal := Vector2(velocity.x, velocity.z)
        velocity.x = 0.0
        velocity.z = 0.0
        move_and_slide()
        velocity.x = saved_horizontal.x
        velocity.z = saved_horizontal.y
        return
    elif not is_on_floor():
        velocity.y -= gravity * delta
    else:
        velocity.y = min(velocity.y, 0.0)

    move_and_slide()
