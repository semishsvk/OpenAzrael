#!/usr/bin/env python3
import argparse,json,struct,hashlib
from pathlib import Path
U32=lambda d,o:struct.unpack_from('<I',d,o)[0]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('xrefs'); ap.add_argument('--out',required=True); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); x=json.loads(Path(a.xrefs).read_text())
 leoff=0x37d4c if raw[0x37d4c:0x37d4e]==b'LE' else U32(raw,0x3c); le=raw[leoff:]
 ot,oc=U32(le,0x40),U32(le,0x44); objs=[]
 for i in range(oc):
  size,base,flags,first,npages,_=struct.unpack_from('<IIIIII',le,ot+i*24)
  objs.append({'object':i+1,'size':size,'preferred_base':base,'flags':flags})
 # The graph itself remains useful: target object+offset is the canonical LE target.
 # v33's claim that OFFSET32 runtime patch value is target_offset alone is withdrawn.
 pairs={}
 for r in x['xrefs']:
  k=f"{r['source_object']}->{r['target_object']}"; pairs[k]=pairs.get(k,0)+1
 out={
  'schema':'openazrael.le_fixup_semantics_correction','version':34,'exe_sha256':hashlib.sha256(raw).hexdigest(),
  'record_count':len(x['xrefs']),'object_pair_histogram':pairs,'objects':objs,
  'canonical_target':{'representation':'(target_object, target_offset)','confidence':'HIGH'},
  'source_type_07':{'meaning':'32-bit Offset fixup','confidence':'VERIFIED_SPEC'},
  'target_flag_0x10':{'meaning':'32-bit Target Offset field; otherwise 16-bit','confidence':'VERIFIED_SPEC'},
  'correction':{
   'withdrawn_v33_claim':'runtime_patch_value == target_offset',
   'reason':'LE/LX specification defines TRGOFF as an offset into the target object. Source type 07 defines the width/type of the source fixup, not a proof that the loader writes a naked object-relative offset. Open Watcom headers independently label 07 as OSF_SOURCE_OFF_32 and 0x10 as OSF_TFLAG_OFF_32BIT.',
   'safe_model':'Preserve object identity and TRGOFF as canonical xref. Compute a flat/linear address only inside an explicitly selected loader/runtime model.',
   'confidence':'HIGH'
  },
  'confidence':{'raw_records':'VERIFIED','source_type_semantics':'VERIFIED_SPEC','target_object_and_offset':'HIGH','object_relative_xref_graph':'HIGH','runtime_patch_formula':'HOLD','flat_runtime_address':'HOLD','Miles_callsite_identity':'HOLD'},
  'next':['Rebuild the loader using specification-correct source-page handling including signed cross-page source offsets.','Validate relocation on entry-point code and instruction operands before trusting a flat loaded image.','Use the canonical object-relative graph for navigation without pretending object offsets are runtime pointers.']
 }
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8'); print(json.dumps(out['confidence'],indent=2))
if __name__=='__main__': main()
