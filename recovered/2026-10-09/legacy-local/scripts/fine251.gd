extends SceneTree
func _initialize():call_deferred("_run")
func _run():
 var p=load("res://main.tscn");var s=p.instantiate();root.add_child(s)
 for _i in range(5):await process_frame
 s.get_node("LegacyMenuV145").call("_dismiss_title");var pl=s.get_node("Player")
 var cases=[[-55.0,-28.0,180.0],[45.0,-28.0,180.0],[-5.0,-78.0,180.0],[-5.0,22.0,180.0],[-5.0,-28.0,165.0],[-5.0,-28.0,195.0]]
 for i in range(cases.size()):
  var c=cases[i];pl.global_position=Vector3(c[0],-84.0,c[1]);pl.rotation.y=deg_to_rad(c[2]);for _j in range(3):await process_frame
  root.get_viewport().get_texture().get_image().save_png("user://fine251_"+str(i)+".png")
 print("FINE251 PASS");quit()
