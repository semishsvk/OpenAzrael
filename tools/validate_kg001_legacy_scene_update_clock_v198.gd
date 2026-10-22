extends SceneTree
const Clock = preload("res://scripts/legacy_scene_update_clock_v198.gd")
const Driver = preload("res://scripts/source_frame_animation_driver_v195.gd")

var observed: Array[String] = []
var passes: Array[int] = []

func _initialize() -> void:
    var player := AnimationPlayer.new()
    root.add_child(player)
    var lib := AnimationLibrary.new()
    player.add_animation_library(&"", lib)
    var attack := Animation.new()
    attack.length = 2.0
    lib.add_animation(&"ATTACK", attack)
    var driver := Driver.new()
    root.add_child(driver)
    driver.source_frame_observed.connect(func(family:String, frame:int): observed.append("%s:%d" % [family,frame]))
    if not driver.configure(player,{"ATTACK":[53,61]},1.0/15.0): return _fail("configure")
    if not driver.request_family("ATTACK"): return _fail("request")
    var clock := Clock.new()
    root.add_child(clock)
    clock.legacy_scene_update_pass.connect(func(i:int): passes.append(i))
    if not clock.register_source_frame_driver(driver): return _fail("register")
    for _i in range(9):
        if clock.dispatch_eligible_legacy_scene_update_pass() != 1: return _fail("dispatch")
    var expected:Array[String]=["ATTACK:53","ATTACK:54","ATTACK:55","ATTACK:56","ATTACK:57","ATTACK:58","ATTACK:59","ATTACK:60","ATTACK:61"]
    if observed != expected: return _fail("frames")
    if passes != [1,2,3,4,5,6,7,8,9]: return _fail("passes")
    if clock.dispatch_eligible_legacy_scene_update_pass() != 0: return _fail("finished_driver_advanced")
    if clock.pass_index()!=10: return _fail("pass_index")
    print(JSON.stringify({"schema":"openazrael.kg001.legacy_scene_update_clock_headless_validation","version":198,"status":"PASS","frames":observed,"pass_index":clock.pass_index(),"clock":"EXTERNAL_DISPATCH_ONLY"}))
    quit(0)

func _fail(reason:String) -> void:
    print(JSON.stringify({"schema":"openazrael.kg001.legacy_scene_update_clock_headless_validation","version":198,"status":"FAIL","reason":reason}))
    quit(1)
