extends SceneTree
var fail:Array[String]=[]
func ck(n:String,v:bool)->void:
 if not v: fail.append(n)
func find_area(node:Node,n:String)->Area3D:
 if node is Area3D and node.name==n: return node
 for c in node.get_children():
  var r=find_area(c,n)
  if r!=null:return r
 return null
func _initialize()->void:call_deferred("run")
func run()->void:
 await process_frame
 var scene=load("res://main.tscn").instantiate(); root.add_child(scene)
 await process_frame; await process_frame
 var rm=scene.get_node("RoomManager")
 var cases={
  "R1":{"Interact_r1p1":"R1P1","Interact_r3t1":"R1DemoTapPiece1"},
  "R7":{"Interact_WellKey":"R7Key","Scan_R7Well":"R7Well"},
  "R8":{"Interact_R8Lens":"R8Lens","Interact_R8Bible":"R8Bible","Interact_R8Tapestry2":"R8TapestryBack","Scan_R8BrokeMir":"R8BrokeMir","Scan_R8Font":"R8Font","Scan_R8Plaque":"R8Plaque","Scan_R8Plate":"R8Plate","Scan_R8Stair":"R8Stair","Scan_R8Water":"R8Water","Scan_R8WellPipe":"R8WellPipe","Scan_R8WindowMirror":"R8WindowMirror"}
 }
 var count=0
 for room in cases:
  rm.load_room(room,false); await process_frame
  for area_name in cases[room]:
   count+=1
   var a=find_area(rm,area_name)
   ck(room+"_"+area_name+"_exists",a!=null)
   if a!=null: ck(room+"_"+area_name+"_source",String(a.get_meta("source_object_id",""))==String(cases[room][area_name]))
 print("OPENAZRAEL_SCANNER_PROVENANCE_V207 "+JSON.stringify({"status":"PASS" if fail.is_empty() else "FAIL","areas":count,"checks":count*2,"failed":fail}))
 var events=root.get_node_or_null("LegacyEvents")
 if events != null and events.has_method("clear_physical_audio"): events.clear_physical_audio()
 scene.queue_free(); await process_frame; await process_frame; await process_frame; await process_frame
 quit(0 if fail.is_empty() else 1)
