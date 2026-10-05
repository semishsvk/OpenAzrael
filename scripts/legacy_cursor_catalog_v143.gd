extends RefCounted
class_name LegacyCursorCatalogV143

const ROOT := "res://assets/ui/mice/"
const FALLBACK := "POINTER"
const DISPLAY_SIZE := Vector2(30.0, 30.0)
const ACTIVE_IDS := {
    "POINTER": true,
    "TAKE": true,
    "USE": true,
    "PULL": true,
    "ROT": true,
    "CANT": true,
}

static func normalize_id(cursor_id: String) -> String:
    var value := cursor_id.strip_edges().to_upper()
    return value if ACTIVE_IDS.has(value) else FALLBACK

static func texture_path(cursor_id: String) -> String:
    return ROOT + normalize_id(cursor_id) + ".png"

static func load_texture(cursor_id: String) -> Texture2D:
    var path := texture_path(cursor_id)
    if not ResourceLoader.exists(path):
        return null
    return load(path) as Texture2D
