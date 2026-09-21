extends RefCounted
class_name PPPVRuntimeGuard

const MAX_UNSUPPORTED_FALL_FRAMES := 18
const MAX_VERTICAL_DROP_PER_FRAME := 24.0
const MAX_ACTION_VERTICAL_DROP := 96.0
const DEFAULT_SPAWN_POSITION_TOLERANCE := 14.0
const DEFAULT_SPAWN_YAW_TOLERANCE := 0.35
const MOVEMENT_ACTIONS := [
    &"move_forward",
    &"move_back",
    &"move_left",
    &"move_right"
]

var player: CharacterBody3D
var manager: Node
var state: Node
var evidence: PPPVEvidenceBus

var _failures: Array[String] = []
var _replay: Array[Dictionary] = []
var _active_action_id := ""
var _active_action_kind := ""
var _active_replay_index := -1
var _start_snapshot: Dictionary = {}
var _last_position := Vector3.ZERO
var _last_room := ""
var _unsupported_fall_frames := 0
var _sample_index := 0
var _action_failure_count := 0

func _init(
    production_player: CharacterBody3D,
    room_manager: Node,
    demo_state: Node,
    evidence_bus: PPPVEvidenceBus
) -> void:
    player = production_player
    manager = room_manager
    state = demo_state
    evidence = evidence_bus

func _v3(value: Vector3) -> Array:
    return [value.x, value.y, value.z]

func _state_payload():
    if state == null or not state.has_method("canonical_state_payload"):
        return null
    var payload = state.call("canonical_state_payload")
    if payload is Array or payload is Dictionary:
        return payload.duplicate(true)
    return payload

func _state_hash() -> String:
    if state != null and state.has_method("canonical_state_hash"):
        return String(state.call("canonical_state_hash"))
    return ""

func snapshot(action_id: String = "", phase: String = "") -> Dictionary:
    var floor_normal := Vector3.ZERO
    var on_floor := false
    if player != null:
        on_floor = player.is_on_floor()
        if on_floor:
            floor_normal = player.get_floor_normal()
    var row := {
        "physics_frame": Engine.get_physics_frames(),
        "action_id": action_id,
        "phase": phase,
        "room": String(manager.get("current_room_id")) if manager != null else "",
        "position": _v3(player.global_position),
        "rotation": _v3(player.global_rotation),
        "velocity": _v3(player.velocity),
        "is_on_floor": on_floor,
        "floor_normal": _v3(floor_normal),
        "state_sha256": _state_hash(),
        "state_payload": _state_payload()
    }
    return row

func begin_action(action: Dictionary) -> void:
    _active_action_id = String(action.get("action_id", ""))
    _active_action_kind = String(action.get("kind", ""))
    _unsupported_fall_frames = 0
    _sample_index = 0
    _action_failure_count = _failures.size()
    _start_snapshot = snapshot(_active_action_id, "before")
    _last_position = player.global_position
    _last_room = String(_start_snapshot.get("room", ""))

    evidence.record("world_snapshot", _start_snapshot.duplicate(true))
    _replay.append({
        "action_id": _active_action_id,
        "kind": _active_action_kind,
        "command": action.duplicate(true),
        "before": _start_snapshot.duplicate(true),
        "trajectory": [],
        "result": {}
    })
    _active_replay_index = _replay.size() - 1

func _critical(code: String, details: Dictionary = {}) -> void:
    var failure := _active_action_id + ":" + code
    if not _failures.has(failure):
        _failures.append(failure)
    var payload := details.duplicate(true)
    payload["action_id"] = _active_action_id
    payload["code"] = code
    payload["critical"] = true
    evidence.record("critical_runtime_violation", payload)

func _validate_live_invariants(action_id: String) -> void:
    if player == null:
        return
    if not player.is_inside_tree():
        _critical("player_left_scene_tree", {
            "action_id": action_id
        })
        return

    if (
        not player.global_position.is_finite()
        or not player.global_rotation.is_finite()
        or not player.velocity.is_finite()
    ):
        _critical("non_finite_player_state", {
            "action_id": action_id,
            "position": _v3(player.global_position),
            "rotation": _v3(player.global_rotation),
            "velocity": _v3(player.velocity)
        })

    if manager == null:
        _critical("room_manager_missing", {
            "action_id": action_id
        })
        return

    var room_id := String(manager.get("current_room_id"))
    var room_node = manager.get("current_room")
    if room_id.is_empty():
        _critical("current_room_id_empty", {
            "action_id": action_id
        })
    if room_node == null or not is_instance_valid(room_node):
        _critical("current_room_node_invalid", {
            "action_id": action_id,
            "room": room_id
        })


func _validate_neutral_movement_input(action_id: String) -> void:
    var stuck: Array[String] = []
    for input_action in MOVEMENT_ACTIONS:
        if Input.is_action_pressed(input_action):
            stuck.append(String(input_action))
    if not stuck.is_empty():
        _critical("movement_input_stuck_after_action", {
            "action_id": action_id,
            "pressed_actions": stuck
        })


func sample(action_id: String = "") -> bool:
    if player == null:
        return true

    var effective_id := action_id if not action_id.is_empty() else _active_action_id
    _validate_live_invariants(effective_id)
    var current := snapshot(effective_id, "sample")
    var position := player.global_position
    var current_room := String(current.get("room", ""))
    var room_changed := not _last_room.is_empty() and current_room != _last_room
    var delta_y := 0.0 if room_changed else position.y - _last_position.y

    if room_changed:
        _unsupported_fall_frames = 0
        evidence.record("room_change_sample", {
            "action_id": effective_id,
            "source_room": _last_room,
            "destination_room": current_room,
            "previous_position": _v3(_last_position),
            "destination_position": current["position"],
            "continuity_reset": true
        })
    elif not player.is_on_floor() and player.velocity.y < -0.1:
        _unsupported_fall_frames += 1
    else:
        _unsupported_fall_frames = 0

    var start_position := _last_position
    if _start_snapshot.has("position"):
        var raw = _start_snapshot["position"]
        if raw is Array and raw.size() >= 3:
            start_position = Vector3(float(raw[0]), float(raw[1]), float(raw[2]))

    var total_drop := 0.0 if room_changed else start_position.y - position.y
    var sample := {
        "index": _sample_index,
        "physics_frame": current["physics_frame"],
        "room": current_room,
        "position": current["position"],
        "rotation": current["rotation"],
        "velocity": current["velocity"],
        "is_on_floor": current["is_on_floor"],
        "room_changed": room_changed,
        "delta_y": delta_y,
        "drop_from_action_start": total_drop
    }

    if _active_replay_index >= 0 and _active_replay_index < _replay.size():
        _replay[_active_replay_index]["trajectory"].append(sample)

    if not room_changed and delta_y < -MAX_VERTICAL_DROP_PER_FRAME:
        _critical("floor_drop_per_frame", {
            "delta_y": delta_y,
            "position": current["position"],
            "previous_position": _v3(_last_position)
        })
    if (
        not room_changed
        and total_drop > MAX_ACTION_VERTICAL_DROP
        and _unsupported_fall_frames >= 6
        and player.velocity.y < -0.1
    ):
        _critical("action_vertical_drop", {
            "drop": total_drop,
            "unsupported_frames": _unsupported_fall_frames,
            "position": current["position"],
            "start_position": _start_snapshot.get("position", [])
        })
    if not room_changed and _unsupported_fall_frames > MAX_UNSUPPORTED_FALL_FRAMES:
        _critical("unsupported_fall", {
            "unsupported_frames": _unsupported_fall_frames,
            "position": current["position"],
            "velocity": current["velocity"]
        })

    _last_position = position
    _last_room = current_room
    _sample_index += 1
    return current_action_ok()

func report_watchdog(
    action_id: String,
    reason: String,
    details: Dictionary = {}
) -> void:
    var payload := details.duplicate(true)
    payload["action_id"] = action_id
    payload["reason"] = reason
    payload["critical"] = true
    evidence.record("softlock_watchdog", payload)
    var previous_id := _active_action_id
    _active_action_id = action_id
    _critical("softlock_watchdog:" + reason, details)
    _active_action_id = previous_id

func _array_v3(value) -> Vector3:
    if not value is Array or value.size() < 3:
        return Vector3.ZERO
    return Vector3(float(value[0]), float(value[1]), float(value[2]))

func _transition_record(
    source_room: String,
    trigger: String,
    destination_room: String
) -> Dictionary:
    if manager == null:
        return {}
    var runtime_evidence = manager.get("evidence")
    if not runtime_evidence is Dictionary:
        return {}
    for raw in runtime_evidence.get("demo_transitions", []):
        if not raw is Dictionary:
            continue
        if (
            String(raw.get("source_room", "")) == source_room
            and String(raw.get("trigger", "")) == trigger
            and String(raw.get("destination_room", "")) == destination_room
        ):
            return raw
    return {}

func verify_transition_spawn(
    action_id: String,
    source_room: String,
    trigger: String,
    destination_room: String,
    position_tolerance: float = DEFAULT_SPAWN_POSITION_TOLERANCE,
    yaw_tolerance: float = DEFAULT_SPAWN_YAW_TOLERANCE
) -> bool:
    var transition := _transition_record(source_room, trigger, destination_room)
    if transition.is_empty():
        _critical("transition_record_missing", {
            "source_room": source_room,
            "trigger": trigger,
            "destination_room": destination_room
        })
        return false

    var destination_view := String(transition.get("destination_view", ""))
    if destination_view.is_empty() or not manager.has_method("_view_record"):
        _critical("destination_view_missing", {
            "destination_room": destination_room,
            "destination_view": destination_view
        })
        return false

    var view = manager.call("_view_record", destination_room, destination_view)
    if not view is Dictionary or view.is_empty():
        _critical("destination_view_record_missing", {
            "destination_room": destination_room,
            "destination_view": destination_view
        })
        return false

    var centroid := _array_v3(view.get("centroid", []))
    var normal := _array_v3(view.get("normal", [])).normalized()
    var eye_height := float(player.get("eye_height"))
    var expected_position := centroid + normal * 120.0 - Vector3.UP * eye_height
    var position_error := player.global_position.distance_to(expected_position)

    var flat := Vector3(normal.x, 0.0, normal.z).normalized()
    if flat.length_squared() < 0.001:
        flat = Vector3.FORWARD
    var expected_yaw := atan2(-flat.x, -flat.z)
    var yaw_error := absf(wrapf(player.rotation.y - expected_yaw, -PI, PI))

    var ok := (
        String(manager.get("current_room_id")) == destination_room
        and position_error <= position_tolerance
        and yaw_error <= yaw_tolerance
    )
    evidence.record("transition_spawn_check", {
        "action_id": action_id,
        "source_room": source_room,
        "trigger": trigger,
        "destination_room": destination_room,
        "destination_view": destination_view,
        "actual_position": _v3(player.global_position),
        "expected_position": _v3(expected_position),
        "position_error": position_error,
        "position_tolerance": position_tolerance,
        "actual_yaw": player.rotation.y,
        "expected_yaw": expected_yaw,
        "yaw_error": yaw_error,
        "yaw_tolerance": yaw_tolerance,
        "match": ok
    })
    if not ok:
        _critical("transition_spawn_mismatch", {
            "source_room": source_room,
            "trigger": trigger,
            "destination_room": destination_room,
            "destination_view": destination_view,
            "position_error": position_error,
            "yaw_error": yaw_error
        })
    return ok

func end_action(success: bool, details: Dictionary = {}) -> void:
    _validate_live_invariants(_active_action_id)
    _validate_neutral_movement_input(_active_action_id)
    var after := snapshot(_active_action_id, "after")
    evidence.record("world_snapshot", after.duplicate(true))
    var action_failures: Array[String] = []
    for index in range(_action_failure_count, _failures.size()):
        action_failures.append(_failures[index])

    if _active_replay_index >= 0 and _active_replay_index < _replay.size():
        _replay[_active_replay_index]["after"] = after.duplicate(true)
        _replay[_active_replay_index]["result"] = {
            "success": success and action_failures.is_empty(),
            "details": details.duplicate(true),
            "failures": action_failures
        }

    evidence.record("replay_action_result", {
        "action_id": _active_action_id,
        "success": success and action_failures.is_empty(),
        "failures": action_failures,
        "trajectory_samples": _sample_index
    })

    _active_action_id = ""
    _active_action_kind = ""
    _active_replay_index = -1
    _start_snapshot = {}
    _last_room = ""
    _unsupported_fall_frames = 0
    _sample_index = 0

func current_action_ok() -> bool:
    return _failures.size() == _action_failure_count

func failure_list() -> Array[String]:
    return _failures.duplicate()

func replay_bundle() -> Dictionary:
    return {
        "schema": "remaster.synthetic_player_replay",
        "version": 1,
        "frame_level_avatar_trajectory": true,
        "actions": _replay.duplicate(true)
    }
