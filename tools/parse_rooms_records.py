#!/usr/bin/env python3
"""Evidence-first ROOMS.DAT demo record slicer.

Confirmed observation: within the R1/R7 demo object tables, consecutive object
records begin exactly 0x3c (60) bytes apart. This tool does NOT assign meanings
to the non-name bytes yet; it preserves them for differential analysis.
"""
from pathlib import Path
import json, re, struct

HERE=Path(__file__).resolve().parents[1]
DATA=HERE/'data'/'ROOMS.DAT'
b=DATA.read_bytes()

TABLES=[
    {'room':'R1Demo','start':0x1517A,'end':0x1531E},
    {'room':'R7Demo','start':0x15540,'end':0x158C4},
]
REC=0x3C

def cstr(x):
    return x.split(b'\0',1)[0].decode('latin1','replace')

def printable_runs(x):
    return [m.group().decode('latin1') for m in re.finditer(rb'[ -~]{4,}',x)]

def u32s(x):
    return [f'0x{struct.unpack_from("<I",x,i)[0]:08X}' for i in range(0,len(x)-3,4)]

out={'source':'ROOMS.DAT','record_size':60,'record_size_hex':'0x3C','status':'confirmed for the sliced demo tables; field semantics unresolved','tables':[]}
for t in TABLES:
    recs=[]
    for off in range(t['start'],t['end'],REC):
        raw=b[off:off+REC]
        if len(raw)<REC: break
        recs.append({'offset':f'0x{off:X}','name':cstr(raw),'ascii_runs':printable_runs(raw),'raw_hex':raw.hex(),'u32_le':u32s(raw)})
    out['tables'].append({**t,'start':f"0x{t['start']:X}",'end':f"0x{t['end']:X}",'records':recs})

p=HERE/'data'/'rooms_demo_records.json'
p.write_text(json.dumps(out,indent=2),encoding='utf-8')
print(f'wrote {p}')
for t in out['tables']:
    print(t['room'],len(t['records']))
    for r in t['records']: print(' ',r['offset'],r['name'])
