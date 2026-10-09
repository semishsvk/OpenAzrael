#!/usr/bin/env python3
"""OpenAzrael v33: build selector/object-relative LE type-7 xrefs.
Conservative rule: LE source type 7 is a 32-bit OFFSET relocation. For internal
references the relocation value is the target object's offset; object identity
is retained separately (selector/object ordinal), not folded into the offset.
"""
import argparse,json,hashlib,struct
from pathlib import Path
U32=lambda d,o:struct.unpack_from('<I',d,o)[0]

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('fixups'); ap.add_argument('--out',required=True); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); fx=json.loads(Path(a.fixups).read_text())
 leoff=0x37d4c if raw[0x37d4c:0x37d4e]==b'LE' else U32(raw,0x3c); le=raw[leoff:]
 ot,oc=U32(le,0x40),U32(le,0x44); objs=[]
 for i in range(oc):
  size,base,flags,first,npages,_=struct.unpack_from('<IIIIII',le,ot+i*24)
  objs.append({'object':i+1,'size':size,'preferred_base':base,'flags':flags})
 recs=[]
 for r in fx['records']:
  if r.get('source_type')!=7 or r.get('target_kind')!='internal' or r.get('target_offset') is None: continue
  to=r['target_object']; off=r['target_offset']
  if not (1<=to<=len(objs) and 0<=off<objs[to-1]['size']): continue
  recs.append({'source_object':r['source_object'],'source_offset':r['source_offset'],'source_linear_diagnostic':r['source_linear'],
               'fixup_type':7,'fixup_semantics':'OFFSET32','target_object':to,'target_offset':off,
               'target_linear_diagnostic':objs[to-1]['preferred_base']+off,
               'runtime_patch_value':off,'confidence':'HIGH'})
 # useful target-object/source-object matrix
 matrix={}
 for r in recs:
  k=f"{r['source_object']}->{r['target_object']}"; matrix[k]=matrix.get(k,0)+1
 out={'schema':'openazrael.trusted_object_relative_xrefs','version':33,'exe_sha256':hashlib.sha256(raw).hexdigest(),
      'semantics':{'source_type_7':'32-bit offset relocation','runtime_value':'target_offset','object_identity':'target_object ordinal/selector context','preferred_linear':'diagnostic only; preferred_base + offset'},
      'record_count':len(recs),'object_pair_histogram':matrix,'objects':objs,'xrefs':recs,
      'confidence':{'type7_offset_semantics':'HIGH','target_object_and_offset':'HIGH','object_relative_xref_graph':'HIGH','preferred_linear_runtime_address':'HOLD','Miles_function_identity':'HOLD','Play3DSample_implementation':'HOLD'},
      'findings':['The previous H1 vs H2 ambiguity was caused by mixing segmented/object-relative LE offsets with diagnostic preferred linear addresses.','Type 7 relocates a 32-bit OFFSET. The target object ordinal carries object/selector identity; the patched 32-bit value is the target offset, not preferred_base+offset.','This is sufficient to build a trusted object-relative xref graph without claiming a flat runtime address.'],
      'next':['Use object-relative xrefs to identify code references into object 2 data/import structures.','Locate Miles backend dispatch/thunks by code pattern and referenced data, not diagnostic strings.','Build function boundaries/call graph in object 1 and resume Play3DSample backward slicing.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8')
 print(json.dumps({'record_count':len(recs),'object_pair_histogram':matrix,'confidence':out['confidence']},indent=2))
if __name__=='__main__': main()
