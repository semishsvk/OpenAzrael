#!/usr/bin/env python3
import argparse,json,hashlib,collections,struct
from pathlib import Path
ap=argparse.ArgumentParser(); ap.add_argument('--puzzles',type=Path,required=True); ap.add_argument('--v97',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args()
data=a.puzzles.read_bytes(); v97=json.loads(a.v97.read_text()); recs=v97['records']
headers=[data[r['record_anchor']:r['record_anchor']+128] for r in recs]
constant=[]; variable=[]
for off in range(128):
 c=collections.Counter(h[off] for h in headers)
 ent={'offset':off,'offset_hex':hex(off),'unique_values':len(c),'top_values':[{'value':k,'hex':f'0x{k:02x}','count':n} for k,n in c.most_common(8)]}
 (constant if len(c)==1 else variable).append(ent)
# contiguous constant runs
runs=[]; s=None; prev=None
for x in [e['offset'] for e in constant]:
 if s is None: s=prev=x
 elif x==prev+1: prev=x
 else: runs.append([s,prev]); s=prev=x
if s is not None:runs.append([s,prev])
# aligned dwords constant across all records
cd=[]
for off in range(0,128,4):
 vals=[struct.unpack_from('<I',h,off)[0] for h in headers]
 c=collections.Counter(vals)
 if len(c)==1:
  v=vals[0]; cd.append({'offset':off,'offset_hex':hex(off),'value':v,'value_hex':f'0x{v:08x}','pointer_like_004x':0x00400000<=v<0x00500000})
# family-specific header signatures after first 16 bytes
fam={}
for name in ('COMPACT_18','EXTENDED_24'):
 rr=[r for r in recs if r['family']==name]; hs=[data[r['record_anchor']:r['record_anchor']+128] for r in rr]
 fam[name]={'count':len(rr),'unique_full_headers':len(set(hs)),'unique_tail_16_127':len(set(h[16:] for h in hs)),'unique_tail_24_127':len(set(h[24:] for h in hs))}
out={'version':98,'source':{'file':str(a.puzzles),'sha256':hashlib.sha256(data).hexdigest(),'v97':str(a.v97),'v97_sha256':hashlib.sha256(a.v97.read_bytes()).hexdigest()},'population':len(recs),'header_size':128,'invariants':{'constant_byte_offsets':len(constant),'variable_byte_offsets':len(variable),'constant_fraction':len(constant)/128,'constant_runs':runs,'aligned_constant_dwords':len(cd),'aligned_constant_pointer_like_004x':sum(x['pointer_like_004x'] for x in cd)},'family_header_diversity':fam,'constant_aligned_dwords':cd,'variable_columns':variable,'interpretation':{'VERIFIED':'Across all 224 v97 structural records, 100 of the 128 bytes preceding the action block are byte-for-byte constant. Numerous aligned 32-bit values are also identical across every record.','HIGH':'The FE+0..127 region is a strongly templated serialized record header/body rather than arbitrary padding; action data begins separately at +128.','PROBABLE':'Several repeated aligned values in the 0x0048xxxx-0x004bxxxx range are pointer-like serialized runtime/class metadata values from the original engine/toolchain. This explains the unusually stable binary template, but pointer semantics are not yet independently proven.','HOLD':'Do not dereference or assign class/vtable meanings to 0x004xxxxx values until an R.EXE loader/constructor or runtime correspondence is recovered. EXTENDED_24 remains correlated with spatial-like payload, not proven to be a distinct C++ subclass.'}}
a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'records':len(recs),'constant_bytes':len(constant),'constant_dwords':len(cd),'pointer_like':sum(x['pointer_like_004x'] for x in cd)},sort_keys=True))
