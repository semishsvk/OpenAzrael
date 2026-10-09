extends SceneTree

const SaveSystem = preload("res://scripts/legacy_save_system_v145.gd")
var failures: Array[String] = []
var checks := 0

func _check(name:String, ok:bool) -> void:
    checks += 1
    if not ok:
        failures.append(name)

func _settle(frames:int=3) -> void:
    for _i in range(frames):
        await process_frame

func _run() -> void:
    var required := {
        "HUD3":[640,480],
        "TITLE":[631,474],
        "SAVE13":[206,170],
        "NBUT0ON":[83,36],
        "NBUT1ON":[77,42],
        "NBUT2ON":[90,43],
        "MAPON":[639,47],
        "MAPOFF":[639,47],
    }
    for stem in required:
        var path: String = "res://assets/ui/legacy_menu/" + String(stem) + ".png"
        _check("asset_exists:"+String(stem), ResourceLoader.exists(path))
        if ResourceLoader.exists(path):
            var tex := load(path) as Texture2D
            _check("texture:"+String(stem), tex != null)
            if tex != null:
                _check("width:"+String(stem), tex.get_width()==int(required[stem][0]))
                _check("height:"+String(stem), tex.get_height()==int(required[stem][1]))

    var state = root.get_node_or_null("DemoState")
    var packed = load("res://main.tscn")
    _check("state", state != null)
    _check("main", packed is PackedScene)
    if state == null or not packed is PackedScene:
        _finish()
        return

    state.reset_all()
    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle(6)

    var manager = scene.get_node_or_null("RoomManager")
    var player = scene.get_node_or_null("Player")
    var menu = scene.get_node_or_null("LegacyMenuV145")
    _check("manager", manager != null)
    _check("player", player is CharacterBody3D)
    _check("menu", menu != null)
    if manager == null or not player is CharacterBody3D or menu == null:
        _finish(scene)
        return

    _check("five_slots", SaveSystem.SLOT_NAMES.size()==5)
    _check("slot_alpha", SaveSystem.SLOT_NAMES[0]=="FILE ALPHA")
    _check("slot_epsilon", SaveSystem.SLOT_NAMES[4]=="FILE EPSILON")

    _check("load_hotspot", String(menu.call("_service_action_at", Vector2(235,260)+Vector2(50,35)))=="LOAD")
    _check("save_hotspot", String(menu.call("_service_action_at", Vector2(235,260)+Vector2(60,100)))=="SAVE")
    _check("music_hotspot", String(menu.call("_service_action_at", Vector2(235,260)+Vector2(120,45)))=="MUSIC")
    _check("sfx_hotspot", String(menu.call("_service_action_at", Vector2(235,260)+Vector2(120,80)))=="SFX")
    _check("quit_hotspot", String(menu.call("_service_action_at", Vector2(235,260)+Vector2(80,60)))=="QUIT")
    _check("confirm_hotspot", String(menu.call("_service_action_at", Vector2(235,260)+Vector2(40,130)))=="CONFIRM")

    manager.load_room("R1", false)
    await _settle(3)
    player.global_position = Vector3(12.5, 33.25, -77.5)
    player.rotation.y = 0.42
    player.set("pitch", -0.18)
    state.acquire("rusty_tongs")
    state.set_flag("R1Door1Open")
    _check("save_slot", SaveSystem.save_slot(0, manager, player))
    _check("save_exists", SaveSystem.slot_exists(0))

    state.reset_all()
    manager.load_room("R8", false)
    player.global_position = Vector3(1,2,3)
    player.rotation.y = 0.0
    player.set("pitch", 0.0)

    _check("load_slot", SaveSystem.load_slot(0, manager, player))
    _check("state_restored", state.has("rusty_tongs") and state.flag("R1Door1Open"))
    _check("room_restored", String(manager.current_room_id)=="R1")
    _check("position_restored", player.global_position.distance_to(Vector3(12.5,33.25,-77.5)) < 0.01)
    _check("yaw_restored", absf(player.rotation.y-0.42)<0.001)
    _check("pitch_restored", absf(float(player.get("pitch"))+0.18)<0.001)

    var save_path := SaveSystem.slot_path(0)
    if FileAccess.file_exists(save_path):
        DirAccess.remove_absolute(ProjectSettings.globalize_path(save_path))

    _finish(scene)

func _finish(scene:Node=null) -> void:
    var out := {
        "schema":"openazrael.kg001.legacy_menu_runtime",
        "version":145,
        "status":"PASS" if failures.is_empty() else "FAIL",
        "checks":checks,
        "failed":failures,
        "save_slots":SaveSystem.SLOT_NAMES,
        "source_ui":"ATDEMO PCX-derived PNG only",
    }
    print("OPENAZRAEL_KG001_MENU_V145 " + JSON.stringify(out))
    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _initialize() -> void:
    call_deferred("_run")
