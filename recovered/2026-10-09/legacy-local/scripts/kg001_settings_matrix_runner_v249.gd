extends SceneTree
var failed:Array[String]=[]
var checks:=0
func check(n:String,v:bool): checks+=1;if not v:failed.append(n)
func _initialize():call_deferred("_run")
func _run():
 var loc=root.get_node("LocalizationManager");var gfx=root.get_node("GraphicsMode")
 for locale in ["en","sk"]:
  loc.call("set_locale",locale)
  for mode in [0,1]:
   gfx.call("set_mode",mode)
   check(locale+"_"+str(mode)+"_locale",String(loc.get("current_locale"))==locale)
   check(locale+"_"+str(mode)+"_gfx",int(gfx.get("mode"))==mode)
   check(locale+"_"+str(mode)+"_name",String(gfx.call("mode_name"))==("CLASSIC" if mode==0 else "ENHANCED"))
 gfx.call("set_mode",0);loc.call("set_locale","en")
 var out={"schema":"openazrael.settings_matrix","version":249,"checks":checks,"failed":failed,"status":"PASS" if failed.is_empty() else "FAIL","matrix":["EN+ORIGINAL","SK+ORIGINAL","EN+UPSCALED","SK+UPSCALED"]}
 print("OPENAZRAEL_SETTINGS_MATRIX_V249 "+JSON.stringify(out));quit(0 if failed.is_empty() else 1)
