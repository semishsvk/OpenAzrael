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
@export var traversal_safe_margin := 0.25

@onready var camera: Camera3D = $Camera3D
var pitch := 0.0

func _ready() -> void:
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
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
    if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
        rotation.y -= event.relative.x * mouse_sensitivity
        pitch = clamp(pitch - event.relative.y * mouse_sensitivity, -1.35, 1.35)
        camera.rotation.x = pitch
    elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
        Input.mouse_mode = Input.MOUSE_MODE_VISIBLE if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED else Input.MOUSE_MODE_CAPTURED

func _step_floor_probe(direction: Vector3, horizontal_motion: Vector3) -> Dictionary:
    var probe_distance := step_probe_distance + horizontal_motion.length()
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
    return get_world_3d().direct_space_state.intersect_ray(query)

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
        return false

    var normal: Vector3 = floor_hit.get("normal", Vector3.ZERO)
    if normal.dot(Vector3.UP) < cos(floor_max_angle):
        return false

    var floor_y := float((floor_hit["position"] as Vector3).y)
    var step_height := floor_y - global_position.y
    if step_height <= 0.05 or step_height > max_step_height + 0.05:
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
        return false

    var raised := global_transform
    raised.origin += lift
    if test_move(
        raised,
        horizontal_motion,
        null,
        traversal_safe_margin,
        false
    ):
        return false

    global_position += lift
    velocity.y = 0.0
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
    elif not is_on_floor():
        velocity.y -= gravity * delta
    else:
        velocity.y = min(velocity.y, 0.0)

    move_and_slide()
