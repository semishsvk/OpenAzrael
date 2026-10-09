extends SceneTree
func _initialize(): call_deferred("_run")
func _run():
 var p=load("res://main.tscn");var s=p.instantiate();root.add_child(s)
 for _i in range(8):await process_frame
 var menu=s.get_node("LegacyMenuV145");menu.call("_dismiss_title")
 for _i in range(8):await process_frame
 var img=root.get_viewport().get_texture().get_image()
 var path="user://r1_visual_smoke.png";var err=img.save_png(path)
 var st={"size":[img.get_width(),img.get_height()],"err":err,"path":ProjectSettings.globalize_path(path)}
 var sum:=0.0
 for y in range(0,img.get_height(),16):
  for x in range(0,img.get_width(),16):
   var c=img.get_pixel(x,y);sum+=c.r+c.g+c.b
 st["sample_rgb_sum"]=sum
 print("OPENAZRAEL_R1_VISUAL_SMOKE_V251 "+JSON.stringify(st));quit(0)
