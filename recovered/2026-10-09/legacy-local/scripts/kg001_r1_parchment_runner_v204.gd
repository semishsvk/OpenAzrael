extends SceneTree
var failures:Array[String]=[]
func check(n:String,v:bool)->void:
 if not v: failures.append(n)
func _initialize()->void: call_deferred("run")
func run()->void:
 var f=FileAccess.open("res://data/tests/kg001_r1_parchment_semantics_contract_v204.json",FileAccess.READ)
 check("contract_exists",f!=null)
 var d=JSON.parse_string(f.get_as_text()) if f else {}
 check("record_identity",d.get("source",{}).get("record_name","")=="R1P1" and int(d.get("source",{}).get("record_offset",-1))==121265)
 check("runtime_identity",d.get("source",{}).get("runtime_name","")=="r1p1")
 check("description",d.get("evidence",{}).get("description","")=="Parchment")
 check("no_invented_body",d.get("evidence",{}).get("dedicated_read_body","")=="NOT_EVIDENCED")
 var loc=root.get_node("LocalizationManager")
 loc.set_locale("en",false); check("en_name",loc.tr_key("item.parchment_r1.name")=="Parchment")
 loc.set_locale("sk",false); check("sk_name",loc.tr_key("item.parchment_r1.name")=="Pergamen")
 print("OPENAZRAEL_R1_PARCHMENT_V204 "+JSON.stringify({"status":"PASS" if failures.is_empty() else "FAIL","checks":7,"failed":failures}))
 quit(0 if failures.is_empty() else 1)
