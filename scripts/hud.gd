extends CanvasLayer

@onready var label: Label = $Panel/Label
@onready var room_manager = get_node("../RoomManager")
@onready var player = get_node("../Player")
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
    _build_candidate_debug_panel()
    _build_audio_debug_panel()

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
    var inv: Array[String] = []
    for k in DemoState.inventory.keys():
        inv.append(String(k))
    inv.sort()
    var status := ""
    if DemoState.flag("demo_complete"):
        status = "\nDEMO COMPLETE — Shield acquired"
    elif DemoState.flag("R8BathDrain"):
        status = "\nBaptistery bath: DRAINED"
    label.text = "%s | %s\nRoom: %s\nInventory: %s%s\nWASD move | Shift sprint | Mouse look | E interact | F6 triggers | F7 candidate debug | F8 audio | F9 parity | F10 state dump | F11 bug report | 1/2/3 debug room" % [
        CandidateDiagnostics.BUILD_ID,
        CandidateDiagnostics.BUILD_CHECKPOINT,
        room_manager.current_room_id,
        ", ".join(inv) if not inv.is_empty() else "(empty)",
        status
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
        audio_debug_label.text = AudioDebugView.format_snapshot(room_manager.current_room_id, mode_name, snaps, master, LegacyEvents.captured_audio()) + ("\n" + capture_notice if not capture_notice.is_empty() else "")
