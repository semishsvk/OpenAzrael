#!/usr/bin/env python3
import argparse,hashlib,json,math,struct
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def u32(d,o): return struct.unpack_from('<I',d,o)[0]
def obj1(raw):
 le=raw[0x37d4c:]; ot=u32(le,0x40); dp=u32(le,0x80); size=u32(le,ot); return bytes(le[dp:dp+size])
def ext80(bb):
 sig=int.from_bytes(bb[:8],'little'); se=int.from_bytes(bb[8:10],'little'); sign=-1 if se>>15 else 1; exp=se&0x7fff
 return sign*(sig/(1<<63))*2.0**(exp-16383)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe');ap.add_argument('--out',required=True);a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); sha=hashlib.sha256(raw).hexdigest(); b=obj1(raw)
 cbytes=b[0x30d70:0x30d7a]; c=ext80(cbytes)
 inv={
  'sha':sha==EXPECTED,
  'helper_constant_literal_is_adjacent':cbytes.hex()=='00c06821a2da0fc9ff3f',
  'helper_constant_is_pi_over_2':abs(c-math.pi/2)<1e-15,
  'normal_sqrt_returns_al_zero':b[0x36db3:0x36db7]==bytes.fromhex('d9fab000'),
  'normal_path_executes_post_atan_subtraction':b[0x30d89:0x30d9d]==bytes.fromhex('3c007510d9c9e8456501002edb2d18380300dee1'),
  'fpatan_helper_exact':b[0x472d9:0x472de]==bytes.fromhex('d9c9d9f3c3'),
 }
 if not all(inv.values()): raise SystemExit(inv)
 out={'schema':'openazrael.heading_constant_resolution','version':63,'status':'PASS','exe_sha256':sha,'invariants':inv,
 'literal':{'object1_offset':'0x30D70','bytes':cbytes.hex(),'decoded_ext80':c,'identity':'PI_OVER_2','confidence':'VERIFIED'},
 'x87_model':{'normal_path':'input x; form 1-x^2; sqrt; FXCH; FPATAN; load pi/2; FSUBRP','result':'asin(x) for normal finite |x|<=1 path','confidence':'HIGH'},
 'correction_to_v62':{'post_fpatan_constant':'RESOLVED_V63_PI_OVER_2','helper_normal_path':'HIGH_ASIN_EQUIVALENT','complete_xyz_heading':'STILL_HOLD','reason':'The helper itself is now closed, but the caller-level 0/360 opposite-cardinal collision remains real. Therefore the unresolved issue is caller semantics/convention, not the helper constant.'},
 'guardrail':'Do not restore v61 complete XYZ->heading. Resolve how the caller uses the 0/360 endpoint distinction and relative-angle branch before accepting cardinal semantics.',
 'next':['Symbolically execute CE29..CEF7 using raw (not modulo-normalized) 0 versus 360 endpoints.','Test listener/source cardinal pairs through the complete relative-angle and pan branch.','Only if full-pipeline cardinal outputs distinguish left/right/front/rear should XYZ->pan be promoted.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8'); print(json.dumps({'status':'PASS','constant':c,'identity':'PI_OVER_2','helper':'ASIN_EQUIVALENT_HIGH','xyz_heading':'HOLD'},indent=2))
if __name__=='__main__':main()
