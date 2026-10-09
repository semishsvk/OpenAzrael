#!/usr/bin/env python3
from pathlib import Path
import argparse,json,hashlib,collections

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--puzzles',required=True); ap.add_argument('--v90',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
 d=Path(a.puzzles).read_bytes(); v=json.loads(Path(a.v90).read_text())
 fes=[i for i,b in enumerate(d) if b==0xfe]; next_fe={x:y for x,y in zip(fes,fes[1:])}
 dominant=[]; other=[]
 for r in v['records']:
  anchor=r['nearest_fe_anchor']; gap=(next_fe.get(anchor)-anchor) if anchor in next_fe else None
  rr=dict(r); rr['next_fe_gap']=gap
  if gap==190:
   start=anchor+128; end=anchor+190; slot=d[start:end]
   token_start=3; nul=slot.find(b'\0',token_start)
   token_end=nul if nul>=0 else None
   residue=slot[nul+1:] if nul>=0 else b''
   rr.update({
    'record_span_bytes':190,'action_slot_offset':128,'action_slot_size':62,
    'action_slot_sha256':hashlib.sha256(slot).hexdigest(),
    'token_terminator_offset_in_slot':nul,
    'token_span_bytes':(nul-token_start) if nul>=0 else None,
    'opaque_residue_offset_in_slot':(nul+1) if nul>=0 else None,
    'opaque_residue_hex':residue.hex(),
    'opaque_residue_nonzero_bytes':sum(x!=0 for x in residue),
    'slot_parse_status':'STRUCTURAL_ONLY_NO_RESIDUE_SEMANTICS'
   }); dominant.append(rr)
  else: other.append(rr)
 # Per-byte invariance only for the exact 190-byte family; descriptive, not semantic.
 byte_stats=[]
 for off in range(190):
  c=collections.Counter(d[r['nearest_fe_anchor']+off] for r in dominant)
  byte_stats.append({'offset':off,'offset_hex':f'0x{off:02x}','distinct_values':len(c),'most_common':[[k,n] for k,n in c.most_common(5)]})
 obj={
  'version':91,'format':'OpenAzrael PUZZLES.DAT dominant 190-byte action-slot refinement',
  'source':{'name':Path(a.puzzles).name,'size':len(d),'sha256':hashlib.sha256(d).hexdigest()},
  'supersedes':'v90 located the action prefix at FE+128; v91 closes the byte span of that field only for the dominant next-FE gap=190 family.',
  'grammar_status':'DOMINANT_RECORD_ACTION_SLOT_BOUNDARY_HIGH_OTHER_FIELDS_PARTIAL',
  'execution_policy':'NOT_DIRECTLY_EXECUTABLE',
  'dominant_family':{
   'record_span_bytes':190,'action_slot_offset':128,'action_slot_size':62,
   'record_count':len(dominant),'confidence':'HIGH',
   'definition':'v90 structurally anchored action record whose next FE anchor is exactly 190 bytes later'
  },
  'dominant_records':dominant,'non_190_structural_records':other,'byte_statistics':byte_stats,
  'boundaries':[
   'The 62-byte action slot is a structural span from FE+128 to immediately before the next FE only in the 190-byte family.',
   'Only 10 00, opcode byte, printable NUL-terminated token, and the slot boundary are parsed. Bytes after the token are preserved as opaque residue.',
   'Opaque residue is not interpreted as comments, operands, flags, or padding in v91.',
   'The 32 structurally anchored v90 records outside the 190-byte family remain outside this closed slot grammar and are not forced into it.',
   'Byte invariance is descriptive evidence, not a semantic field assignment.'
  ]
 }
 Path(a.out).write_text(json.dumps(obj,indent=2)+'\n')
 print(json.dumps({'dominant_190':len(dominant),'other_structural':len(other),'slot_size':62,'all_tokens_terminated':all(r['token_terminator_offset_in_slot'] is not None for r in dominant)},sort_keys=True))
if __name__=='__main__': main()
