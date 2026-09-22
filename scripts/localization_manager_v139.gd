extends Node

signal locale_changed(locale: String)

const MANIFEST_PATH := "res://localization/languages.json"
const USER_CONFIG_PATH := "user://localization.cfg"

var manifest: Dictionary = {}
var locale_rows: Array[Dictionary] = []
var locale_by_code: Dictionary = {}
var pack_cache: Dictionary = {}
var current_locale := "en"
var fallback_locale := "en"

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    _load_manifest()
    var selected := String(manifest.get("default_locale", fallback_locale))
    var cfg := ConfigFile.new()
    if cfg.load(USER_CONFIG_PATH) == OK:
        selected = String(cfg.get_value("localization", "locale", selected))
    if not set_locale(selected, false):
        set_locale(fallback_locale, false)

func _read_json(path: String) -> Dictionary:
    if not FileAccess.file_exists(path):
        push_error("Localization: missing JSON " + path)
        return {}
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
    if not parsed is Dictionary:
        push_error("Localization: invalid JSON " + path)
        return {}
    return parsed

func _load_manifest() -> void:
    manifest = _read_json(MANIFEST_PATH)
    locale_rows.clear()
    locale_by_code.clear()
    fallback_locale = String(manifest.get("fallback_locale", "en"))
    for raw in manifest.get("locales", []):
        if not raw is Dictionary:
            continue
        var row: Dictionary = raw
        var code := String(row.get("code", "")).strip_edges()
        var file_path := String(row.get("file", "")).strip_edges()
        if code.is_empty() or file_path.is_empty():
            continue
        locale_rows.append(row.duplicate(true))
        locale_by_code[code] = row.duplicate(true)

func available_locales() -> Array[Dictionary]:
    var out: Array[Dictionary] = []
    for row in locale_rows:
        out.append(row.duplicate(true))
    return out

func has_locale(code: String) -> bool:
    return locale_by_code.has(code)

func _pack_path(code: String) -> String:
    if not locale_by_code.has(code):
        return ""
    var rel := String(locale_by_code[code].get("file", ""))
    return "res://" + rel.trim_prefix("res://")

func _load_pack(code: String) -> Dictionary:
    if pack_cache.has(code):
        return pack_cache[code]
    var path := _pack_path(code)
    if path.is_empty():
        return {}
    var pack := _read_json(path)
    if String(pack.get("schema", "")) != "openazrael.localization_pack":
        push_error("Localization: bad pack schema for " + code)
        return {}
    if String(pack.get("locale", "")) != code:
        push_error("Localization: locale mismatch for " + code)
        return {}
    var strings = pack.get("strings", {})
    if not strings is Dictionary:
        push_error("Localization: strings must be a dictionary for " + code)
        return {}
    pack_cache[code] = pack
    return pack

func set_locale(code: String, persist: bool = true) -> bool:
    if not has_locale(code):
        push_warning("Localization: unknown locale " + code)
        return false
    var pack := _load_pack(code)
    if pack.is_empty():
        return false
    # Always prime the fallback pack so missing strings are deterministic.
    if code != fallback_locale:
        _load_pack(fallback_locale)
    current_locale = code
    TranslationServer.set_locale(code)
    if persist:
        var cfg := ConfigFile.new()
        cfg.set_value("localization", "locale", code)
        cfg.save(USER_CONFIG_PATH)
    locale_changed.emit(code)
    return true

func locale_info(code: String = "") -> Dictionary:
    var target := current_locale if code.is_empty() else code
    return locale_by_code.get(target, {}).duplicate(true)

func tr_key(key: String, replacements: Dictionary = {}) -> String:
    var value := ""
    var current_pack := _load_pack(current_locale)
    var current_strings: Dictionary = current_pack.get("strings", {})
    if current_strings.has(key):
        value = String(current_strings[key])
    if value.is_empty() and current_locale != fallback_locale:
        var fallback_pack := _load_pack(fallback_locale)
        var fallback_strings: Dictionary = fallback_pack.get("strings", {})
        if fallback_strings.has(key):
            value = String(fallback_strings[key])
    if value.is_empty():
        value = key
    for name in replacements.keys():
        value = value.replace("{" + String(name) + "}", String(replacements[name]))
    return value

func has_translation(key: String, code: String = "") -> bool:
    var target := current_locale if code.is_empty() else code
    var pack := _load_pack(target)
    var strings: Dictionary = pack.get("strings", {})
    return strings.has(key) and not String(strings[key]).is_empty()
