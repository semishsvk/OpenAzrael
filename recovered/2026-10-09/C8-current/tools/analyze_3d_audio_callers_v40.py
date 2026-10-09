#!/usr/bin/env python3
import argparse, hashlib, json, struct
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def u32(d,o): return struct.unpack_from('<I',d,o)[0]
def build_obj1(raw):
    lo=0x37d4c
    if raw[lo:lo+2]!=b'LE': raise SystemExit('validated LE header missing')
    le=raw[lo:]; ot=u32(le,0x40); pm=u32(le,0x48); dp=u32(le,0x80); ps=u32(le,0x28)
    size,base,flags,first,npg,res=struct.unpack_from('<IIIIII',le,ot)
    b=bytearray(size)
    for lp in range(npg):
        e=le[pm+4*(first-1+lp):pm+4*(first-1+lp)+4]; pn=(e[0]<<16)|(e[1]<<8)|e[2]
        if not pn: continue
        src=lo+dp+(pn-1)*ps; dst=lp*ps; n=min(ps,size-dst,max(0,len(raw)-src)); b[dst:dst+n]=raw[src:src+n]
    return bytes(b)
def call_target(b,o): return o+5+struct.unpack_from('<i',b,o+1)[0] if b[o]==0xe8 else None
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
    raw=Path(a.exe).read_bytes(); sha=hashlib.sha256(raw).hexdigest(); b=build_obj1(raw); target=0xcde1
    hits=[i for i in range(len(b)-5) if b[i]==0xe8 and call_target(b,i)==target]
    expected=[0x1639,0xd208,0xd3f7,0xd5d7]
    checks={
      'exact_four_direct_callers':hits==expected,
      'core_ret_24':b[0xd132:0xd135]==bytes.fromhex('c21800'),
      'frame_caller_pushes_six_xyz_dwords':b[0x161c:0x1634]==bytes.fromhex('8b45ca508b55c6528b5dc2538b4de2518b75de568b7dda57'),
      'frame_caller_sets_context_eax':b[0x1634:0x1639]==bytes.fromhex('b8781c0100'),
      'start_caller_d208_pushes_two_xyz_globals':b[0xd1e1:0xd205]==bytes.fromhex('ff35e4270200ff35e0270200ff35dc270200ff35d8270200ff35d4270200ff35d0270200'),
      'start_caller_d3f7_pushes_two_xyz_globals':b[0xd3d0:0xd3f4]==bytes.fromhex('ff35e4270200ff35e0270200ff35dc270200ff35d8270200ff35d4270200ff35d0270200'),
      'start_caller_d5d7_pushes_two_xyz_globals':b[0xd5b0:0xd5d4]==bytes.fromhex('ff35e4270200ff35e0270200ff35dc270200ff35d8270200ff35d4270200ff35d0270200'),
      'd208_preceded_by_sample_start_wrapper':call_target(b,0xd1d2)==0x1ef44,
      'd3f7_preceded_by_sample_start_wrapper':call_target(b,0xd3c1)==0x1ef44,
      'd5d7_preceded_by_sample_start_wrapper':call_target(b,0xd5a1)==0x1ef44,
    }
    if sha!=EXPECTED: raise SystemExit('unexpected R.EXE hash')
    if not all(checks.values()): raise SystemExit('v40 invariant failed: '+repr(checks))
    out={
      'schema':'openazrael.audio_3d_callers','version':40,'exe_sha256':sha,'status':'PASS','invariants':checks,
      'core':{'offset':'0xCDE1','calling_convention_evidence':'RET 24 consumes exactly six 32-bit stack arguments','interpretation':'two XYZ triples','confidence':'HIGH'},
      'direct_callers':[
       {'call_site':'0x1639','role':'continuous/frame spatial update','evidence':'Pushes six local dwords arranged as two 3-component vectors immediately before call; no sample-start call in the local sequence.','confidence':'HIGH'},
       {'call_site':'0xD208','role':'sample-start spatial initialization/update','evidence':'Calls 0x1EF44 sample-start wrapper, stores returned sample handle, pushes globals 0x227D0..0x227E4 (six dwords / two XYZ triples), then calls 0xCDE1.','confidence':'HIGH'},
       {'call_site':'0xD3F7','role':'sample-start spatial initialization/update','evidence':'Same sample-start + six-global-XYZ + 0xCDE1 pattern as 0xD208.','confidence':'HIGH'},
       {'call_site':'0xD5D7','role':'sample-start spatial initialization/update','evidence':'Same sample-start + six-global-XYZ + 0xCDE1 pattern; afterwards stores callback/state fields in the 24-byte emitter record.','confidence':'HIGH'}],
      'major_finding':{'finding':'0xCDE1 is not merely a math-like candidate: its caller topology binds it to both sample creation and continuous updates, always with two XYZ triples. This is strong structural evidence for the original 3D sample spatialization/update routine.','confidence':'HIGH'},
      'constant_recovery_correction':{'finding':'The object-relative xref metadata cannot yet be used to resolve the apparent 0x1954..0x1994/0x615E operands. In this region its source coordinates do not consistently coincide with x86 operand starts, and one attempted mapping for the volume-scale operand targets diagnostic ASCII rather than a numeric global.','impact':'Do not infer K_DISTANCE, angular constants, or GLOBAL_VOLUME_SCALE from canonical_xrefs_v36. Recover them from initialization/runtime state or a corrected relocation-source mapping.','confidence':'HIGH'},
      'confidence':{'3d_spatial_update_routine':'HIGH','two_xyz_argument_layout':'HIGH','sample_start_binding':'HIGH','continuous_update_binding':'HIGH','exact_constants':'HOLD','exact_attenuation_formula_numeric':'HOLD'},
      'next':['Trace initialization of the six globals 0x227D0..0x227E4 and the listener/source vector producers.','Recover runtime constants through initializer writes or dynamic-equivalent state reconstruction, not current xref patch coordinates.','Use the confirmed two-XYZ ABI to implement a Classic forensic harness with symbolic constants and golden structural tests.']}
    Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8')
    print(json.dumps({'status':'PASS','callers':[hex(x) for x in hits],'all_invariants':all(checks.values()),'core_confidence':'HIGH'},indent=2))
if __name__=='__main__': main()
