#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/"tools/run_kg001_candidate_v112.py").read_text(encoding="utf-8")
checks={
 "tmp_evidence":'ROOT/".tmp/kg001"' in source,
 "godot_discovery":all(x in source for x in ("GODOT_BIN","godot4","godot")),
 "source_validators":all(x in source for x in ("validate_project_context.py","validate_demo_runtime_ir.py","kg001_state_space_v108.py","validate_kg001_full_demo_v111.py")),
 "godot_import_step":'"--import"' in source and "import_status" in source,
 "runtime_v109":"kg001_headless_runner_v109.gd" in source,
 "runtime_v110":"kg001_room_trigger_runner_v110.gd" in source,
 "runtime_v111":"kg001_full_demo_runner_v111.gd" in source,
 "runtime_audio_v116":"kg001_audio_runtime_runner_v116.gd" in source and "OPENAZRAEL_KG001_AUDIO_V116" in source,
 "source_audio_validator":"validate_kg001_audio_runtime_v116.py" in source,
 "source_texture_colorkey_validator":"validate_kg001_texture_colorkey_v116.py" in source,
 "source_toolchain_validator":"validate_kg001_toolchain_v117.py" in source,
 "source_export_validator":"validate_kg001_export_preset_v117.py" in source,
 "source_visual_capture_validator":"validate_kg001_visual_capture_v117.py" in source,
 "source_asset_preload_validator":"validate_source_safe_asset_loading_v117.py" in source,
 "source_candidate2_asset_set_validator":"validate_kg001_candidate2_asset_set_v118.py" in source,
 "source_test_build_contract_validator":"validate_kg001_test_build_contract_v118.py" in source,
 "build_manifest_generator":"write_kg001_build_manifest.py" in source and "BUILD_MANIFEST" in source,
 "git_clean_before_after":"clean_before=git_clean()" in source and "clean_after=git_clean()" in source,
 "forbidden_tracking_check":"repository_safety()" in source and "FORBIDDEN_TRACKED_PREFIXES" in source,
 "asset_ignore_check":'"check-ignore"' in source,
 "fresh_requires_import":'import_status=="PASS"' in source,
 "fresh_requires_all_runtime":"full_runtime_pass" in source and "all(asset_present.values())" in source,
 "fresh_requires_complete_asset_set":"--require-complete" in source and 'asset_gate.get("status")=="PASS"' in source and 'asset_gate.get("local_asset_status")=="COMPLETE"' in source,
 "promotion_is_optional":"--promote-results" in source,
 "fresh_is_optional":"--fresh-checkout" in source,
 "visual_capture_is_optional":"--visual-capture" in source,
 "visual_capture_runner":"kg001_visual_capture_v117.gd" in source and "OPENAZRAEL_KG001_VISUAL_V117" in source,
 "visual_capture_requires_local_assets":"VISUAL_AUDIO" in source and "BLOCKED_MISSING_ASSETS" in source,
 "visual_capture_affects_overall_only":"visual_pass" in source and "overall_pass" in source and "fresh_pass" in source,
 "visual_capture_promotion":"kg001_visual_capture_runtime_v117.json" in source,
 "source_only_exit_semantics":'else:\n        # Preserve the historical source-safe/default runner contract' in source and "exit_pass=source_ok" in source,
 "requested_visual_exit_semantics":"elif args.visual_capture:" in source and "exit_pass=source_ok and full_runtime_pass and visual_pass" in source,
}
failed=[k for k,v in checks.items() if not v]
print("OpenAzrael v112 candidate runner source contract:","PASS" if not failed else "FAIL")
for name,value in checks.items(): print(f" - {name}: {'PASS' if value else 'FAIL'}")
sys.exit(1 if failed else 0)
