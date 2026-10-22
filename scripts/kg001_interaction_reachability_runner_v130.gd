extends SceneTree
const EvidenceBus=preload("res://scripts/validation/pppv_evidence_bus.gd")
const Navigator=preload("res://scripts/validation/pppv_navigator.gd")
const PlayerDriver=preload("res://scripts/validation/pppv_player_driver.gd")
const ROOM_VIEWS={"R1":"spaview","R7":"view","R8":"Object14"}
const TARGETS={
    "R1":["Interact_TONG6","Interact_r1p1","Interact_r3t1","Interact_doorcor01","Interact_doorcor2"],
    "R7":["Interact_WellKey","Interact_well_lev02","Interact_well_weel3"],
    "R8":["Interact_r8t3","Interact_r8t4","Interact_R8Lens","Interact_R8Bible","Interact_R8Tapestry2","Interact_tapframe1","Interact_tapframe3","Interact_tapframe4"],
}
# Audited R1 corridor route shared with v119/v141. The final point is beyond
# Door2, so v130 stops at the penultimate point before probing fresh-state
# interactions in the corridor.
const R1_ROUTE=[
    Vector3(-203.801173,-84.921990,300.265764),Vector3(-168.693718,-91.949649,281.939643),
    Vector3(-113.787899,-107.514682,201.650247),Vector3(-72.816896,-114.240783,116.816224),
    Vector3(-75.0,-114.3,70.0),Vector3(-75.0,-114.3,20.0),Vector3(-50.0,-114.3,-20.0),
    Vector3(0.0,-115.0,-50.0),Vector3(38.260757,-115.691564,-50.391974),
    Vector3(95.934301,-117.355663,-127.453640),Vector3(141.988445,-115.622030,-209.540090),
    Vector3(119.25,-114.455,-261.236),Vector3(156.921,-114.276,-313.508),
    Vector3(203.566,-114.275,-324.678),Vector3(210.088,-114.364,-410.699),
    Vector3(266.328,-114.24,-415.593),Vector3(299.061,-110.726,-486.612),
    Vector3(356.752,-108.708,-475.156),Vector3(405.288,-99.161,-522.654),
    Vector3(449.221720,-93.255052,-498.865461),Vector3(476.42,-85.03,-514.95),
    Vector3(529.295811,-84.2055,-513.041569),
]
# Source-derived physical ingress through R8's authored right-hand broken mirror.
# These are navigation goals only; the player reaches them through production
# movement input and normal collision/step-up semantics.
const R8_INGRESS_ROUTE=[
    [-278.067350,-87.124025,394.941924],
    [-254.067350,-79.249800,394.941936],
    [-243.696350,-74.195030,394.941940],
    [-233.238082,-69.118450,394.941948],
    [-222.866992,-64.063640,394.941952],
    [-208.866992,-63.785391,394.941959],
    [-101.798000,-63.785391,160.000000],
    [-101.798000,-63.572091,136.000000],
    [-67.000000,-63.572091,93.000000],
    [-55.000000,-63.572091,92.000000],
    [8.000000,-63.572091,93.000000],
]
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
func _walk_r1_corridor(nav)->bool:
    for i in range(R1_ROUTE.size()-1):
        var result:Dictionary=await nav.approach_world_point("reach_R1_route_%02d"%i,R1_ROUTE[i],Callable(),900,150,18.0)
        if not bool(result.get("reached",false)):return false
    return true
func _production_interact(nav,driver,manager,target_name:String,prefix:String)->bool:
    var result:Dictionary=await nav.approach_interactable(prefix+"_approach",target_name,manager.current_room,1100,180)
    if not bool(result.get("reached",false)):return false
    var aim:Dictionary=await nav.aim_at_interactable(prefix+"_aim",target_name,manager.current_room,220)
    if not bool(aim.get("acquired",false)):return false
    return await driver.interact_via_probe(prefix+"_interact",target_name)
func _route_r8_ingress(nav)->bool:
    for i in range(R8_INGRESS_ROUTE.size()):
        var raw:Array=R8_INGRESS_ROUTE[i]
        var point:=Vector3(float(raw[0]),float(raw[1]),float(raw[2]))
        var reach:=3.0 if i>=1 and i<=4 else (1.0 if i==6 or i==7 else 12.0)
        var result:Dictionary=await nav.approach_world_point(
            "reach_R8_ingress_%02d"%i,
            point,
            Callable(),
            900,
            150,
            reach
        )
        if not bool(result.get("reached",false)):
            return false
    return true
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
    var driver=PlayerDriver.new(player,probe,evidence,null)
    for room_id in ["R1","R7","R8"]:
        for target_name in TARGETS[room_id]:
            state.reset_all()
            var loaded:=bool(manager.call("load_room_at_portal",room_id,ROOM_VIEWS[room_id],false))
            _check(room_id+"/"+String(target_name)+"_production_spawn",loaded)
            if not loaded:
                rows.append({"room":room_id,"target":target_name,"reached":false,"aimed":false,"frames":0,"reason":"production_spawn_failed"})
                continue
            await _settle(8)
            if room_id=="R1" and target_name!="Interact_doorcor01":
                var door1_ok:=await _production_interact(nav,driver,manager,"Interact_doorcor01","reach_R1_door1")
                _check(room_id+"/"+String(target_name)+"_door1_production_interaction",door1_ok)
                if not door1_ok:
                    rows.append({"room":room_id,"target":target_name,"reached":false,"aimed":false,"frames":0,"reason":"r1_door1_interaction_failed"})
                    continue
                await _settle(8)
                var corridor_ok:=await _walk_r1_corridor(nav)
                _check(room_id+"/"+String(target_name)+"_audited_corridor",corridor_ok)
                if not corridor_ok:
                    rows.append({"room":room_id,"target":target_name,"reached":false,"aimed":false,"frames":0,"reason":"r1_audited_corridor_failed"})
                    continue
            if room_id=="R8":
                var ingress_ok:=await _route_r8_ingress(nav)
                _check(room_id+"/"+String(target_name)+"_source_ingress",ingress_ok)
                if not ingress_ok:
                    rows.append({"room":room_id,"target":target_name,"reached":false,"aimed":false,"frames":0,"reason":"r8_source_ingress_failed"})
                    continue
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
    state.reset_all()
    _check("R8_hidden_shield_production_spawn",bool(manager.call("load_room_at_portal","R8",ROOM_VIEWS["R8"],false)))
    await _settle(2)
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
