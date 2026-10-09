#!/usr/bin/env python3
import argparse, hashlib, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from analyze_ambient_loader_v42 import build_obj1, EXPECTED

def rel32(b, at): return at+5+int.from_bytes(b[at+1:at+5],'little',signed=True)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
    raw=Path(a.exe).read_bytes(); b=build_obj1(raw); sha=hashlib.sha256(raw).hexdigest()
    checks={
      'exe_hash':sha==EXPECTED,
      'amb_push_tail_constants':b[0xd8a4:0xd8af]==bytes.fromhex('6a0068e80300006a006a01'),
      'amb_calls_d523':rel32(b,0xd8cb)==0xd523,
      'd523_reads_word_1000_arg':b[0xd58e:0xd592]==bytes.fromhex('0fbf4d30'),
      'd523_reads_byte_zero_arg':b[0xd589:0xd58e]==bytes.fromhex('0fbe453450'),
      'd523_calls_1ef44':rel32(b,0xd5a1)==0x1ef44,
      '1ef44_forwards_stack_byte':b[0x1ef93:0x1ef9a]==bytes.fromhex('8b450dc1f81850'),
      '1ef44_calls_1edd7':rel32(b,0x1efac)==0x1edd7,
      'loop_arg_loaded_from_stack':b[0x1f08d:0x1f097]==bytes.fromhex('31c0668b451050ff75f4'),
      'loop_setter':rel32(b,0x1f097)==0x38eee,
      'start_after_loop':rel32(b,0x1f0a2)==0x38bd8,
      'defaults_pan64_setup':b[0x202b1:0x202b8]==bytes.fromhex('c745ec40000000'),
      'defaults_volume64_stack':b[0x202b8:0x202bc]==bytes.fromhex('8b45ec50'),
      'defaults_apply_builder':rel32(b,0x20300)==0x2020b,
      'builder_pan_offset8':b[0x20249:0x20252]==bytes.fromhex('8b45f88b55ec894208'),
      'builder_volume_offset18':b[0x2026d:0x20276]==bytes.fromhex('8b451c8b55ec894218'),
      'pan_setter':rel32(b,0x2031f)==0x38e78,
      'volume_setter':rel32(b,0x20330)==0x38e02,
    }
    bad=[k for k,v in checks.items() if not v]
    if bad: raise SystemExit('v46 invariant failed: '+repr(bad))
    out={
      'schema':'openazrael.ambient_playback_defaults','version':46,'status':'PASS','exe_sha256':sha,'invariants':checks,
      'ambient_callsite':{
        'routine':'0xD7BF -> 0xD523','confidence':'HIGH',
        'constants':{'stack_0x30':1000,'stack_0x34':0},
        'evidence':'0xD8A4..0xD8CB pushes literal 0,1000,0,1,... before 0xD523; 0xD523 reads +0x30 as word and +0x34 as byte.'
      },
      'loop_count':{
        'ambient_argument':0,'confidence':'HIGH',
        'path':'D8A4 literal 0 -> D523 +0x34 -> 1EF44 stack forwarding -> 1EDD7 +0x10 -> AIL_set_sample_loop_count -> AIL_start_sample',
        'semantic_interpretation':'PROBABLE_INFINITE_LOOP','note':'The executable proves the numeric AIL loop-count argument is 0. Infinite-loop meaning is kept PROBABLE here rather than promoted solely from API convention.'
      },
      'sample_defaults':{
        'confidence':'HIGH',
        'pan':64,'volume':64,
        'path':'0x20288 seeds a 36-byte slot through 0x2020B; slot+0x08=64 reaches AIL_set_sample_pan and slot+0x18=64 reaches AIL_set_sample_volume.',
        'unresolved_slot_plus_04':{'value_seeded':0,'callee':'0x3974F','identity':'HOLD'}
      },
      'classic_audio_impact':{
        'ambient_loop_count_numeric':'HIGH','initial_pan_64':'HIGH','initial_volume_64':'HIGH',
        'infinite_loop_semantics':'PROBABLE','0x3974F_identity':'HOLD','exact_attenuation_formula':'HOLD','exact_pan_formula':'HOLD'
      },
      'next':['Bind 0x3974F to its exact Miles diagnostic/API identity without relying only on ordering.','Trace the 1000 argument beyond 0xD523/0x1EF44 and determine its semantic role.','Continue exact 3D attenuation/pan reconstruction, while preserving the newly verified loop/default values in Classic Audio metadata.']
    }
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'PASS','checks':len(checks),'ambient_loop_count':0,'pan_default':64,'volume_default':64},indent=2))
if __name__=='__main__': main()
