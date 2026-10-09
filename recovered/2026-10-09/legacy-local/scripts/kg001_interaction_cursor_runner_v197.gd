extends SceneTree

const MANIFEST := "res://data/ui/legacy_cursor_manifest_v143.json"
var failures: Array[String] = []
var checks := 0

func _check(name: String, ok: bool) -> void:
    checks += 1
    if not ok:
        failures.append(name)

func _settle(frames: int = 3) -> void:
    for _i in range(frames):
        await process_frame

func _find(node: Node, wanted: String) -> Node:
    if String(node.name) == wanted:
        return node
    for child in node.get_children():
        var found := _find(child, wanted)
        if found != null:
            return found
    return null

func _cursor(node: Node) -> String:
    if node == null or not node.has_method("interaction_cursor_id"):
        return ""
    return String(node.call("interaction_cursor_id"))

func _load_room(manager, room_id: String) -> void:
    manager.transition_cooldown = 999.0
    manager.load_room(room_id, false)
    await _settle(3)

func _run() -> void:
    _check("manifest_exists", FileAccess.file_exists(MANIFEST))
    if not FileAccess.file_exists(MANIFEST):
        _finish()
        return
    var manifest = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST))
    _check("manifest_valid", manifest is Dictionary)
    if not manifest is Dictionary:
        _finish()
        return

    _check("source_cursor_count", int(manifest.get("source_file_count", 0)) == 35)
    for filename in manifest.get("files", {}).keys():
        var spec: Array = manifest["files"][filename]
        var stem := String(filename).get_basename()
        var path := "res://assets/ui/mice/" + stem + ".png"
        _check("cursor_exists:" + stem, ResourceLoader.exists(path))
        if ResourceLoader.exists(path):
            var tex := load(path) as Texture2D
            _check("cursor_texture:" + stem, tex != null)
            if tex != null:
                _check("cursor_width:" + stem, int(tex.get_width()) == int(spec[2]))
                _check("cursor_height:" + stem, int(tex.get_height()) == int(spec[3]))

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
    await _settle(5)
    var manager = scene.get_node_or_null("RoomManager")
    var hud = scene.get_node_or_null("HUD")
    _check("manager", manager != null)
    _check("hud", hud != null)
    if manager == null:
        _finish(scene)
        return

    var cursor_rect = hud.find_child("InteractionCursorV143", true, false) if hud != null else null
    _check("hud_cursor_created", cursor_rect is TextureRect)
    if cursor_rect is TextureRect:
        _check("hud_pointer_texture_loaded", (cursor_rect as TextureRect).texture != null)
        _check("hud_nearest_filter", (cursor_rect as TextureRect).texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST)

    await _load_room(manager, "R1")
    _check("R1_tongs_TAKE", _cursor(_find(manager.current_room, "Interact_TONG6")) == "TAKE")
    _check("R1_parchment_TAKE", _cursor(_find(manager.current_room, "Interact_r1p1")) == "TAKE")
    _check("R1_tapestry1_TAKE", _cursor(_find(manager.current_room, "Interact_r3t1")) == "TAKE")
    _check("R1_door1_USE", _cursor(_find(manager.current_room, "Interact_doorcor01")) == "USE")
    _check("R1_door2_locked_CANT", _cursor(_find(manager.current_room, "Interact_doorcor2")) == "CANT")
    state.acquire("well_key")
    _check("R1_door2_unlocked_USE", _cursor(_find(manager.current_room, "Interact_doorcor2")) == "USE")

    state.reset_all()
    await _load_room(manager, "R7")
    _check("R7_key_without_tongs_CANT", _cursor(_find(manager.current_room, "Interact_WellKey")) == "CANT")
    _check("R7_lever_PULL", _cursor(_find(manager.current_room, "Interact_well_lev02")) == "PULL")
    _check("R7_wheel_ROT", _cursor(_find(manager.current_room, "Interact_well_weel3")) == "ROT")
    state.acquire("rusty_tongs")
    _check("R7_key_with_tongs_USE", _cursor(_find(manager.current_room, "Interact_WellKey")) == "USE")

    state.reset_all()
    await _load_room(manager, "R8")
    _check("R8_piece3_TAKE", _cursor(_find(manager.current_room, "Interact_r8t3")) == "TAKE")
    _check("R8_piece4_TAKE", _cursor(_find(manager.current_room, "Interact_r8t4")) == "TAKE")
    _check("R8_lens_submerged_CANT", _cursor(_find(manager.current_room, "Interact_R8Lens")) == "CANT")
    _check("R8_bible_without_lens_CANT", _cursor(_find(manager.current_room, "Interact_R8Bible")) == "CANT")
    _check("R8_tapestry_ROT", _cursor(_find(manager.current_room, "Interact_R8Tapestry2")) == "ROT")
    _check("R8_frame2_empty_CANT", _cursor(_find(manager.current_room, "Interact_tapframe2")) == "CANT")
    state.set_flag("R8BathDrain")
    _check("R8_lens_drained_TAKE", _cursor(_find(manager.current_room, "Interact_R8Lens")) == "TAKE")
    state.acquire("r8_lens")
    _check("R8_bible_with_lens_USE", _cursor(_find(manager.current_room, "Interact_R8Bible")) == "USE")
    state.acquire("tapestry_piece_1")
    _check("R8_frame2_with_piece_USE", _cursor(_find(manager.current_room, "Interact_tapframe2")) == "USE")

    _finish(scene)

func _finish(scene: Node = null) -> void:
    var out := {
        "schema": "openazrael.kg001.interaction_cursor_runtime",
        "version": 197,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": checks,
        "failed": failures,
        "source_cursor_count": 35,
        "active_runtime_icons": ["POINTER","TAKE","USE","PULL","ROT","CANT"],
        "b_variant_semantics": "HOLD_UNRESOLVED",
    }
    print("OPENAZRAEL_KG001_CURSOR_V197 " + JSON.stringify(out))
    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _initialize() -> void:
    call_deferred("_run")
