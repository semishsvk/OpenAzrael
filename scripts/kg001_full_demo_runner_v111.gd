extends SceneTree

const REQUIRED_ROOMS := [
    "res://assets/rooms/R1.glb",
    "res://assets/rooms/R7.glb",
    "res://assets/rooms/R8.glb"
]
const COMPLETE_HASH := "e266137c74746996608ffcdd165b6a1072e2c9f55833473546061ccac0e05902"
const EXPECTED_AUDIO := ["979TONGS.WAV", "S152V2.WAV", "S137.WAV", "S121.WAV", "799SECDR.WAV"]

var failures: Array[String] = []
var check_count := 0

func _initialize() -> void:
    call_deferred("_run")

func _check(name: String, condition: bool) -> void:
    check_count += 1
    if not condition:
        failures.append(name)

func _find_named(node: Node, wanted: String) -> Node:
    if String(node.name) == wanted:
        return node
    for child in node.get_children():
        var found := _find_named(child, wanted)
        if found != null:
            return found
    return null

func _interact_named(manager, wanted: String) -> bool:
    if not is_instance_valid(manager.current_room):
        return false
    var node := _find_named(manager.current_room, wanted)
    if node == null or not node.has_method("interact"):
        return false
    node.call("interact")
    return true

func _v3(value: Array) -> Vector3:
    return Vector3(float(value[0]), float(value[1]), float(value[2]))

func _place_on_trigger(manager, player, room_id: String, trigger_name: String) -> bool:
    var record: Dictionary = manager.call("_trigger_record", room_id, trigger_name)
    if record.is_empty():
        return false
    player.global_position = _v3(record["centroid"])
    manager.transition_cooldown = 0.0
    return true

func _settle(frames: int = 3) -> void:
    for _i in range(frames):
        await process_frame

func _finish(status_override: String = "") -> void:
    var status := status_override
    if status.is_empty():
        status = "PASS" if failures.is_empty() else "FAIL"
    var events = root.get_node_or_null("LegacyEvents")
    var state = root.get_node_or_null("DemoState")
    var result := {
        "schema": "openazrael.kg001.full_demo",
        "version": 111,
        "status": status,
        "checks": check_count,
        "failed": failures,
        "persistent_hash": state.canonical_state_hash() if state != null else "",
        "logical_audio_events": events.captured_audio() if events != null else [],
        "scope": "synthetic production-interaction R1 -> R7 -> R1 -> R8 demo playthrough"
    }
    print("OPENAZRAEL_KG001_V111 " + JSON.stringify(result))
    quit(0 if status == "PASS" else (2 if status.begins_with("BLOCKED") else 1))

func _run() -> void:
    var missing: Array[String] = []
    for path in REQUIRED_ROOMS:
        if not ResourceLoader.exists(path):
            missing.append(path)
    if not missing.is_empty():
        print("OPENAZRAEL_KG001_V111 " + JSON.stringify({
            "schema":"openazrael.kg001.full_demo",
            "version":111,
            "status":"BLOCKED_MISSING_ASSETS",
            "missing":missing
        }))
        quit(2)
        return

    var events = root.get_node_or_null("LegacyEvents")
    var state = root.get_node_or_null("DemoState")
    if events == null or state == null:
        failures.append("required_autoloads")
        _finish()
        return

    events.set_capture_only(true)
    events.clear_capture()
    state.reset_all()

    var packed = load("res://main.tscn")
    if packed == null:
        failures.append("main_scene_load")
        _finish()
        return

    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle()

    var manager = scene.get_node("RoomManager")
    var player = scene.get_node("Player")
    _check("initial_room_R1", manager.current_room_id == "R1")

    _check("pickup_tongs_interaction", _interact_named(manager, "Interact_TONG6"))
    await _settle(1)
    _check("tongs_acquired", state.has("rusty_tongs"))

    _check("door1_interaction", _interact_named(manager, "Interact_doorcor01"))
    await _settle(1)
    _check("door1_open", state.flag("R1Door1Open"))

    _check("place_R1_R7_trigger", _place_on_trigger(manager, player, "R1", "zxcoriR5"))
    await _settle()
    _check("entered_R7", manager.current_room_id == "R7")

    _check("well_key_interaction", _interact_named(manager, "Interact_WellKey"))
    await _settle(1)
    _check("well_key_acquired", state.has("well_key"))

    _check("switch_lever_exists", _find_named(manager.current_room, "Interact_well_lev02") != null)
    _check("switch_wheel_exists", _find_named(manager.current_room, "Interact_well_weel3") != null)
    _check("switch_1_interaction", _interact_named(manager, "Interact_well_lev02"))
    _check("switch_step_1", int(state.value("R7SwitchStep", -1)) == 1)
    _check("switch_2_interaction", _interact_named(manager, "Interact_well_weel3"))
    _check("switch_step_2", int(state.value("R7SwitchStep", -1)) == 2)
    _check("switch_3_interaction", _interact_named(manager, "Interact_well_lev02"))
    await _settle(1)
    _check("switchboard_solved", state.flag("R8BathDrain"))

    _check("place_R7_R1_trigger", _place_on_trigger(manager, player, "R7", "zxwell2R6"))
    await _settle()
    _check("returned_R1", manager.current_room_id == "R1")
    _check(
        "consumed_tongs_do_not_respawn",
        _find_named(manager.current_room, "Interact_TONG6") == null
        and state.puzzle_node("PickupCollected:rusty_tongs")
        and not state.has("rusty_tongs")
    )

    _check("door2_interaction", _interact_named(manager, "Interact_doorcor2"))
    await _settle(1)
    _check("door2_open", state.flag("R1Door2Open") and state.flag("FR1DoorUnlocked"))

    _check("place_R1_R8_trigger", _place_on_trigger(manager, player, "R1", "zxcoriR2"))
    await _settle()
    _check("entered_R8", manager.current_room_id == "R8")

    _check("lens_interaction", _interact_named(manager, "Interact_R8Lens"))
    await _settle(1)
    _check("lens_acquired", state.has("r8_lens") and state.flag("R8Lens"))

    var bible := _find_named(manager.current_room, "Interact_R8Bible")
    _check("bible_interaction_exists", bible != null and bible.has_method("interact"))
    if bible != null and bible.has_method("interact"):
        bible.call("interact")
    await _settle(1)
    _check("lens_placed", state.puzzle_node("R8LensPlace") and not state.has("r8_lens"))

    if bible != null:
        player.global_position = bible.get("activation_center")
        Engine.time_scale = 100.0
        bible.call("interact")
        await _settle(2)
        _check("optical_started", state.puzzle_node("R8RaiseTimer"))
        for _i in range(600):
            if state.puzzle_node("DoorR8"):
                break
            await process_frame
        Engine.time_scale = 1.0
    else:
        _check("optical_started", false)

    _check("secret_door_open", state.puzzle_node("DoorR8"))

    _check("shield_interaction", _interact_named(manager, "Interact_ShieldR8"))
    await _settle(1)
    _check("demo_complete", state.flag("demo_complete") and state.has("shield"))
    _check("final_persistent_hash", state.canonical_state_hash() == COMPLETE_HASH)
    _check("logical_audio_stream", events.captured_audio() == EXPECTED_AUDIO)

    scene.queue_free()
    _finish()
