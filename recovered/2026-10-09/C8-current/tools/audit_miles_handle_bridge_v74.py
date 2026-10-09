#!/usr/bin/env python3
import argparse, hashlib, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from analyze_ambient_loader_v42 import build_obj1, EXPECTED

def rel32_target(b, call):
    return call+5+int.from_bytes(b[call+1:call+5],'little',signed=True)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
    raw=Path(a.exe).read_bytes(); b=build_obj1(raw); sha=hashlib.sha256(raw).hexdigest()
    checks={
      'exe_hash': sha==EXPECTED,
      'd523_stores_returned_pool_index_in_emitter': b[0xd5a6:0xd5b0]==bytes.fromhex('8b55f4668982f4270200'),
      'volume_reads_emitter_pool_index': b[0xcf91:0xcf98]==bytes.fromhex('8b55f80fbf520c'),
      'volume_wrapper_called': rel32_target(b,0xcfb8)==0x1f5fc,
      'pan_wrapper_called': rel32_target(b,0xcfa2)==0x1f6f1,
      'volume_wrapper_pool_stride_36': b[0x1f657:0x1f683]==bytes.fromhex('8b45f6c1f8106bc0248b55f001c28b45f489421c807dfc00751aff75f48b45f6c1f8106bc0240345f0ff7004'),
      'volume_wrapper_calls_miles_handle_at_pool_plus4': rel32_target(b,0x1f683)==0x38e02,
      'pan_wrapper_pool_stride_36': b[0x1f774:0x1f7a0]==bytes.fromhex('8b45f6c1f8106bc0248b55f001c28b45f489420c807dfc00751aff75f48b45f6c1f8106bc0240345f0ff7004'),
      'pan_wrapper_calls_miles_handle_at_pool_plus4': rel32_target(b,0x1f7a0)==0x38e78,
      'sample_start_selects_pool_handle_plus4': b[0x1ee66:0x1ee78]==bytes.fromhex('8b45e2c1f8106bc0240345f08b40048945e0'),
      'sample_start_passes_same_handle_to_status': rel32_target(b,0x1ee7b)==0x38f64,
      'lower_start_passes_handle_to_init': b[0x1efe2:0x1eff8]==bytes.fromhex('ff75f4e85b9c010083c404ff75f4e86c99010083c404'),
      'lower_start_calls_init': rel32_target(b,0x1eff0)==0x38961,
      'lower_start_file_uses_same_handle': b[0x1f047:0x1f053]==bytes.fromhex('8b45d450ff75f4e87b990100'),
      'lower_start_calls_set_sample_file': rel32_target(b,0x1f04e)==0x389ce,
      'lower_start_calls_start_sample': rel32_target(b,0x1f0a2)==0x38bd8,
    }
    bad=[k for k,v in checks.items() if not v]
    if bad: raise SystemExit('v74 invariant failed: '+repr(bad))
    out={
      'schema':'openazrael.miles_handle_bridge','version':74,'status':'PASS','exe_sha256':sha,'invariants':checks,
      'result':{
        'emitter_field_plus_0c':'sample_pool_index (signed 16-bit)',
        'sample_pool_record_stride_bytes':36,
        'sample_pool_miles_handle_offset':4,
        'mapping':'emitter.slot -> stored sample_pool_index -> audio_manager + index*36 -> Miles sample handle at +4 -> AIL_set_sample_pan/volume',
        'confidence':'HIGH'
      },
      'correction':'Earlier shorthand sometimes called emitter+0x0C a sample handle. v74 narrows this: it is an engine sample-pool index; the actual Miles handle is loaded from pool[index]+0x04 before AIL calls.',
      'runtime_capture_consequence':'A Miles debug trace handle can be matched to the engine sample pool once a pool-index/handle snapshot or independently proven pool allocation ordering is available. v74 does not infer that ordering from trace chronology.',
      'hold':['runtime sample-pool base address/value under DOS','pool-index -> concrete handle values in an observed run','automatic handle -> AMB filename/slot mapping without an independent runtime anchor']
    }
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'PASS','checks':len(checks),'bridge':'engine sample_pool_index -> pool[index]+4 Miles handle','confidence':'HIGH'},indent=2))
if __name__=='__main__': main()
