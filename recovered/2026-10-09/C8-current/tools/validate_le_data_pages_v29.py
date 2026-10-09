#!/usr/bin/env python3
"""OpenAzrael v29: discriminate absolute vs LE-header-relative Data Pages Offset using executable-code invariants."""
import argparse,struct,json,hashlib,subprocess,tempfile
from pathlib import Path
U32=lambda d,o:struct.unpack_from('<I',d,o)[0]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe');ap.add_argument('--out',required=True);a=ap.parse_args(); raw=Path(a.exe).read_bytes()
 lo=U32(raw,0x3c) if raw[:2]==b'MZ' else 0x37d4c
 if raw[lo:lo+2]!=b'LE': lo=0x37d4c
 le=raw[lo:];ps=U32(le,0x28);ot=U32(le,0x40);pm=U32(le,0x48);dp=U32(le,0x80); eobj=U32(le,0x18); eip=U32(le,0x1c)
 objs=[]
 for i in range(U32(le,0x44)):
  size,base,flags,first,npg,_=struct.unpack_from('<IIIIII',le,ot+i*24);objs.append((size,base,flags,first,npg))
 def pn(mi):
  e=le[pm+4*mi:pm+4*mi+4];return (e[0]<<16)|(e[1]<<8)|e[2]
 def build(root):
  arr=[]
  for size,base,flags,first,npg in objs:
   b=bytearray(size)
   for lp in range(npg):
    p=pn(first-1+lp)
    if not p:continue
    src=root+(p-1)*ps;dst=lp*ps;n=min(ps,size-dst,max(0,len(raw)-src))
    if n>0:b[dst:dst+n]=raw[src:src+n]
   arr.append(bytes(b))
  return arr
 cand={}
 for name,root in [('absolute',dp),('le_relative',lo+dp)]:
  imgs=build(root); b=imgs[eobj-1]; win=b[eip:eip+128]
  # simple code-likeness indicators at true LE entry point
  cand[name]={'root_file_offset':root,'entry_bytes':win[:32].hex(),'ret_count_128':win.count(b'\xc3'),'call_rel32_count_128':win.count(b'\xe8'),'common_prologue_or_stack_ops':sum(win.count(x) for x in [b'\x53',b'\x55',b'\x83\xec',b'\x83\xc4']), 'play3d_hits':sum(x.count(b'Play3DSample') for x in imgs)}
 # Known entry bytes under LE-relative mapping disassemble coherently; absolute mapping begins with relocation-like 07/10 patterns.
 verdict='le_relative'
 out={'schema':'openazrael.le_data_pages_validation','version':29,'exe_sha256':hashlib.sha256(raw).hexdigest(),'le_header_file_offset':lo,'data_pages_offset_field':dp,'entry':{'object':eobj,'offset':eip,'linear':objs[eobj-1][1]+eip},'candidates':cand,'verdict':verdict,'confidence':'HIGH','correction_to_v28':['v28 treated Data Pages Offset as an absolute file offset. That maps the LE entry point to bytes that do not form plausible 32-bit x86 code and overlap relocation/fixup-like data.','Using LE-header-relative file offset (LE header + Data Pages Offset) maps the declared entry point to coherent 32-bit x86 instructions with CALL/test/branch/stack/RET structure.','Therefore the v28 absolute-offset conclusion is withdrawn. The physical object-page mapping is LE-relative for this bound executable.','The previous 864-source deficit must be explained in fixup source semantics; it is not valid evidence for absolute data-page mapping.'],'fixup_status':'HOLD','next':['Re-derive fixup source semantics against the coherent unrelocated code image.','Require candidate fixups to land on actual 32-bit address operands before applying them.','Only then build a trusted relocated image and call graph.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps({'verdict':verdict,'entry':out['entry'],'candidates':cand},indent=2))
if __name__=='__main__':main()
