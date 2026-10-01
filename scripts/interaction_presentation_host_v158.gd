extends CanvasLayer
## Source-gated interaction presentation host.
## v158 deliberately renders nothing unless a presentation entry has a bound source asset.

signal presentation_opened(presentation_id: String)
signal presentation_closed(presentation_id: String)

var _active_id := ""
var _active_control: Control

func is_open() -> bool:
    return not _active_id.is_empty()

func active_id() -> String:
    return _active_id

func open_source_texture(presentation_id: String, texture: Texture2D) -> bool:
    if presentation_id.is_empty() or texture == null or is_open():
        return false
    var rect := TextureRect.new()
    rect.name = "SourcePresentation"
    rect.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
    rect.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
    rect.texture = texture
    rect.mouse_filter = Control.MOUSE_FILTER_STOP
    add_child(rect)
    _active_control = rect
    _active_id = presentation_id
    presentation_opened.emit(_active_id)
    return true

func close() -> bool:
    if not is_open():
        return false
    var closed_id := _active_id
    _active_id = ""
    if is_instance_valid(_active_control):
        _active_control.queue_free()
    _active_control = null
    presentation_closed.emit(closed_id)
    return true
