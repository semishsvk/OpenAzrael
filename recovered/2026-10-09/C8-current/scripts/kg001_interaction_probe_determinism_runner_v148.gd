extends SceneTree

const ProbeScript = preload("res://scripts/interaction_probe.gd")
const REPEATED_RUNS := 64

class TestInteractable:
    extends Area3D
    var interaction_count := 0

    func interact() -> void:
        interaction_count += 1

var failures: Array[String] = []
var checks := 0

func _check(name: String, ok: bool) -> void:
    checks += 1
    if not ok:
        failures.append(name)

func _make_area(name_value: String, priority: int, position: Vector3) -> TestInteractable:
    var area := TestInteractable.new()
    area.name = name_value
    area.collision_layer = 2
    area.collision_mask = 0
    area.position = position
    area.set_meta("interaction_priority", priority)
    var shape_node := CollisionShape3D.new()
    var shape := SphereShape3D.new()
    shape.radius = 20.0
    shape_node.shape = shape
    area.add_child(shape_node)
    return area

func _run() -> void:
    var world := Node3D.new()
    world.name = "InteractionProbeDeterminismWorld"
    root.add_child(world)

    var camera := Camera3D.new()
    camera.name = "Camera3D"
    camera.current = true
    world.add_child(camera)

    var probe = ProbeScript.new()
    probe.name = "InteractionProbe"
    probe.max_distance = 1.0
    camera.add_child(probe)

    # Both spheres contain the camera.  Their ray exit is farther away than the
    # one-unit primary ray, forcing the production inside-Area fallback.
    var lower := _make_area("OverlapLowerPriority", 10, Vector3(0.0, 0.0, -0.2))
    var preferred := _make_area("OverlapPreferred", 20, Vector3(0.0, 0.0, -0.4))
    world.add_child(lower)
    world.add_child(preferred)

    await process_frame
    await physics_frame
    await physics_frame

    var point_q := PhysicsPointQueryParameters3D.new()
    point_q.position = camera.global_position
    point_q.collision_mask = 2
    point_q.collide_with_areas = true
    point_q.collide_with_bodies = false
    var camera_overlaps := world.get_world_3d().direct_space_state.intersect_point(point_q, 16)
    var overlap_colliders: Array = camera_overlaps.map(func(row): return row.get("collider"))
    _check("both_areas_contain_camera",
        lower in overlap_colliders and preferred in overlap_colliders)
    var all_preferred := true
    for _i in range(REPEATED_RUNS):
        var selected = probe.current_interactive()
        if selected != preferred:
            all_preferred = false
            break
    _check("repeated_runtime_selection_is_stable", all_preferred)

    # Also reverse the raw overlap rows to prove fallback ordering itself does
    # not depend on PhysicsDirectSpaceState return order.
    var forward := [{"collider": lower}, {"collider": preferred}]
    var reverse := [{"collider": preferred}, {"collider": lower}]
    var direction := -camera.global_transform.basis.z
    _check("forward_order_prefers_explicit_priority",
        probe._select_overlap_candidate(forward, camera.global_position, direction) == preferred)
    _check("reverse_order_prefers_explicit_priority",
        probe._select_overlap_candidate(reverse, camera.global_position, direction) == preferred)

    preferred.set_meta("interaction_priority", 10)
    lower.set_meta("interaction_priority", 10)
    preferred.position = Vector3(0.0, 0.0, -2.0)
    lower.position = Vector3(2.0, 0.0, -2.0)
    var angle_forward := [{"collider": lower}, {"collider": preferred}]
    var angle_reverse := [{"collider": preferred}, {"collider": lower}]
    _check("angle_tiebreak_forward",
        probe._select_overlap_candidate(angle_forward, camera.global_position, direction) == preferred)
    _check("angle_tiebreak_reverse",
        probe._select_overlap_candidate(angle_reverse, camera.global_position, direction) == preferred)

    var out := {
        "schema": "openazrael.kg001.interaction_probe_determinism_runtime",
        "version": 148,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": checks,
        "failed": failures,
        "repeated_runs": REPEATED_RUNS,
        "selection_order": ["interaction_priority_desc", "view_angle_asc", "distance_asc", "stable_path_asc"],
        "raycast_remains_primary": true,
    }
    print("OPENAZRAEL_KG001_INTERACTION_PROBE_DETERMINISM_V148 " + JSON.stringify(out))
    world.queue_free()
    quit(0 if failures.is_empty() else 1)

func _initialize() -> void:
    call_deferred("_run")
