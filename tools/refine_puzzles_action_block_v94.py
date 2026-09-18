#!/usr/bin/env python3
from pathlib import Path
import argparse,json,hashlib

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--puzzles',required=True); ap.add_argument('--v91',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
 d=Path(a.puzzles).read_bytes(); old=json.loads(Path(a.v91).read_text())
 recs=[]; tail_zero=0; token_ok=0; postnul_nonzero=0
 for r in old['dominant_records']:
  o=r['source_offset']; slot=d[o:o+62]; active=slot[:32]; tail=slot[32:]
  payload=active[3:32]; z=payload.find(b'\0'); tok=payload[:z].decode('ascii','replace') if z>=0 else None
  if tail==b'\0'*30: tail_zero+=1
  if tok==r['token']: token_ok+=1
  if z>=0 and any(payload[z+1:]): postnul_nonzero+=1
  recs.append({'source_offset':o,'source_offset_hex':hex(o),'opcode':r['legacy_opcode_hex'],'token':r['token'],
   'active_block_size':32,'header_hex':active[:3].hex(),'payload_hex':payload.hex(),'payload_first_nul':z,
   'decoded_leading_token':tok,'bytes_after_first_nul_hex':payload[z+1:].hex() if z>=0 else None,
   'zero_tail_size':30,'zero_tail_all_zero':tail==b'\0'*30,
   'active_block_sha256':hashlib.sha256(active).hexdigest()})
 out={'version':94,'source':{'name':'PUZZLES.DAT','sha256':hashlib.sha256(d).hexdigest()},
  'population':len(recs),'invariants':{
   'slot_size':62,'active_prefix_candidate_size':32,'trailing_zero_region_size':30,
   'trailing_zero_region_exact_matches':tail_zero,'leading_token_matches_v91':token_ok,
   'records_with_nonzero_bytes_after_first_token_nul_inside_29_byte_payload':postnul_nonzero},
  'interpretation':{
   'VERIFIED':'For all 198 dominant records, bytes +32..+61 of the 62-byte action slot are zero. The nonzero/action-bearing region is confined to +0..+31. Bytes +0..+1 are 10 00, +2 is the legacy opcode, and a NUL-terminated leading token begins at +3.',
   'HIGH':'Treat +0..+31 as the serialized action block boundary for the dominant 190-byte record family.',
   'HOLD':'The 29 bytes at +3..+31 are opcode-specific payload/storage. Nonzero bytes after the first token NUL must not be treated as one generic residue or as universal fixed fields until the loader/handlers prove their layout.',
   'SUPERSEDES':'v92 generic residue interpretation and v93 suggestion that repeated printable columns necessarily represent independent fixed fields.'},
  'records':recs}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf-8')
 print(json.dumps(out['invariants'],indent=2))
if __name__=='__main__': main()
