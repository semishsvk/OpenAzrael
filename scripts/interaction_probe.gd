extends Node3D

@export var max_distance := 145.0
@onready var camera: Camera3D = get_parent()

func _find_interactive() -> Object:
    var from := camera.global_position
    var to := from + (-camera.global_transform.basis.z * max_distance)
    var q := PhysicsRayQueryParameters3D.create(from, to)
    q.collision_mask = 2
    q.collide_with_areas = true
    q.collide_with_bodies = false
    var hit := get_world_3d().direct_space_state.intersect_ray(q)
    return hit.get("collider") if hit else null

func current_interactive() -> Object:
    return _find_interactive()

func current_cursor_id() -> String:
    var target := _find_interactive()
    if target == null:
        return "POINTER"
    if target.has_method("interaction_cursor_id"):
        var value := String(target.call("interaction_cursor_id")).strip_edges().to_upper()
        return value if not value.is_empty() else "USE"
    return "USE"

func _unhandled_input(event: InputEvent) -> void:
    if event.is_action_pressed("interact"):
        var n := _find_interactive()
        if n != null and n.has_method("interact"):
            CandidateDiagnostics.record_interaction(String(n.name))
            n.interact()
        else:
            CandidateDiagnostics.record_event("interaction_miss", {})
