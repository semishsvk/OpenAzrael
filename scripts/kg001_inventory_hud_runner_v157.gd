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

func _floor_probe(scene: Node3D, player: CharacterBody3D) -> Dictionary:
    var ray_from := player.global_position + Vector3.UP * 8.0
    var ray_to := player.global_position + Vector3.DOWN * 72.0
    var query := PhysicsRayQueryParameters3D.create(ray_from, ray_to, 1)
    query.exclude = [player.get_rid()]
    query.hit_back_faces = true
    var hit := scene.get_world_3d().direct_space_state.intersect_ray(query)
    if hit.is_empty():
        return {
            "supported": false,
            "player_position": [
                player.global_position.x,
                player.global_position.y,
                player.global_position.z
            ]
        }
    var floor_position := hit.get("position", Vector3.ZERO) as Vector3
    var gap := player.global_position.y - floor_position.y
    return {
        "supported": gap >= -4.0 and gap <= 24.0,
        "gap": gap,
        "player_position": [
            player.global_position.x,
            player.global_position.y,
            player.global_position.z
        ],
        "floor_position": [
            floor_position.x, floor_position.y, floor_position.z
        ],
        "collider": (
            String((hit.get("collider") as Object).get("name"))
            if hit.get("collider") != null
            else ""
        )
    }

func _verify_floor_support(
    scene: Node3D,
    player: CharacterBody3D,
    required_frames: int = 30
) -> bool:
    for _i in range(required_frames):
        await physics_frame
        var probe := _floor_probe(scene, player)
        if not bool(probe.get("supported", false)):
            failures.append("R8_portal_support:" + JSON.stringify(probe))
            return false
    return true

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

    var font_path := "res://assets/ui/legacy_menu/INVFONT.png"
    _check("source_font_exists", ResourceLoader.exists(font_path))
    if ResourceLoader.exists(font_path):
        var font_tex := load(font_path) as Texture2D
        _check("source_font_texture", font_tex != null)
        if font_tex != null:
            _check("source_font_width", font_tex.get_width() == 1380)
            _check("source_font_height", font_tex.get_height() == 12)

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
    _check("tongs_source_glyph_count", int(menu.call("debug_inventory_snapshot").get("glyph_node_count", -1)) == 10)

    state.remove("rusty_tongs")
    state.acquire("well_key")
    await _settle()
    _check("tongs_removed_key_visible", _ids(menu) == ["well_key"] and _labels(menu) == ["Key"])
    _check("key_source_glyph_count", int(menu.call("debug_inventory_snapshot").get("glyph_node_count", -1)) == 3)

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
    _check("key_shield_source_glyph_count", int(menu.call("debug_inventory_snapshot").get("glyph_node_count", -1)) == 9)

    _check(
        "R8_portal_entry",
        bool(manager.call("load_room_at_portal", "R8", "Object14", false))
    )
    _check(
        "R8_portal_support_30_frames",
        await _verify_floor_support(scene, player, 30)
    )
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
    var ambient = manager.get("legacy_audio")
    if ambient != null and ambient.has_method("clear_emitters"):
        ambient.call("clear_emitters")
    var music = root.get_node_or_null("CandidateMusic")
    if music != null:
        music.call("stop")
        var music_player = music.get_node_or_null("CandidateMusicPlayer")
        if music_player is AudioStreamPlayer:
            music_player.stop()
            music_player.stream = null
    # Godot command-line audio teardown is asynchronous. Give the audio thread
    # a short real-time grace period after clearing streams so shutdown does
    # not report the known AudioStreamPlayer/OggPacketSequence false leak.
    await create_timer(0.5).timeout
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
