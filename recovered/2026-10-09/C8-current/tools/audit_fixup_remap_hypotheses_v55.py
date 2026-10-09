#!/usr/bin/env python3
import argparse,json,hashlib
from pathlib import Path
ANCHORS=[0xcf4d,0xcf7e,0xd005,0xd00b,0xd01e,0xd05b,0xd061,0xd074]
WIN=(0xcf30,0xd090)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('fixups'); ap.add_argument('--out',required=True); a=ap.parse_args()
 d=json.loads(Path(a.fixups).read_text())
 recs=[r for r in d['records'] if r.get('source_object')==1 and r.get('source_offset') is not None]
 src=sorted(set(r['source_offset'] for r in recs if WIN[0]<=r['source_offset']<=WIN[1]))
 # Exhaustively test a constant correction. A real page-base off-by-N bug would produce one dominant shift.
 shifts={}
 for k in range(-32,33):
  hit=[x for x in ANCHORS if x-k in src]
  shifts[k]=hit
 best=max(shifts,key=lambda k:len(shifts[k])); bestn=len(shifts[best])
 nearest={hex(x):sorted((abs(x-s),x-s,s) for s in src)[:4] for x in ANCHORS}
 # Test page-sized / object-base style corrections modulo 4K too: exact residue agreement should be high if only page association is wrong.
 residue_hits=sum(1 for x in ANCHORS if any((x-s)%4096==0 for s in src))
 checks={
  'eight_independent_anchors':len(ANCHORS)==8,
  'legacy_window_dense':len(src)>=25,
  'no_constant_shift_explains_majority':bestn<5,
  'no_4k_page_shift_explains_anchors':residue_hits<5,
  'v54_zero_exact_matches_reproduced':all(x not in src for x in ANCHORS),
 }
 if not all(checks.values()): raise SystemExit(checks)
 out={'schema':'openazrael.fixup_remap_hypothesis_audit','version':55,'status':'PASS','input_sha256':hashlib.sha256(Path(a.fixups).read_bytes()).hexdigest(),
 'invariants':checks,'anchors':[hex(x) for x in ANCHORS],'legacy_window_sources':[hex(x) for x in src],
 'constant_shift_search':{'range':'-32..+32','best_shift':best,'best_match_count':bestn,'best_matches':[hex(x) for x in shifts[best]],'all_match_counts':{str(k):len(v) for k,v in shifts.items()}},
 'page_shift_test':{'page_size':4096,'residue_match_count':residue_hits},
 'nearest_legacy_sources':{k:[{'legacy_source':hex(s),'anchor_minus_source':delta,'distance':dist} for dist,delta,s in v] for k,v in nearest.items()},
 'finding':'The v27 source-coordinate failure is not repairable by a single object-base, instruction-prefix, or 4 KiB page shift. The mismatch pattern changes across adjacent instructions. Therefore v55 rejects offset patching and requires a clean raw-record/page-association reparse.',
 'correction':{'decision':'REJECT_SIMPLE_SOURCE_OFFSET_REMAP','supersedes':['Any proposed global +1/+3/-1 style correction to v27 source offsets'],'retains':'v54 quarantine'},
 'confidence':{'simple_shift_rejected':'HIGH','correct_raw_record_parser':'HOLD','exact_attenuation_constants':'HOLD','exact_pan_constants':'HOLD'},
 'next':['Reparse raw fixup records from R.EXE bytes with record-boundary tracing and independent page ownership.','Validate record boundaries before interpreting source coordinates.','Accept a corrected mapper only after all eight 0xCDE1 operand anchors match exactly.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8')
 print(json.dumps({'status':'PASS','checks':len(checks),'best_shift':best,'best_matches':bestn,'page_residue_matches':residue_hits},indent=2))
if __name__=='__main__': main()
