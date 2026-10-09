#!/usr/bin/env python3
from pathlib import Path
import json,argparse,hashlib
ap=argparse.ArgumentParser();ap.add_argument('--ir',required=True);ap.add_argument('--puzzles',required=True);a=ap.parse_args()
o=json.loads(Path(a.ir).read_text()); d=Path(a.puzzles).read_bytes(); checks=[]
def ck(n,v): checks.append((n,bool(v)))
ck('version',o.get('version')==88); ck('source_sha',o['source']['sha256']==hashlib.sha256(d).hexdigest())
ck('nonempty',o['record_count']>0); ck('count',o['record_count']==len(o['records']))
ck('offsets_in_range',all(0<=r['source_offset']<len(d) for r in o['records']))
ck('pattern_recheck',all(d[r['source_offset']:r['source_offset']+2]==b'\x10\x00' and d[r['source_offset']+2]==r['legacy_opcode'] for r in o['records']))
ck('unknown_safe',all(r['confidence']=='UNKNOWN' and r['ir_op']=='unknown_legacy_opcode' for r in o['records'] if r['legacy_opcode'] not in {0,1,4,7,8,9,0x17,0x18,0x19,0x22,0x28}))
ck('not_executable',o['execution_policy'].startswith('NOT_DIRECTLY_EXECUTABLE'))
ck('hold_boundary',len(o.get('hold',[]))>=4)
for n,v in checks: print(('PASS' if v else 'FAIL'),n)
print(f"{sum(v for _,v in checks)}/{len(checks)} PASS")
raise SystemExit(0 if all(v for _,v in checks) else 1)
