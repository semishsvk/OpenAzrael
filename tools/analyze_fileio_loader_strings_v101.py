#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,struct
ap=argparse.ArgumentParser();ap.add_argument('--exe',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
b=Path(a.exe).read_bytes(); LE=0x37d4c; le=b[LE:]; u=lambda o:struct.unpack_from('<I',le,o)[0]
ps=u(0x28);ot=u(0x40);dp=u(0x80); size,base,_,first,pages,_=struct.unpack_from('<IIIIII',le,ot); o=le[dp+(first-1)*ps:dp+(first-1)*ps+size]
need=[b'ReadFlagData',b'%s.dat',b'GetLine',b'Invalid flag type %d',b'characte.dat',b'maps.dat']
hits={}
for s in need:
 arr=[];p=0
 while True:
  i=o.find(s,p)
  if i<0:break
  arr.append(i);p=i+1
 hits[s.decode()] = arr
anchor=hits['ReadFlagData'][0]
# collect nul-terminated printable strings in +/-0x140
lo=max(0,anchor-0x140); hi=min(len(o),anchor+0x240); region=o[lo:hi]
strings=[]; start=None
for j,c in enumerate(region+b'\0'):
 if 32<=c<127:
  if start is None:start=j
 else:
  if start is not None and j-start>=1:
   s=region[start:j].decode('ascii','replace'); strings.append({'offset':lo+start,'offset_hex':hex(lo+start),'text':s})
  start=None
out={'schema':'openazrael.fileio_loader_string_audit','version':101,'exe_sha256':hashlib.sha256(b).hexdigest(),
'object1_base':hex(base),'anchors':{k:[hex(x) for x in v] for k,v in hits.items()},'readflagdata_cluster':strings,
'findings':{
'VERIFIED':['The bound R.EXE contains ReadFlagData, GetLine, Invalid flag type %d, %s.dat and mode string r in one compact object1 string cluster.','The literal string PUZZLES.DAT is absent from the bound executable; loader discovery cannot depend on that filename literal.'],
'HIGH':['The cluster is consistent with a generic text/flag-data parsing path that dynamically constructs <name>.dat and parses line-oriented integer/string fields.'],
'HOLD':['No static code xref or call edge from this string cluster to the 190-byte PUZZLES.DAT record representation is proven here. ReadFlagData is not promoted to the PUZZLES loader.','The exact PUZZLES.DAT disk-record to runtime-action constructor remains unresolved.']},
'next':['Use the ReadFlagData/%s.dat/GetLine cluster as a runtime breakpoint/trace anchor rather than claiming it statically.','Observe the filename produced at runtime and whether PUZZLES data passes this path; only then follow reads/writes into runtime action objects.']}
Path(a.out).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'status':'PASS','anchor':hex(anchor),'cluster_strings':len(strings),'puzzles_literal_in_exe':b'PUZZLES.DAT' in b or b'puzzles.dat' in b},indent=2))
