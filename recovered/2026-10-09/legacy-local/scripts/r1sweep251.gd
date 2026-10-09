extends SceneTree
func _initialize():call_deferred("_run")
func _run():
 var p=load("res://main.tscn");var s=p.instantiate();root.add_child(s)
 for _i in range(5):await process_frame
 var menu=s.get_node("LegacyMenuV145");menu.call("_dismiss_title");var pl=s.get_node("Player");pl.global_position=Vector3(-4.77,-84.0,-28.29)
 for yaw in [0.0,90.0,180.0,270.0]:
  pl.rotation.y=deg_to_rad(yaw)
  for _i in range(4):await process_frame
  root.get_viewport().get_texture().get_image().save_png("user://r1sweep_"+str(int(yaw))+".png")
 print("SWEEP251 PASS");quit()
