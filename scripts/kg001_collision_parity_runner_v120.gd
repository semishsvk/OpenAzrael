extends SceneTree

const REQUIRED_ROOMS := {
    "R1": "res://assets/rooms/R1.glb",
    "R7": "res://assets/rooms/R7.glb",
    "R8": "res://assets/rooms/R8.glb",
}
const WALKABLE_NORMAL_ABS_Y_MIN := 0.65
const MIN_TOTAL_PROJECTED_AREA := 150.0

const GLOBAL_EXEMPT := {
    "view": true,
    "spaview": true,
    "entcori": true,
    "Object14": true,
    "Object03": true,
    "zxwater": true,
    "tapestry1": true,
    "tapestry3": true,
    "tapestry4": true,
}
const ROOM_EXEMPT := {
    "R7": {"Object02": true},
    "R8": {"Object02": true},
}

var failures: Array[String] = []
var check_count := 0
var rows: Array = []

func _initialize() -> void:
    call_deferred("_run")

func _check(name: String, condition: bool) -> void:
    check_count += 1
    if not condition:
        failures.append(name)

func _settle(frames: int = 3) -> void:
    for _i in range(frames):
        await process_frame

func _walk(node: Node, out: Array[Node]) -> void:
    out.append(node)
    for child in node.get_children():
        _walk(child, out)

func _object_name_for_mesh(mi: MeshInstance3D) -> String:
    var name := String(mi.name)
    if name.ends_with("__mesh"):
        return name.substr(0, name.length() - 6)
    return name

func _is_explicit_exempt(room_id: String, object_name: String) -> bool:
    if object_name.begins_with("ZQ"):
        return true
    if GLOBAL_EXEMPT.has(object_name):
        return true
    var room_map: Dictionary = ROOM_EXEMPT.get(room_id, {})
    return room_map.has(object_name)

func _walkable_projected_area(mi: MeshInstance3D) -> Dictionary:
    var total := 0.0
    var triangles := 0
    var max_triangle := 0.0
    if mi.mesh == null:
        return {
            "total_projected_area": total,
            "walkable_triangles": triangles,
            "max_projected_triangle_area": max_triangle,
        }

    for surface in range(mi.mesh.get_surface_count()):
        var arrays := mi.mesh.surface_get_arrays(surface)
        var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
        var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
        var triangle_count := int(indices.size() / 3) if not indices.is_empty() else int(vertices.size() / 3)
        for tri in range(triangle_count):
            var ia := indices[tri * 3] if not indices.is_empty() else tri * 3
            var ib := indices[tri * 3 + 1] if not indices.is_empty() else tri * 3 + 1
            var ic := indices[tri * 3 + 2] if not indices.is_empty() else tri * 3 + 2

            var a := mi.global_transform * vertices[ia]
            var b := mi.global_transform * vertices[ib]
            var c := mi.global_transform * vertices[ic]
            var cross := (b - a).cross(c - a)
            var area := cross.length() * 0.5
            if area <= 0.001:
                continue
            var normal := cross.normalized()
            var abs_y := absf(normal.y)
            if abs_y < WALKABLE_NORMAL_ABS_Y_MIN:
                continue
            var projected := area * abs_y
            total += projected
            triangles += 1
            max_triangle = maxf(max_triangle, projected)

    return {
        "total_projected_area": total,
        "walkable_triangles": triangles,
        "max_projected_triangle_area": max_triangle,
    }

func _collision_child(mi: MeshInstance3D, object_name: String) -> StaticBody3D:
    var candidate := mi.get_node_or_null("Collision_" + object_name)
    return candidate as StaticBody3D if candidate is StaticBody3D else null

func _collision_shape(body: StaticBody3D) -> CollisionShape3D:
    if body == null:
        return null
    for child in body.get_children():
        if child is CollisionShape3D:
            return child as CollisionShape3D
    return null

func _audit_room(manager, room_id: String) -> void:
    manager.transition_cooldown = 999.0
    manager.load_room(room_id, false)
    await _settle(2)
    _check(room_id + "_loaded", manager.current_room != null)
    if manager.current_room == null:
        return

    var nodes: Array[Node] = []
    _walk(manager.current_room, nodes)
    var candidate_count := 0

    for node in nodes:
        if not (node is MeshInstance3D):
            continue
        var mi := node as MeshInstance3D
        if mi.mesh == null or not mi.visible:
            continue

        var object_name := _object_name_for_mesh(mi)
        var geom := _walkable_projected_area(mi)
        var projected_area := float(geom["total_projected_area"])
        var floor_like := projected_area >= MIN_TOTAL_PROJECTED_AREA
        if not floor_like:
            continue

        candidate_count += 1
        var exempt := _is_explicit_exempt(room_id, object_name)
        var body := _collision_child(mi, object_name)
        var cs := _collision_shape(body)
        var shape = cs.shape if cs != null else null
        var reasons: Array[String] = []

        if not exempt:
            if body == null:
                reasons.append("missing_collision_body")
            else:
                if int(body.collision_layer) != 1:
                    reasons.append("collision_layer")
                if int(body.collision_mask) != 4:
                    reasons.append("collision_mask")
                if not (shape is ConcavePolygonShape3D):
                    reasons.append("shape_not_concave_trimesh")
                elif not (shape as ConcavePolygonShape3D).backface_collision:
                    reasons.append("backface_collision_disabled")

        var row := {
            "room": room_id,
            "mesh": String(mi.name),
            "object": object_name,
            "projected_walkable_area": projected_area,
            "walkable_triangles": int(geom["walkable_triangles"]),
            "max_projected_triangle_area": float(geom["max_projected_triangle_area"]),
            "explicit_exempt": exempt,
            "collision_body": String(body.name) if body != null else "",
            "collision_layer": int(body.collision_layer) if body != null else 0,
            "collision_mask": int(body.collision_mask) if body != null else 0,
            "shape": shape.get_class() if shape != null else "",
            "backface_collision": (
                (shape as ConcavePolygonShape3D).backface_collision
                if shape is ConcavePolygonShape3D
                else false
            ),
            "fail_reasons": reasons,
        }
        rows.append(row)

        if not exempt:
            _check(
                "%s_%s_collision_parity" % [room_id, object_name],
                reasons.is_empty()
            )

        if room_id == "R1" and object_name == "Object02":
            _check("R1_Object02_generic_floor_detected", floor_like)
            _check("R1_Object02_not_exempt", not exempt)
            _check(
                "R1_Object02_collision_present",
                body != null and String(body.name) == "Collision_Object02"
            )

    _check(room_id + "_floor_like_candidates_present", candidate_count > 0)

func _finish(scene: Node = null) -> void:
    var non_exempt_failures: Array = []
    for row in rows:
        if not (row is Dictionary):
            continue
        var reasons_value = row.get("fail_reasons", [])
        var row_failed := (
            reasons_value is Array and not reasons_value.is_empty()
        )
        if not bool(row.get("explicit_exempt", false)) and row_failed:
            non_exempt_failures.append(row)

    var result := {
        "schema": "openazrael.kg001.collision_parity",
        "version": 120,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": check_count,
        "failed": failures,
        "floor_like_meshes": rows.size(),
        "non_exempt_failures": non_exempt_failures,
        "rows": rows,
        "scope": (
            "generic R1/R7/R8 visible floor-like mesh versus runtime world "
            + "collision parity; independent explicit semantic exemptions"
        )
    }
    print("OPENAZRAEL_KG001_COLLISION_PARITY_V120 " + JSON.stringify(result))
    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _run() -> void:
    var missing: Array[String] = []
    for room_id in REQUIRED_ROOMS.keys():
        var path := String(REQUIRED_ROOMS[room_id])
        if not ResourceLoader.exists(path):
            missing.append(path)
    if not missing.is_empty():
        print("OPENAZRAEL_KG001_COLLISION_PARITY_V120 " + JSON.stringify({
            "schema": "openazrael.kg001.collision_parity",
            "version": 120,
            "status": "BLOCKED_MISSING_ASSETS",
            "missing": missing
        }))
        quit(2)
        return

    var packed = load("res://main.tscn")
    _check("main_scene_load", packed != null)
    if packed == null:
        _finish()
        return

    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle(3)

    var manager = scene.get_node_or_null("RoomManager")
    _check("room_manager_present", manager != null)
    if manager == null:
        _finish(scene)
        return

    for room_id in ["R1", "R7", "R8"]:
        await _audit_room(manager, room_id)

    _finish(scene)
