extends CanvasLayer
class_name LegacyMenuRuntimeV145

const LOGICAL_SIZE := Vector2(640, 480)
const SERVICE_ORIGIN := Vector2(235, 260)
const SaveSystem := preload("res://scripts/legacy_save_system_v145.gd")

const HUD_BUTTONS := {
    "SCAN": Rect2(235, 343, 83, 36),
    "MAP": Rect2(213, 381, 77, 42),
    "SERVICE": Rect2(363, 386, 90, 43),
}
# Evidence-constrained, non-overlapping label regions measured from SAVE13.PCX.
# Exact 1996 input hitboxes remain HOLD until original runtime capture proves them.
const SERVICE_ACTIONS := {
    "LOAD": Rect2(45, 24, 60, 25),
    "MUSIC": Rect2(112, 35, 44, 24),
    "QUIT": Rect2(70, 52, 38, 30),
    "SFX": Rect2(110, 66, 38, 31),
    "SAVE": Rect2(48, 91, 58, 26),
    "CONFIRM": Rect2(22, 124, 69, 22),
}
const SCAN_STATUS := [
    "Updating Environment Scan....",
    "Calculating Item Values....",
    "Updating Auto-Map Facility....",
    "Performing Penetrative Scan....",
    "Life Form Scan....",
    "Performing Surface Scan....",
]

@onready var room_manager = get_node("../RoomManager")
@onready var player = get_node("../Player")
@onready var probe = get_node("../Player/Camera3D/InteractionProbe")

var root_control: Control
var classic_canvas: Control
var hud_texture: TextureRect
var title_texture: TextureRect
var service_texture: TextureRect
var map_indicator: TextureRect
var status_label: Label
var slot_label: Label

var title_open := false
var service_open := false
var map_mode := false
var pending_action := ""
var selected_slot := 0
var volume_target := ""
var _scale := 1.0
var _offset := Vector2.ZERO

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    layer = 50
    _build()
    _reflow()
    if DisplayServer.get_name() != "headless":
        _show_title()
    else:
        title_open = false
        root_control.visible = false
    get_viewport().size_changed.connect(_reflow)

func _load_tex(stem: String) -> Texture2D:
    var path := "res://assets/ui/legacy_menu/" + stem + ".png"
    return load(path) as Texture2D if ResourceLoader.exists(path) else null

func _make_tex(name: String, stem: String, pos: Vector2, size: Vector2) -> TextureRect:
    var node := TextureRect.new()
    node.name = name
    node.position = pos
    node.size = size
    node.texture = _load_tex(stem)
    node.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
    node.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    node.stretch_mode = TextureRect.STRETCH_KEEP
    node.mouse_filter = Control.MOUSE_FILTER_IGNORE
    classic_canvas.add_child(node)
    return node

func _build() -> void:
    root_control = Control.new()
    root_control.name = "LegacyMenuRootV145"
    root_control.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    root_control.mouse_filter = Control.MOUSE_FILTER_IGNORE
    add_child(root_control)

    classic_canvas = Control.new()
    classic_canvas.name = "Classic640x480"
    classic_canvas.size = LOGICAL_SIZE
    classic_canvas.mouse_filter = Control.MOUSE_FILTER_IGNORE
    root_control.add_child(classic_canvas)

    hud_texture = _make_tex("HUD3", "HUD3", Vector2.ZERO, LOGICAL_SIZE)
    title_texture = _make_tex("Title1996", "TITLE", Vector2(4, 3), Vector2(631, 474))
    service_texture = _make_tex("ServiceMenu", "SAVE13", SERVICE_ORIGIN, Vector2(206, 170))
    map_indicator = _make_tex("MapIndicator", "MAPOFF", Vector2(0, 0), Vector2(639, 47))

    status_label = Label.new()
    status_label.name = "LegacyStatus"
    status_label.position = Vector2(17, 312)
    status_label.size = Vector2(600, 24)
    status_label.add_theme_font_size_override("font_size", 10)
    status_label.add_theme_color_override("font_color", Color(0.78, 0.78, 0.58, 1.0))
    status_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
    classic_canvas.add_child(status_label)

    slot_label = Label.new()
    slot_label.name = "LegacySaveSlots"
    slot_label.position = SERVICE_ORIGIN + Vector2(25, 35)
    slot_label.size = Vector2(95, 82)
    slot_label.add_theme_font_size_override("font_size", 9)
    slot_label.add_theme_color_override("font_color", Color(0.72, 0.66, 0.46, 1.0))
    slot_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
    classic_canvas.add_child(slot_label)

    service_texture.visible = false
    slot_label.visible = false
    map_indicator.visible = false

func _reflow() -> void:
    if classic_canvas == null:
        return
    var vp := get_viewport().get_visible_rect().size
    _scale = min(vp.x / LOGICAL_SIZE.x, vp.y / LOGICAL_SIZE.y)
    _offset = (vp - LOGICAL_SIZE * _scale) * 0.5
    classic_canvas.scale = Vector2(_scale, _scale)
    classic_canvas.position = _offset

func blocks_world_cursor() -> bool:
    return title_open or service_open

func _screen_to_classic(screen_pos: Vector2) -> Vector2:
    return (screen_pos - _offset) / maxf(_scale, 0.0001)

func _show_title() -> void:
    title_open = true
    title_texture.visible = true
    hud_texture.visible = false
    service_texture.visible = false
    slot_label.visible = false
    map_indicator.visible = false
    get_tree().paused = true
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func _dismiss_title() -> void:
    title_open = false
    title_texture.visible = false
    hud_texture.visible = true
    get_tree().paused = false
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
    CandidateDiagnostics.record_event("legacy_title_dismiss", {"compatibility_input": true})

func _set_service(opened: bool) -> void:
    service_open = opened
    service_texture.visible = opened
    slot_label.visible = opened and pending_action in ["LOAD", "SAVE"]
    if opened:
        get_tree().paused = true
        Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
        _refresh_slots()
    else:
        pending_action = ""
        volume_target = ""
        slot_label.visible = false
        get_tree().paused = false
        Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
    CandidateDiagnostics.record_event("legacy_service_menu", {"open": opened})

func _refresh_slots() -> void:
    var lines: Array[String] = []
    for i in range(SaveSystem.SLOT_NAMES.size()):
        var mark := "> " if i == selected_slot else "  "
        var exists := " *" if SaveSystem.slot_exists(i) else ""
        lines.append(mark + SaveSystem.slot_name(i) + exists)
    slot_label.text = "\n".join(lines)
    slot_label.visible = service_open and pending_action in ["LOAD", "SAVE"]

func _service_action_at(local: Vector2) -> String:
    var p := local - SERVICE_ORIGIN
    for action in SERVICE_ACTIONS:
        if SERVICE_ACTIONS[action].has_point(p):
            return String(action)
    if Rect2(20, 35, 100, 85).has_point(p) and pending_action in ["LOAD", "SAVE"]:
        var row := clampi(int((p.y - 35.0) / 16.0), 0, SaveSystem.SLOT_NAMES.size() - 1)
        selected_slot = row
        _refresh_slots()
        return "SLOT"
    return ""

func _scan() -> void:
    var target = probe.call("current_interactive") if probe != null and probe.has_method("current_interactive") else null
    status_label.text = SCAN_STATUS[5] if target == null else SCAN_STATUS[0] + " " + String(target.get("name"))
    CandidateDiagnostics.record_event("legacy_scan", {"target": "" if target == null else String(target.get("name"))})

func _toggle_map() -> void:
    map_mode = not map_mode
    map_indicator.texture = _load_tex("MAPON" if map_mode else "MAPOFF")
    map_indicator.visible = true
    status_label.text = "Updating Auto-Map Facility...."
    CandidateDiagnostics.record_event("legacy_map_toggle", {"active": map_mode, "renderer": "HOLD_SOURCE_MAP_RENDERER"})

func _music_bus() -> int:
    var idx := AudioServer.get_bus_index("Music")
    return idx if idx >= 0 else AudioServer.get_bus_index("Master")

func _sfx_bus() -> int:
    var idx := AudioServer.get_bus_index("SFX")
    return idx if idx >= 0 else AudioServer.get_bus_index("Master")

func _adjust_selected_volume(delta_steps: int) -> void:
    var bus := _music_bus() if volume_target == "MUSIC" else _sfx_bus()
    if bus < 0:
        return
    var current := AudioServer.get_bus_volume_db(bus)
    var next := clampf(current + float(delta_steps) * 2.0, -40.0, 0.0)
    AudioServer.set_bus_volume_db(bus, next)
    status_label.text = "%s %.1f dB" % [volume_target, next]
    CandidateDiagnostics.record_event("legacy_volume", {"target": volume_target, "db": next})

func _execute_confirm() -> void:
    match pending_action:
        "SAVE":
            var ok := SaveSystem.save_slot(selected_slot, room_manager, player)
            status_label.text = "Saving Game...." if ok else "SAVE FAILED"
            _refresh_slots()
        "LOAD":
            var ok := SaveSystem.load_slot(selected_slot, room_manager, player)
            status_label.text = "Loading Game...." if ok else "LOAD FAILED"
            if ok:
                _set_service(false)
        "QUIT":
            CandidateDiagnostics.record_event("legacy_quit_confirmed", {})
            get_tree().quit(0)
        _:
            status_label.text = ""
    pending_action = "" if pending_action == "QUIT" else pending_action

func _handle_service_action(action: String) -> void:
    match action:
        "LOAD", "SAVE", "QUIT":
            pending_action = action
            volume_target = ""
            _refresh_slots()
            status_label.text = action + " — CONFIRM"
        "MUSIC", "SFX":
            pending_action = ""
            volume_target = action
            slot_label.visible = false
            status_label.text = action + " — MOUSE WHEEL"
        "CONFIRM":
            _execute_confirm()
        "SLOT":
            pass

func _unhandled_input(event: InputEvent) -> void:
    if DisplayServer.get_name() == "headless":
        return

    if title_open:
        if (event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT) or (event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_ENTER):
            _dismiss_title()
            get_viewport().set_input_as_handled()
        return

    if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_M:
        _toggle_map()
        get_viewport().set_input_as_handled()
        return

    if service_open and event is InputEventMouseButton and event.pressed:
        var local := _screen_to_classic(event.position)
        if event.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN] and not volume_target.is_empty():
            _adjust_selected_volume(1 if event.button_index == MOUSE_BUTTON_WHEEL_UP else -1)
            get_viewport().set_input_as_handled()
            return
        if event.button_index == MOUSE_BUTTON_RIGHT:
            _set_service(false)
            get_viewport().set_input_as_handled()
            return
        if event.button_index == MOUSE_BUTTON_LEFT:
            var action := _service_action_at(local)
            if not action.is_empty():
                _handle_service_action(action)
                get_viewport().set_input_as_handled()
            return

    if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
        var local := _screen_to_classic(event.position)
        for action in HUD_BUTTONS:
            if HUD_BUTTONS[action].has_point(local):
                match String(action):
                    "SCAN": _scan()
                    "MAP": _toggle_map()
                    "SERVICE": _set_service(true)
                get_viewport().set_input_as_handled()
                return
