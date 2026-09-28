extends RefCounted
class_name PPPVNavigator

var player: CharacterBody3D
var interaction_probe: Node
var evidence: PPPVEvidenceBus
var runtime_guard = null

func _init(
    production_player: CharacterBody3D,
    production_interaction_probe: Node,
    evidence_bus: PPPVEvidenceBus,
    guard = null
) -> void:
    player = production_player
    interaction_probe = production_interaction_probe
    evidence = evidence_bus
    runtime_guard = guard

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

func _guard_sample(action_id: String) -> bool:
    if runtime_guard == null:
        return true
    return bool(runtime_guard.sample(action_id))

func _watchdog(action_id: String, reason: String, details: Dictionary) -> void:
    if runtime_guard != null:
        runtime_guard.report_watchdog(action_id, reason, details)

func _v3(value: Vector3) -> Array:
    return [value.x, value.y, value.z]

func _support_snapshot() -> Dictionary:
    if runtime_guard != null and runtime_guard.has_method("_support_below_player"):
        var support = runtime_guard.call("_support_below_player")
        if support is Dictionary:
            return support.duplicate(true)
    return {
        "supported": player.is_on_floor(),
        "fallback_is_on_floor": true
    }

func _navigation_diagnostic(
    target_name: String,
    target_position: Vector3,
    frame: int,
    best_distance: float,
    last_progress_frame: int,
    last_progress_position: Vector3,
    correction_count: int,
    yaw_sign_flips: int,
    last_yaw_error: float,
    reason: String
) -> Dictionary:
    var pitch_value = player.get("pitch")
    var pitch := (
        float(pitch_value)
        if typeof(pitch_value) in [TYPE_FLOAT, TYPE_INT]
        else 0.0
    )
    var flat_delta := target_position - player.global_position
    flat_delta.y = 0.0
    return {
        "reason": reason,
        "target": target_name,
        "navigation_target": _v3(target_position),
        "player_position": _v3(player.global_position),
        "player_velocity": _v3(player.velocity),
        "heading_yaw": player.rotation.y,
        "pitch": pitch,
        "distance_to_target": flat_delta.length(),
        "interaction_probe_target": _probe_target_name(),
        "is_on_floor": player.is_on_floor(),
        "support": _support_snapshot(),
        "direction_corrections": correction_count,
        "yaw_sign_flips": yaw_sign_flips,
        "last_yaw_error": last_yaw_error,
        "watchdog_progress_metric_frames_since_progress": maxi(frame - last_progress_frame, 0),
        "best_distance": best_distance,
        "last_successful_route_waypoint": _v3(last_progress_position),
        "route_waypoint_kind": "continuous_direct_target_progress"
    }

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
    var runtime_guard_failed := false
    var correction_count := 0
    var yaw_sign_flips := 0
    var previous_yaw_sign := 0
    var last_yaw_error := 0.0
    var last_progress_position := start

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

        # Movement only needs to reach a safe interaction standoff.
        # Exact cursor/probe acquisition is validated separately by
        # aim_at_interactable(), so do not keep walking into the target
        # merely because the current camera ray does not hit it yet.
        var standoff_distance := 64.0
        if distance <= standoff_distance:
            reached = true
            break

        var yaw_error := _turn_toward(target_position)
        last_yaw_error = yaw_error
        if absf(yaw_error) > 0.01:
            correction_count += 1
            var yaw_sign := 1 if yaw_error > 0.0 else -1
            if previous_yaw_sign != 0 and yaw_sign != previous_yaw_sign:
                yaw_sign_flips += 1
            previous_yaw_sign = yaw_sign
        if absf(yaw_error) <= 0.45:
            Input.action_press(&"move_forward", 1.0)
        else:
            Input.action_release(&"move_forward")

        await player.get_tree().physics_frame
        if not _guard_sample(action_id):
            runtime_guard_failed = true
            evidence.record("navigation_failure", {
                "action_id": action_id,
                "target": target_name,
                "reason": "runtime_guard_failure",
                "frame": frame
            })
            break

        var step_distance := Vector2(
            player.global_position.x - previous.x,
            player.global_position.z - previous.z
        ).length()
        if step_distance > 0.05 or distance < best_distance - 0.25:
            last_progress_frame = frame
            best_distance = minf(best_distance, distance)
            last_progress_position = player.global_position
        previous = player.global_position

        if frame - last_progress_frame >= stuck_frames:
            var watchdog_details := _navigation_diagnostic(
                target_name,
                target_position,
                frame,
                best_distance,
                last_progress_frame,
                last_progress_position,
                correction_count,
                yaw_sign_flips,
                last_yaw_error,
                "navigation_stuck"
            )
            watchdog_details["strategy"] = "steer_to_interactable"
            evidence.record("navigation_failure", {
                "action_id": action_id,
                "target": target_name,
                "reason": "stuck",
                "frame": frame,
                "best_distance": best_distance
            })
            _watchdog(action_id, "navigation_stuck", watchdog_details)
            break

    Input.action_release(&"move_forward")
    await player.get_tree().physics_frame
    if not runtime_guard_failed:
        runtime_guard_failed = not _guard_sample(action_id)

    var finish := player.global_position
    var horizontal_distance := Vector2(
        finish.x - start.x,
        finish.z - start.z
    ).length()
    var final_target_position := target.global_position
    var completion_reason := (
        "probe_target_matches"
        if _probe_target_name() == target_name
        else (
            "standoff_reached_probe_pending"
            if reached
            else (
                "runtime_guard_failure"
                if runtime_guard_failed
                else "navigation_incomplete"
            )
        )
    )
    evidence.record("navigation_diagnostic", {
        "action_id": action_id,
        "snapshot": _navigation_diagnostic(
            target_name,
            final_target_position,
            maxi(used_frames - 1, 0),
            best_distance,
            last_progress_frame,
            last_progress_position,
            correction_count,
            yaw_sign_flips,
            last_yaw_error,
            completion_reason
        )
    })
    evidence.record("movement", {
        "action_id": action_id,
        "target": target_name,
        "progress_ok": horizontal_distance > 0.5 or reached,
        "horizontal_distance": horizontal_distance,
        "reached": reached,
        "runtime_guard_failed": runtime_guard_failed,
        "used_frames": used_frames,
        "direction_corrections": correction_count,
        "yaw_sign_flips": yaw_sign_flips,
        "completion_reason": completion_reason
    })
    evidence.record_interaction_probe(
        target_name,
        reached,
        _probe_target_name()
    )
    return {
        "reached": reached and not runtime_guard_failed,
        "horizontal_distance": horizontal_distance,
        "runtime_guard_failed": runtime_guard_failed,
        "used_frames": used_frames
    }


func approach_world_point(
    action_id: String,
    target_position: Vector3,
    stop_condition: Callable = Callable(),
    max_frames: int = 900,
    stuck_frames: int = 150,
    reach_distance: float = 8.0
) -> Dictionary:
    evidence.record_player_action(action_id, "input", {
        "strategy": "steer_to_world_point",
        "target_position": [
            target_position.x,
            target_position.y,
            target_position.z
        ],
        "max_frames": max_frames
    })

    var start := player.global_position
    var previous := start
    var best_distance := Vector2(
        target_position.x - start.x,
        target_position.z - start.z
    ).length()
    var last_progress_frame := 0
    var used_frames := 0
    var reached := false
    var stopped_by_condition := false
    var runtime_guard_failed := false

    Input.action_release(&"move_forward")
    for frame in range(max_frames):
        used_frames = frame + 1

        if stop_condition.is_valid() and bool(stop_condition.call()):
            stopped_by_condition = true
            reached = true
            break

        var flat_delta := target_position - player.global_position
        flat_delta.y = 0.0
        var distance := flat_delta.length()
        if distance <= reach_distance:
            reached = true
            break

        var yaw_error := _turn_toward(target_position)
        if absf(yaw_error) <= 0.45:
            Input.action_press(&"move_forward", 1.0)
        else:
            Input.action_release(&"move_forward")

        await player.get_tree().physics_frame
        if not _guard_sample(action_id):
            runtime_guard_failed = true
            evidence.record("navigation_failure", {
                "action_id": action_id,
                "reason": "runtime_guard_failure",
                "frame": frame
            })
            break

        var step_distance := Vector2(
            player.global_position.x - previous.x,
            player.global_position.z - previous.z
        ).length()
        var new_distance := Vector2(
            target_position.x - player.global_position.x,
            target_position.z - player.global_position.z
        ).length()
        if step_distance > 0.05 or new_distance < best_distance - 0.25:
            last_progress_frame = frame
            best_distance = minf(best_distance, new_distance)
        previous = player.global_position

        if frame - last_progress_frame >= stuck_frames:
            var watchdog_details := {
                "frame": frame,
                "best_distance": best_distance,
                "target_position": [
                    target_position.x,
                    target_position.y,
                    target_position.z
                ],
                "strategy": "steer_to_world_point"
            }
            evidence.record("navigation_failure", {
                "action_id": action_id,
                "reason": "stuck_world_point",
                "frame": frame,
                "best_distance": best_distance
            })
            _watchdog(action_id, "navigation_stuck_world_point", watchdog_details)
            break

    Input.action_release(&"move_forward")
    await player.get_tree().physics_frame
    if not runtime_guard_failed:
        runtime_guard_failed = not _guard_sample(action_id)

    var finish := player.global_position
    var horizontal_distance := Vector2(
        finish.x - start.x,
        finish.z - start.z
    ).length()
    evidence.record("movement", {
        "action_id": action_id,
        "strategy": "steer_to_world_point",
        "progress_ok": horizontal_distance > 0.5 or reached,
        "horizontal_distance": horizontal_distance,
        "reached": reached,
        "stopped_by_condition": stopped_by_condition,
        "runtime_guard_failed": runtime_guard_failed,
        "used_frames": used_frames
    })
    return {
        "reached": reached and not runtime_guard_failed,
        "stopped_by_condition": stopped_by_condition and not runtime_guard_failed,
        "horizontal_distance": horizontal_distance,
        "runtime_guard_failed": runtime_guard_failed,
        "used_frames": used_frames
    }


func aim_at_interactable(
    action_id: String,
    target_name: String,
    search_root: Node,
    max_frames: int = 180
) -> Dictionary:
    var target := _find_named(search_root, target_name)
    evidence.record_player_action(action_id, "input", {
        "strategy": "aim_at_interactable",
        "input_action": "mouse_motion",
        "target": target_name,
        "max_frames": max_frames
    })
    if target == null:
        evidence.record("navigation_failure", {
            "action_id": action_id,
            "target": target_name,
            "reason": "aim_target_not_found"
        })
        return {"acquired": false, "reason": "aim_target_not_found"}

    var camera := interaction_probe.get_parent() as Camera3D
    if camera == null:
        evidence.record("navigation_failure", {
            "action_id": action_id,
            "target": target_name,
            "reason": "aim_camera_unavailable"
        })
        return {"acquired": false, "reason": "aim_camera_unavailable"}

    var acquired := false
    var used_frames := 0
    for frame in range(max_frames):
        used_frames = frame + 1
        if _probe_target_name() == target_name:
            acquired = true
            break

        _turn_toward(target.global_position, 70.0)

        var delta := target.global_position - camera.global_position
        if delta.length_squared() > 0.0001:
            var desired_pitch := asin(
                clampf(delta.normalized().y, -1.0, 1.0)
            )
            var pitch_value = player.get("pitch")
            var current_pitch := (
                float(pitch_value)
                if typeof(pitch_value) in [TYPE_FLOAT, TYPE_INT]
                else camera.rotation.x
            )
            var pitch_error := desired_pitch - current_pitch
            var vertical_pixels := clampf(
                -pitch_error / _mouse_sensitivity(),
                -70.0,
                70.0
            )
            var event := InputEventMouseMotion.new()
            event.relative = Vector2(0.0, vertical_pixels)
            Input.parse_input_event(event)

        await player.get_tree().process_frame

    evidence.record_interaction_probe(
        target_name,
        acquired,
        _probe_target_name()
    )
    evidence.record("aim", {
        "action_id": action_id,
        "target": target_name,
        "acquired": acquired,
        "used_frames": used_frames
    })
    if not acquired:
        evidence.record("navigation_failure", {
            "action_id": action_id,
            "target": target_name,
            "reason": "aim_target_not_acquired",
            "used_frames": used_frames
        })
    return {
        "acquired": acquired,
        "used_frames": used_frames
    }
