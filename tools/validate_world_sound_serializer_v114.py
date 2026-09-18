#!/usr/bin/env python3
from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'data/world_sound_serializer_v114.json'
errors=[]
try: d=json.loads(P.read_text(encoding='utf-8'))
except Exception as e:
 print('OpenAzrael v114 WORLD serializer validation: FAIL'); print(' - load:',e); raise SystemExit(1)
if d.get('schema')!='openazrael.world_sound_serializer_audit' or d.get('version')!=114 or d.get('status')!='PASS': errors.append('schema/version/status drift')
r=d.get('reader_chain',{}); w=d.get('writer_chain',{}); q=d.get('opcode28_residue_audit',{})
if r.get('top_reader_hex')!='0x29e98' or r.get('node_reader_hex')!='0x29cf4' or r.get('blob_reader_hex')!='0x29638': errors.append('reader chain drift')
if w.get('top_writer_hex')!='0x29e40' or w.get('node_writer_hex')!='0x29d74' or w.get('blob_writer_hex')!='0x2972c': errors.append('writer chain drift')
if '0x1B' not in r.get('blob27_behavior','') or '0x1B' not in w.get('blob27_behavior',''): errors.append('27-byte wholesale IO drift')
if q.get('sound_records')!=44 or q.get('all_section6_blob27_records')!=400 or q.get('all_section6_blob37_records')!=387: errors.append('record population drift')
if q.get('unique_tail_17_26')!=41 or q.get('zero_tail_17_26')!=4 or q.get('nonzero_tail_17_26')!=40: errors.append('tail population drift')
if q.get('duplicate_semantic_binding_groups')!=7 or q.get('duplicate_groups_with_varying_tail')!=7: errors.append('duplicate-tail variability drift')
if q.get('tapframe_797tap_records')!=12 or q.get('tapframe_797tap_unique_tails')!=12: errors.append('797tap variability drift')
a=d.get('allocation_audit',{})
if len(a.get('matches',[]))!=1 or a['matches'][0].get('mov_site_hex')!='0x29703' or a['matches'][0].get('call_site_hex')!='0x29712': errors.append('immediate 27-byte allocation audit drift')
if not all(d.get('checks',{}).values()) or len(d.get('checks',{}))!=29: errors.append('machine invariant drift')
forbidden={'raw','raw_hex','block_hex','payload_hex','bytes_hex','tail_hex','stem_remainder_hex'}
def walk(x,path='root'):
 if isinstance(x,dict):
  for k,v in x.items():
   if k.lower() in forbidden: errors.append(f'forbidden raw field at {path}.{k}')
   walk(v,f'{path}.{k}')
 elif isinstance(x,list):
  for i,v in enumerate(x): walk(v,f'{path}[{i}]')
walk(d)
if errors:
 print('OpenAzrael v114 WORLD serializer validation: FAIL')
 for e in errors: print(' -',e)
 sys.exit(1)
print('OpenAzrael v114 WORLD serializer validation: PASS')
print(' opaque 27-byte reader/writer: VERIFIED')
print(' sound tails: 41 unique / 44 records; 7/7 duplicate semantic groups vary')
print(' tail semantic status: UNKNOWN/HOLD')
