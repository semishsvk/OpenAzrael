extends SceneTree
var failed:Array[String]=[]
var checks:=0
func check(name:String,value:bool):
    checks+=1
    if not value:failed.append(name)
func _initialize():call_deferred("run")
func run():
    var scene=load("res://main.tscn").instantiate()
    root.add_child(scene)
    for i in range(8):await process_frame
    var menu=scene.get_node("LegacyMenuV145")
    var help=menu.find_child("CanonicalHelpV213",true,false)
    check("production_help",help!=null)
    if help!=null:
        check("source_canvas",help.position==Vector2.ZERO and help.size==Vector2(640,480))
        check("source_texture",help.texture.resource_path=="res://assets/ui/legacy_menu/HELP.png")
        check("default_hidden",not help.visible and not help.enabled)
        var key:=InputEventKey.new()
        key.pressed=true
        key.keycode=KEY_H
        help._unhandled_key_input(key)
        check("H_opens",help.visible and help.enabled)
        check("world_cursor_blocked",menu.blocks_world_cursor())
        key.echo=true
        help._unhandled_key_input(key)
        check("repeat_ignored",help.enabled)
        key.echo=false
        help._unhandled_key_input(key)
        check("H_closes",not help.visible and not help.enabled)
        check("world_cursor_restored",not menu.blocks_world_cursor())
    print(JSON.stringify({"status":"PASS" if failed.is_empty() else "FAIL","checks":checks,"failed":failed}))
    scene.queue_free()
    quit(0 if failed.is_empty() else 1)
