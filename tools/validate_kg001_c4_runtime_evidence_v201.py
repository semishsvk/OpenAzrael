#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"data/tests/kg001_c4_runtime_evidence_contract_v201.json"

def load(p):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return None
def head():
    p=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return p.stdout.strip() if p.returncode==0 else ""
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pppv")
    ap.add_argument("--determinism")
    ap.add_argument("--visual")
    ap.add_argument("--pacing")
    ap.add_argument("--pppv-identity")
    ap.add_argument("--out",default=".tmp/kg001_c4_closure/c4_runtime_evidence_v201.json")
    a=ap.parse_args()
    c=load(CONTRACT); h=head()
    defaults=c["required_receipts"]
    paths={
      "pppv":ROOT/(a.pppv or defaults["pppv"]),
      "determinism":ROOT/(a.determinism or defaults["pppv_determinism"]),
      "visual":ROOT/(a.visual or defaults["visual"]),
      "pacing":ROOT/(a.pacing or defaults["pacing"]),
      "pppv_identity":ROOT/(a.pppv_identity or defaults["pppv_identity"])
    }
    docs={k:load(v) if v.is_file() else None for k,v in paths.items()}
    checks={}
    checks["head_resolved"]=bool(h)
    checks["all_receipts_present"]=all(v is not None for v in docs.values())
    p=docs["pppv"] or {}; d=docs["determinism"] or {}; v=docs["visual"] or {}; pc=docs["pacing"] or {}; ident=docs["pppv_identity"] or {}
    checks["pppv_identity_pass"]=ident.get("status")=="PASS"
    checks["pppv_identity_head_bound"]=ident.get("commit_sha")==h
    checks["pppv_receipt_hash_bound"]=bool(paths["pppv"].is_file()) and ident.get("pppv_evaluation_sha256")==sha(paths["pppv"])
    checks["determinism_receipt_hash_bound"]=bool(paths["determinism"].is_file()) and ident.get("pppv_determinism_sha256")==sha(paths["determinism"])
    checks["pppv_pass"]=p.get("status")=="PASS"
    checks["pppv_head_bound"]=ident.get("commit_sha")==h
    checks["determinism_pass"]=d.get("status")=="PASS"
    checks["determinism_head_bound"]=ident.get("commit_sha")==h
    checks["four_transitions"]=d.get("transition_scenario_count")==4 or p.get("transition_scenario_count")==4
    checks["visual_pass"]=v.get("status")=="PASS"
    checks["visual_head_bound"]=v.get("commit_sha")==h
    required=c["visual_required_checks"]
    visual_checks=v.get("checks",{}) if isinstance(v.get("checks",{}),dict) else {}
    checks["visual_regressions_all_observed"]=all(visual_checks.get(k) is True for k in required)
    checks["visual_not_ai"]=v.get("ai_generated") is False
    checks["pacing_pass"]=pc.get("status")=="PASS"
    checks["pacing_reference_only"]=pc.get("authority")=="REPRODUCIBILITY_REFERENCE_NOT_SOURCE_AUTHORITY"
    checks["pacing_no_fixed_hz_claim"]=pc.get("fixed_source_hz_claimed") is False
    failed=[k for k,vv in checks.items() if not vv]
    payload={
      "schema":"openazrael.kg001.c4_runtime_evidence_validation","version":201,
      "status":"PASS" if not failed else "BLOCKED",
      "commit_sha":h,"checks":checks,"failed":failed,
      "receipts":{k:({"path":str(paths[k].relative_to(ROOT)),"sha256":sha(paths[k])} if paths[k].is_file() else {"path":str(paths[k].relative_to(ROOT)),"missing":True}) for k in paths},
      "candidate_gate":"OPEN" if not failed else "BLOCKED",
      "historical_candidate4_receipts_accepted":False
    }
    out=ROOT/a.out; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2,sort_keys=True))
    return 0 if not failed else 2
if __name__=="__main__":sys.exit(main())
