#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"data/tests/kg001_eugene_executable_character_controller_contract_v183.json"
def main():
 p=argparse.ArgumentParser();p.add_argument("--exe",type=Path);a=p.parse_args();c=json.loads(C.read_text())
 checks={"schema":c.get("schema")=="openazrael.kg001.eugene_executable_character_controller_contract" and c.get("version")==183,
 "source_hash_pinned":c["source"]["sha256"]=="381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00",
 "semantic_holds_preserved":set(c["unresolved"])=={"GLOBAL_RAND_CALL_INDEX_AT_EUGENE_ENTRY","MODEL_FRONT_SOURCE_PROOF","ANIMATION_CLOCK_SOURCE_PROOF","EUGROAR_TRIGGER_PARAMETER_200_SEMANTICS"}}
 if a.exe:
  b=a.exe.read_bytes()
  checks["source_identity"]=len(b)==c["source"]["bytes"] and hashlib.sha256(b).hexdigest()==c["source"]["sha256"]
  checks["ani_parser_offsets"]=all(b[o:o+len(s)].decode("ascii")==s for o,s in c["ani_parser_tokens"])
  checks["diagnostic_offsets"]=all(b[o:o+len(s)].decode("ascii")==s for o,s in c["diagnostics"])
  checks["timer_offsets"]=all(b[o:o+len(s)].decode("ascii")==s for o,s in c["timer_evidence"])
 failed=[k for k,v in checks.items() if not v]
 print(json.dumps({"schema":"openazrael.kg001.eugene_executable_character_controller_validation","version":183,
 "status":"STRUCTURAL_PASS" if not failed else "FAIL","checks":checks,"failed":failed,
 "semantic_holds":c["unresolved"],"runtime_status":"NOT_EXECUTED"},indent=2))
 return 1 if failed else 0
if __name__=="__main__":sys.exit(main())
