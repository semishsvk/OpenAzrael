extends SceneTree

const STATES := ["TITLE","HUD","SERVICE"]
var output_dir := ""

func _settle(frames: int = 8) -> void:
    for _i in range(frames):
        await process_frame

func _capture(name: String) -> String:
    await process_frame
    RenderingServer.force_draw(false, 0.0)
    var texture := root.get_viewport().get_texture()
    if texture == null:
        return ""
    var image := texture.get_image()
    if image == null or image.is_empty():
        return ""
    var base := output_dir
    if base.is_empty():
        base = ProjectSettings.globalize_path("user://")
    DirAccess.make_dir_recursive_absolute(base)
    var path := base.path_join("OpenAzrael_Godot_v206_" + name + ".png")
    var err := image.save_png(path)
    if err != OK:
        return ""
    return path

func _run() -> void:
    output_dir = OS.get_environment("OPENAZRAEL_CAPTURE_DIR")
    var packed = load("res://main.tscn")
    if not packed is PackedScene:
        print("OPENAZRAEL_GRAPHICAL_MENU_V206 " + JSON.stringify({"status":"FAIL","reason":"main_scene"}))
        quit(2)
        return

    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle(12)
    var menu = scene.get_node_or_null("LegacyMenuV145")
    if menu == null:
        print("OPENAZRAEL_GRAPHICAL_MENU_V206 " + JSON.stringify({"status":"FAIL","reason":"menu"}))
        quit(2)
        return

    var files := {}
    files["TITLE"] = await _capture("Title")

    menu.call("_dismiss_title")
    await _settle(12)
    files["HUD"] = await _capture("HUD")

    menu.call("_set_service", true)
    await _settle(8)
    files["SERVICE"] = await _capture("Service")

    var ok := true
    for state in STATES:
        ok = ok and not String(files.get(state, "")).is_empty()
    print("OPENAZRAEL_GRAPHICAL_MENU_V206 " + JSON.stringify({
        "status":"PASS" if ok else "FAIL",
        "version":206,
        "states":STATES,
        "files":files,
        "viewport":[root.get_viewport().get_visible_rect().size.x, root.get_viewport().get_visible_rect().size.y],
        "source_ui":"ATDEMO PCX-derived PNG only",
    }))
    scene.queue_free()
    quit(0 if ok else 1)

func _initialize() -> void:
    call_deferred("_run")
