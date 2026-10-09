#!/usr/bin/env python3
import argparse,json,hashlib,struct
from pathlib import Path
REQ={'listener_pos.bin':12,'listener_fwd.bin':12,'emitters.bin':168,'manager.bin':0x364}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--capture-dir',required=True); ap.add_argument('--out',required=True); a=ap.parse_args(); d=Path(a.capture_dir)
 checks=[]
 for name,n in REQ.items():
  p=d/name; ok=p.exists() and p.stat().st_size==n; checks.append({'file':name,'expected_bytes':n,'actual_bytes':p.stat().st_size if p.exists() else None,'pass':ok,'sha256':sha(p) if ok else None})
 mp=d/'audio_manager_pointer.bin'
 ptr=None
 if mp.exists() and mp.stat().st_size==4: ptr=struct.unpack('<I',mp.read_bytes())[0]
 extras={x:(d/x).exists() for x in ['AIL_DEBUG.LOG','openazrael_audio_capture_v71.jsonl']}
 status='PASS' if all(x['pass'] for x in checks) and all(extras.values()) else 'INCOMPLETE'
 out={'schema':'openazrael.capture_bundle_validation','version':81,'status':status,'binary_checks':checks,'manager_pointer_observed':hex(ptr) if ptr is not None else None,'external_files':extras,'note':'PASS validates bundle completeness/byte sizes only; it is not audio parity evidence.'}
 Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps({'status':status,'manager_pointer':out['manager_pointer_observed'],'binary_files_ok':sum(x['pass'] for x in checks),'external_files_ok':sum(extras.values())},indent=2)); return 0 if status=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
