extends SceneTree

var failures: Array[String] = []
var checks := 0

func _check(name: String, ok: bool) -> void:
    checks += 1
    if not ok:
        failures.append(name)

func _settle(frames: int = 3) -> void:
    for _i in range(frames):
        await process_frame

func _run() -> void:
    for path in [
        "res://assets/ui/mice/POINTER.png",
        "res://assets/ui/mice/TAKE.png",
        "res://assets/ui/legacy_menu/HUD3.png",
        "res://assets/ui/legacy_menu/SAVE13.png",
    ]:
        _check("asset:" + path, ResourceLoader.exists(path))

    var packed = load("res://main.tscn")
    _check("main_scene", packed is PackedScene)
    if not packed is PackedScene:
        _finish()
        return

    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle(6)

    var hud = scene.get_node_or_null("HUD")
    var menu = scene.get_node_or_null("LegacyMenuV145")
    _check("hud", hud != null)
    _check("menu", menu != null)
    if hud == null or menu == null:
        _finish(scene)
        return

    var cursor = hud.find_child("InteractionCursorV143", true, false)
    var cursor_layer = hud.find_child("InteractionCursorLayerV146", true, false)
    _check("cursor", cursor is TextureRect)
    _check("cursor_layer", cursor_layer is CanvasLayer)
    if cursor_layer is CanvasLayer:
        _check("cursor_layer_above_menu", (cursor_layer as CanvasLayer).layer > menu.layer)
        _check("cursor_layer_100", (cursor_layer as CanvasLayer).layer == 100)

    # Force title modal in headless runner and verify world cursor is suppressed.
    menu.call("_show_title")
    _check("title_cursor_processes_while_paused", hud.can_process())
    cursor.position = Vector2(-9999, -9999)
    await _settle()
    _check("title_cursor_updates_naturally", cursor.position.x > -9999)
    _check("title_blocks_world", bool(menu.call("blocks_world_cursor")))
    _check("title_pointer", String(hud.get("interaction_cursor_id")) == "POINTER")
    menu.call("_dismiss_title")

    # Service panel must likewise force a neutral source pointer.
    menu.call("_set_service", true)
    _check("service_cursor_processes_while_paused", hud.can_process())
    cursor.position = Vector2(-9999, -9999)
    await _settle()
    _check("service_cursor_updates_naturally", cursor.position.x > -9999)
    _check("service_blocks_world", bool(menu.call("blocks_world_cursor")))
    _check("service_pointer", String(hud.get("interaction_cursor_id")) == "POINTER")

    # All six source-label action regions are still reachable at the v145
    # canonical sample points, with no ambiguous action result.
    var origin := Vector2(235, 260)
    var samples := {
        "LOAD": Vector2(50,35),
        "SAVE": Vector2(60,100),
        "MUSIC": Vector2(120,45),
        "SFX": Vector2(120,80),
        "QUIT": Vector2(80,60),
        "CONFIRM": Vector2(40,130),
    }
    for action in samples:
        var got := String(menu.call("_service_action_at", origin + samples[action]))
        _check("service_action:" + action, got == action)

    menu.call("_set_service", false)
    _check("service_releases_world", not bool(menu.call("blocks_world_cursor")))

    _finish(scene)

func _finish(scene: Node = null) -> void:
    var out := {
        "schema":"openazrael.kg001.menu_cursor_context",
        "version":146,
        "status":"PASS" if failures.is_empty() else "FAIL",
        "checks":checks,
        "failed":failures,
        "cursor_layer":100,
        "menu_layer":50,
        "modal_cursor":"POINTER",
    }
    print("OPENAZRAEL_KG001_MENU_CURSOR_V146 " + JSON.stringify(out))
    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _initialize() -> void:
    call_deferred("_run")
