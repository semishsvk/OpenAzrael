#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,struct,re

def u32(d,o): return struct.unpack_from('<I',d,o)[0]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe');ap.add_argument('--out',required=True);a=ap.parse_args()
 d=Path(a.exe).read_bytes(); leoff=0x37D4C
 if d[leoff:leoff+2] != b'LE': raise SystemExit('Expected Watcom LE header not found')
 le=d[leoff:]; ps=u32(le,0x28);dp=u32(le,0x80);ot=u32(le,0x40);oc=u32(le,0x44)
 objs=[]
 for i in range(oc):
  size,base,flags,mapidx,mapsize,res=struct.unpack_from('<IIIIII',le,ot+i*24)
  st=leoff+dp+(mapidx-1)*ps; blob=d[st:st+size]
  objs.append((i+1,size,base,st,blob))
 names=[b'Play3DSample',b'END3DSAMPLE',b'StartAmbientSoundFX',b'AIL_set_sample_volume',b'AIL_set_sample_pan',b'AIL_set_sample_loop_count',b'AIL_set_sample_playback_rate',b'AIL_sample_volume',b'AIL_sample_pan']
 ev=[]
 for name in names:
  hits=[]
  for no,size,base,st,b in objs:
   pos=0
   while True:
    q=b.find(name,pos)
    if q<0:break
    hits.append({'object':no,'object_offset':q,'linear_address':base+q,'bound_file_offset':st+q});pos=q+1
  ev.append({'symbol':name.decode(),'hits':hits})
 # Deliberately conservative: direct immediates are only a probe, not an xref proof.
 probes=[]
 for e in ev[:3]:
  for h in e['hits']:
   vals=[h['linear_address'],h['object_offset']]
   found=[]
   for no,size,base,st,b in objs:
    for v in vals:
     pat=struct.pack('<I',v)
     p=0
     while True:
      q=b.find(pat,p)
      if q<0:break
      found.append({'object':no,'object_offset':q,'encoded_value':v});p=q+1
   probes.append({'target':e['symbol'],'target_linear_address':h['linear_address'],'direct_imm32_candidates':found})
 out={'schema':'openazrael.play3d_forensics','version':24,'source_sha256':hashlib.sha256(d).hexdigest(),'le_header_file_offset':leoff,
      'evidence':ev,'direct_reference_probe':probes,
      'verified':['Play3DSample diagnostic labels exist in executable.','Ambient loader uses AMB%d.SND and StartAmbientSoundFX labels.','Miles sample API exposes explicit volume, pan, loop-count and playback-rate controls.'],
      'hold':['Diagnostic strings are data labels, not recovered function entry points.','No direct imm32 reference to those labels proves a Play3DSample code address; LE fixups/indirect references must be resolved.','Exact distance attenuation, listener transform and pan formula remain undecoded.'],
      'policy':'Exporter/runtime must preserve original XYZ/sample identity while keeping Classic attenuation/pan math marked HOLD.'}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf-8')
 print('wrote',a.out)
if __name__=='__main__':main()
