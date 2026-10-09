extends SceneTree
var failed:Array[String]=[]
func ck(n:String,v:bool)->void:
    if not v: failed.append(n)
func _initialize()->void: call_deferred("_run")
func _run()->void:
    var p=load("res://main.tscn")
    ck("main",p is PackedScene)
    if not p is PackedScene: return finish()
    var s=p.instantiate(); root.add_child(s); current_scene=s
    await process_frame; await process_frame
    var rm=s.get_node("RoomManager")
    var state=root.get_node("DemoState")
    state.reset_all(); rm.load_room("R1",false)
    await process_frame; await process_frame
    var parchment=rm.current_room.get_node_or_null("Interact_r1p1")
    var tapestry=rm.current_room.get_node_or_null("Interact_r3t1")
    ck("parchment_area",parchment!=null)
    ck("tapestry_area",tapestry!=null)
    if parchment!=null:
        ck("parchment_take_cursor",String(parchment.call("interaction_cursor_id"))=="TAKE")
        parchment.call("interact"); await process_frame
    ck("parchment_inventory",state.has("parchment_r1"))
    ck("parchment_world_removed",rm.current_room.get_node_or_null("Interact_r1p1")==null)
    ck("parchment_fullscreen_preview",PickupPreview.active and PickupPreview.image.texture.resource_path.ends_with("VSTPAP01.png"))
    PickupPreview.dismiss()
    if tapestry!=null:
        ck("tapestry_take_cursor",String(tapestry.call("interaction_cursor_id"))=="TAKE")
        tapestry.call("interact"); await process_frame
    ck("tapestry_inventory",state.has("tapestry_piece_1"))
    ck("tapestry_world_removed",rm.current_room.get_node_or_null("Interact_r3t1")==null)
    ck("tapestry_fullscreen_preview",PickupPreview.active and PickupPreview.image.texture.resource_path.ends_with("BAPTAPCE.png"))
    PickupPreview.dismiss()
    rm.load_room("R1",false); await process_frame; await process_frame
    ck("parchment_persistent",rm.current_room.get_node_or_null("Interact_r1p1")==null)
    ck("tapestry_persistent",rm.current_room.get_node_or_null("Interact_r3t1")==null)
    finish()
func finish()->void:
    print("OPENAZRAEL_R1_FLOOR_ORACLE_V225 "+JSON.stringify({"schema":"openazrael.kg001.r1_floor_oracle","version":225,"status":"PASS" if failed.is_empty() else "FAIL","failed":failed,"oracle_class":"VIDEO_REFERENCE+CORPUS_AUTHORITY","video":"DrnAYByca0U","interactions":["parchment_r1","tapestry_piece_1"]}))
    quit(0 if failed.is_empty() else 1)
