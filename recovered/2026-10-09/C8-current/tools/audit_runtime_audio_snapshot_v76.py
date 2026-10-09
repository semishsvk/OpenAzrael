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
      'manager_allocation_size_0x364': b[0x2015f:0x20169]==bytes.fromhex('b864030000e8970a0000'),
      'manager_constructor_called': rel32(b,0x2017b)==0x1eb68,
      'manager_pointer_stored_global_0x41d9c': b[0x20191:0x20199]==bytes.fromhex('8b45f8a39c1d0400'),
      'init_requested_count_8': b[0x20199:0x201a0]==bytes.fromhex('31dbba08000000'),
      'manager_pointer_reloaded_for_init': b[0x201a0:0x201a5]==bytes.fromhex('a19c1d0400'),
      'manager_init_called': rel32(b,0x201a5)==0x1ec3a,
      'init_capacity_field_set_8': b[0x1ec56:0x1ec62]==bytes.fromhex('8b45f466c780a40100000800'),
      'active_count_copied_from_capacity': b[0x1ec62:0x1ec76]==bytes.fromhex('8b45f4668b90a40100008b45f4668990a6010000'),
      'pool_record_handle_store_stride36_plus4': b[0x1ecea:0x1ecf9]==bytes.fromhex('31c0668b45ec6bc0240345f4895004'),
      'allocator_reads_same_count_field': b[0x1ee4d:0x1ee64]==bytes.fromhex('8b45f0668b80a601000025ffff00008b55e2c1fa1039c2'),
      'allocator_reads_same_handle_stride36_plus4': b[0x1ee66:0x1ee78]==bytes.fromhex('8b45e2c1f8106bc0240345f08b40048945e0'),
    }
    bad=[k for k,v in checks.items() if not v]
    if bad: raise SystemExit('v76 invariant failed: '+repr(bad))
    out={
      'schema':'openazrael.runtime_audio_snapshot','version':76,'status':'PASS','exe_sha256':sha,'invariants':checks,
      'result':{
        'audio_manager_global_operand':'0x41D9C','manager_allocation_bytes':0x364,
        'sample_pool_capacity':8,'sample_pool_active_count_offset':'0x1A6','sample_pool_capacity_offset':'0x1A4',
        'sample_record_stride_bytes':36,'miles_handle_offset':4,
        'emitter_table_operand':'0x227E8','emitter_record_stride_bytes':24,'emitter_record_count':7,'emitter_pool_index_offset':'0x0C',
        'confidence':'HIGH'
      },
      'runtime_snapshot_recipe':[
        'Resolve/read the runtime pointer stored by the instruction whose bound operand is 0x41D9C; do not assume a DOS linear address from this static operand.',
        'Dump 0x364 bytes beginning at the resulting audio-manager pointer. The first eight 36-byte records contain Miles handles at +0x04; count/capacity are at +0x1A6/+0x1A4.',
        'Separately dump the seven 24-byte 3D emitter records rooted at the runtime-resolved emitter-table operand corresponding to 0x227E8.',
        'For each active emitter, read signed pool index at +0x0C, then join to manager[pool_index*36+4] to recover the exact Miles handle.',
        'Join that handle to AIL_DEBUG pan/volume lines from v72-v73. Only runtime-observed joins may be labelled OBSERVED.'
      ],
      'boundary':{
        'static_operand_equals_runtime_linear_address':'HOLD',
        'reason':'LE relocation/source mapping remains quarantined. v76 closes the data structure and pointer provenance, not the final DOS linear address after loading.',
        'actual_runtime_values':'UNOBSERVED'
      }
    }
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'PASS','checks':len(checks),'pool_capacity':8,'manager_global_operand':'0x41D9C','manager_size':'0x364','confidence':'HIGH'},indent=2))
if __name__=='__main__': main()
