#!/usr/bin/env python3
import argparse, hashlib, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from analyze_ambient_loader_v42 import build_obj1, EXPECTED

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); b=build_obj1(raw); sha=hashlib.sha256(raw).hexdigest()
 checks={
  'exe_hash':sha==EXPECTED,
  # loader makes filename buffer address EBX immediately before calling D523
  'loader_filename_buffer_to_ebx': b[0xd8c1:0xd8cb]==bytes.fromhex('0fb7f98d5da289fa89f0'),
  'loader_calls_d523': b[0xd8cb:0xd8d0]==bytes.fromhex('e853fcffff'),
  # D523 saves incoming EBX via push EBX; after ENTER/local pushes this is addressable at EBP-0x14
  'd523_preserves_incoming_ebx': b[0xd523:0xd52c]==bytes.fromhex('515657c80c00005053'),
  'd523_recovers_filename_as_edx': b[0xd599:0xd5a6]==bytes.fromhex('a19c1d04008b55ece89e190100'),
  'd523_calls_1ef44': int.from_bytes(b[0xd5a2:0xd5a6],'little',signed=True)+0xd5a6==0x1ef44,
  # 1EF44 stores EDX and passes it unchanged to 1FE7F lookup/load routine
  'wrapper_saves_edx': b[0x1ef4f:0x1ef58]==bytes.fromhex('8945f08955f4895dfc'),
  'wrapper_filename_to_1fe7f': b[0x1ef83:0x1ef90]==bytes.fromhex('31db8b55f48b45f0e8ef0e0000'),
  'wrapper_calls_1fe7f': int.from_bytes(b[0x1ef8c:0x1ef90],'little',signed=True)+0x1ef90==0x1fe7f,
  # resolved resource/sample descriptor is then passed into lower sample-start routine 1EDD7
  'resolved_descriptor_saved': b[0x1ef90:0x1ef93]==bytes.fromhex('8945e8'),
  'descriptor_to_1edd7': b[0x1efa6:0x1efb1]==bytes.fromhex('8b55e88b45f0e826feffff'),
  'wrapper_returns_sample_index': b[0x1efb1:0x1efbf]==bytes.fromhex('8945ec8b45ec89ec5d5f5ec20400'),
  # D523 stores AX into emitter record +0x0c
  'd523_stores_returned_handle': b[0xd5a6:0xd5b0]==bytes.fromhex('8b55f4668982f4270200'),
 }
 bad={k:v for k,v in checks.items() if not v}
 if bad: raise SystemExit('v43 invariant failed: '+repr(bad))
 out={
  'schema':'openazrael.sample_filename_to_handle','version':43,'status':'PASS','exe_sha256':sha,'invariants':checks,
  'pipeline':[
   {'stage':'AMB parser','evidence':'0xD7BF parses the sample filename into its local filename buffer; 0xD8C4 loads that buffer address into EBX before 0xD523.','confidence':'HIGH'},
   {'stage':'3D slot starter','routine':'0xD523','evidence':'incoming EBX is preserved on entry and recovered from EBP-0x14 into EDX immediately before call 0x1EF44.','confidence':'HIGH'},
   {'stage':'sample start wrapper','routine':'0x1EF44','evidence':'EDX is saved as local -0x0C and passed unchanged to 0x1FE7F; returned descriptor is then passed to 0x1EDD7.','confidence':'HIGH'},
   {'stage':'runtime slot binding','evidence':'return value from 0x1EF44 is stored as 16-bit value at emitter[slot]+0x0C (0x227F4 + slot*24).','confidence':'HIGH'}
  ],
  'end_to_end':'AMB SAMPLE filename -> parser local buffer -> EBX -> 0xD523 -> EDX -> 0x1EF44 -> 0x1FE7F resource/sample resolution -> 0x1EDD7 lower sample start -> returned sample index/handle -> emitter[slot]+0x0C -> 0xCDE1 spatialization -> Miles pan/volume',
  'correction':'v42 described the filename-to-handle link as the next target. v43 binds that dataflow directly at instruction level.',
  'confidence':{'filename_to_D523':'HIGH','D523_to_1EF44':'HIGH','filename_to_1FE7F':'HIGH','returned_handle_to_emitter_record':'HIGH','exact_semantics_of_1FE7F_resource_object':'PROBABLE','exact_Miles_sample_object_inside_1EDD7':'HOLD'},
  'next':['Disassemble 0x1FE7F resource resolution and 0x1EDD7 sample-start internals to identify the exact sample cache/resource structure.','Bind the lower call chain to Miles allocate/init/start APIs.','Use the now-closed AMB filename->runtime-slot path in Classic Audio provenance/debug output.']
 }
 Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':'PASS','filename_to_handle':'HIGH','checks':len(checks)},indent=2))
if __name__=='__main__': main()
