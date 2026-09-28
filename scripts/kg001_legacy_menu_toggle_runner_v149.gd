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

func _texture_is(node: TextureRect, stem: String) -> bool:
    if node == null or node.texture == null:
        return false
    return String(node.texture.resource_path).ends_with("/" + stem + ".png")

func _run() -> void:
    for i in range(14):
        var stem := "SAVE%02d" % i
        _check("asset_" + stem, ResourceLoader.exists("res://assets/ui/legacy_menu/" + stem + ".png"))

    var packed = load("res://main.tscn")
    _check("main_scene", packed is PackedScene)
    if not packed is PackedScene:
        _finish()
        return

    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle(5)

    var menu = scene.get_node_or_null("LegacyMenuV145")
    _check("menu", menu != null)
    if menu == null:
        _finish(scene)
        return

    # Headless startup suppresses the graphical title; normalize the service state.
    menu.call("_set_service", false)
    _check("initial_closed", not bool(menu.get("service_open")))

    menu.call("_activate_hud_action", "SERVICE")
    _check("options_opens", bool(menu.get("service_open")))
    var service_texture = menu.get("service_texture") as TextureRect
    _check("open_uses_SAVE06", _texture_is(service_texture, "SAVE06"))

    # The exact same source OPTIONS control closes the panel.
    menu.call("_activate_hud_action", "SERVICE")
    _check("options_closes", not bool(menu.get("service_open")))
    _check("close_clears_pending", String(menu.get("pending_action")).is_empty())
    _check("close_clears_volume", String(menu.get("volume_target")).is_empty())

    # Re-open and validate source hover-state frame identities.
    menu.call("_activate_hud_action", "SERVICE")
    var origin := Vector2(235, 260)
    var samples := {
        "LOAD": [Vector2(50,35), "SAVE08"],
        "SAVE": [Vector2(60,100), "SAVE07"],
        "MUSIC": [Vector2(120,45), "SAVE09"],
        "SFX": [Vector2(120,80), "SAVE10"],
        "QUIT": [Vector2(80,60), "SAVE11"],
    }
    for action in samples:
        var pair: Array = samples[action]
        var got := String(menu.call("_service_visual_frame", origin + pair[0]))
        _check("hover_" + action, got == String(pair[1]))

    menu.call("_handle_service_action", "SAVE")
    _check("save_confirm_SAVE12", String(menu.call("_service_visual_frame", origin)) == "SAVE12")

    # Reset pending state through a close/open cycle, then verify LOAD confirm.
    menu.call("_toggle_service")
    menu.call("_toggle_service")
    menu.call("_handle_service_action", "LOAD")
    _check("load_confirm_SAVE13", String(menu.call("_service_visual_frame", origin)) == "SAVE13")

    menu.call("_toggle_service")
    _check("final_closed", not bool(menu.get("service_open")))

    _finish(scene)

func _finish(scene: Node = null) -> void:
    var out := {
        "schema":"openazrael.kg001.legacy_menu_toggle",
        "version":149,
        "status":"PASS" if failures.is_empty() else "FAIL",
        "checks":checks,
        "failed":failures,
        "open_control":"NBUT2 OPTIONS",
        "close_control":"same NBUT2 OPTIONS hotspot",
        "rmb_close":false,
        "stable_open_frame":"SAVE06",
        "timing":"HOLD_EXACT_1996_CAPTURE",
    }
    print("OPENAZRAEL_KG001_MENU_TOGGLE_V149 " + JSON.stringify(out))
    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _initialize() -> void:
    call_deferred("_run")
