extends SceneTree

const REQUIRED_ROOM := "res://assets/rooms/R7.glb"
const TONGS_AUDIO := "res://assets/audio/979TONGS.WAV"
const EXPECTED_STEPS := [
    "remove_room:R7Key",
    "play_sound:979TONGS.WAV",
    "add_room:R7Key",
    "remove_room:RustyTongR6",
    "remove_inventory:TONG6",
    "default_take:R7Key"
]

var failures: Array[String] = []
var check_count := 0
var captured_steps: Array[String] = []

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

func _on_demo_action_step(step: String) -> void:
    captured_steps.append(step)

func _finish(scene: Node = null, status_override: String = "") -> void:
    var status := status_override
    if status.is_empty():
        status = "PASS" if failures.is_empty() else "FAIL"
    var result := {
        "schema": "openazrael.kg001.well_tongs_animation",
        "version": 118,
        "status": status,
        "checks": check_count,
        "failed": failures,
        "captured_steps": captured_steps,
        "expected_steps": EXPECTED_STEPS,
        "scope": (
            "official-demo R7 well+tongs action stream: R7Key remove, "
            + "979TONGS, R7Key add, RustyTongR6 remove, TONG6 consume, "
            + "then default key take"
        ),
        "boundary": (
            "No transform Tween is invented because the recovered demo "
            + "action group contains no transform/rotation opcode."
        )
    }
    print("OPENAZRAEL_KG001_WELL_TONGS_V118 " + JSON.stringify(result))
    if scene != null:
        scene.queue_free()
    quit(0 if status == "PASS" else (2 if status.begins_with("BLOCKED") else 1))

func _run() -> void:
    var missing: Array[String] = []
    for path in [REQUIRED_ROOM, TONGS_AUDIO]:
        if not ResourceLoader.exists(path):
            missing.append(path)
    if not missing.is_empty():
        print("OPENAZRAEL_KG001_WELL_TONGS_V118 " + JSON.stringify({
            "schema": "openazrael.kg001.well_tongs_animation",
            "version": 118,
            "status": "BLOCKED_MISSING_ASSETS",
            "missing": missing
        }))
        quit(2)
        return

    var state = root.get_node_or_null("DemoState")
    var events = root.get_node_or_null("LegacyEvents")
    if state == null or events == null:
        failures.append("required_autoloads")
        _finish()
        return

    state.reset_all()
    events.set_capture_only(true)
    events.clear_capture()

    var stream = load(TONGS_AUDIO)
    _check("979tongs_stream_loads", stream != null)
    if stream != null:
        _check(
            "979tongs_duration_matches_demo",
            absf(stream.get_length() - 0.9501133786848073) < 0.002
        )

    var packed = load("res://main.tscn")
    if packed == null:
        failures.append("main_scene_load")
        _finish()
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

    var well_interact := _find_named(manager.current_room, "Interact_WellKey")
    var key_visual := _find_named(manager.current_room, "nibdyky01")
    _check("well_interaction_present", well_interact != null)
    _check("well_key_visual_present", key_visual is Node3D)
    if well_interact == null or not (key_visual is Node3D):
        _finish(scene)
        return

    well_interact.demo_action_step.connect(_on_demo_action_step)

    # Negative path: no tongs means no compiled action group is emitted.
    well_interact.call("interact")
    await _settle(1)
    _check("without_tongs_no_steps", captured_steps.is_empty())
    _check("without_tongs_no_key", not state.has("well_key"))
    _check("without_tongs_R7KeyTake_false", not state.puzzle_node("R7KeyTake"))
    _check("without_tongs_R7key_false", not state.flag("R7key"))
    _check("without_tongs_key_stays_visible", (key_visual as Node3D).visible)

    # Positive path: exact official-demo group plus the default TAKE completion.
    state.acquire("rusty_tongs")
    well_interact.call("interact")
    await _settle(1)

    _check("exact_demo_action_order", captured_steps == EXPECTED_STEPS)
    _check(
        "logical_979tongs_emitted",
        events.captured_audio() == ["979TONGS.WAV"]
    )
    _check("well_key_acquired", state.has("well_key"))
    _check("tongs_consumed", not state.has("rusty_tongs"))
    _check("R7KeyTake_set", state.puzzle_node("R7KeyTake"))
    _check("R7key_set", state.flag("R7key"))
    _check(
        "well_interaction_consumed",
        not is_instance_valid(well_interact) or well_interact.is_queued_for_deletion()
    )
    _check(
        "key_absent_after_default_take",
        is_instance_valid(key_visual) and not (key_visual as Node3D).visible
    )

    _finish(scene)
