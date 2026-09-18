#!/usr/bin/env python3
import argparse,json,hashlib,struct
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
U32=lambda d,o:struct.unpack_from('<I',d,o)[0]
def build_objects(raw):
 lo=0x37d4c; le=raw[lo:]; ot=U32(le,0x40); dp=U32(le,0x80); ps=U32(le,0x28); pm=U32(le,0x48)
 def pn(mi):
  e=le[pm+4*mi:pm+4*mi+4]; return (e[0]<<16)|(e[1]<<8)|e[2]
 out=[]
 for i in range(U32(le,0x44)):
  size,base,flags,first,npg,res=struct.unpack_from('<IIIIII',le,ot+i*24); b=bytearray(size)
  for lp in range(npg):
   p=pn(first-1+lp)
   if p:
    src=lo+dp+(p-1)*ps; dst=lp*ps; n=min(ps,size-dst,max(0,len(raw)-src)); b[dst:dst+n]=raw[src:src+n]
  out.append(bytes(b))
 return out

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('xrefs'); ap.add_argument('--out',required=True); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); sha=hashlib.sha256(raw).hexdigest(); o1,o2=build_objects(raw)[:2]; x=json.loads(Path(a.xrefs).read_text())['xrefs']
 def hit(s,t): return any(r['source_object']==1 and r['source_offset']==s and r['target_object']==2 and r['target_offset']==t for r in x)
 # Independently decoded x86 operand starts in the 3D core. These are raw/bound-image facts, not fixup-derived.
 sites={
  'distance_scale_load':(0xcf4b,0xcf4d,'DD 05 <disp32>','0x00001994'),
  'global_volume_word_load':(0xcf7b,0xcf7e,'0F BF 05 <disp32>','0x0000615E'),
  'pan_mul_a':(0xd003,0xd005,'DC 0D <disp32>','0x00001954'),
  'pan_div_a':(0xd009,0xd00b,'DC 35 <disp32>','0x0000195C'),
  'pan_bias_a':(0xd01c,0xd01e,'DD 05 <disp32>','0x00001964'),
  'pan_mul_b':(0xd059,0xd05b,'DC 0D <disp32>','0x00001954'),
  'pan_div_b':(0xd05f,0xd061,'DC 35 <disp32>','0x0000195C'),
  'pan_bias_b':(0xd072,0xd074,'DD 05 <disp32>','0x00001964'),
 }
 # Known v36 graph records around two sites are demonstrably not operand aligned / semantically plausible.
 checks={
  'v36_has_bad_cf4a_binding':hit(0xcf4a,0x6abe),
  'v36_has_bad_cf7d_binding':hit(0xcf7d,0x1724),
  'cf4d_operand_bytes':o1[0xcf4d:0xcf51]==bytes.fromhex('94190000'),
  'cf7e_operand_bytes':o1[0xcf7e:0xcf82]==bytes.fromhex('5e610000'),
  'obj2_1724_is_diagnostic_ascii':b'AIL_set_sample_volume' in o2[0x1700:0x1760],
 }
 if not all(checks.values()): raise SystemExit(checks)
 out={'schema':'openazrael.fixup_graph_quarantine','version':53,'status':'PASS','exe_sha256':sha,'invariants':checks,
 'decision':{'canonical_object_relative_xrefs_v36':'QUARANTINED_FOR_OPERAND_LEVEL_SEMANTICS','structural_fixup_inventory':'RETAINED','cross_page_deduplication':'RETAINED','runtime_target_binding':'HOLD'},
 'reason':['v52 proved two high-value v36 source coordinates do not land on actual disp32 starts in coherent x86.','One alleged target resolves inside diagnostic ASCII, independently falsifying semantic use of that binding.','Therefore v36 remains useful as a structural/deduplicated fixup corpus, but MUST NOT be used to bind 3D-core operands to runtime constants or APIs.'],
 'verified_raw_3d_operand_manifest':{k:{'instruction_start':hex(i),'disp32_start':hex(d),'encoding':e,'raw_unrelocated_value':v,'runtime_target':'HOLD'} for k,(i,d,e,v) in sites.items()},
 'confidence':{'raw_x86_operand_sites':'HIGH','v36_operand_semantics_invalid':'HIGH','structural_fixup_count':'HIGH','runtime_target_mapping':'HOLD','numeric_3d_constants':'HOLD'},
 'next':['Bypass the quarantined graph for Classic Audio numerics. Recover constants from a trustworthy relocated runtime image, initialization writes, or an independently validated LE loader.','Use the raw operand manifest as hard anchors: any future relocation model must resolve these exact disp32 starts, not nearby instruction bytes.','Only after that create attenuation/pan golden vectors.']}
 if sha!=EXPECTED: out['warning']='EXE hash differs from validated demo build'
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8')
 print(json.dumps({'status':'PASS','invariants':sum(checks.values()),'total':len(checks),'v36_semantics':'QUARANTINED','raw_3d_operands':len(sites)},indent=2))
if __name__=='__main__': main()
