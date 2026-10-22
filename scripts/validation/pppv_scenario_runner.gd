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
    for arg in OS.get_cmdline_args() + OS.get_cmdline_user_args():
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

func _setup_floor_probe(manager: Node) -> Dictionary:
    var player := manager.get("player") as CharacterBody3D
    if not (player is CharacterBody3D) or not player.is_inside_tree():
        return {"supported": false, "reason": "player_unavailable"}
    var ray_from: Vector3 = player.global_position + Vector3.UP * 8.0
    var ray_to: Vector3 = player.global_position + Vector3.DOWN * 72.0
    var query := PhysicsRayQueryParameters3D.create(
        ray_from,
        ray_to,
        int(player.collision_mask)
    )
    query.exclude = [player.get_rid()]
    query.hit_back_faces = true
    var hit: Dictionary = player.get_world_3d().direct_space_state.intersect_ray(query)
    if hit.is_empty():
        return {
            "supported": false,
            "player_position": [
                player.global_position.x,
                player.global_position.y,
                player.global_position.z
            ],
            "ray_from": [ray_from.x, ray_from.y, ray_from.z],
            "ray_to": [ray_to.x, ray_to.y, ray_to.z]
        }
    var hit_position := hit.get("position", Vector3.ZERO) as Vector3
    var gap: float = player.global_position.y - hit_position.y
    return {
        "supported": gap >= -4.0 and gap <= 24.0,
        "player_position": [
            player.global_position.x,
            player.global_position.y,
            player.global_position.z
        ],
        "floor_position": [
            hit_position.x, hit_position.y, hit_position.z
        ],
        "gap": gap,
        "collider": (
            String((hit.get("collider") as Object).get("name"))
            if hit.get("collider") != null
            else ""
        )
    }

func _verify_setup_support(
    manager: Node,
    room: String,
    portal: String
) -> bool:
    var last_probe: Dictionary = {}
    for frame in range(30):
        await physics_frame
        last_probe = _setup_floor_probe(manager)
        if not bool(last_probe.get("supported", false)):
            failures.append(
                "portal_support_failed:%s/%s:%s"
                % [room, portal, JSON.stringify(last_probe)]
            )
            return false
    return true

func _find_named(root_node: Node, wanted: String) -> Node:
    if String(root_node.name) == wanted:
        return root_node
    for child in root_node.get_children():
        var found := _find_named(child, wanted)
        if found != null:
            return found
    return null

func _known_state_keys(scenario: Dictionary) -> Dictionary:
    var inventory_keys: Array[String] = []
    var flag_keys: Array[String] = []
    var puzzle_keys: Array[String] = []
    var out := {
        "inventory": inventory_keys,
        "flags": flag_keys,
        "puzzle": puzzle_keys
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
    var spawn_view := String(setup.get("spawn_view", ""))
    if (
        room.is_empty()
        or spawn_view.is_empty()
        or not manager.has_method("load_room_at_portal")
    ):
        failures.append("invalid_room_setup")
        return false

    var room_entry_ok := bool(
        manager.call("load_room_at_portal", room, spawn_view, false)
    )
    if not room_entry_ok:
        failures.append("room_portal_setup_failed:%s/%s" % [room, spawn_view])
        return false
    if not await _verify_setup_support(manager, room, spawn_view):
        return false

    var current_room = manager.get("current_room")
    if current_room == null:
        failures.append("room_not_loaded:" + room)
        return false

    if bool(setup.get("lock_room_transitions", false)):
        manager.set("transition_cooldown", 999.0)

    return true

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
    current_scene = scene
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
