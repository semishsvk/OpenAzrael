#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from tools.kg001_gate_manifest import CANDIDATE3_REQUIRED_RUNTIME

def validate(receipt: dict, head: str) -> tuple[bool,list[str]]:
    failures=[]
    if receipt.get("commit_sha") != head:
        failures.append("PREFLIGHT_COMMIT_SHA_MISMATCH")
    runtime_status=receipt.get("runtime_status")
    if not isinstance(runtime_status,dict):
        runtime_status=receipt.get("runtimes",{})
    if not isinstance(runtime_status,dict):
        failures.append("RUNTIME_STATUS_MAP_MISSING")
        runtime_status={}
    for name in CANDIDATE3_REQUIRED_RUNTIME:
        if runtime_status.get(name) != "PASS":
            failures.append(f"REQUIRED_RUNTIME_NOT_PASS:{name}:{runtime_status.get(name)}")
    if receipt.get("fresh_checkout") not in ("PASS", {"status":"PASS"}):
        fresh=receipt.get("fresh_checkout")
        if not (isinstance(fresh,dict) and fresh.get("status")=="PASS"):
            failures.append("FRESH_CHECKOUT_NOT_PASS")
    return not failures,failures

def main():
    path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/".tmp/kg001/candidate4_preflight_receipt.json"
    head=sys.argv[2] if len(sys.argv)>2 else ""
    try: receipt=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"status":"FAIL","failures":["RECEIPT_INVALID"],"error":str(exc)},indent=2)); return 1
    ok,failures=validate(receipt,head)
    print(json.dumps({"schema":"openazrael.kg001.release_runtime_evidence_validation","version":176,
      "status":"PASS" if ok else "FAIL","commit_sha":head,
      "required_runtime_count":len(CANDIDATE3_REQUIRED_RUNTIME),"failures":failures},indent=2))
    return 0 if ok else 1
if __name__=="__main__": raise SystemExit(main())
