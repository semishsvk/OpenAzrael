#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/"data/ui/legacy_cursor_manifest_v143.json").read_text(encoding="utf-8"))
contract=json.loads((ROOT/"data/tests/kg001_interaction_cursor_contract_v143.json").read_text(encoding="utf-8"))
restore=(ROOT/"tools/restore_legacy_cursors_v143.py").read_text(encoding="utf-8")
probe=(ROOT/"scripts/interaction_probe.gd").read_text(encoding="utf-8")
hud=(ROOT/"scripts/hud.gd").read_text(encoding="utf-8")
runner=(ROOT/"scripts/kg001_interaction_cursor_runner_v143.gd").read_text(encoding="utf-8")
scripts={
 "pickup":(ROOT/"scripts/pickup.gd").read_text(encoding="utf-8"),
 "well_key":(ROOT/"scripts/well_key_interaction.gd").read_text(encoding="utf-8"),
 "r7_switch":(ROOT/"scripts/r7_switch_control.gd").read_text(encoding="utf-8"),
 "r1_door":(ROOT/"scripts/r1_door_interaction.gd").read_text(encoding="utf-8"),
 "r8_lens":(ROOT/"scripts/r8_lens_interaction.gd").read_text(encoding="utf-8"),
 "r8_bible":(ROOT/"scripts/r8_bible_interaction.gd").read_text(encoding="utf-8"),
 "r8_tapestry":(ROOT/"scripts/r8_tapestry_interaction.gd").read_text(encoding="utf-8"),
 "r8_shield":(ROOT/"scripts/r8_shield_interaction.gd").read_text(encoding="utf-8"),
 "r8_frame":(ROOT/"scripts/r8_tapestry_frame.gd").read_text(encoding="utf-8"),
}
names=list(manifest.get("files",{}))
checks={
 "schema":manifest.get("schema")=="openazrael.legacy_cursor_manifest" and manifest.get("version")==143,
 "contract":contract.get("schema")=="openazrael.kg001.interaction_cursor_contract" and contract.get("version")==143,
 "exact_source_count":len(names)==35 and len(set(names))==35 and manifest.get("source_file_count")==35,
 "core_source_icons":all(name in names for name in ("POINTER.PCX","TAKE.PCX","USE.PCX","PULL.PCX","ROT.PCX","CANT.PCX")),
 "all_fingerprints":all(len(str(spec[0]))==64 and int(spec[1])>0 for spec in manifest["files"].values()),
 "indexed_alpha_only":all(token in restore for token in ('indexed.mode!="P"','int(v)==0 else 255','rgba.putalpha(alpha)')),
 "no_resampling":"resize(" not in restore and "thumbnail(" not in restore,
 "b_variants_hold":manifest.get("b_variant_semantics")=="HOLD_UNRESOLVED",
 "probe_dynamic_cursor":all(token in probe for token in ("current_cursor_id","interaction_cursor_id","POINTER","USE")),
 "hud_source_art":all(token in hud for token in ("LegacyCursorCatalogV143","InteractionCursorV143","TEXTURE_FILTER_NEAREST","current_cursor_id")),
 "all_interactables_mapped":all("interaction_cursor_id" in text for text in scripts.values()),
 "semantic_take":'"TAKE"' in scripts["pickup"] and '"TAKE"' in scripts["r8_lens"] and '"TAKE"' in scripts["r8_shield"],
 "semantic_tongs":'"CANT"' in scripts["well_key"] and '"USE"' in scripts["well_key"],
 "semantic_controls":'"PULL"' in scripts["r7_switch"] and '"ROT"' in scripts["r7_switch"],
 "semantic_tapestry":'"ROT"' in scripts["r8_tapestry"],
 "blocked_state_cant":all('"CANT"' in scripts[k] for k in ("well_key","r1_door","r8_lens","r8_bible","r8_shield","r8_frame")),
 "runtime_runner":"OPENAZRAEL_KG001_CURSOR_V143" in runner and "source_cursor_count" in runner,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.interaction_cursor_contract_validation","version":143,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","runtime_status":"NOT_EXECUTED","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
