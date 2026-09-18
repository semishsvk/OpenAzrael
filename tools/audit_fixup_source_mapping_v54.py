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
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('fixups'); ap.add_argument('--out',required=True); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); sha=hashlib.sha256(raw).hexdigest(); o1=build_objects(raw)[0]
 recs=json.loads(Path(a.fixups).read_text())['records']
 src={r['source_offset']:r for r in recs if r.get('source_object')==1 and r.get('source_offset') is not None}
 anchors={
  0xcf4d:'94190000',0xcf7e:'5e610000',0xd005:'54190000',0xd00b:'5c190000',0xd01e:'64190000',0xd05b:'54190000',0xd061:'5c190000',0xd074:'64190000'}
 exact={hex(k): k in src for k in anchors}
 bytes_ok={hex(k):o1[k:k+4].hex()==v for k,v in anchors.items()}
 neighborhood=[r for r in recs if r.get('source_object')==1 and 0xcf30<=r.get('source_offset',-1)<=0xd090]
 # These are independently decoded instruction spans where a type-7 absolute relocation would be plausible only at disp32 starts.
 checks={
  'all_anchor_bytes_match':all(bytes_ok.values()),
  'zero_exact_fixups_on_8_known_disp32_starts':not any(exact.values()),
  'legacy_fixups_dense_in_same_code_window':len(neighborhood)>=25,
  'legacy_cf4a_present':0xcf4a in src,
  'legacy_cf7d_present':0xcf7d in src,
 }
 if not all(checks.values()): raise SystemExit(checks)
 out={'schema':'openazrael.fixup_source_mapping_audit','version':54,'status':'PASS','exe_sha256':sha,'invariants':checks,
 'verified_operand_anchors':{hex(k):{'raw_bytes':o1[k:k+4].hex(),'expected':v,'legacy_fixup_exact_match':exact[hex(k)]} for k,v in anchors.items()},
 'legacy_window':{'range':'object1:0xCF30..0xD090','record_count':len(neighborhood),'source_offsets':[hex(r['source_offset']) for r in neighborhood]},
 'correction':{'decision':'QUARANTINE_LEGACY_FIXUP_SOURCE_COORDINATES_FOR_INSTRUCTION_BINDING','supersedes':['v27 confidence.fixup_source_coordinates=HIGH when used as instruction operands','v30 broad operand-alignment confidence','v33/v36 operand-level source bindings'],
 'reason':'Eight independently decoded absolute disp32 operands in the coherent 3D core receive zero exact source-coordinate matches, while the legacy parser emits a dense set of nearby type-7 records. This cannot support operand-level relocation binding.'},
 'retained':['Raw LE fixup record bytes remain evidence.','Page/object extraction remains independently useful where validated.','Fixup counts and structural inventory may be retained, but source-to-instruction and target semantics are HOLD.'],
 'confidence':{'3d_operand_anchors':'HIGH','legacy_source_to_instruction_binding_invalid':'HIGH','correct_LE_source_mapping':'HOLD','numeric_attenuation_constants':'HOLD','numeric_pan_constants':'HOLD'},
 'next':['Re-parse raw LE fixup records from specification without inheriting v27 page/source assumptions.','Require exact agreement with all eight 3D disp32 anchors before accepting a corrected mapper.','In parallel preserve the symbolic 0xCDE1 math, which is instruction-level evidence independent of relocation constants.']}
 if sha!=EXPECTED: out['warning']='EXE hash differs from validated demo build'
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8'); print(json.dumps({'status':'PASS','invariants':sum(checks.values()),'total':len(checks),'exact_anchor_fixups':sum(exact.values()),'legacy_window_records':len(neighborhood)},indent=2))
if __name__=='__main__': main()
