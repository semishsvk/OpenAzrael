extends CanvasLayer
var backdrop: ColorRect
var image: TextureRect
var active := false
func _ready()->void:
    layer=90
    backdrop=ColorRect.new(); backdrop.color=Color.BLACK
    backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    backdrop.mouse_filter=Control.MOUSE_FILTER_STOP
    add_child(backdrop)
    image=TextureRect.new()
    image.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    image.expand_mode=TextureRect.EXPAND_IGNORE_SIZE
    image.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_CENTERED
    image.texture_filter=CanvasItem.TEXTURE_FILTER_NEAREST
    image.mouse_filter=Control.MOUSE_FILTER_STOP
    add_child(image)
    visible=false
func show_item(item_id:String)->bool:
    var path:=""
    if item_id=="parchment_r1": path="res://assets/ui/object_inspect/PARCHMENT_R1.png"
    elif item_id=="tapestry_piece_1": path="res://assets/ui/object_inspect/R3T1_0.png"
    elif item_id=="tapestry_piece_3": path="res://assets/ui/object_inspect/R8T3_0.png"
    elif item_id=="tapestry_piece_4": path="res://assets/ui/object_inspect/R8T4_0.png"
    else: return false
    var tex=load(path)
    if not tex is Texture2D: return false
    image.texture=tex; active=true; visible=true
    get_viewport().set_input_as_handled()
    return true
func dismiss()->void:
    active=false; visible=false; image.texture=null
func _unhandled_input(event:InputEvent)->void:
    if not active: return
    if event is InputEventMouseButton and event.pressed:
        dismiss(); get_viewport().set_input_as_handled()
    elif event is InputEventKey and event.pressed and not event.echo:
        if event.keycode in [KEY_E,KEY_ESCAPE,KEY_ENTER,KEY_SPACE]:
            dismiss(); get_viewport().set_input_as_handled()
