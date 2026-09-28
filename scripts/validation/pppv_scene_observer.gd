extends RefCounted
class_name PPPVSceneObserver

var evidence: PPPVEvidenceBus

func _init(evidence_bus: PPPVEvidenceBus) -> void:
    evidence = evidence_bus

func _find_named(root: Node, wanted: String) -> Node:
    if String(root.name) == wanted:
        return root
    for child in root.get_children():
        var found := _find_named(child, wanted)
        if found != null:
            return found
    return null

func _has_property(source: Object, property_name: String) -> bool:
    for row in source.get_property_list():
        if String(row.get("name", "")) == property_name:
            return true
    return false

func _v3(value: Vector3) -> Array:
    return [value.x, value.y, value.z]

func _snapshot_node(root: Node, node_name: String) -> Dictionary:
    var node := _find_named(root, node_name)
    if node == null:
        return {
            "exists": false,
            "node": node_name
        }

    var out := {
        "exists": true,
        "node": node_name
    }
    if node is Node3D:
        var n := node as Node3D
        out["global_position"] = _v3(n.global_position)
        out["global_rotation"] = _v3(n.global_rotation)
    if _has_property(node, "visible"):
        out["visible"] = bool(node.get("visible"))
    return out

func capture(root: Node, specs: Array) -> Dictionary:
    var snapshots: Dictionary = {}
    for raw_spec in specs:
        if not raw_spec is Dictionary:
            continue
        var observation_id := String(
            raw_spec.get("observation_id", raw_spec.get("node", ""))
        )
        var node_name := String(raw_spec.get("node", ""))
        if observation_id.is_empty() or node_name.is_empty():
            continue
        snapshots[observation_id] = _snapshot_node(root, node_name)
    return snapshots

func _array_v3(value) -> Vector3:
    if not value is Array or value.size() < 3:
        return Vector3.ZERO
    return Vector3(float(value[0]), float(value[1]), float(value[2]))

func emit_changes(
    root: Node,
    specs: Array,
    before: Dictionary
) -> void:
    for raw_spec in specs:
        if not raw_spec is Dictionary:
            continue
        var observation_id := String(
            raw_spec.get("observation_id", raw_spec.get("node", ""))
        )
        var node_name := String(raw_spec.get("node", ""))
        if observation_id.is_empty() or node_name.is_empty():
            continue

        var before_row = before.get(
            observation_id,
            {"exists": false, "node": node_name}
        )
        if not before_row is Dictionary:
            before_row = {"exists": false, "node": node_name}
        var after_row := _snapshot_node(root, node_name)

        var before_exists := bool(before_row.get("exists", false))
        var after_exists := bool(after_row.get("exists", false))
        var position_delta := 0.0
        var rotation_delta := 0.0

        if before_exists and after_exists:
            if (
                before_row.has("global_position")
                and after_row.has("global_position")
            ):
                position_delta = _array_v3(
                    after_row["global_position"]
                ).distance_to(
                    _array_v3(before_row["global_position"])
                )
            if (
                before_row.has("global_rotation")
                and after_row.has("global_rotation")
            ):
                var before_rotation := _array_v3(
                    before_row["global_rotation"]
                )
                var after_rotation := _array_v3(
                    after_row["global_rotation"]
                )
                rotation_delta = Vector3(
                    absf(wrapf(
                        after_rotation.x - before_rotation.x,
                        -PI,
                        PI
                    )),
                    absf(wrapf(
                        after_rotation.y - before_rotation.y,
                        -PI,
                        PI
                    )),
                    absf(wrapf(
                        after_rotation.z - before_rotation.z,
                        -PI,
                        PI
                    ))
                ).length()

        var before_visible = before_row.get("visible")
        var after_visible = after_row.get("visible")
        var visibility_changed := (
            before_visible != null
            and after_visible != null
            and bool(before_visible) != bool(after_visible)
        )
        var position_changed := position_delta > 0.001
        var rotation_changed := rotation_delta > 0.001

        evidence.record("scene_change", {
            "observation_id": observation_id,
            "node": node_name,
            "before_exists": before_exists,
            "after_exists": after_exists,
            "position_changed": position_changed,
            "rotation_changed": rotation_changed,
            "transform_changed": position_changed or rotation_changed,
            "position_delta": position_delta,
            "rotation_delta": rotation_delta,
            "visibility_changed": visibility_changed,
            "before_visible": before_visible,
            "after_visible": after_visible
        })
