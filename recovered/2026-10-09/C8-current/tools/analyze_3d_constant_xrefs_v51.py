#!/usr/bin/env python3
import argparse,json
from pathlib import Path

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('xrefs'); ap.add_argument('--out',required=True); a=ap.parse_args()
 d=json.loads(Path(a.xrefs).read_text()); xs=d['xrefs']
 def hits(lo,hi): return [r for r in xs if r['source_object']==1 and lo<=r['source_offset']<=hi]
 core=hits(0xce20,0xcf90)
 targets={}
 for r in core:
  k=f"obj{r['target_object']}:{r['target_offset']:#x}"; targets.setdefault(k,[]).append(r['source_offset'])
 checks={
  'k_distance_site_maps_obj2_6abe': any(r['source_offset']==0xcf4a and r['target_object']==2 and r['target_offset']==0x6abe for r in xs),
  'global_scale_site_maps_obj2_1724': any(r['source_offset']==0xcf7d and r['target_object']==2 and r['target_offset']==0x1724 for r in xs),
  'pan_math_reuses_obj2_6abc': sum(1 for r in core if r['target_object']==2 and r['target_offset']==0x6abc)>=4,
  'pan_math_reuses_obj2_6abe': sum(1 for r in core if r['target_object']==2 and r['target_offset']==0x6abe)>=3,
  'canonical_graph_v36': d.get('version')==36 and d.get('canonical_xref_count')==28527,
 }
 if not all(checks.values()): raise SystemExit(checks)
 out={'schema':'openazrael.audio_3d_constant_xrefs','version':51,'status':'PASS','invariants':checks,
 'findings':{
  'K_DISTANCE_reference_target':{'source':'object1:0xCF4A relocation operand in the distance-constant load','target':'object2:0x6ABE','confidence':'HIGH_REFERENCE_IDENTITY','numeric_value':'HOLD'},
  'GLOBAL_VOLUME_SCALE_reference_target':{'source':'object1:0xCF7D relocation operand in signed-word global-scale load','target':'object2:0x1724','confidence':'HIGH_REFERENCE_IDENTITY','numeric_value':'HOLD'},
  'pan_constant_cluster':{'targets':['object2:0x6ABC','object2:0x6ABE'],'confidence':'HIGH_REFERENCE_CLUSTER','numeric_values':'HOLD'}},
 'important_limit':'v34 established that canonical LE OFFSET32 xrefs are trustworthy as object-relative reference identities, but target_offset must not be blindly treated as the runtime patched linear address/value. The apparent 0x6ABC/0x6ABE overlap is therefore not decoded as floating constants here.',
 'core_target_histogram':{k:{'count':len(v),'source_offsets':[hex(x) for x in sorted(v)]} for k,v in sorted(targets.items())},
 'implementation_decision':'Classic numeric attenuation/pan remains HOLD. v51 replaces vague unrelocated-placeholder labels with stable canonical reference identities, enabling a future object-2 initializer/data recovery to bind values without guessing.',
 'next':['Recover object-2 bytes/initializers for canonical targets 0x6ABC/0x6ABE and 0x1724 using a trusted LE reconstruction.','Cross-check target semantics against writes/initializers, not just reads.','Then add golden-vector tests for exact volume/pan.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8')
 print(json.dumps({'status':'PASS','invariants':sum(checks.values()),'total':len(checks),'K_DISTANCE':'object2:0x6ABE','GLOBAL_VOLUME_SCALE':'object2:0x1724'},indent=2))
if __name__=='__main__': main()
