extends TextureRect
class_name LegacyHelpRuntimeV213
var menu: Node
var enabled := false
func _ready() -> void:
    position=Vector2.ZERO
    size=Vector2(640,480)
    texture=load("res://assets/ui/legacy_menu/HELP.png")
    texture_filter=CanvasItem.TEXTURE_FILTER_NEAREST
    mouse_filter=Control.MOUSE_FILTER_IGNORE
    expand_mode=TextureRect.EXPAND_IGNORE_SIZE
    stretch_mode=TextureRect.STRETCH_KEEP
    z_index=200
    visible=false
func _unhandled_key_input(event:InputEvent) -> void:
    if event is InputEventKey and event.pressed and not event.echo and event.keycode==KEY_H:
        if menu!=null and bool(menu.get("title_open")):return
        enabled=not enabled
        visible=enabled
        if menu!=null:menu.set("help_open",enabled)
        get_viewport().set_input_as_handled()
func _unhandled_input(event:InputEvent) -> void:
    if enabled and event is InputEventMouseButton:
        get_viewport().set_input_as_handled()
