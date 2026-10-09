from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/"scripts/player.gd"
s=p.read_text(encoding="utf-8")
s=s.replace('var hud_cursor_active := false','''var hud_cursor_active := false
# Compatibility profile is an approximation until original input mapping is verified.
var control_profile := "modern"
var sniper_active := false
const SNIPER_SCALE := 0.5
''',1)
s=s.replace('camera.set_frustum(viewport_size.y / frame_scale / 345.0, Vector2(0.0, -50.0 / 345.0), 1.0, 30000.0)','camera.set_frustum(viewport_size.y / frame_scale / 345.0 * (SNIPER_SCALE if sniper_active else 1.0), Vector2(0.0, -50.0 / 345.0), 1.0, 30000.0)',1)
needle='    if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_TAB:'
assert needle in s
s=s.replace(needle,'''    if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F6:
        control_profile = "classic_compat" if control_profile == "modern" else "modern"
        CandidateDiagnostics.record_event("control_profile", {"profile":control_profile, "authority":"COMPATIBILITY_NOT_ORIGINAL_VERIFIED"})
        get_viewport().set_input_as_handled()
        return
    if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F:
        sniper_active = not sniper_active
        _apply_source_projection()
        CandidateDiagnostics.record_event("sniper_mode", {"active":sniper_active, "projection":"PROVISIONAL_ZOOM_NOT_ORIGINAL_VERIFIED"})
        get_viewport().set_input_as_handled()
        return
'''+needle,1)
needle='    var input2 := Input.get_vector("move_left", "move_right", "move_forward", "move_back")'
assert needle in s
s=s.replace(needle,'''    var input2 := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
    if control_profile == "classic_compat":
        input2 = Vector2(
            float(Input.is_key_pressed(KEY_RIGHT)) - float(Input.is_key_pressed(KEY_LEFT)),
            float(Input.is_key_pressed(KEY_DOWN)) - float(Input.is_key_pressed(KEY_UP))
        )''',1)
p.write_text(s,encoding="utf-8")
print("DUAL_CONTROL_PATCH_APPLIED")
