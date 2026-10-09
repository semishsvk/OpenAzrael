extends SceneTree
var fail:Array[String]=[]
func ck(n:String,v:bool)->void:
 if not v: fail.append(n)
func _initialize()->void: call_deferred("run")
func scan_fake(menu:Node,name:String,source_id:String="")->String:
 var a=Area3D.new(); a.name=name
 if not source_id.is_empty(): a.set_meta("source_object_id",source_id)
 var result=menu._scan_text_for_target(a)
 a.free()
 return result
func run()->void:
 await process_frame
 var loc=root.get_node("LocalizationManager")
 var menu=load("res://scripts/legacy_menu_runtime_v145.gd").new()
 loc.set_locale("en",false)
 ck("en_bible",scan_fake(menu,"Interact_R8Bible")=="Stone - carving of 13th century bible - lenses detected beneath - SUGGEST - use as an optical system")
 ck("en_key_alias",scan_fake(menu,"Interact_WellKey")=="Brass - key - slight corrosion detected - primitive design - SUGGEST - celtic origins")
 loc.set_locale("sk",false)
 ck("sk_bible",scan_fake(menu,"Interact_R8Bible").begins_with("Kame"))
 ck("sk_key_alias",scan_fake(menu,"Interact_WellKey").begins_with("Mosadz"))
 ck("meta_binding",scan_fake(menu,"Whatever","R1WallText").contains("Toto miesto"))
 ck("fallback",scan_fake(menu,"Interact_UNKNOWN").contains("Interact_UNKNOWN"))
 ck("null_surface",not menu._scan_text_for_target(null).is_empty())
 menu.free()
 print("OPENAZRAEL_SCANNER_BINDING_V206 "+JSON.stringify({"status":"PASS" if fail.is_empty() else "FAIL","checks":7,"failed":fail}))
 quit(0 if fail.is_empty() else 1)
