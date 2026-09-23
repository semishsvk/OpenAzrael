#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT = Path(__file__).resolve().parents[1]
contract = json.loads((ROOT / "data/tests/kg001_inventory_hud_contract_v157.json").read_text(encoding="utf-8"))
menu = (ROOT / "scripts/legacy_menu_runtime_v145.gd").read_text(encoding="utf-8")
state = (ROOT / "scripts/demo_state.gd").read_text(encoding="utf-8")
events = json.loads((ROOT / "data/gameplay_event_graph_v87.json").read_text(encoding="utf-8"))
runner = (ROOT / "scripts/kg001_inventory_hud_runner_v157.gd").read_text(encoding="utf-8")

checks = {
    "schema": contract.get("schema") == "openazrael.kg001.inventory_hud_contract" and contract.get("version") == 157,
    "pixel_exact_inventory_rect": 'Rect2(70, 345, 103, 69)' in menu,
    "source_of_truth": "DemoState.inventory" in menu and "inventory_changed" in menu,
    "no_parallel_inventory_state": "var inventory: Dictionary" not in menu,
    "demo_labels": all(token in menu for token in ('"Rusty tongs"', '"Well Key"', '"Lens"', '"Shield"')),
    "known_ids": all(token in menu for token in ('"rusty_tongs"', '"well_key"', '"r8_lens"', '"shield"')),
    "unknown_ids_not_rendered": "_inventory_unknown_ids" in menu and "INVENTORY_ITEM_LABELS.has" in menu,
    "scroll_keys": "KEY_UP" in menu and "KEY_DOWN" in menu and "_scroll_inventory" in menu,
    "font_hold_explicit": "COMPATIBILITY_FONT__INVFONT_GLYPH_MAP_HOLD" in menu,
    "canonical_state_inventory": "_canonical_pairs(inventory)" in state and "inventory_changed.emit()" in state,
    "lens_remove_event": any(a.get("op") == "remove_inventory" and a.get("key") == "r8_lens" for a in events["graphs"]["R8_LENS_PLACE"]["actions"]),
    "shield_add_event": any(a.get("op") == "add_inventory" and a.get("key") == "shield" for a in events["graphs"]["R8_TAKE_SHIELD"]["actions"]),
    "runtime_flow": all(token in runner for token in ("rusty_tongs", "R8_LENS_PLACE", "R8_TAKE_SHIELD", "save_slot", "load_slot", "unmapped_future_item")),
}
failed = [name for name, ok in checks.items() if not ok]
print(json.dumps({
    "schema": "openazrael.kg001.inventory_hud_source_validation",
    "version": 157,
    "status": "SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "runtime_status": "NOT_EXECUTED",
    "checks": checks,
    "failed": failed,
}, indent=2))
sys.exit(1 if failed else 0)
