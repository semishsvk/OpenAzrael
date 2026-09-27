extends CanvasLayer

@onready var label: Label = $Panel/Label
@onready var room_manager = get_node("../RoomManager")
@onready var player = get_node("../Player")
@onready var interaction_probe = get_node("../Player/Camera3D/InteractionProbe")
@onready var legacy_menu = get_node_or_null("../LegacyMenuV145")
const LegacyCursorCatalogV143 := preload("res://scripts/legacy_cursor_catalog_v143.gd")
var interaction_cursor_layer: CanvasLayer
var interaction_cursor: TextureRect
var interaction_cursor_cache: Dictionary = {}
var interaction_cursor_id := ""
var audio_debug_visible := false
var audio_debug_panel: PanelContainer
var audio_debug_label: Label
var candidate_debug_visible := false
var candidate_debug_panel: PanelContainer
var candidate_debug_label: Label
const AudioDebugView := preload("res://scripts/audio_debug_view_v69.gd")
const AudioParityCapture := preload("res://scripts/audio_parity_capture_v71.gd")
const AUDIO_CAPTURE_PATH := "user://openazrael_audio_capture_v71.jsonl"
var capture_notice := ""
var state_dump_notice := ""

func _ready() -> void:
    # The source pointer must keep following the mouse while title/service UI
    # pauses gameplay. Player and room processing remain paused independently.
    process_mode = Node.PROCESS_MODE_ALWAYS
    var legacy_classic_mode_active := is_instance_valid(legacy_menu)
    if legacy_classic_mode_active and is_instance_valid(label):
        var legacy_overlay := label.get_parent()
        if legacy_overlay is CanvasItem:
            (legacy_overlay as CanvasItem).visible = false
    _build_candidate_debug_panel()
    _build_audio_debug_panel()
    _build_interaction_cursor()

func _unhandled_key_input(event: InputEvent) -> void:
    if not event is InputEventKey or not event.pressed or event.echo:
        return
    if event.keycode == KEY_F7:
        candidate_debug_visible = not candidate_debug_visible
        if is_instance_valid(candidate_debug_panel):
            candidate_debug_panel.visible = candidate_debug_visible
        CandidateDiagnostics.record_event("candidate_hud_visibility", {"visible": candidate_debug_visible})
        get_viewport().set_input_as_handled()
    elif event.keycode == KEY_F8:
        audio_debug_visible = not audio_debug_visible
        if is_instance_valid(audio_debug_panel):
            audio_debug_panel.visible = audio_debug_visible
        get_viewport().set_input_as_handled()
    elif event.keycode == KEY_F9:
        _capture_audio_parity()
        get_viewport().set_input_as_handled()
    elif event.keycode == KEY_F10:
        var path := CandidateDiagnostics.dump_state(room_manager.current_room_id, player.global_position)
        state_dump_notice = "F10 state dump: " + (path if not path.is_empty() else "FAILED")
        get_viewport().set_input_as_handled()

func _build_interaction_cursor() -> void:
    interaction_cursor_layer = CanvasLayer.new()
    interaction_cursor_layer.name = "InteractionCursorLayerV146"
    interaction_cursor_layer.layer = 100
    add_child(interaction_cursor_layer)

    interaction_cursor = TextureRect.new()
    interaction_cursor.name = "InteractionCursorV143"
    interaction_cursor.mouse_filter = Control.MOUSE_FILTER_IGNORE
    interaction_cursor.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
    interaction_cursor.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    interaction_cursor.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
    interaction_cursor.size = LegacyCursorCatalogV143.DISPLAY_SIZE
    interaction_cursor.z_index = 1000
    interaction_cursor_layer.add_child(interaction_cursor)
    _update_interaction_cursor()

func _cursor_texture(cursor_id: String) -> Texture2D:
    var normalized := LegacyCursorCatalogV143.normalize_id(cursor_id)
    if interaction_cursor_cache.has(normalized):
        return interaction_cursor_cache[normalized] as Texture2D
    var texture := LegacyCursorCatalogV143.load_texture(normalized)
    if texture == null and normalized != LegacyCursorCatalogV143.FALLBACK:
        texture = LegacyCursorCatalogV143.load_texture(LegacyCursorCatalogV143.FALLBACK)
    interaction_cursor_cache[normalized] = texture
    return texture

func _update_interaction_cursor() -> void:
    if not is_instance_valid(interaction_cursor):
        return
    var next_id := "POINTER"
    var menu_blocks_world := (
        is_instance_valid(legacy_menu)
        and legacy_menu.has_method("blocks_world_cursor")
        and bool(legacy_menu.call("blocks_world_cursor"))
    )
    if not menu_blocks_world and is_instance_valid(interaction_probe) and interaction_probe.has_method("current_cursor_id"):
        next_id = String(interaction_probe.call("current_cursor_id"))
    var normalized := LegacyCursorCatalogV143.normalize_id(next_id)
    if normalized != interaction_cursor_id or interaction_cursor.texture == null:
        interaction_cursor_id = normalized
        interaction_cursor.texture = _cursor_texture(normalized)
    interaction_cursor.visible = interaction_cursor.texture != null
    var viewport_size := get_viewport().get_visible_rect().size
    if DisplayServer.get_name() != "headless" and Input.mouse_mode == Input.MOUSE_MODE_VISIBLE:
        interaction_cursor.position = get_viewport().get_mouse_position() - interaction_cursor.size * 0.5
    else:
        interaction_cursor.position = (viewport_size - interaction_cursor.size) * 0.5

func _capture_audio_parity() -> void:
    var la = room_manager.legacy_audio
    var camera := get_viewport().get_camera_3d()
    if not is_instance_valid(la) or camera == null:
        capture_notice = "Audio capture unavailable"
        return
    var snaps: Array[Dictionary] = la.call("get_debug_snapshot")
    var mode_name := "CLASSIC" if int(la.get("audio_mode")) == 0 else "ENHANCED"
    var master := int(la.get("parity_master_volume"))
    var record := AudioParityCapture.build_record(room_manager.current_room_id, mode_name, camera.global_position, -camera.global_transform.basis.z.normalized(), snaps, master)
    var err := AudioParityCapture.append_jsonl(AUDIO_CAPTURE_PATH, record)
    capture_notice = "F9 capture saved: %s" % AUDIO_CAPTURE_PATH if err == OK else "F9 capture failed: %s" % error_string(err)

func _panel_box(alpha: float) -> StyleBoxFlat:
    var box := StyleBoxFlat.new()
    box.bg_color = Color(0, 0, 0, alpha)
    box.corner_radius_top_left = 5
    box.corner_radius_top_right = 5
    box.corner_radius_bottom_left = 5
    box.corner_radius_bottom_right = 5
    return box

func _build_candidate_debug_panel() -> void:
    candidate_debug_panel = PanelContainer.new()
    candidate_debug_panel.name = "CandidateDebugPanelV116"
    candidate_debug_panel.position = Vector2(14, 112)
    candidate_debug_panel.custom_minimum_size = Vector2(910, 0)
    candidate_debug_panel.visible = false
    candidate_debug_panel.add_theme_stylebox_override("panel", _panel_box(0.82))
    candidate_debug_label = Label.new()
    candidate_debug_label.name = "CandidateDebugLabel"
    candidate_debug_label.add_theme_font_size_override("font_size", 14)
    candidate_debug_label.add_theme_color_override("font_color", Color(0.92, 0.92, 0.92, 1))
    candidate_debug_label.text = "Candidate diagnostics initializing..."
    candidate_debug_panel.add_child(candidate_debug_label)
    add_child(candidate_debug_panel)

func _physical_audio_debug_text() -> String:
    var lines: Array[String] = []
    var master := AudioServer.get_bus_index("Master")
    if master < 0:
        lines.append("Master bus: MISSING")
    else:
        lines.append("Master bus: mute=%s volume_db=%.2f" % [str(AudioServer.is_bus_mute(master)), AudioServer.get_bus_volume_db(master)])
    var physical: Array = LegacyEvents.physical_audio_snapshot() if LegacyEvents.has_method("physical_audio_snapshot") else []
    lines.append("Event physical players: %d" % physical.size())
    for item in physical:
        var snap: Dictionary = item
        lines.append("   %s playing=%s stream=%s bus=%s vol=%.2f" % [
            String(snap.get("asset", "?")),
            str(bool(snap.get("playing", false))),
            str(bool(snap.get("stream_valid", false))),
            String(snap.get("bus", "?")),
            float(snap.get("volume_db", 0.0))
        ])
    return "\n".join(lines)

func _build_audio_debug_panel() -> void:
    audio_debug_panel = PanelContainer.new()
    audio_debug_panel.name = "AudioDebugPanelV69"
    audio_debug_panel.position = Vector2(14, 410)
    audio_debug_panel.custom_minimum_size = Vector2(910, 0)
    audio_debug_panel.visible = false
    audio_debug_panel.add_theme_stylebox_override("panel", _panel_box(0.82))
    audio_debug_label = Label.new()
    audio_debug_label.name = "AudioDebugLabel"
    audio_debug_label.add_theme_font_size_override("font_size", 14)
    audio_debug_label.add_theme_color_override("font_color", Color(0.92, 0.92, 0.92, 1))
    audio_debug_label.text = "Audio debug initializing..."
    audio_debug_panel.add_child(audio_debug_label)
    add_child(audio_debug_panel)

func _sorted_keys(source: Dictionary) -> String:
    var out: Array[String] = []
    for key in source.keys():
        out.append(String(key))
    out.sort()
    return ", ".join(out) if not out.is_empty() else "(none)"

func _true_keys(source: Dictionary) -> String:
    var out: Array[String] = []
    for key in source.keys():
        if bool(source[key]):
            out.append(String(key))
    out.sort()
    return ", ".join(out) if not out.is_empty() else "(none)"

func _process(_delta: float) -> void:
    _update_interaction_cursor()
    var inv: Array[String] = []
    for k in DemoState.inventory.keys():
        inv.append(String(k))
    inv.sort()
    var status := ""
    if DemoState.flag("demo_complete"):
        status = "\n" + LocalizationManager.tr_key("ui.hud.demo_complete")
    elif DemoState.flag("R8BathDrain"):
        status = "\n" + LocalizationManager.tr_key("ui.hud.bath_drained")
    label.text = "%s | %s\nRoom: %s\nInventory: %s%s\n%s" % [
        CandidateDiagnostics.BUILD_ID,
        CandidateDiagnostics.BUILD_CHECKPOINT,
        room_manager.current_room_id,
        ", ".join(inv) if not inv.is_empty() else LocalizationManager.tr_key("ui.hud.empty"),
        status,
        LocalizationManager.tr_key("ui.hud.controls")
    ]

    if candidate_debug_visible and is_instance_valid(candidate_debug_label):
        var p: Vector3 = player.global_position
        candidate_debug_label.text = "KG-001 Candidate diagnostics\nCheckpoint: %s\nRoom: %s | Player: (%.3f, %.3f, %.3f)\nState SHA-256: %s\nFlags(true): %s\nPuzzle nodes(true): %s\nValues: %s\nLast trigger: %s\nLast event: %s\nLast logical audio: %s\nEvent log: %s\nLast bug report: %s%s" % [
            CandidateDiagnostics.BUILD_CHECKPOINT,
            room_manager.current_room_id,
            p.x, p.y, p.z,
            DemoState.canonical_state_hash(),
            _true_keys(DemoState.flags),
            _true_keys(DemoState.puzzle_nodes),
            _sorted_keys(DemoState.values),
            CandidateDiagnostics.last_trigger,
            CandidateDiagnostics.last_event_text(),
            CandidateDiagnostics.last_audio,
            CandidateDiagnostics.EVENT_LOG_PATH,
            CandidateDiagnostics.last_bug_report if not CandidateDiagnostics.last_bug_report.is_empty() else "(none)",
            "\n" + state_dump_notice if not state_dump_notice.is_empty() else ""
        ]

    if audio_debug_visible and is_instance_valid(audio_debug_label):
        var la = room_manager.legacy_audio
        var snaps: Array[Dictionary] = []
        var mode_name := "UNKNOWN"
        var master := 99
        if is_instance_valid(la):
            snaps = la.call("get_debug_snapshot")
            mode_name = "CLASSIC" if int(la.get("audio_mode")) == 0 else "ENHANCED"
            master = int(la.get("parity_master_volume"))
        audio_debug_label.text = AudioDebugView.format_snapshot(room_manager.current_room_id, mode_name, snaps, master) + "\n" + _physical_audio_debug_text() + ("\n" + capture_notice if not capture_notice.is_empty() else "")
