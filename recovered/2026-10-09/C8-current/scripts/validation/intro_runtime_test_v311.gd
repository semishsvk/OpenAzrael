extends Node

const Intro := preload("res://scripts/intro_player_v311.gd")
const OUTPUT := "res://.tmp/intro_decode_v311/godot_intro_tests.json"
var checks: Array[Dictionary] = []
var hashes_checked := 0
var last_reason := ""

class TickProbe extends Node:
    var ticks := 0
    func _process(_delta: float) -> void:
        ticks += 1

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    call_deferred("run")

func verify(label: String, ok: bool, detail: Variant = null) -> void:
    checks.append({"check": label, "pass": ok, "detail": detail})
    if not ok:
        print("INTRO_TEST_FAIL: ", label, " ", detail)

func digest(bytes: PackedByteArray) -> String:
    var context := HashingContext.new()
    context.start(HashingContext.HASH_SHA256)
    context.update(bytes)
    return context.finish().hex_encode()

func new_player() -> CanvasLayer:
    var intro := Intro.new()
    intro.auto_start = false
    intro.manual_clock = true
    add_child(intro)
    return intro

func run() -> void:
    var runtime: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(Intro.MANIFEST))
    var probe := TickProbe.new()
    probe.process_mode = Node.PROCESS_MODE_PAUSABLE
    add_child(probe)
    var intro := new_player()
    verify("default_headless_does_not_claim_pause", not get_tree().paused and not intro._owns_pause)
    var image_hashes_ok := true
    var exact_frame_counts_ok := true
    var all_completed := true
    for id: String in ["MINDLOGO", "INTRO", "MOV_INTRO", "MOV_DEMO"]:
        var ids: Array[String] = [id]
        verify("begin_" + id, intro.begin(ids), intro.debug_snapshot())
        var clip: Dictionary = runtime["clips"][id]
        var frame_count := int(clip["frame_count"])
        for index in range(frame_count):
            var snap: Dictionary = intro.debug_snapshot()
            if not bool(snap["active"]) or int(snap["frame_index"]) != index:
                exact_frame_counts_ok = false
            var image: Image = intro._image.texture.get_image()
            image.convert(Image.FORMAT_RGB8)
            var expected := String(clip["sequence"][index]["rgb_sha256"])
            var actual := digest(image.get_data())
            if actual != expected:
                image_hashes_ok = false
                print("IMAGE_HASH_FAIL ", id, " ", index)
            hashes_checked += 1
            intro.advance(1.0 / float(clip["fps"]))
        if id == "INTRO":
            verify("preserve_audio_tail_and_last_frame", intro._active and intro._frame_index == 49)
            verify("audio_stream_plays_while_tree_paused", intro._audio.playing and not intro._audio.stream_paused)
            var stream: AudioStreamWAV = intro._audio.stream
            var restored: PackedByteArray = stream.data.duplicate()
            if stream.format == AudioStreamWAV.FORMAT_8_BITS:
                for byte_index in range(restored.size()):
                    restored[byte_index] = restored[byte_index] ^ 128
            verify("imported_audio_is_lossless_source_pcm8", stream.format == AudioStreamWAV.FORMAT_8_BITS and digest(restored) == String(clip["audio"]["pcm_u8_sha256"]), {"format": stream.format, "bytes": restored.size()})
            intro.advance(float(clip["duration"]) - float(frame_count) / float(clip["fps"]))
        all_completed = all_completed and not intro._active and intro._last_reason == "completed" and not get_tree().paused
    verify("all_245_imported_frame_pixels_equal_decoder", image_hashes_ok and hashes_checked == 245, hashes_checked)
    verify("all_frame_indices_and_boundaries", exact_frame_counts_ok)
    verify("all_four_clips_finish_and_restore_pause", all_completed)
    verify("nominal_fps_is_not_opaque_header_12", runtime["clips"]["INTRO"]["fps"] == 10)
    verify("publisher_native_timer_period_66666_us", runtime["clips"]["MINDLOGO"].get("frame_period_us", 0) == 66666)
    verify("complete_original_startup_order", runtime["startup_order"] == ["MINDLOGO", "INTRO", "TITLE", "MOV_INTRO"])
    verify("native_movie_framing", int(runtime["clips"]["MOV_INTRO"]["source_position"][0]) == 20 and int(runtime["clips"]["MOV_INTRO"]["source_position"][1]) == 90)
    var title_only: Array[String] = ["TITLE"]
    verify("native_title_stage_loads", intro.begin(title_only))
    verify("title_not_centered_or_stretched", intro._image.size == Vector2(631, 474) * minf(get_viewport().get_visible_rect().size.x / 640.0, get_viewport().get_visible_rect().size.y / 480.0))
    intro.advance(2.59)
    verify("title_nominal_hold_before_boundary", intro._active)
    intro.advance(0.01)
    verify("title_nominal_hold_finishes", not intro._active and not get_tree().paused)

    verify("begin_default_order", intro.begin(), intro.debug_snapshot())
    verify("publisher_first", intro.debug_snapshot()["clip"] == "MINDLOGO")
    verify("game_tree_is_paused", get_tree().paused and bool(get_tree().get_meta(Intro.ACTIVE_META, false)))
    var before := probe.ticks
    await get_tree().process_frame
    await get_tree().process_frame
    verify("world_does_not_tick_during_intro", probe.ticks == before)
    intro.advance(float(runtime["clips"]["MINDLOGO"]["duration"]))
    verify("boundary_switches_to_intro_frame_zero", intro.debug_snapshot()["clip"] == "INTRO" and intro._frame_index == 0)
    intro.advance(50.0)
    verify("large_delta_completes_without_loop_or_softlock", not intro._active and not get_tree().paused)

    var one: Array[String] = ["MINDLOGO"]
    intro.begin(one)
    intro.manual_clock = false
    intro._process(1.0)
    verify("asset_loading_delta_cannot_skip_initial_frames", intro._frame_index == 0, intro.debug_snapshot())
    intro.manual_clock = true
    var other := new_player()
    verify("second_owner_is_rejected", not other.begin(one) and other._last_reason == "ownership_error")
    verify("second_owner_cannot_unpause_first", get_tree().paused and intro._owns_pause)
    other.queue_free()
    intro.skip_all()
    verify("escape_api_restores_pause_and_cursor", not get_tree().paused and not intro._owns_pause and not get_tree().has_meta(Intro.OWNER_META))
    await get_tree().process_frame
    await get_tree().process_frame
    verify("world_resumes_after_intro", probe.ticks > before)

    intro.begin()
    var next_key := InputEventKey.new()
    next_key.keycode = KEY_SPACE
    next_key.pressed = true
    Input.parse_input_event(next_key)
    await get_tree().process_frame
    await get_tree().process_frame
    verify("space_skips_only_current_clip", intro.debug_snapshot()["clip"] == "INTRO" and intro._active, intro.debug_snapshot())
    var escape := InputEventKey.new()
    escape.keycode = KEY_ESCAPE
    escape.pressed = true
    Input.parse_input_event(escape)
    await get_tree().process_frame
    await get_tree().process_frame
    verify("escape_stops_audio_and_whole_sequence", not intro._active and not intro._audio.playing and not get_tree().paused)

    intro.manifest_path = "res://.tmp/not_present_intro_manifest.json"
    verify("missing_manifest_fails_without_pause_leak", not intro.begin() and not get_tree().paused and intro._last_error == "missing_intro_manifest")
    intro.manifest_path = Intro.MANIFEST
    var invalid: Array[String] = ["UNKNOWN"]
    verify("unknown_clip_fails_without_pause_leak", not intro.begin(invalid) and not get_tree().paused)
    var corrupted: Dictionary = runtime.duplicate(true)
    corrupted["clips"]["MINDLOGO"]["sequence"][0]["path"] = "res://assets/intro_v311/MISSING.png"
    var corrupt_path := "res://.tmp/intro_decode_v311/corrupt_manifest.json"
    var file := FileAccess.open(corrupt_path, FileAccess.WRITE)
    file.store_string(JSON.stringify(corrupted)); file.close()
    intro.manifest_path = corrupt_path
    verify("missing_frame_fails_without_pause_leak", not intro.begin(one) and not get_tree().paused)
    intro.manifest_path = Intro.MANIFEST
    var invalid_positions: Array = [[-1, 0], [1, 0], ["not-a-number", 0]]
    for index in range(invalid_positions.size()):
        corrupted = runtime.duplicate(true)
        corrupted["clips"]["MINDLOGO"]["source_position"] = invalid_positions[index]
        file = FileAccess.open(corrupt_path, FileAccess.WRITE)
        file.store_string(JSON.stringify(corrupted)); file.close()
        intro.manifest_path = corrupt_path
        verify("invalid_source_position_" + str(index), not intro.begin(one) and not get_tree().paused and intro._last_error.begins_with("invalid_intro_source_placement"), intro.debug_snapshot())
    intro.manifest_path = Intro.MANIFEST

    get_tree().paused = true
    intro.begin(one)
    intro.skip_all()
    verify("preexisting_pause_is_preserved", get_tree().paused)
    get_tree().paused = false
    intro.begin(one)
    intro.queue_free()
    await get_tree().process_frame
    verify("removal_releases_pause_and_metadata", not get_tree().paused and not get_tree().has_meta(Intro.OWNER_META))

    # Allow the audio mixer to release stopped playback references before exit.
    await get_tree().create_timer(0.1, true).timeout
    var failures := 0
    for row: Dictionary in checks:
        if not row["pass"]:
            failures += 1
    var report := {"schema": "openazrael.intro_runtime_tests.v311", "status": "PASS" if failures == 0 else "FAIL",
        "checks": checks, "check_count": checks.size(), "failed": failures, "frame_hashes_checked": hashes_checked,
        "engine": Engine.get_version_info(), "display": DisplayServer.get_name(),
        "original_runtime_fidelity": "HOLD", "scope": "Godot playback state, texture pixels, input and audio lifecycle"}
    file = FileAccess.open(OUTPUT, FileAccess.WRITE)
    file.store_string(JSON.stringify(report, "  ")); file.close()
    print("INTRO_RUNTIME_V311 ", JSON.stringify({"status": report["status"], "checks": checks.size(), "failed": failures, "frames": hashes_checked}))
    get_tree().quit(0 if failures == 0 else 1)
