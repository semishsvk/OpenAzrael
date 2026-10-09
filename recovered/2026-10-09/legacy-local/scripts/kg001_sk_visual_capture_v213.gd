extends SceneTree

func _settle(n:int=4)->void:
    for _i in range(n): await process_frame

func _shot(path:String)->bool:
    await process_frame
    RenderingServer.force_draw(false,0.0)
    return root.get_viewport().get_texture().get_image().save_png(path)==OK

func _initialize()->void:
    call_deferred("_run")

func _run()->void:
    var loc=root.get_node_or_null("LocalizationManager")
    var packed=load("res://main.tscn")
    if loc==null or not packed is PackedScene:
        print("OPENAZRAEL_SK_VISUAL_V213 "+JSON.stringify({"status":"FAIL","reason":"bootstrap"})); quit(2); return
    loc.set_locale("sk",false)
    var scene=packed.instantiate(); root.add_child(scene); await _settle(8)
    var menu=scene.get_node_or_null("LegacyMenuV145")
    if menu!=null: menu.call("_dismiss_title")
    await _settle(3)
    var hud=scene.get_node_or_null("HUD")
    if hud==null:
        print("OPENAZRAEL_SK_VISUAL_V213 "+JSON.stringify({"status":"FAIL","reason":"hud"})); quit(2); return
    hud.call("_on_conversation_requested",{"character":"Niamh","family":"1A"})
    await _settle(3)
    var panel=hud.find_child("DialoguePanelExperimentalSK", true, false)
    var label=panel.get_node_or_null("DialogueLabel") if panel else null
    var expected="Dobrý Bože. Čo si zač?"
    var text_value=String(label.text) if label else ""
    var outdir=OS.get_environment("OPENAZRAEL_CAPTURE_DIR")
    DirAccess.make_dir_recursive_absolute(outdir)
    var path=outdir.path_join("OpenAzrael_SK_Niamh_v215.png")
    var ok=panel!=null and panel.visible and text_value==expected and await _shot(path)
    print("OPENAZRAEL_SK_VISUAL_V215 "+JSON.stringify({"status":"PASS" if ok else "FAIL","text":text_value,"expected":expected,"panel_size":[panel.size.x,panel.size.y] if panel else [],"capture":path}))
    scene.queue_free(); await process_frame; quit(0 if ok else 1)
