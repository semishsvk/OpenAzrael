#!/usr/bin/env python3
from pathlib import Path
import struct
import numpy as np
from PIL import Image

HEADER_SIZE=60
NODE_TABLE_BYTES=2048


def decode_azf(path: Path):
    d=Path(path).read_bytes()
    if len(d)<HEADER_SIZE:
        raise ValueError('file too small')
    w,h=struct.unpack_from('<II',d,0)
    palette_count=struct.unpack_from('<I',d,0x34)[0]
    if not (1 <= palette_count <= 256):
        raise ValueError(f'invalid palette_count={palette_count}')
    palette=np.frombuffer(d[HEADER_SIZE:HEADER_SIZE+palette_count*4],dtype=np.uint8).reshape(palette_count,4).copy()
    src=HEADER_SIZE+palette_count*4
    raw_size,root=struct.unpack_from('<II',d,src)
    table=np.frombuffer(d[src+8:src+8+NODE_TABLE_BYTES],dtype='<u2')
    stream=d[src+8+NODE_TABLE_BYTES:]
    if len(table)!=1024:
        raise ValueError('short node table')

    out=np.empty(raw_size,dtype=np.uint8)
    word=0; bits_left=0; stream_pos=0
    for i in range(raw_size):
        node=root
        while node >= 256:
            ti=node*2
            if ti+1 >= len(table):
                raise ValueError(f'node out of table: {node}')
            if bits_left==0:
                if stream_pos+4 > len(stream):
                    raise EOFError(f'compressed stream ended at output byte {i}')
                word=struct.unpack_from('<I',stream,stream_pos)[0]
                stream_pos += 4
                bits_left=32
            bit=word & 1
            word >>= 1
            bits_left -= 1
            node=int(table[ti+bit])
        out[i]=node

    if raw_size != w*h:
        # Keep decoding generic, but current demo textures are 8-bit indexed w*h.
        shape=(raw_size,)
    else:
        shape=(h,w)
    return {
        'width':w,'height':h,'palette_count':palette_count,'palette':palette,
        'raw_size':raw_size,'root':root,'node_table':table,'indices':out.reshape(shape),
        'stream_bytes':len(stream),'consumed_stream_bytes':stream_pos,'bits_left':bits_left
    }


def save_png(azf_path: Path, png_path: Path, quantize_like_engine=True):
    a=decode_azf(azf_path)
    if a['raw_size'] != a['width']*a['height']:
        raise ValueError('not a w*h indexed texture')
    rgb=a['palette'][:,:3].copy()
    # R.EXE LoadAZF quantizes palette components to multiples of 4 before
    # nearest-colour mapping into the renderer palette. For preservation PNGs,
    # retaining that quantization best matches the original path while avoiding
    # the runtime global-palette remap.
    if quantize_like_engine:
        rgb=(rgb//4)*4
    idx=a['indices']
    if idx.max() >= len(rgb):
        raise ValueError(f'pixel index {idx.max()} exceeds palette size {len(rgb)}')
    Image.fromarray(rgb[idx],'RGB').save(png_path)
    return a

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('input',type=Path)
    ap.add_argument('output',type=Path)
    ns=ap.parse_args()
    a=save_png(ns.input,ns.output)
    print(f"{ns.input.name}: {a['width']}x{a['height']} palette={a['palette_count']} root={a['root']} stream={a['consumed_stream_bytes']}/{a['stream_bytes']} -> {ns.output}")
