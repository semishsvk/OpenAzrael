extends SceneTree
var checks: Dictionary = {}
func _initialize(): call_deferred("run")
func key(code: int, down: bool = true):
    var e=InputEventKey.new()
    e.keycode=code
    e.physical_keycode=code
    e.pressed=down
    Input.parse_input_event(e)
    Input.flush_buffered_events()
    await process_frame
    await process_frame
func tap(code: int):
    await key(code)
    await key(code,false)
func motion():
    var e=InputEventMouseMotion.new()
    e.relative=Vector2(40,-8)
    Input.parse_input_event(e)
    Input.flush_buffered_events()
    await process_frame
func run():
    var scene=load("res://main.tscn").instantiate()
    root.add_child(scene)
    current_scene=scene
    for i in range(8): await process_frame
    var menu=scene.get_node("LegacyMenuV145")
    var player=scene.get_node("Player")
    checks["title_releases_pointer"]=menu.title_open and Input.mouse_mode==Input.MOUSE_MODE_VISIBLE
    await tap(KEY_ENTER)
    checks["gameplay_captures_pointer"]=not menu.title_open and Input.mouse_mode==Input.MOUSE_MODE_CAPTURED
    var yaw=player.rotation.y
    await motion()
    checks["mouse_look_without_RMB"]=not is_equal_approx(yaw,player.rotation.y)
    await tap(KEY_TAB)
    yaw=player.rotation.y
    await motion()
    checks["Tab_cursor_blocks_look"]=player.hud_cursor_active and Input.mouse_mode==Input.MOUSE_MODE_VISIBLE and is_equal_approx(yaw,player.rotation.y)
    var position=player.global_position
    await key(KEY_W)
    for i in range(12): await physics_frame
    checks["Tab_cursor_blocks_walk"]=position.distance_to(player.global_position)<0.001
    await key(KEY_W,false)
    await tap(KEY_TAB)
    checks["Tab_resumes_capture"]=not player.hud_cursor_active and Input.mouse_mode==Input.MOUSE_MODE_CAPTURED
    await tap(KEY_H)
    position=player.global_position
    yaw=player.rotation.y
    await motion()
    await key(KEY_W)
    for i in range(12): await physics_frame
    checks["help_blocks_controls"]=menu.help_open and Input.mouse_mode==Input.MOUSE_MODE_VISIBLE and position.distance_to(player.global_position)<0.001 and is_equal_approx(yaw,player.rotation.y)
    await key(KEY_W,false)
    await tap(KEY_H)
    checks["help_restores_capture"]=not menu.help_open and Input.mouse_mode==Input.MOUSE_MODE_CAPTURED
    await tap(KEY_ESCAPE)
    checks["Escape_service_menu"]=menu.service_open and paused and Input.mouse_mode==Input.MOUSE_MODE_VISIBLE
    await tap(KEY_ESCAPE)
    checks["Escape_resumes_gameplay"]=not menu.service_open and not paused and Input.mouse_mode==Input.MOUSE_MODE_CAPTURED
    await tap(KEY_F2)
    var language=get_first_node_in_group("language_menu")
    checks["F2_language_releases_pointer"]=language.is_open() and player._controls_blocked() and Input.mouse_mode==Input.MOUSE_MODE_VISIBLE
    await tap(KEY_ESCAPE)
    checks["language_close_restores_capture"]=not language.is_open() and not menu.service_open and Input.mouse_mode==Input.MOUSE_MODE_CAPTURED
    player._notification(Node.NOTIFICATION_APPLICATION_FOCUS_OUT)
    checks["focus_loss_releases_pointer"]=player.hud_cursor_active and Input.mouse_mode==Input.MOUSE_MODE_VISIBLE
    await tap(KEY_TAB)
    checks["focus_resume_requires_Tab"]=not player.hud_cursor_active and Input.mouse_mode==Input.MOUSE_MODE_CAPTURED
    var failed=[]
    for name in checks:
        if not checks[name]:failed.append(name)
    print(JSON.stringify({"schema":"openazrael.modern_controls_v220","status":"PASS" if failed.is_empty() else "FAIL","checks":checks,"failed":failed,"display":DisplayServer.get_name()}))
    paused=false
    scene.queue_free()
    quit(0 if failed.is_empty() else 1)
