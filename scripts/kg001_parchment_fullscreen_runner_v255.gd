extends SceneTree
const Preview=preload("res://scripts/pickup_preview_v226.gd")
var failed:Array[String]=[]
func ck(v:bool,n:String)->void:
    if not v: failed.append(n)
func _initialize()->void: call_deferred("_run")
func _run()->void:
    var p=Preview.new(); root.add_child(p); await process_frame
    ck(p.show_item("parchment_r1"),"show")
    ck(bool(p.active) and p.visible,"active_visible")
    ck(p.image.texture is Texture2D,"texture")
    if p.image.texture is Texture2D:
        ck(p.image.texture.get_width()==640 and p.image.texture.get_height()==480,"source_640x480")
        ck(String(p.image.texture.resource_path)=="res://assets/ui/object_inspect/PARCHMENT_R1.png","source_asset")
    ck(p.image.stretch_mode==TextureRect.STRETCH_KEEP_ASPECT_CENTERED,"aspect_centered")
    p.dismiss(); ck(not p.active and not p.visible,"dismiss")
    print("OPENAZRAEL_PARCHMENT_FULLSCREEN_V255 "+JSON.stringify({"status":"PASS" if failed.is_empty() else "FAIL","failed":failed}))
    quit(0 if failed.is_empty() else 1)
