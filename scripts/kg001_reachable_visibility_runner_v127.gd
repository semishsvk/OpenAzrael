extends SceneTree
var failures:Array[String]=[]
var checks:=0
var audited:=0
func _check(name:String,ok:bool)->void:
    checks+=1
    if not ok: failures.append(name)
func _settle(n:int=1)->void:
    for _i in range(n): await process_frame
func _find(n:Node,wanted:String)->Node:
    if String(n.name)==wanted:return n
    for c in n.get_children():
        var f:=_find(c,wanted)
        if f!=null:return f
    return null
func _visible(room:Node,name:String)->bool:
    var n:=_find(room,name)
    return n!=null and n is Node3D and (n as Node3D).is_visible_in_tree()

func _run()->void:
    var path:="res://data/runtime_generated/kg001_state_matrix_v127.json"
    if not FileAccess.file_exists(path):
        print("OPENAZRAEL_KG001_REACHABLE_VISIBILITY_V127 "+JSON.stringify({"status":"BLOCKED_MISSING_STATE_MATRIX"})); quit(2); return
    var matrix=JSON.parse_string(FileAccess.get_file_as_string(path))
    _check("matrix_valid",matrix is Dictionary and int(matrix.get("reachable_states",0))==104)
    var state=root.get_node_or_null("DemoState"); _check("state",state!=null)
    var packed=load("res://main.tscn"); _check("main",packed is PackedScene)
    if state==null or not packed is PackedScene: _finish(); return
    var scene=packed.instantiate(); root.add_child(scene); await _settle(2)
    var manager=scene.get_node_or_null("RoomManager"); _check("manager",manager!=null)
    if manager==null:_finish(scene);return
    for record in matrix["records"]:
        var payload:Array=record["persistent_payload"]
        var restored=state.restore_canonical_state_payload(payload)
        _check("state_"+str(record["index"])+"_restore",restored)
        _check("state_"+str(record["index"])+"_hash",state.canonical_state_hash()==String(record["persistent_sha256"]))
        manager.load_room(String(record["room"]),false); await _settle()
        for object_name in record["expected_visibility"].keys():
            var expected=bool(record["expected_visibility"][object_name])
            _check("state_"+str(record["index"])+"_"+String(object_name),_visible(manager.current_room,String(object_name))==expected)
        audited+=1
    _finish(scene)
func _finish(scene:Node=null)->void:
    var out={"schema":"openazrael.kg001.reachable_visibility","version":127,"status":"PASS" if failures.is_empty() else "FAIL","checks":checks,"states_audited":audited,"failed":failures,"state_replay":"production canonical restore; reachable states only"}
    print("OPENAZRAEL_KG001_REACHABLE_VISIBILITY_V127 "+JSON.stringify(out))
    if scene!=null:scene.queue_free()
    quit(0 if failures.is_empty() else 1)
func _initialize()->void:call_deferred("_run")
