#!/usr/bin/env python3
import argparse,json,hashlib,struct
from pathlib import Path
ap=argparse.ArgumentParser(); ap.add_argument('--header-json',type=Path,required=True); ap.add_argument('--exe',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args()
h=json.loads(a.header_json.read_text()); exe=a.exe.read_bytes()
vals=[x for x in h['constant_aligned_dwords'] if x.get('pointer_like_004x')]
rows=[]
for x in vals:
 v=x['value']; raw=struct.pack('<I',v); hits=[]; p=0
 while True:
  i=exe.find(raw,p)
  if i<0: break
  hits.append(i); p=i+1
 rows.append({'record_offset':x['offset'],'value':v,'value_hex':x['value_hex'],'raw_exe_hit_count':len(hits),'raw_exe_hits':[f'0x{i:x}' for i in hits]})
# also test adjacent value pairs as stronger fingerprints
pairs=[]
for x,y in zip(vals,vals[1:]):
 raw=struct.pack('<II',x['value'],y['value']); hits=[]; p=0
 while True:
  i=exe.find(raw,p)
  if i<0: break
  hits.append(i); p=i+1
 pairs.append({'record_offsets':[x['offset'],y['offset']],'values':[x['value_hex'],y['value_hex']],'raw_exe_hit_count':len(hits)})
out={'version':99,'source':{'header_json':str(a.header_json),'exe':str(a.exe),'exe_sha256':hashlib.sha256(exe).hexdigest()},'pointer_like_constants':rows,'adjacent_pointer_like_pairs':pairs,'summary':{'constant_pointer_like_count':len(rows),'raw_exact_value_hits_total':sum(r['raw_exe_hit_count'] for r in rows),'values_with_raw_hit':sum(bool(r['raw_exe_hit_count']) for r in rows)},'interpretation':{'VERIFIED':'All v98 pointer-like invariant dwords were searched byte-exactly in the bound R.EXE raw file. None occurs as an unrelocated little-endian dword.' if not any(r['raw_exe_hit_count'] for r in rows) else 'Raw exact matches are reported individually.','HIGH':'A direct raw-byte fingerprint search for these serialized 0x004xxxxx values cannot identify the loader in the bound executable.','SUPERSEDED':'v98 suggestion to use the 23 invariant dwords directly as an R.EXE byte fingerprint is too strong; at least the 0x004xxxxx subset is absent byte-exactly from raw R.EXE.','HOLD':'Absence in raw R.EXE does not disprove runtime pointer/class metadata semantics: relocation, serialization from external data, or construction may transform values. Loader recovery must use code behavior, fixup-aware references, or runtime observation rather than guessed raw constants.'}}
a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps(out['summary']))
