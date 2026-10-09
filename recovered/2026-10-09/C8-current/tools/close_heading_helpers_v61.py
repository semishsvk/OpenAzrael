#!/usr/bin/env python3
import argparse,hashlib,json,math,struct
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def u32(d,o): return struct.unpack_from('<I',d,o)[0]
def obj1(raw):
 le=raw[0x37d4c:]; ot=u32(le,0x40); dp=u32(le,0x80); size=u32(le,ot); return bytes(le[dp:dp+size])
def heading(x,z):
 n=math.hypot(x,z)
 if n==0: return None
 x/=n; z/=n
 # 0x30D7A is asin(z): sqrt(1-z*z), fpatan, then pi/2 - acos(z).
 a=math.degrees(math.asin(max(-1.0,min(1.0,z))))
 if x>0: a=360.0-a
 return a
def pan_from_headings(a,b):
 mode=1
 if a <= 180.0 and b > 180.0:
  d=360.0-b+a
  if d>180.0: d=-(360.0-d)
 else:
  d=-(360.0-a+b)
  if d < -180.0: d += 360.0
 if d>90.0: mode=2; d=180.0-d
 elif d < -90.0: mode=2; d=-180.0-d
 return math.trunc(d*63.0/90.0+64.0),mode,d
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe');ap.add_argument('--out',required=True);a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); sha=hashlib.sha256(raw).hexdigest(); b=obj1(raw)
 inv={
 'sqrt_helper_nonnegative_fsqrt':b[0x36d86:0x36dbb].find(bytes.fromhex('d9fa'))>=0,
 'heading_forms_one_minus_x2':b[0x30d7a:0x30d84]==bytes.fromhex('d9c0d8c8d9e8dee1b001'),
 'heading_calls_sqrt_helper':b[0x30d84:0x30d89]==bytes.fromhex('e8fd5f0000'),
 'atan_helper_is_fxch_fpatan_ret':b[0x472d9:0x472de]==bytes.fromhex('d9c9d9f3c3'),
 'heading_calls_atan_helper':b[0x30d8d:0x30d94]==bytes.fromhex('d9c9e845650100'),
 'wrapper_single_double':b[0x30d9e:0x30daa]==bytes.fromhex('dd442404e8d3ffffffc20800'),
 'caller_uses_z_component':b[0xcff5:0xcffe]==bytes.fromhex('d945d883ec08dd1c24'),
 'caller_quadrant_uses_x_sign':b[0xd012:0xd01c]==bytes.fromhex('d9eed85dd0dfe09e730c'),
 }
 if sha!=EXPECTED or not all(inv.values()): raise SystemExit('v61 invariant failure')
 vec=[]
 listener=(-1.0,0.0)
 lh=heading(*listener)
 for name,x,z in [('front',-1,0),('front_right',-1,1),('right',0,1),('rear_right',1,1),('rear',1,0),('rear_left',1,-1),('left',0,-1),('front_left',-1,-1)]:
  sh=heading(x,z); p,m,d=pan_from_headings(lh,sh); vec.append({'case':name,'listener_xz':listener,'source_direction_xz':[x,z],'listener_heading_deg':lh,'source_heading_deg':sh,'folded_angle_deg':d,'pan':p,'mode_divisor':m})
 out={'schema':'openazrael.heading_helpers','version':61,'status':'PASS','exe_sha256':sha,'invariants':inv,
 'identities':{
  '0x36D86':'HIGH: x87 square-root helper; normal nonnegative path executes FSQRT.','0x472D9':'VERIFIED instruction semantics: FXCH ST(1); FPATAN; RET.','0x30D7A':'HIGH: asin-equivalent for normal |x|<=1 path, constructed as pi/2 - atan2(sqrt(1-x^2), x).','0x30D9E':'HIGH: stack-double wrapper around 0x30D7A.'},
 'xyz_heading':{'confidence':'HIGH','horizontal_axes':'X/Z; Y is explicitly zeroed before normalization','formula':'normalize X/Z; angle=degrees(asin(z)); if x>0, angle=360-angle','note':'This reproduces the instruction-level normal path. Zero-length vectors remain a separate edge-case/HOLD.'},
 'golden_xyz_vectors':vec,
 'remaining_holds':['zero-length horizontal heading behavior through normalization helper','runtime startup/default value of master-volume word','bit-exact x87 rounding at all boundary values; reference uses host math'],
 'decision':'Close normal nonzero XYZ -> heading helper semantics as HIGH and permit a non-active Classic reference spatializer. Keep live Godot AudioStreamPlayer3D path unchanged until parity harness/coordinate calibration.'}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8'); print(json.dumps({'status':'PASS','invariants':len(inv),'xyz_vectors':len(vec),'heading':'HIGH'},indent=2))
if __name__=='__main__':main()
