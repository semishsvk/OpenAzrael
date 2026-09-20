extends SceneTree

const REQUIRED_ROOM := "res://assets/rooms/R7.glb"
const WATCH_RADIUS := 140.0
const OBSERVE_FRAMES := 60

var failures: Array[String] = []
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

func _find_named(node: Node, wanted: String) -> Node:
    if String(node.name) == wanted:
        return node
    for child in node.get_children():
        var found := _find_named(child, wanted)
        if found != null:
            return found
    return null

func _collect_local_nodes(
    node: Node,
    center: Vector3,
    out: Dictionary
) -> void:
    if node is Node3D:
        var n := node as Node3D
        if n.global_position.distance_to(center) <= WATCH_RADIUS:
            out[n.get_instance_id()] = {
                "node": n,
                "name": String(n.name),
                "transform": n.global_transform,
                "visible": n.visible
            }
    for child in node.get_children():
        _collect_local_nodes(child, center, out)

func _snapshot_local_nodes(room: Node3D, center: Vector3) -> Dictionary:
    var out: Dictionary = {}
    _collect_local_nodes(room, center, out)
    return out

func _transform_changed(a: Transform3D, b: Transform3D) -> bool:
    return (
        a.origin.distance_to(b.origin) > 0.01
        or not a.basis.is_equal_approx(b.basis)
    )

func _observe_animation_activity(
    room: Node3D,
    center: Vector3,
    baseline: Dictionary
) -> Dictionary:
    var changed_frames: Array[int] = []
    var transform_change_frames: Array[int] = []
    var visibility_change_frames: Array[int] = []
    var new_node_frames: Array[int] = []
    var changed_names: Dictionary = {}

    for frame in range(OBSERVE_FRAMES):
        await process_frame
        var current := _snapshot_local_nodes(room, center)
        var frame_changed := false
        var frame_transform := false
        var frame_visibility := false
        var frame_new := false

        for id in current.keys():
            var row: Dictionary = current[id]
            if not baseline.has(id):
                frame_changed = true
                frame_new = true
                changed_names[String(row["name"])] = true
                continue

            var before: Dictionary = baseline[id]
            var node := row["node"] as Node3D
            if not is_instance_valid(node):
                continue
            if _transform_changed(
                before["transform"] as Transform3D,
                row["transform"] as Transform3D
            ):
                frame_changed = true
                frame_transform = true
                changed_names[String(row["name"])] = true
            if bool(before["visible"]) != bool(row["visible"]):
                frame_changed = true
                frame_visibility = true
                changed_names[String(row["name"])] = true

        if frame_changed:
            changed_frames.append(frame)
        if frame_transform:
            transform_change_frames.append(frame)
        if frame_visibility:
            visibility_change_frames.append(frame)
        if frame_new:
            new_node_frames.append(frame)

    # An instantaneous hide/removal is not an animation. Require visual
    # activity across multiple distinct frames and either real transform
    # motion or a multi-frame visibility/new-node sequence.
    var distributed_activity := changed_frames.size() >= 2
    var motion_activity := transform_change_frames.size() >= 2
    var staged_visibility_activity := (
        visibility_change_frames.size() >= 2
        or new_node_frames.size() >= 2
    )
    return {
        "changed_frames": changed_frames,
        "transform_change_frames": transform_change_frames,
        "visibility_change_frames": visibility_change_frames,
        "new_node_frames": new_node_frames,
        "changed_names": changed_names.keys(),
        "animation_observed": (
            distributed_activity
            and (motion_activity or staged_visibility_activity)
        )
    }

func _run() -> void:
    if not ResourceLoader.exists(REQUIRED_ROOM):
        print("OPENAZRAEL_KG001_WELL_TONGS_V118 " + JSON.stringify({
            "schema": "openazrael.kg001.well_tongs_animation",
            "version": 118,
            "status": "BLOCKED_MISSING_ASSETS",
            "missing": [REQUIRED_ROOM]
        }))
        quit(2)
        return

    var state = root.get_node_or_null("DemoState")
    if state == null:
        print("OPENAZRAEL_KG001_WELL_TONGS_V118 " + JSON.stringify({
            "schema": "openazrael.kg001.well_tongs_animation",
            "version": 118,
            "status": "FAIL",
            "error": "DemoState missing"
        }))
        quit(1)
        return

    state.reset_all()
    var packed = load("res://main.tscn")
    if packed == null:
        print("OPENAZRAEL_KG001_WELL_TONGS_V118 " + JSON.stringify({
            "schema": "openazrael.kg001.well_tongs_animation",
            "version": 118,
            "status": "FAIL",
            "error": "main.tscn load failed"
        }))
        quit(1)
        return

    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle(3)

    var manager = scene.get_node_or_null("RoomManager")
    _check("room_manager_present", manager != null)
    if manager == null:
        _finish(scene)
        return

    manager.transition_cooldown = 999.0
    manager.load_room("R7", false)
    await _settle(3)

    var well_interact := _find_named(
        manager.current_room, "Interact_WellKey"
    )
    var key_visual := _find_named(manager.current_room, "nibdyky01")
    _check("well_interaction_present", well_interact != null)
    _check("well_key_visual_present", key_visual is Node3D)
    if well_interact == null or not (key_visual is Node3D):
        _finish(scene)
        return

    # Negative precondition: touching the well without tongs must not acquire
    # the key, set the retrieval node/flag, hide/move the visual or destroy the
    # interaction.
    var negative_transform := (key_visual as Node3D).global_transform
    var negative_visible := (key_visual as Node3D).visible
    well_interact.call("interact")
    await _settle(4)
    _check("without_tongs_no_key", not state.has("well_key"))
    _check(
        "without_tongs_no_retrieval_node",
        not state.puzzle_node("R7KeyTake")
    )
    _check("without_tongs_no_R7key_flag", not state.flag("R7key"))
    _check(
        "without_tongs_visual_transform_unchanged",
        is_instance_valid(key_visual)
        and (key_visual as Node3D).global_transform.is_equal_approx(
            negative_transform
        )
    )
    _check(
        "without_tongs_visual_stays_visible",
        is_instance_valid(key_visual)
        and (key_visual as Node3D).visible == negative_visible
    )
    _check(
        "without_tongs_interaction_remains",
        is_instance_valid(well_interact)
    )

    # Positive precondition: use the actual inventory state expected by the
    # production interaction, then observe the real R7 well cluster. The test
    # intentionally does not prescribe Tween vs AnimationPlayer or a guessed
    # original trajectory.
    state.acquire("rusty_tongs")
    var center := (key_visual as Node3D).global_position
    var baseline := _snapshot_local_nodes(manager.current_room, center)
    well_interact.call("interact")
    var activity := await _observe_animation_activity(
        manager.current_room, center, baseline
    )

    _check("with_tongs_well_key_acquired", state.has("well_key"))
    _check(
        "with_tongs_R7KeyTake_set",
        state.puzzle_node("R7KeyTake")
    )
    _check("with_tongs_R7key_flag_set", state.flag("R7key"))
    _check(
        "with_tongs_animation_activity_observed",
        bool(activity["animation_observed"])
    )

    var result := {
        "schema": "openazrael.kg001.well_tongs_animation",
        "version": 118,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": check_count,
        "failed": failures,
        "activity": activity,
        "scope": (
            "production Interact_WellKey negative/positive preconditions plus "
            + "multi-frame visual animation activity in the real R7 well cluster"
        ),
        "boundary": (
            "The runner verifies that a real visual animation is triggered, "
            + "but does not invent the unrecovered original trajectory/timing."
        )
    }
    print("OPENAZRAEL_KG001_WELL_TONGS_V118 " + JSON.stringify(result))
    scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _finish(scene: Node) -> void:
    var result := {
        "schema": "openazrael.kg001.well_tongs_animation",
        "version": 118,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": check_count,
        "failed": failures
    }
    print("OPENAZRAEL_KG001_WELL_TONGS_V118 " + JSON.stringify(result))
    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() else 1)
