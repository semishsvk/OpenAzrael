extends RefCounted

const MANIFEST_PATH := "res://data/runtime_generated/demo_room_fidelity_v124.json"

static func load_manifest() -> Dictionary:
    if not FileAccess.file_exists(MANIFEST_PATH):
        return {}
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST_PATH))
    return parsed if parsed is Dictionary else {}

static func walk(node: Node, out: Array[Node]) -> void:
    out.append(node)
    for child in node.get_children():
        walk(child, out)

static func find_named(node: Node, wanted: String) -> Node:
    if String(node.name) == wanted:
        return node
    for child in node.get_children():
        var found := find_named(child, wanted)
        if found != null:
            return found
    return null

static func mesh_triangle_count(mesh: Mesh) -> int:
    var triangles := 0
    for surface in range(mesh.get_surface_count()):
        var arrays := mesh.surface_get_arrays(surface)
        var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
        var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
        triangles += int(indices.size() / 3) if not indices.is_empty() else int(vertices.size() / 3)
    return triangles

static func quantized_uv_sha(mi: MeshInstance3D, quantum: float) -> Dictionary:
    var values: Array[String] = []
    var uv_count := 0
    for surface in range(mi.mesh.get_surface_count()):
        var arrays := mi.mesh.surface_get_arrays(surface)
        var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
        uv_count += uvs.size()
        for uv in uvs:
            values.append(str(int(round(uv.x / quantum))))
            values.append(str(int(round(uv.y / quantum))))
    var context := HashingContext.new()
    context.start(HashingContext.HASH_SHA256)
    context.update(",".join(values).to_utf8_buffer())
    return {"count": uv_count, "sha256": context.finish().hex_encode()}

static func transform_values(t: Transform3D) -> Array:
    return [
        t.basis.x.x, t.basis.y.x, t.basis.z.x, t.origin.x,
        t.basis.x.y, t.basis.y.y, t.basis.z.y, t.origin.y,
        t.basis.x.z, t.basis.y.z, t.basis.z.z, t.origin.z,
        0.0, 0.0, 0.0, 1.0,
    ]

static func bounds_values(a: AABB) -> Array:
    return [
        a.position.x, a.position.y, a.position.z,
        a.end.x, a.end.y, a.end.z,
    ]

static func arrays_close(actual: Array, expected: Array, tolerance: float) -> bool:
    if actual.size() != expected.size():
        return false
    for i in range(actual.size()):
        if absf(float(actual[i]) - float(expected[i])) > tolerance:
            return false
    return true

static func room_mesh_map(room: Node) -> Dictionary:
    var nodes: Array[Node] = []
    walk(room, nodes)
    var out := {}
    for node in nodes:
        if node is MeshInstance3D and (node as MeshInstance3D).mesh != null:
            out[String(node.name)] = node
    return out
