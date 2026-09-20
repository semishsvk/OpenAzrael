extends RefCounted

const ALLOWED_PREFIX := "res://assets/textures/"

static func safe_texture_path(path: String) -> bool:
    return (
        path.begins_with(ALLOWED_PREFIX)
        and not path.contains("..")
        and path.ends_with(".png")
    )

static func load_texture(path: String) -> Texture2D:
    if not safe_texture_path(path):
        return null
    var resource := ResourceLoader.load(path)
    if resource is Texture2D:
        return resource as Texture2D
    return null
