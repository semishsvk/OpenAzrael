extends SceneTree
func _initialize():call_deferred("_run")
func _run():
 var p=load("res://assets/rooms/R1.glb");var r=p.instantiate();root.add_child(r);await process_frame
 for n in r.find_children("*","MeshInstance3D",true,false):
  if "save" in String(n.name).to_lower():print("SAVE251 ",n.name," aabb=",n.get_aabb()," gt=",n.global_transform)
 quit()
