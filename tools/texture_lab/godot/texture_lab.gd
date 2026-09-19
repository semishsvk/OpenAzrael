extends Node3D

const SELECTION_PATH := "res://tools/texture_lab/config/rt_poc_01_selection.json"
const TIER_NAMES := ["CLASSIC", "ENHANCED", "AI RESTORED", "AI RECREATED"]
const ENHANCED_METHODS := ["nearest", "bicubic", "lanczos"]
const TILE_REPEATS := [1, 2, 4]

@onready var surface_a: MeshInstance3D = $Surface
@onready var surface_b: MeshInstance3D = $SurfaceB
@onready var light: DirectionalLight3D = $DirectionalLight3D
@onready var label: Label = $HUD/Panel/Margin/Label

var entries: Array = []
var texture_index := 0
var tier_index := 0
var reference_tier_index := 0
var enhanced_method_index := 2
var tile_index := 0
var lit := false
var compare_mode := false

var material_a := StandardMaterial3D.new()
var material_b := StandardMaterial3D.new()

var current_path := ""
var current_status := ""
var reference_path := ""
var reference_status := ""

func _ready() -> void:
    _configure_material(material_a)
    _configure_material(material_b)
    surface_a.material_override = material_a
    surface_b.material_override = material_b
    _load_selection()
    _refresh()

func _configure_material(target: StandardMaterial3D) -> void:
    target.roughness = 0.85
    target.metallic = 0.0

func _load_selection() -> void:
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(SELECTION_PATH))
    if not parsed is Dictionary or not parsed.has("textures"):
        push_error("Texture Lab: invalid selection file")
        return
    entries = parsed["textures"]

func _path_for_entry(entry: Dictionary, tier: int) -> String:
    var id := String(entry["id"])
    match tier:
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

func _fit_surface(target: MeshInstance3D, image: Image, extent: float) -> void:
    var quad := target.mesh as QuadMesh
    if quad == null:
        return
    var aspect := float(image.get_width()) / max(1.0, float(image.get_height()))
    if aspect >= 1.0:
        quad.size = Vector2(extent, extent / aspect)
    else:
        quad.size = Vector2(extent * aspect, extent)

func _apply_surface(
    target: MeshInstance3D,
    target_material: StandardMaterial3D,
    path: String,
    repeat: int,
    extent: float
) -> String:
    var image := _load_image(path)
    if image == null:
        target_material.albedo_texture = null
        target_material.albedo_color = Color(0.12, 0.02, 0.12, 1.0)
        var quad := target.mesh as QuadMesh
        if quad != null:
            quad.size = Vector2(extent, extent)
        return "MISSING"

    var display_image := _tiled_image(image, repeat)
    target_material.albedo_color = Color.WHITE
    target_material.albedo_texture = ImageTexture.create_from_image(display_image)
    _fit_surface(target, display_image, extent)
    return "OK"

func _apply_lighting() -> void:
    var mode := (
        BaseMaterial3D.SHADING_MODE_PER_PIXEL
        if lit
        else BaseMaterial3D.SHADING_MODE_UNSHADED
    )
    material_a.shading_mode = mode
    material_b.shading_mode = mode
    light.visible = lit

func _refresh() -> void:
    if entries.is_empty():
        current_status = "NO SELECTION"
        reference_status = "NO SELECTION"
        _update_label()
        return

    texture_index = wrapi(texture_index, 0, entries.size())
    tier_index = wrapi(tier_index, 0, TIER_NAMES.size())
    reference_tier_index = wrapi(reference_tier_index, 0, TIER_NAMES.size())

    var entry: Dictionary = entries[texture_index]
    var repeat: int = TILE_REPEATS[tile_index]
    current_path = _path_for_entry(entry, tier_index)

    if compare_mode:
        reference_path = _path_for_entry(entry, reference_tier_index)
        surface_a.visible = true
        surface_b.visible = true
        surface_a.position = Vector3(-1.7, 0.0, 0.0)
        surface_b.position = Vector3(1.7, 0.0, 0.0)
        reference_status = _apply_surface(
            surface_a,
            material_a,
            reference_path,
            repeat,
            2.65
        )
        current_status = _apply_surface(
            surface_b,
            material_b,
            current_path,
            repeat,
            2.65
        )
    else:
        reference_path = ""
        reference_status = ""
        surface_a.visible = true
        surface_b.visible = false
        surface_a.position = Vector3.ZERO
        current_status = _apply_surface(
            surface_a,
            material_a,
            current_path,
            repeat,
            3.4
        )

    _apply_lighting()
    _update_label()

func _update_label() -> void:
    if entries.is_empty():
        label.text = "OpenAzrael Texture Lab — no selection loaded"
        return

    var entry: Dictionary = entries[texture_index]
    var method := ENHANCED_METHODS[enhanced_method_index]
    var tile_text := "%dx%d" % [TILE_REPEATS[tile_index], TILE_REPEATS[tile_index]]
    var lighting_text := "LIT" if lit else "UNSHADED"

    if compare_mode:
        label.text = (
            "OpenAzrael Texture Lab  |  %d/%d  %s\n"
            + "A/B: ON  |  Reference: %s [%s]  |  Candidate: %s [%s]\n"
            + "Enhanced: %s  |  Tile: %s  |  Lighting: %s\n"
            + "A: %s\n"
            + "B: %s\n"
            + "←/→ texture   1/2/3/4 candidate tier   R reference tier   B A/B toggle\n"
            + "Q/W/E nearest/bicubic/lanczos   T tile 1/2/4   L lighting   S screenshot"
        ) % [
            texture_index + 1,
            entries.size(),
            String(entry["id"]),
            TIER_NAMES[reference_tier_index],
            reference_status,
            TIER_NAMES[tier_index],
            current_status,
            method,
            tile_text,
            lighting_text,
            reference_path,
            current_path
        ]
    else:
        var active_method := method if tier_index == 1 else "-"
        label.text = (
            "OpenAzrael Texture Lab  |  %d/%d  %s\n"
            + "Tier: %s  |  Enhanced: %s  |  Tile: %s  |  Lighting: %s  |  %s\n"
            + "Path: %s\n"
            + "←/→ texture   1 Classic   2 Enhanced   3 AI Restored   4 AI Recreated\n"
            + "B A/B compare   R cycle reference   Q/W/E nearest/bicubic/lanczos\n"
            + "T tile 1/2/4   L lighting   S screenshot"
        ) % [
            texture_index + 1,
            entries.size(),
            String(entry["id"]),
            TIER_NAMES[tier_index],
            active_method,
            tile_text,
            lighting_text,
            current_status,
            current_path
        ]

func _save_screenshot() -> void:
    var image := get_viewport().get_texture().get_image()
    var id := String(entries[texture_index]["id"]).replace("#", "_")
    var tier := TIER_NAMES[tier_index].to_lower().replace(" ", "_")
    var path := ""
    if compare_mode:
        var reference := TIER_NAMES[reference_tier_index].to_lower().replace(" ", "_")
        path = "user://texture_lab_%s_ab_%s_vs_%s.png" % [id, reference, tier]
    else:
        path = "user://texture_lab_%s_%s.png" % [id, tier]
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
        KEY_B:
            compare_mode = not compare_mode
        KEY_R:
            reference_tier_index = (reference_tier_index + 1) % TIER_NAMES.size()
        KEY_S:
            _save_screenshot()
        _:
            return
    _refresh()
