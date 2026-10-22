#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"data/tests/kg001_candidate5_release_contract_v202.json"
def main():
 c=json.loads(C.read_text(encoding="utf-8")); checks={}
 checks["schema"]=c.get("schema")=="openazrael.kg001.candidate5_release_contract" and c.get("version")==202
 checks["candidate"]=c.get("candidate")=="KG-001 Candidate 5"
 checks["inherits_c4"]=c.get("inherits",{}).get("all_candidate4_required_preflight") is True and c.get("inherits",{}).get("all_candidate4_packaged_critical_gameplay") is True
 checks["fail_closed"]=c.get("candidate_gate")=="BLOCKED"
 checks["historical_c4_forbidden"]=c.get("release_policy",{}).get("candidate4_historical_receipts_forbidden") is True
 checks["exact_head"]=c.get("release_policy",{}).get("exact_head_evidence_binding") is True
 checks["source_gates_exist"]=all((ROOT/p).is_file() for p in c.get("additional_source_gates",[]))
 a=c.get("animation_policy",{})
 checks["animation_source_frame"]=a.get("integer_source_frame_authority") is True and a.get("one_update_per_equivalent_legacy_scene_pass") is True
 checks["no_fixed_hz_authority"]=a.get("fixed_source_hz_authority") is False
 checks["no_godot_clock_claim"]=a.get("godot_process_clock_source_exact") is False and a.get("godot_physics_clock_source_exact") is False
 checks["v199_required"]=a.get("production_clock_binding_requires_v199_pass") is True and "ORIGINAL_RUNTIME_PACING_V199" in c.get("required_runtime_evidence",[])
 checks["v201_required"]="C4_RUNTIME_EVIDENCE_V201" in c.get("required_runtime_evidence",[])
 failed=[k for k,v in checks.items() if not v]
 print(json.dumps({"schema":"openazrael.kg001.candidate5_release_contract_validation","version":202,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","checks":checks,"failed":failed,"candidate_gate":"BLOCKED"},indent=2))
 return 0 if not failed else 1
if __name__=="__main__":sys.exit(main())
