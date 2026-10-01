#!/usr/bin/env python3
import json,re,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]

def parse_maps(p):
    rooms={}; cur=None
    for raw in p.read_text('latin1').splitlines():
        s=raw.strip()
        if not s or s.startswith('//'): continue
        m=re.match(r'ROOM\s+(\d+)\s*(.*)',s,re.I)
        if m:
            cur={'map_id':int(m.group(1)),'name':m.group(2).strip(),'elements':[]}; rooms[cur['map_id']]=cur; continue
        if s.upper()=='END': cur=None; continue
        if cur:
            a=s.split()
            if len(a)>=3:
                e={'sprite':a[0],'x':int(a[1]),'y':int(a[2])}
                if len(a)>=4 and re.fullmatch(r'-?\d+',a[3]): e['target_map_id']=int(a[3])
                cur['elements'].append(e)
    return rooms

def strings_with_offsets(data,minlen=4):
    out=[]
    for m in re.finditer(rb'[\x20-\x7e]{%d,}'%minlen,data):
        out.append((m.start(),m.group().decode('latin1')))
    return out

maps=parse_maps(root/'data/MAPS.DAT')
data=(root/'data/ROOMS.DAT').read_bytes()
ss=strings_with_offsets(data)
markers=['R1Demo','R7Demo','R1DemoTapPiece1','EntryCoordSpaRoom','EntryCoordWashRoom','R1Entry','R1FromR2','R1FromR5','corridordoor1','corridordoor2','R7NiamhAZ','r1p1','PAPER','Parchment']
found={k:[{'offset':o,'text':s} for o,s in ss if k.lower() in s.lower()] for k in markers}
result={'source':'Azrael\'s Tear playable demo (internal resources dated Feb 1996)','maps':maps,'rooms_dat_demo_markers':found,
        'notes':['MAPS.DAT is plain-text and parsed structurally.','ROOMS.DAT is a binary/runtime-oriented structure; markers are offset evidence, not yet a claimed full parse.']}
(root/'data/demo_metadata.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(root/'data/demo_metadata.json')

