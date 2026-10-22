#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json, struct, sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_file_open_families_v103 import build_objects, LE_OFFSET
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
PRIMARY,DUP=0x103D4,0x11AB8
u16=lambda b,o:struct.unpack_from('<H',b,o)[0]
u32=lambda b,o:struct.unpack_from('<I',b,o)[0]

def edges(buf,t):
 out=[]
 for i in range(len(buf)-6):
  if buf[i] in (0xE8,0xE9) and i+5+int.from_bytes(buf[i+1:i+5],'little',signed=True)==t: out.append(i)
  if buf[i]==0x0F and 0x80<=buf[i+1]<=0x8F and i+6+int.from_bytes(buf[i+2:i+6],'little',signed=True)==t: out.append(i)
  if (buf[i]==0xEB or 0x70<=buf[i]<=0x7F) and i+2+int.from_bytes(buf[i+1:i+2],'little',signed=True)==t: out.append(i)
 return sorted(set(out))

def calls(buf,t): return [i for i in range(len(buf)-5) if buf[i]==0xE8 and i+5+int.from_bytes(buf[i+1:i+5],'little',signed=True)==t]
def immrefs(buf,v):
 n=v.to_bytes(4,'little'); out=[]; p=0
 while True:
  p=buf.find(n,p)
  if p<0:return out
  out.append(p); p+=1

def fixups(raw):
 le=raw[LE_OFFSET:]; pages=u32(le,0x14); fp=u32(le,0x68); fr=u32(le,0x6C)
 pt=[u32(le,fp+4*i) for i in range(pages+1)]; out=[]
 for page in range(pages):
  i,end=fr+pt[page],fr+pt[page+1]
  while i<end:
   src,fl=le[i],le[i+1]; i+=2; listed=bool(src&0x20); st=src&0x0F; tt=fl&3
   if listed: count=le[i]; i+=1
   else: count=1; i+=2
   obj=off=None
   if tt==0:
    obj=u16(le,i) if fl&0x40 else le[i]; i+=2 if fl&0x40 else 1
    if st!=2: off=u32(le,i) if fl&0x10 else u16(le,i); i+=4 if fl&0x10 else 2
   elif tt in (1,2):
    i+=2 if fl&0x40 else 1
    i+=1 if tt==1 and fl&0x80 else (4 if fl&0x10 else 2)
   else: i+=2 if fl&0x40 else 1
   if fl&4:i+=4 if fl&0x20 else 2
   if listed:i+=2*count
   if i>end: raise SystemExit(f'fixup parse overflow page {page}')
   out.append((tt,obj,off))
 return out

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--exe',required=True); ap.add_argument('--out'); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); objs=build_objects(raw); o1,o1p=objs[0]['virtual'],objs[0]['page_span']; fx=fixups(raw)
 inc=bytes.fromhex('66 8b 93 86 02 00 00 66 8b 83 84 02 00 00 66 39 d0 7d 0f 89 c2 42 66 89 93 84 02 00 00')
 target=lambda t:[x for x in fx if x==(0,1,t)]
 checks={
  'exe_hash':hashlib.sha256(raw).hexdigest()==EXPECTED,
  'frame_increment_primary':o1[0x10612:0x10612+len(inc)]==inc,
  'frame_increment_duplicate':o1[0x11C93:0x11C93+len(inc)]==inc,
  'no_direct_edge_primary':edges(o1,PRIMARY)==[], 'no_direct_edge_duplicate':edges(o1,DUP)==[],
  'no_internal_fixup_target_primary':target(PRIMARY)==[], 'no_internal_fixup_target_duplicate':target(DUP)==[],
  'fixup_parse_complete':len(fx)==28547,
  'movecharacters_text':o1p[0x11C558+0x2608:0x11C558+0x2608+15]==b'MoveCharacters\0',
  'movecharacters_single_immediate_xref':immrefs(o1,0x2608)==[0x13F15],
  'addtimer_calls':calls(o1,0x17DD8)==[0x18770,0x1956A], 'removetimer_calls':calls(o1,0x17E64)==[0x187A1],
  'timer_drain_mainloop':calls(o1,0x1A848)==[0x15AC],
  'timer_drain_operates_timer_ids':all(x in o1[0x1A848:0x1A8A4] for x in [bytes.fromhex('66 83 3d 7a 47 02 00'),bytes.fromhex('0f bf 90 66 47 02 00')]),
 }
 bad=[k for k,v in checks.items() if not v]
 out={'schema':'openazrael.kg001.source_update_cadence_validation','version':196,'status':'PASS' if not bad else 'FAIL','checks':checks,'failed':bad,'fixup_records':len(fx),'frame_update':{'direct_control_flow_xrefs':{'0x103D4':len(edges(o1,PRIMARY)),'0x11AB8':len(edges(o1,DUP))},'internal_le_fixup_targets':{'0x103D4':len(target(PRIMARY)),'0x11AB8':len(target(DUP))}},'conclusion':{'fixed_source_hz':None,'source_update_cadence':'HOLD_NOT_PROVEN','world_timer_classification':'WORLD_SCRIPT_TIMER_SCHEDULER','movecharacters_classification':'SCRIPT_ACTION_INTERPRETER_COMMAND_NOT_MAIN_LOOP_CLOCK'}}
 if a.out:Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps(out,indent=2,sort_keys=True)); return 1 if bad else 0
if __name__=='__main__':sys.exit(main())
