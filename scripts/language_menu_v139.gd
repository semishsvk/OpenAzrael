extends CanvasLayer

var root_overlay: Control
var panel: PanelContainer
var title_label: Label
var language_label: Label
var language_select: OptionButton
var close_button: Button
var locale_codes: Array[String] = []
var opened := false

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    add_to_group("language_menu")
    _build_ui()
    LocalizationManager.locale_changed.connect(_on_locale_changed)
    _refresh_text()
    _refresh_locales()
    root_overlay.visible = false

func _build_ui() -> void:
    root_overlay = Control.new()
    root_overlay.name = "LocalizationMenuOverlay"
    root_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    root_overlay.mouse_filter = Control.MOUSE_FILTER_STOP
    add_child(root_overlay)

    var dim := ColorRect.new()
    dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    dim.color = Color(0, 0, 0, 0.55)
    root_overlay.add_child(dim)

    panel = PanelContainer.new()
    panel.name = "LocalizationMenuPanel"
    panel.set_anchors_preset(Control.PRESET_CENTER)
    panel.position = Vector2(-210, -110)
    panel.custom_minimum_size = Vector2(420, 220)
    root_overlay.add_child(panel)

    var margin := MarginContainer.new()
    margin.add_theme_constant_override("margin_left", 24)
    margin.add_theme_constant_override("margin_right", 24)
    margin.add_theme_constant_override("margin_top", 20)
    margin.add_theme_constant_override("margin_bottom", 20)
    panel.add_child(margin)

    var box := VBoxContainer.new()
    box.add_theme_constant_override("separation", 14)
    margin.add_child(box)

    title_label = Label.new()
    title_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    title_label.add_theme_font_size_override("font_size", 24)
    box.add_child(title_label)

    language_label = Label.new()
    box.add_child(language_label)

    language_select = OptionButton.new()
    language_select.item_selected.connect(_on_language_selected)
    box.add_child(language_select)

    close_button = Button.new()
    close_button.pressed.connect(close_menu)
    box.add_child(close_button)

func _refresh_text() -> void:
    if title_label == null:
        return
    title_label.text = LocalizationManager.tr_key("ui.menu.title")
    language_label.text = LocalizationManager.tr_key("ui.menu.language")
    close_button.text = LocalizationManager.tr_key("ui.menu.close")
    var info := LocalizationManager.locale_info()
    var direction := String(info.get("direction", "ltr")).to_lower()
    root_overlay.layout_direction = Control.LAYOUT_DIRECTION_RTL if direction == "rtl" else Control.LAYOUT_DIRECTION_LTR

func _refresh_locales() -> void:
    if language_select == null:
        return
    language_select.clear()
    locale_codes.clear()
    var selected := 0
    var rows := LocalizationManager.available_locales()
    for i in range(rows.size()):
        var row: Dictionary = rows[i]
        var code := String(row.get("code", ""))
        var native_name := String(row.get("native_name", code))
        locale_codes.append(code)
        language_select.add_item(native_name)
        language_select.set_item_metadata(i, code)
        if code == LocalizationManager.current_locale:
            selected = i
    if language_select.item_count > 0:
        language_select.select(selected)

func _on_language_selected(index: int) -> void:
    if index < 0 or index >= locale_codes.size():
        return
    if LocalizationManager.set_locale(locale_codes[index]):
        _refresh_text()
        _refresh_locales()

func _on_locale_changed(_locale: String) -> void:
    _refresh_text()
    _refresh_locales()

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventKey and event.pressed and not event.echo and ((event.keycode == KEY_ESCAPE and opened) or event.keycode == KEY_F2):
        toggle_menu()
        get_viewport().set_input_as_handled()

func toggle_menu() -> void:
    if opened:
        close_menu()
    else:
        open_menu()

func open_menu() -> void:
    opened = true
    root_overlay.visible = true
    get_node("../Player").sync_pointer_mode()
    _refresh_text()
    _refresh_locales()

func close_menu() -> void:
    opened = false
    root_overlay.visible = false
    get_node("../Player").sync_pointer_mode()

func is_open() -> bool:
    return opened
