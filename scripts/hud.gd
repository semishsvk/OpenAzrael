extends CanvasLayer

@onready var label: Label = $Panel/Label
@onready var room_manager = get_node("../RoomManager")
var audio_debug_visible := false
var audio_debug_panel: PanelContainer
var audio_debug_label: Label
const AudioDebugView := preload("res://scripts/audio_debug_view_v69.gd")
const AudioParityCapture := preload("res://scripts/audio_parity_capture_v71.gd")
const AUDIO_CAPTURE_PATH := "user://openazrael_audio_capture_v71.jsonl"
var capture_notice := ""

func _ready() -> void:
    _build_audio_debug_panel()

func _unhandled_key_input(event: InputEvent) -> void:
    if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F8:
        audio_debug_visible = not audio_debug_visible
        if is_instance_valid(audio_debug_panel):
            audio_debug_panel.visible = audio_debug_visible
        get_viewport().set_input_as_handled()
    elif event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F9:
        _capture_audio_parity()
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

func _build_audio_debug_panel() -> void:
    audio_debug_panel = PanelContainer.new()
    audio_debug_panel.name = "AudioDebugPanelV69"
    audio_debug_panel.position = Vector2(14, 112)
    audio_debug_panel.custom_minimum_size = Vector2(910, 0)
    audio_debug_panel.visible = false
    var box := StyleBoxFlat.new()
    box.bg_color = Color(0, 0, 0, 0.82)
    box.corner_radius_top_left = 5
    box.corner_radius_top_right = 5
    box.corner_radius_bottom_left = 5
    box.corner_radius_bottom_right = 5
    audio_debug_panel.add_theme_stylebox_override("panel", box)
    audio_debug_label = Label.new()
    audio_debug_label.name = "AudioDebugLabel"
    audio_debug_label.add_theme_font_size_override("font_size", 14)
    audio_debug_label.add_theme_color_override("font_color", Color(0.92, 0.92, 0.92, 1))
    audio_debug_label.text = "Audio debug initializing..."
    audio_debug_panel.add_child(audio_debug_label)
    add_child(audio_debug_panel)

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
    label.text = "OpenAzrael reconstruction v71\nRoom: %s\nInventory: %s%s\nWASD move | Shift sprint | Mouse look | E interact | F8 audio debug | F9 parity capture | 1/2/3 debug room" % [room_manager.current_room_id, ", ".join(inv) if not inv.is_empty() else "(empty)", status]
    if audio_debug_visible and is_instance_valid(audio_debug_label):
        var la = room_manager.legacy_audio
        var snaps: Array[Dictionary] = []
        var mode_name := "UNKNOWN"
        var master := 99
        if is_instance_valid(la):
            snaps = la.call("get_debug_snapshot")
            mode_name = "CLASSIC" if int(la.get("audio_mode")) == 0 else "ENHANCED"
            master = int(la.get("parity_master_volume"))
        audio_debug_label.text = AudioDebugView.format_snapshot(room_manager.current_room_id, mode_name, snaps, master) + ("\n" + capture_notice if not capture_notice.is_empty() else "")
