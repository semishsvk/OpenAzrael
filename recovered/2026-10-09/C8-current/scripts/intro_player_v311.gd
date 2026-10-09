extends CanvasLayer
## Lossless source-derived movie playback. Codec PASS is not original-runtime fidelity PASS.
## Frame/audio resources are restored by tools/build_intro_assets_v311.py.

signal sequence_started
signal clip_started(clip_id: String)
signal frame_displayed(clip_id: String, frame_index: int)
signal sequence_finished(reason: String)

const MANIFEST := "res://data/runtime_generated/intro_movies_v311.json"
const ACTIVE_META := "openazrael_intro_active"
const OWNER_META := "openazrael_intro_owner"

@export var auto_start := true
@export var manifest_path := MANIFEST
var manual_clock := false

var _manifest: Dictionary = {}
var _clips: Dictionary = {}
var _order: Array[String] = []
var _textures: Dictionary = {}
var _audio_streams: Dictionary = {}
var _audio: AudioStreamPlayer
var _image: TextureRect
var _backdrop: ColorRect
var _owns_pause := false
var _was_paused := false
var _previous_mouse_mode: int = Input.MOUSE_MODE_VISIBLE
var _active := false
var _clip_index := -1
var _frame_index := -1
var _elapsed := 0.0
var _audio_wait := 0.0
var _clip_started_usec := 0
var _first_process_tick := false
var _last_error := ""
var _last_reason := ""
var _played_frames := 0
var _startup_owns_title := false

func _automatic_enabled() -> bool:
    if not auto_start or Engine.is_editor_hint():
        return false
    if OS.get_environment("OPENAZRAEL_SKIP_INTRO") == "1" or "--skip-intro" in OS.get_cmdline_user_args():
        return false
    return DisplayServer.get_name() != "headless" or OS.get_environment("OPENAZRAEL_FORCE_INTRO") == "1"

func _enter_tree() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    layer = 1000
    # The scene places this node before gameplay children. Pause before they tick.
    if _automatic_enabled():
        _claim_pause()

func _ready() -> void:
    _build_surface()
    visible = _owns_pause
    if _automatic_enabled():
        call_deferred("begin")

func _build_surface() -> void:
    _backdrop = ColorRect.new()
    _backdrop.name = "IntroBlackMatte"
    _backdrop.color = Color.BLACK
    _backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    _backdrop.mouse_filter = Control.MOUSE_FILTER_STOP
    add_child(_backdrop)
    _image = TextureRect.new()
    _image.name = "SourceFrame"
    _image.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
    _image.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    _image.stretch_mode = TextureRect.STRETCH_SCALE
    _image.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
    _image.mouse_filter = Control.MOUSE_FILTER_IGNORE
    add_child(_image)
    _audio = AudioStreamPlayer.new()
    _audio.name = "IntroSourceAudio"
    _audio.process_mode = Node.PROCESS_MODE_ALWAYS
    _audio.bus = &"Master"
    add_child(_audio)
    get_viewport().size_changed.connect(_layout_source_frame)

func _claim_pause() -> bool:
    if _owns_pause:
        return true
    var tree := get_tree()
    if tree.has_meta(OWNER_META):
        _last_error = "another_intro_owns_pause"
        return false
    _was_paused = tree.paused
    _previous_mouse_mode = Input.mouse_mode
    tree.set_meta(OWNER_META, get_instance_id())
    tree.set_meta(ACTIVE_META, true)
    tree.paused = true
    _owns_pause = true
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
    return true

func _release_pause() -> void:
    if not _owns_pause:
        return
    var tree := get_tree()
    if tree != null and int(tree.get_meta(OWNER_META, -1)) == get_instance_id():
        tree.remove_meta(OWNER_META)
        tree.remove_meta(ACTIVE_META)
        tree.paused = _was_paused
        Input.mouse_mode = _previous_mouse_mode
    _owns_pause = false

func _exit_tree() -> void:
    if is_instance_valid(_audio):
        _audio.stop()
        _audio.stream = null
    if is_instance_valid(_image):
        _image.texture = null
    _textures.clear()
    _audio_streams.clear()
    _release_pause()

func _record(kind: String, values: Dictionary) -> void:
    var diagnostics := get_node_or_null("/root/CandidateDiagnostics")
    if diagnostics != null and diagnostics.has_method("record_event"):
        diagnostics.call("record_event", kind, values)

func _load_assets(requested: Array[String]) -> bool:
    _last_error = ""
    _textures.clear()
    _audio_streams.clear()
    if not FileAccess.file_exists(manifest_path):
        _last_error = "missing_intro_manifest"
        return false
    var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(manifest_path))
    if not parsed is Dictionary or String(parsed.get("schema", "")) != "openazrael.intro_runtime.v311":
        _last_error = "invalid_intro_manifest"
        return false
    _manifest = parsed
    if not _manifest.get("clips", null) is Dictionary:
        _last_error = "invalid_intro_clips"
        return false
    _clips = _manifest["clips"]
    _order.clear()
    var selected: Variant = requested if not requested.is_empty() else _manifest.get("startup_order", [])
    if not selected is Array or selected.is_empty():
        _last_error = "empty_intro_sequence"
        return false
    for raw_id: Variant in selected:
        var id := String(raw_id)
        if not _clips.has(id) or not _clips[id] is Dictionary:
            _last_error = "unknown_intro_clip:" + id
            return false
        var clip: Dictionary = _clips[id]
        var count := int(clip.get("frame_count", 0))
        var fps := float(clip.get("fps", 0))
        var width := int(clip.get("width", 0))
        var height := int(clip.get("height", 0))
        var sequence: Variant = clip.get("sequence", [])
        var duration := float(clip.get("duration", 0))
        if not is_finite(fps) or not is_finite(duration) or count < 1 or count > 10000 or fps <= 0 or fps > 120 or width < 1 or height < 1 or width > 4096 or height > 4096:
            _last_error = "invalid_intro_geometry_or_clock:" + id
            return false
        if not sequence is Array or sequence.size() != count or duration + 0.00000001 < float(count) / fps or duration > 3600:
            _last_error = "invalid_intro_sequence_length:" + id
            return false
        for frame: Variant in sequence:
            if not frame is Dictionary:
                _last_error = "invalid_intro_frame:" + id
                return false
            var path := String(frame.get("path", ""))
            if not path.begins_with("res://assets/intro_v311/") or ".." in path or not ResourceLoader.exists(path):
                _last_error = "missing_intro_frame:" + path
                return false
            if not _textures.has(path):
                var resource: Resource = load(path)
                if not resource is Texture2D or resource.get_width() != width or resource.get_height() != height:
                    _last_error = "invalid_intro_texture:" + path
                    return false
                _textures[path] = resource
        var placement: Variant = clip.get("source_position", [(640 - width) / 2, (480 - height) / 2])
        if not placement is Array or placement.size() != 2:
            _last_error = "invalid_intro_source_placement:" + id
            return false
        if typeof(placement[0]) not in [TYPE_INT, TYPE_FLOAT] or typeof(placement[1]) not in [TYPE_INT, TYPE_FLOAT]:
            _last_error = "invalid_intro_source_placement:" + id
            return false
        if not is_finite(float(placement[0])) or not is_finite(float(placement[1])) or float(placement[0]) < 0 or float(placement[1]) < 0 or float(placement[0]) + width > 640 or float(placement[1]) + height > 480:
            _last_error = "invalid_intro_source_placement:" + id
            return false
        var audio_meta: Variant = clip.get("audio", null)
        if audio_meta != null:
            if not audio_meta is Dictionary:
                _last_error = "invalid_intro_audio_metadata:" + id
                return false
            var path := String(audio_meta.get("path", ""))
            if not path.begins_with("res://assets/intro_v311/") or ".." in path or not ResourceLoader.exists(path):
                _last_error = "missing_intro_audio:" + id
                return false
            var stream: Resource = load(path)
            if not stream is AudioStreamWAV or stream.get_length() <= 0:
                _last_error = "invalid_intro_audio:" + id
                return false
            if (stream as AudioStreamWAV).format not in [AudioStreamWAV.FORMAT_8_BITS, AudioStreamWAV.FORMAT_16_BITS]:
                _last_error = "lossy_intro_audio_import:" + id
                return false
            if (stream as AudioStreamWAV).mix_rate != int(audio_meta.get("sample_rate", 0)) or (stream as AudioStreamWAV).stereo != (int(audio_meta.get("channels", 1)) == 2):
                _last_error = "intro_audio_rate_or_channel_mismatch:" + id
                return false
            (stream as AudioStreamWAV).loop_mode = AudioStreamWAV.LOOP_DISABLED
            if absf(stream.get_length() - float(audio_meta.get("duration", 0))) > 0.002:
                _last_error = "intro_audio_duration_mismatch:" + id
                return false
            _audio_streams[id] = stream
        _order.append(id)
    return true

func begin(requested: Array[String] = []) -> bool:
    if _active:
        return false
    _startup_owns_title = false
    if not _load_assets(requested):
        _finish("asset_error")
        return false
    if not _claim_pause():
        _finish("ownership_error")
        return false
    _startup_owns_title = requested.is_empty() and bool(_manifest.get("startup_includes_title", false))
    _active = true
    visible = true
    _clip_index = -1
    _played_frames = 0
    _last_reason = ""
    _record("intro_sequence_started", {"order": _order, "startup_title_handled": startup_title_was_handled(),
        "source_rect": [_image.position.x, _image.position.y, _image.size.x, _image.size.y] if is_instance_valid(_image) else [],
        "fidelity": _manifest.get("fidelity_status", "HOLD")})
    sequence_started.emit()
    _start_clip(0)
    return true

func _start_clip(index: int) -> void:
    _audio.stop()
    _audio.stream = null
    if index >= _order.size():
        _finish("completed")
        return
    _clip_index = index
    _frame_index = -1
    _elapsed = 0.0
    _audio_wait = 0.0
    _clip_started_usec = Time.get_ticks_usec()
    _first_process_tick = true
    var id := _order[index]
    if _audio_streams.has(id):
        _audio.stream = _audio_streams[id]
        _audio.play()
    _record("intro_clip_started", {"clip": id, "source": _clips[id]["source"], "source_sha256": _clips[id]["source_sha256"]})
    clip_started.emit(id)
    _show_frame(0)

func _show_frame(index: int) -> void:
    if index == _frame_index or not _active:
        return
    var id := _order[_clip_index]
    var clip: Dictionary = _clips[id]
    _frame_index = clampi(index, 0, int(clip["frame_count"]) - 1)
    var entry: Dictionary = clip["sequence"][_frame_index]
    _image.texture = _textures[String(entry["path"])]
    _layout_source_frame()
    _played_frames += 1
    frame_displayed.emit(id, _frame_index)

func startup_title_was_handled() -> bool:
    return _startup_owns_title and _last_reason in ["completed", "skipped"]

func _layout_source_frame() -> void:
    if not is_instance_valid(_image) or _clip_index < 0 or _clip_index >= _order.size():
        return
    var clip: Dictionary = _clips[_order[_clip_index]]
    var width := int(clip["width"])
    var height := int(clip["height"])
    var placement: Array = clip.get("source_position", [(640 - width) / 2, (480 - height) / 2])
    var viewport_size := get_viewport().get_visible_rect().size
    var scale_factor := minf(viewport_size.x / 640.0, viewport_size.y / 480.0)
    var offset := (viewport_size - Vector2(640, 480) * scale_factor) * 0.5
    _image.position = offset + Vector2(float(placement[0]), float(placement[1])) * scale_factor
    _image.size = Vector2(width, height) * scale_factor

func _process(delta: float) -> void:
    if _active and not manual_clock:
        var movie_delta := delta
        if _first_process_tick:
            # The first engine delta can include synchronous asset loading
            # before audio/clip start. Never charge that time to the movie.
            _first_process_tick = false
            movie_delta = minf(delta, float(Time.get_ticks_usec() - _clip_started_usec) / 1000000.0)
        advance(movie_delta)

func advance(delta: float) -> void:
    if not _active or delta < 0 or not is_finite(delta):
        return
    var remaining := delta
    while _active:
        var clip: Dictionary = _clips[_order[_clip_index]]
        var duration := float(clip["duration"])
        var step := minf(remaining, maxf(duration - _elapsed, 0.0))
        _elapsed += step
        remaining -= step
        _show_frame(mini(int(floor((_elapsed + 0.00000001) * float(clip["fps"]))), int(clip["frame_count"]) - 1))
        if _elapsed + 0.00000001 >= duration:
            # In real time, let the audio mixer finish its last sample block.
            # Manual replay uses the exact manifest duration instead.
            if not manual_clock and _audio.playing:
                _audio_wait += delta
                if _audio_wait > 2.0:
                    _last_error = "intro_audio_finish_timeout"
                    _finish("audio_error")
                break
            _start_clip(_clip_index + 1)
            if remaining > 0.00000001:
                continue
        break

func skip_current() -> void:
    if _active:
        _record("intro_skip_clip", {"clip": _order[_clip_index]})
        _start_clip(_clip_index + 1)

func skip_all() -> void:
    if _active or _owns_pause:
        _finish("skipped")

func _input(event: InputEvent) -> void:
    if not _active and not _owns_pause:
        return
    # Consume first: the same Escape/click must never reach title/gameplay handlers.
    get_viewport().set_input_as_handled()
    if event is InputEventKey and event.pressed and not event.echo:
        if event.keycode == KEY_ESCAPE:
            skip_all()
        elif event.keycode in [KEY_SPACE, KEY_ENTER, KEY_KP_ENTER]:
            skip_current()
    elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
        skip_current()

func _finish(reason: String) -> void:
    _active = false
    _last_reason = reason
    if is_instance_valid(_audio):
        _audio.stop()
        _audio.stream = null
    visible = false
    if is_instance_valid(_image):
        _image.texture = null
    _release_pause()
    _record("intro_sequence_finished", {"reason": reason, "error": _last_error, "presented_frames": _played_frames})
    _textures.clear()
    _audio_streams.clear()
    sequence_finished.emit(reason)

func debug_snapshot() -> Dictionary:
    return {"active": _active, "owns_pause": _owns_pause, "clip_index": _clip_index,
        "clip": _order[_clip_index] if _clip_index >= 0 and _clip_index < _order.size() else "",
        "frame_index": _frame_index, "elapsed": _elapsed, "presented_frames": _played_frames,
        "audio_playing": _audio.playing if is_instance_valid(_audio) else false,
        "last_error": _last_error, "last_reason": _last_reason,
        "startup_title_handled": startup_title_was_handled(),
        "source_rect": [_image.position.x, _image.position.y, _image.size.x, _image.size.y] if is_instance_valid(_image) else [],
        "fidelity": _manifest.get("fidelity_status", "HOLD")}
