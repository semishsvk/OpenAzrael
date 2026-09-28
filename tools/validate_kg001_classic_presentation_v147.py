#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_classic_presentation_contract_v147.json").read_text(encoding="utf-8"))
menu=(ROOT/"scripts/legacy_menu_runtime_v145.gd").read_text(encoding="utf-8")
hud=(ROOT/"scripts/hud.gd").read_text(encoding="utf-8")
capture=(ROOT/"scripts/kg001_legacy_menu_graphical_capture_v147.gd").read_text(encoding="utf-8")
project=(ROOT/"main.tscn").read_text(encoding="utf-8")
checks={
 "schema":contract.get("schema")=="openazrael.kg001.classic_presentation_contract" and contract.get("version")==147,
 "logical_frame":"Vector2(640, 480)" in menu,
 "four_mattes":all(token in menu for token in ("ClassicMatteLeftV147","ClassicMatteRightV147","ClassicMatteTopV147","ClassicMatteBottomV147")),
 "black_matte":"node.color = Color.BLACK" in menu,
 "frame_rect":"func classic_frame_rect() -> Rect2:" in menu and "LOGICAL_SIZE * _scale" in menu,
 "widescreen_masking":all(token in menu for token in ("matte_left.size","matte_right.size","matte_top.size","matte_bottom.size")),
 "modern_overlay_hidden":"legacy_classic_mode_active" in hud and "legacy_overlay" in hud and ".visible = false" in hud,
 "debug_surfaces_retained":all(token in hud for token in ("KEY_F7","KEY_F8","KEY_F9","KEY_F10")),
 "legacy_scene_wired":'name="LegacyMenuV145"' in project,
 "capture_real_viewport":all(token in capture for token in ("get_viewport().get_texture().get_image()","RenderingServer.frame_post_draw","TITLE","HUD","SERVICE")),
 "capture_no_ai":"image_gen" not in capture.lower(),
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
 "schema":"openazrael.kg001.classic_presentation_validation",
 "version":147,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL",
 "runtime_status":"NOT_EXECUTED",
 "checks":checks,
 "failed":failed,
},indent=2))
sys.exit(1 if failed else 0)
