extends SceneTree
func _initialize():call_deferred("_run")
func _run():
 var p=load("res://main.tscn");var s=p.instantiate();root.add_child(s);for _i in range(5):await process_frame
 var pl=s.get_node("Player");var menu=s.get_node("LegacyMenuV145");print("A ",pl.global_position," paused=",paused);menu.call("_dismiss_title");print("B paused=",paused)
 pl.teleport_eye_to(Vector3(0,-70,-350),Vector3(0,0,1));print("C ",pl.global_position," cam=",pl.get_node("Camera3D").global_position);await process_frame;print("D ",pl.global_position," cam=",pl.get_node("Camera3D").global_position);quit()
