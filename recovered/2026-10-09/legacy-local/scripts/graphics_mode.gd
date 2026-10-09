extends Node

enum GraphicsMode { CLASSIC, UPSCALED_4X, REMASTERED }
const ENHANCED := GraphicsMode.UPSCALED_4X

const MANIFEST_PATH := "res://data/texture_variant_manifest_v247.json"
var mode: int = GraphicsMode.CLASSIC
var _variant_map: Dictionary = {}
var _manifest_ok := false

func _ready() -> void:
    _load_manifest()

func _load_manifest() -> void:
    _variant_map.clear()
    _manifest_ok = false
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST_PATH))
    if not parsed is Dictionary:
        return
    if int(parsed.get("count", 0)) != 89 or not bool(parsed.get("all_pixel_preserving", false)):
        return
    for rec in parsed.get("textures", []):
        if rec is Dictionary and bool(rec.get("pixel_preserving", false)):
            _variant_map[String(rec.get("source", ""))] = String(rec.get("upscaled", ""))
    _manifest_ok = _variant_map.size() == 89

func mode_name() -> String:
    match mode:
        GraphicsMode.CLASSIC:
            return "CLASSIC"
        GraphicsMode.UPSCALED_4X:
            return "UPSCALED_4X"
        GraphicsMode.REMASTERED:
            return "REMASTERED_RESERVED"
    return "CLASSIC"

func set_mode(next_mode: int) -> void:
    if next_mode == GraphicsMode.UPSCALED_4X and _manifest_ok:
        mode = GraphicsMode.UPSCALED_4X
    else:
        mode = GraphicsMode.CLASSIC

func manifest_ok() -> bool:
    return _manifest_ok

func variant_count() -> int:
    return _variant_map.size()

func apply_to_room(room: Node) -> int:
    if room == null or mode != GraphicsMode.UPSCALED_4X or not _manifest_ok:
        return 0
    var changed := 0
    for node in room.find_children("*", "MeshInstance3D", true, false):
        var mesh_instance := node as MeshInstance3D
        if mesh_instance == null or mesh_instance.mesh == null:
            continue
        for surface in range(mesh_instance.mesh.get_surface_count()):
            var material := mesh_instance.get_active_material(surface) as StandardMaterial3D
            if material == null or material.albedo_texture == null:
                continue
            var replacement_path := String(_variant_map.get(material.albedo_texture.resource_path, ""))
            if replacement_path.is_empty() or not ResourceLoader.exists(replacement_path):
                continue
            var replacement := load(replacement_path) as Texture2D
            if replacement == null:
                continue
            var override := material.duplicate(true) as StandardMaterial3D
            override.albedo_texture = replacement
            mesh_instance.set_surface_override_material(surface, override)
            changed += 1
    return changed
