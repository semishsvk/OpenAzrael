#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/"data/ui/legacy_menu_manifest_v144.json").read_text(encoding="utf-8"))
contract=json.loads((ROOT/"data/tests/menu_lab_contract_v144.json").read_text(encoding="utf-8"))
restore=(ROOT/"tools/restore_legacy_menu_v144.py").read_text(encoding="utf-8")
assets=manifest.get("assets",[])
cats={a.get("category") for a in assets}
checks={
 "schema":manifest.get("schema")=="openazrael.menu_lab.source_manifest" and manifest.get("version")==144,
 "contract":contract.get("schema")=="openazrael.menu_lab.contract" and contract.get("version")==144,
 "title_exact":any(a.get("file")=="TITLE.PCX" and a.get("width")==631 and a.get("height")==474 for a in assets),
 "hud_exact":all(any(a.get("file")==name and a.get("width")==640 and a.get("height")==480 for a in assets) for name in ("HUD3.PCX","HUDOFF.PCX")),
 "six_hud_button_states":sum(1 for a in assets if a.get("category")=="hud_button")==6,
 "eight_replay_frames":sum(1 for a in assets if a.get("category")=="replay_animation")==8,
 "fourteen_save_previews":sum(1 for a in assets if a.get("category")=="save_preview")==14,
 "font_strips":sum(1 for a in assets if a.get("category")=="font_strip")==3,
 "required_categories":set(contract.get("required_asset_categories",[])).issubset(cats),
 "fingerprints":all(len(str(a.get("sha256","")))==64 and int(a.get("bytes",0))>0 for a in assets),
 "restore_no_resample":"resize(" not in restore and "thumbnail(" not in restore,
 "restore_rgb_only_hold":"HOLD_OPAQUE_RGB_SOURCE_PIXELS_ONLY" in restore,
 "no_guessed_menu":any("No guessed New Game" in s for s in manifest.get("unresolved",[])) is False and "No invented menu option" in manifest.get("policy",""),
 "readme_roles":all(any(token in s for s in manifest.get("proven_behaviour",[])) for token in ("top-left HUD button scans","button below scan toggles map","right-hand HUD button brings up")),
 "runtime_boundary":"forensic/source inventory only" in contract.get("runtime_boundary","").lower(),
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.menu_lab.validation","version":144,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
