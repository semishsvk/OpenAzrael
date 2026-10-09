extends SceneTree
func _initialize():call_deferred("_run")
func _run():
 var p=load("res://main.tscn");var s=p.instantiate();root.add_child(s)
 for _i in range(5):await process_frame
 var cams=s.find_children("*","Camera3D",true,false)
 for c in cams:print("CAM251 ",c.get_path()," current=",c.current," pos=",c.global_position)
 print("VP_CURRENT ",root.get_viewport().get_camera_3d().get_path() if root.get_viewport().get_camera_3d() else "NONE");quit()
