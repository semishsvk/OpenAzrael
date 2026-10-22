#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"data/tests/kg001_c4_regression_closure_contract_v200.json"

def main():
    m=json.loads(MANIFEST.read_text(encoding="utf-8"))
    checks={}
    checks["schema"]=m.get("schema")=="openazrael.kg001.c4_regression_closure" and m.get("version")==200
    checks["candidate_fail_closed"]=m.get("candidate_gate")=="BLOCKED"
    checks["source_not_runtime"]=m.get("policy",{}).get("source_presence_is_not_runtime_proof") is True
    checks["historical_proof_rejected"]=m.get("policy",{}).get("historical_candidate4_proof_is_not_current_head_proof") is True
    ids={r.get("id") for r in m.get("regressions",[])}
    checks["all_c4_regressions_declared"]={
        "menu_hud","cursor","inventory_rendering","animation",
        "keyhole_and_windows_orientation","stairs_collision","room_transitions"
    } <= ids
    missing=[]
    for row in m.get("regressions",[]):
        for rel in row.get("source",[]):
            if not (ROOT/rel).exists(): missing.append(rel)
        validator=row.get("source_validator")
        if validator and not (ROOT/validator).exists(): missing.append(validator)
    checks["declared_sources_exist"]=not missing
    transitions=next((r for r in m["regressions"] if r["id"]=="room_transitions"),{})
    checks["transitions_critical"]=transitions.get("critical") is True and transitions.get("transition_count")==4
    anim=next((r for r in m["regressions"] if r["id"]=="animation"),{})
    checks["animation_requires_original_runtime"]="ORIGINAL_RUNTIME_PACING_CAPTURE" in anim.get("required_evidence",[])
    uv=next((r for r in m["regressions"] if r["id"]=="keyhole_and_windows_orientation"),{})
    checks["uv_no_per_texture_hack"]=uv.get("invariant")=="NO_PER_TEXTURE_ORIENTATION_HACK"
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({
        "schema":"openazrael.kg001.c4_regression_closure_validation",
        "version":200,
        "status":"SOURCE_CONTRACT_PASS_RUNTIME_BLOCKED" if not failed else "FAIL",
        "checks":checks,
        "missing":sorted(set(missing)),
        "failed":failed,
        "candidate_gate":"BLOCKED"
    },indent=2,sort_keys=True))
    return 0 if not failed else 1

if __name__=="__main__": sys.exit(main())
