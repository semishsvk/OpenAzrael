extends Node3D

const SELECTION_PATH := "res://tools/texture_lab/config/rt_poc_01_selection.json"
const TIER_NAMES := ["CLASSIC", "ENHANCED", "AI RESTORED", "AI RECREATED"]
const ENHANCED_METHODS := ["nearest", "bicubic", "lanczos"]
const TILE_REPEATS := [1, 2, 4]

@onready var surface: MeshInstance3D = $Surface
@onready var light: DirectionalLight3D = $DirectionalLight3D
@onready var label: Label = $HUD/Panel/Margin/Label

var entries: Array = []
var texture_index := 0
var tier_index := 0
var enhanced_method_index := 2
var tile_index := 0
var lit := false
var material := StandardMaterial3D.new()
var current_path := ""
var current_status := ""

func _ready() -> void:
    material.roughness = 0.85
    material.metallic = 0.0
    surface.material_override = material
    _load_selection()
    _refresh()

func _load_selection() -> void:
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(SELECTION_PATH))
    if not parsed is Dictionary or not parsed.has("textures"):
        push_error("Texture Lab: invalid selection file")
        return
    entries = parsed["textures"]

func _path_for_entry(entry: Dictionary) -> String:
    var id := String(entry["id"])
    match tier_index:
        0:
            return "res://assets/textures/classic/%s.png" % id
        1:
            var method := ENHANCED_METHODS[enhanced_method_index]
            return "res://assets/textures/enhanced/%s/%s_x4.png" % [id, method]
        2:
            return "res://assets/textures/ai_restored/%s/realesrgan_x4.png" % id
        3:
            return "res://assets/textures/ai_recreated/%s/selected.png" % id
    return ""

func _load_image(path: String) -> Image:
    var absolute := ProjectSettings.globalize_path(path)
    if not FileAccess.file_exists(path) and not FileAccess.file_exists(absolute):
        return null
    var image := Image.load_from_file(absolute)
    if image == null or image.is_empty():
        return null
    return image

func _tiled_image(source: Image, repeat: int) -> Image:
    if repeat <= 1:
        return source
    var result := Image.create(
        source.get_width() * repeat,
        source.get_height() * repeat,
        false,
        source.get_format()
    )
    var rect := Rect2i(Vector2i.ZERO, source.get_size())
    for y in range(repeat):
        for x in range(repeat):
            result.blit_rect(
                source,
                rect,
                Vector2i(x * source.get_width(), y * source.get_height())
            )
    return result

func _fit_surface(image: Image) -> void:
    var quad := surface.mesh as QuadMesh
    if quad == null:
        return
    var aspect := float(image.get_width()) / max(1.0, float(image.get_height()))
    var extent := 3.4
    if aspect >= 1.0:
        quad.size = Vector2(extent, extent / aspect)
    else:
        quad.size = Vector2(extent * aspect, extent)

func _refresh() -> void:
    if entries.is_empty():
        current_status = "NO SELECTION"
        _update_label()
        return

    texture_index = wrapi(texture_index, 0, entries.size())
    var entry: Dictionary = entries[texture_index]
    current_path = _path_for_entry(entry)
    var image := _load_image(current_path)

    if image == null:
        current_status = "MISSING"
        material.albedo_texture = null
        material.albedo_color = Color(0.12, 0.02, 0.12, 1.0)
    else:
        current_status = "OK"
        var repeat: int = TILE_REPEATS[tile_index]
        var display_image := _tiled_image(image, repeat)
        material.albedo_color = Color.WHITE
        material.albedo_texture = ImageTexture.create_from_image(display_image)
        _fit_surface(display_image)

    material.shading_mode = (
        BaseMaterial3D.SHADING_MODE_PER_PIXEL
        if lit
        else BaseMaterial3D.SHADING_MODE_UNSHADED
    )
    light.visible = lit
    _update_label()

func _update_label() -> void:
    if entries.is_empty():
        label.text = "OpenAzrael Texture Lab — no selection loaded"
        return
    var entry: Dictionary = entries[texture_index]
    var method := ENHANCED_METHODS[enhanced_method_index] if tier_index == 1 else "-"
    label.text = (
        "OpenAzrael Texture Lab  |  %d/%d  %s\n"
        + "Tier: %s  |  Enhanced: %s  |  Tile: %dx%d  |  Lighting: %s  |  %s\n"
        + "Path: %s\n"
        + "←/→ texture   1 Classic   2 Enhanced   3 AI Restored   4 AI Recreated\n"
        + "Q/W/E nearest/bicubic/lanczos   T tile 1/2/4   L lighting   S screenshot"
    ) % [
        texture_index + 1,
        entries.size(),
        String(entry["id"]),
        TIER_NAMES[tier_index],
        method,
        TILE_REPEATS[tile_index],
        TILE_REPEATS[tile_index],
        "LIT" if lit else "UNSHADED",
        current_status,
        current_path
    ]

func _save_screenshot() -> void:
    var image := get_viewport().get_texture().get_image()
    var id := String(entries[texture_index]["id"]).replace("#", "_")
    var tier := TIER_NAMES[tier_index].to_lower().replace(" ", "_")
    var path := "user://texture_lab_%s_%s.png" % [id, tier]
    var err := image.save_png(path)
    if err == OK:
        print("Texture Lab screenshot: ", path)
    else:
        push_error("Texture Lab screenshot failed: %s" % err)

func _unhandled_key_input(event: InputEvent) -> void:
    if not event.pressed or event.echo:
        return
    match event.keycode:
        KEY_LEFT:
            texture_index -= 1
        KEY_RIGHT:
            texture_index += 1
        KEY_1:
            tier_index = 0
        KEY_2:
            tier_index = 1
        KEY_3:
            tier_index = 2
        KEY_4:
            tier_index = 3
        KEY_Q:
            enhanced_method_index = 0
            tier_index = 1
        KEY_W:
            enhanced_method_index = 1
            tier_index = 1
        KEY_E:
            enhanced_method_index = 2
            tier_index = 1
        KEY_T:
            tile_index = (tile_index + 1) % TILE_REPEATS.size()
        KEY_L:
            lit = not lit
        KEY_S:
            _save_screenshot()
        _:
            return
    _refresh()
