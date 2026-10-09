extends SceneTree
const C=preload("res://scripts/validation/bug_report_framework_context.gd")
func _initialize():
 var x=C.new().collect();var inc=0
 for a in x.artifacts:
  if bool(a.get("included",false)):inc+=1
 var ok=inc==4 and bool(x.get("source_safe",false)) and not bool(x.get("commercial_assets_included",true))
 print("OPENAZRAEL_BUG_CONTEXT_V249 "+JSON.stringify({"included":inc,"status":"PASS" if ok else "FAIL","artifacts":x.artifacts}))
 quit(0 if ok else 1)
