#!/usr/bin/env python3
"""Decode Azrael's Tear retail image .RES bundles."""
from __future__ import annotations
import argparse, hashlib, json, re, struct
from pathlib import Path
import numpy as np
from PIL import Image
from legacy_colorkey import render_indexed_colorkey

NODE_TABLE_BYTES=2048
HEADER_BYTES=0x40

def sha256_bytes(d:bytes)->str: return hashlib.sha256(d).hexdigest()

def xaf_unique_textures(path:Path)->list[str]:
    refs=re.findall(r'\btexture\s+"([^"]+)"',path.read_text("latin1"),re.I)
    out=[]; seen=set()
    for ref in refs:
        key=ref.casefold()
        if key not in seen: seen.add(key); out.append(ref)
    return out

def iter_records(data:bytes):
    off=0; index=0
    while off < len(data):
        if off+HEADER_BYTES+4 > len(data): raise ValueError(f"truncated record header at 0x{off:x}")
        declared=struct.unpack_from("<I",data,off)[0]
        physical=declared+4
        if declared<HEADER_BYTES or off+physical>len(data): raise ValueError(f"invalid record size {declared} at 0x{off:x}")
        block=data[off:off+physical]
        w,h=struct.unpack_from("<II",block,4)
        pc=struct.unpack_from("<I",block,0x38)[0]
        if not 1<=pc<=256: raise ValueError(f"invalid palette_count={pc} in record {index}")
        payload=HEADER_BYTES+pc*4
        if payload+8+NODE_TABLE_BYTES>len(block): raise ValueError(f"short Huffman payload in record {index}")
        raw_size,root=struct.unpack_from("<II",block,payload)
        if raw_size!=w*h: raise ValueError(f"record {index}: raw_size={raw_size} != {w}*{h}")
        yield index,off,declared,block,w,h,pc,payload,raw_size,root
        off+=physical; index+=1
    if off!=len(data): raise ValueError(f"record framing ended at {off}, file size {len(data)}")

def decode_record(block,w,h,pc,payload,raw_size,root):
    palette=np.frombuffer(block[HEADER_BYTES:HEADER_BYTES+pc*4],dtype=np.uint8).reshape(pc,4).copy()
    table=np.frombuffer(block[payload+8:payload+8+NODE_TABLE_BYTES],dtype="<u2")
    stream=block[payload+8+NODE_TABLE_BYTES:]
    out=np.empty(raw_size,dtype=np.uint8)
    word=bits_left=stream_pos=0
    for i in range(raw_size):
        node=root
        while node>=256:
            ti=node*2
            if ti+1>=len(table): raise ValueError(f"node out of table: {node}")
            if bits_left==0:
                if stream_pos+4>len(stream): raise EOFError(f"compressed stream ended at output byte {i}")
                word=struct.unpack_from("<I",stream,stream_pos)[0]; stream_pos+=4; bits_left=32
            bit=word&1; word>>=1; bits_left-=1; node=int(table[ti+bit])
        if node>=pc: raise ValueError(f"decoded palette index {node} >= {pc}")
        out[i]=node
    return palette,out.reshape(h,w),stream_pos,len(stream),bits_left

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input_res",type=Path); ap.add_argument("input_xaf",type=Path); ap.add_argument("output_dir",type=Path)
    ap.add_argument("--no-quantize",action="store_true")
    a=ap.parse_args(); data=a.input_res.read_bytes(); refs=xaf_unique_textures(a.input_xaf); records=list(iter_records(data))
    if len(refs)!=len(records): raise SystemExit(f"BLOCKED: XAF unique texture refs={len(refs)} != RES records={len(records)}")
    a.output_dir.mkdir(parents=True,exist_ok=True)
    manifest={"schema":"openazrael.retail_res_decode.v1","source_res":a.input_res.name,"source_res_sha256":sha256_bytes(data),
              "source_xaf":a.input_xaf.name,"mapping":"XAF_UNIQUE_FIRST_OCCURRENCE_TO_RES_RECORD_ORDER","record_count":len(records),"records":[]}
    for ref,rec in zip(refs,records):
        idx,off,declared,block,w,h,pc,payload,raw_size,root=rec
        palette,indices,consumed,stream_bytes,bits_left=decode_record(block,w,h,pc,payload,raw_size,root)
        rgb=palette[:,:3].copy()
        if not a.no_quantize: rgb=(rgb//4)*4
        rendered,ck=render_indexed_colorkey(indices,palette,rgb,ref)
        mode="RGBA" if rendered.shape[-1]==4 else "RGB"
        safe=re.sub(r'[^A-Za-z0-9_.#-]+','_',Path(ref).name)
        out=a.output_dir/f"{Path(safe).stem}.png"
        Image.fromarray(rendered,mode).save(out)
        manifest["records"].append({"record":idx,"offset":off,"declared_size":declared,"physical_size":declared+4,
          "texture_ref":ref,"width":w,"height":h,"palette_count":pc,"raw_size":raw_size,"root":root,
          "stream_bytes":stream_bytes,"consumed_stream_bytes":consumed,"bits_left":bits_left,
          "png":out.name,"png_sha256":sha256_bytes(out.read_bytes()),"legacy_colorkey":ck})
    mp=a.output_dir/"manifest.json"; mp.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"status":"PASS","records":len(records),"manifest":str(mp)},indent=2))

if __name__=="__main__": main()
