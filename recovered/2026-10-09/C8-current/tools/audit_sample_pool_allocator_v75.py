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
      'auto_select_branch_tests_requested_index_minus1':b[0x1ee32:0x1ee41]==bytes.fromhex('8b45fac1f81083f8ff0f8584000000'),
      'scan_counter_initialized_zero':b[0x1ee41:0x1ee4d]==bytes.fromhex('c745e400000000eb03ff45e4'),
      'scan_bound_uses_manager_sample_count':b[0x1ee4d:0x1ee64]==bytes.fromhex('8b45f0668b80a601000025ffff00008b55e2c1fa1039c2'),
      'scan_record_stride_36_and_handle_plus4':b[0x1ee66:0x1ee78]==bytes.fromhex('8b45e2c1f8106bc0240345f08b40048945e0'),
      'scan_calls_AIL_sample_status':rel32(b,0x1ee7b)==0x38f64,
      'busy_test_is_status_bit_0x04':b[0x1ee80:0x1ee87]==bytes.fromhex('83c404a804752b'),
      'first_nonbusy_slot_captured':b[0x1ee87:0x1ee8e]==bytes.fromhex('8b45e4668945fc'),
      'first_nonbusy_slot_immediately_started':rel32(b,0x1eea4)==0x1efbf,
      'successful_scan_exits_without_increment':b[0x1eea9:0x1eeb2]==bytes.fromhex('c745e800000000eb02'),
      'busy_slot_loops_to_increment':b[0x1eeb2:0x1eeb4]==bytes.fromhex('eb96'),
      'exhausted_auto_scan_fallback_index_1':b[0x1eeb4:0x1eec5]==bytes.fromhex('8b45fac1f81083f8ff750666c745fc0100'),
      'explicit_index_path_skips_allocator_scan':b[0x1eec5:0x1eede]==bytes.fromhex('66837de80074678b45fac1f8106bc0240345f08b40048945e0'),
    }
    bad=[k for k,v in checks.items() if not v]
    if bad: raise SystemExit('v75 invariant failed: '+repr(bad))
    out={
      'schema':'openazrael.sample_pool_allocator','version':75,'status':'PASS','exe_sha256':sha,'invariants':checks,
      'result':{
        'automatic_request_sentinel':-1,
        'allocation_policy':'scan sample-pool indices from 0 upward; query AIL_sample_status(pool[index].miles_handle); select the first slot whose status does not have bit 0x04 set; immediately start it and stop scanning',
        'record_stride_bytes':36,'miles_handle_offset':4,'busy_status_mask':'0x04','confidence':'HIGH'
      },
      'important_boundary':{
        'deterministic_index_from_clean_initial_state':'HOLD',
        'reason':'The allocator policy is now closed, but a concrete AMB filename -> pool index still depends on the runtime status of lower-numbered slots when each AMB sample starts. Other sounds may already occupy slots, and v75 does not assume a pristine pool.',
        'trace_order_is_not_identity':'Retained: chronological Miles log order alone is not used as a filename/slot proof.'
      },
      'runtime_capture_consequence':'A debugger snapshot of pool[index]+4 handles plus status, taken when AMB sources are active, is sufficient to map Miles trace handles to engine pool indices without patching R.EXE. Combined with emitter+0x0C from v74, that closes emitter slot -> pool index -> Miles handle at runtime.',
      'next':['Find whether Miles debug output exposes enough status/allocation context to recover the selected pool index without a debugger.','Otherwise define the minimal DOSBox debugger watch/snapshot addresses after resolving the runtime audio-manager base.','Join that observation with v74 emitter+0x0C and v71 capture records; only independently observed mappings become OBSERVED.']
    }
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'PASS','checks':len(checks),'allocator':'FIRST_NONBUSY_FROM_INDEX_0','busy_mask':'0x04','confidence':'HIGH'},indent=2))
if __name__=='__main__': main()
