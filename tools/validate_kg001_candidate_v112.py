#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/"tools/run_kg001_candidate_v112.py").read_text(encoding="utf-8")
manifest=(ROOT/"tools/kg001_gate_manifest.py").read_text(encoding="utf-8")
combined=source+"\n"+manifest
checks={
 "tmp_evidence":'ROOT/".tmp/kg001"' in source,
 "godot_discovery":all(x in source for x in ("GODOT_BIN","godot4","godot")),
 "source_validators":all(x in manifest for x in ("validate_public_release_safety.py","validate_project_context.py","validate_demo_runtime_ir.py","kg001_state_space_v108.py","validate_kg001_full_demo_v111.py")),
 "godot_import_step":'"--import"' in source and "import_status" in source,
 "deterministic_runtime_fixed_fps":'"--fixed-fps","60"' in source,
 "shutdown_resource_leak_filter":'resources still in use at exit' in source and 're.fullmatch' in source,
 "runtime_v109":"kg001_headless_runner_v109.gd" in manifest,
 "runtime_v110":"kg001_room_trigger_runner_v110.gd" in manifest,
 "runtime_v111":"kg001_full_demo_runner_v111.gd" in manifest,
 "runtime_audio_v116":"kg001_audio_runtime_runner_v116.gd" in manifest and "OPENAZRAEL_KG001_AUDIO_V116" in manifest,
 "runtime_physical_v117":"kg001_physical_traversal_runner_v117.gd" in manifest and "OPENAZRAEL_KG001_PHYSICAL_V117" in manifest,
 "runtime_well_tongs_v118":"kg001_well_tongs_animation_runner_v118.gd" in manifest and "OPENAZRAEL_KG001_WELL_TONGS_V118" in manifest,
 "runtime_r1_route_v119":"kg001_r1_route_runner_v119.gd" in manifest and "OPENAZRAEL_KG001_R1_ROUTE_V119" in manifest,
 "runtime_collision_v120":"kg001_collision_parity_runner_v120.gd" in manifest and "OPENAZRAEL_KG001_COLLISION_PARITY_V120" in manifest,
 "source_audio_validator":"validate_kg001_audio_runtime_v116.py" in manifest,
 "source_physical_validator":"validate_kg001_physical_traversal_v117.py" in manifest,
 "source_well_tongs_validator":"validate_kg001_well_tongs_animation_v118.py" in manifest,
 "source_r1_route_validator":"validate_kg001_r1_route_v119.py" in manifest,
 "source_collision_parity_validator":"validate_kg001_collision_parity_v120.py" in manifest,
 "source_inventory_hud_validator":"validate_kg001_inventory_hud_v157.py" in manifest,
 "runtime_inventory_hud_v157":"kg001_inventory_hud_runner_v157.gd" in manifest and "OPENAZRAEL_KG001_INVENTORY_HUD_V157" in manifest,
 "source_texture_colorkey_validator":"validate_kg001_texture_colorkey_v116.py" in manifest,
 "git_clean_before_after":"clean_before=git_clean()" in source and "clean_after=git_clean()" in source,
 "forbidden_tracking_check":"repository_safety()" in source and "FORBIDDEN_TRACKED_PREFIXES" in source,
 "asset_ignore_check":'"check-ignore"' in source,
 "fresh_requires_import":'import_status=="PASS"' in source,
 "fresh_requires_all_runtime":"full_runtime_pass" in source and "all(asset_present.values())" in source,
 "promotion_is_optional":"--promote-results" in source,
 "promotion_covers_all_transition_v141":'kg001_all_transitions_v141_runtime.json' in source and 'kg001_all_transition_traversal_runtime_v141.json' in source,
 "promotion_covers_interaction_probe_v148":'kg001_interaction_probe_v148_runtime.json' in source and 'kg001_interaction_probe_determinism_runtime_v148.json' in source,
 "promotion_covers_save_v150":'kg001_save_compat_v150_runtime.json' in source and 'kg001_save_compat_runtime_v150.json' in source,
 "promotion_covers_inventory_hud_v157":'kg001_inventory_hud_v157_runtime.json' in source and 'kg001_inventory_hud_runtime_v157.json' in source,
 "fresh_is_optional":"--fresh-checkout" in source,
 "source_only_mode":"--source-only" in source and "openazrael.kg001.source_gate" in source,
 "canonical_manifest_import":'from tools.kg001_gate_manifest import SOURCE_COMMANDS, RUNTIMES' in source,
 "candidate3_guard_validator":"validate_candidate3_preflight.py" in manifest,
 "public_release_safety_validator":"validate_public_release_safety.py" in manifest,
}
failed=[k for k,v in checks.items() if not v]
print("OpenAzrael v112 candidate runner source contract:","PASS" if not failed else "FAIL")
for name,value in checks.items(): print(f" - {name}: {'PASS' if value else 'FAIL'}")
sys.exit(1 if failed else 0)
