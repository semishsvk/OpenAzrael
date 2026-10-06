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
    if e:
        check("Eugene_production_movement_armed",e.movement_is_armed())
        var e_before:Vector3=e.global_position
        for tick in range(180):await physics_frame
        check("Eugene_production_moves_without_test_arming",e.global_position.distance_to(e_before)>1.0)
    m.load_room("R7",false);await process_frame
    scene.get_node("Player").teleport_eye_to(Vector3(17.51384,3.785862,-32.31179),Vector3(-0.773586,-0.179026,0.607878))
    m.call("_on_character_animation_requested",{"character":"Niamh","family":"NOLOOP1","target_object":"nibody","source_required":true,"next_family":"REST"})
    var n=m.current_room.find_child("SourceCharacter_Niamh",true,false)
    check("Niamh_runtime_spawn",n!=null)
    if n:
        var belly=n.get_node("NIBELLY");var before:Vector3=belly.position;var world_before:Vector3=belly.global_position
        m.call("_on_conversation_requested",{"character":"Niamh","family":"1A","source_required":true})
        var ui=scene.get_node("ConversationUIV208")
        check("dialogue_open",ui.active and paused)
        check("dialogue_above_menu",ui.layer>scene.get_node("LegacyMenuV145").layer)
        print("LAYOUT "+str(ui.panel.position)+" "+str(ui.panel.size)+" ROOT "+str(root.size)+" RECT "+str(ui.get_viewport().get_visible_rect()));check("dialogue_above_lower_HUD",ui.panel.position.y+ui.panel.size.y<=root.size.y*331.0/480.0+1)
        await create_timer(0.5).timeout
        check("Niamh_moves_while_dialogue_paused",belly.position.distance_to(before)>20)
        var rise:Vector3=belly.global_position-world_before
        check("Niamh_rises_vertically_out_of_well",rise.y>20 and Vector2(rise.x,rise.z).length()<0.1)
        check("Niamh_room_proxy_rotation_not_applied",n.basis.is_equal_approx(Basis.IDENTITY))
        await create_timer(0.6).timeout
        check("Niamh_enters_REST",n.get_node("SourceCharacterAnimation").current_animation=="REST")
        var head=n.find_child("NIHEAD1__mesh",true,false) as MeshInstance3D
        var cam=scene.get_node("Player/Camera3D") as Camera3D
        var head_center=(head.global_transform*head.get_aabb()).get_center()
        var query=PhysicsRayQueryParameters3D.create(cam.global_position,head_center,1)
        check("Niamh_head_not_occluded_by_well_pipes",cam.get_world_3d().direct_space_state.intersect_ray(query).is_empty())
        var pixel=cam.unproject_position(head_center)
        check("Niamh_head_inside_gameplay_view",Rect2(Vector2(225,108),Vector2(828,388)).has_point(pixel))
        check("dialogue_does_not_cover_Niamh_head",not Rect2(ui.panel.position,ui.panel.size).has_point(pixel))
    paused=false;scene.queue_free()
    print("V223_CHARACTER_PLACEMENT "+JSON.stringify({"status":"PASS" if failed.is_empty() else "FAIL","checks":checks,"failed":failed,"scope":"source keys and pose motion; no original runtime visual attestation"}))
    quit(0 if failed.is_empty() else 1)



