#!/usr/bin/env python3
import argparse,struct,json,hashlib
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
U32=lambda d,o:struct.unpack_from('<I',d,o)[0]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe');ap.add_argument('--out',required=True);a=ap.parse_args()
 raw=Path(a.exe).read_bytes();sha=hashlib.sha256(raw).hexdigest();lo=0x37d4c
 if sha!=EXPECTED or raw[lo:lo+2]!=b'LE':raise SystemExit('unexpected image')
 le=raw[lo:];ps=U32(le,0x28);ot=U32(le,0x40);oc=U32(le,0x44);dp=U32(le,0x80)
 objs=[]
 for i in range(oc): objs.append(struct.unpack_from('<IIIIII',le,ot+i*24))
 o1size,o1base,_,o1first,o1pages,_=objs[0];o2size,o2base,_,o2first,o2pages,_=objs[1]
 o1=le[dp+(o1first-1)*ps:dp+(o1first-1)*ps+o1size]
 o2=le[dp+(o2first-1)*ps:dp+(o2first-1)*ps+min(o2size,o2pages*ps)]
 anchors={0xcf4d:0x1994,0xcf7e:0x615e,0xd005:0x1954,0xd00b:0x195c,0xd01e:0x1964,0xd05b:0x1954,0xd061:0x195c,0xd074:0x1964}
 got={hex(k):U32(o1,k) for k in anchors}
 probes={}
 for off in [0x1724,0x6abc,0x6abe,0x1954,0x195c,0x1964,0x1994,0x615e]:
  b=o2[off:off+24] if off<len(o2) else b''
  probes[hex(off)]={'bytes':b.hex(),'ascii':''.join(chr(x) if 32<=x<127 else '.' for x in b)}
 checks={
  'two_objects':oc==2,
  'object1_base_0x10000':o1base==0x10000,
  'object2_base_0x130000':o2base==0x130000,
  'object2_first_page_0x120':o2first==0x120,
  'object2_has_0x12_initialized_pages':o2pages==0x12,
  'raw_operand_placeholders_match':all(got[hex(k)]==v for k,v in anchors.items()),
  'o2_1724_contains_AIL_volume_text':b'AIL_set_sample_volume' in o2[0x1700:0x1760],
  'o2_6abc_6abe_are_zero_initialized':o2[0x6abc:0x6ac6]==b'\0'*10,
 }
 if not all(checks.values()):raise SystemExit(checks)
 out={'schema':'openazrael.initialized_data_audit','version':57,'status':'PASS','exe_sha256':sha,'invariants':checks,
 'objects':[{'id':1,'virtual_size':o1size,'base':hex(o1base),'first_page':o1first,'pages':o1pages},{'id':2,'virtual_size':o2size,'base':hex(o2base),'first_page':o2first,'pages':o2pages,'initialized_bytes':len(o2)}],
 'operand_placeholders':{hex(k):{'raw_u32':hex(v),'classification':'UNRELOCATED_PLACEHOLDER__NOT_NUMERIC_CONSTANT'} for k,v in anchors.items()},
 'object2_probes':probes,
 'findings':['The eight 0xCDE1 disp32 operands contain small raw values (0x1954/0x195c/0x1964/0x1994/0x615e) in the embedded object image. They are relocation placeholders, not safe literal floating-point/audio constants.','Object 2 is based at 0x130000 and has only 0x12 initialized 4 KiB pages despite a much larger virtual size. The suspected 0x6abc/0x6abe region is zero-initialized in the embedded image and therefore cannot reveal the runtime 3D constants statically.','object2:0x1724 is inside the AIL_set_sample_volume diagnostic string region, independently confirming that the old v51 target interpretation cannot be used as a numeric scalar.'],
 'decision':'STATIC_INITIALIZED_DATA_PATH_EXHAUSTED_FOR_EXACT_3D_CONSTANTS; use loader relocation/emulation or runtime initialization tracing. Do not decode raw disp32 placeholders as constants.',
 'confidence':{'object_layout':'HIGH','raw_disp32_placeholder_identity':'HIGH','static_object2_probe':'HIGH','exact_3d_numeric_constants':'HOLD'},
 'next':['Trace initialization writes after relocation, or emulate the LE loader sufficiently to produce the relocated object image.','Use the eight exact x86 operand anchors as mandatory acceptance tests for any relocated-image reconstruction.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps({'status':'PASS','checks':len(checks),'decision':out['decision']},indent=2))
if __name__=='__main__':main()
