extends CanvasLayer

@onready var room_manager = get_node("../RoomManager")
var panel: PanelContainer
var text_label: Label
var active := false
var lines: Array[String] = []
var index := 0

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    panel = PanelContainer.new()
    panel.name = "ConversationPanel"
    panel.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
    panel.position = Vector2(220, 500)
    panel.custom_minimum_size = Vector2(840, 150)
    panel.visible = false
    var box := StyleBoxFlat.new()
    box.bg_color = Color(0, 0, 0, 0.88)
    box.set_corner_radius_all(6)
    panel.add_theme_stylebox_override("panel", box)
    text_label = Label.new()
    text_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    text_label.add_theme_font_size_override("font_size", 20)
    text_label.add_theme_color_override("font_color", Color(0.96, 0.96, 0.92, 1))
    panel.add_child(text_label)
    add_child(panel)
    if room_manager.has_signal("conversation_presented"):
        room_manager.conversation_presented.connect(_on_conversation_presented)

func _on_conversation_presented(payload: Dictionary) -> void:
    lines.clear()
    var character := String(payload.get("character", ""))
    lines.append("%s: %s" % [character, String(payload.get("opening", ""))])
    var branches: Dictionary = payload.get("branches", {})
    for key in ["Ni1A_30", "Ni1A_A", "Ni1A_999"]:
        if branches.has(key):
            var row: Dictionary = branches[key]
            var display := String(row.get("display", "")).strip_edges()
            if not display.is_empty():
                lines.append("%s: %s" % [character, display])
    if lines.is_empty():
        return
    index = 0
    active = true
    panel.visible = true
    get_tree().paused = true
    _refresh()
    CandidateDiagnostics.record_event("conversation_ui", {"status":"OPEN","character":character,"lines":lines.size()})

func _refresh() -> void:
    text_label.text = lines[index] + "\n\n[E / Enter] Continue"

func _unhandled_input(event: InputEvent) -> void:
    if not active:
        return
    if event.is_action_pressed("interact") or (event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_ENTER):
        index += 1
        if index >= lines.size():
            active = false
            panel.visible = false
            get_tree().paused = false
            CandidateDiagnostics.record_event("conversation_ui", {"status":"CLOSED"})
        else:
            _refresh()
        get_viewport().set_input_as_handled()
