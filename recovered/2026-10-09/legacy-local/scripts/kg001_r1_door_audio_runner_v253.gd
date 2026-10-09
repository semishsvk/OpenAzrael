extends SceneTree
var failures:Array[String]=[]
var checks:=0
func ck(n:String,v:bool): checks+=1; failures.append(n) if not v else null
func findn(n:Node,w:String)->Node:
    if String(n.name)==w:return n
    for c in n.get_children():
        var f=findn(c,w)
        if f:return f
    return null
func _initialize(): call_deferred("run")
func run():
    var packed=load("res://main.tscn"); var scene=packed.instantiate(); root.add_child(scene); current_scene=scene
    for i in range(5): await process_frame
    var mgr=scene.get_node("RoomManager"); var st=root.get_node("DemoState"); var ev=root.get_node("LegacyEvents")
    ev.set_capture_only(true); ev.clear_capture()
    var d1=findn(mgr.current_room,"Interact_doorcor01"); ck("door1_exists",d1!=null); d1.interact(); await process_frame
    ck("door1_audio",ev.captured_audio()==["995.WAV"])
    ev.clear_capture()
    var d2=findn(mgr.current_room,"Interact_doorcor2"); ck("door2_exists",d2!=null); d2.interact(); await process_frame
    ck("locked_door2_no_open_audio",ev.captured_audio().is_empty())
    st.acquire("well_key"); d2.interact(); await process_frame
    ck("door2_audio_after_unlock",ev.captured_audio()==["995.WAV"])
    print("OPENAZRAEL_R1_DOOR_AUDIO_V253 "+JSON.stringify({"status":"PASS" if failures.is_empty() else "FAIL","checks":checks,"failed":failures,"asset":"995.WAV"}))
    quit(0 if failures.is_empty() else 1)
