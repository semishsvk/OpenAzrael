extends TextureRect
class_name LegacyCompassRuntimeV204

const SOURCE_PATH := "res://data/tests/kg001_canonical_compass_v204.json"
var camera: Camera3D
var source: Dictionary = {}
var shade := PackedByteArray()
var _last_heading := -1
var _image_texture: ImageTexture

func _ready() -> void:
    source = JSON.parse_string(FileAccess.get_file_as_string(SOURCE_PATH))
    shade = Marshalls.base64_to_raw(source["shade_base64"])
    position = Vector2(146, 15)
    size = Vector2(348, 24)
    texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
    mouse_filter = Control.MOUSE_FILTER_IGNORE
    expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    stretch_mode = TextureRect.STRETCH_KEEP
    _refresh()

func heading_degrees() -> int:
    if camera == null:
        return 0
    var forward := -camera.global_basis.z
    return wrapi(roundi(rad_to_deg(atan2(forward.x, forward.z))), 0, 360)

func indexed_frame(heading: int) -> PackedByteArray:
    var pixels := PackedByteArray()
    pixels.resize(348 * 24)
    pixels.fill(0)
    for tick in range(24):
        var x := wrapi(2 * (tick * 15 - heading) + 174, 0, 720)
        for character in String(source["labels"][tick]):
            var glyph: Dictionary = source["glyphs"][character]
            var width := int(glyph["width"])
            for y in range(int(glyph["height"])):
                for dx in range(width):
                    if x + dx >= 0 and x + dx < 348:
                        pixels[(y + 2) * 348 + x + dx] = int(glyph["pixels"][y * width + dx])
            x += int(glyph["advance"])
    for y in range(24):
        for x in range(348):
            pixels[y * 348 + x] &= int(shade[y * 348 + x])
    return pixels

func _refresh() -> void:
    if source.is_empty():
        return
    var heading := heading_degrees()
    if heading == _last_heading:
        return
    _last_heading = heading
    var indexed := indexed_frame(heading)
    var rgba := PackedByteArray()
    rgba.resize(indexed.size() * 4)
    rgba.fill(0)
    for i in range(indexed.size()):
        if indexed[i] == 0:
            continue
        var rgb: Array = source["indexed_palette_rgb"][str(indexed[i])]
        for channel in range(3):
            rgba[i * 4 + channel] = int(rgb[channel])
        rgba[i * 4 + 3] = 255
    var image := Image.create_from_data(348, 24, false, Image.FORMAT_RGBA8, rgba)
    if _image_texture == null:
        _image_texture = ImageTexture.create_from_image(image)
        texture = _image_texture
    else:
        _image_texture.update(image)

func _process(_delta: float) -> void:
    _refresh()
