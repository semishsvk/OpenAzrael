extends SceneTree
var failed:Array[String]=[]
var checks:=0
func ck(n:String,v:bool): checks+=1;if not v:failed.append(n)
func _initialize():call_deferred("_run")
func _run():
 var loc=root.get_node("LocalizationManager");var gfx=root.get_node("GraphicsMode");var p=load("res://main.tscn");var scene=p.instantiate();root.add_child(scene)
 for _i in range(5):await process_frame
 var rm=scene.get_node("RoomManager")
 for locale in ["en","sk"]:
  ck("locale_"+locale,bool(loc.call("set_locale",locale,false)))
  ck("translation_"+locale,String(loc.call("tr_key","ui.graphics.original"))!="ui.graphics.original")
  for mode in [0,1]:
   gfx.call("set_mode",mode);rm.load_room("R1",false);await process_frame
   var n:=0
   for x in rm.current_room.find_children("*","MeshInstance3D",true,false):
    var mi=x as MeshInstance3D
    if mi==null or mi.mesh==null:continue
    for s in range(mi.mesh.get_surface_count()):
     var m=mi.get_surface_override_material(s) as StandardMaterial3D
     if m!=null and m.albedo_texture!=null and "assets/upscaled4x/" in m.albedo_texture.resource_path:n+=1
   ck(locale+"_"+str(mode),n==0 if mode==0 else n>0)
 print("OPENAZRAEL_PRESENTATION_MATRIX_V248 "+JSON.stringify({"checks":checks,"failed":failed,"status":"PASS" if failed.is_empty() else "FAIL"}));quit(0 if failed.is_empty() else 1)
