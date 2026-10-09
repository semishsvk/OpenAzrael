#!/usr/bin/env python3
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from analyze_ambient_loader_v42 import build_obj1,EXPECTED

def rel32(b,at): return at+5+int.from_bytes(b[at+1:at+5],'little',signed=True)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); b=build_obj1(raw); sha=hashlib.sha256(raw).hexdigest()
 checks={
  'exe_hash':sha==EXPECTED,
  'amb_callsite_pushes_flag0_after_literal1000':b[0xd8a4:0xd8af]==bytes.fromhex('6a0068e80300006a006a01'),
  'restart_path_same_1000_and_flag0':b[0xd0f2:0xd0fd]==bytes.fromhex('6a0068e80300006a006a01'),
  'd523_reads_flag_from_plus34':b[0xd589:0xd58e]==bytes.fromhex('0fbe453450'),
  'd523_reads_1000_word_from_plus30_into_ecx':b[0xd58e:0xd592]==bytes.fromhex('0fbf4d30'),
  'd523_calls_1ef44':rel32(b,0xd5a1)==0x1ef44,
  '1ef44_preserves_ecx':b[0x1ef58:0x1ef5b]==bytes.fromhex('894df8'),
  '1ef44_forwards_flag_as_stack_arg':b[0x1ef93:0x1ef9a]==bytes.fromhex('8b450dc1f81850'),
  '1ef44_recovers_ecx1000':b[0x1ef9a:0x1efa3]==bytes.fromhex('8b4df6c1f9108b5dfa'),
  '1ef44_calls_1edd7':rel32(b,0x1efac)==0x1edd7,
  '1edd7_preserves_ecx1000':b[0x1edeb:0x1edee]==bytes.fromhex('894df8'),
  '1edd7_flag_controls_branch':b[0x1eede:0x1eee2]==bytes.fromhex('807d1001'),
  '1edd7_pushes_preserved_ecx1000_to_1efbf':b[0x1ee8e:0x1eea9]==bytes.fromhex('31c0668b45f8508b4df48b5dfac1fb108b55e08b45f0e816010000'),
  '1efbf_reads_its_stack_arg_as_loop_count':b[0x1f08d:0x1f09c]==bytes.fromhex('31c0668b451050ff75f4e8529e0100'),
  'loop_setter_target':rel32(b,0x1f097)==0x38eee,
  'start_follows_loop_setter':rel32(b,0x1f0a2)==0x38bd8,
 }
 bad=[k for k,v in checks.items() if not v]
 if bad: raise SystemExit('v50 invariant failed: '+repr(bad))
 out={
  'schema':'openazrael.ambient_loop_abi_correction','version':50,'status':'PASS','exe_sha256':sha,'invariants':checks,
  'correction':{
   'supersedes':'v46 loop-count interpretation and v49 HOLD status for literal 1000',
   'ambient_loop_count_argument':1000,'confidence':'HIGH',
   'flag_argument':0,'flag_semantics':'HOLD',
   'path':'D8A6 literal 1000 -> D523 +0x30 -> ECX -> 1EF44 preserved/forwarded ECX -> 1EDD7 preserved ECX -> pushed into 1EFBF -> 1EFBF +0x10 -> AIL_set_sample_loop_count -> AIL_start_sample',
   'why_v46_was_wrong':'v46 followed the separate stack flag argument (0) into 1EDD7 but did not continue the independently preserved ECX word (1000). The flag controls a branch in 1EDD7; the preserved ECX value is the one forwarded to the lower starter and consumed by the loop-count setter.'
  },
  'restart_evidence':{'confidence':'HIGH','note':'The ambient restart path at 0xD0F2 pushes the same 1000/0 tail pair before 0xD523, independently matching the loader call convention.'},
  'semantic_scope':{'numeric_loop_count':1000,'confidence':'HIGH','meaning_of_1000_in_miles':'HOLD','note':'Do not relabel 1000 as infinite or exact repeat semantics without separately binding the Miles API convention/version.'},
  'next':['Audit every project/runtime reference that still claims loop_count=0 and supersede it.','Resume exact 3D attenuation formula reconstruction at 0xCF31..0xCF8E, including relocated floating constants.','Resolve pan angular constants/relocations and reproduce the Classic spatializer in a testable pure function.']
 }
 Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':'PASS','checks':len(checks),'corrected_loop_count':1000,'flag':0},indent=2))
if __name__=='__main__': main()
