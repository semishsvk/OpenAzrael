extends SceneTree

const REQUIRED_ROOMS := {
    "R1": "res://assets/rooms/R1.glb",
    "R7": "res://assets/rooms/R7.glb",
    "R8": "res://assets/rooms/R8.glb",
}
const WALKABLE_NORMAL_ABS_Y_MIN := 0.65
const MIN_PROJECTED_TRIANGLE_AREA := 1.0
const SUPPORT_TOLERANCE_Y := 1.0
const RAY_HALF_HEIGHT := 3.0
const MAX_RECORDED_FAILURES := 100

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
    "TONG6": true,
    "r1p1": true,
    "r3t1": true,
    "r8t3": true,
    "r8t4": true,
    # Interactables/decorations can contain horizontal faces but are not
    # walkable floor semantics. Their collision may sit above the visual face.
    "save": true,
    "nibody": true,
    "well_pzpi1": true,
    "well_pzpi2": true,
    "r8s1": true,
    "door": true,
    "door01": true,
    "bible": true,
    "fontbot02": true,
}
const ROOM_EXEMPT := {
    "R7": {"Object02": true},
    # Source pane/shard overlays have horizontal edges but are not floors.
    # Production deliberately excludes them to keep the mirror opening usable.
    "R8": {"Object02": true, "mirror01": true, "broken3": true},
}

var failures: Array[String] = []
var failed_samples: Array = []
var room_summary: Dictionary = {}
var check_count := 0

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

func _support_at(scene: Node3D, point: Vector3) -> Dictionary:
    var query := PhysicsRayQueryParameters3D.create(
        point + Vector3.UP * RAY_HALF_HEIGHT,
        point + Vector3.DOWN * RAY_HALF_HEIGHT,
        1
    )
    query.hit_back_faces = true
    query.collide_with_areas = false
    return scene.get_world_3d().direct_space_state.intersect_ray(query)

func _record_failure(
    room_id: String,
    object_name: String,
    surface: int,
    triangle: int,
    sample_index: int,
    point: Vector3,
    hit: Dictionary,
    reason: String
) -> void:
    if failed_samples.size() >= MAX_RECORDED_FAILURES:
        return
    var collider_name := ""
    var hit_y = null
    if not hit.is_empty():
        var collider = hit.get("collider")
        collider_name = String(collider.name) if collider is Node else ""
        hit_y = float((hit["position"] as Vector3).y)
    failed_samples.append({
        "room": room_id,
        "object": object_name,
        "surface": surface,
        "triangle": triangle,
        "sample_index": sample_index,
        "point": [point.x, point.y, point.z],
        "collider": collider_name,
        "hit_y": hit_y,
        "reason": reason,
    })

func _audit_room(scene: Node3D, manager, room_id: String) -> void:
    manager.transition_cooldown = 999.0
    manager.load_room(room_id, false)
    await _settle(2)
    _check(room_id + "_loaded", manager.current_room != null)
    if manager.current_room == null:
        return

    var nodes: Array[Node] = []
    _walk(manager.current_room, nodes)
    var walkable_triangles := 0
    var samples := 0
    var missing_support := 0
    var support_below_visual := 0
    var meshes_sampled := 0

    for node in nodes:
        if not (node is MeshInstance3D):
            continue
        var mi := node as MeshInstance3D
        if mi.mesh == null:
            continue

        var object_name := _object_name_for_mesh(mi)
        var include_hidden_support := room_id == "R8" and object_name == "Object01"
        if not mi.visible and not include_hidden_support:
            continue
        if _is_explicit_exempt(room_id, object_name):
            continue

        var mesh_had_samples := false
        for surface in range(mi.mesh.get_surface_count()):
            var arrays := mi.mesh.surface_get_arrays(surface)
            var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
            var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
            var triangle_count := (
                int(indices.size() / 3)
                if not indices.is_empty()
                else int(vertices.size() / 3)
            )

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
                var projected_area := area * abs_y
                if abs_y < WALKABLE_NORMAL_ABS_Y_MIN:
                    continue
                if projected_area < MIN_PROJECTED_TRIANGLE_AREA:
                    continue

                walkable_triangles += 1
                mesh_had_samples = true

                # Four interior barycentric samples avoid fragile exact-edge rays
                # while covering the centroid and each vertex-side region.
                var sample_points := [
                    (a + b + c) / 3.0,
                    a * 0.60 + b * 0.20 + c * 0.20,
                    a * 0.20 + b * 0.60 + c * 0.20,
                    a * 0.20 + b * 0.20 + c * 0.60,
                ]
                for sample_index in range(sample_points.size()):
                    var point: Vector3 = sample_points[sample_index]
                    samples += 1
                    var hit := _support_at(scene, point)
                    if hit.is_empty():
                        missing_support += 1
                        _record_failure(
                            room_id, object_name, surface, tri, sample_index,
                            point, hit, "missing_collision_support"
                        )
                        continue
                    var hit_y := float((hit["position"] as Vector3).y)
                    # A collider above the sampled visual triangle means the
                    # player-space column is occupied/obstructed, not that the
                    # floor is missing. Only support materially BELOW the
                    # authored surface can allow a fall-through class bug.
                    if hit_y < point.y - SUPPORT_TOLERANCE_Y:
                        support_below_visual += 1
                        _record_failure(
                            room_id, object_name, surface, tri, sample_index,
                            point, hit, "collision_support_below_visual_floor"
                        )

        if mesh_had_samples:
            meshes_sampled += 1

    room_summary[room_id] = {
        "meshes_sampled": meshes_sampled,
        "walkable_triangles": walkable_triangles,
        "samples": samples,
        "missing_support": missing_support,
        "support_below_visual": support_below_visual,
    }
    _check(room_id + "_walkable_triangles_present", walkable_triangles > 0)
    _check(room_id + "_surface_samples_present", samples > 0)
    _check(room_id + "_no_missing_support", missing_support == 0)
    _check(room_id + "_no_support_below_visual", support_below_visual == 0)

func _finish(scene: Node = null) -> void:
    var result := {
        "schema": "openazrael.kg001.surface_collision_coverage",
        "version": 121,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": check_count,
        "failed": failures,
        "rooms": room_summary,
        "failed_samples": failed_samples,
        "policy": (
            "four interior physics-ray samples for every non-exempt floor-like "
            + "triangle in R1/R7/R8; no synthetic collision or player teleport"
        ),
    }
    print("OPENAZRAEL_KG001_SURFACE_COLLISION_V121 " + JSON.stringify(result))
    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _run() -> void:
    var missing := []
    for path in REQUIRED_ROOMS.values():
        if not ResourceLoader.exists(String(path)):
            missing.append(path)
    if not missing.is_empty():
        print("OPENAZRAEL_KG001_SURFACE_COLLISION_V121 " + JSON.stringify({
            "schema": "openazrael.kg001.surface_collision_coverage",
            "version": 121,
            "status": "BLOCKED_MISSING_ASSETS",
            "missing": missing,
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
        await _audit_room(scene, manager, room_id)

    _finish(scene)
