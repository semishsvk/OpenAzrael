extends Node
func _ready()->void:
    if OS.get_environment("OPENAZRAEL_UI_NATIVE").is_empty(): return
    call_deferred("_capture")
func shot(path:String)->void:
    await get_tree().process_frame
    RenderingServer.force_draw(false,0.0)
    var img:=get_viewport().get_texture().get_image()
    var e:=img.save_png(path)
    if e!=OK: push_error("capture failed "+str(e))
func _capture()->void:
    await get_tree().process_frame
    var main:=get_tree().current_scene
    var menu:=main.get_node_or_null("LegacyMenuV145") if main else null
    if menu==null:
        push_error("LegacyMenuV145 not found"); get_tree().quit(2); return
    menu.call("_dismiss_title")
    await shot(OS.get_environment("OPENAZRAEL_UI_NATIVE")+"/HUD.png")
    menu.call("_set_service",true)
    await shot(OS.get_environment("OPENAZRAEL_UI_NATIVE")+"/SERVICE.png")
    print("OPENAZRAEL_UI_NATIVE_V210 ",JSON.stringify({"status":"PASS","viewport":[get_viewport().size.x,get_viewport().size.y]}))
    get_tree().quit(0)