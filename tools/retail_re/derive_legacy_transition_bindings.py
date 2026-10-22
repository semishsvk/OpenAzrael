#!/usr/bin/env python3
"""Derive legacy XAF transition helper bindings against ROOMS.DAT strings."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path

def derive(xaf:Path,rooms:Path):
 t=xaf.read_text("latin1")
 printable=''.join(chr(b) if 32<=b<127 else ' ' for b in rooms.read_bytes())
 objs=[m.group(1) for m in re.finditer(r'\bobject\s+"([^"]+)"\s*\{',t,re.I)]
 tos=[];namespaces=[]
 for o in objs:
  m=re.match(r'^zxr(\d+)2([A-Za-z]\d+[A-Za-z0-9]*)$',o,re.I)
  if not m: continue
  src=int(m.group(1));dest=m.group(2);token=f"R{src}To{dest}"
  tos.append({"object":o,"legacy_source":f"R{src}","dest":dest,"rooms_token":token,"present":bool(re.search(re.escape(token),printable,re.I))})
  namespaces.append(src)
 ns=namespaces[0] if namespaces and len(set(namespaces))==1 else None
 fr=[]
 if ns is not None:
  for o in objs:
   m=re.match(r'^zy([A-Za-z]\d+[A-Za-z0-9]*)$',o,re.I)
   if not m: continue
   src=m.group(1);token=f"R{ns}From{src}"
   fr.append({"object":o,"legacy_source":f"R{ns}","from":src,"rooms_token":token,"present":bool(re.search(re.escape(token),printable,re.I))})
 return {"schema":"openazrael.retail_legacy_transition_binding.v1","xaf":xaf.name,"legacy_namespace":f"R{ns}" if ns is not None else None,
         "to_bindings":tos,"from_bindings":fr,"all_present":bool(tos or fr) and all(x["present"] for x in tos+fr)}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("xaf",type=Path);ap.add_argument("rooms_dat",type=Path);ap.add_argument("--out",type=Path);a=ap.parse_args()
 r=derive(a.xaf,a.rooms_dat);s=json.dumps(r,indent=2)+"\n"
 if a.out:a.out.write_text(s,encoding="utf8")
 print(s,end="")
if __name__=="__main__":main()
