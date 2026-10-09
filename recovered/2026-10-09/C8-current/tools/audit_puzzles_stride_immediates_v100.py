#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json
ap=argparse.ArgumentParser(); ap.add_argument('--exe',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
b=Path(a.exe).read_bytes(); LE=0x37d4c; DP=LE+0x3a400; VS=1173723; o=b[DP:DP+VS]
# x86 encodings with unambiguous imm32 payloads useful for a conservative scan
enc={
 190:[('push_imm32',b'\x68\xbe\x00\x00\x00'),('mov_eax_imm32',b'\xb8\xbe\x00\x00\x00'),('mov_ecx_imm32',b'\xb9\xbe\x00\x00\x00'),('mov_edx_imm32',b'\xba\xbe\x00\x00\x00'),('mov_ebx_imm32',b'\xbb\xbe\x00\x00\x00')],
 128:[('push_imm32',b'\x68\x80\x00\x00\x00'),('mov_eax_imm32',b'\xb8\x80\x00\x00\x00'),('mov_ecx_imm32',b'\xb9\x80\x00\x00\x00'),('mov_edx_imm32',b'\xba\x80\x00\x00\x00'),('mov_ebx_imm32',b'\xbb\x80\x00\x00\x00')],
 32:[('push_imm32',b'\x68\x20\x00\x00\x00'),('mov_eax_imm32',b'\xb8\x20\x00\x00\x00'),('mov_ecx_imm32',b'\xb9\x20\x00\x00\x00'),('mov_edx_imm32',b'\xba\x20\x00\x00\x00'),('mov_ebx_imm32',b'\xbb\x20\x00\x00\x00')],
}
res={}
for val, pats in enc.items():
 hits=[]
 for name,p in pats:
  pos=0
  while True:
   i=o.find(p,pos)
   if i<0: break
   hits.append({'offset':i,'offset_hex':hex(i),'encoding':name,'bytes':p.hex(),'context':o[max(0,i-16):i+len(p)+24].hex()}); pos=i+1
 res[str(val)]=sorted(hits,key=lambda x:x['offset'])
# proximity: any 190 candidate within 0x400 of 128/32 candidates?
h190=[x['offset'] for x in res['190']]; h128=[x['offset'] for x in res['128']]; h32=[x['offset'] for x in res['32']]
prox=[]
for x in h190:
 for label,hs in [('128',h128),('32',h32)]:
  near=sorted((abs(y-x),y) for y in hs if abs(y-x)<=0x400)
  if near: prox.append({'stride190':hex(x),'other':label,'distance':near[0][0],'other_offset':hex(near[0][1])})
out={'version':100,'exe_sha256':hashlib.sha256(b).hexdigest(),'object1':{'file_offset':hex(DP),'virtual_size':VS},'scan':'conservative exact imm32 x86 encodings only; not a full disassembly','hits':res,'proximity_within_0x400':prox,'interpretation':{'VERIFIED':f"Conservative object1 scan found {len(h190)} exact imm32 instruction candidates for 190, {len(h128)} for 128, and {len(h32)} for 32 in the selected MOV/PUSH encodings.",'HIGH':'The rare immediate 190 sites do not form a convincing 190/128/32 loader fingerprint. Static stride-constant hunting is therefore not sufficient to identify the PUZZLES.DAT loader.','HOLD':'This does not prove the loader lacks these constants: it may use imm8 arithmetic, register-computed sizes, library reads, generated offsets, or a different runtime representation. No loader address is claimed.'}}
Path(a.out).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'counts':{k:len(v) for k,v in res.items()},'proximity':len(prox)},indent=2))
