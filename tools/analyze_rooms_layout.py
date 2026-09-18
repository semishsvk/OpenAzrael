#!/usr/bin/env python3
from pathlib import Path
import json,re,struct
base=Path(__file__).resolve().parents[1]
data=(base/'data/ROOMS.DAT').read_bytes()
names=['corridordoor1','corridordoor2','R1WallText','R1Boulder','R1P1','TongR6','R1DemoTapPiece1','R7Key','R7Pipes','R7Well','R7Well1','R7Well2','HotInsertLever','HotMoveWheel','HotPipe','HotRotateWheel','ColdInsertLever','ColdMoveWheel','ColdPipe','ColdRotateWheel','RustyTongR6','WellRoomdoor']
rows=[]
for name in names:
    b=name.encode(); off=data.find(b,0x15000)
    if off<0: continue
    nxt=min([x for n in names if (x:=data.find(n.encode(),max(0x15000,off+len(b))))>off] or [len(data)])
    # bytes only to next known label; this is evidence span, explicitly NOT a record
    span=data[off:nxt]
    ptrs=[]
    for i in range(0,max(0,len(span)-3)):
        v=struct.unpack_from('<I',span,i)[0]
        if 0x00400000 <= v <= 0x006fffff:
            ptrs.append({'rel':i,'value':f'0x{v:08X}'})
    strings=[m.group().decode('ascii','replace') for m in re.finditer(rb'[ -~]{4,}',span)]
    rows.append({'name':name,'offset':f'0x{off:X}','next_known_offset':f'0x{nxt:X}','distance_to_next_known':nxt-off,'ascii_runs':strings[:8],'pointer_like_windows':ptrs[:20],'span_hex':span[:128].hex()})
out={'source':'ROOMS.DAT','status':'evidence scan; NO fixed record size asserted','correction':'v9 0x3C fixed-record interpretation is rejected: 0x3C stepping cuts through prose/string payload for multiple labels. The regular spacing is not sufficient evidence of record boundaries.','objects':rows}
(base/'data/rooms_layout_evidence_v10.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('wrote',base/'data/rooms_layout_evidence_v10.json')
for r in rows: print(r['offset'],r['name'],'next distance',r['distance_to_next_known'])
