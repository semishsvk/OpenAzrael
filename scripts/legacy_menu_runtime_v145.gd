extends CanvasLayer
class_name LegacyMenuRuntimeV145

const LOGICAL_SIZE := Vector2(640, 480)
const SERVICE_ORIGIN := Vector2(235, 260)
const SaveSystem := preload("res://scripts/legacy_save_system_v145.gd")
const LegacyScannerRuntimeV164 := preload("res://scripts/legacy_scanner_runtime_v164.gd")

# Source-derived service-menu frame semantics.
# SAVE00..SAVE06 are the closed->open construction sequence.
# Exact 1996 frame timing remains HOLD; runtime uses the proven stable states.
const SERVICE_OPEN_SEQUENCE := ["SAVE00", "SAVE01", "SAVE02", "SAVE03", "SAVE04", "SAVE05", "SAVE06"]
const SERVICE_CLOSE_SEQUENCE := ["SAVE06", "SAVE05", "SAVE04", "SAVE03", "SAVE02", "SAVE01", "SAVE00"]
const SERVICE_BASE_FRAME := "SAVE06"
const SERVICE_HOVER_FRAMES := {
    "SAVE": "SAVE07",
    "LOAD": "SAVE08",
    "MUSIC": "SAVE09",
    "SFX": "SAVE10",
    "QUIT": "SAVE11",
}
const SERVICE_CONFIRM_FRAMES := {
    "SAVE": "SAVE12",
    "LOAD": "SAVE13",
}

const HUD_BUTTONS := {
    "SCAN": Rect2(235, 343, 83, 36),
    "MAP": Rect2(213, 381, 77, 42),
    "SERVICE": Rect2(363, 386, 90, 43),
}

# Pixel-exact occurrence of INVBACK2.PCX inside HUD3.PCX from the official demo.
# The background is already baked into HUD3, so runtime renders only the item text.
const INVENTORY_RECT := Rect2(70, 345, 103, 69)
const INVENTORY_TEXT_ORIGIN := Vector2(70, 349)
const INVENTORY_VISIBLE_ROWS := 5
const INVENTORY_FONT_CELL_SIZE := Vector2(10, 12)
const INVENTORY_FONT_FIRST_CODEPOINT := 35
const INVENTORY_FONT_CELL_COUNT := 138
const INVENTORY_SPACE_ADVANCE := 3.0
const INVENTORY_ITEM_ORDER := ["rusty_tongs", "well_key", "r8_lens", "shield"]
const INVENTORY_ITEM_LABELS := {
    "rusty_tongs": "Rusty tongs",
    "well_key": "Key",
    "r8_lens": "Lens",
    "shield": "Shield",
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
var matte_left: ColorRect
var matte_right: ColorRect
var matte_top: ColorRect
var matte_bottom: ColorRect
var hud_texture: TextureRect
var title_texture: TextureRect
var service_texture: TextureRect
var map_indicator: TextureRect
var status_label: Label
var slot_label: Label
var inventory_text_layer: Control
var scanner_runtime: LegacyScannerRuntimeV164

var title_open := false
var service_open := false
var map_mode := false
var pending_action := ""
var selected_slot := 0
var volume_target := ""
var inventory_scroll := 0
var _scale := 1.0
var _offset := Vector2.ZERO

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    layer = 50
    _build()
    var inventory_callback := Callable(self, "_on_inventory_changed")
    if not DemoState.is_connected("inventory_changed", inventory_callback):
        DemoState.connect("inventory_changed", inventory_callback)
    _refresh_inventory()
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

func _make_matte(name: String) -> ColorRect:
    var node := ColorRect.new()
    node.name = name
    node.color = Color.BLACK
    node.mouse_filter = Control.MOUSE_FILTER_IGNORE
    node.z_index = -100
    root_control.add_child(node)
    return node

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

    matte_left = _make_matte("ClassicMatteLeftV147")
    matte_right = _make_matte("ClassicMatteRightV147")
    matte_top = _make_matte("ClassicMatteTopV147")
    matte_bottom = _make_matte("ClassicMatteBottomV147")

    classic_canvas = Control.new()
    classic_canvas.name = "Classic640x480"
    classic_canvas.size = LOGICAL_SIZE
    classic_canvas.mouse_filter = Control.MOUSE_FILTER_IGNORE
    root_control.add_child(classic_canvas)

    hud_texture = _make_tex("HUD3", "HUD3", Vector2.ZERO, LOGICAL_SIZE)
    title_texture = _make_tex("Title1996", "TITLE", Vector2(4, 3), Vector2(631, 474))
    service_texture = _make_tex("ServiceMenu", SERVICE_BASE_FRAME, SERVICE_ORIGIN, Vector2(206, 170))
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

    inventory_text_layer = Control.new()
    inventory_text_layer.name = "LegacyInventoryItemsV157"
    inventory_text_layer.position = INVENTORY_TEXT_ORIGIN
    inventory_text_layer.size = Vector2(INVENTORY_RECT.size.x, INVENTORY_FONT_CELL_SIZE.y * INVENTORY_VISIBLE_ROWS)
    inventory_text_layer.clip_contents = true
    inventory_text_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
    classic_canvas.add_child(inventory_text_layer)

    scanner_runtime = LegacyScannerRuntimeV164.new()
    classic_canvas.add_child(scanner_runtime)
    scanner_runtime.initialize(room_manager)

    service_texture.visible = false
    slot_label.visible = false
    map_indicator.visible = false

func _inventory_item_ids() -> Array[String]:
    var out: Array[String] = []
    for item_id in INVENTORY_ITEM_ORDER:
        if DemoState.has(String(item_id)):
            out.append(String(item_id))
    return out

func _inventory_unknown_ids() -> Array[String]:
    var out: Array[String] = []
    for raw_id in DemoState.inventory.keys():
        var item_id := String(raw_id)
        if bool(DemoState.inventory.get(raw_id, false)) and not INVENTORY_ITEM_LABELS.has(item_id):
            out.append(item_id)
    out.sort()
    return out

func _inventory_labels() -> Array[String]:
    var out: Array[String] = []
    for item_id in _inventory_item_ids():
        out.append(String(INVENTORY_ITEM_LABELS[item_id]))
    return out

func _inventory_font_texture() -> Texture2D:
    return _load_tex("INVFONT")

func _inventory_glyph_codepoint(character: String) -> int:
    if character.is_empty():
        return -1
    return character.unicode_at(0)

func _inventory_draw_line(text: String, row: int) -> void:
    var atlas := _inventory_font_texture()
    if atlas == null:
        return
    var x := 0.0
    for character in text:
        if character == " ":
            x += INVENTORY_SPACE_ADVANCE
            continue
        var codepoint := _inventory_glyph_codepoint(character)
        var cell := codepoint - INVENTORY_FONT_FIRST_CODEPOINT
        if cell < 0 or cell >= INVENTORY_FONT_CELL_COUNT:
            cell = 63 - INVENTORY_FONT_FIRST_CODEPOINT
        if x + INVENTORY_FONT_CELL_SIZE.x > INVENTORY_RECT.size.x:
            break
        var region := AtlasTexture.new()
        region.atlas = atlas
        region.region = Rect2(float(cell) * INVENTORY_FONT_CELL_SIZE.x, 0.0, INVENTORY_FONT_CELL_SIZE.x, INVENTORY_FONT_CELL_SIZE.y)
        var glyph := TextureRect.new()
        glyph.texture = region
        glyph.position = Vector2(x, float(row) * INVENTORY_FONT_CELL_SIZE.y)
        glyph.size = INVENTORY_FONT_CELL_SIZE
        glyph.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
        glyph.stretch_mode = TextureRect.STRETCH_KEEP
        glyph.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
        glyph.mouse_filter = Control.MOUSE_FILTER_IGNORE
        inventory_text_layer.add_child(glyph)
        x += INVENTORY_FONT_CELL_SIZE.x

func _refresh_inventory() -> void:
    if inventory_text_layer == null:
        return
    for child in inventory_text_layer.get_children():
        inventory_text_layer.remove_child(child)
        child.queue_free()
    var items := _inventory_labels()
    var max_scroll := maxi(items.size() - INVENTORY_VISIBLE_ROWS, 0)
    inventory_scroll = clampi(inventory_scroll, 0, max_scroll)
    var end := mini(inventory_scroll + INVENTORY_VISIBLE_ROWS, items.size())
    var row := 0
    for i in range(inventory_scroll, end):
        _inventory_draw_line(items[i], row)
        row += 1
    inventory_text_layer.visible = not title_open

func _on_inventory_changed() -> void:
    _refresh_inventory()
    CandidateDiagnostics.record_event("legacy_inventory_changed", {
        "items": _inventory_item_ids(),
        "scroll": inventory_scroll,
        "unknown_ids": _inventory_unknown_ids(),
    })

func _scroll_inventory(delta_rows: int) -> bool:
    var items := _inventory_labels()
    var max_scroll := maxi(items.size() - INVENTORY_VISIBLE_ROWS, 0)
    var before := inventory_scroll
    inventory_scroll = clampi(inventory_scroll + delta_rows, 0, max_scroll)
    _refresh_inventory()
    if inventory_scroll != before:
        CandidateDiagnostics.record_event("legacy_inventory_scroll", {
            "scroll": inventory_scroll,
            "max_scroll": max_scroll,
        })
        return true
    return false

func debug_inventory_snapshot() -> Dictionary:
    var labels := _inventory_labels()
    var visible: Array[String] = []
    var end := mini(inventory_scroll + INVENTORY_VISIBLE_ROWS, labels.size())
    for i in range(inventory_scroll, end):
        visible.append(labels[i])
    return {
        "rect": [INVENTORY_RECT.position.x, INVENTORY_RECT.position.y, INVENTORY_RECT.size.x, INVENTORY_RECT.size.y],
        "text_origin": [INVENTORY_TEXT_ORIGIN.x, INVENTORY_TEXT_ORIGIN.y],
        "font_cell": [INVENTORY_FONT_CELL_SIZE.x, INVENTORY_FONT_CELL_SIZE.y],
        "font_first_codepoint": INVENTORY_FONT_FIRST_CODEPOINT,
        "font_cell_count": INVENTORY_FONT_CELL_COUNT,
        "visible_rows": INVENTORY_VISIBLE_ROWS,
        "item_ids": _inventory_item_ids(),
        "labels": labels,
        "visible_labels": visible,
        "scroll": inventory_scroll,
        "unknown_ids": _inventory_unknown_ids(),
        "glyph_node_count": inventory_text_layer.get_child_count() if inventory_text_layer != null else 0,
        "font_fidelity": "SOURCE_INVFONT_FIXED_CELL_MAP",
    }

func _reflow() -> void:
    if classic_canvas == null:
        return
    var vp := get_viewport().get_visible_rect().size
    _scale = min(vp.x / LOGICAL_SIZE.x, vp.y / LOGICAL_SIZE.y)
    _offset = (vp - LOGICAL_SIZE * _scale) * 0.5
    classic_canvas.scale = Vector2(_scale, _scale)
    classic_canvas.position = _offset

    var framed := LOGICAL_SIZE * _scale
    matte_left.position = Vector2.ZERO
    matte_left.size = Vector2(maxf(_offset.x, 0.0), vp.y)
    matte_right.position = Vector2(_offset.x + framed.x, 0.0)
    matte_right.size = Vector2(maxf(vp.x - (_offset.x + framed.x), 0.0), vp.y)
    matte_top.position = Vector2(0.0, 0.0)
    matte_top.size = Vector2(vp.x, maxf(_offset.y, 0.0))
    matte_bottom.position = Vector2(0.0, _offset.y + framed.y)
    matte_bottom.size = Vector2(vp.x, maxf(vp.y - (_offset.y + framed.y), 0.0))

func classic_frame_rect() -> Rect2:
    return Rect2(_offset, LOGICAL_SIZE * _scale)

func blocks_world_cursor() -> bool:
    return title_open or service_open

func debug_scanner_snapshot() -> Dictionary:
    return scanner_runtime.debug_snapshot() if scanner_runtime != null else {}

func _screen_to_classic(screen_pos: Vector2) -> Vector2:
    return (screen_pos - _offset) / maxf(_scale, 0.0001)

func _show_title() -> void:
    title_open = true
    title_texture.visible = true
    hud_texture.visible = false
    service_texture.visible = false
    slot_label.visible = false
    map_indicator.visible = false
    inventory_text_layer.visible = false
    get_tree().paused = true
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func _dismiss_title() -> void:
    title_open = false
    title_texture.visible = false
    hud_texture.visible = true
    inventory_text_layer.visible = true
    _refresh_inventory()
    get_tree().paused = false
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
    if scanner_runtime != null:
        scanner_runtime.start_boot_sequence()
    CandidateDiagnostics.record_event("legacy_title_dismiss", {"compatibility_input": true})

func _set_service_frame(stem: String) -> void:
    var texture := _load_tex(stem)
    if texture != null:
        service_texture.texture = texture

func _service_visual_frame(local: Vector2) -> String:
    if SERVICE_CONFIRM_FRAMES.has(pending_action):
        return String(SERVICE_CONFIRM_FRAMES[pending_action])
    if pending_action == "QUIT":
        return "SAVE11"
    if not volume_target.is_empty() and SERVICE_HOVER_FRAMES.has(volume_target):
        return String(SERVICE_HOVER_FRAMES[volume_target])
    var action := _service_action_at(local)
    if SERVICE_HOVER_FRAMES.has(action):
        return String(SERVICE_HOVER_FRAMES[action])
    return SERVICE_BASE_FRAME

func _update_service_visual(local: Vector2) -> void:
    if not service_open:
        return
    _set_service_frame(_service_visual_frame(local))

func _toggle_service() -> void:
    _set_service(not service_open)

func _activate_hud_action(action: String) -> void:
    match action:
        "SCAN":
            _scan()
        "MAP":
            _toggle_map()
        "SERVICE":
            _toggle_service()

func _set_service(opened: bool) -> void:
    service_open = opened
    service_texture.visible = opened
    slot_label.visible = opened and pending_action in ["LOAD", "SAVE"]
    if opened:
        _set_service_frame(SERVICE_BASE_FRAME)
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

    if not service_open and event is InputEventKey and event.pressed and not event.echo and event.keycode in [KEY_UP, KEY_DOWN]:
        # README assigns cursor keys to movement and inventory scrolling.
        # Scroll without consuming the event so movement semantics are preserved.
        _scroll_inventory(-1 if event.keycode == KEY_UP else 1)

    if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_M:
        _toggle_map()
        get_viewport().set_input_as_handled()
        return

    if service_open and event is InputEventMouseMotion:
        _update_service_visual(_screen_to_classic(event.position))

    if service_open and event is InputEventMouseButton and event.pressed:
        var local := _screen_to_classic(event.position)
        if event.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN] and not volume_target.is_empty():
            _adjust_selected_volume(1 if event.button_index == MOUSE_BUTTON_WHEEL_UP else -1)
            get_viewport().set_input_as_handled()
            return
        if event.button_index == MOUSE_BUTTON_LEFT:
            # The original OPTIONS control is the service-menu toggle.
            # When the panel is open the same HUD hotspot remains the close control.
            if HUD_BUTTONS["SERVICE"].has_point(local):
                _toggle_service()
                get_viewport().set_input_as_handled()
                return
            var action := _service_action_at(local)
            if not action.is_empty():
                _handle_service_action(action)
                _update_service_visual(local)
                get_viewport().set_input_as_handled()
            return

    if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
        var local := _screen_to_classic(event.position)
        for action in HUD_BUTTONS:
            if HUD_BUTTONS[action].has_point(local):
                _activate_hud_action(String(action))
                get_viewport().set_input_as_handled()
                return
