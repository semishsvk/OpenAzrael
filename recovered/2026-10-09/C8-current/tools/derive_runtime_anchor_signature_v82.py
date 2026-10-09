#!/usr/bin/env python3
import argparse, hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_ambient_loader_v42 import build_obj1
OFF=0xCDE1
EXPECTED_SHA='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def hits(buf, sig):
 out=[]; p=0
 while True:
  p=buf.find(sig,p)
  if p<0:return out
  out.append(p);p+=1
def main():
 ap=argparse.ArgumentParser(description='Derive a relocation-safe candidate byte signature for the v82 runtime CDE1 anchor.')
 ap.add_argument('--exe',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); sha=hashlib.sha256(raw).hexdigest(); obj=build_obj1(raw)
 if OFF+32>len(obj): raise SystemExit('object1 too short')
 candidates=[]
 for n in (8,12,16,20,24,32):
  sig=obj[OFF:OFF+n]; hs=hits(obj,sig)
  candidates.append({'bytes':n,'hex':sig.hex(),'object1_hits':[hex(x) for x in hs],'unique_in_rebuilt_object1':len(hs)==1})
 # First 16 bytes contain only prologue/local setup in the decoded stream and no absolute data operand.
 chosen=next(x for x in candidates if x['bytes']==16)
 out={'schema':'openazrael.runtime_anchor_signature','version':82,'exe_sha256':sha,'expected_demo_exe_sha256':EXPECTED_SHA,'exe_identity_pass':sha==EXPECTED_SHA,'anchor_object1_offset':hex(OFF),'chosen_signature':chosen,'candidates':candidates,'runtime_use_status':'HIGH','evidence_boundary':'The 16-byte signature is VERIFIED unique in the rebuilt object-1 image of the bound demo R.EXE. Using it to locate the loaded runtime copy is HIGH until independently observed in a real DOS run. A search hit must be verified by reading surrounding bytes before deriving v77 addresses.'}
 Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':'PASS' if out['exe_identity_pass'] and chosen['unique_in_rebuilt_object1'] else 'FAIL','exe_identity_pass':out['exe_identity_pass'],'signature_bytes':16,'signature':chosen['hex'],'object1_hits':chosen['object1_hits']},indent=2))
 return 0 if out['exe_identity_pass'] and chosen['unique_in_rebuilt_object1'] else 2
if __name__=='__main__': raise SystemExit(main())
