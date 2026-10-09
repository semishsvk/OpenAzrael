extends SceneTree
var failed:Array[String]=[]
func ck(v:bool,n:String)->void:
    if not v: failed.append(n)
func _initialize()->void: call_deferred("_run")
func _run()->void:
    var packed=load("res://main.tscn") as PackedScene
    var scene=packed.instantiate(); root.add_child(scene)
    await process_frame; await process_frame
    var m=scene.get_node("RoomManager")
    m.load_room("R7",false); await process_frame
    m.call("_on_character_animation_requested",{"character":"Niamh","family":"NOLOOP1","target_object":"nibody","source_required":true,"next_family":"REST"})
    var n=m.current_room.find_child("SourceCharacter_Niamh",true,false)
    ck(n!=null,"spawn")
    if n==null: quit(1); return
    var ap=n.get_node("SourceCharacterAnimation") as AnimationPlayer
    var belly=n.get_node("NIBELLY") as Node3D
    ck(ap.has_animation(&"NOLOOP1") and ap.has_animation(&"REST"),"entry_clips")
    await create_timer(1.1).timeout
    ck(ap.current_animation=="REST","rest_after_entry")
    var rest_y=belly.position.y
    m.call("_on_conversation_requested",{"character":"Niamh","family":"1A","source_required":true})
    await process_frame
    var ui=scene.get_node("ConversationUIV208")
    ck(ui.active and ui.choices.size()==2,"dialog_open_two_visible")
    var exit_index=-1
    for i in range(ui.choices.size()):
        if String(ui.choices[i].get("id",""))=="999": exit_index=i
    ck(exit_index>=0,"exit_999_present")
    if exit_index>=0:
        ui.selected=exit_index; ui.call("_show_response",ui.choices[exit_index])
        ck(ui.response_mode,"exit_response")
        var ev=InputEventKey.new(); ev.keycode=KEY_ENTER; ev.pressed=true
        ui.call("_unhandled_input",ev)
        ck(not ui.active,"exit_closes_dialog")
        ck(ap.current_animation=="NOLOOP2","exit_starts_noloop2")
        await create_timer(1.1).timeout
        ck(abs(belly.position.y - (-92.2139)) < 0.2,"returns_frame0_y")
        ck(rest_y > -20.0,"rest_above_well")
    var receipt={"schema":"openazrael.kg001.niamh_scene_fidelity_runtime","version":256,"status":"PASS" if failed.is_empty() else "FAIL","failed":failed,"rest_y":rest_y,"exit_y":belly.position.y,"source_exit_record":"999","source_exit_family":"NOLOOP2"}
    var f=FileAccess.open("res://.tmp/niamh_scene_v256_receipt.json",FileAccess.WRITE)
    if f: f.store_string(JSON.stringify(receipt,"  ")); f.close()
    print("OPENAZRAEL_NIAMH_SCENE_V256 "+JSON.stringify(receipt))
    paused=false; scene.queue_free(); quit(0 if failed.is_empty() else 1)
