#!/usr/bin/env python3
import argparse,hashlib,json,struct
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def u32(d,o): return struct.unpack_from('<I',d,o)[0]
def obj1(raw):
 lo=0x37d4c; le=raw[lo:]; ot=u32(le,0x40); dp=u32(le,0x80); size=u32(le,ot); return bytes(le[dp:dp+size])
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); sha=hashlib.sha256(raw).hexdigest(); b=obj1(raw)
 c={
 'heading_wrapper_loads_double':b[0x30d9e:0x30da7]==bytes.fromhex('dd442404e8d3ffffff'),
 'heading_core_square_one_minus':b[0x30d7a:0x30d84]==bytes.fromhex('d9c0d8c8d9e8dee1b001'),
 'heading_core_helper1':b[0x30d84]==0xe8 and b[0x30d89:0x30d8d]==bytes.fromhex('3c007510'),
 'heading_core_helper2':b[0x30d8d:0x30d94]==bytes.fromhex('d9c9e845650100'),
 'caller_deg_conversion':b[0xcffe:0xd00f]==bytes.fromhex('e89b3d0200dc0d54190000dc355c190000'),
 'caller_quadrant_x_sign':b[0xd012:0xd028]==bytes.fromhex('d9eed85dd0dfe09e730cdd0564190000dc65dcdd5ddc'),
 'global_volume_signed_word':b[0xcf7b:0xcf82]==bytes.fromhex('0fbf055e610000'),
 'ui_clamp_87':b[0x220a:0x2213]==bytes.fromhex('66c7055e6100005700'),
 'ui_scale_87_to_127':b[0x2213:0x2231]==bytes.fromhex('8b155c610000c1fa106bd27fbb5700000089d0c1fa1ff7fb66a35e610000'),
 'volume_saved_before_transform':b[0x5091:0x509d]==bytes.fromhex('66a15e61000066a300230200'),
 }
 if sha!=EXPECTED or not all(c.values()): raise SystemExit('v60 invariant failure')
 out={'schema':'openazrael.heading_global_volume','version':60,'status':'PASS','exe_sha256':sha,'invariants':c,
 'heading':{
  'confidence':'HIGH_STRUCTURE__TRIG_IDENTITY_PROBABLE',
  'facts':['0x30D9E loads one double argument and delegates to 0x30D7A.','0x30D7A forms 1-x^2, calls a math helper, then a second transcendental helper and conditionally subtracts from a long-double constant.','0xCFFE/D054 use the result and convert radians to degrees with 180/pi, then use the sign of horizontal X to choose the 360-degree quadrant.'],
  'interpretation':'The dataflow is consistent with an inverse-trigonometric heading helper (asin/acos-equivalent construction), but exact helper/API identity remains PROBABLE until 0x36D86 and 0x472D9 are independently identified.',
  'xyz_to_heading_status':'HIGH_GEOMETRIC_STRUCTURE; exact transcendental helper names PROBABLE'
 },
 'global_volume':{
  'confidence':'HIGH',
  'runtime_field':'signed WORD at unrelocated operand placeholder 0x615E in the analyzed object image',
  'audio_use':'0xCDE1 multiplies 3D gain by this value and divides by 99 before AIL_set_sample_volume.',
  'ui_mapping':'A UI/control path clamps a source value to 0..87 and scales it by 127/87 before storing the result into the 0x615E word.',
  'derived_range':'0..127 for this UI path',
  'default':'HOLD: no unique startup default established by this audit',
  'important_correction':'Do not hard-code 99 as master volume. 99 is the spatial gain ceiling/normalizer; the master-volume field has an independently evidenced 0..127 UI-scaled path.'
 },
 'next':['Identify 0x36D86 and 0x472D9 independently to close exact normalized X/Z -> heading semantics.','Trace startup/config load for the master-volume word to establish default and persistence.','Then implement the complete Classic reference spatializer and golden XYZ vectors.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8'); print(json.dumps({'status':'PASS','invariants':sum(c.values()),'total':len(c),'global_volume_range':'0..127','heading':'HIGH_STRUCTURE'},indent=2))
if __name__=='__main__':main()
