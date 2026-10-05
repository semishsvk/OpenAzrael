extends TextureRect
class_name LegacyHealthHudV217
var player: Node
var menu: Node
var contract: Dictionary
var rendered_health := -1
var source_image: Image
func _ready() -> void:
    contract = JSON.parse_string(FileAccess.get_file_as_string("res://data/ui/legacy_health_hud_v217.json"))
    position = Vector2(320,357)
    size = Vector2(105,15)
    texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
    mouse_filter = Control.MOUSE_FILTER_IGNORE
    expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    stretch_mode = TextureRect.STRETCH_KEEP
    _refresh()
func image_for_health(health: int) -> Image:
    var image := Image.create(105,15,false,Image.FORMAT_RGB8)
    var palette: Array = contract["palette_rgb6_expanded"]
    var empty: Array = contract["bitmaps"]["empty"]["pixels"]
    var filled: Array = contract["bitmaps"]["filled"]["pixels"]
    var last_x := int(clampi(health,0,1000)*104/1000)
    for y in range(15):
        for x in range(105):
            var index := int(empty[y*105+x])
            var active := int(filled[y*105+x])
            if x <= last_x and active != 0: index = active
            var rgb: Array = palette[index]
            image.set_pixel(x,y,Color8(int(rgb[0]),int(rgb[1]),int(rgb[2])))
    return image
func _refresh() -> void:
    var health := int(player.call("legacy_health_value"))
    if health == rendered_health: return
    rendered_health = health
    source_image = image_for_health(health)
    texture = ImageTexture.create_from_image(source_image)
func _process(_delta: float) -> void:
    visible = menu != null and not bool(menu.get("title_open"))
    if player == null or menu == null: return
    if not bool(menu.call("blocks_world_cursor")):
        player.call("advance_legacy_health_poll")
    _refresh()
