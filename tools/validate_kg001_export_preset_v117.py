#!/usr/bin/env python3
"""Validate the KG-001 Candidate 2 Windows export contract."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
PRESET=ROOT/"export_presets.cfg"
CONTRACT=ROOT/"data/tests/kg001_toolchain_contract_v117.json"

text=PRESET.read_text(encoding="utf-8") if PRESET.is_file() else ""
toolchain=json.loads(CONTRACT.read_text(encoding="utf-8"))
checks={
    "preset_exists":PRESET.is_file(),
    "candidate2_name":'name="Windows Candidate 2"' in text,
    "windows_platform":'platform="Windows Desktop"' in text,
    "x86_64":'binary_format/architecture="x86_64"' in text,
    "external_pck":'binary_format/embed_pck=false' in text,
    "debug_console":'debug/export_console_wrapper=1' in text,
    "candidate2_feature":'custom_features="kg001_candidate2"' in text,
    "candidate2_path":'OpenAzrael-KG001-Candidate2-v116.exe' in text,
    "build_manifest_included":'data/generated/kg001_candidate_build_manifest.json' in text,
    "event_graph_included":'data/gameplay_event_graph_v87.json' in text,
    "trigger_evidence_included":'data/xaf_trigger_evidence.json' in text,
    "audio_ir_included":'data/audio/legacy_world_ir.json' in text,
    "source_tools_excluded":'tools/*' in text,
    "test_evidence_excluded":'data/tests/*' in text,
    "candidate2_version":'application/file_version="0.116.0.2"' in text,
    "context_v30":'v116-context-v30' in text,
    "godot_contract_pinned":toolchain.get("godot",{}).get("version")=="4.7.2.stable.official.ed1daf0bf",
}
failed=[k for k,v in checks.items() if not v]
result={
    "schema":"openazrael.kg001.windows_export_contract",
    "version":117,
    "status":"PASS" if not failed else "FAIL",
    "preset":"Windows Candidate 2",
    "checks":checks,
    "failed":failed,
    "runtime_export_status":"NOT_EXECUTED",
}
print(json.dumps(result,indent=2))
sys.exit(1 if failed else 0)
