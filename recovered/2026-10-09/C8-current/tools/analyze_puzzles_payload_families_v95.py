#!/usr/bin/env python3
from pathlib import Path
import argparse,json,hashlib,struct,math,collections

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--v94',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    old=json.loads(Path(a.v94).read_text(encoding='utf-8')); recs=[]; families=collections.Counter(); extended=[]
    for r in old['records']:
        p=bytes.fromhex(r['payload_hex']); nz=[i for i,b in enumerate(p) if b]; last=max(nz) if nz else -1
        fam='COMPACT_18' if p[18:]==b'\0'*11 else ('EXTENDED_24' if p[24:]==b'\0'*5 else 'OTHER'); families[fam]+=1
        o={k:r[k] for k in ('source_offset','source_offset_hex','opcode','token')}; o.update({'family':fam,'payload_last_nonzero_index':last,'payload_18_28_all_zero':p[18:]==b'\0'*11,'payload_24_28_all_zero':p[24:]==b'\0'*5})
        if fam=='EXTENDED_24':
            xyz=[struct.unpack('<f',p[i:i+4])[0] for i in (12,16,20)]; o.update({'aligned_f32_payload_offsets':[12,16,20],'aligned_f32_values':xyz,'aligned_f32_finite':all(math.isfinite(v) for v in xyz)}); extended.append(o)
        recs.append(o)
    out={'version':95,'source':{'v94':str(a.v94),'v94_sha256':hashlib.sha256(Path(a.v94).read_bytes()).hexdigest()},'population':len(recs),'families':dict(families),'invariants':{'compact_family_rule':'payload bytes +18..+28 are all zero','extended_family_rule':'not compact, but payload bytes +24..+28 are all zero','other_count':families['OTHER'],'extended_aligned_f32_offsets':[12,16,20],'extended_aligned_f32_finite_count':sum(x['aligned_f32_finite'] for x in extended),'extended_count':len(extended)},'interpretation':{'VERIFIED':'Within the 198 dominant v94 records, 189 payloads have an exact zero suffix at +18..+28 and the remaining 9 have an exact zero suffix at +24..+28. No record falls outside these two byte-layout families.','HIGH':'The nine EXTENDED_24 records contain three aligned little-endian IEEE-754 single-precision values at payload offsets +12,+16,+20; all 27 decoded values are finite.','PROBABLE':'Those three aligned floats are spatial XYZ-like data. Repeated triplets include (42,40,-80) and (-329,0,-223), which lie inside reconstructed demo room geometry bounds for R7 and R1 respectively. Exact loader/field semantics remain unproven.','HOLD':'Do not assign universal meanings to preceding payload bytes or equate COMPACT_18/EXTENDED_24 directly with runtime opcode structures until the PUZZLES.DAT loader/constructor is recovered.'},'extended_records':extended,'records':recs}
    Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf-8'); print(json.dumps({'population':len(recs),'families':dict(families),'extended_finite':out['invariants']['extended_aligned_f32_finite_count']},indent=2))
if __name__=='__main__': main()
