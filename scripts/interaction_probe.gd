extends Node3D

@export var max_distance := 145.0
@onready var camera: Camera3D = get_parent()

func _interaction_priority(collider: Object) -> int:
    if collider == null:
        return 0
    if collider.has_method("interaction_priority"):
        return int(collider.call("interaction_priority"))
    if collider is Node and collider.has_meta("interaction_priority"):
        return int(collider.get_meta("interaction_priority", 0))
    return 0

func _stable_node_path(collider: Object) -> String:
    if collider is Node:
        return String(collider.get_path())
    return String(collider)

func _overlap_candidate(collider: Object, from: Vector3, direction: Vector3) -> Dictionary:
    var target_position := from
    if collider is Node3D:
        target_position = collider.global_position
    var delta := target_position - from
    var distance := delta.length()
    var angle_error := 0.0
    if distance > 0.000001:
        var view := direction.normalized()
        angle_error = acos(clampf(view.dot(delta / distance), -1.0, 1.0))
    return {
        "collider": collider,
        "priority": _interaction_priority(collider),
        "angle_error": angle_error,
        "distance": distance,
        "stable_path": _stable_node_path(collider),
    }

func _candidate_less(a: Dictionary, b: Dictionary) -> bool:
    if int(a["priority"]) != int(b["priority"]):
        return int(a["priority"]) > int(b["priority"])
    if not is_equal_approx(float(a["angle_error"]), float(b["angle_error"])):
        return float(a["angle_error"]) < float(b["angle_error"])
    if not is_equal_approx(float(a["distance"]), float(b["distance"])):
        return float(a["distance"]) < float(b["distance"])
    return String(a["stable_path"]) < String(b["stable_path"])

func _select_overlap_candidate(overlaps: Array, from: Vector3, direction: Vector3) -> Object:
    var candidates: Array[Dictionary] = []
    for row in overlaps:
        if not row is Dictionary:
            continue
        var collider = row.get("collider")
        if collider != null and collider.has_method("interact"):
            candidates.append(_overlap_candidate(collider, from, direction))
    if candidates.is_empty():
        return null
    candidates.sort_custom(_candidate_less)
    return candidates[0]["collider"]

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

    # A normal interaction standoff can place the camera inside one or more
    # authored Area3D volumes.  Ray queries need not report a containing Area
    # when the origin starts inside it.  The fallback therefore considers every
    # interactable overlap and sorts deterministically: explicit priority,
    # view-angle error, distance, then stable scene-tree path.
    var point_q := PhysicsPointQueryParameters3D.new()
    point_q.position = from
    point_q.collision_mask = 2
    point_q.collide_with_areas = true
    point_q.collide_with_bodies = false
    var overlaps := space.intersect_point(point_q, 16)
    return _select_overlap_candidate(overlaps, from, direction)

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
