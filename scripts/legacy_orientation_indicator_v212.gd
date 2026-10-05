extends TextureRect
class_name LegacyOrientationIndicatorV212
const SOURCE_PATH := "res://data/tests/kg001_original_orientation_indicator_v212.json"
var player: Node
var menu: Node
var enabled := true
var source: Dictionary = {}
var _last_angle := 9999
var _image_texture: ImageTexture
func _ready() -> void:
    source = JSON.parse_string(FileAccess.get_file_as_string(SOURCE_PATH))
    position = Vector2(44,49)
    size = Vector2(52,168)
    texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
    mouse_filter = Control.MOUSE_FILTER_IGNORE
    expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    stretch_mode = TextureRect.STRETCH_KEEP
    _refresh()
func angle_degrees() -> int:
    return roundi(rad_to_deg(float(player.get("pitch")))) if player != null else 0
func _line(pixels: PackedByteArray, x1:int,y1:int,x2:int,y2:int,index:int) -> void:
    for y in range(mini(y1,y2),maxi(y1,y2)+1):
        for x in range(mini(x1,x2),maxi(x1,x2)+1):
            if x>=0 and x<52 and y>=0 and y<168:
                pixels[y*52+x]=index
func indexed_frame(angle:int) -> PackedByteArray:
    var pixels := PackedByteArray()
    pixels.resize(52*168)
    pixels.fill(0)
    _line(pixels,15,105,15,165,56)
    for line in [[14,104,14,166],[16,104,16,166],[15,104,15,104],[15,166,15,166]]:
        _line(pixels,line[0],line[1],line[2],line[3],54)
    var y := 135 - int(float(angle)/2.0)
    _line(pixels,4,y,26,y,56)
    _line(pixels,3,y-1,27,y-1,54)
    _line(pixels,3,y+1,27,y+1,54)
    _line(pixels,3,y,3,y,54)
    _line(pixels,27,y,27,y,54)
    var x := 29
    for character in str(angle):
        var glyph: Dictionary = source["glyphs"][character]
        for gy in range(int(glyph["height"])):
            for gx in range(int(glyph["width"])):
                var value := int(glyph["pixels"][gy*int(glyph["width"])+gx])
                if value != 0 and x+gx<52:
                    pixels[(gy+130)*52+x+gx]=value
        x += int(glyph["advance"])
    return pixels
func _refresh() -> void:
    if source.is_empty():return
    var angle := angle_degrees()
    if angle == _last_angle:return
    _last_angle=angle
    var indexed := indexed_frame(angle)
    var rgba := PackedByteArray()
    rgba.resize(indexed.size()*4)
    rgba.fill(0)
    for i in range(indexed.size()):
        if indexed[i]==0:continue
        var rgb: Array = source["indexed_palette_rgb"][str(indexed[i])]
        for channel in range(3):rgba[i*4+channel]=int(rgb[channel])
        rgba[i*4+3]=255
    var image := Image.create_from_data(52,168,false,Image.FORMAT_RGBA8,rgba)
    if _image_texture==null:
        _image_texture=ImageTexture.create_from_image(image)
        texture=_image_texture
    else:_image_texture.update(image)
func _process(_delta:float) -> void:
    visible=enabled and (menu==null or not bool(menu.get("title_open")))
    _refresh()
func _unhandled_key_input(event:InputEvent) -> void:
    if event is InputEventKey and event.pressed and not event.echo and event.keycode==KEY_Y:
        enabled=not enabled
        get_viewport().set_input_as_handled()
