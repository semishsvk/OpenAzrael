extends SceneTree
func _initialize() -> void:
    var root := get_root()
    root.size = Vector2i(640,480)
    var rect := TextureRect.new()
    rect.position = Vector2.ZERO
    rect.size = Vector2(640,480)
    rect.texture = load("res://assets/ui/legacy_menu/TITLE.png")
    rect.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
    rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    rect.stretch_mode = TextureRect.STRETCH_KEEP
    root.add_child(rect)
    await process_frame
    RenderingServer.force_draw(false,0.0)
    var img := root.get_texture().get_image()
    var out := OS.get_environment("OPENAZRAEL_NATIVE_TITLE")
    var err := img.save_png(out)
    print("OPENAZRAEL_TITLE_NATIVE_V208 ", JSON.stringify({"status":"PASS" if err==OK else "FAIL","size":[img.get_width(),img.get_height()],"err":err}))
    rect.queue_free()
    await process_frame
    quit(0 if err==OK else 2)