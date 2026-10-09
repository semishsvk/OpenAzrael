extends SceneTree
const Menu=preload("res://scripts/legacy_menu_runtime_v145.gd")
func shot(path:String)->void:
    await process_frame
    RenderingServer.force_draw(false,0.0)
    var img:=get_root().get_texture().get_image()
    var e:=img.save_png(path)
    if e!=OK: push_error("capture failed "+str(e))
func _initialize()->void:
    await process_frame
    await process_frame
    get_root().size=Vector2i(640,480)
    var main=load("res://main.tscn").instantiate()
    get_root().add_child(main)
    await process_frame
    var menu=main.get_node_or_null("LegacyMenuV145")
    if menu==null:
        for c in main.get_children():
            if c is Menu: menu=c; break
    if menu==null:
        push_error("LegacyMenu not found"); quit(2); return
    menu.call("_dismiss_title")
    await shot(OS.get_environment("OPENAZRAEL_UI_NATIVE")+"/HUD.png")
    menu.call("_set_service",true)
    await shot(OS.get_environment("OPENAZRAEL_UI_NATIVE")+"/SERVICE.png")
    print("OPENAZRAEL_UI_NATIVE_V209 ",JSON.stringify({"status":"PASS","viewport":[640,480]}))
    main.queue_free(); await process_frame; quit(0)