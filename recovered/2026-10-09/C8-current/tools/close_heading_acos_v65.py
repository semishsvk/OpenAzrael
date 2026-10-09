#!/usr/bin/env python3
import argparse,hashlib,json,math,struct
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def u32(d,o): return struct.unpack_from('<I',d,o)[0]
def obj1(raw):
 le=raw[0x37d4c:]; ot=u32(le,0x40); dp=u32(le,0x80); size=u32(le,ot); return bytes(le[dp:dp+size])
def heading(x,z):
 n=math.hypot(x,z)
 if n==0:return None
 x/=n; z/=n
 # 30D7A: sqrt(1-z^2); atan2(z,sqrt); pi/2 - result = acos(z)
 a=math.degrees(math.acos(max(-1.0,min(1.0,z))))
 if x>0:a=360.0-a
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
  'helper_square_and_one_minus_square':b[0x30d7a:0x30d84]==bytes.fromhex('d9c0d8c8d9e8dee1b001'),
  'sqrt_helper_call':b[0x30d84:0x30d89]==bytes.fromhex('e8fd5f0000'),
  'fxch_then_fpatan_helper':b[0x30d8d:0x30d94]==bytes.fromhex('d9c9e845650100'),
  'pi_over_2_load_then_reverse_subtract':b[0x30d94:0x30d9d]==bytes.fromhex('2edb2d18380300dee1'),
  'fpatan_helper_exact':b[0x472d9:0x472de]==bytes.fromhex('d9c9d9f3c3'),
  'caller_passes_normalized_z':b[0xcff5:0xd003]==bytes.fromhex('d945d883ec08dd1c24e89b3d0200'),
  'caller_positive_x_quadrant_branch':b[0xd012:0xd028]==bytes.fromhex('d9eed85dd0dfe09e730cdd0564190000dc65dcdd5ddc'),
 }
 # x87 stack proof: DE E1 is reverse subtract here because preceding [1,z^2] must yield nonnegative 1-z^2 before FSQRT.
 # After FXCH + helper FXCH + FPATAN, result is atan2(z,sqrt(1-z^2))=asin(z); final same DE E1 with [pi/2,asin] gives pi/2-asin=acos(z).
 dirs={'front':(0,1),'front_right':(1,1),'right':(1,0),'rear_right':(1,-1),'rear':(0,-1),'rear_left':(-1,-1),'left':(-1,0),'front_left':(-1,1)}
 hs={k:heading(*v) for k,v in dirs.items()}
 expected={'front':0.0,'front_right':315.0,'right':270.0,'rear_right':225.0,'rear':180.0,'rear_left':135.0,'left':90.0,'front_left':45.0}
 inv['eight_cardinal_intercardinal_headings_distinct']=len({round(v,9) for v in hs.values()})==8
 inv['headings_match_acos_quadrant_model']=all(abs(hs[k]-expected[k])<1e-9 for k in expected)
 base=hs['front']; outs={k:pan(base,v) for k,v in hs.items()}
 inv['front_vs_rear_do_not_collide']=outs['front']!=outs['rear']
 inv['left_vs_right_pan_do_not_collide']=outs['left'][0]!=outs['right'][0]
 if not all(inv.values()): raise SystemExit(inv)
 out={'schema':'openazrael.heading_acos_closure','version':65,'status':'PASS','exe_sha256':sha,'invariants':inv,
 'x87_stack_proof':[
  'Input z is duplicated: [z,z]. Squaring ST0 gives [z^2,z]. FLD1 gives [1,z^2,z].',
  'DE E1 is the reverse-subtract form in this encoding/context, producing [1-z^2,z]; the following FSQRT therefore yields [sqrt(1-z^2),z].',
  'Caller FXCH gives [z,sqrt]. 0x472D9 performs FXCH; FPATAN, so FPATAN evaluates atan2(z,sqrt(1-z^2)) = asin(z).',
  'FLDT loads verified pi/2 above asin(z); the final DE E1 produces pi/2-asin(z)=acos(z).',
  'Therefore 0x30D7A normal-domain result is acos(z), not asin(z).'
 ],
 'heading_model':{'normal_nonzero_horizontal_vector':'angle=degrees(acos(normalized_z)); if normalized_x>0: angle=360-angle','confidence':'HIGH','zero_horizontal_vector':'HOLD'},
 'golden_headings_deg':hs,
 'front_listener_pipeline':{k:{'pan':v[0],'mode_divisor':v[1],'folded_angle_deg':v[2]} for k,v in outs.items()},
 'correction':{'v63_asin_equivalent_identity':'SUPERSEDED','v64_cardinal_collision':'RESOLVED','pi_over_2_literal':'RETAINED_VERIFIED','complete_xyz_heading_normal_nonzero':'HIGH_CONDITIONAL_ON_V58_CALLER_ANGLE_CONSTANT_LATTICE','zero_vector_and_x87_boundary_behavior':'HOLD'},
 'note':'This closes the helper stack semantics. The v58 ordered placeholder-to-literal mapping for caller angle constants remains separately PROVISIONAL after v64; this tool does not silently upgrade that relocation binding.',
 'next':['Independently bind caller angle placeholders (180/pi/360/+/-90) or reconstruct their relocation/runtime values.','Add parity fixtures for all 7 authentic AMB emitters once listener poses are available.','Only then wire the v65 reference into active Classic Audio.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8')
 print(json.dumps({'status':'PASS','checks':len(inv),'helper':'acos(z)','headings':hs,'front_pipeline':outs},indent=2))
if __name__=='__main__':main()
