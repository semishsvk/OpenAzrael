extends SceneTree
var failed:Array[String]=[]
var checks:=0
func ck(n:String,v:bool):
    checks+=1
    if not v: failed.append(n)
func _initialize(): call_deferred("_run")
func _run():
    var p=load("res://main.tscn")
    ck("main_scene_load",p!=null)
    if p==null: return finish()
    var s=p.instantiate(); root.add_child(s); current_scene=s
    await process_frame; await process_frame
    ck("player_present",s.has_node("Player"))
    ck("room_manager_present",s.has_node("RoomManager"))
    ck("hud_present",s.has_node("HUD"))
    ck("legacy_menu_present",s.has_node("LegacyMenuV145"))
    ck("conversation_ui_present",s.has_node("ConversationUIV208"))
    for a in ["move_forward","move_back","move_left","move_right","interact","sprint"]:
        ck("input_"+a,InputMap.has_action(a))
    var rm=s.get_node("RoomManager")
    rm.call("_on_conversation_requested",{"character":"Niamh","family":"1A","source_required":true})
    await process_frame
    var ui=s.get_node("ConversationUIV208")
    ck("niamh_dialog_opens",bool(ui.get("active")))
    ck("niamh_dialog_choices",(ui.get("choices") as Array).size()==10)
    ui.call("_close")
    ck("niamh_dialog_closes",not bool(ui.get("active")))
    ck("world_unpaused_after_dialog",not paused)
    var e=rm.get_node_or_null("Entry Corridor (R1)/SourceCharacter_EugenB")
    ck("eugene_source_character",e!=null)
    if e!=null:
        var ap=e.get_node_or_null("SourceCharacterAnimation") as AnimationPlayer
        ck("eugene_animation_player",ap!=null)
        if ap!=null: ck("eugene_animation_root",String(ap.root_node)=="../EugenB_Model")
    finish()
func finish():
    print("OPENAZRAEL_PLAYER_FACING_V211 "+JSON.stringify({"schema":"openazrael.kg001.player_facing_acceptance","version":211,"status":"PASS" if failed.is_empty() else "FAIL","checks":checks,"failed":failed,"controls":"WASD + E interact"}))
    quit(0 if failed.is_empty() else 1)
