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
 "runtime_v117":"kg001_physical_traversal_runner_v117.gd" in source,
 "runtime_v118":"kg001_well_tongs_animation_runner_v118.gd" in source,
 "framework_source_suite":all(x in source for x in ("tools.remaster_framework.cli","tools/remaster_framework/tests","runtime_capabilities")),
 "framework_bundle":"kg001_candidate_framework" in source and "kg001_framework_bundle.json" in source,
 "framework_metadata_staging":"--stage-framework-metadata" in source and "runtime_metadata" in source,
 "git_clean_before_after":"clean_before=git_clean()" in source and "clean_after=git_clean()" in source,
 "forbidden_tracking_check":"repository_safety()" in source and "FORBIDDEN_TRACKED_PREFIXES" in source,
 "asset_ignore_check":'"check-ignore"' in source,
 "fresh_requires_import":'import_status=="PASS"' in source,
 "fresh_requires_all_runtime":"full_runtime_pass" in source and "all(asset_present.values())" in source,
 "promotion_is_optional":"--promote-results" in source,
 "fresh_is_optional":"--fresh-checkout" in source,
}
failed=[k for k,v in checks.items() if not v]
print("OpenAzrael v112 candidate runner source contract:","PASS" if not failed else "FAIL")
for name,value in checks.items(): print(f" - {name}: {'PASS' if value else 'FAIL'}")
sys.exit(1 if failed else 0)
