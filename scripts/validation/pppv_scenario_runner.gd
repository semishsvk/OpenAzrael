extends SceneTree

const EvidenceBusScript = preload("res://scripts/validation/pppv_evidence_bus.gd")
const PlayerDriverScript = preload("res://scripts/validation/pppv_player_driver.gd")
const NavigatorScript = preload("res://scripts/validation/pppv_navigator.gd")
const ObserverScript = preload("res://scripts/validation/openazrael_pppv_observer.gd")
const SceneObserverScript = preload("res://scripts/validation/pppv_scene_observer.gd")
const ActionExecutorScript = preload("res://scripts/validation/pppv_action_executor.gd")
const RuntimeGuardScript = preload("res://scripts/validation/pppv_runtime_guard.gd")

var failures: Array[String] = []

func _initialize() -> void:
    call_deferred("_run")

func _arg_value(prefix: String, default_value: String = "") -> String:
    for arg in OS.get_cmdline_args():
        if arg.begins_with(prefix):
            return arg.substr(prefix.length())
    return default_value

func _load_json(path: String) -> Dictionary:
    if path.is_empty() or not FileAccess.file_exists(path):
        return {}
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
    return parsed if parsed is Dictionary else {}

func _settle(frames: int = 2) -> void:
    for _i in range(frames):
        await process_frame

func _settle_physics(frames: int = 2) -> void:
    for _i in range(frames):
        await physics_frame

func _find_named(root_node: Node, wanted: String) -> Node:
    if String(root_node.name) == wanted:
        return root_node
    for child in root_node.get_children():
        var found := _find_named(child, wanted)
        if found != null:
            return found
    return null

func _known_state_keys(scenario: Dictionary) -> Dictionary:
    var out := {
        "inventory": [],
        "flags": [],
        "puzzle": []
    }
    for row in scenario.get("state_expectations", []):
        if not row is Dictionary:
            continue
        var path := String(row.get("path", ""))
        var pieces := path.split(".", false, 1)
        if pieces.size() != 2:
            continue
        var group := String(pieces[0])
        var key := String(pieces[1])
        if group == "inventory" and not out["inventory"].has(key):
            out["inventory"].append(key)
        elif group == "flags" and not out["flags"].has(key):
            out["flags"].append(key)
        elif group == "puzzle" and not out["puzzle"].has(key):
            out["puzzle"].append(key)
    return out

func _apply_setup(
    scenario: Dictionary,
    manager: Node,
    state: Node
) -> bool:
    var setup = scenario.get("setup", {})
    if not setup is Dictionary:
        setup = {}

    if bool(setup.get("reset_room_state", false)) and state.has_method("reset_all"):
        state.call("reset_all")

    var inventory = setup.get("inventory", {})
    if inventory is Dictionary:
        for raw_key in inventory.keys():
            var key := String(raw_key)
            if bool(inventory[raw_key]):
                state.call("acquire", key)
            elif bool(state.call("has", key)):
                state.call("remove", key)

    var flags = setup.get("flags", {})
    if flags is Dictionary:
        for raw_key in flags.keys():
            state.call("set_flag", String(raw_key), bool(flags[raw_key]))

    var puzzle = setup.get("puzzle", {})
    if puzzle is Dictionary:
        for raw_key in puzzle.keys():
            state.call(
                "set_puzzle_node",
                String(raw_key),
                bool(puzzle[raw_key])
            )

    var room := String(scenario.get("room", ""))
    if room.is_empty() or not manager.has_method("load_room"):
        failures.append("invalid_room_setup")
        return false

    manager.call("load_room", room, false)
    await _settle(2)

    var current_room = manager.get("current_room")
    if current_room == null:
        failures.append("room_not_loaded:" + room)
        return false

    var spawn_view := String(setup.get("spawn_view", ""))
    if not spawn_view.is_empty():
        manager.call("_spawn_at_portal", room, spawn_view)
        await _settle_physics(3)

    if bool(setup.get("lock_room_transitions", false)):
        manager.set("transition_cooldown", 999.0)

    return true

func _room_is(manager: Node, expected_room: String) -> bool:
    return String(manager.get("current_room_id")) == expected_room

func _trigger_centroid(manager: Node, room: String, trigger: String):
    if not manager.has_method("_trigger_record"):
        return null
    var record = manager.call("_trigger_record", room, trigger)
    if not record is Dictionary or record.is_empty():
        return null
    var value = record.get("centroid", [])
    if not value is Array or value.size() < 3:
        return null
    return Vector3(float(value[0]), float(value[1]), float(value[2]))

func _execute_action(
    action: Dictionary,
    manager: Node,
    driver,
    navigator,
    observer
) -> bool:
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
                var centroid = _trigger_centroid(
                    manager,
                    source_room,
                    goal_trigger
                )
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
                    Callable(self, "_room_is").bind(
                        manager,
                        destination_room
                    ),
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

func _write_bundle(path: String, payload: Dictionary) -> bool:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        return false
    file.store_string(JSON.stringify(payload, "  ") + "\n")
    file.close()
    return true

func _finish(
    output_path: String,
    scenario: Dictionary,
    evidence,
    before_state: Dictionary,
    after_state: Dictionary,
    scene: Node,
    runtime_guard = null
) -> void:
    if runtime_guard != null:
        for failure in runtime_guard.failure_list():
            if not failures.has(String(failure)):
                failures.append(String(failure))
    var status := "EXECUTION_PASS" if failures.is_empty() else "EXECUTION_FAIL"
    var payload := {
        "schema": "remaster.runtime_validation_bundle",
        "version": 1,
        "scenario_id": scenario.get("scenario_id", ""),
        "status": status,
        "failures": failures,
        "scenario": scenario,
        "evidence": evidence.bundle(),
        "before_state": before_state,
        "after_state": after_state,
        "runtime_guard_failures": (
            runtime_guard.failure_list() if runtime_guard != null else []
        ),
        "replay": (
            runtime_guard.replay_bundle() if runtime_guard != null else {}
        ),
        "runtime_boundary": {
            "direct_interact_calls": false,
            "gameplay_teleport_during_actions": false,
            "frame_level_avatar_trajectory": true,
            "world_state_snapshots": true,
            "softlock_watchdog": true,
            "transition_spawn_validation": true
        }
    }
    var wrote := _write_bundle(output_path, payload)
    if not wrote:
        push_error("OpenAzrael PPPV: cannot write " + output_path)
        status = "EXECUTION_FAIL"
    print("OPENAZRAEL_PPPV_RUNTIME " + JSON.stringify({
        "scenario_id": scenario.get("scenario_id", ""),
        "status": status,
        "failures": failures,
        "output": output_path
    }))
    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() and wrote else 1)

func _run() -> void:
    var scenario_path := _arg_value("--pppv-scenario=")
    var output_path := _arg_value(
        "--pppv-output=",
        "user://openazrael_pppv_runtime.json"
    )
    var scenario := _load_json(scenario_path)
    if scenario.get("schema") != "remaster.validation_scenario":
        push_error("OpenAzrael PPPV: invalid scenario JSON")
        quit(2)
        return

    var packed = load("res://main.tscn")
    if packed == null:
        push_error("OpenAzrael PPPV: main scene unavailable")
        quit(2)
        return

    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle(3)

    var manager = scene.get_node_or_null("RoomManager")
    var player = scene.get_node_or_null("Player")
    var probe = scene.get_node_or_null("Player/Camera3D/InteractionProbe")
    var state = root.get_node_or_null("DemoState")
    var events = root.get_node_or_null("LegacyEvents")
    var diagnostics = root.get_node_or_null("CandidateDiagnostics")
    if (
        manager == null
        or not (player is CharacterBody3D)
        or probe == null
        or state == null
        or events == null
    ):
        push_error("OpenAzrael PPPV: required runtime nodes unavailable")
        scene.queue_free()
        quit(2)
        return

    var setup_ok: bool = await _apply_setup(scenario, manager, state)
    if not setup_ok:
        var empty_bus = EvidenceBusScript.new()
        _finish(output_path, scenario, empty_bus, {}, {}, scene, null)
        return

    var evidence = EvidenceBusScript.new()
    var observer = ObserverScript.new(evidence, state, events, diagnostics)
    observer.attach()
    var runtime_guard = RuntimeGuardScript.new(
        player,
        manager,
        state,
        evidence
    )
    var driver = PlayerDriverScript.new(
        player,
        probe,
        evidence,
        runtime_guard
    )
    var navigator = NavigatorScript.new(
        player,
        probe,
        evidence,
        runtime_guard
    )
    var scene_observer = SceneObserverScript.new(evidence)
    var action_executor = ActionExecutorScript.new(
        manager,
        driver,
        navigator,
        observer,
        runtime_guard
    )
    var scene_specs = scenario.get("metadata", {}).get("scene_observations", [])
    if not scene_specs is Array:
        scene_specs = []
    var scene_before: Dictionary = scene_observer.capture(
        manager.get("current_room"),
        scene_specs
    )

    var keys := _known_state_keys(scenario)
    var before_state: Dictionary = observer.snapshot_state(
        keys["inventory"],
        keys["flags"],
        keys["puzzle"]
    )

    for raw_action in scenario.get("actions", []):
        if not raw_action is Dictionary:
            failures.append("invalid_action_row")
            break
        var ok: bool = await action_executor.execute(raw_action)
        if not ok:
            for failure in action_executor.failure_list():
                if not failures.has(failure):
                    failures.append(failure)
            break

    await _settle(2)
    scene_observer.emit_changes(
        manager.get("current_room"),
        scene_specs,
        scene_before
    )
    var after_state: Dictionary = observer.snapshot_state(
        keys["inventory"],
        keys["flags"],
        keys["puzzle"]
    )
    _finish(
        output_path,
        scenario,
        evidence,
        before_state,
        after_state,
        scene,
        runtime_guard
    )
