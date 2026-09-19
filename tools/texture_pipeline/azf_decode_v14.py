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
        shape=(raw_size,)
    else:
        shape=(h,w)
    return {
        'width':w,'height':h,'palette_count':palette_count,'palette':palette,
        'raw_size':raw_size,'root':root,'node_table':table,'indices':out.reshape(shape),
        'stream_bytes':len(stream),'consumed_stream_bytes':stream_pos,'bits_left':bits_left
    }


def quantized_rgb_palette(decoded, quantize_like_engine=True):
    rgb=decoded['palette'][:,:3].copy()
    if quantize_like_engine:
        rgb=(rgb//4)*4
    return rgb


def detect_colorkey_index(azf_path: Path, decoded, rgb):
    """Return the exact legacy palette index used as binary transparency.

    Demo evidence: every # suffixed texture has one used quantized-magenta
    palette index, while no non-# Classic texture uses that convention.
    Selection is made in indexed space before RGB expansion so only the actual
    palette index becomes transparent; nearby colours remain untouched.
    """
    if '#' not in Path(azf_path).stem:
        return None
    idx=decoded['indices']
    counts=np.bincount(idx.reshape(-1),minlength=len(rgb))
    candidates=[]
    for palette_index,colour in enumerate(rgb):
        r,g,b=(int(colour[0]),int(colour[1]),int(colour[2]))
        if counts[palette_index] and r>=240 and g<=16 and b>=240:
            candidates.append((int(counts[palette_index]),palette_index))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return int(candidates[0][1])


def save_png(azf_path: Path, png_path: Path, quantize_like_engine=True):
    a=decode_azf(azf_path)
    if a['raw_size'] != a['width']*a['height']:
        raise ValueError('not a w*h indexed texture')
    rgb=quantized_rgb_palette(a,quantize_like_engine)
    idx=a['indices']
    if idx.max() >= len(rgb):
        raise ValueError(f'pixel index {idx.max()} exceeds palette size {len(rgb)}')

    key_index=detect_colorkey_index(azf_path,a,rgb)
    if '#' in Path(azf_path).stem and key_index is None:
        raise ValueError(f'legacy # texture has no used magenta colour-key palette index: {Path(azf_path).name}')

    if key_index is None:
        Image.fromarray(rgb[idx],'RGB').save(png_path)
        a['colorkey_index']=None
        a['colorkey_rgb']=None
        a['colorkey_pixels']=0
        a['output_mode']='RGB'
    else:
        alpha=np.full(len(rgb),255,dtype=np.uint8)
        alpha[key_index]=0
        rgba=np.concatenate([rgb,alpha[:,None]],axis=1)
        Image.fromarray(rgba[idx],'RGBA').save(png_path)
        a['colorkey_index']=key_index
        a['colorkey_rgb']=[int(x) for x in rgb[key_index]]
        a['colorkey_pixels']=int(np.count_nonzero(idx==key_index))
        a['output_mode']='RGBA'
    return a


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('input',type=Path)
    ap.add_argument('output',type=Path)
    ns=ap.parse_args()
    a=save_png(ns.input,ns.output)
    key=f" key={a['colorkey_index']} rgb={a['colorkey_rgb']} pixels={a['colorkey_pixels']}" if a['colorkey_index'] is not None else ''
    print(f"{ns.input.name}: {a['width']}x{a['height']} palette={a['palette_count']} mode={a['output_mode']}{key} root={a['root']} stream={a['consumed_stream_bytes']}/{a['stream_bytes']} -> {ns.output}")
