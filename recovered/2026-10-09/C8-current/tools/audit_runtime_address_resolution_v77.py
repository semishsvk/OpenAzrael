#!/usr/bin/env python3
import argparse, hashlib, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from analyze_ambient_loader_v42 import build_obj1, EXPECTED

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); obj=build_obj1(raw); sha=hashlib.sha256(raw).hexdigest()
 anchors={
  'spatial_core':0xCDE1,
  'listener_position':0x227D0,
  'listener_forward':0x227DC,
  'emitter_table':0x227E8,
  'audio_manager_global':0x41D9C,
 }
 checks={
  'exe_hash':sha==EXPECTED,
  'all_anchors_inside_object1':all(0 <= v < len(obj) for v in anchors.values()),
  'spatial_core_signature':obj[0xCDE1:0xCDF2]==bytes.fromhex('5351525657c830000050c745f001000000'),
  'emitter_base_immediate_in_core':obj[0xCDF2:0xCDF9]==bytes.fromhex('c745f8e8270200'),
  'listener_position_immediate':obj[0xCE07:0xCE0C]==bytes.fromhex('bfd0270200'),
  'listener_forward_immediate':obj[0xCE12:0xCE17]==bytes.fromhex('bfdc270200'),
  'manager_global_used_for_pan':obj[0xCF98:0xCF9D]==bytes.fromhex('a19c1d0400'),
  'manager_global_used_for_volume':obj[0xCFAE:0xCFB3]==bytes.fromhex('a19c1d0400'),
  'emitter_stride_24':obj[0xCFBD:0xCFC1]==bytes.fromhex('8345f818'),
 }
 bad=[k for k,v in checks.items() if not v]
 if bad: raise SystemExit('v77 invariant failed: '+repr(bad))
 # Same LE object => a debugger-observed runtime address of any verified object1 anchor yields one object delta.
 rel={k:hex(v-anchors['spatial_core']) for k,v in anchors.items() if k!='spatial_core'}
 out={
  'schema':'openazrael.runtime_address_resolution','version':77,'status':'PASS','exe_sha256':sha,
  'object1_size':len(obj),'anchors_object1_offsets':{k:hex(v) for k,v in anchors.items()},
  'relative_to_spatial_core':rel,'invariants':checks,
  'resolver':{
   'method':'SAME_OBJECT_RUNTIME_ANCHOR_DELTA',
   'formula':'runtime_target = runtime_spatial_core + (target_object1_offset - 0xCDE1)',
   'required_observation':'Observe the loaded runtime address of the verified 0xCDE1 spatial-core signature in a debugger/emulator.',
   'confidence':'HIGH'
  },
  'boundary':{
   'preferred_LE_object_base_as_runtime_address':'NOT_REQUIRED',
   'old_fixup_graph':'QUARANTINED',
   'absolute_DOS_linear_addresses':'UNOBSERVED',
   'note':'v77 does not guess a load base. It resolves targets from one runtime-observed address inside the same LE object.'
  }
 }
 Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':'PASS','checks':len(checks),'object1_size':hex(len(obj)),'resolver':'same-object anchor delta','confidence':'HIGH'},indent=2))
if __name__=='__main__': main()
