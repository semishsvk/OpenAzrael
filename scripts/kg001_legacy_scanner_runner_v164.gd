extends SceneTree

var failures: Array[String] = []
var checks := 0

func _check(name: String, ok: bool) -> void:
    checks += 1
    if not ok:
        failures.append(name)

func _run() -> void:
    var packed = load("res://main.tscn")
    _check("main_scene_load", packed is PackedScene)
    if not packed is PackedScene:
        quit(1)
        return
    var scene = packed.instantiate()
    root.add_child(scene)
    for _i in range(12):
        await physics_frame
    var menu = scene.get_node_or_null("LegacyMenuV145")
    var manager = scene.get_node_or_null("RoomManager")
    var player = scene.get_node_or_null("Player") as CharacterBody3D
    _check("menu_present", menu != null)
    _check("manager_present", manager != null)
    _check("player_present", player != null)
    if menu == null or manager == null or player == null:
        scene.queue_free()
        quit(1)
        return

    var initial_position: Vector3 = player.global_position
    var initial_yaw: float = player.rotation.y
    var initial_velocity: Vector3 = player.velocity
    var scanner = menu.get("scanner_runtime")
    _check("scanner_present", scanner != null)
    if scanner == null:
        scene.queue_free()
        quit(1)
        return

    var initial: Dictionary = scanner.call("debug_snapshot")
    _check("source_ready", bool(initial.get("source_ready", false)))
    _check("font_ready", bool(initial.get("font_ready", false)))
    _check("initial_room_R1", String(initial.get("room", "")) == "R1")
    _check("initial_envscan", String(initial.get("text", "")).begins_with("ENVSCAN - corridor"))
    var boot_text := String(scanner.call("_boot_text"))
    _check("boot_source_heading", boot_text.begins_with("Model 7 Head Up Display"))
    _check("boot_source_indentation", "        777777777" in boot_text and "                        77" in boot_text)
    _check("hud_boot_audio_ready", scanner.call("_audio_stream", "hud_boot") != null)
    _check("scan_audio_ready", scanner.call("_audio_stream", "scan") != null)

    scanner.call("show_environment_scan", "R7")
    var r7: Dictionary = scanner.call("debug_snapshot")
    _check("R7_envscan", "stagnant water" in String(r7.get("text", "")))

    scanner.call("show_environment_scan", "R8")
    var r8: Dictionary = scanner.call("debug_snapshot")
    _check("R8_envscan", "baptistery" in String(r8.get("text", "")))

    _check("no_player_position_mutation", player.global_position.distance_to(initial_position) < 0.5)
    _check("no_player_yaw_mutation", absf(wrapf(player.rotation.y - initial_yaw, -PI, PI)) < 0.001)
    _check("no_player_velocity_mutation", player.velocity.distance_to(initial_velocity) < 0.5)

    var result := {
        "schema": "openazrael.kg001.legacy_scanner_runtime",
        "version": 164,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": checks,
        "failed": failures,
        "initial": initial,
        "r7": r7,
        "r8": r8,
    }
    print("OPENAZRAEL_KG001_LEGACY_SCANNER_V164 " + JSON.stringify(result))
    scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _initialize() -> void:
    call_deferred("_run")
