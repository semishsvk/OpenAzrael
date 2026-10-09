extends SceneTree

var failed: Array[String] = []
var checks := 0

func check(label: String, condition: bool) -> void:
    checks += 1
    if not condition:
        failed.append(label)

func key(player: Node, code: Key) -> void:
    var event := InputEventKey.new()
    event.keycode = code
    event.pressed = true
    player._unhandled_input(event)

func _initialize() -> void:
    call_deferred("_run")

func _run() -> void:
    var scene = load("res://main.tscn").instantiate()
    root.add_child(scene)
    for i in range(12):
        await process_frame
    var player = scene.get_node("Player")
    var camera: Camera3D = player.get_node("Camera3D")
    var menu = scene.get_node("LegacyMenuV145")
    check("initial_modern", player.control_profile == "modern")
    check("initial_sniper_off", not player.sniper_active)
    # The title is a modal and must be dismissed before gameplay input.
    menu._dismiss_title()
    for i in range(3):
        await process_frame
    var original := camera.size
    var yaw: float = player.rotation.y
    var pitch: float = player.pitch
    key(player, KEY_F6)
    check("classic_profile", player.control_profile == "classic_compat")
    key(player, KEY_F6)
    check("modern_restored", player.control_profile == "modern")
    key(player, KEY_F)
    check("sniper_active", player.sniper_active)
    check("sniper_zoom_smaller_frustum", camera.size < original)
    check("yaw_preserved", is_equal_approx(player.rotation.y, yaw))
    check("pitch_preserved", is_equal_approx(player.pitch, pitch))
    key(player, KEY_F)
    check("sniper_off", not player.sniper_active)
    check("frustum_restored", is_equal_approx(camera.size, original))
    key(player, KEY_TAB)
    check("hud_cursor", player.hud_cursor_active)
    key(player, KEY_TAB)
    check("hud_cursor_released", not player.hud_cursor_active)
    print("OPENAZRAEL_KG001_CONTROLS_V304 " + JSON.stringify({"status":"PASS" if failed.is_empty() else "FAIL","checks":checks,"failed":failed,"original_frustum":original,"restored_frustum":camera.size}))
    scene.queue_free()
    quit(0 if failed.is_empty() else 1)
