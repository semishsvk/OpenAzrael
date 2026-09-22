extends SceneTree

const REQUIRED := {
    "R1": {
        "path": "res://assets/rooms/R1.glb",
        "bytes": 535916,
        "sha256": "8a35e60b3f26d1fa656653cc7d3d5875c0927c77882189a6f073bf7ed16a3a6c",
        "mesh_instances": 69,
        "triangles": 593,
        "critical_visible": ["save__mesh", "Object02__mesh", "wall10__mesh", "floorbit03__mesh"],
    },
    "R7": {
        "path": "res://assets/rooms/R7.glb",
        "bytes": 790640,
        "sha256": "3c2aa95c4612c550edf8729299f7fe3e992308c2ae9e051b01973f6f48db7971",
        "mesh_instances": 48,
        "triangles": 689,
        "critical_visible": ["well_floor__mesh", "nibody__mesh", "pipes2well__mesh"],
    },
    "R8": {
        "path": "res://assets/rooms/R8.glb",
        "bytes": 1341944,
        "sha256": "c36c69baaaff414e12c1c64c0c4e1e9febebf321fb1aa8f888e601326ff5f476",
        "mesh_instances": 87,
        "triangles": 1050,
        "critical_visible": ["bath__BAPFLOOR", "stairs__STAIR2", "broken3__mesh", "bible__mesh"],
    },
}

var failures: Array[String] = []
var check_count := 0
var direct_summary: Dictionary = {}
var runtime_summary: Dictionary = {}

func _initialize() -> void:
    call_deferred("_run")

func _check(name: String, condition: bool) -> void:
    check_count += 1
    if not condition:
        failures.append(name)

func _settle(frames: int = 2) -> void:
    for _i in range(frames):
        await process_frame

func _walk(node: Node, out: Array[Node]) -> void:
    out.append(node)
    for child in node.get_children():
        _walk(child, out)

func _find_named(node: Node, wanted: String) -> Node:
    if String(node.name) == wanted:
        return node
    for child in node.get_children():
        var found := _find_named(child, wanted)
        if found != null:
            return found
    return null

func _mesh_triangle_count(mesh: Mesh) -> int:
    var triangles := 0
    for surface in range(mesh.get_surface_count()):
        var arrays := mesh.surface_get_arrays(surface)
        var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
        var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
        triangles += int(indices.size() / 3) if not indices.is_empty() else int(vertices.size() / 3)
    return triangles

func _scene_geometry_summary(root_node: Node) -> Dictionary:
    var nodes: Array[Node] = []
    _walk(root_node, nodes)
    var mesh_count := 0
    var triangles := 0
    var names: Array[String] = []
    for node in nodes:
        if not (node is MeshInstance3D):
            continue
        var mi := node as MeshInstance3D
        if mi.mesh == null:
            continue
        mesh_count += 1
        triangles += _mesh_triangle_count(mi.mesh)
        names.append(String(mi.name))
    names.sort()
    return {
        "mesh_instances": mesh_count,
        "triangles": triangles,
        "mesh_names": names,
    }

func _sha256(path: String) -> String:
    var bytes := FileAccess.get_file_as_bytes(path)
    var context := HashingContext.new()
    var err := context.start(HashingContext.HASH_SHA256)
    if err != OK:
        return ""
    err = context.update(bytes)
    if err != OK:
        return ""
    return context.finish().hex_encode()

func _audit_direct(room_id: String, spec: Dictionary) -> void:
    var path := String(spec["path"])
    _check(room_id + "_resource_exists", ResourceLoader.exists(path))
    if not ResourceLoader.exists(path):
        return

    var packed = load(path)
    _check(room_id + "_packed_scene", packed is PackedScene)
    if not packed is PackedScene:
        return

    var room = packed.instantiate()
    root.add_child(room)
    await _settle(1)

    var summary := _scene_geometry_summary(room)
    direct_summary[room_id] = summary
    _check(room_id + "_direct_mesh_count", int(summary["mesh_instances"]) == int(spec["mesh_instances"]))
    _check(room_id + "_direct_triangle_count", int(summary["triangles"]) == int(spec["triangles"]))

    for wanted in spec["critical_visible"]:
        var node := _find_named(room, String(wanted))
        _check(room_id + "_direct_has_" + String(wanted), node is MeshInstance3D)
        if node is MeshInstance3D:
            _check(room_id + "_direct_visible_" + String(wanted), (node as MeshInstance3D).is_visible_in_tree())

    room.queue_free()
    await _settle(1)

func _audit_runtime(scene: Node, manager, room_id: String, spec: Dictionary) -> void:
    manager.transition_cooldown = 999.0
    manager.load_room(room_id, false)
    await _settle(2)
    _check(room_id + "_runtime_loaded", manager.current_room != null)
    if manager.current_room == null:
        return

    var summary := _scene_geometry_summary(manager.current_room)
    runtime_summary[room_id] = summary
    _check(room_id + "_runtime_mesh_count", int(summary["mesh_instances"]) == int(spec["mesh_instances"]))
    _check(room_id + "_runtime_triangle_count", int(summary["triangles"]) == int(spec["triangles"]))

    for wanted in spec["critical_visible"]:
        var node := _find_named(manager.current_room, String(wanted))
        _check(room_id + "_runtime_has_" + String(wanted), node is MeshInstance3D)
        if node is MeshInstance3D:
            _check(room_id + "_runtime_visible_" + String(wanted), (node as MeshInstance3D).is_visible_in_tree())

func _finish(scene: Node = null) -> void:
    var result := {
        "schema": "openazrael.kg001.geometry_render_parity",
        "version": 122,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": check_count,
        "failed": failures,
        "direct_import": direct_summary,
        "runtime_load": runtime_summary,
        "critical_r1_rock_mesh": "save__mesh",
        "policy": "source-derived imported/runtime mesh and triangle parity + critical static visibility; generated GLB byte hashes are dynamic and separately receipted",
    }
    print("OPENAZRAEL_KG001_GEOMETRY_RENDER_PARITY_V122 " + JSON.stringify(result))
    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _run() -> void:
    var missing := []
    for spec in REQUIRED.values():
        var path := String(spec["path"])
        if not ResourceLoader.exists(path):
            missing.append(path)
    if not missing.is_empty():
        print("OPENAZRAEL_KG001_GEOMETRY_RENDER_PARITY_V122 " + JSON.stringify({
            "schema": "openazrael.kg001.geometry_render_parity",
            "version": 122,
            "status": "BLOCKED_MISSING_ASSETS",
            "missing": missing,
        }))
        quit(2)
        return

    for room_id in ["R1", "R7", "R8"]:
        await _audit_direct(room_id, REQUIRED[room_id])

    var packed = load("res://main.tscn")
    _check("main_scene_load", packed is PackedScene)
    if not packed is PackedScene:
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
        await _audit_runtime(scene, manager, room_id, REQUIRED[room_id])

    _finish(scene)
