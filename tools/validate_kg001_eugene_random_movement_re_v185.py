#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parents[1]; C=ROOT/"data/tests/kg001_eugene_random_movement_re_contract_v185.json"
def main():
 a=argparse.ArgumentParser();a.add_argument("--exe",type=Path);x=a.parse_args();c=json.loads(C.read_text())
 checks={"schema":c.get("version")==185 and c.get("status")=="EXECUTABLE_CODE_VERIFIED",
 "movement":c["random_movement"]["function_hex"]=="0x86780" and c["random_movement"]["candidate_distance_immediate"]==80,
 "heading":c["random_movement"]["heading_modulus"]==360 and c["random_movement"]["secondary_heading_modulus"]==360,
 "holds":"GLOBAL_RAND_CALL_INDEX_AT_EUGENE_ENTRY" in c["holds"]}
 if x.exe:
  b=x.exe.read_bytes();checks["hash"]=hashlib.sha256(b).hexdigest()==c["source"]["sha256"]
  checks["rand_code"]=b[0x97f8f:0x97fa7].find(bytes.fromhex("6d4ec641"))>=0 and b[0x97f8f:0x97fa7].find(bytes.fromhex("39300000"))>=0 and b[0x97f8f:0x97fa8].find(bytes.fromhex("ff7f0000"))>=0
  def target(p): return p+5+struct.unpack_from("<i",b,p+1)[0]
  checks["heading_calls"]=target(0x86852)==0x97f85 and target(0x869c6)==0x97f85 and b[0x86859:0x8685e]==bytes.fromhex("be68010000") and b[0x869cd:0x869d2]==bytes.fromhex("bb68010000")
  checks["candidate_80"]=b[0x86795:0x8679a]==bytes.fromhex("b950000000")
 failed=[k for k,v in checks.items() if not v]
 print(json.dumps({"schema":"openazrael.kg001.eugene_random_movement_re_validation","version":185,"status":"EXECUTABLE_CODE_PASS" if not failed else "FAIL","checks":checks,"failed":failed,"runtime_status":"NOT_EXECUTED","holds":c["holds"]},indent=2));return 1 if failed else 0
if __name__=="__main__":sys.exit(main())
