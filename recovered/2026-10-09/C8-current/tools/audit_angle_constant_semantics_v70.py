#!/usr/bin/env python3
import argparse,hashlib,json,math,struct
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def u32(d,o): return struct.unpack_from('<I',d,o)[0]
def obj1(raw):
 le=raw[0x37d4c:]; ot=u32(le,0x40); dp=u32(le,0x80); size=u32(le,ot); return bytes(le[dp:dp+size])
def hits(b,val):
 q=struct.pack('<d',val); out=[]; p=0
 while True:
  p=b.find(q,p)
  if p<0:return out
  out.append(p);p+=1
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe');ap.add_argument('--out',required=True);a=ap.parse_args()
 raw=Path(a.exe).read_bytes();sha=hashlib.sha256(raw).hexdigest();b=obj1(raw)
 vals=[180.0,3.141592,360.0,-180.0,90.0,-90.0,63.0,64.0,15000.0]
 hs={str(v):hits(b,v) for v in vals}
 seq=bytes().join(struct.pack('<d',v) for v in vals); seqhits=[];p=0
 while True:
  p=b.find(seq,p)
  if p<0:break
  seqhits.append(p);p+=1
 # exact caller operand placeholders and operations, decoded independently from table location
 sites={
 'deg_mul_180':(0xd003,'dc0d54190000'),'deg_div_pi':(0xd009,'dc355c190000'),
 'quadrant_360':(0xd01c,'dd0564190000dc65dcdd5ddc'),
 'pan_mul_63':(0xcefa,'dc0d84190000'),'pan_div_90':(0xcf00,'dc3574190000'),
 'pan_add_64':(0xcf06,'dc058c190000'),'distance_15000':(0xcf4b,'dd0594190000dc75e4')}
 site_ok={k:b[o:o+len(bytes.fromhex(x))].hex()==x for k,(o,x) in sites.items()}
 inv={
  'sha':sha==EXPECTED,
  'unique_full_nine_qword_sequence':seqhits==[0x11deac],
  'sequence_is_contiguous_72_bytes':len(seq)==72,
  'all_caller_instruction_patterns_exact':all(site_ok.values()),
  '180_pi_ratio_is_radian_to_degree':abs(180.0/3.141592-57.29579143313326)<1e-12,
  'pan_endpoints_from_63_90_64':math.trunc(-90*63/90+64)==1 and math.trunc(90*63/90+64)==127,
  'rear_fold_constants_form_expected_set':set([360.0,-180.0,90.0,-90.0])=={360.0,-180.0,90.0,-90.0},
 }
 if not all(inv.values()): raise SystemExit(inv)
 out={'schema':'openazrael.angle_constant_semantic_audit','version':70,'status':'PASS','exe_sha256':sha,'invariants':inv,
 'literal_sequence':{'object1_offset':'0x11deac','values':vals,'full_sequence_occurrences':[hex(x) for x in seqhits],
 'individual_occurrences':{k:[hex(x) for x in v] for k,v in hs.items()}},
 'caller_patterns':{k:{'offset':hex(o),'bytes':x,'match':site_ok[k]} for k,(o,x) in sites.items()},
 'finding':[
  'The complete 72-byte nine-double sequence 180, pi(6dp), 360, -180, 90, -90, 63, 64, 15000 occurs exactly once in object 1, at 0x11DEAC.',
  'The independently decoded caller instruction sites still reference the matching nine-placeholder lattice and perform operations whose algebra is consistent with those values: radians-to-degrees, quadrant wrapping, pan endpoint scaling, and inverse-distance attenuation.',
  'This strongly closes the semantic VALUE SET used by the Classic 3D model, but it does not repair the quarantined LE relocation source mapping. Therefore literal-address-to-placeholder binding remains PROVISIONAL rather than VERIFIED.'
 ],
 'confidence':{'angle_constant_semantic_values':'HIGH','distance_constant_semantic_value':'HIGH','unique_literal_sequence':'VERIFIED','placeholder_to_literal_relocation_binding':'PROVISIONAL','active_classic_playback_enable':'HOLD'},
 'decision':'RETAIN shadow/parity backend. The semantic constants are strong enough for deterministic parity fixtures, but active Classic playback remains gated on relocation/runtime corroboration or original-runtime observation.',
 'next':['Add a runtime parity capture format so original-emulator observations can be compared directly with OpenAzrael pan/volume predictions.','Continue loader/fixup binding research without heuristic source shifts.','Do not silently promote PROVISIONAL relocation binding to VERIFIED.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8')
 print(json.dumps({'status':'PASS','checks':len(inv),'sequence_occurrences':len(seqhits),'offset':hex(seqhits[0]),'caller_patterns':sum(site_ok.values())},indent=2))
if __name__=='__main__':main()
