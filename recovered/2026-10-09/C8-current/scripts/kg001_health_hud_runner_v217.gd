extends SceneTree
var checks: Dictionary = {}
func _initialize(): call_deferred("_run")
func _run():
    var scene = load("res://main.tscn").instantiate()
    root.add_child(scene)
    await process_frame
    var menu = scene.get_node("LegacyMenuV145")
    var player = scene.get_node("Player")
    var bar = menu.classic_canvas.get_node("SourceHealthHudV217")
    bar.set_process(false)
    checks["source_bitmap_dimensions"] = bar.source_image.get_size()==Vector2i(105,15)
    var hash = HashingContext.new()
    hash.start(HashingContext.HASH_SHA256)
    hash.update(bar.image_for_health(1000).get_data())
    checks["all_1575_original_bar_rgb_pixels"] = hash.finish().hex_encode()==bar.contract["original_full_bar_rgb_sha256"]
    player.legacy_health=500
    player.legacy_health_poll_counter=0
    for i in range(4): player.advance_legacy_health_poll()
    checks["source_four_poll_increment"] = player.legacy_health==501
    for i in range(2000): player.advance_legacy_health_poll()
    checks["source_maximum_1000"] = player.legacy_health==1000
    player.apply_legacy_damage(200,"v217_test")
    checks["eugene_damage_reaches_bar"] = player.legacy_health_value()==800 and bar.image_for_health(800).get_data()!=bar.image_for_health(1000).get_data()
    player.legacy_health=0
    for i in range(12):player.advance_legacy_health_poll()
    checks["no_dead_player_regeneration"] = player.legacy_health==0
    checks["no_fixed_source_hz_claim"] = bar.contract["fixed_source_hz_claimed"]==false
    checks["source_origin"] = bar.position==Vector2(320,357)
    menu.title_open=true
    var before=player.legacy_health_poll_counter
    bar._process(1.0)
    checks["blocking_menu_pauses_regeneration"] = player.legacy_health_poll_counter==before
    var failed=[]
    for key in checks:
        if not checks[key]: failed.append(key)
    print("V217_HEALTH_HUD "+JSON.stringify({"status":"PASS" if failed.is_empty() else "FAIL","checks":checks,"failed":failed}))
    scene.queue_free()
    quit(0 if failed.is_empty() else 2)
