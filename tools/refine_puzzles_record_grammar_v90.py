#!/usr/bin/env python3
from pathlib import Path
import argparse,json,hashlib,bisect,collections,re

def cstr(d,s,limit=96):
 e=d.find(b'\0',s,min(len(d),s+limit))
 if e<0 or e==s:return None
 b=d[s:e]
 if any(x<32 or x>=127 for x in b):return None
 return b.decode('ascii')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--puzzles',required=True);ap.add_argument('--v89',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
 d=Path(a.puzzles).read_bytes(); old=json.loads(Path(a.v89).read_text())
 fes=[i for i,b in enumerate(d) if b==0xfe]
 structural=[]; hold=[]
 for r in old['records']:
  o=r['source_offset']; k=bisect.bisect_right(fes,o)-1
  anchor=fes[k] if k>=0 else None; rel=o-anchor if anchor is not None else None
  rr=dict(r); rr['nearest_fe_anchor']=anchor; rr['nearest_fe_anchor_hex']=f'0x{anchor:x}' if anchor is not None else None; rr['offset_from_anchor']=rel
  if anchor is not None and rel==128 and d[anchor+128:anchor+130]==b'\x10\x00':
   nm=cstr(d,anchor+1)
   rr.update({'record_anchor_name':nm,'record_class':'STRUCTURALLY_ANCHORED_ACTION','record_confidence':'HIGH',
              'structural_evidence':'FE record anchor; action prefix 10 00 occurs exactly +128 bytes from anchor'})
   structural.append(rr)
  else:
   rr.update({'record_class':'UNANCHORED_PATTERN_HOLD','record_confidence':'HOLD',
              'structural_evidence':'does not satisfy the dominant FE + 128 action-field invariant'})
   hold.append(rr)
 gaps=collections.Counter(b-a for a,b in zip(fes,fes[1:]))
 names=sum(1 for r in structural if r.get('record_anchor_name'))
 obj={'version':90,'format':'OpenAzrael PUZZLES.DAT structural action-record refinement',
      'source':{'name':Path(a.puzzles).name,'size':len(d),'sha256':hashlib.sha256(d).hexdigest()},
      'supersedes':'v89 treated all surviving 10 00 <opcode> <token> patterns alike; v90 separates structurally anchored action fields from unanchored patterns.',
      'grammar_status':'ACTION_FIELD_OFFSET_HIGH_FULL_RECORD_GRAMMAR_PARTIAL',
      'execution_policy':'NOT_DIRECTLY_EXECUTABLE',
      'fe_anchor_count':len(fes),'dominant_fe_gap':gaps.most_common(1)[0][0],'dominant_fe_gap_count':gaps.most_common(1)[0][1],
      'structurally_anchored_count':len(structural),'anchored_with_name_count':names,'unanchored_hold_count':len(hold),
      'invariant':{'anchor_byte':'0xfe','action_field_offset':128,'action_prefix':'10 00','confidence':'HIGH'},
      'records':structural,'hold_records':hold,
      'boundaries':['FE is a strong recurring record anchor for this action-bearing structure, but v90 does not claim every FE byte starts the same semantic record type.','The +128 action-field invariant is HIGH for 230 v89 candidates; opcode meanings retain their individual confidence.','Record length is not globally fixed: 190-byte FE spacing dominates but larger composite/enclosing structures exist.','Four v89 patterns fail the +128 invariant and are quarantined as HOLD rather than discarded.']}
 Path(a.out).write_text(json.dumps(obj,indent=2)+'\n')
 print(json.dumps({'anchored':len(structural),'hold':len(hold),'fe':len(fes),'dominant_gap':gaps.most_common(1)},sort_keys=True))
if __name__=='__main__':main()
