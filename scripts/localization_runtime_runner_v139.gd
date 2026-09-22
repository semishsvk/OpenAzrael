extends SceneTree

var failures: Array[String] = []

func _initialize() -> void:
    call_deferred("_run")

func _check(name: String, ok: bool) -> void:
    if not ok:
        failures.append(name)

func _run() -> void:
    await process_frame
    var manager = root.get_node_or_null("LocalizationManager")
    _check("autoload_exists", manager != null)
    if manager == null:
        print("OPENAZRAEL_LOCALIZATION_V139 " + JSON.stringify({
            "schema":"openazrael.localization_runtime",
            "version":139,
            "status":"FAIL",
            "failures":failures
        }))
        quit(1)
        return

    var original := String(manager.current_locale)
    var rows: Array = manager.available_locales()
    var codes: Array[String] = []
    for row in rows:
        codes.append(String(row.get("code", "")))
    _check("en_available", "en" in codes)
    _check("sk_available", "sk" in codes)
    _check("fallback_en", String(manager.fallback_locale) == "en")

    _check("set_sk", manager.set_locale("sk", false))
    _check("sk_title", manager.tr_key("ui.menu.title") == "Nastavenia")
    _check("sk_controls", manager.tr_key("ui.hud.controls").begins_with("WASD pohyb"))
    # Slovak deliberately omits the source dialogue entry: fallback must be
    # deterministic and return the exact English source string.
    _check("fallback_dialogue", manager.tr_key("dialog.demo.niamh.0001") == "Good Lord. What are you?")

    _check("set_en", manager.set_locale("en", false))
    _check("en_title", manager.tr_key("ui.menu.title") == "Options")
    _check("missing_key_identity", manager.tr_key("missing.contract.key") == "missing.contract.key")
    _check("reject_unknown_locale", not manager.set_locale("xx-NOT-A-REAL-LOCALE", false))

    if manager.has_locale(original):
        manager.set_locale(original, false)

    var status := "PASS" if failures.is_empty() else "FAIL"
    print("OPENAZRAEL_LOCALIZATION_V139 " + JSON.stringify({
        "schema":"openazrael.localization_runtime",
        "version":139,
        "status":status,
        "available_locales":codes,
        "fallback_locale":String(manager.fallback_locale),
        "failures":failures
    }))
    quit(0 if failures.is_empty() else 1)
