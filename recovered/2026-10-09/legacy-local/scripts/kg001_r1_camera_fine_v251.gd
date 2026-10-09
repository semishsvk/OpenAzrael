extends SceneTree
func _initialize():call_deferred("_run")
func _run():
 var p=load("res://main.tscn");var s=p.instantiate();root.add_child(s);for _i in range(5):await process_frame
 var rm=s.get_node("RoomManager");var pl=s.get_node("Player");rm.load_room("R1",false);s.get_node("LegacyMenuV145").call("_dismiss_title")
 var eyes=[Vector3(100,-70,-250),Vector3(130,-70,-250),Vector3(160,-70,-250)]
 var ts=[Vector3(-160,-80,180),Vector3(-200,-80,220)]
 var k=0
 for e in eyes:
  for t in ts:
   pl.teleport_eye_to(e,(t-e).normalized());for _j in range(2):await process_frame
   root.get_viewport().get_texture().get_image().save_png("user://fine_%02d.png"%k);print("FINE ",k," ",e," ",t);k+=1
 quit()
