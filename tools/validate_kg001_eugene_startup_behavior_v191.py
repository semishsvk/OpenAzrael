#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"data/tests/kg001_eugene_startup_behavior_contract_v191.json"
SHA="381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00"
def main():
 c=json.loads(C.read_text())
 ok=(c["initialization"]["value"]==0 and c["autonomous_random_movement"]["guard"]=="character+0x25A != 0" and c["random_movement"]["shared_global_rand"] is True)
 if len(sys.argv)>1:
  b=Path(sys.argv[1]).read_bytes()
  ok &= hashlib.sha256(b).hexdigest()==SHA
  ok &= b[0x82d67:0x82d6f].hex()=="66c7805a02000000"
  ok &= b[0x848ab:0x848c9].hex().startswith("6683b85a020000007419")
 if not ok:
  print("EUGENE_STARTUP_BEHAVIOR_FAIL"); return 1
 print("EUGENE_STARTUP_BEHAVIOR_PASS")
 print("runtime=NOT_EXECUTED")
 return 0
if __name__=="__main__": raise SystemExit(main())
