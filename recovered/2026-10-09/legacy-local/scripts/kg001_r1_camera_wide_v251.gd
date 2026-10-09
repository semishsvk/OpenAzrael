extends SceneTree
func _initialize():call_deferred("_run")
func _run():
 var p=load("res://main.tscn");var s=p.instantiate();root.add_child(s);for _i in range(5):await process_frame
 var rm=s.get_node("RoomManager");var pl=s.get_node("Player");rm.load_room("R1",false);s.get_node("LegacyMenuV145").call("_dismiss_title")
 var poss=[Vector3(0,-70,-180),Vector3(0,-70,-250),Vector3(0,-70,-350),Vector3(100,-70,-250),Vector3(-100,-70,-250),Vector3(150,-70,-350),Vector3(-150,-70,-350),Vector3(250,-70,-350),Vector3(-250,-70,-350),Vector3(0,-40,-250),Vector3(0,-100,-250),Vector3(100,-100,-300)]
 var targets=[Vector3(-80,-80,120),Vector3(-120,-70,180),Vector3(-50,-80,80)]
 var k=0
 for eye in poss:
  for t in targets:
   pl.teleport_eye_to(eye,(t-eye).normalized());for _j in range(2):await process_frame
   root.get_viewport().get_texture().get_image().save_png("user://wide_%02d.png"%k);print("WIDE ",k," ",eye," ",t);k+=1
 quit()
