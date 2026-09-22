#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_legacy_menu_toggle_contract_v149.json").read_text(encoding="utf-8"))
menu=(ROOT/"scripts/legacy_menu_runtime_v145.gd").read_text(encoding="utf-8")
runner=(ROOT/"scripts/kg001_legacy_menu_toggle_runner_v149.gd").read_text(encoding="utf-8")

checks={
 "schema":contract.get("schema")=="openazrael.kg001.legacy_menu_toggle_contract" and contract.get("version")==149,
 "source_open_sequence":all(token in menu for token in ('"SAVE00"','"SAVE01"','"SAVE02"','"SAVE03"','"SAVE04"','"SAVE05"','"SAVE06"')),
 "base_frame":"SERVICE_BASE_FRAME := \"SAVE06\"" in menu,
 "hover_frames":all(token in menu for token in ('"SAVE": "SAVE07"','"LOAD": "SAVE08"','"MUSIC": "SAVE09"','"SFX": "SAVE10"','"QUIT": "SAVE11"')),
 "confirm_frames":all(token in menu for token in ('"SAVE": "SAVE12"','"LOAD": "SAVE13"')),
 "same_button_toggle":"func _toggle_service() -> void:" in menu and "_set_service(not service_open)" in menu,
 "hud_service_uses_toggle":'"SERVICE":\n            _toggle_service()' in menu,
 "open_menu_same_hotspot_closes":'HUD_BUTTONS["SERVICE"].has_point(local)' in menu and "_toggle_service()" in menu,
 "rmb_not_close":'if event.button_index == MOUSE_BUTTON_RIGHT:\n            _set_service(false)' not in menu,
 "mouse_hover_visual":"InputEventMouseMotion" in menu and "_update_service_visual" in menu,
 "exact_timing_hold":"Exact 1996 frame timing remains HOLD" in menu,
 "runtime_marker":"OPENAZRAEL_KG001_MENU_TOGGLE_V149" in runner,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
 "schema":"openazrael.kg001.legacy_menu_toggle_validation",
 "version":149,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL",
 "runtime_status":"NOT_EXECUTED",
 "checks":checks,
 "failed":failed,
},indent=2))
sys.exit(1 if failed else 0)
