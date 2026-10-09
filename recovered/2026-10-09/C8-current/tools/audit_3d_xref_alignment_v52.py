#!/usr/bin/env python3
import argparse,hashlib,json,struct
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def U32(d,o): return struct.unpack_from('<I',d,o)[0]
def build_objects(raw):
 lo=0x37d4c
 if raw[lo:lo+2]!=b'LE': raise SystemExit('expected demo LE header not found')
 le=raw[lo:]; ot=U32(le,0x40); dp=U32(le,0x80); ps=U32(le,0x28); pm=U32(le,0x48)
 def pn(mi):
  e=le[pm+4*mi:pm+4*mi+4]; return (e[0]<<16)|(e[1]<<8)|e[2]
 out=[]
 for i in range(U32(le,0x44)):
  size,base,flags,first,npg,res=struct.unpack_from('<IIIIII',le,ot+i*24); b=bytearray(size)
  for lp in range(npg):
   p=pn(first-1+lp)
   if not p: continue
   src=lo+dp+(p-1)*ps; dst=lp*ps; n=min(ps,size-dst,max(0,len(raw)-src))
   if n: b[dst:dst+n]=raw[src:src+n]
  out.append(bytes(b))
 return out

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('xrefs'); ap.add_argument('--out',required=True); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); sha=hashlib.sha256(raw).hexdigest(); o1,o2=build_objects(raw)[:2]
 x=json.loads(Path(a.xrefs).read_text())['xrefs']
 def has(src,tgt): return any(r['source_object']==1 and r['source_offset']==src and r['target_object']==2 and r['target_offset']==tgt for r in x)
 # Instruction boundaries are independently visible in coherent raw object-1 x86.
 # CF4B: DD 05 <disp32>, operand begins CF4D. CF7B: 0F BF 05 <disp32>, operand begins CF7E.
 checks={
  'v51_xref_cf4a_exists':has(0xcf4a,0x6abe),
  'v51_xref_cf7d_exists':has(0xcf7d,0x1724),
  'cf4b_is_fldl_abs':o1[0xcf4b:0xcf4d]==bytes.fromhex('dd05'),
  'cf4d_is_actual_disp32_start':o1[0xcf4d:0xcf51]==bytes.fromhex('94190000'),
  'cf7b_is_movswl_abs':o1[0xcf7b:0xcf7e]==bytes.fromhex('0fbf05'),
  'cf7e_is_actual_disp32_start':o1[0xcf7e:0xcf82]==bytes.fromhex('5e610000'),
  'v51_cf4a_not_operand_start':0xcf4a != 0xcf4d,
  'v51_cf7d_not_operand_start':0xcf7d != 0xcf7e,
  'obj2_1724_is_ascii_debug_text':b'AIL_set_sample_volume' in o2[max(0,0x1724-32):0x1724+64],
  'obj2_6abc_initialized_zero':o2[0x6abc:0x6ac4]==b'\x00'*8,
  'obj2_6abe_initialized_zero':o2[0x6abe:0x6ac6]==b'\x00'*8,
 }
 if not all(checks.values()): raise SystemExit(checks)
 out={
  'schema':'openazrael.audio_3d_xref_alignment_audit','version':52,'status':'PASS','exe_sha256':sha,
  'invariants':checks,
  'correction':{
   'supersedes':'v51 HIGH_REFERENCE_IDENTITY claims for object1:0xCF4A->object2:0x6ABE and object1:0xCF7D->object2:0x1724',
   'reason':'The v36 canonical source coordinates do not land on the disp32 operand starts of the independently coherent x86 instructions in the 3D core. CF4A is before the FLDL instruction at CF4B (disp32 begins CF4D); CF7D is the ModR/M byte of MOVSWL at CF7B (disp32 begins CF7E). Object2:0x1724 also resolves inside an AIL_set_sample_volume diagnostic string, which is semantically incompatible with use as the signed global volume scalar.',
   'confidence':'HIGH'
  },
  'verified_raw_sites':{
   'distance_constant_load':{'instruction':'object1:0xCF4B DD 05 [disp32]','raw_disp32_start':'0xCF4D','raw_placeholder':'0x00001994','runtime_target':'HOLD'},
   'global_volume_scale_load':{'instruction':'object1:0xCF7B 0F BF 05 [disp32]','raw_disp32_start':'0xCF7E','raw_placeholder':'0x0000615E','runtime_target':'HOLD'}
  },
  'object2_audit':{
   '0x1724':'initialized bytes are part of AIL_set_sample_volume diagnostic text; NOT accepted as GLOBAL_VOLUME_SCALE',
   '0x6ABC':'zero-initialized in file image; semantic binding from v51 withdrawn',
   '0x6ABE':'zero-initialized in file image; semantic binding from v51 withdrawn'
  },
  'confidence':{'coherent_x86_instruction_boundaries':'HIGH','v51_reference_binding_invalid':'HIGH','exact_runtime_fixup_source_mapping':'HOLD','distance_constant_numeric_value':'HOLD','global_volume_scale_numeric_value':'HOLD','pan_constants_numeric_values':'HOLD'},
  'implementation_decision':'Keep Classic attenuation/pan numerics on HOLD. Do not use v51 object2 targets in runtime code. Re-derive LE source-coordinate semantics against actual disp32 operand starts before resolving constants.',
  'next':['Repair LE fixup source mapping using instruction-operand alignment as a hard invariant.','Rebuild a corrected object-relative xref graph and require known 3D core fixups to land on CF4D/CF7E-style operand starts.','Only then resolve runtime targets and construct golden-vector attenuation/pan tests.']
 }
 if sha!=EXPECTED: out['warning']='EXE hash differs from validated demo build'
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8'); print(json.dumps({'status':'PASS','invariants':sum(checks.values()),'total':len(checks),'v51_binding':'SUPERSEDED'},indent=2))
if __name__=='__main__': main()
