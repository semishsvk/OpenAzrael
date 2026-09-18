extends Node3D

var debug_visible := false
var _debug_nodes: Array[Node] = []
@onready var room_manager = get_node("../RoomManager")

func _ready() -> void:
    if room_manager.has_signal("room_changed"):
        room_manager.room_changed.connect(_on_room_changed)

func _v3(a: Array) -> Vector3:
    return Vector3(float(a[0]), float(a[1]), float(a[2]))

func _clear_debug_nodes() -> void:
    for node in _debug_nodes:
        if is_instance_valid(node):
            node.queue_free()
    _debug_nodes.clear()

func _rebuild() -> void:
    _clear_debug_nodes()
    if not debug_visible or room_manager.evidence.is_empty():
        return
    var room_id := String(room_manager.current_room_id)
    if not room_manager.evidence.has("rooms") or not room_manager.evidence["rooms"].has(room_id):
        return
    for trigger in room_manager.evidence["rooms"][room_id].get("triggers", []):
        var mn := _v3(trigger["bounds"][0])
        var mx := _v3(trigger["bounds"][1])
        var size := Vector3(
            max(0.5, abs(mx.x - mn.x)),
            max(0.5, abs(mx.y - mn.y)),
            max(0.5, abs(mx.z - mn.z))
        )
        var center := (mn + mx) * 0.5

        var box := BoxMesh.new()
        box.size = size
        var material := StandardMaterial3D.new()
        material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
        material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
        material.albedo_color = Color(1.0, 0.32, 0.08, 0.18)
        box.material = material

        var mesh := MeshInstance3D.new()
        mesh.name = "DebugTrigger_" + String(trigger.get("name", "unknown"))
        mesh.mesh = box
        add_child(mesh)
        mesh.global_position = center
        _debug_nodes.append(mesh)

        var label := Label3D.new()
        label.name = "DebugTriggerLabel_" + String(trigger.get("name", "unknown"))
        label.text = String(trigger.get("name", "unknown"))
        label.font_size = 28
        label.modulate = Color(1.0, 0.85, 0.65, 1.0)
        add_child(label)
        label.global_position = center + Vector3.UP * (size.y * 0.5 + 8.0)
        _debug_nodes.append(label)

func _on_room_changed(_room_id: String) -> void:
    if debug_visible:
        _rebuild()
    else:
        _clear_debug_nodes()

func _unhandled_key_input(event: InputEvent) -> void:
    if not event is InputEventKey or not event.pressed or event.echo:
        return
    if event.keycode == KEY_F6:
        debug_visible = not debug_visible
        _rebuild()
        CandidateDiagnostics.record_event("trigger_debug_visibility", {"visible": debug_visible})
        get_viewport().set_input_as_handled()
