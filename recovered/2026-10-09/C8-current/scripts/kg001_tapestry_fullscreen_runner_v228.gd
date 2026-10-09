extends SceneTree
var failed:Array[String]=[]
func ck(n:String,v:bool)->void:
    if not v: failed.append(n)
func _initialize()->void: call_deferred("_run")
func _run()->void:
    var p=load("res://main.tscn"); ck("main",p is PackedScene)
    if not p is PackedScene: return finish()
    var s=p.instantiate(); root.add_child(s); current_scene=s
    await process_frame; await process_frame
    var rm=s.get_node("RoomManager"); var st=root.get_node("DemoState"); st.reset_all()
    var specs=[["R1","Interact_r3t1","tapestry_piece_1","R3T1_0.png"],["R8","Interact_r8t3","tapestry_piece_3","R8T3_0.png"],["R8","Interact_r8t4","tapestry_piece_4","R8T4_0.png"]]
    for q in specs:
        rm.load_room(q[0],false); await process_frame; await process_frame
        var a=rm.current_room.get_node_or_null(q[1]); ck(q[2]+"_area",a!=null)
        if a!=null: a.call("interact"); await process_frame
        ck(q[2]+"_inventory",st.has(q[2]))
        ck(q[2]+"_preview",PickupPreview.active and PickupPreview.image.texture.resource_path.ends_with(q[3]))
        if PickupPreview.active:
            ck(q[2]+"_640x480",PickupPreview.image.texture.get_size()==Vector2(640,480))
        PickupPreview.dismiss()
    finish()
func finish()->void:
    print("OPENAZRAEL_TAPESTRY_FULLSCREEN_V228 "+JSON.stringify({"status":"PASS" if failed.is_empty() else "FAIL","failed":failed,"authority":"CORPUS_AUTHORITY","screens":["R3T1_0.PCX","R8T3_0.PCX","R8T4_0.PCX"]}))
    quit(0 if failed.is_empty() else 1)
