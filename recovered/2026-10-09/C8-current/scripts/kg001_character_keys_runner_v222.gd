extends SceneTree
var failed=[]
var checks=0
func check(name:String,ok:bool):
    checks+=1
    if not ok:failed.append(name)
func _initialize():call_deferred("_run")
func _run():
    root.size=Vector2i(1280,720)
    for character in ["Niamh","Eugene","EugenB"]:
        var families=["NOLOOP1","REST","NOLOOP2"] if character=="Niamh" else ["REST","RUN","ATTACK","SHOT","DEATH_TWITCH","DEAD"]
        for family in families:
            var clip=load("res://assets/characters/"+character+"/"+family+".tres") as Animation
            check(character+family+"_loaded",clip!=null)
            if clip:
                check(character+family+"_tracks",clip.get_track_count()>0)
                for track in range(clip.get_track_count()):check(character+family+"_keys_"+str(track),clip.track_get_key_count(track)>0)
    var scene=load("res://main.tscn").instantiate();root.add_child(scene);current_scene=scene
    for i in range(5):await process_frame
    scene.get_node("LegacyMenuV145").call("_dismiss_title")
    var m=scene.get_node("RoomManager")
    var e=m.current_room.find_child("SourceCharacter_Eugene",true,false)
    check("Eugene_runtime_spawn",e!=null)
    if e:check("Eugene_source_rest_scale",e.get_node("Eugene_Model/EUBUM").scale.distance_to(Vector3.ONE*0.1)<0.001)
    m.load_room("R7",false);await process_frame
    m.call("_on_character_animation_requested",{"character":"Niamh","family":"NOLOOP1","target_object":"nibody","source_required":true,"next_family":"REST"})
    var n=m.current_room.find_child("SourceCharacter_Niamh",true,false)
    check("Niamh_runtime_spawn",n!=null)
    if n:
        var belly=n.get_node("NIBELLY");var before:Vector3=belly.position
        m.call("_on_conversation_requested",{"character":"Niamh","family":"1A","source_required":true})
        var ui=scene.get_node("ConversationUIV208")
        check("dialogue_open",ui.active and paused)
        check("dialogue_above_menu",ui.layer>scene.get_node("LegacyMenuV145").layer)
        print("LAYOUT "+str(ui.panel.position)+" "+str(ui.panel.size)+" ROOT "+str(root.size)+" RECT "+str(ui.get_viewport().get_visible_rect()));check("dialogue_above_lower_HUD",ui.panel.position.y+ui.panel.size.y<=root.size.y*331.0/480.0+1)
        await create_timer(0.5).timeout
        check("Niamh_moves_while_dialogue_paused",belly.position.distance_to(before)>20)
        await create_timer(0.6).timeout
        check("Niamh_enters_REST",n.get_node("SourceCharacterAnimation").current_animation=="REST")
    paused=false;scene.queue_free()
    print("V222_CHARACTER_KEYS "+JSON.stringify({"status":"PASS" if failed.is_empty() else "FAIL","checks":checks,"failed":failed,"scope":"source keys and pose motion; no original runtime visual attestation"}))
    quit(0 if failed.is_empty() else 1)



