#!/usr/bin/env python3
import argparse,struct,json,hashlib
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
U32=lambda d,o:struct.unpack_from('<I',d,o)[0]
D64=lambda d,o:struct.unpack_from('<d',d,o)[0]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe');ap.add_argument('--out',required=True);a=ap.parse_args()
 raw=Path(a.exe).read_bytes();sha=hashlib.sha256(raw).hexdigest();lo=0x37d4c
 if sha!=EXPECTED or raw[lo:lo+2]!=b'LE': raise SystemExit('unexpected image')
 le=raw[lo:];dp=U32(le,0x80);ot=U32(le,0x40);o1size=U32(le,ot);o1=le[dp:dp+o1size]
 # The 0xCDE1 code references a regular qword placeholder lattice. Independently, the tail
 # of object 1 contains an equally-spaced literal lattice whose values exactly match the math.
 ph=[0x1954,0x195c,0x1964,0x196c,0x1974,0x197c,0x1984,0x198c,0x1994]
 lit0=0x11deac
 vals=[D64(o1,lit0+8*i) for i in range(len(ph))]
 expected=[180.0,3.141592,360.0,-180.0,90.0,-90.0,63.0,64.0,15000.0]
 refs={
  '180':[0xce2e,0xce4e,0xce76,0xcece,0xd081],
  'pi':[0xd009,0xd05f],
  '360':[0xce65,0xce7f,0xce8c,0xceb0,0xd01c,0xd072],
  '-180':[0xcea2,0xceeb],
  '90':[0xcebc,0xcf00],
  '-90':[0xced9],
  '63':[0xcefa],
  '64':[0xcf06],
  '15000':[0xcf4b],
 }
 checks={
  'placeholder_qword_lattice':ph==list(range(0x1954,0x1995,8)),
  'literal_qword_lattice':all(abs(vals[i]-expected[i])<1e-12 for i in range(len(vals))),
  'literal_180_exact':vals[0]==180.0,
  'literal_360_exact':vals[2]==360.0,
  'literal_63_64_exact':vals[6:8]==[63.0,64.0],
  'literal_15000_exact':vals[8]==15000.0,
  'pi_literal_matches_6dp':abs(vals[1]-3.141592)<1e-15,
  'angle_conversion_pattern':o1[0xd003:0xd00f].hex()=='dc0d54190000dc355c190000',
  'quadrant_360_pattern':o1[0xd01c:0xd028].hex()=='dd0564190000dc65dcdd5ddc',
  'pan_scale_pattern':o1[0xcefa:0xcf0c].hex()=='dc0d84190000dc3574190000dc058c190000',
  'distance_15000_pattern':o1[0xcf4b:0xcf54].hex()=='dd0594190000dc75e4',
 }
 if not all(checks.values()): raise SystemExit(checks)
 mapping={hex(ph[i]):{'literal_object1_offset':hex(lit0+8*i),'value':vals[i]} for i in range(len(ph))}
 out={'schema':'openazrael.audio_3d_constant_lattice','version':58,'status':'PASS','exe_sha256':sha,'invariants':checks,
 'mapping':mapping,'instruction_reference_groups':refs,
 'findings':[
  'The 3D core references nine qword placeholders at 0x1954..0x1994 in exact 8-byte steps.',
  'Object 1 independently contains a nine-qword literal table at 0x11DEAC..0x11DEEC with values 180, 3.141592, 360, -180, 90, -90, 63, 64, 15000 in the same order.',
  'The instruction semantics independently fit that ordering: 180/pi converts radians to degrees; 360 and +/-180/90 implement angular wrapping/quadrants; 63/90 + 64 implement pan scaling/centering; 15000 is divided by distance before the gain clamp.',
  'This recovers the numeric constant lattice without trusting the quarantined v27-v36 operand-level LE xref graph.'
 ],
 'confidence':{'literal_table_values':'VERIFIED','ordered_placeholder_to_literal_lattice':'HIGH','K_DISTANCE_15000':'HIGH','angle_constants':'HIGH','exact_global_volume_scalar':'HOLD'},
 'decision':'ACCEPT numeric 3D constant lattice for forensic model; keep global-volume variable and complete golden-vector parity HOLD until the remaining control flow is modeled/tested.',
 'supersedes':['v57 implication that exact 3D numeric constants necessarily require full loader relocation before any can be recovered'],
 'next':['Translate the complete pan branch into a side-effect-free reference function and generate golden vectors.','Recover the global-volume word used at raw placeholder 0x615e independently; do not infer it from the constant lattice.','Only after golden-vector tests, wire exact Classic pan/attenuation into Godot runtime.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps({'status':'PASS','checks':len(checks),'K_DISTANCE':15000,'constants':len(mapping)},indent=2))
if __name__=='__main__':main()
