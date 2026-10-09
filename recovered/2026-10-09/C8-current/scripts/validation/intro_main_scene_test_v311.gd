extends Node
## Source-bound startup sequence + direct Godot framebuffer comparison.
## This is NOT a DOS/VGA wall-clock capture and does not certify palette fades.
const Intro := preload("res://scripts/intro_player_v311.gd")
var checks: Array[Dictionary] = []
var captures: Array[Dictionary] = []
var main: Node
var intro: CanvasLayer
var runtime: Dictionary
var started: Array[String] = []

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    get_window().size = Vector2i(640, 480)
    call_deferred("run")

func verify(label: String, ok: bool, detail: Variant = null) -> void:
    checks.append({"check": label, "pass": ok, "detail": detail})
    if not ok:
        print("INTRO_MAIN_FAIL ", label, " ", detail)

func digest(bytes: PackedByteArray) -> String:
    var ctx := HashingContext.new()
    ctx.start(HashingContext.HASH_SHA256); ctx.update(bytes)
    return ctx.finish().hex_encode()

func on_clip(id: String) -> void:
    started.append(id)

func capture(name: String, expected_clip: String, expected_frame: int = 0) -> void:
    await get_tree().process_frame
    await RenderingServer.frame_post_draw
    var image := get_viewport().get_texture().get_image()
    image.convert(Image.FORMAT_RGB8)
    var path := "res://.tmp/intro_decode_v311/" + name + ".png"
    var saved := image.save_png(path)
    var clip: Dictionary = runtime["clips"][expected_clip]
    var source := (load(String(clip["sequence"][expected_frame]["path"])) as Texture2D).get_image()
    source.convert(Image.FORMAT_RGB8)
    var expected := Image.create(640, 480, false, Image.FORMAT_RGB8)
    expected.fill(Color.BLACK)
    var position: Array = clip["source_position"]
    expected.blit_rect(source, Rect2i(Vector2i.ZERO, source.get_size()), Vector2i(int(position[0]), int(position[1])))
    var actual_hash := digest(image.get_data())
    var expected_hash := digest(expected.get_data())
    var row := {"name": name, "width": image.get_width(), "height": image.get_height(),
        "rgb_sha256": actual_hash, "expected_rgb_sha256": expected_hash, "pixel_exact": actual_hash == expected_hash,
        "path": path, "save_error": saved, "origin": "Godot ViewportTexture", "source_clip": expected_clip,
        "source_frame": expected_frame, "source_position": position}
    verify("viewport_exact_" + name, image.get_size() == Vector2i(640,480) and actual_hash == expected_hash and saved == OK, row)
    captures.append(row)

func run() -> void:
    runtime = JSON.parse_string(FileAccess.get_file_as_string(Intro.MANIFEST))
    main = load("res://main.tscn").instantiate()
    intro = main.get_node("StartupIntroV311")
    intro.manual_clock = true
    intro.clip_started.connect(on_clip)
    add_child(main)
    await get_tree().process_frame
    await get_tree().process_frame
    var menu: Node = main.get_node("LegacyMenuV145")
    var player: Node3D = main.get_node("Player")
    verify("main_scene_auto_starts_intro", intro._active, intro.debug_snapshot())
    verify("game_title_waits_behind_original_sequence", menu.title_open and get_tree().paused)
    var before := player.global_position
    var state_before := DemoState.canonical_state_hash()
    await capture("main_mindscape_frame0", "MINDLOGO", 0)
    await get_tree().create_timer(1.7, true).timeout
    verify("fallback_timeout_not_spent_during_movie", menu.title_open and intro._active)
    var w := InputEventKey.new(); w.keycode = KEY_W; w.physical_keycode = KEY_W; w.pressed = true
    Input.parse_input_event(w)
    await get_tree().process_frame
    w = InputEventKey.new(); w.keycode = KEY_W; w.physical_keycode = KEY_W; w.pressed = false
    Input.parse_input_event(w)
    await get_tree().process_frame
    verify("gameplay_input_does_not_move_paused_player", player.global_position == before)
    var mind_period := float(runtime["clips"]["MINDLOGO"]["frame_period_us"]) / 1000000.0
    intro.advance(39.0 * mind_period)
    await capture("main_mindscape_frame39", "MINDLOGO", 39)
    intro.advance(mind_period)
    await capture("main_ig_frame0", "INTRO", 0)
    verify("source_15fps_mindscape_transition", is_equal_approx(40.0 * mind_period, 2.66664))
    verify("intro_audio_without_room_music_overlap", intro._audio.playing and get_tree().paused and (not CandidateMusic._player.playing or CandidateMusic._player.stream_paused))
    # Native original R.EXE DOSBox-X screenshots at INTRO frames 8/28/47
    # have exact source-time correspondences; capture these Godot frames
    # for direct original-vs-Godot renderer parity. Preserve v312 frame25/49.
    intro.advance(0.8)
    await capture("main_ig_frame8", "INTRO", 8)
    intro.advance(1.7)
    await capture("main_ig_frame25", "INTRO", 25)
    intro.advance(0.3)
    await capture("main_ig_frame28", "INTRO", 28)
    intro.advance(1.9)
    await capture("main_ig_frame47", "INTRO", 47)
    intro.advance(0.2)
    await capture("main_ig_frame49", "INTRO", 49)
    get_window().size = Vector2i(1280, 720)
    await get_tree().process_frame
    await RenderingServer.frame_post_draw
    var wide := get_viewport().get_texture().get_image()
    wide.convert(Image.FORMAT_RGB8)
    var left := wide.get_region(Rect2i(0, 0, 160, 720)).get_data()
    var right := wide.get_region(Rect2i(1120, 0, 160, 720)).get_data()
    verify("widescreen_preserves_640x480_canvas", wide.get_size() == Vector2i(1280, 720) and left.count(0) == left.size() and right.count(0) == right.size() and wide.get_pixel(160, 0) == Color.WHITE)
    wide.save_png("res://.tmp/intro_decode_v311/main_ig_widescreen.png")
    get_window().size = Vector2i(640, 480)
    await get_tree().process_frame
    intro.advance(0.1)
    verify("audio_tail_preserved_before_title", intro._active and intro._frame_index == 49)
    intro.advance(float(runtime["clips"]["INTRO"]["duration"]) - 5.0)
    verify("title_occurs_before_poem_not_after", intro._active and intro.debug_snapshot()["clip"] == "TITLE" and get_tree().paused, intro.debug_snapshot())
    await capture("source_title_before_poem", "TITLE")
    verify("native_title_origin_zero", intro._image.position == Vector2.ZERO and intro._image.size == Vector2(631,474))
    intro.advance(2.59)
    verify("title_nominal_hold_not_truncated", intro.debug_snapshot()["clip"] == "TITLE")
    intro.advance(0.01)
    verify("original_poem_bound_to_startup", intro.debug_snapshot()["clip"] == "MOV_INTRO" and intro._frame_index == 0)
    verify("poem_native_600x300_center_not_stretched", intro._image.position == Vector2(20,90) and intro._image.size == Vector2(600,300))
    await capture("source_poem_frame0", "MOV_INTRO", 0)
    intro.advance(5.4)
    await capture("source_poem_frame54", "MOV_INTRO", 54)
    verify("original_startup_order_executed_once", started == ["MINDLOGO", "INTRO", "TITLE", "MOV_INTRO"], started.duplicate())
    verify("demo_outro_not_inserted_into_startup", not started.has("MOV_DEMO"))
    verify("intro_does_not_mutate_demo_save_state", state_before == DemoState.canonical_state_hash())
    intro.advance(0.1)
    verify("completion_no_duplicate_title_flash", not intro._active and not get_tree().paused and not menu.title_open and not menu.title_texture.visible)
    verify("completion_scanner_boot_starts", bool(menu.debug_scanner_snapshot().get("active", false)) and String(menu.debug_scanner_snapshot().get("mode", "")) == "boot", menu.debug_scanner_snapshot())
    verify("intro_metadata_fully_released", not get_tree().has_meta(Intro.OWNER_META) and not get_tree().has_meta(Intro.ACTIVE_META))
    # Verify Escape during the new static title releases the complete sequence.
    menu._show_title()
    intro.begin()
    intro.skip_current()
    intro.skip_current()
    verify("skip_test_reaches_title", intro.debug_snapshot()["clip"] == "TITLE")
    var escape := InputEventKey.new(); escape.keycode = KEY_ESCAPE; escape.pressed = true
    Input.parse_input_event(escape)
    await get_tree().process_frame
    verify("escape_title_no_pause_leak_or_service_popup", not intro._active and not get_tree().paused and not menu.title_open and not menu.service_open)
    var failed := 0
    for row: Dictionary in checks:
        if not row["pass"]:
            failed += 1
    var report := {"schema": "openazrael.intro_main_scene_tests.v312", "status": "PASS" if failed == 0 else "FAIL",
        "checks": checks, "failed": failed, "captures": captures, "display": DisplayServer.get_name(),
        "scope": "Original startup control flow, source positioning and Godot pixel/state integration",
        "audio_sync": "NOT_VERIFIED_BY_MANUAL_CLOCK_CAPTURE", "dos_wallclock_fades": "HOLD"}
    var file := FileAccess.open("res://.tmp/intro_decode_v311/godot_intro_main_tests.json", FileAccess.WRITE)
    file.store_string(JSON.stringify(report, "  ")); file.close()
    print("INTRO_MAIN_V312 ", JSON.stringify({"status": report["status"], "checks": checks.size(), "failed": failed, "captures": captures.size()}))
    CandidateMusic.stop()
    main.queue_free()
    await get_tree().process_frame
    await get_tree().create_timer(0.1, true).timeout
    get_tree().quit(0 if failed == 0 else 1)
