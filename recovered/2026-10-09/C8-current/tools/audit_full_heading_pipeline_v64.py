#!/usr/bin/env python3
import argparse,hashlib,json,math,struct
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def u32(d,o): return struct.unpack_from('<I',d,o)[0]
def obj1(raw):
 le=raw[0x37d4c:]; ot=u32(le,0x40); dp=u32(le,0x80); size=u32(le,ot); return bytes(le[dp:dp+size])
def heading_v61(x,z):
 n=math.hypot(x,z)
 if n==0: return None
 x/=n; z/=n
 a=math.degrees(math.asin(max(-1,min(1,z))))
 if x>0:a=360-a
 return a
def pan(a,b):
 mode=1
 if a<=180 and b>180:
  d=360-b+a
  if d>180:d=-(360-d)
 else:
  d=-(360-a+b)
  if d < -180:d+=360
 if d>90:mode=2;d=180-d
 elif d < -90:mode=2;d=-180-d
 return math.trunc(d*63/90+64),mode,d
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe');ap.add_argument('--out',required=True);a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); b=obj1(raw); sha=hashlib.sha256(raw).hexdigest()
 inv={
 'sha':sha==EXPECTED,
 'caller_passes_normalized_z':b[0xcff5:0xd003]==bytes.fromhex('d945d883ec08dd1c24e89b3d0200'),
 'caller_sign_test_is_zero_vs_x':b[0xd012:0xd01c]==bytes.fromhex('d9eed85dd0dfe09e730c'),
 'positive_x_applies_constant_minus_angle':b[0xd01c:0xd028]==bytes.fromhex('dd0564190000dc65dcdd5ddc'),
 'helper_post_atan_reverse_subtract':b[0x30d94:0x30d9d]==bytes.fromhex('2edb2d18380300dee1'),
 }
 # Adversarial end-to-end test of the v61/v63 combined interpretation.
 hneg=heading_v61(-1,0); hpos=heading_v61(1,0)
 p_same=pan(hneg,hneg); p_opposite=pan(hneg,hpos)
 cardinal_collision=(p_same==p_opposite)
 inv['v61_full_pipeline_opposite_x_collides']=cardinal_collision
 if not all(inv.values()): raise SystemExit(inv)
 out={
 'schema':'openazrael.full_heading_pipeline_audit','version':64,'status':'PASS','exe_sha256':sha,'invariants':inv,
 'adversarial_case':{'listener_xz':[-1,0],'same_source_xz':[-1,0],'opposite_source_xz':[1,0],
   'listener_heading_v61':hneg,'opposite_heading_v61':hpos,'same_output':{'pan':p_same[0],'mode_divisor':p_same[1],'folded_angle':p_same[2]},'opposite_output':{'pan':p_opposite[0],'mode_divisor':p_opposite[1],'folded_angle':p_opposite[2]}},
 'finding':'The v61/v63 combined asin-equivalent + caller quadrant interpretation fails even when raw 0 and 360 endpoints are preserved through the complete CE29..CF11 pan branch: opposite X directions produce the same pan and mode as identical directions.',
 'correction':{
   'v63_helper_identity_asin_equivalent':'SUPERSEDED_V64_AS_COMPLETE_SEMANTIC_IDENTITY',
   'pi_over_2_literal':'RETAINED_VERIFIED',
   'sqrt_helper':'RETAINED_HIGH','fpatan_instruction':'RETAINED_VERIFIED',
   'caller_z_input_and_x_sign_branch':'RETAINED_HIGH','complete_xyz_to_heading':'HOLD','complete_xyz_to_pan':'HOLD',
   'v58_ordered_placeholder_to_literal_mapping':'DOWNGRADED_TO_PROVISIONAL_FOR_ANGLE_CONSTANTS'
 },
 'reason':'A mathematically correct complete direction mapping must distinguish antipodal horizontal vectors. Since the instruction bytes are verified, at least one semantic assumption in the x87 stack interpretation and/or placeholder-to-literal angle-constant mapping remains wrong. Do not wire v61/v63 XYZ heading into runtime.',
 'next':['Trace the x87 stack state instruction-by-instruction through 0x30D7A with independently verified FSUBRP/FPATAN operand semantics.','Independently bind the 0x1964 placeholder rather than relying on ordered-lattice correspondence from v58.','Require antipodal/cardinal full-pipeline tests before promoting XYZ->pan.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8')
 print(json.dumps({'status':'PASS','checks':len(inv),'opposite_collision':cardinal_collision,'xyz_pan':'HOLD'},indent=2))
if __name__=='__main__':main()
