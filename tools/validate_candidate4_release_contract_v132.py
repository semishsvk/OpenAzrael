#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_candidate4_release_contract_v132.json").read_text(encoding="utf-8"))
audio=(ROOT/"tools/validate_candidate4_audio_corpus_v132.py").read_text(encoding="utf-8")
checks={
 "schema":contract.get("schema")=="openazrael.kg001.candidate4_release_contract" and contract.get("version")==132,
 "candidate4":contract.get("candidate")=="KG-001 Candidate 4",
 "zero_critical":contract.get("release_policy",{}).get("zero_known_critical_bugs") is True,
 "geometry_rooms":contract.get("geometry",{}).get("rooms")==["R1","R7","R8"],
 "forensic_v131":"room_forensic_v131" in contract.get("geometry",{}).get("required_runtime_layers",[]),
 "wav_30":contract.get("audio",{}).get("canonical_wav_count")==30,
 "xmi_24":contract.get("audio",{}).get("canonical_xmi_count")==24,
 "music_fail_closed":contract.get("audio",{}).get("music_policy")=="REQUIRE_RUNTIME_OR_PROVEN_NOT_USED_ON_ACCEPTED_DEMO_ROUTE",
 "pppv_two_runs":contract.get("gameplay",{}).get("minimum_identical_end_to_end_runs",0)>=2,
 "audio_validator_30":"len(sounds)!=30" in audio and "RUNTIME_WAV_CORPUS_INCOMPLETE" in audio,
 "audio_validator_music":"MUSIC_ROUTE_EVIDENCE_MISSING" in audio,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.candidate4_release_contract_validation","version":132,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
