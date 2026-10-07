#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_legacy_menu_runtime_contract_v145.json").read_text(encoding="utf-8"))
menu=(ROOT/"scripts/legacy_menu_runtime_v145.gd").read_text(encoding="utf-8")
save=(ROOT/"scripts/legacy_save_system_v145.gd").read_text(encoding="utf-8")
main=(ROOT/"main.tscn").read_text(encoding="utf-8")
project=(ROOT/"project.godot").read_text(encoding="utf-8")
checks={
 "schema":contract.get("schema")=="openazrael.kg001.legacy_menu_runtime_contract" and contract.get("version")==145,
 "logical_640x480":"Vector2(640, 480)" in menu,
 "exact_hud_rects":all(token in menu for token in ("Rect2(235, 343, 83, 36)","Rect2(213, 381, 77, 42)","Rect2(363, 386, 90, 43)")),
 "hud_roles":all(token in menu for token in ('"SCAN"','"MAP"','"SERVICE"')),
 "service_source_art":'"SAVE13"' in menu and "SERVICE_ORIGIN" in menu,
 "service_actions":all(token in menu for token in ('"LOAD"','"SAVE"','"MUSIC"','"SFX"','"QUIT"','"CONFIRM"')),
 "five_source_slots":all(token in save for token in ("FILE ALPHA","FILE BETA","FILE GAMMA","FILE DELTA","FILE EPSILON")),
 "source_filename_pattern":'"user://SAVE%d.dat"' in save,
 "state_roundtrip":"canonical_state_payload" in save and "restore_canonical_state_payload" in save,
 "room_pose_roundtrip":all(token in save for token in ("current_room_id","player_position","player_yaw","player_pitch","load_room")),
 "confirm_actions":'"SAVE":' in menu and '"LOAD":' in menu and '"QUIT":' in menu and "_execute_confirm" in menu,
 "volume_controls":"AudioServer.set_bus_volume_db" in menu and '"MUSIC"' in menu and '"SFX"' in menu,
 "scan_context":"current_interactive" in menu and "legacy_scan" in menu,
 "map_key":"KEY_M" in menu and "legacy_map_toggle" in menu,
 "headless_safe":'DisplayServer.get_name() == "headless"' in menu,
 "main_scene_wired":"legacy_menu_runtime_v145.gd" in main and 'name="LegacyMenuV145"' in main,
 "mouse_source_mode":all(token in (ROOT/"scripts/hud.gd").read_text(encoding="utf-8") for token in ("get_viewport().get_mouse_position()","Input.mouse_mode == Input.MOUSE_MODE_VISIBLE")),
 "mouse_ray_context":"project_ray_normal" in (ROOT/"scripts/interaction_probe.gd").read_text(encoding="utf-8"),
 "no_ai":"image_gen" not in menu.lower() and "generated menu" not in menu.lower(),
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.legacy_menu_runtime_validation","version":145,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","runtime_status":"NOT_EXECUTED","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
