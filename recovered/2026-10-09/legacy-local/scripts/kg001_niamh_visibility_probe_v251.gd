extends SceneTree
func settle(n:int):
 for _i in range(n): await process_frame
func v3(a:Array)->Vector3:return Vector3(float(a[0]),float(a[1]),float(a[2]))
func _initialize():call_deferred("_run")
func _run():
 var events=root.get_node("LegacyEvents");var state=root.get_node("DemoState");events.set_capture_only(true);state.reset_all()
 var p=load("res://main.tscn");var scene=p.instantiate();root.add_child(scene);await settle(4)
 var rm=scene.get_node("RoomManager");var player=scene.get_node("Player");rm.transition_cooldown=999.0;rm.load_room("R7",false);await settle(3)
 var ghost:Dictionary=rm.call("_trigger_record","R7","zxactghost");var mn=v3(ghost["bounds"][0]);var c=v3(ghost["centroid"])
 player.global_position=Vector3(mn.x-40.0,c.y,mn.z-40.0);await settle(2);player.global_position=c;await settle(4)
 var n=rm.current_room.get_node_or_null("SourceCharacter_Niamh")
 if n==null:print("NIAMH_VIS251 "+JSON.stringify({"exists":false}));quit(1);return
 var meshes=n.find_children("*","MeshInstance3D",true,false);var visible=0;var bounds=[]
 for x in meshes:
  var mi=x as MeshInstance3D
  if mi!=null and mi.mesh!=null:
   if mi.is_visible_in_tree():visible+=1
   bounds.append({"name":mi.name,"visible":mi.is_visible_in_tree(),"aabb":str(mi.get_aabb()),"global":str(mi.global_transform)})
 print("NIAMH_VIS251 "+JSON.stringify({"exists":true,"root_visible":n.visible,"pos":str(n.global_position),"scale":str(n.global_scale),"mesh_count":meshes.size(),"visible_meshes":visible,"proxy_pos":str(rm.call("_find_node","nibody").global_position),"meshes":bounds}))
 quit()
