#!/usr/bin/env python3
import argparse,json,struct,math,hashlib
from pathlib import Path

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('puzzles'); ap.add_argument('-o','--out',required=True); a=ap.parse_args()
 b=Path(a.puzzles).read_bytes(); fe=[i for i,x in enumerate(b) if x==0xfe]
 dominant=[]
 for x,y in zip(fe,fe[1:]):
  if y-x!=190: continue
  s=x+128; blk=b[s:s+32]
  if len(blk)<32 or blk[:2]!=b'\x10\x00': continue
  vals=struct.unpack('<3f',blk[15:27])
  plausible=all(math.isfinite(v) and abs(v)<=1000 for v in vals) and any(abs(v)>=1 for v in vals)
  if plausible:
   dominant.append({'record_anchor':x,'action_offset':s,'action_offset_hex':hex(s),'opcode':f'0x{blk[2]:02x}',
    'prefix_12_hex':blk[3:15].hex(),'prefix_12_ascii':''.join(chr(q) if 32<=q<127 else '.' for q in blk[3:15]),
    'aligned_f32_block_offsets':[15,19,23],'aligned_f32_payload_offsets':[12,16,20], 'values':list(vals)})
 from collections import Counter
 c=Counter(tuple(round(v,6) for v in r['values']) for r in dominant)
 out={'version':96,'source':{'file':str(a.puzzles),'sha256':sha(a.puzzles)},
  'method':'Scan every consecutive FE-anchor pair with exact 190-byte spacing; inspect the 32-byte action block at FE+128 independent of printable-token decoding. Candidate spatial triples are aligned float32 at action offsets +15,+19,+23 (payload +12,+16,+20), finite, abs<=1000, with at least one abs>=1.',
  'dominant_fe_gap_count':sum(1 for x,y in zip(fe,fe[1:]) if y-x==190),
  'dominant_action_header_count':sum(1 for x,y in zip(fe,fe[1:]) if y-x==190 and b[x+128:x+130]==b'\x10\x00'),
  'spatial_like_count':len(dominant),'triplet_frequency':[{ 'values':list(k),'count':v} for k,v in c.most_common()],
  'correction':{'v95_extended_count':9,'v96_spatial_like_count':len(dominant),'newly_recovered_count':len(dominant)-9,
   'reason':'v95 population inherited the v88 printable-leading-token filter. Six structurally valid 190-byte records contain binary prefix bytes before an embedded name and were therefore absent from the 198-record token-derived population.'},
  'confidence':{'VERIFIED':'The listed action blocks exist at FE+128 inside 190-byte dominant records and the stated bytes decode to the reported float32 values.',
   'HIGH':'The repeated aligned numeric triplets form a distinct spatial-like subpopulation when scanning structurally rather than by printable token.',
   'PROBABLE':'The repeated (42,40,-80) and (-329,0,-223) clusters are XYZ-like spatial coordinates.',
   'HOLD':'Do not treat every numeric-looking triple as XYZ or infer field semantics until the PUZZLES.DAT loader/runtime constructor is recovered. The (0,0,20) record is retained as spatial-like, not proven spatial.'},
  'records':dominant}
 Path(a.out).write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'spatial_like':len(dominant),'new_vs_v95':len(dominant)-9,'frequencies':out['triplet_frequency']},indent=2))
if __name__=='__main__': main()
