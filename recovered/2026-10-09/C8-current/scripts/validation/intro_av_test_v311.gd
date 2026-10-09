extends Node
## Exercise the real process/audio clocks and capture engine bus samples.
const Intro := preload("res://scripts/intro_player_v311.gd")
var checks: Array[Dictionary] = []
var frame_events: Array[Dictionary] = []

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    call_deferred("run")

func check(label: String, ok: bool, detail: Variant = null) -> void:
    checks.append({"check": label, "pass": ok, "detail": detail})
    if not ok:
        print("INTRO_AV_FAIL ", label, " ", detail)

func run() -> void:
    var intro := Intro.new()
    intro.auto_start = false
    add_child(intro)
    intro.frame_displayed.connect(func(id: String, frame: int): frame_events.append({"clip": id, "frame": frame, "ticks": Time.get_ticks_usec()}))
    var effect := AudioEffectCapture.new()
    effect.buffer_length = 8.0
    var slot := AudioServer.get_bus_effect_count(0)
    AudioServer.add_bus_effect(0, effect)
    var ids: Array[String] = ["INTRO"]
    check("start_real_clock", intro.begin(ids))
    var start := Time.get_ticks_usec()
    var max_skew := 0.0
    var audio_monotonic := true
    var last_audio_pos := 0.0
    var samples: Array[Dictionary] = []
    while intro._active and float(Time.get_ticks_usec() - start) / 1000000.0 < 8.0:
        await get_tree().create_timer(0.1, true).timeout
        if intro._active and intro._audio.playing:
            var position := intro._audio.get_playback_position()
            audio_monotonic = audio_monotonic and position >= last_audio_pos
            last_audio_pos = position
            if intro._frame_index < 49:
                max_skew = maxf(max_skew, absf(float(intro._frame_index) / 10.0 - position))
            samples.append({"frame": intro._frame_index, "audio_seconds": position, "tree_paused": get_tree().paused})
    var elapsed := float(Time.get_ticks_usec() - start) / 1000000.0
    var finished := not intro._active and intro._last_reason == "completed"
    check("audio_and_video_finish_without_watchdog", finished, intro.debug_snapshot())
    check("all_50_frames_presented", intro._played_frames == 50, intro._played_frames)
    check("source_audio_tail_not_cut_at_video_end", elapsed >= 5.50 and elapsed < 6.2, elapsed)
    check("audio_playback_clock_is_monotonic", audio_monotonic and samples.size() > 40, samples.size())
    check("internal_av_clock_skew_under_two_frames", max_skew < 0.2, max_skew)
    check("completed_restores_game_pause", not get_tree().paused)
    var available := effect.get_frames_available()
    var captured := effect.get_buffer(available)
    var peak := 0.0
    var energy := 0.0
    for sample: Vector2 in captured:
        peak = maxf(peak, maxf(absf(sample.x), absf(sample.y)))
        energy += sample.x * sample.x + sample.y * sample.y
    var rms := sqrt(energy / maxf(float(available * 2), 1.0))
    check("engine_bus_captured_non_silent_audio", available > AudioServer.get_mix_rate() * 5 and peak > 0.01 and rms > 0.002,
        {"sample_frames": available, "peak": peak, "rms": rms, "mix_rate": AudioServer.get_mix_rate()})
    check("capture_buffer_did_not_overflow", effect.get_discarded_frames() == 0, effect.get_discarded_frames())
    AudioServer.remove_bus_effect(0, slot)
    intro.skip_all()
    intro.queue_free()
    var failures := 0
    for row: Dictionary in checks:
        if not row["pass"]:
            failures += 1
    var report := {"schema": "openazrael.intro_realtime_av_tests.v311", "status": "PASS" if failures == 0 else "FAIL",
        "checks": checks, "failed": failures, "clock_samples": samples, "frame_events": frame_events,
        "original_runtime_sync": "HOLD", "scope": "Godot real-clock playback and engine audio bus, not external oracle"}
    var file := FileAccess.open("res://.tmp/intro_decode_v311/godot_intro_av_tests.json", FileAccess.WRITE)
    file.store_string(JSON.stringify(report, "  ")); file.close()
    print("INTRO_AV_V311 ", JSON.stringify({"status": report["status"], "checks": checks.size(), "failed": failures,
        "elapsed": elapsed, "peak": peak, "rms": rms, "max_internal_skew": max_skew}))
    await get_tree().process_frame
    get_tree().quit(0 if failures == 0 else 1)
