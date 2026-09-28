extends Control
class_name LegacyScannerRuntimeV164

const SOURCE_JSON := "res://assets/ui/legacy_menu/legacy_scanner_v164.json"
const SOURCE_FONT := "res://assets/ui/legacy_menu/RUSGLD2.png"
const DEFAULT_RECT := Rect2(452, 54, 172, 246)
const FONT_CELL := Vector2(10, 12)
const FIRST_CODEPOINT := 35
const CELL_COUNT := 138
const SPACE_ADVANCE := 5.0
const LINE_ADVANCE := 12.0

var room_manager: Node
var source: Dictionary = {}
var font_texture: Texture2D
var audio_player: AudioStreamPlayer
var display_text := ""
var display_mode := "idle"
var active := false
var pending_room := ""
var _sequence_generation := 0
var _last_room := ""

func initialize(manager: Node) -> void:
    room_manager = manager
    name = "LegacyScannerV164"
    position = DEFAULT_RECT.position
    size = DEFAULT_RECT.size
    clip_contents = true
    mouse_filter = Control.MOUSE_FILTER_IGNORE
    z_index = 30
    source = _load_source()
    font_texture = load(SOURCE_FONT) as Texture2D if ResourceLoader.exists(SOURCE_FONT) else null
    audio_player = AudioStreamPlayer.new()
    audio_player.name = "LegacyScannerAudioV164"
    audio_player.bus = "SFX"
    add_child(audio_player)
    if room_manager != null and room_manager.has_signal("room_changed"):
        var callback := Callable(self, "_on_room_changed")
        if not room_manager.is_connected("room_changed", callback):
            room_manager.connect("room_changed", callback)
    if DisplayServer.get_name() == "headless":
        active = true
        var room_id := String(room_manager.get("current_room_id")) if room_manager != null else ""
        if not room_id.is_empty():
            _show_environment_result(room_id)
    else:
        visible = false
    CandidateDiagnostics.record_event("legacy_scanner_v164_initialized", {
        "source_ready": not source.is_empty(),
        "font_ready": font_texture != null,
        "rect": [position.x, position.y, size.x, size.y],
    })

func _load_source() -> Dictionary:
    if not FileAccess.file_exists(SOURCE_JSON):
        CandidateDiagnostics.record_event("legacy_scanner_v164_source_missing", {"path": SOURCE_JSON})
        return {}
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(SOURCE_JSON))
    if parsed is Dictionary and int(parsed.get("version", 0)) == 164:
        return parsed
    CandidateDiagnostics.record_event("legacy_scanner_v164_source_invalid", {"path": SOURCE_JSON})
    return {}

func _message_text(raw) -> String:
    return String(raw).strip_edges()

func _boot_text() -> String:
    var lines: Array[String] = []
    for row in source.get("boot", []):
        if not row is Dictionary:
            continue
        # HUDMES boot rows intentionally contain leading spaces (the source
        # builds the stylized Model-7 glyph with them). Preserve those bytes;
        # the restore step already removes only source trailing terminators.
        var text := String(row.get("text", ""))
        if not text.strip_edges().is_empty():
            lines.append(text)
    return "\n".join(lines)

func _room_text(room_id: String) -> String:
    var rooms = source.get("rooms", {})
    if not rooms is Dictionary or not rooms.has(room_id):
        return ""
    var row = rooms[room_id]
    if not row is Dictionary:
        return ""
    return _message_text(row.get("text", ""))

func _scan_status() -> String:
    return _message_text(source.get("scan_status", "Updating Environment Scan...."))

func _set_display(mode: String, text: String, room_id: String = "") -> void:
    display_mode = mode
    display_text = text
    if not room_id.is_empty():
        _last_room = room_id
    visible = active and not display_text.is_empty() and DisplayServer.get_name() != "headless"
    queue_redraw()
    CandidateDiagnostics.record_event("legacy_scanner_v164_display", {
        "mode": mode,
        "room": room_id,
        "text": text,
    })

func _audio_stream(kind: String) -> AudioStream:
    var audio = source.get("audio", {})
    if not audio is Dictionary or not audio.has(kind):
        return null
    var row = audio[kind]
    if not row is Dictionary:
        return null
    var path := String(row.get("path", ""))
    return load(path) as AudioStream if not path.is_empty() and ResourceLoader.exists(path) else null

func _play_and_wait(kind: String, generation: int) -> void:
    if DisplayServer.get_name() == "headless" or audio_player == null:
        return
    var stream := _audio_stream(kind)
    if stream == null:
        return
    audio_player.stop()
    audio_player.stream = stream
    audio_player.play()
    await audio_player.finished
    if generation != _sequence_generation:
        return

func start_boot_sequence() -> void:
    active = true
    pending_room = String(room_manager.get("current_room_id")) if room_manager != null else pending_room
    _sequence_generation += 1
    var generation := _sequence_generation
    _run_boot(generation)

func _run_boot(generation: int) -> void:
    var text := _boot_text()
    if text.is_empty():
        _finish_boot(generation)
        return
    _set_display("boot", text)
    await _play_and_wait("hud_boot", generation)
    _finish_boot(generation)

func _finish_boot(generation: int) -> void:
    if generation != _sequence_generation:
        return
    var room_id := pending_room
    if room_id.is_empty() and room_manager != null:
        room_id = String(room_manager.get("current_room_id"))
    if not room_id.is_empty():
        show_environment_scan(room_id)

func _on_room_changed(room_id: String) -> void:
    pending_room = room_id
    if not active:
        return
    if DisplayServer.get_name() == "headless":
        _show_environment_result(room_id)
        return
    show_environment_scan(room_id)

func show_environment_scan(room_id: String) -> void:
    pending_room = room_id
    if not active:
        return
    _sequence_generation += 1
    var generation := _sequence_generation
    _run_environment_scan(room_id, generation)

func _run_environment_scan(room_id: String, generation: int) -> void:
    var result := _room_text(room_id)
    if result.is_empty():
        _set_display("hold_missing_room_scan", _scan_status(), room_id)
        return
    _set_display("environment_scan", _scan_status(), room_id)
    await _play_and_wait("scan", generation)
    if generation != _sequence_generation:
        return
    _show_environment_result(room_id)

func _show_environment_result(room_id: String) -> void:
    var result := _room_text(room_id)
    if result.is_empty():
        _set_display("hold_missing_room_scan", "", room_id)
        return
    _set_display("environment_result", result, room_id)

func _glyph_width(character: String) -> float:
    return SPACE_ADVANCE if character == " " else FONT_CELL.x

func _wrap_line(text: String) -> Array[String]:
    var out: Array[String] = []
    var current := ""
    var width := 0.0
    var max_width := size.x
    for character in text:
        if character == "\n":
            out.append(current)
            current = ""
            width = 0.0
            continue
        var advance := _glyph_width(character)
        if width + advance > max_width and not current.is_empty():
            out.append(current.rstrip(" "))
            current = ""
            width = 0.0
        current += character
        width += advance
    if not current.is_empty() or out.is_empty():
        out.append(current)
    return out

func _wrapped_lines(text: String) -> Array[String]:
    var out: Array[String] = []
    for source_line in text.replace("\r", "").split("\n"):
        for wrapped in _wrap_line(String(source_line)):
            out.append(wrapped)
    return out

func _draw_glyph(character: String, at: Vector2) -> float:
    if character == " ":
        return SPACE_ADVANCE
    if font_texture == null or character.is_empty():
        return FONT_CELL.x
    var codepoint := character.unicode_at(0)
    var cell := codepoint - FIRST_CODEPOINT
    if cell < 0 or cell >= CELL_COUNT:
        cell = 63 - FIRST_CODEPOINT
    var source_rect := Rect2(float(cell) * FONT_CELL.x, 0.0, FONT_CELL.x, FONT_CELL.y)
    draw_texture_rect_region(font_texture, Rect2(at, FONT_CELL), source_rect)
    return FONT_CELL.x

func _draw() -> void:
    if font_texture == null or display_text.is_empty():
        return
    var y := 0.0
    for line in _wrapped_lines(display_text):
        if y + FONT_CELL.y > size.y:
            break
        var x := 0.0
        for character in line:
            x += _draw_glyph(character, Vector2(x, y))
            if x >= size.x:
                break
        y += LINE_ADVANCE

func debug_snapshot() -> Dictionary:
    return {
        "schema": "openazrael.legacy_scanner.runtime_snapshot",
        "version": 164,
        "active": active,
        "mode": display_mode,
        "room": _last_room,
        "text": display_text,
        "rect": [position.x, position.y, size.x, size.y],
        "font_ready": font_texture != null,
        "source_ready": not source.is_empty(),
        "timing": "SOURCE_AUDIO_EVENT_BOUNDARIES_ONLY",
    }
