#!/usr/bin/env python3
from pathlib import Path
import argparse, json, re
from collections import Counter, defaultdict

def strings(data, minlen=3):
    out=[]; start=None
    for i,b in enumerate(data+b'\x00'):
        if 32 <= b < 127:
            if start is None: start=i
        else:
            if start is not None and i-start>=minlen:
                out.append(data[start:i].decode('ascii','replace'))
            start=None
    return out

def parse_flag_names(path):
    d=Path(path).read_bytes()
    out=set()
    for s in strings(d):
        m=re.match(r'^([^,]+),\s*[01]$',s.strip())
        if m: out.add(m.group(1))
    return out

def token_inventory(path):
    d=Path(path).read_bytes()
    return set(strings(d))

def stem_inventory(root, ext):
    return {p.stem.lower() for p in Path(root).rglob('*') if p.is_file() and p.suffix.lower()==ext.lower()}

def scan_actions(data):
    recs=[]
    for i in range(len(data)-4):
        if data[i:i+2] != b'\x10\x00':
            continue
        opcode=data[i+2]
        j=i+3
        k=data.find(b'\x00',j,min(j+96,len(data)))
        if k < 0 or k==j: continue
        raw=data[j:k]
        if len(raw)>64 or any(c<32 or c>=127 for c in raw): continue
        token=raw.decode('ascii')
        # avoid obvious accidental fragments; retain identifiers, media stems, Event-like tokens for audit
        if not re.search(r'[A-Za-z]', token): continue
        recs.append({'offset':i,'offset_hex':hex(i),'opcode':opcode,'opcode_hex':hex(opcode),'token':token})
    return recs

def classify(token, flags, objects, wavs, movs):
    t=token.lower()
    kinds=[]
    if token in flags: kinds.append('persistent_flag')
    if token in objects: kinds.append('retail_object_token')
    if t in wavs: kinds.append('wav_stem')
    if t in movs or t.endswith('.mov'): kinds.append('movie')
    if token.startswith('R') and any(c.isdigit() for c in token[:4]): kinds.append('room_state_or_object')
    return kinds or ['unclassified']

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--puzzles',required=True)
    ap.add_argument('--flags',required=True)
    ap.add_argument('--objects',required=True)
    ap.add_argument('--asset-root',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    data=Path(a.puzzles).read_bytes()
    flags=parse_flag_names(a.flags)
    objects=token_inventory(a.objects)
    wavs=stem_inventory(a.asset_root,'.wav')
    movs=stem_inventory(a.asset_root,'.mov')
    recs=scan_actions(data)
    by=defaultdict(list)
    for r in recs:
        r['classification']=classify(r['token'],flags,objects,wavs,movs)
        by[r['opcode_hex']].append(r)
    summary=[]
    for op,rs in sorted(by.items(), key=lambda x:int(x[0],16)):
        cats=Counter(c for r in rs for c in r['classification'])
        summary.append({
            'opcode':op,'count':len(rs),'classification_counts':dict(cats),
            'sample_tokens':list(dict.fromkeys(r['token'] for r in rs))[:24]
        })
    evidence={
      'source':str(a.puzzles),
      'pattern':'10 00 <opcode-byte> <printable NUL-terminated token>',
      'warning':'Pattern corpus is evidence, not yet a full PUZZLES.DAT grammar; accidental byte matches remain possible.',
      'summary':summary,
      'records':recs,
      'high_confidence':{
        '0x28':'play sound/sample family: all strong examples resolve to WAV stems',
        '0x22':'movie operation family: observed tob.mov',
        '0x04':'persistent-flag operation family: many targets are independently present in retail FLAGLIST.DAT'
      },
      'hypotheses':{
        '0x19':'authored object-position/state transition family; tapestry placement and R8 lens place/look dominate evidence',
        '0x18':'object animation/change operation family; DoorR8 is a strong example',
        '0x17':'object/control interaction family',
        '0x07_0x08':'inventory/object-transfer families; direction/add-vs-remove not yet proven'
      }
    }
    Path(a.out).write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print(json.dumps({'records':len(recs),'opcodes':len(by),'summary':summary},indent=2))
if __name__=='__main__': main()
