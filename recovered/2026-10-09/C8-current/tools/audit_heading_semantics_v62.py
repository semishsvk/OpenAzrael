#!/usr/bin/env python3
import argparse,hashlib,json,math,struct
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def u32(d,o): return struct.unpack_from('<I',d,o)[0]
def obj1(raw):
 le=raw[0x37d4c:]; ot=u32(le,0x40); dp=u32(le,0x80); size=u32(le,ot); return bytes(le[dp:dp+size])
def v61_heading(x,z):
 n=math.hypot(x,z)
 if n==0:return None
 x/=n;z/=n;a=math.degrees(math.asin(max(-1,min(1,z))))
 if x>0:a=360-a
 return a
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe');ap.add_argument('--out',required=True);a=ap.parse_args()
 raw=Path(a.exe).read_bytes();sha=hashlib.sha256(raw).hexdigest();b=obj1(raw)
 inv={
  'heading_input_is_normalized_z':b[0xcff5:0xcffe]==bytes.fromhex('d945d883ec08dd1c24'),
  'quadrant_test_uses_normalized_x':b[0xd012:0xd01c]==bytes.fromhex('d9eed85dd0dfe09e730c'),
  'helper_forms_square_and_one':b[0x30d7a:0x30d84]==bytes.fromhex('d9c0d8c8d9e8dee1b001'),
  'helper_calls_sqrt_path':b[0x30d84:0x30d89]==bytes.fromhex('e8fd5f0000'),
  'helper_uses_fpatan':b[0x30d8d:0x30d94]==bytes.fromhex('d9c9e845650100'),
  'helper_has_post_atan_extended_constant_op':b[0x30d94:0x30d9d]==bytes.fromhex('2edb2d18380300dee1'),
 }
 old={'x_neg_z0':v61_heading(-1,0),'x_pos_z0':v61_heading(1,0),'x_neg_zpos':v61_heading(-1,1),'x_pos_zneg':v61_heading(1,-1)}
 collision=(old['x_neg_z0']%360)==(old['x_pos_z0']%360)
 if sha!=EXPECTED or not all(inv.values()) or not collision: raise SystemExit('v62 invariant failure')
 out={'schema':'openazrael.heading_semantics_correction','version':62,'status':'PASS','exe_sha256':sha,'invariants':inv,
 'adversarial_check':{'v61_formula':'degrees(asin(z)); if x>0 => 360-angle','cardinal_outputs':old,'opposite_x_cardinals_collapse_mod_360':collision,
 'finding':'The v61 closed-form interpretation maps opposite normalized X directions (X=-1,Z=0 and X=+1,Z=0) to the same heading modulo 360. A heading used for spatial pan cannot distinguish those directions under that formula. Therefore the v61 formula/golden semantic labels are not safe as an exact reconstruction.'},
 'correction':{'v61_xyz_heading_formula':'SUPERSEDED_V62','v61_xyz_golden_vectors':'SUPERSEDED_V62','instruction_level_facts':'RETAINED_HIGH','exact_0x30D7A_semantics':'HOLD','complete_xyz_to_pan':'HOLD','heading_independent_pan_transform':'RETAINED_HIGH','attenuation':'RETAINED_HIGH'},
 'reasoning_guardrail':'Do not name 0x30D7A asin/acos or wire XYZ->pan until the post-FPATAN extended-precision constant at the relocated 0x33818 operand and exact x87 stack subtraction direction are independently resolved.',
 'next':['Resolve the relocated 80-bit constant referenced by 0x30D94.','Model the x87 stack for DE E1 and FPATAN exactly, then require four cardinal directions to remain distinct before accepting XYZ heading.','Keep live Godot Classic renderer approximate until corrected XYZ golden vectors pass.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps({'status':'PASS','invariants':len(inv),'v61_heading':'SUPERSEDED_V62','cardinal_collision':collision},indent=2))
if __name__=='__main__':main()
