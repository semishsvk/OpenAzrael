#!/usr/bin/env python3
import json, argparse
from pathlib import Path
from collections import Counter,defaultdict

def runs(buf):
    out=[]; s=None
    for i,b in enumerate(buf):
        if 32 <= b < 127:
            if s is None: s=i
        elif s is not None:
            out.append({'offset':s,'text':buf[s:i].decode('ascii')}); s=None
    if s is not None: out.append({'offset':s,'text':buf[s:].decode('ascii')})
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--slots',required=True); ap.add_argument('--puzzles',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); src=json.load(open(a.slots)); raw=Path(a.puzzles).read_bytes()
    groups=defaultdict(list)
    for r in src['dominant_records']:
        off=r['source_offset']; slot=raw[off:off+62]
        groups[r['legacy_opcode']].append((r,slot))
    report={'version':93,'source':'puzzles_action_slot_v91.json + original PUZZLES.DAT','scope':'198 dominant 190-byte records',
      'method':'Column-alignment analysis of the full 62-byte serialized action slot. This supersedes treating all bytes after the first NUL token as one semantic residue.',
      'important_boundary':'Field boundaries below are structural byte-column observations. Names such as secondary_text/state_like are descriptive only; runtime semantics remain HOLD unless independently proven.',
      'record_count':sum(map(len,groups.values())),'opcode_groups':[]}
    for op,recs in sorted(groups.items()):
        starts=Counter(); bytes_by_col=[Counter() for _ in range(62)]
        rr=[]
        for r,s in recs:
            rs=runs(s)
            for x in rs[1:]: starts[x['offset']]+=1
            for i,b in enumerate(s): bytes_by_col[i][b]+=1
            rr.append({'source_offset':r['source_offset'],'token':r['token'],'ascii_runs':rs,'slot_hex':s.hex()})
        stable=[]
        for i,c in enumerate(bytes_by_col):
            b,n=c.most_common(1)[0]
            if len(recs)>=2 and n/len(recs)>=0.8 and b!=0:
                stable.append({'offset':i,'byte':b,'ascii':chr(b) if 32<=b<127 else None,'count':n,'fraction':round(n/len(recs),4)})
        report['opcode_groups'].append({'opcode':op,'opcode_hex':f'0x{op:02X}','count':len(recs),
          'post_primary_ascii_run_start_histogram':{str(k):v for k,v in sorted(starts.items())},
          'stable_nonzero_columns_80pct':stable,'records':rr})
    # Explicit structural findings, computed from corpus.
    def g(op): return groups.get(op,[])
    findings=[]
    r28=g(0x28)
    if r28:
        second11=sum(any(x['offset']==11 for x in runs(s)[1:]) for _,s in r28)
        findings.append({'opcode_hex':'0x28','finding':'secondary printable field begins at serialized slot offset +11 in the dominant subset where that field is printable','count_at_offset_11':second11,'total':len(r28),'confidence':'HIGH_STRUCTURAL','semantic_status':'HOLD'})
    r19=g(0x19)
    if r19:
        col20=Counter(s[20] for _,s in r19); col18=Counter(s[18] for _,s in r19)
        findings.append({'opcode_hex':'0x19','finding':'fixed authored columns exist beyond the primary target string; column +20 is highly stable and +18 varies with small ASCII state-like values in many records','column_20':dict((str(k),v) for k,v in col20.items()),'column_18':dict((str(k),v) for k,v in col18.items()),'confidence':'HIGH_STRUCTURAL','semantic_status':'HOLD'})
    report['findings']=findings
    Path(a.out).write_text(json.dumps(report,indent=2,sort_keys=False)+'\n')
    print(f"records={report['record_count']} groups={len(report['opcode_groups'])}")
    for f in findings: print(f['opcode_hex'],f['finding'])
if __name__=='__main__': main()
