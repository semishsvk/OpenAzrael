extends SceneTree

const SaveSystem = preload("res://scripts/legacy_save_system_v145.gd")
var failures: Array[String] = []
var checks := 0

func _check(name: String, ok: bool) -> void:
    checks += 1
    if not ok:
        failures.append(name)

func _settle(frames: int = 2) -> void:
    for _i in range(frames):
        await process_frame

func _labels(menu: Node) -> Array:
    var snap: Dictionary = menu.call("debug_inventory_snapshot")
    return snap.get("labels", [])

func _ids(menu: Node) -> Array:
    var snap: Dictionary = menu.call("debug_inventory_snapshot")
    return snap.get("item_ids", [])

func _run() -> void:
    var state = root.get_node_or_null("DemoState")
    var events = root.get_node_or_null("LegacyEvents")
    var packed = load("res://main.tscn")
    _check("state", state != null)
    _check("events", events != null)
    _check("main", packed is PackedScene)
    if state == null or events == null or not packed is PackedScene:
        _finish()
        return

    state.reset_all()
    events.call("set_capture_only", true)
    var scene = packed.instantiate()
    root.add_child(scene)
    current_scene = scene
    await _settle(5)

    var menu = scene.get_node_or_null("LegacyMenuV145")
    var manager = scene.get_node_or_null("RoomManager")
    var player = scene.get_node_or_null("Player")
    _check("menu", menu != null)
    _check("manager", manager != null)
    _check("player", player is CharacterBody3D)
    if menu == null or manager == null or not player is CharacterBody3D:
        _finish(scene)
        return

    var initial: Dictionary = menu.call("debug_inventory_snapshot")
    _check("inventory_rect", initial.get("rect", []) == [70.0, 345.0, 103.0, 69.0])
    _check("source_font_cell", initial.get("font_cell", []) == [10.0, 12.0])
    _check("source_font_first_codepoint", int(initial.get("font_first_codepoint", -1)) == 35)
    _check("source_font_cell_count", int(initial.get("font_cell_count", -1)) == 138)
    _check("source_font_fidelity", String(initial.get("font_fidelity", "")) == "SOURCE_INVFONT_FIXED_CELL_MAP")
    _check("initial_empty", _labels(menu).is_empty())

    state.acquire("rusty_tongs")
    await _settle()
    _check("tongs_visible", _ids(menu) == ["rusty_tongs"] and _labels(menu) == ["Rusty tongs"])

    state.remove("rusty_tongs")
    state.acquire("well_key")
    await _settle()
    _check("tongs_removed_key_visible", _ids(menu) == ["well_key"] and _labels(menu) == ["Key"])

    state.acquire("r8_lens")
    await _settle()
    _check("lens_visible", _ids(menu) == ["well_key", "r8_lens"])

    events.call("run", "R8_LENS_PLACE")
    await _settle()
    _check("lens_removed_by_event", _ids(menu) == ["well_key"])

    events.call("run", "R8_TAKE_SHIELD")
    await _settle()
    _check("shield_added_by_event", _ids(menu) == ["well_key", "shield"])
    _check("shield_label", _labels(menu) == ["Key", "Shield"])

    manager.call("load_room", "R8", false)
    await _settle()
    player.global_position = Vector3(12.0, 34.0, -56.0)
    player.rotation.y = 0.25
    player.set("pitch", -0.1)
    _check("save_slot", SaveSystem.save_slot(0, manager, player))

    state.reset_all()
    await _settle()
    _check("reset_clears_hud", _labels(menu).is_empty())

    _check("load_slot", SaveSystem.load_slot(0, manager, player))
    await _settle(4)
    _check("load_restores_inventory_ids", _ids(menu) == ["well_key", "shield"])
    _check("load_restores_inventory_labels", _labels(menu) == ["Key", "Shield"])

    state.acquire("unmapped_future_item")
    await _settle()
    var unknown: Dictionary = menu.call("debug_inventory_snapshot")
    _check("unknown_not_rendered", _labels(menu) == ["Key", "Shield"])
    _check("unknown_reported", unknown.get("unknown_ids", []) == ["unmapped_future_item"])

    var save_path := SaveSystem.slot_path(0)
    if FileAccess.file_exists(save_path):
        DirAccess.remove_absolute(ProjectSettings.globalize_path(save_path))

    events.call("set_capture_only", false)
    _finish(scene)

func _finish(scene: Node = null) -> void:
    var out := {
        "schema": "openazrael.kg001.inventory_hud_runtime",
        "version": 157,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": checks,
        "failed": failures,
        "source_of_truth": "DemoState.inventory",
        "inventory_rect": [70, 345, 103, 69],
        "font_fidelity": "SOURCE_INVFONT_FIXED_CELL_MAP",
    }
    print("OPENAZRAEL_KG001_INVENTORY_HUD_V157 " + JSON.stringify(out))
    if scene != null:
        scene.queue_free()
    await process_frame
    quit(0 if failures.is_empty() else 1)

func _initialize() -> void:
    call_deferred("_run")
