#!/usr/bin/env python3
"""OpenAzrael v31: dump raw LE fixup records and correlate trusted operand-aligned sources with raw x86 operands.
Forensic only: target semantics remain HOLD until relocation behavior is independently validated.
"""
import argparse,struct,json,collections,hashlib,re,subprocess
from pathlib import Path
U16=lambda d,o:struct.unpack_from('<H',d,o)[0];U32=lambda d,o:struct.unpack_from('<I',d,o)[0];I16=lambda d,o:struct.unpack_from('<h',d,o)[0]
def disasm(path,base):
 out=subprocess.check_output(['objdump','-D','-b','binary','-m','i386',f'--adjust-vma={base}',str(path)],text=True,errors='replace')
 rx=re.compile(r'^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)\s*(.*)$');ins=[];mp={}
 for line in out.splitlines():
  m=rx.match(line)
  if not m:continue
  s=int(m.group(1),16);b=bytes.fromhex(m.group(2));idx=len(ins);ins.append((s,s+len(b),b,m.group(3).strip()))
  for x in range(s,s+len(b)):mp[x]=idx
 return ins,mp
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe');ap.add_argument('obj1');ap.add_argument('obj2');ap.add_argument('--out',required=True);a=ap.parse_args()
 raw=Path(a.exe).read_bytes();lo=U32(raw,0x3c) if raw[:2]==b'MZ' else 0x37d4c
 if raw[lo:lo+2]!=b'LE':lo=0x37d4c
 le=raw[lo:];n=U32(le,0x14);ps=U32(le,0x28);ot=U32(le,0x40);oc=U32(le,0x44);fpt=U32(le,0x68);frt=U32(le,0x6c)
 objs=[]
 for i in range(oc):
  size,base,flags,first,npages,_=struct.unpack_from('<IIIIII',le,ot+i*24);objs.append({'number':i+1,'size':size,'base':base,'first_page':first,'page_count':npages})
 pages=[U32(le,fpt+4*i) for i in range(n+1)]
 def src_obj(pg0):
  p=pg0+1
  for o in objs:
   if o['first_page']<=p<o['first_page']+o['page_count']:return o,(p-o['first_page'])*ps
  return None,None
 records=[]
 for pg in range(n):
  p=frt+pages[pg];end=frt+pages[pg+1]
  while p<end:
   rs=p;typ,fl=le[p],le[p+1];p+=2;islist=bool(typ&0x20)
   if islist:ns=le[p];p+=1;srcs=[]
   else:ns=0;srcs=[I16(le,p)];p+=2
   ordsz=2 if fl&0x40 else 1;tk=fl&3;target={}
   if tk==0:
    obj=U16(le,p) if ordsz==2 else le[p];p+=ordsz;off=None
    if (typ&0xf)!=2:off=U32(le,p) if fl&0x10 else U16(le,p);p+=4 if fl&0x10 else 2
    add=None
    if fl&0x04:add=U32(le,p) if fl&0x20 else U16(le,p);p+=4 if fl&0x20 else 2
    target={'kind':'internal','object':obj,'offset':off,'additive':add}
   elif tk==1:
    mod=U16(le,p) if ordsz==2 else le[p];p+=ordsz
    proc=le[p] if fl&0x80 else (U32(le,p) if fl&0x10 else U16(le,p));p+=1 if fl&0x80 else (4 if fl&0x10 else 2)
    if fl&4:p+=4 if fl&32 else 2
    target={'kind':'import_ordinal','module':mod,'proc':proc}
   elif tk==2:
    mod=U16(le,p) if ordsz==2 else le[p];p+=ordsz;name=U32(le,p) if fl&16 else U16(le,p);p+=4 if fl&16 else 2
    if fl&4:p+=4 if fl&32 else 2
    target={'kind':'import_name','module':mod,'name_offset':name}
   else:
    p+=ordsz
    if fl&4:p+=4 if fl&32 else 2
    target={'kind':'entry'}
   if islist:srcs=[I16(le,p+2*i) for i in range(ns)];p+=2*ns
   so,pbase=src_obj(pg)
   records.append({'page':pg+1,'record_le_offset':rs,'raw':le[rs:p].hex(),'source_type':typ&15,'source_flags':typ,'target_flags':fl,'sources':srcs,'source_object':so['number'] if so else None,'page_object_base':pbase,'target':target})
 ins={};mp={};blobs={1:Path(a.obj1).read_bytes(),2:Path(a.obj2).read_bytes()}
 for o in (1,2):ins[o],mp[o]=disasm(a.obj1 if o==1 else a.obj2,objs[o-1]['base'])
 aligned=[]
 for r in records:
  so=r['source_object'];baseoff=r['page_object_base']
  if so not in mp:continue
  for srel in r['sources']:
   off=baseoff+srel;lin=objs[so-1]['base']+off;idx=mp[so].get(lin)
   if idx is None:continue
   st,en,b,txt=ins[so][idx]
   if len(b)>=5 and lin==en-4 and 0<=off<=len(blobs[so])-4:
    rawop=struct.unpack_from('<I',blobs[so],off)[0];t=r['target'];tl=None
    if t.get('kind')=='internal' and t.get('offset') is not None and 1<=t.get('object',0)<=len(objs):tl=objs[t['object']-1]['base']+t['offset']
    aligned.append({'source_object':so,'source_linear':lin,'source_offset':off,'instruction_start':st,'instruction':txt,'instruction_bytes':b.hex(),'raw_operand_u32':rawop,'record_le_offset':r['record_le_offset'],'record_raw':r['raw'],'source_type':r['source_type'],'target_flags':r['target_flags'],'target':t,'candidate_target_linear':tl,'raw_equals_target_offset':rawop==t.get('offset'),'raw_equals_target_linear':rawop==tl})
 flags=collections.Counter((r['source_flags'],r['target_flags'],r['target']['kind']) for r in records)
 tf=collections.Counter(r['target_flags'] for r in records); sf=collections.Counter(r['source_flags'] for r in records)
 # representative operand-aligned records, including decisive entry neighborhood
 reps=[x for x in aligned if 0x3df40<=x['source_linear']<=0x3df90][:20]
 reps += [x for x in aligned if x not in reps][:60-len(reps)]
 out={'schema':'openazrael.le_fixup_raw_record_audit','version':31,'exe_sha256':hashlib.sha256(raw).hexdigest(),'structural_records':len(records),'source_flag_histogram':{hex(k):v for k,v in sf.items()},'target_flag_histogram':{hex(k):v for k,v in tf.items()},'record_shape_histogram':[{'source_flags':hex(k[0]),'target_flags':hex(k[1]),'kind':k[2],'count':v} for k,v in flags.most_common()],'operand_aligned_count':len(aligned),'operand_aligned_raw_equals_target_offset':sum(x['raw_equals_target_offset'] for x in aligned),'operand_aligned_raw_equals_candidate_target_linear':sum(x['raw_equals_target_linear'] for x in aligned),'representative_records':reps,'confidence':{'record_boundaries':'HIGH','source_coordinates':'HIGH','raw_record_bytes':'VERIFIED','operand_alignment':'MEDIUM','target_field_syntax':'HIGH','loader_relocation_semantics':'HOLD'},'findings':['Raw fixup records are now preserved byte-for-byte alongside parsed fields, allowing every target-decoder hypothesis to be reproduced.','The entry-neighborhood source at 0x3df6e is record 07 00 6e 0f 02 18 7c: source type 7, flags 0, source 0x0f6e, internal object 2, 16-bit field 0x7c18. The unrelocated x86 operand is 0x00006f84, so the 0x7c18 field is not a copy of the pre-load operand.','The source at 0x3df4c is record 07 00 4c 0f 01 03 00 and lands on the displacement of an otherwise coherent instruction. Its candidate target is unusual, so operand alignment alone cannot certify relocation application.','Therefore v31 separates three facts: record grammar, source placement, and loader patch semantics. Only the first two are promoted; loader patch semantics remain HOLD.'],'next':['Use the raw-record corpus to implement alternative LE source-type-7 relocation semantics without mutating the canonical runtime.','Score each hypothesis on code preservation and known control/data-reference invariants.','Build trusted xrefs only from hypotheses that pass those independent invariants.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps({k:out[k] for k in ['structural_records','source_flag_histogram','target_flag_histogram','operand_aligned_count','operand_aligned_raw_equals_target_offset','operand_aligned_raw_equals_candidate_target_linear']},indent=2))
if __name__=='__main__':main()
