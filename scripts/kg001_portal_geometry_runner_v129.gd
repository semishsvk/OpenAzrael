extends SceneTree
const DOOR_FOR_TRIGGER={"zxcoriR5":"doorcor01","zxcoriR2":"doorcor2"}
const MAX_DOOR_TRIGGER_DISTANCE:=180.0
var failures:Array[String]=[]
var checks:=0
var rows:Array=[]
func _check(n:String,ok:bool)->void:
    checks+=1
    if not ok:failures.append(n)
func _v3(a:Array)->Vector3:return Vector3(float(a[0]),float(a[1]),float(a[2]))
func _settle_physics(n:int=6)->void:
    for _i in range(n):await physics_frame
func _floor(scene:Node3D,player:CharacterBody3D,p:Vector3)->Dictionary:
    var q:=PhysicsRayQueryParameters3D.create(p+Vector3.UP*80.0,p+Vector3.DOWN*180.0,1)
    q.exclude=[player.get_rid()];q.hit_back_faces=true
    return scene.get_world_3d().direct_space_state.intersect_ray(q)
func _run()->void:
    var packed=load("res://main.tscn");_check("main",packed is PackedScene)
    if not packed is PackedScene:_finish();return
    var scene=packed.instantiate();root.add_child(scene);await _settle_physics(3)
    var manager=scene.get_node_or_null("RoomManager");var player=scene.get_node_or_null("Player")
    _check("manager",manager!=null);_check("player",player is CharacterBody3D)
    if manager==null or not player is CharacterBody3D:_finish(scene);return
    var edges:Array=manager.evidence.get("demo_transitions",[])
    _check("exact_transition_count",edges.size()==4)
    for tr in edges:
        var source:=String(tr["source_room"]);var trigger_name:=String(tr["trigger"])
        var dest:=String(tr["destination_room"]);var view_name:=String(tr["destination_view"])
        manager.load_room(source,false);await _settle_physics(2)
        var trigger:Dictionary=manager.call("_trigger_record",source,trigger_name)
        _check(source+"/"+trigger_name+"_trigger",not trigger.is_empty())
        if source=="R1" and DOOR_FOR_TRIGGER.has(trigger_name):
            var door_name:=String(DOOR_FOR_TRIGGER[trigger_name])
            var door=manager.call("_find_node",door_name)
            _check(source+"/"+door_name+"_door",door is Node3D)
            if door is Node3D and not trigger.is_empty():
                var bounds:AABB=manager.call("_node_global_bounds",door)
                var t:=_v3(trigger["centroid"])
                var horizontal:=Vector2(bounds.get_center().x-t.x,bounds.get_center().z-t.z).length()
                _check(source+"/"+trigger_name+"_door_adjacent",horizontal<=MAX_DOOR_TRIGGER_DISTANCE)
        manager.load_room(dest,false);await _settle_physics(2)
        var view:Dictionary=manager.call("_view_record",dest,view_name)
        _check(dest+"/"+view_name+"_view",not view.is_empty())
        if view.is_empty():continue
        manager.call("_spawn_at_portal",dest,view_name)
        await _settle_physics(10)
        var hit:=_floor(scene,player,player.global_position)
        var support_ok:=not hit.is_empty()
        _check(dest+"/"+view_name+"_spawn_support",support_ok)
        var fell:=false
        var support_y: float = float(player.global_position.y)
        if support_ok:support_y=float((hit["position"] as Vector3).y);fell=player.global_position.y<support_y-4.0
        _check(dest+"/"+view_name+"_no_fall",not fell)
        _check(dest+"/"+view_name+"_settled_floor",player.is_on_floor() or (support_ok and absf(player.global_position.y-support_y)<4.5))
        rows.append({"source":source,"trigger":trigger_name,"destination":dest,"view":view_name,"support":support_ok,"player":[player.global_position.x,player.global_position.y,player.global_position.z]})
    _finish(scene)
func _finish(scene:Node=null)->void:
    var out={"schema":"openazrael.kg001.portal_geometry_closure","version":129,"status":"PASS" if failures.is_empty() else "FAIL","checks":checks,"failed":failures,"transitions":rows}
    print("OPENAZRAEL_KG001_PORTAL_GEOMETRY_V129 "+JSON.stringify(out))
    if scene!=null:scene.queue_free()
    quit(0 if failures.is_empty() else 1)
func _initialize()->void:call_deferred("_run")
