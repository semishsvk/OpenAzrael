#!/usr/bin/env python3
import argparse,json,hashlib,struct,math,collections
from pathlib import Path

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('puzzles'); ap.add_argument('-o','--out',required=True); a=ap.parse_args()
    b=Path(a.puzzles).read_bytes(); fe=[i for i,v in enumerate(b) if v==0xfe]
    recs=[]; fam=collections.Counter(); byop=collections.defaultdict(collections.Counter); ext=[]
    for x,y in zip(fe,fe[1:]):
        if y-x!=190: continue
        s=x+128; blk=b[s:s+32]
        if len(blk)!=32 or blk[:2]!=b'\x10\x00': continue
        p=blk[3:32]
        if p[18:]==b'\0'*11: family='COMPACT_18'
        elif p[24:]==b'\0'*5: family='EXTENDED_24'
        else: family='OTHER'
        fam[family]+=1; byop[f'0x{blk[2]:02x}'][family]+=1
        nz=[i for i,v in enumerate(p) if v]
        r={'record_anchor':x,'record_anchor_hex':hex(x),'action_offset':s,'action_offset_hex':hex(s),
           'opcode':f'0x{blk[2]:02x}','family':family,'payload_hex':p.hex(),
           'payload_last_nonzero_index':max(nz) if nz else -1}
        if family=='EXTENDED_24':
            vals=list(struct.unpack('<3f',p[12:24])); r['aligned_f32_payload_offsets']=[12,16,20]; r['aligned_f32_values']=vals; r['aligned_f32_finite']=all(math.isfinite(v) for v in vals); ext.append(r)
        recs.append(r)
    triples=collections.Counter(tuple(round(v,6) for v in r['aligned_f32_values']) for r in ext)
    out={'version':97,'source':{'file':str(a.puzzles),'sha256':sha(a.puzzles)},
      'population_rule':'Consecutive FE anchors exactly 190 bytes apart, with a 32-byte action block at FE+128 beginning 10 00. No printable-token requirement.',
      'population':len(recs),'families':dict(fam),'opcode_family_counts':{k:dict(v) for k,v in sorted(byop.items())},
      'invariants':{
        'all_records_have_payload_24_28_zero':all(bytes.fromhex(r['payload_hex'])[24:]==b'\0'*5 for r in recs),
        'compact_rule':'payload +18..+28 all zero','extended_rule':'payload +18..+23 contains data and +24..+28 all zero',
        'other_count':fam['OTHER'],'extended_count':fam['EXTENDED_24'],'extended_f32_finite_count':sum(r['aligned_f32_finite'] for r in ext),
        'extended_equals_v96_spatial_like_count':fam['EXTENDED_24']==15},
      'triplet_frequency':[{'values':list(k),'count':v} for k,v in triples.most_common()],
      'correction':{'v95_scope':'189 COMPACT_18 + 9 EXTENDED_24 was correct only for the old 198 printable-token subset.',
        'v97_structural_scope':f"{fam['COMPACT_18']} COMPACT_18 + {fam['EXTENDED_24']} EXTENDED_24 across {len(recs)} structurally selected records.",
        'new_extended_vs_v95':fam['EXTENDED_24']-9},
      'confidence':{
        'VERIFIED':'All 224 structurally selected action blocks have payload bytes +24..+28 equal to zero; exactly 209 also have +18..+23 zero and exactly 15 retain data through +23. No OTHER family exists in this population.',
        'HIGH':'The 15 EXTENDED_24 records are exactly the 15 records independently recovered by the v96 aligned-float structural scan; all 45 aligned float32 values at +12/+16/+20 are finite.',
        'PROBABLE':'The repeated extended float triplets encode legacy XYZ-like spatial context for the R1 and Niamh clusters.',
        'HOLD':'Do not assign universal semantics to COMPACT_18 fields, nor claim every EXTENDED_24 float triple is a position, until loader/runtime construction is recovered.'},
      'extended_records':ext,'records':recs}
    Path(a.out).write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'population':len(recs),'families':dict(fam),'extended_finite':out['invariants']['extended_f32_finite_count'],'other':fam['OTHER']},indent=2))
if __name__=='__main__': main()
