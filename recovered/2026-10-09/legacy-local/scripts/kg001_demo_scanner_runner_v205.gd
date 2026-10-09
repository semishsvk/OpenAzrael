extends SceneTree
var failures:Array[String]=[]
func ck(n:String,v:bool)->void:
 if not v: failures.append(n)
func _initialize()->void: call_deferred("run")
func run()->void:
 var f=FileAccess.open("res://data/tests/kg001_demo_scanner_registry_v205.json",FileAccess.READ)
 ck("registry_exists",f!=null)
 var d=JSON.parse_string(f.get_as_text()) if f else {}
 var rows:Array=d.get("records",[])
 ck("record_count",rows.size()==21)
 var loc=root.get_node("LocalizationManager")
 loc.set_locale("en",false)
 for r in rows: ck("en_"+String(r["source_id"]),loc.tr_key(String(r["localization_key"]))==String(r["source_text"]))
 loc.set_locale("sk",false)
 for r in rows: ck("sk_"+String(r["source_id"]),not loc.tr_key(String(r["localization_key"])).begins_with("["))
 ck("wall_translation",loc.tr_key("scan.R1WallText").contains("Toto miesto"))
 ck("tapestry_translation",loc.tr_key("scan.R8TapestryBack").contains("Bafometa"))
 print("OPENAZRAEL_DEMO_SCANNER_V205 "+JSON.stringify({"status":"PASS" if failures.is_empty() else "FAIL","checks":47,"records":rows.size(),"failed":failures}))
 quit(0 if failures.is_empty() else 1)
