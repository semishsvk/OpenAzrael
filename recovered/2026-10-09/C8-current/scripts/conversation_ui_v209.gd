extends CanvasLayer

const IR_PATH := "res://data/runtime_generated/niamh_conversation_ir_v209.json"
@onready var room_manager = get_node("../RoomManager")
var panel: PanelContainer
var text_label: RichTextLabel
var footer_label: Label
var active := false
var family := "1A"
var choices: Array[Dictionary] = []
var selected := 0
var response_mode := false
var current_record: Dictionary = {}

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    layer = 60
    panel = PanelContainer.new()
    panel.name = "ConversationPanel"
    panel.custom_minimum_size = Vector2.ZERO
    panel.visible = false
    var box := StyleBoxFlat.new()
    box.bg_color = Color(0,0,0,1.0)
    box.set_corner_radius_all(6)
    panel.add_theme_stylebox_override("panel", box)
    text_label = RichTextLabel.new()
    text_label.bbcode_enabled = true
    text_label.fit_content = false
    text_label.custom_minimum_size = Vector2.ZERO
    text_label.add_theme_font_size_override("normal_font_size", 19)
    var content := VBoxContainer.new()
    text_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
    content.add_child(text_label)
    footer_label = Label.new()
    footer_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    content.add_child(footer_label)
    panel.add_child(content)
    add_child(panel)
    get_viewport().size_changed.connect(_reflow)
    _reflow()
    room_manager.conversation_presented.connect(_on_conversation_presented)

# Keep dialogue to the right of the character view and above the lower HUD.
# The previous full-width panel concealed Niamh throughout her rise/REST.
# Placement is an authored usability fix until the original dialogue frame is captured.
func _reflow() -> void:
    var size := get_viewport().get_visible_rect().size
    var scale_factor := minf(size.x / 640.0, size.y / 480.0)
    var origin := (size - Vector2(640, 480) * scale_factor) * 0.5
    panel.position = origin + Vector2(380, 84) * scale_factor
    panel.size = Vector2(216, 242) * scale_factor
    text_label.add_theme_font_size_override("normal_font_size", maxi(12, roundi(12 * scale_factor)))
    footer_label.add_theme_font_size_override("font_size", maxi(10, roundi(10 * scale_factor)))

func _load_family(name: String) -> Array[Dictionary]:
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(IR_PATH))
    if not parsed is Dictionary: return []
    var families: Dictionary = parsed.get("families", {})
    if not families.has(name): return []
    var out: Array[Dictionary] = []
    for row in families[name].get("records", []):
        if not row is Dictionary: continue
        var player := String(row.get("player_text","")).strip_edges()
        var answer := String(row.get("niamh_text","")).strip_edges()
        # Never expose source control text or unresolved/missing answers as
        # playable dialogue.
        if player == "DO NOT DISPLAY" or answer == "Answer text missing!":
            continue
        out.append(row)
    return out

func _on_conversation_presented(payload: Dictionary) -> void:
    if String(payload.get("character","")) != "Niamh": return
    family = String(payload.get("family","1A"))
    choices = _load_family(family)
    if choices.is_empty(): return
    selected = 0
    response_mode = false
    current_record = {}
    active = true
    panel.visible = true
    get_tree().paused = true
    _refresh_choices()
    CandidateDiagnostics.record_event("conversation_ui", {"status":"OPEN","character":"Niamh","family":family,"choices":choices.size(),"ir":"v209"})

func _refresh_choices() -> void:
    var body := "[b]Conversation - Niamh[/b]\n\n"
    for i in range(choices.size()):
        var row: Dictionary = choices[i]
        var prefix := "[b]>[/b] " if i == selected else "  "
        body += prefix + String(row.get("player_text","")) + "\n"
    body += "\n[W/S or Up/Down] Select    [E / Enter] Speak    [Esc] Leave"
    text_label.text = body
    text_label.scroll_to_line(selected + 2)

func _show_response(row: Dictionary) -> void:
    current_record = row
    response_mode = true
    footer_label.text = "[E / Enter] Continue    [Esc] Leave"
    text_label.text = "[b]You:[/b] %s\n\n[b]Niamh:[/b] %s" % [String(row.get("player_text","")), String(row.get("niamh_text",""))]
    CandidateDiagnostics.record_event("conversation_choice", {"family":family,"id":String(row.get("id","")),"marker":String(row.get("source_marker",""))})

func _close(exit_record_id: String = "") -> void:
    active = false
    panel.visible = false
    get_tree().paused = false
    CandidateDiagnostics.record_event("conversation_ui", {"status":"CLOSED","family":family,"exit_record_id":exit_record_id})
    if exit_record_id == "999" and room_manager.has_method("request_niamh_source_exit"):
        room_manager.call("request_niamh_source_exit", exit_record_id)

func _unhandled_input(event: InputEvent) -> void:
    if not active or not event is InputEventKey or not event.pressed or event.echo:
        return
    if response_mode:
        if event.is_action_pressed("interact") or event.keycode == KEY_ENTER:
            var completed_id := String(current_record.get("id", ""))
            response_mode = false
            current_record = {}
            # NIAMH.DAT record 999 is the explicit leave branch. Completing its
            # source response closes the conversation and starts the authored
            # NOLOOP2 return motion instead of redisplaying the topic menu.
            if completed_id == "999":
                _close(completed_id)
                get_viewport().set_input_as_handled()
                return
            # First-contact family becomes the reusable topic family after a
            # source-backed exchange. This is runtime state only until the raw
            # condition/action tuples are semantically decoded.
            if family == "1A":
                # Retail has a 1B topic family, but canonical ATDEMO does not.
                # Advance only when the active source IR actually provides it.
                var next := _load_family("1B")
                if not next.is_empty():
                    family = "1B"
                    choices = next
            selected = clampi(selected,0,maxi(0,choices.size()-1))
            _refresh_choices()
        elif event.keycode == KEY_ESCAPE:
            _close()
    else:
        if event.keycode in [KEY_W,KEY_UP]:
            selected = posmod(selected-1,choices.size()); _refresh_choices()
        elif event.keycode in [KEY_S,KEY_DOWN]:
            selected = posmod(selected+1,choices.size()); _refresh_choices()
        elif event.is_action_pressed("interact") or event.keycode == KEY_ENTER:
            _show_response(choices[selected])
        elif event.keycode == KEY_ESCAPE:
            _close()
    get_viewport().set_input_as_handled()
