#!/usr/bin/env python3
"""Source-safe contract for KG-001 Candidate 2 canonical visual capture."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/kg001_visual_capture_v117.gd"
text=SCRIPT.read_text(encoding="utf-8") if SCRIPT.is_file() else ""

checks={
    "script_exists":SCRIPT.is_file(),
    "graphical_only":'DisplayServer.get_name() == "headless"' in text and "BLOCKED_HEADLESS" in text,
    "canonical_views":all(token in text for token in [
        '{"room":"R1", "view":"spaview"}',
        '{"room":"R7", "view":"view"}',
        '{"room":"R8", "view":"Object14"}',
    ]),
    "run_scoped_output":'CandidateDiagnostics.run_dir + "/captures"' in text,
    "manifest_output":'"/captures/manifest.json"' in text,
    "run_identity":'CandidateDiagnostics.run_id' in text,
    "commit_identity":'CandidateDiagnostics.build_manifest.get("commit_sha"' in text,
    "hide_hud":'scene.get_node_or_null("HUD")' in text and 'visible = false' in text,
    "hide_trigger_debug":'TriggerDebugV116' in text,
    "freeze_player":'set_physics_process(false)' in text,
    "canonical_spawn":'manager.call("_spawn_at_portal", room_id, view_name)' in text,
    "png_capture":'save_png(path)' in text,
    "sha256":'HashingContext.HASH_SHA256' in text,
    "viewport_1280x720":'== 1280' in text and '== 720' in text,
    "three_capture_count":'rows.size() == 3' in text,
    "observational_oracle":'OBSERVATIONAL_CANONICAL_VIEW_NOT_CROSS_GPU_PIXEL_HASH' in text,
    "telemetry_event":'record_event("canonical_visual_capture"' in text,
}
failed=[name for name,value in checks.items() if not value]
result={
    "schema":"openazrael.kg001.visual_capture_contract",
    "version":117,
    "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "runtime_status":"NOT_EXECUTED",
    "requires_graphical_display":True,
    "captures":[
        {"room":"R1","view":"spaview","width":1280,"height":720},
        {"room":"R7","view":"view","width":1280,"height":720},
        {"room":"R8","view":"Object14","width":1280,"height":720},
    ],
    "oracle":"OBSERVATIONAL_CANONICAL_VIEW_NOT_CROSS_GPU_PIXEL_HASH",
    "checks":checks,
    "failed":failed,
}
print(json.dumps(result,indent=2))
sys.exit(1 if failed else 0)
