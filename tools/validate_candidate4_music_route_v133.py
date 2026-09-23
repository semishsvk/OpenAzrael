#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_candidate4_music_route_contract_v133.json").read_text(encoding="utf-8"))
tool=(ROOT/"tools/analyze_candidate4_music_route_v133.py").read_text(encoding="utf-8")
preflight=(ROOT/"tools/run_candidate4_preflight.py").read_text(encoding="utf-8")
audio=(ROOT/"tools/validate_candidate4_audio_corpus_v132.py").read_text(encoding="utf-8")
checks={
 "schema":contract.get("schema")=="openazrael.kg001.candidate4_music_route_contract" and contract.get("version")==133,
 "bound_rexe":contract.get("input_policy",{}).get("bound_demo_rexe_sha256")=="381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00",
 "xmi_24":contract.get("input_policy",{}).get("canonical_xmi_count")==24,
 "no_raw":contract.get("source_safety",{}).get("raw_music_dat_emitted") is False and contract.get("source_safety",{}).get("raw_xmi_emitted") is False,
 "no_numeric_guess":contract.get("semantic_policy",{}).get("bare_numeric_room_inference_allowed") is False,
 "bound_room_mapping":contract.get("semantic_policy",{}).get("bound_demo_room_numeric_mapping")=={"0":"R1","1":"R7","2":"R8"},
 "bound_room_evidence":contract.get("semantic_policy",{}).get("bound_numeric_room_mapping_evidence")=="data/world_sound_record_fields_v113.json",
 "bound_gm_slots":contract.get("semantic_policy",{}).get("bound_rexe_gm_slot_table",[])[6:8]==["INGAME.XMI","INGAME2.XMI"],
 "tool_checks_rexe":"BOUND_DEMO_REXE_HASH_MISMATCH" in tool,
 "tool_checks_xmi":"CANONICAL_XMI_CORPUS_INVALID" in tool,
 "tool_checks_bound_numeric":"BOUND_NUMERIC_MUSIC_EVIDENCE_INVALID" in tool and "GM_SLOT_TABLE" in tool and "ROOM_EVIDENCE" in tool,
 "tool_no_numeric_promotion":"Bare numeric fields are metadata only" in tool,
 "tool_holds_ambiguous":"MUSIC_TABLE_ROUTE_MAPPING_INCOMPLETE_OR_AMBIGUOUS" in tool,
 "tool_requires_complete_rooms":'route_complete=all(len(by_room[room])==1 for room in ("R1","R7","R8"))' in tool,
 "preflight_runs_analyzer":"analyze_candidate4_music_route_v133.py" in preflight,
 "audio_uses_local_route":'.tmp/kg001/candidate4_music_route_v133.json' in audio,
 "runtime_music_fail_closed":"MUSIC_RUNTIME_REQUIRED" in audio,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.candidate4_music_route_contract_validation",
 "version":133,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL",
 "checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
