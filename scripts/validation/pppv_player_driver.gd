extends RefCounted
class_name PPPVPlayerDriver

const MOVEMENT_ACTIONS := [
    &"move_forward",
    &"move_back",
    &"move_left",
    &"move_right"
]

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

func _release_movement() -> void:
    for action in MOVEMENT_ACTIONS:
        Input.action_release(action)

func walk_input(
    action_id: String,
    input_action: StringName,
    frames: int
) -> Dictionary:
    if frames <= 0 or not InputMap.has_action(input_action):
        evidence.record("driver_error", {
            "action_id": action_id,
            "reason": "invalid_movement_request",
            "input_action": String(input_action),
            "frames": frames
        })
        return {}

    _release_movement()
    var start := player.global_position
    evidence.record_player_action(action_id, "input", {
        "input_action": String(input_action),
        "frames": frames
    })

    Input.action_press(input_action, 1.0)
    for _i in range(frames):
        await player.get_tree().physics_frame
    Input.action_release(input_action)
    await player.get_tree().physics_frame

    var finish := player.global_position
    var horizontal_distance := Vector2(
        finish.x - start.x,
        finish.z - start.z
    ).length()
    var raw := {
        "action_id": action_id,
        "input_action": String(input_action),
        "start": [start.x, start.y, start.z],
        "end": [finish.x, finish.y, finish.z],
        "horizontal_distance": horizontal_distance
    }
    evidence.record("movement_sample", raw)
    return raw

func mouse_look(
    action_id: String,
    relative: Vector2
) -> void:
    evidence.record_player_action(action_id, "input", {
        "input_action": "mouse_motion",
        "relative": [relative.x, relative.y]
    })
    var event := InputEventMouseMotion.new()
    event.relative = relative
    Input.parse_input_event(event)
    await player.get_tree().process_frame

func interact_via_probe(
    action_id: String,
    target_name: String
) -> bool:
    var candidate: Object = null
    if interaction_probe != null and interaction_probe.has_method("_find_interactive"):
        candidate = interaction_probe.call("_find_interactive")

    var actual_name := ""
    if candidate != null:
        actual_name = String(candidate.get("name"))
    var reachable := candidate != null and (
        target_name.is_empty() or actual_name == target_name
    )
    evidence.record_interaction_probe(target_name, reachable, actual_name)
    evidence.record_player_action(action_id, "interaction_probe", {
        "target": target_name,
        "actual_target": actual_name,
        "reachable": reachable
    })
    if not reachable:
        return false

    var pressed := InputEventAction.new()
    pressed.action = &"interact"
    pressed.pressed = true
    Input.parse_input_event(pressed)
    await player.get_tree().process_frame

    var released := InputEventAction.new()
    released.action = &"interact"
    released.pressed = false
    Input.parse_input_event(released)
    await player.get_tree().process_frame

    evidence.record("interaction_input_dispatched", {
        "target": target_name,
        "actual_target": actual_name
    })
    return true
