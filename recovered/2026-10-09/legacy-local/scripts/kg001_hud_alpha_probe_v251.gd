extends SceneTree
func _initialize():
 var t=load("res://assets/ui/legacy_menu/HUD3.png") as Texture2D;var im=t.get_image();var z=0
 for y in range(im.get_height()):
  for x in range(im.get_width()):
   if im.get_pixel(x,y).a<0.5:z+=1
 print("HUDALPHA251 ",z," center=",im.get_pixel(320,240));quit()
