extends RefCounted

const EXPECTED_SCHEMA := "openazrael.texture_lab.runtime_texture_manifest.v1"
const ALLOWED_PREFIX := "res://assets/textures/"

var profile := ""
var status := ""
var runtime_ready := false
var _rows: Dictionary = {}

func load_manifest(path: String) -> bool:
    _rows.clear()
    profile = ""
    status = ""
    runtime_ready = false

    var absolute := ProjectSettings.globalize_path(path)
    if not FileAccess.file_exists(path) and not FileAccess.file_exists(absolute):
        return false

    var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
    if not parsed is Dictionary:
        return false
    if String(parsed.get("schema", "")) != EXPECTED_SCHEMA:
        return false
    if bool(parsed.get("automatic_promotion", true)):
        return false
    if not bool(parsed.get("runtime_ready", false)):
        return false

    var rows = parsed.get("textures", [])
    if not rows is Array:
        return false

    for raw in rows:
        if not raw is Dictionary:
            return false
        var texture_id := String(raw.get("id", ""))
        var texture_path := String(raw.get("path", ""))
        if texture_id.is_empty():
            return false
        if not _safe_texture_path(texture_path):
            return false
        if not _row_integrity_ok(raw):
            return false
        _rows[texture_id] = raw.duplicate(true)

    profile = String(parsed.get("profile", ""))
    status = String(parsed.get("status", ""))
    runtime_ready = bool(parsed.get("runtime_ready", false))
    return not profile.is_empty()

func _safe_texture_path(path: String) -> bool:
    if not path.begins_with(ALLOWED_PREFIX):
        return false
    if path.contains(".."):
        return false
    return path.ends_with(".png")

func _sha256_file(path: String) -> String:
    if not FileAccess.file_exists(path):
        return ""
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return ""
    var ctx := HashingContext.new()
    if ctx.start(HashingContext.HASH_SHA256) != OK:
        return ""
    const CHUNK_SIZE := 1024 * 1024
    while file.get_position() < file.get_length():
        var remaining := file.get_length() - file.get_position()
        ctx.update(file.get_buffer(min(CHUNK_SIZE, remaining)))
    return ctx.finish().hex_encode()

func _row_integrity_ok(row: Dictionary) -> bool:
    var path := String(row.get("path", ""))
    if not FileAccess.file_exists(path):
        return false
    var expected_sha := String(row.get("sha256", ""))
    var expected_size := int(row.get("size_bytes", -1))
    if expected_sha.is_empty() or expected_size < 0:
        return false
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null or file.get_length() != expected_size:
        return false
    return _sha256_file(path) == expected_sha

func has_texture(texture_id: String) -> bool:
    return _rows.has(texture_id)

func path_for(texture_id: String) -> String:
    if not _rows.has(texture_id):
        return ""
    return String((_rows[texture_id] as Dictionary).get("path", ""))

func tier_for(texture_id: String) -> String:
    if not _rows.has(texture_id):
        return ""
    return String((_rows[texture_id] as Dictionary).get("resolved_tier", ""))

func reason_for(texture_id: String) -> String:
    if not _rows.has(texture_id):
        return ""
    return String((_rows[texture_id] as Dictionary).get("resolution_reason", ""))

func file_present_for(texture_id: String) -> bool:
    if not _rows.has(texture_id):
        return false
    return bool((_rows[texture_id] as Dictionary).get("file_present", false))
