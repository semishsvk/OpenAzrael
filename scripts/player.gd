extends CharacterBody3D

@export var walk_speed := 78.0
@export var sprint_multiplier := 1.65
@export var acceleration := 9.0
@export var gravity := 150.0
@export var eye_height := 32.0
@export var mouse_sensitivity := 0.0025

@onready var camera: Camera3D = $Camera3D
var pitch := 0.0

func _ready() -> void:
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func teleport_eye_to(eye_pos: Vector3, forward: Vector3) -> void:
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

func _physics_process(delta: float) -> void:
    var input2 := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
    var dir := (global_transform.basis * Vector3(input2.x, 0.0, input2.y))
    dir.y = 0.0
    dir = dir.normalized()
    var speed := walk_speed * (sprint_multiplier if Input.is_key_pressed(KEY_SHIFT) else 1.0)
    var target := dir * speed
    velocity.x = move_toward(velocity.x, target.x, acceleration * speed * delta)
    velocity.z = move_toward(velocity.z, target.z, acceleration * speed * delta)
    if not is_on_floor():
        velocity.y -= gravity * delta
    else:
        velocity.y = min(velocity.y, 0.0)
    move_and_slide()
