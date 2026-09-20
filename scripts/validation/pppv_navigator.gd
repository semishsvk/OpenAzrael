extends RefCounted
class_name PPPVNavigator

var player: CharacterBody3D
var interaction_probe: Node
var evidence: PPPVEvidenceBus

func _init(
    production_player: CharacterBody3D,
    production_interaction_probe: Node,
    evidence_bus: PPPVEvidenceBus
) -> void:
    player = production_player
    interaction_probe = production_interaction_probe
    evidence = evidence_bus

func _find_named(root: Node, wanted: String) -> Node3D:
    if root is Node3D and String(root.name) == wanted:
        return root as Node3D
    for child in root.get_children():
        var found := _find_named(child, wanted)
        if found != null:
            return found
    return null

func _probe_target_name() -> String:
    if interaction_probe == null or not interaction_probe.has_method("_find_interactive"):
        return ""
    var candidate: Object = interaction_probe.call("_find_interactive")
    return String(candidate.get("name")) if candidate != null else ""

func _mouse_sensitivity() -> float:
    var value = player.get("mouse_sensitivity")
    if typeof(value) in [TYPE_FLOAT, TYPE_INT] and float(value) > 0.000001:
        return float(value)
    return 0.0025

func _turn_toward(target_position: Vector3, max_pixels: float = 90.0) -> float:
    var flat := target_position - player.global_position
    flat.y = 0.0
    if flat.length_squared() < 0.0001:
        return 0.0

    var desired_yaw := atan2(-flat.x, -flat.z)
    var delta_yaw := wrapf(desired_yaw - player.rotation.y, -PI, PI)
    var pixels := clampf(
        -delta_yaw / _mouse_sensitivity(),
        -max_pixels,
        max_pixels
    )
    var event := InputEventMouseMotion.new()
    event.relative = Vector2(pixels, 0.0)
    Input.parse_input_event(event)
    return delta_yaw

func approach_interactable(
    action_id: String,
    target_name: String,
    search_root: Node,
    max_frames: int = 600,
    stuck_frames: int = 120
) -> Dictionary:
    var target := _find_named(search_root, target_name)
    evidence.record_player_action(action_id, "input", {
        "strategy": "steer_to_interactable",
        "target": target_name,
        "max_frames": max_frames
    })
    if target == null:
        evidence.record("navigation_failure", {
            "action_id": action_id,
            "target": target_name,
            "reason": "target_not_found"
        })
        return {"reached": false, "reason": "target_not_found"}

    var start := player.global_position
    var previous := start
    var last_progress_frame := 0
    var best_distance := start.distance_to(target.global_position)
    var used_frames := 0
    var reached := false

    Input.action_release(&"move_forward")
    for frame in range(max_frames):
        used_frames = frame + 1
        var visible_target := _probe_target_name()
        if visible_target == target_name:
            reached = true
            break

        var target_position := target.global_position
        var flat_delta := target_position - player.global_position
        flat_delta.y = 0.0
        var distance := flat_delta.length()

        var yaw_error := _turn_toward(target_position)
        if absf(yaw_error) <= 0.45:
            Input.action_press(&"move_forward", 1.0)
        else:
            Input.action_release(&"move_forward")

        await player.get_tree().physics_frame

        var step_distance := Vector2(
            player.global_position.x - previous.x,
            player.global_position.z - previous.z
        ).length()
        if step_distance > 0.05 or distance < best_distance - 0.25:
            last_progress_frame = frame
            best_distance = minf(best_distance, distance)
        previous = player.global_position

        if frame - last_progress_frame >= stuck_frames:
            evidence.record("navigation_failure", {
                "action_id": action_id,
                "target": target_name,
                "reason": "stuck",
                "frame": frame,
                "best_distance": best_distance
            })
            break

    Input.action_release(&"move_forward")
    await player.get_tree().physics_frame

    var finish := player.global_position
    var horizontal_distance := Vector2(
        finish.x - start.x,
        finish.z - start.z
    ).length()
    evidence.record("movement", {
        "action_id": action_id,
        "target": target_name,
        "progress_ok": horizontal_distance > 0.5 or reached,
        "horizontal_distance": horizontal_distance,
        "reached": reached,
        "used_frames": used_frames
    })
    evidence.record_interaction_probe(
        target_name,
        reached,
        _probe_target_name()
    )
    return {
        "reached": reached,
        "horizontal_distance": horizontal_distance,
        "used_frames": used_frames
    }
