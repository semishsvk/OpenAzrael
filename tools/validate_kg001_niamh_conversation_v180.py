#!/usr/bin/env python3
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_niamh_conversation_1a_contract_v180.json").read_text(encoding="utf-8"))
room=(ROOT/"scripts/room_manager.gd").read_text(encoding="utf-8")
checks={
 "schema":contract.get("schema")=="openazrael.kg001.niamh_conversation_1a_contract",
 "version":contract.get("version")==180,
 "family":contract.get("source",{}).get("family")=="1A",
 "opening":contract.get("opening")=="Good Lord. What are you?",
 "branch_30":"Ni1A_30" in contract.get("branches",{}),
 "branch_999":"Ni1A_999" in contract.get("branches",{}),
 "branch_A":"Ni1A_A" in contract.get("branches",{}),
 "do_not_display":contract.get("branches",{}).get("Ni1A_A",{}).get("source_control_text")=="DO NOT DISPLAY",
 "no_invented_voice":contract.get("audio",{}).get("policy")=="DO_NOT_INVENT_VOICE_AUDIO",
 "runtime_contract_binding":"kg001_niamh_conversation_1a_contract_v180.json" in room,
 "runtime_source_ready":'"status": "SOURCE_TEXT_READY"' in room,
}
ok=all(checks.values())
print(json.dumps({"schema":"openazrael.kg001.niamh_conversation_1a_validation","version":180,
 "status":"SOURCE_TEXT_STATIC_PASS" if ok else "FAIL","checks":checks,
 "runtime":"NOT_EXECUTED","voice_audio":"NOT_PRESENT_IN_CANONICAL_DEMO"},indent=2))
raise SystemExit(0 if ok else 1)
