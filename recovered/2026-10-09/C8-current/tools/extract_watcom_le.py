#!/usr/bin/env python3
"""Locate and describe a bound Watcom LE module without redistributing its code."""
from pathlib import Path
import argparse, hashlib, json, struct

def u16(d,o): return struct.unpack_from('<H',d,o)[0]
def u32(d,o): return struct.unpack_from('<I',d,o)[0]

def plausible(d,o):
    if d[o:o+2] != b'LE' or o+0xAC>len(d): return False
    try:
        return (d[o+2]==0 and d[o+3]==0 and u16(d,o+8) in (1,2,3,4) and
                1 <= u32(d,o+0x14) < 100000 and
                u32(d,o+0x28) in (0x1000,0x2000,0x4000) and
                1 <= u32(d,o+0x44) < 1024 and
                0 < u32(d,o+0x40) < 0x100000 and
                0 < u32(d,o+0x80) < len(d))
    except Exception: return False

def find_le(d):
    out=[]; p=0
    while True:
        p=d.find(b'LE',p)
        if p<0: break
        if plausible(d,p): out.append(p)
        p+=2
    return out

def parse_fixup_count(le):
    n=u32(le,0x14); fpt=u32(le,0x68); frt=u32(le,0x6c)
    page=[u32(le,fpt+4*i) for i in range(n+1)]
    # Structural parser compatible with the record shapes used in this executable.
    count=0; errors=[]
    for pg in range(n):
        p=frt+page[pg]; end=frt+page[pg+1]
        while p<end:
            s=p
            try:
                typ=le[p]; fl=le[p+1]; p+=2
                islist=bool(typ&0x20)
                if islist: nsrc=le[p]; p+=1
                else: p+=2; nsrc=0
                p += 2 if fl&0x40 else 1
                target=fl&3
                if target==0:
                    if (typ&0xf)!=2: p += 4 if fl&0x10 else 2
                    if fl&0x04: p += 4 if fl&0x20 else 2
                elif target==1:
                    p += 2 if fl&0x40 else 1
                    if fl&0x80: p+=1
                    else: p += 4 if fl&0x10 else 2
                    if fl&0x04: p += 4 if fl&0x20 else 2
                elif target==2:
                    p += 2 if fl&0x40 else 1
                    p += 4 if fl&0x10 else 2
                    if fl&0x04: p += 4 if fl&0x20 else 2
                else:
                    p += 2 if fl&0x40 else 1
                    if fl&0x04: p += 4 if fl&0x20 else 2
                if islist: p += 2*nsrc
                if p<=s or p>end: raise ValueError((s,p,end))
                count+=1
            except Exception as e:
                errors.append({'page_index':pg,'offset':hex(s),'error':repr(e)})
                break
    return count, errors

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('exe')
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    d=Path(a.exe).read_bytes(); candidates=find_le(d)
    if not candidates: raise SystemExit('No plausible LE header found')
    o=candidates[0]; le=d[o:]
    object_table=u32(le,0x40); object_count=u32(le,0x44)
    objs=[]
    for i in range(object_count):
        size,base,flags,mapidx,mapsize,res=struct.unpack_from('<IIIIII',le,object_table+i*24)
        objs.append({'number':i+1,'virtual_size':size,'relocation_base':hex(base),'flags':hex(flags),'first_page':mapidx,'page_count':mapsize})
    fixups,fixerrors=parse_fixup_count(le)
    dp=u32(le,0x80); ps=u32(le,0x28)
    # Object 2 is AUTODS in this executable. Record a few diagnostic strings by offset only.
    autods=u32(le,0x94)
    strings={}
    if 1<=autods<=len(objs):
        ob=objs[autods-1]
        data_start=dp+(ob['first_page']-1)*ps
        blob=le[data_start:data_start+ob['virtual_size']]
        for label in [b'TOO MANY TIMERS IN OPERATION',b'AddNewTimer',b'TIMER %f NOT FOUND',b'RemoveTimer',b'Invalid operation %d',b'ProcessResponses',b'WORLDENG::ProcessObjectEvent',b'RegisterTimer',b'ITimer']:
            x=blob.find(label)
            if x>=0: strings[label.decode('ascii')]=hex(x)
    info={
      'input':Path(a.exe).name,
      'sha256':hashlib.sha256(d).hexdigest(),
      'bound_file_size':len(d),
      'le_header_file_offset':hex(o),
      'le_candidates':[hex(x) for x in candidates],
      'cpu_type':u16(le,0x08),'os_type':u16(le,0x0a),
      'module_pages':u32(le,0x14),'page_size':u32(le,0x28),'last_page_size':u32(le,0x2c),
      'entry_object':u32(le,0x18),'entry_eip':hex(u32(le,0x1c)),
      'stack_object':u32(le,0x20),'stack_esp':hex(u32(le,0x24)),
      'object_count':object_count,'objects':objs,
      'autods_object':autods,
      'object_page_map_offset':hex(u32(le,0x48)),
      'fixup_page_table_offset':hex(u32(le,0x68)),
      'fixup_record_table_offset':hex(u32(le,0x6c)),
      'data_pages_offset_from_le_start':hex(dp),
      'data_pages_bound_file_offset':hex(o+dp),
      'parsed_fixup_records':fixups,'fixup_parse_errors':fixerrors,
      'autods_diagnostic_string_offsets':strings,
      'notes':[
        'The LE offsets are relative to the LE module start after unbinding; the bound file embeds the LE module after its DOS/4GW wrapper.',
        'The original executable bytes are intentionally not copied into the OpenAzrael checkpoint.',
        'Fixup records parse structurally, but exact source-xref address interpretation remains under validation.'
      ]
    }
    Path(a.out).write_text(json.dumps(info,indent=2),encoding='utf-8')
    print(json.dumps(info,indent=2))
if __name__=='__main__': main()
