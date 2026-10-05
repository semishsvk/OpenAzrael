extends Control
class_name LegacyScannerRuntimeV164

const SOURCE_JSON := "res://assets/ui/legacy_menu/legacy_scanner_v164.json"
const SOURCE_FONT := "res://assets/ui/legacy_menu/RUSGLD2.png"
const DEFAULT_RECT := Rect2(425, 84, 170, 206)
const FONT_CELL := Vector2(10, 12)
const FIRST_CODEPOINT := 35
const CELL_COUNT := 138
const SPACE_ADVANCE := 3.0
const METRICS_PATH := "res://data/ui/legacy_scanner_font_v214.json"
const LINE_ADVANCE := 12.0

var panel_image: Image
var panel_texture: ImageTexture
var source_font_image: Image
var pending_tokens: Array[String] = []
var text_cursor := Vector2i.ZERO
var startup_requested := false
var startup_started := false
var hint_timer_active := false
var hint_polls := 0
var hint_counter := 0
const HINT_MESSAGES := [136, 137, 139]

var room_manager: Node
var source: Dictionary = {}
var font_metrics: Dictionary = {}
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
    font_metrics = JSON.parse_string(FileAccess.get_file_as_string(METRICS_PATH))
    font_texture = load(SOURCE_FONT) as Texture2D if ResourceLoader.exists(SOURCE_FONT) else null
    panel_image = Image.create(170, 206, false, Image.FORMAT_RGBA8)
    panel_image.fill(Color.TRANSPARENT)
    panel_texture = ImageTexture.create_from_image(panel_image)
    source_font_image = font_texture.get_image() if font_texture != null else null
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
    var text := ""
    for id in range(3, 16):
        text += String(source.get("source_messages", {}).get(str(id), ""))
    return text

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
    _enqueue_source_text(text if text.ends_with("\n") else text + "\n\n")
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
    if startup_requested:
        _begin_source_startup()

func _glyph_width(character: String) -> float:
    if character == " ":
        return SPACE_ADVANCE
    var metric: Dictionary = font_metrics.get("glyphs", {}).get(str(character.unicode_at(0)), {})
    return float(metric.get("advance", FONT_CELL.x))

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
    var glyphs: Dictionary = font_metrics.get("glyphs", {})
    var metric: Dictionary = glyphs.get(str(character.unicode_at(0)), glyphs.get("63", {}))
    var width := float(metric.get("width", FONT_CELL.x))
    var source_rect := Rect2(float(metric.get("x", 0)), 0.0, width, FONT_CELL.y)
    draw_texture_rect_region(font_texture, Rect2(at, Vector2(width, FONT_CELL.y)), source_rect)
    return float(metric.get("advance", width))

func _draw() -> void:
    if panel_texture != null:
        draw_texture(panel_texture, Vector2.ZERO)

func _enqueue_source_text(text: String) -> void:
    var regex := RegEx.new()
    regex.compile("[^ \r\n]+|[ \r\n]")
    for match in regex.search_all(text):
        pending_tokens.append(match.get_string())

func _source_scroll() -> void:
    var amount := text_cursor.y + 12 - 206
    if amount <= 0:
        return
    var moved := panel_image.get_region(Rect2i(0, amount, 170, 206 - amount))
    panel_image.fill(Color.TRANSPARENT)
    panel_image.blit_rect(moved, Rect2i(0, 0, 170, 206 - amount), Vector2i.ZERO)
    text_cursor.y -= amount

func _source_text_poll() -> void:
    if source_font_image == null:
        return
    while not pending_tokens.is_empty():
        var token := pending_tokens[0]
        if token == "\r":
            pending_tokens.pop_front()
            continue
        if token == "\n":
            pending_tokens.pop_front()
            text_cursor.x = 0
            text_cursor.y += 12
            _source_scroll()
            break
        if token == " ":
            pending_tokens.pop_front()
            text_cursor.x += 3
            continue
        var advance := 0
        for character in token:
            advance += int(_glyph_width(character))
        if text_cursor.x + advance >= 170:
            text_cursor.x = 0
            text_cursor.y += 12
            _source_scroll()
            break
        pending_tokens.pop_front()
        _source_scroll()
        for character in token:
            var glyphs: Dictionary = font_metrics.get("glyphs", {})
            var metric: Dictionary = glyphs.get(str(character.unicode_at(0)), glyphs.get("63", {}))
            for y in range(12):
                for x in range(int(metric.get("width", 0))):
                    var color := source_font_image.get_pixel(int(metric.get("x", 0)) + x, y)
                    # Original VGA palette stores RGB6; native runtime expands by <<2.
                    color = Color8(color.r8 & 252, color.g8 & 252, color.b8 & 252, color.a8)
                    if color.a > 0 and text_cursor.x + x < 170:
                        panel_image.set_pixel(text_cursor.x + x, text_cursor.y + y, color)
            text_cursor.x += int(metric.get("advance", 0))
    panel_texture.update(panel_image)
    queue_redraw()

func request_source_startup() -> void:
    if startup_requested or startup_started:
        return
    startup_requested = true
    if active and display_mode == "environment_result":
        _begin_source_startup()

func _begin_source_startup() -> void:
    if startup_started:
        return
    startup_started = true
    hint_counter = 1
    hint_polls = 0
    hint_timer_active = true
    for id in [86, 138]:
        _enqueue_source_text(String(source.get("source_messages", {}).get(str(id), "")))
    display_mode = "source_startup"

func _process(_delta: float) -> void:
    if not active:
        return
    _source_text_poll()
    if not hint_timer_active:
        return
    hint_polls += 1
    if hint_polls < 100:
        return
    hint_polls = 0
    # WORLD timer 2 and flag 29: source presentation polls, never inferred Hz.
    if not pending_tokens.is_empty():
        return
    var id: int = HINT_MESSAGES[hint_counter - 1]
    _enqueue_source_text(String(source.get("source_messages", {}).get(str(id), "")))
    hint_counter += 1
    if hint_counter > 3:
        hint_timer_active = false

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
