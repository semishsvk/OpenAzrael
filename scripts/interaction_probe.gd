extends Node3D

@export var max_distance := 145.0
@onready var camera: Camera3D = get_parent()

func _find_interactive() -> Object:
    var from := camera.global_position
    var direction := -camera.global_transform.basis.z
    if DisplayServer.get_name() != "headless" and Input.mouse_mode == Input.MOUSE_MODE_VISIBLE:
        var mouse_pos := get_viewport().get_mouse_position()
        from = camera.project_ray_origin(mouse_pos)
        direction = camera.project_ray_normal(mouse_pos)
    var to := from + (direction * max_distance)
    var q := PhysicsRayQueryParameters3D.create(from, to)
    q.collision_mask = 2
    q.collide_with_areas = true
    q.collide_with_bodies = false
    var space := get_world_3d().direct_space_state
    var hit := space.intersect_ray(q)
    if hit:
        return hit.get("collider")

    # A normal interaction standoff can place the camera inside a large
    # authored Area3D (door interaction spheres are the main example).
    # Physics ray queries do not necessarily report the containing Area when
    # the ray origin starts inside it, so fall back to an overlap query at the
    # exact ray origin. This preserves ray-first cursor semantics and only
    # resolves the otherwise-unreachable containing interactive Area.
    var point_q := PhysicsPointQueryParameters3D.new()
    point_q.position = from
    point_q.collision_mask = 2
    point_q.collide_with_areas = true
    point_q.collide_with_bodies = false
    var overlaps := space.intersect_point(point_q, 16)
    for row in overlaps:
        var collider = row.get("collider")
        if collider != null and collider.has_method("interact"):
            return collider
    return null

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
