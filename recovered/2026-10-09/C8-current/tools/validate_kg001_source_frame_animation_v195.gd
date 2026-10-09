extends SceneTree

const Driver = preload("res://scripts/source_frame_animation_driver_v195.gd")

var observed: Array[String] = []
var transitions: Array[String] = []

func _initialize() -> void:
    var player := AnimationPlayer.new()
    root.add_child(player)
    var lib := AnimationLibrary.new()
    player.add_animation_library(&"", lib)
    for spec in [
        ["ATTACK", 53, 70],
        ["NOLOOP1", 0, 14],
        ["REST", 15, 41],
    ]:
        var anim := Animation.new()
        anim.length = float(int(spec[2]) - int(spec[1]) + 1)
        lib.add_animation(StringName(spec[0]), anim)

    var driver = Driver.new()
    root.add_child(driver)
    driver.source_frame_observed.connect(func(family: String, frame: int):
        observed.append("%s:%d" % [family, frame])
    )
    driver.source_family_transitioned.connect(func(a: String, b: String):
        transitions.append("%s>%s" % [a, b])
    )

    var families := {
        "ATTACK": [53, 70],
        "NOLOOP1": [0, 14],
        "REST": [15, 41],
    }
    if not driver.configure(player, families, 1.0 / 15.0):
        _fail("configure")
        return
    if not driver.request_family("ATTACK"):
        _fail("attack_request")
        return
    for _i in range(9):
        if not driver.source_update():
            _fail("attack_update")
            return
    var expected_attack: Array[String] = [
        "ATTACK:53","ATTACK:54","ATTACK:55","ATTACK:56","ATTACK:57",
        "ATTACK:58","ATTACK:59","ATTACK:60","ATTACK:61"
    ]
    if observed != expected_attack or observed.count("ATTACK:60") != 1:
        _fail("attack_frame_sequence")
        return

    observed.clear()
    transitions.clear()
    if not driver.request_family("NOLOOP1", "REST"):
        _fail("niamh_request")
        return
    for _i in range(15):
        if not driver.source_update():
            _fail("niamh_noloop_update")
            return
    if observed.front() != "NOLOOP1:0" or observed.back() != "NOLOOP1:14":
        _fail("niamh_noloop_bounds")
        return
    if transitions != ["NOLOOP1>REST"] or driver.source_family() != "REST" or driver.source_frame() != 15:
        _fail("niamh_transition")
        return
    if not driver.source_update() or observed.back() != "REST:15":
        _fail("niamh_rest_first_frame")
        return
    if driver.request_family("MISSING"):
        _fail("missing_family_not_fail_closed")
        return

    print(JSON.stringify({
        "schema":"openazrael.kg001.source_frame_animation_headless_validation",
        "version":195,
        "status":"PASS",
        "attack_sequence":expected_attack,
        "attack_frame60_count":1,
        "niamh_transition":"NOLOOP1>REST",
        "rest_first_frame":15,
        "source_clock":"EXPLICIT_SOURCE_UPDATE_ONLY"
    }))
    quit(0)

func _fail(reason: String) -> void:
    print(JSON.stringify({"schema":"openazrael.kg001.source_frame_animation_headless_validation","version":195,"status":"FAIL","reason":reason}))
    quit(1)
