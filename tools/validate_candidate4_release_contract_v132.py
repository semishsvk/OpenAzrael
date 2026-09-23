#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from tools.kg001_gate_manifest import (
    CANDIDATE3_REQUIRED_RUNTIME,
    CANDIDATE3_ADDITIONAL_RUNTIME_EVIDENCE,
    PPPV_REQUIRED_EVIDENCE,
    CANDIDATE4_REQUIRED_PREFLIGHT,
    CANDIDATE4_SOURCE_VALIDATORS,
)
import tools.run_candidate4_preflight as candidate4_preflight

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
 "music_reproducibility_boundary":(
     contract.get("audio",{}).get("music_reproducibility",{}).get("event_schedule_sha256_required") is True
     and contract.get("audio",{}).get("music_reproducibility",{}).get("pcm_f32le_sha256_required") is True
     and contract.get("audio",{}).get("music_reproducibility",{}).get("fluidsynth_version_required") is True
     and contract.get("audio",{}).get("music_reproducibility",{}).get("libsndfile_version_required") is True
     and contract.get("audio",{}).get("music_reproducibility",{}).get("cross_platform_pcm_bit_identity_guaranteed") is False
     and contract.get("audio",{}).get("music_reproducibility",{}).get("cross_platform_ogg_bit_identity_guaranteed") is False
 ),
 "pppv_two_runs":contract.get("gameplay",{}).get("minimum_identical_end_to_end_runs",0)>=2,
 "audio_validator_30":"len(sounds)!=30" in audio and "RUNTIME_WAV_CORPUS_INCOMPLETE" in audio,
 "audio_validator_music":"MUSIC_ROUTE_EVIDENCE_MISSING" in audio,
 "preflight_source_validators_exact":tuple(candidate4_preflight.SOURCE_VALIDATORS)==CANDIDATE4_SOURCE_VALIDATORS,
 "inherited_runtime_exact":contract.get("inherited_candidate3",{}).get("required_runtime_pass")==list(CANDIDATE3_REQUIRED_RUNTIME),
 "inherited_additional_runtime_exact":contract.get("inherited_candidate3",{}).get("required_additional_runtime_evidence_pass")==list(CANDIDATE3_ADDITIONAL_RUNTIME_EVIDENCE),
 "pppv_evidence_exact":contract.get("inherited_candidate3",{}).get("required_pppv_v2_pass")==list(PPPV_REQUIRED_EVIDENCE),
 "required_preflight_exact":contract.get("required_preflight")==list(CANDIDATE4_REQUIRED_PREFLIGHT),
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.candidate4_release_contract_validation","version":132,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
