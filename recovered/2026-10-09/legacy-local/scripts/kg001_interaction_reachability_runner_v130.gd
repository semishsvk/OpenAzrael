extends SceneTree
const EvidenceBus=preload("res://scripts/validation/pppv_evidence_bus.gd")
const Navigator=preload("res://scripts/validation/pppv_navigator.gd")
const ROOM_VIEWS={"R1":"spaview","R7":"view","R8":"Object14"}
const TARGETS={
    "R1":["Interact_TONG6","Interact_r1p1","Interact_r3t1","Interact_doorcor01","Interact_doorcor2"],
    "R7":["Interact_WellKey","Interact_well_lev02","Interact_well_weel3"],
    "R8":["Interact_r8t3","Interact_r8t4","Interact_R8Lens","Interact_R8Bible","Interact_R8Tapestry2","Interact_tapframe1","Interact_tapframe3","Interact_tapframe4"],
}
var failures:Array[String]=[]
var checks:=0
var rows:Array=[]
func _check(n:String,ok:bool)->void:
    checks+=1
    if not ok:failures.append(n)
func _settle(n:int=4)->void:
    for _i in range(n):await physics_frame
func _find(n:Node,w:String)->Node:
    if String(n.name)==w:return n
    for c in n.get_children():
        var f:=_find(c,w)
        if f!=null:return f
    return null
func _run()->void:
    var packed=load("res://main.tscn");_check("main",packed is PackedScene)
    if not packed is PackedScene:_finish();return
    var state=root.get_node_or_null("DemoState");_check("state",state!=null)
    var scene=packed.instantiate();root.add_child(scene);await _settle(3)
    var manager=scene.get_node_or_null("RoomManager");var player=scene.get_node_or_null("Player")
    _check("manager",manager!=null);_check("player",player is CharacterBody3D)
    if manager==null or state==null or not player is CharacterBody3D:_finish(scene);return
    var probe=player.get_node_or_null("Camera3D/InteractionProbe");_check("probe",probe!=null)
    if probe==null:_finish(scene);return
    var evidence=EvidenceBus.new()
    var nav=Navigator.new(player,probe,evidence,null)
    for room_id in ["R1","R7","R8"]:
        for target_name in TARGETS[room_id]:
            state.reset_all();manager.load_room(room_id,false);manager.call("_spawn_at_portal",room_id,ROOM_VIEWS[room_id]);await _settle(8)
            var target=_find(manager.current_room,String(target_name))
            _check(room_id+"/"+String(target_name)+"_exists",target is Area3D)
            if not target is Area3D:continue
            _check(room_id+"/"+String(target_name)+"_active",(target as Area3D).collision_layer==2)
            var result:Dictionary=await nav.approach_interactable("reach_"+room_id+"_"+String(target_name),String(target_name),manager.current_room,900,150)
            var reached=bool(result.get("reached",false))
            _check(room_id+"/"+String(target_name)+"_approach",reached)
            var aimed=false
            if reached:
                var aim:Dictionary=await nav.aim_at_interactable("aim_"+room_id+"_"+String(target_name),String(target_name),manager.current_room,180)
                aimed=bool(aim.get("acquired",false))
            _check(room_id+"/"+String(target_name)+"_probe",aimed)
            rows.append({"room":room_id,"target":target_name,"reached":reached,"aimed":aimed,"frames":result.get("used_frames",0)})
    state.reset_all();manager.load_room("R8",false);await _settle(2)
    var shield=_find(manager.current_room,"Interact_ShieldR8")
    _check("R8_hidden_shield_area_exists",shield is Area3D)
    if shield is Area3D:_check("R8_hidden_shield_area_disabled",(shield as Area3D).collision_layer==0)
    _finish(scene)
func _finish(scene:Node=null)->void:
    Input.action_release(&"move_forward")
    var out={"schema":"openazrael.kg001.interaction_reachability","version":130,"status":"PASS" if failures.is_empty() else "FAIL","checks":checks,"failed":failures,"targets":rows,"movement":"production Input via PPPVNavigator"}
    print("OPENAZRAEL_KG001_INTERACTION_REACHABILITY_V130 "+JSON.stringify(out))
    if scene!=null:scene.queue_free()
    quit(0 if failures.is_empty() else 1)
func _initialize()->void:call_deferred("_run")
