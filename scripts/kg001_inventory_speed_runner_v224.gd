extends SceneTree
var failures=[]
var checks=0
var out="F:/OpenRemaster/OpenAzrael/.tmp/kg001_c6_final_audit/inventory_geometry_v224/"
func ck(name:String,ok:bool):
    checks+=1
    if not ok:failures.append(name)
func _initialize():call_deferred("run_test")
func run_test():
    root.size=Vector2i(1280,720)
    var scene=load("res://main.tscn").instantiate();root.add_child(scene);current_scene=scene
    for i in range(6):await process_frame
    var state=root.get_node("DemoState");var menu=scene.get_node("LegacyMenuV145");menu.call("_dismiss_title")
    var manager=scene.get_node("RoomManager");var player=scene.get_node("Player");var probe=player.get_node("Camera3D/InteractionProbe")
    for spec in [["R1","r3t1","tapestry_piece_1"],["R8","r8t3","tapestry_piece_3"],["R8","r8t4","tapestry_piece_4"]]:
        if manager.current_room_id!=spec[0]:manager.load_room(spec[0],false)
        await physics_frame
        var area=manager.current_room.find_child("Interact_"+spec[1],true,false)
        ck(spec[1]+"_pickup_exists",area!=null)
        if not area:continue
        var eye=area.global_position+Vector3(0,35,45)
        player.teleport_eye_to(eye,(area.global_position-eye).normalized())
        await physics_frame
        ck(spec[1]+"_production_probe_targets_piece",probe.current_interactive()==area)
        var ev=InputEventKey.new();ev.keycode=KEY_E;ev.physical_keycode=KEY_E;ev.pressed=true;Input.parse_input_event(ev);Input.flush_buffered_events()
        await process_frame
        ev=InputEventKey.new();ev.keycode=KEY_E;ev.physical_keycode=KEY_E;ev.pressed=false;Input.parse_input_event(ev);Input.flush_buffered_events()
        await process_frame
        ck(spec[1]+"_inventory_changes_via_E",state.has(spec[2]))
        var snap=menu.debug_inventory_snapshot()
        ck(spec[1]+"_HUD_id_present",snap.item_ids.has(spec[2]))
        ck(spec[1]+"_source_name_visible",snap.visible_labels.has("Tapestry Piece"))
        ck(spec[1]+"_no_unknown_item",not snap.unknown_ids.has(spec[2]))
        ck(spec[1]+"_world_piece_hidden",manager.current_room.find_child(spec[1],true,false).visible==false)
        if DisplayServer.get_name()!="headless":
            await RenderingServer.frame_post_draw
            root.get_texture().get_image().save_png(out+spec[1]+"_inventory.png")
    var snap=menu.debug_inventory_snapshot()
    ck("all_three_inventory_ids",snap.item_ids.size()==3)
    ck("all_three_complete_names",snap.labels==["Tapestry Piece","Tapestry Piece","Tapestry Piece"])
    ck("all_name_glyphs_rendered",snap.glyph_node_count==39)
    for i in range(menu.inventory_text_layer.get_child_count()):
        var glyph=menu.inventory_text_layer.get_child(i)
        ck("glyph_inside_inventory_"+str(i),glyph.position.x+glyph.size.x*glyph.scale.x<=103.01)
    # Controller clock test in clear space isolates the FPS multiplier defect.
    var distances=[]
    for ticks in [30,60,120]:
        var npc=CharacterBody3D.new();npc.set_script(load("res://scripts/eugene_controller_v193.gd"));root.add_child(npc)
        npc.set_physics_process(false);npc.configure(Vector3.RIGHT,null,null)
        for tick in range(ticks):npc.call("_physics_process",1.0/float(ticks))
        distances.append(npc.global_position.x)
        ck("NPC_seconds_speed_"+str(ticks),absf(npc.global_position.x-12.0)<0.001)
        npc.queue_free()
    var result={"status":"PASS" if failures.is_empty() else "FAIL","checks":checks,"failed":failures,"inventory":snap,"NPC_distance_per_second_30_60_120_ticks":distances,"source_pacing_attested":false,"pickup_test_scope":"Production E input and interaction probe; camera relocated for isolated regression, not a physical full-demo route"}
    var f=FileAccess.open(out+("headless" if DisplayServer.get_name()=="headless" else "GPU")+"_inventory_speed.json",FileAccess.WRITE);f.store_string(JSON.stringify(result,"  "))
    print("V224_INVENTORY_SPEED "+JSON.stringify(result))
    scene.queue_free();paused=false;quit(0 if failures.is_empty() else 1)


