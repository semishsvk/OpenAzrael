extends Camera3D

@export var speed := 60.0
@export var fast_multiplier := 3.0
@export var mouse_sensitivity := 0.0025
var pitch := 0.0

func _ready() -> void:
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func teleport_to(pos: Vector3, forward: Vector3) -> void:
    global_position = pos
    var f := forward.normalized()
    if f.length_squared() < 0.001:
        f = Vector3.FORWARD
    look_at(global_position + f * 100.0, Vector3.UP)
    pitch = rotation.x

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
        rotate_y(-event.relative.x * mouse_sensitivity)
        pitch = clamp(pitch - event.relative.y * mouse_sensitivity, -1.5, 1.5)
        rotation.x = pitch
    elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
        Input.mouse_mode = Input.MOUSE_MODE_VISIBLE if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED else Input.MOUSE_MODE_CAPTURED

func _process(delta: float) -> void:
    var v := Vector3.ZERO
    v.z = Input.get_axis("move_forward", "move_back")
    v.x = Input.get_axis("move_left", "move_right")
    v.y = Input.get_axis("move_down", "move_up")
    if v.length_squared() > 0:
        v = v.normalized()
        var s := speed * (fast_multiplier if Input.is_key_pressed(KEY_SHIFT) else 1.0)
        global_position += global_transform.basis * v * s * delta
