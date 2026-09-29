#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parents[1];C=ROOT/"data/tests/kg001_eugene_random_movement_callflow_contract_v186.json"
def main():
 p=argparse.ArgumentParser();p.add_argument("--exe",type=Path);a=p.parse_args();c=json.loads(C.read_text())
 checks={"schema":c.get("version")==186 and c.get("status")=="EXECUTABLE_CODE_VERIFIED",
 "caller_classes":c["callers"]["ai_update"]["classification"]=="AUTONOMOUS_CHARACTER_UPDATE" and c["callers"]["action_interpreter"]["classification"]=="SCRIPT_ACTION_PATH",
 "branch_hold":"EUGENE_INITIAL_CHARACTER_FIELD_0x25A" in c["holds"]}
 if a.exe:
  b=a.exe.read_bytes();checks["hash"]=hashlib.sha256(b).hexdigest()==c["source"]["sha256"]
  def tgt(x):return x+5+struct.unpack_from("<i",b,x+1)[0]
  checks["calls"]=tgt(0x848bd)==0x86780 and tgt(0x861d6)==0x86780 and tgt(0x86806)==0x97f85 and tgt(0x86852)==0x97f85 and tgt(0x869c6)==0x97f85
  checks["ai_counter"]=b[0x848ab:0x848b3]==bytes.fromhex("6683b85a02000000") and b[0x848c2:0x848c9]==bytes.fromhex("66ff8e5a020000")
  checks["action_types"]=all(x in b[0x86178:0x861a3] for x in [bytes.fromhex("80fe02"),bytes.fromhex("80fe05"),bytes.fromhex("80fe14"),bytes.fromhex("80fe0d")])
 failed=[k for k,v in checks.items() if not v]
 print(json.dumps({"schema":"openazrael.kg001.eugene_random_movement_callflow_validation","version":186,"status":"EXECUTABLE_CODE_PASS" if not failed else "FAIL","checks":checks,"failed":failed,"runtime_status":"NOT_EXECUTED","holds":c["holds"]},indent=2));return 1 if failed else 0
if __name__=="__main__":sys.exit(main())
