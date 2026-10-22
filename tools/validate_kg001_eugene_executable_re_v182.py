#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"data/tests/kg001_eugene_executable_re_contract_v182.json"
def main():
 p=argparse.ArgumentParser(); p.add_argument("--exe",type=Path); a=p.parse_args()
 c=json.loads(CONTRACT.read_text())
 checks={"schema":c.get("schema")=="openazrael.kg001.eugene_executable_re_contract" and c.get("version")==182,
 "source_hash_pinned":c["source"]["sha256"]=="381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00",
 "holds_preserved":set(c["unresolved"])=={"GLOBAL_RAND_CALL_INDEX_AT_EUGENE_ENTRY","MODEL_FRONT_SOURCE_PROOF","ANIMATION_CLOCK_SOURCE_PROOF","EUGROAR_TRIGGER_PARAMETER_200_SEMANTICS"}}
 if a.exe:
  b=a.exe.read_bytes()
  checks["source_hash_matches"]=hashlib.sha256(b).hexdigest()==c["source"]["sha256"] and len(b)==c["source"]["bytes"]
  checks["direct_eugene_strings_absent"]=b"EUGENE" not in b.upper() and b"EUGROAR" not in b.upper()
  checks["action_offsets"]=all(b[x["offset"]:x["offset"]+len(x["string"])].decode("ascii")==x["string"] for x in c["observations"]["action_api_cluster"])
  checks["animation_token_offsets"]=all(b[o:o+len(s)].decode("ascii")==s for o,s in c["observations"]["animation_token_table"])
 failed=[k for k,v in checks.items() if not v]
 print(json.dumps({"schema":"openazrael.kg001.eugene_executable_re_validation","version":182,
 "status":"STRUCTURAL_PASS" if not failed else "FAIL","checks":checks,"failed":failed,
 "runtime_status":"NOT_EXECUTED","semantic_holds":c["unresolved"]},indent=2))
 return 1 if failed else 0
if __name__=="__main__": sys.exit(main())
