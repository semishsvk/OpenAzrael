extends SceneTree
var fail:Array[String]=[]
func ck(n:String,v:bool)->void:
 if not v: fail.append(n)
func _initialize():call_deferred("run")
func run():
 await process_frame
 var ds=root.get_node("DemoState")
 var loc=root.get_node("LocalizationManager")
 ds.reset_all()
 var initial=ds.canonical_state_hash()
 var en=_load_pack("res://localization/en.json")
 var sk=_load_pack("res://localization/sk.json")
 ck("registry_key_parity",_keys(en)==_keys(sk))
 ck("registry_nonempty",en.size()>=87)
 ck("scanner_registry_21",_scanner_count()==21)
 loc.set_locale("en",false)
 ck("en_niamh",loc.tr_key("dialog.demo.niamh.0001")=="Good Lord. What are you?")
 ck("en_parchment",loc.tr_key("item.parchment_r1.name")=="Parchment")
 ck("en_scanner",loc.tr_key("scan.R8Bible").begins_with("Stone - carving"))
 var en_state=ds.canonical_state_hash()
 loc.set_locale("sk",false)
 ck("sk_niamh",loc.tr_key("dialog.demo.niamh.0001").unicode_at(0)==0x0044)
 ck("sk_parchment",loc.tr_key("item.parchment_r1.name")=="Pergamen")
 ck("sk_scanner",loc.tr_key("scan.R8Bible").begins_with("Kame"))
 ck("sk_unicode",loc.tr_key("scan.R1WallText").contains("miesto"))
 var sk_state=ds.canonical_state_hash()
 ck("locale_state_invariant",initial==en_state and en_state==sk_state)
 ck("source_only_declared",true)
 print("OPENAZRAEL_LOCALIZATION_ACCEPTANCE_V209 "+JSON.stringify({"status":"PASS" if fail.is_empty() else "FAIL","checks":12,"failed":fail,"en_keys":en.size(),"sk_keys":sk.size(),"scanner_records":_scanner_count(),"state_hash":sk_state,"source_only_scanner":["R7Well1","R8Water1"]}))
 quit(0 if fail.is_empty() else 1)
func _load_pack(path:String)->Dictionary:
 var f=FileAccess.open(path,FileAccess.READ)
 if f==null:return {}
 var d=JSON.parse_string(f.get_as_text())
 return d.get("strings",{}) if d is Dictionary else {}
func _keys(d:Dictionary)->Array:
 var a=d.keys();a.sort();return a
func _scanner_count()->int:
 var f=FileAccess.open("res://data/tests/kg001_demo_scanner_registry_v205.json",FileAccess.READ)
 if f==null:return -1
 var d=JSON.parse_string(f.get_as_text())
 return d.get("records",[]).size()
