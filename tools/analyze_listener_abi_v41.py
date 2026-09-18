#!/usr/bin/env python3
import argparse, hashlib, json, struct
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def u32(d,o): return struct.unpack_from('<I',d,o)[0]
def build_obj1(raw):
    lo=0x37d4c
    if raw[lo:lo+2]!=b'LE': raise SystemExit('validated LE header missing')
    le=raw[lo:]; ot=u32(le,0x40); pm=u32(le,0x48); dp=u32(le,0x80); ps=u32(le,0x28)
    size,base,flags,first,npg,res=struct.unpack_from('<IIIIII',le,ot); b=bytearray(size)
    for lp in range(npg):
        e=le[pm+4*(first-1+lp):pm+4*(first-1+lp)+4]; pn=(e[0]<<16)|(e[1]<<8)|e[2]
        if not pn: continue
        src=lo+dp+(pn-1)*ps; dst=lp*ps; n=min(ps,size-dst,max(0,len(raw)-src)); b[dst:dst+n]=raw[src:src+n]
    return bytes(b)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
    raw=Path(a.exe).read_bytes(); sha=hashlib.sha256(raw).hexdigest(); b=build_obj1(raw)
    checks={
      'exe_hash':sha==EXPECTED,
      'core_ret_24':b[0xd132:0xd135]==bytes.fromhex('c21800'),
      'cache_position_to_227d0':b[0xce07:0xce12]==bytes.fromhex('bfd02702008d751ca5a5a5'),
      'cache_orientation_to_227dc':b[0xce12:0xce1d]==bytes.fromhex('bfdc2702008d7528a5a5a5'),
      'emitter_table_base_227e8':b[0xcdf2:0xcdf9]==bytes.fromhex('c745f8e8270200'),
      'emitter_stride_24':b[0xcfbd:0xcfc1]==bytes.fromhex('8345f818'),
      'emitter_count_7':b[0xcfc4:0xcfcb]==bytes.fromhex('0fb745fc83f807'),
      'distance_uses_emitter_minus_first_xyz':b[0xcf14:0xcf31]==bytes.fromhex('8b45f8d900d8651cd95dd0d94008d86524d95dd8d94004d86520d95dd4'),
      'second_xyz_is_copied_for_direction_math':b[0xcfdd:0xcfe6]==bytes.fromhex('8d7dd08d7528a5a5a5'),
      'direction_y_is_zeroed_before_normalize':b[0xcfe6:0xcff5]==bytes.fromhex('c745d4000000008d45d0e84b2e0200'),
      'frame_call_pushes_position_then_orientation':b[0x161c:0x1634]==bytes.fromhex('8b45ca508b55c6528b5dc2538b4de2518b75de568b7dda57'),
      'sample_start_reuses_cached_listener_state':b[0xd1e1:0xd205]==bytes.fromhex('ff35e4270200ff35e0270200ff35dc270200ff35d8270200ff35d4270200ff35d0270200')
    }
    if not all(checks.values()): raise SystemExit('v41 invariant failed: '+repr(checks))
    out={
      'schema':'openazrael.listener_3d_abi','version':41,'exe_sha256':sha,'status':'PASS','invariants':checks,
      'correction_to_v40':{
        'previous':'The six arguments to 0xCDE1 were described as two XYZ position triples (listener + source/emitter).',
        'corrected':'The first triple is listener position. The second triple is listener orientation/forward-direction state used by angular/pan math. Source positions live in the 7-entry emitter table beginning at 0x227E8.',
        'confidence':'HIGH'
      },
      'abi':{
        'routine':'0xCDE1','stack_cleanup_bytes':24,
        'first_xyz':{'stack':'[EBP+1C..24]','cache':'0x227D0..0x227D8','role':'listener_position','confidence':'HIGH'},
        'second_xyz':{'stack':'[EBP+28..30]','cache':'0x227DC..0x227E4','role':'listener_orientation_or_forward_vector','confidence':'HIGH'},
        'source_positions':{'table_base':'0x227E8','record_stride':24,'record_count':7,'xyz_offsets':[0,4,8],'sample_handle_or_id_offset':'0x0C','role':'3D emitter records','confidence':'HIGH'}
      },
      'dataflow':[
        '0xCDE1 copies first XYZ to 0x227D0..0x227D8 and second XYZ to 0x227DC..0x227E4.',
        'For each active emitter record, distance vector = emitter.xyz - first_xyz; helper 0x2FCDC computes its magnitude.',
        'Second XYZ is copied to a temporary vector, its Y component is forced to zero, and it is normalized/converted into angular state used by the pan path.',
        'Sample-start callers 0xD208/0xD3F7/0xD5D7 reuse the cached six listener-state dwords when immediately spatializing a newly started sample.'
      ],
      'implications':{
        'global_227d0_227e4':'listener-state cache, not an independently initialized pair of source/listener positions',
        'ambient_source_position':'comes from emitter table records, consistent with the seven AMB*.SND placements in the demo',
        'classic_renderer':'should model listener position + listener forward/orientation separately from emitter XYZ'
      },
      'confidence':{'listener_position_abi':'HIGH','listener_orientation_abi':'HIGH','emitter_table_identity':'HIGH','exact_axis_sign_for_forward':'HOLD','exact_pan_formula':'HOLD','numeric_constants':'HOLD'},
      'next':['Trace writes/population of the 0x227E8 emitter table back to AMB*.SND loading.','Resolve the exact semantic/sign convention of the second XYZ vector from frame producer 0x2ACE8/0x28C98.','Then reconstruct angular-to-pan mapping while keeping unresolved numeric constants on HOLD.']
    }
    Path(a.out).write_text(json.dumps(out,indent=2)+"\n",encoding='utf8')
    print(json.dumps({'status':'PASS','listener_position':'HIGH','listener_orientation':'HIGH','emitter_table':'HIGH','all_invariants':True},indent=2))
if __name__=='__main__': main()
