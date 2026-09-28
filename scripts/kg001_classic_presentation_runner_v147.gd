extends SceneTree

var failures: Array[String] = []
var checks := 0

func _check(name: String, ok: bool) -> void:
    checks += 1
    if not ok:
        failures.append(name)

func _settle(frames: int = 4) -> void:
    for _i in range(frames):
        await process_frame

func _run() -> void:
    var packed = load("res://main.tscn")
    _check("main_scene", packed is PackedScene)
    if not packed is PackedScene:
        _finish()
        return

    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle(8)

    var menu = scene.get_node_or_null("LegacyMenuV145")
    var hud = scene.get_node_or_null("HUD")
    _check("menu", menu != null)
    _check("hud", hud != null)
    if menu == null or hud == null:
        _finish(scene)
        return

    var root_control = menu.get("root_control")
    var classic_canvas = menu.get("classic_canvas")
    _check("menu_root", root_control is Control)
    _check("classic_canvas", classic_canvas is Control)

    for name in [
        "ClassicMatteLeftV147",
        "ClassicMatteRightV147",
        "ClassicMatteTopV147",
        "ClassicMatteBottomV147",
    ]:
        var matte = menu.find_child(name, true, false)
        _check("matte_exists:" + name, matte is ColorRect)
        if matte is ColorRect:
            _check("matte_black:" + name, (matte as ColorRect).color == Color.BLACK)
            _check("matte_nonnegative:" + name, (matte as ColorRect).size.x >= 0.0 and (matte as ColorRect).size.y >= 0.0)

    var frame: Rect2 = menu.call("classic_frame_rect")
    _check("frame_positive", frame.size.x > 0.0 and frame.size.y > 0.0)
    _check("frame_aspect_4_3", absf(frame.size.x / frame.size.y - (4.0/3.0)) < 0.0001)

    var modern_panel = hud.get_node_or_null("Panel")
    _check("modern_panel", modern_panel is CanvasItem)
    if modern_panel is CanvasItem:
        _check("modern_panel_hidden", not (modern_panel as CanvasItem).visible)

    var candidate_panel = hud.find_child("CandidateDebugPanelV116", true, false)
    var audio_panel = hud.find_child("AudioDebugPanelV69", true, false)
    _check("candidate_debug_exists", candidate_panel is CanvasItem)
    _check("audio_debug_exists", audio_panel is CanvasItem)
    if candidate_panel is CanvasItem:
        _check("candidate_debug_default_hidden", not (candidate_panel as CanvasItem).visible)
    if audio_panel is CanvasItem:
        _check("audio_debug_default_hidden", not (audio_panel as CanvasItem).visible)

    var cursor_layer = hud.find_child("InteractionCursorLayerV146", true, false)
    _check("cursor_layer", cursor_layer is CanvasLayer)
    if cursor_layer is CanvasLayer:
        _check("cursor_above_menu", (cursor_layer as CanvasLayer).layer > menu.layer)

    _finish(scene)

func _finish(scene: Node = null) -> void:
    var out := {
        "schema":"openazrael.kg001.classic_presentation",
        "version":147,
        "status":"PASS" if failures.is_empty() else "FAIL",
        "checks":checks,
        "failed":failures,
        "logical_frame":[640,480],
        "aspect":"4:3",
    }
    print("OPENAZRAEL_KG001_CLASSIC_PRESENTATION_V147 " + JSON.stringify(out))
    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _initialize() -> void:
    call_deferred("_run")
