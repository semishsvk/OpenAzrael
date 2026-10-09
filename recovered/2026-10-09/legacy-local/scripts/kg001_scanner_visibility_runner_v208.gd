extends SceneTree
var fail:Array[String]=[]
func ck(n:String,v:bool)->void:
 if not v:fail.append(n)
func find(n:Node,name:String):
 if n is Area3D and n.name==name:return n
 for c in n.get_children():
  var r=find(c,name)
  if r:return r
 return null
func active(a)->bool:return a!=null and a.monitoring and a.monitorable and a.collision_layer!=0
func vis(rm:Node,n:String):
 var x=rm._find_node(n);return null if x==null else x.is_visible_in_tree()
func _initialize():call_deferred("run")
func run():
 await process_frame
 var ds=root.get_node("DemoState");ds.reset_all()
 var scene=load("res://main.tscn").instantiate();root.add_child(scene);await process_frame;await process_frame
 var rm=scene.get_node("RoomManager")
 rm.load_room("R8",false);await process_frame
 ck("fresh_lenslook_hidden",not active(find(rm,"Scan_R8LensLook")))
 ck("fresh_hole_matches",active(find(rm,"Scan_R8MirrorHole"))==vis(rm,"broken3"))
 ck("water1_source_node_absent",vis(rm,"ZZcutter02")==null)
 ck("water1_area_absent",find(rm,"Scan_R8Water1")==null)
 ds.set_puzzle_node("R8LensPlace",true);ds.set_puzzle_node("R8LensLook",true);ds.set_flag("R8BathDrain",true)
 rm.load_room("R8",false);await process_frame
 ck("post_lenslook_matches",active(find(rm,"Scan_R8LensLook"))==vis(rm,"lenstop01"))
 ck("post_water1_still_absent",find(rm,"Scan_R8Water1")==null)
 rm.load_room("R7",false);await process_frame
 for pair in [["R7Well","wel_well"],["R7Well2","zxdeath"]]:
  ck("r7_"+pair[0]+"_matches",active(find(rm,"Scan_"+pair[0]))==vis(rm,pair[1]))
 ck("r7_well1_source_node_absent",vis(rm,"Object")==null)
 ck("r7_well1_area_absent",find(rm,"Scan_R7Well1")==null)
 print("OPENAZRAEL_SCANNER_VISIBILITY_V208 "+JSON.stringify({"status":"PASS" if fail.is_empty() else "FAIL","checks":10,"failed":fail,"source_only":["R7Well1","R8Water1"]}))
 var events=root.get_node_or_null("LegacyEvents")
 if events != null and events.has_method("clear_physical_audio"): events.clear_physical_audio()
 rm.set_process(false)
 scene.queue_free()
 await process_frame; await process_frame; await process_frame; await process_frame
 quit(0 if fail.is_empty() else 1)
