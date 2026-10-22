extends SceneTree

const SaveSystem = preload("res://scripts/legacy_save_system_v145.gd")
var failures: Array[String] = []
var checks := 0

func _check(name: String, ok: bool) -> void:
    checks += 1
    if not ok:
        failures.append(name)

func _settle(frames: int = 3) -> void:
    for _i in range(frames):
        await process_frame

func _write_raw(path: String, text: String) -> bool:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        return false
    file.store_string(text)
    file.close()
    return true

func _guard_rejection(
    name: String,
    raw: String,
    state: Node,
    manager: Node,
    player: CharacterBody3D
) -> void:
    state.reset_all()
    state.acquire("save_compat_sentinel")
    manager.load_room("R8", false)
    player.global_position = Vector3(3.0, 4.0, 5.0)
    var state_before := String(state.call("canonical_state_hash"))
    var room_before := String(manager.current_room_id)
    var pos_before := player.global_position
    _check(name + ":write", _write_raw(SaveSystem.slot_path(0), raw))
    _check(name + ":rejected", not SaveSystem.load_slot(0, manager, player))
    _check(name + ":state_unchanged", String(state.call("canonical_state_hash")) == state_before)
    _check(name + ":room_unchanged", String(manager.current_room_id) == room_before)
    _check(name + ":position_unchanged", player.global_position.distance_to(pos_before) < 0.001)

func _run() -> void:
    var state = root.get_node_or_null("DemoState")
    var packed = load("res://main.tscn")
    _check("state", state != null)
    _check("main", packed is PackedScene)
    if state == null or not packed is PackedScene:
        _finish()
        return

    state.reset_all()
    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle(6)

    var manager = scene.get_node_or_null("RoomManager")
    var player = scene.get_node_or_null("Player")
    _check("manager", manager != null)
    _check("player", player is CharacterBody3D)
    if manager == null or not player is CharacterBody3D:
        _finish(scene)
        return

    manager.load_room("R1", false)
    await _settle(3)
    player.global_position = Vector3(12.5, 33.25, -77.5)
    player.rotation.y = 0.42
    player.set("pitch", -0.18)
    state.acquire("rusty_tongs")
    state.set_flag("R1Door1Open")
    _check("current_save_write", SaveSystem.save_slot(0, manager, player))
    var save_path := SaveSystem.slot_path(0)
    var canonical_text := FileAccess.get_file_as_string(save_path)
    var canonical = JSON.parse_string(canonical_text)
    _check("current_save_json", canonical is Dictionary)
    if not canonical is Dictionary:
        _finish(scene)
        return

    state.reset_all()
    manager.load_room("R8", false)
    player.global_position = Vector3(1, 2, 3)
    player.rotation.y = 0.0
    player.set("pitch", 0.0)
    _check("current_save_load", SaveSystem.load_slot(0, manager, player))
    _check("current_state_restored", state.has("rusty_tongs") and state.flag("R1Door1Open"))
    _check("current_room_restored", String(manager.current_room_id) == "R1")
    _check("current_position_restored", player.global_position.distance_to(Vector3(12.5, 33.25, -77.5)) < 0.01)
    _check("current_yaw_restored", absf(player.rotation.y - 0.42) < 0.001)
    _check("current_pitch_restored", absf(float(player.get("pitch")) + 0.18) < 0.001)

    var older: Dictionary = canonical.duplicate(true)
    older["version"] = SaveSystem.VERSION - 1
    _guard_rejection("older_version", JSON.stringify(older), state, manager, player)

    var unknown: Dictionary = canonical.duplicate(true)
    unknown["version"] = SaveSystem.VERSION + 1000
    _guard_rejection("unknown_version", JSON.stringify(unknown), state, manager, player)

    _guard_rejection("corrupt_json", "{this is not valid json", state, manager, player)

    var wrong_schema: Dictionary = canonical.duplicate(true)
    wrong_schema["schema"] = "openazrael.unknown_save"
    _guard_rejection("wrong_schema", JSON.stringify(wrong_schema), state, manager, player)

    var bad_state: Dictionary = canonical.duplicate(true)
    bad_state["state"] = [999, [], [], [], []]
    _guard_rejection("incompatible_state_payload", JSON.stringify(bad_state), state, manager, player)

    if FileAccess.file_exists(save_path):
        DirAccess.remove_absolute(ProjectSettings.globalize_path(save_path))
    _finish(scene)

func _finish(scene: Node = null) -> void:
    var out := {
        "schema": "openazrael.kg001.save_compat_runtime",
        "version": 150,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": checks,
        "failed": failures,
        "save_schema": SaveSystem.SCHEMA,
        "save_version": SaveSystem.VERSION,
        "migration_available": false,
        "filename_pattern": "SAVE%d.dat",
        "negative_cases": [
            "older_version",
            "unknown_version",
            "corrupt_json",
            "wrong_schema",
            "incompatible_state_payload",
        ],
    }
    print("OPENAZRAEL_KG001_SAVE_COMPAT_V150 " + JSON.stringify(out))
    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _initialize() -> void:
    call_deferred("_run")
