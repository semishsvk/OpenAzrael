extends SceneTree
var checks := 0
var failed: Array[String] = []
func check(name:String,value:bool):
    checks+=1
    if not value:failed.append(name)
func _initialize():call_deferred("run")
func run():
    var scene=load("res://main.tscn").instantiate()
    root.add_child(scene)
    for i in range(8):await process_frame
    var indicator=scene.get_node("LegacyMenuV145").find_child("CanonicalOrientationV212",true,false)
    check("production_indicator",indicator!=null)
    if indicator!=null:
        var pixels:PackedByteArray=indicator.indexed_frame(0)
        var ctx:=HashingContext.new()
        ctx.start(HashingContext.HASH_SHA256)
        ctx.update(pixels)
        check("source_indexed_pixels",ctx.finish().hex_encode()==indicator.source["startup_indexed_sha256"])
        check("source_origin",indicator.position==Vector2(44,49))
        check("source_size",indicator.size==Vector2(52,168))
        check("enabled_default",indicator.enabled)
        check("positive_angle",indicator.indexed_frame(30)[120*52+4]==56)
        check("negative_angle",indicator.indexed_frame(-30)[150*52+4]==56)
        var key:=InputEventKey.new()
        key.keycode=KEY_Y
        key.pressed=true
        indicator._unhandled_key_input(key)
        check("Y_disables",not indicator.enabled)
        key.echo=true
        indicator._unhandled_key_input(key)
        check("repeat_ignored",not indicator.enabled)
        key.echo=false
        indicator._unhandled_key_input(key)
        check("Y_enables",indicator.enabled)
    print(JSON.stringify({"status":"PASS" if failed.is_empty() else "FAIL","checks":checks,"failed":failed}))
    scene.queue_free()
    quit(0 if failed.is_empty() else 1)
