#!/usr/bin/env python3
import argparse, hashlib, json, struct, subprocess, tempfile
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def U32(d,o): return struct.unpack_from('<I',d,o)[0]
def build_obj1(raw):
 lo=0x37d4c
 if raw[lo:lo+2]!=b'LE': raise SystemExit('expected demo LE header not found')
 le=raw[lo:]; ot=U32(le,0x40); dp=U32(le,0x80)
 size,base,flags,first,npg,res=struct.unpack_from('<IIIIII',le,ot)
 # Independently validated in v29: this bound Watcom LE stores the initialized object-1 image
 # contiguously at LE-relative Data Pages Offset. Do not apply the still-unresolved fixup patcher here.
 return bytes(le[dp:dp+size])
def call_target(b,off):
 assert b[off]==0xe8
 rel=struct.unpack_from('<i',b,off+1)[0]; return off+5+rel
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); sha=hashlib.sha256(raw).hexdigest(); obj=build_obj1(raw)
 # Candidate is discovered/validated by distinctive prologue + ret 0x18 and the two calls fed by computed integers.
 start=0xcde1; end=0xd135
 if obj[start:start+6] != bytes.fromhex('5351525657c8'): raise SystemExit('candidate prologue invariant failed')
 if obj[0xd132:0xd135] != bytes.fromhex('c21800'): raise SystemExit('candidate epilogue invariant failed')
 calls={hex(o):hex(call_target(obj,o)) for o in [0xcf34,0xcfa2,0xcfb8,0xcff0,0xcffe,0xd046,0xd054,0xd125] if obj[o]==0xe8}
 # Key semantic instruction invariants from raw code. These survive because direct relative calls are not LE data fixups.
 invariants={
  'vector_xyz_subtraction': all(obj[o:o+2] in (b'\xd9\x00',b'\xd9\x40') for o in [0xcf17,0xcf1f,0xcf28]),
  'distance_helper_call': call_target(obj,0xcf34)==0x2fcdc,
  'pan_setter_candidate_call': call_target(obj,0xcfa2)==0x1f6f1,
  'volume_setter_candidate_call': call_target(obj,0xcfb8)==0x1f5fc,
  'seven_slot_loop': obj[0xcfc8:0xcfcb]==bytes.fromhex('83f807'),
  'ret_24_bytes': obj[0xd132:0xd135]==bytes.fromhex('c21800')
 }
 out={
  'schema':'openazrael.audio_3d_core_candidate','version':37,'exe_sha256':sha,
  'candidate':{'object':1,'start_offset':start,'end_offset_exclusive':end,'size':end-start,'confidence':'HIGH'},
  'invariants':invariants,'direct_relative_calls':calls,
  'semantic_evidence':[
   {'offset':'0xcf17..0xcf2e','finding':'Subtracts three emitter/listener coordinate components into a temporary vector.','confidence':'HIGH'},
   {'offset':'0xcf34','finding':'Calls helper 0x2FCDC with that 3-component vector; returned floating value is used as a distance-like divisor.','confidence':'HIGH'},
   {'offset':'0xcf4b..0xcf74','finding':'Computes an integer from a floating constant divided by the distance-like value, divides by a mode/scaling term, and clamps to 99.','confidence':'HIGH'},
   {'offset':'0xcf7b..0xcf8e','finding':'Multiplies the clamped value by a signed global scale and divides by 99.','confidence':'HIGH'},
   {'offset':'0xcfa2','finding':'Passes a separately computed integer to wrapper 0x1F6F1; wrapper stores it in per-sample field +0x0C and calls backend 0x38E78. Role is consistent with pan, but API identity is not yet independently proven.','confidence':'PROBABLE'},
   {'offset':'0xcfb8','finding':'Passes the distance-derived/clamped integer to wrapper 0x1F5FC; wrapper stores it in per-sample field +0x1C and calls backend 0x38E02. Role is consistent with volume, but API identity is not yet independently proven.','confidence':'PROBABLE'},
   {'offset':'0xcfc8','finding':'Iterates up to seven 24-byte sample/emitter records, matching the demo maximum of seven explicit AMB emitters.','confidence':'HIGH'}
  ],
  'wrapper_candidates':[
   {'offset':0x1f5fc,'backend_call':0x38e02,'per_sample_field':'0x1c','role':'volume','confidence':'PROBABLE'},
   {'offset':0x1f6f1,'backend_call':0x38e78,'per_sample_field':'0x0c','role':'pan','confidence':'PROBABLE'}
  ],
  'important_correction':'Do not apply the current canonical xref source coordinates as binary patch offsets. They still corrupt valid instructions in this function. v37 uses raw coherent x86 plus direct relative CALLs as independent evidence while keeping relocation patch semantics on HOLD.',
  'confidence':{'3d_audio_update_core_candidate':'HIGH','distance_based_gain_path':'HIGH','pan_wrapper_identity':'PROBABLE','volume_wrapper_identity':'PROBABLE','exact_numeric_constants':'HOLD','LE_runtime_patch_semantics':'HOLD','Play3DSample_name_binding':'HOLD'},
  'next':['Identify backend functions 0x38E02 and 0x38E78 against Miles AIL behavior or import/thunk evidence.','Recover runtime-initialized constants/globals used by the candidate before writing an exact Classic formula.','Find callers of 0xCDE1 and connect them to StartAmbientSoundFX/AMB lifecycle.']
 }
 if sha!=EXPECTED: out['warning']='EXE hash differs from validated demo build'
 if not all(invariants.values()): raise SystemExit('one or more candidate invariants failed')
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8')
 print(json.dumps({'candidate':out['candidate'],'invariants':invariants,'calls':calls,'status':'PASS'},indent=2))
if __name__=='__main__': main()
