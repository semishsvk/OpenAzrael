#!/usr/bin/env python3
import json, hashlib, argparse, collections, re
from pathlib import Path

def zero_tail_start(b):
    # earliest position after which all bytes are zero
    for i in range(len(b)+1):
        if not any(b[i:]): return i
    return len(b)

def ascii_runs(b):
    out=[]
    for m in re.finditer(rb'[ -~]{2,}', b):
        out.append({'offset':m.start(),'text':m.group().decode('ascii')})
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True); ap.add_argument('--output',required=True)
    a=ap.parse_args(); src=json.load(open(a.input)); recs=src['dominant_records']
    groups=collections.defaultdict(list)
    for r in recs:
        b=bytes.fromhex(r['opaque_residue_hex']); z=zero_tail_start(b); prefix=b[:z]
        rr={'source_offset':r['source_offset'],'opcode':r['legacy_opcode'],'opcode_hex':r['legacy_opcode_hex'],'token':r['token'],
            'residue_len':len(b),'meaningful_prefix_len_upper_bound':z,'meaningful_prefix_hex':prefix.hex(),
            'ascii_runs':ascii_runs(prefix),'nonzero_bytes':sum(x!=0 for x in b),
            'confidence':'STRUCTURAL_ONLY','semantic_status':'HOLD'}
        groups[r['legacy_opcode_hex']].append(rr)
    og=[]
    for op, xs in sorted(groups.items(), key=lambda kv:int(kv[0],16)):
        pref=collections.Counter(x['meaningful_prefix_hex'] for x in xs)
        plen=collections.Counter(x['meaningful_prefix_len_upper_bound'] for x in xs)
        og.append({'opcode_hex':op,'count':len(xs),'distinct_tokens':sorted(set(x['token'] for x in xs)),
                   'prefix_length_histogram':dict(sorted(plen.items())), 'distinct_prefixes':len(pref),
                   'most_common_prefixes':[{'hex':h,'count':n} for h,n in pref.most_common(8)],
                   'records':xs,'semantics':'UNKNOWN/HOLD'})
    out={'version':92,'source':'puzzles_action_slot_v91.json','scope':'198 dominant 190-byte records only',
         'method':'Bound opaque residue without assigning semantics. meaningful_prefix_len_upper_bound is the earliest byte after which the rest of the 62-byte action slot is all zero.',
         'important_boundary':'Printable fragments and numeric-looking bytes are observations only; they are not decoded operands.',
         'record_count':len(recs),'opcode_group_count':len(og),'opcode_groups':og}
    Path(a.output).write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
if __name__=='__main__': main()
