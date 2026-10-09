extends SceneTree
func _initialize():call_deferred("_run")
func _run():
 var s=load("res://main.tscn").instantiate();root.add_child(s);for _i in range(5):await process_frame
 s.get_node("LegacyMenuV145").call("_dismiss_title");var p=s.get_node("Player");p.global_position=Vector3(45,-84,-28)
 for yaw in [120.0,135.0,150.0]:
  p.rotation.y=deg_to_rad(yaw);for _i in range(3):await process_frame
  root.get_viewport().get_texture().get_image().save_png("user://yaw251_"+str(int(yaw))+".png")
 quit()
