extends SceneTree
func _initialize():call_deferred("_run")
func _run():
 var p=load("res://main.tscn");var s=p.instantiate();root.add_child(s)
 for _i in range(5):await process_frame
 var rm=s.get_node("RoomManager");var pl=s.get_node("Player");rm.load_room("R1",false);var menu=s.get_node("LegacyMenuV145");menu.call("_dismiss_title")
 var poss=[Vector3(-5,-90,-30),Vector3(-5,-90,20),Vector3(0,-100,50),Vector3(20,-100,30),Vector3(-30,-100,20),Vector3(0,-90,80),Vector3(30,-90,80),Vector3(-30,-90,80)]
 var targets=[Vector3(-198,-54,307),Vector3(-120,-70,220),Vector3(-80,-80,150),Vector3(0,-90,0)]
 var k=0
 for eye in poss:
  for target in targets:
   pl.teleport_eye_to(eye,(target-eye).normalized())
   for _j in range(2):await process_frame
   var im=root.get_viewport().get_texture().get_image();im.save_png("user://sweep_%02d.png"%k);print("SWEEP ",k," eye=",eye," target=",target);k+=1
 quit()
