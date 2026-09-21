extends RefCounted
class_name PPPVActionExecutor

var manager: Node
var driver
var navigator
var observer
var failures: Array[String] = []

func _init(
    room_manager: Node,
    player_driver,
    player_navigator,
    runtime_observer
) -> void:
    manager = room_manager
    driver = player_driver
    navigator = player_navigator
    observer = runtime_observer

func _settle(frames: int = 2) -> void:
    for _i in range(frames):
        await manager.get_tree().process_frame

func _find_named(root_node: Node, wanted: String) -> Node:
    if String(root_node.name) == wanted:
        return root_node
    for child in root_node.get_children():
        var found := _find_named(child, wanted)
        if found != null:
            return found
    return null

func _room_is(expected_room: String) -> bool:
    return String(manager.get("current_room_id")) == expected_room

func _trigger_centroid(room: String, trigger: String):
    if not manager.has_method("_trigger_record"):
        return null
    var record = manager.call("_trigger_record", room, trigger)
    if not record is Dictionary or record.is_empty():
        return null
    var value = record.get("centroid", [])
    if not value is Array or value.size() < 3:
        return null
    return Vector3(float(value[0]), float(value[1]), float(value[2]))

func execute(action: Dictionary) -> bool:
    var action_id := String(action.get("action_id", ""))
    var kind := String(action.get("kind", ""))
    var params = action.get("parameters", {})
    if not params is Dictionary:
        params = {}

    match kind:
        "move":
            var goal_trigger := String(params.get("goal_trigger", ""))
            if not goal_trigger.is_empty():
                var source_room := String(
                    params.get("source_room", manager.get("current_room_id"))
                )
                var destination_room := String(
                    params.get("destination_room", "")
                )
                var centroid = _trigger_centroid(source_room, goal_trigger)
                if centroid == null:
                    failures.append(action_id + ":invalid_trigger_goal")
                    return false

                if destination_room.is_empty():
                    var trigger_result: Dictionary = await navigator.approach_world_point(
                        action_id,
                        centroid,
                        Callable(),
                        int(params.get("max_frames", 1200)),
                        int(params.get("stuck_frames", 180)),
                        float(params.get("reach_distance", 4.0))
                    )
                    if not bool(trigger_result.get("reached", false)):
                        failures.append(action_id + ":trigger_goal_not_reached")
                        return false
                    return true

                manager.set("transition_cooldown", 0.0)
                var transition_result: Dictionary = await navigator.approach_world_point(
                    action_id,
                    centroid,
                    Callable(self, "_room_is").bind(destination_room),
                    int(params.get("max_frames", 1200)),
                    int(params.get("stuck_frames", 180)),
                    float(params.get("reach_distance", 8.0))
                )
                if (
                    not bool(transition_result.get("stopped_by_condition", false))
                    or String(manager.get("current_room_id")) != destination_room
                ):
                    failures.append(action_id + ":transition_not_observed")
                    return false
                return true

            var goal_target := String(params.get("goal_target", ""))
            if not goal_target.is_empty():
                var current_room = manager.get("current_room")
                if current_room == null:
                    failures.append(action_id + ":missing_current_room")
                    return false
                var nav_result: Dictionary = await navigator.approach_interactable(
                    action_id,
                    goal_target,
                    current_room,
                    int(params.get("max_frames", 600)),
                    int(params.get("stuck_frames", 120))
                )
                if not bool(nav_result.get("reached", false)):
                    failures.append(action_id + ":navigation_failed")
                    return false
                return true

            var input_action := StringName(String(action.get("input_action", "")))
            var walk_frames := int(action.get("frames", params.get("frames", 60)))
            var walk_result: Dictionary = await driver.walk_input(
                action_id,
                input_action,
                walk_frames
            )
            if walk_result.is_empty():
                failures.append(action_id + ":movement_failed")
                return false
            return true

        "look":
            var look_target := String(params.get("goal_target", ""))
            if not look_target.is_empty():
                var look_room = manager.get("current_room")
                if look_room == null:
                    failures.append(action_id + ":missing_current_room")
                    return false
                var aim_result: Dictionary = await navigator.aim_at_interactable(
                    action_id,
                    look_target,
                    look_room,
                    int(params.get("max_frames", 180))
                )
                if not bool(aim_result.get("acquired", false)):
                    failures.append(action_id + ":aim_target_not_acquired")
                    return false
                return true

            var relative = params.get("relative", [0.0, 0.0])
            if not relative is Array or relative.size() < 2:
                failures.append(action_id + ":invalid_look")
                return false
            await driver.mouse_look(
                action_id,
                Vector2(float(relative[0]), float(relative[1]))
            )
            return true

        "interact":
            var target := String(action.get("target", ""))
            var current_room = manager.get("current_room")
            if current_room != null:
                observer.attach_interaction(_find_named(current_room, target))
            var ok: bool = await driver.interact_via_probe(action_id, target)
            if not ok:
                failures.append(action_id + ":interaction_target_not_reachable")
                return false
            await _settle(2)
            return true

        "wait":
            var wait_frames := int(action.get("frames", params.get("frames", 1)))
            var wait_ok: bool = await driver.wait_physics(
                action_id,
                maxi(wait_frames, 1)
            )
            if not wait_ok:
                failures.append(action_id + ":wait_failed")
                return false
            return true

        _:
            failures.append(action_id + ":unsupported_action:" + kind)
            return false

func failure_list() -> Array[String]:
    return failures.duplicate()
