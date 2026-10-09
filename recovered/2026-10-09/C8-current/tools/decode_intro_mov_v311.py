#!/usr/bin/env python3
"""Bounded decoder for the four ATDEMO Azrael MOV files.

Container/Huffman mapping was reconstructed from the read-only corpus and
cross-checked with the existing RES decoder and NihAV Game Tool 0.6.0 azmov.
The external GPL tool is a validation reference, not a runtime dependency.
Format algorithms are reimplemented here; no third-party source is bundled.
The 16-bit value at header offset 6 is opaque, NOT a verified depth or FPS.
Playback policy (10 fps, 22050 Hz U8) is kept separate from decoding evidence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import wave
from collections import Counter
from pathlib import Path

MAX_OUTPUT = 64 * 1024 * 1024
FILES = ('MINDLOGO.MOV', 'INTRO.MOV', 'MOV/INTRO.MOV', 'MOV/DEMO.MOV')
SOURCE_SHA = {
    'MINDLOGO.MOV': '14092da909352b9fa54fce96404f311d33ae15ca637b50cd990281759c4a973d',
    'INTRO.MOV': '67f774407584617ffa25e35ec6285e7b9b8db7b2d6afe4d8e4c5cc45304ae403',
    'MOV/INTRO.MOV': '5e3649ed33260df65f2b8258d04914d2352d2466d0085f21d83f63e2a4a5cdd6',
    'MOV/DEMO.MOV': 'a00fbd4f2560a43b4cd24b0abb51a22051a5d7aab067aff751d1dcf1366bc8c4',
}

class DecodeError(ValueError):
    pass

def require(ok: bool, message: str) -> None:
    if not ok:
        raise DecodeError(message)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def unpack_huffman(src: bytes, expected: int) -> tuple[bytes, dict]:
    require(len(src) >= 2056, 'truncated Huffman header/table')
    size, root = struct.unpack_from('<II', src)
    require(0 < expected <= MAX_OUTPUT and size == expected, 'invalid Huffman output size')
    require(256 <= root < 512, 'unsupported/invalid Huffman root')
    tree = struct.unpack_from('<1024H', src, 8)
    visiting, seen = set(), set()
    def check(node: int) -> None:
        require(0 <= node < 512, 'Huffman child outside table')
        if node < 256 or node in seen:
            return
        require(node not in visiting, 'cyclic Huffman tree')
        visiting.add(node)
        check(tree[2 * node]); check(tree[2 * node + 1])
        visiting.remove(node); seen.add(node)
    check(root)
    result = bytearray()
    node, bits = root, 0
    for byte in src[2056:]:
        for bit in range(8):
            node = tree[node * 2 + ((byte >> bit) & 1)]
            bits += 1
            if node < 256:
                result.append(node)
                node = root
                if len(result) == expected:
                    word_bytes = ((bits + 31) // 32) * 4
                    require(2056 + word_bytes == len(src), 'unconsumed/truncated Huffman word data')
                    return bytes(result), {'root': root, 'nodes': len(seen), 'bits_used': bits,
                                           'word_bytes': word_bytes, 'output_sha256': sha(result)}
    raise DecodeError('Huffman bitstream exhausted')

def read_container(data: bytes) -> tuple[dict, list[dict]]:
    require(len(data) >= 30, 'truncated MOV header')
    magic, count, opaque, width, height = struct.unpack_from('<I4H', data)
    require(magic == 0xAB12EF90, 'bad MOV magic')
    require(0 < count <= 10000, 'invalid frame count')
    require(4 <= width <= 4096 and 4 <= height <= 4096 and width % 4 == height % 4 == 0,
            'invalid four-pixel geometry')
    groups, pos = [], 30
    for index in range(count):
        require(pos + 16 <= len(data), 'truncated group header')
        magic, subcount, raw_size, packed_size, opaque2 = struct.unpack_from('<IHIIH', data, pos)
        require(magic == 0xEE9901CF, 'bad group magic')
        require(0 < raw_size <= MAX_OUTPUT and 0 < subcount <= 256, 'invalid group size/count')
        start, end = pos + 16, pos + 16 + (packed_size or raw_size)
        require(end <= len(data), 'truncated group payload')
        if packed_size:
            decoded, huff = unpack_huffman(data[start:end], raw_size)
        else:
            decoded, huff = data[start:end], None
        packets, cursor = [], 0
        for _ in range(subcount):
            require(cursor + 16 <= len(decoded), 'truncated packet header')
            tag, kind, size = struct.unpack_from('<IHI', decoded, cursor)
            require(tag == 0x0123FEDC, 'bad inner packet magic')
            pstart, pend = cursor + 16, cursor + 16 + size
            require(pend <= len(decoded), 'truncated inner packet')
            packets.append({'type': kind, 'data': decoded[pstart:pend], 'offset': cursor})
            cursor = pend
        require(cursor == raw_size, 'unconsumed group bytes / wrong subpacket count')
        groups.append({'index': index, 'offset': pos, 'end': end, 'raw_size': raw_size,
                       'packed_size': packed_size, 'opaque': opaque2, 'huffman': huff,
                       'decoded_sha256': sha(decoded), 'packets': packets})
        pos = end
    require(pos == len(data), 'unconsumed file bytes / wrong declared frame count')
    return {'frames': count, 'opaque_u16_at_6': opaque, 'width': width, 'height': height}, groups

def decode_delta(data: bytes, previous: bytes, older: bytes,
                 width: int, height: int) -> tuple[bytes, dict]:
    require(width % 4 == height % 4 == 0, 'delta requires four-pixel geometry')
    require(len(previous) == len(older) == width * height, 'wrong delta reference size')
    dest = bytearray(older)  # Preserve original two-buffer semantics for current-frame motion.
    position, mode, available, skip = 0, 0, 0, 0
    stats = Counter()
    def take(n: int) -> bytes:
        nonlocal position
        require(position + n <= len(data), 'truncated delta instruction')
        value = data[position:position + n]; position += n
        return value
    def copy(target: int, origin: int, src: bytes | bytearray) -> None:
        require(0 <= origin <= len(dest) - 3 * width - 4, 'motion outside image buffer')
        # Byte-order copying intentionally supports overlapping current-frame motion.
        for row in range(4):
            for col in range(4):
                dest[target + row * width + col] = src[origin + row * width + col]
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            target = y * width + x
            if skip:
                copy(target, target, previous); skip -= 1
                continue
            if not available:
                mode = take(1)[0]; available = 4
            opcode = mode & 3; mode >>= 2; available -= 1
            stats[str(opcode)] += 1
            if opcode == 1:
                length = take(1)[0] or 256
                skip = length - 1
                copy(target, target, previous)
            elif opcode == 3:
                tile = take(16)
                for row in range(4):
                    dest[target + row * width:target + row * width + 4] = tile[row * 4:row * 4 + 4]
            elif opcode == 2:
                packed = take(1)[0]
                origin = target + (packed >> 4) - 7 + ((packed & 15) - 7) * width
                copy(target, origin, previous)
            else:
                mx, my = take(2)
                current = bool(my & 128)
                origin = target + mx - 127 + (my - (191 if current else 63)) * width
                copy(target, origin, dest if current else previous)
                stats['current_motion' if current else 'previous_motion'] += 1
    require(skip == 0, 'skip run extends beyond image')
    require(position == len(data), 'unconsumed delta bytes')
    return bytes(dest), {'bytes_consumed': position, 'opcodes': dict(stats)}

def decode_movie(data: bytes) -> dict:
    header, groups = read_container(data)
    w, h = header['width'], header['height']
    current = older = bytes(w * h)
    palette = bytes(768)
    frames, audio, audio_kinds, packet_types = [], bytearray(), set(), Counter()
    keyframe_seen = palette_seen = False
    for group in groups:
        changes, delta_stats = 0, None
        for packet in group['packets']:
            kind, payload = packet['type'], packet['data']
            packet_types[str(kind)] += 1
            if kind == 5:
                require(0 < len(payload) <= 768 and len(payload) % 3 == 0, 'bad VGA palette size')
                require(max(payload) <= 63, 'palette component is not VGA 6-bit')
                palette = payload + palette[len(payload):]; palette_seen = True
            elif kind == 1:
                require(len(payload) == w * h, 'wrong keyframe size')
                current = payload; keyframe_seen = True; changes += 1
            elif kind == 4:
                require(keyframe_seen, 'delta without a keyframe')
                reconstructed, delta_stats = decode_delta(payload, current, older, w, h)
                older, current = current, reconstructed; changes += 1
            elif kind in (6, 7):
                audio.extend(payload); audio_kinds.add(kind)
            else:
                raise DecodeError('unsupported inner packet type: ' + str(kind))
        require(palette_seen and keyframe_seen and changes == 1, 'missing/ambiguous frame state')
        frames.append({'indices': current, 'palette': palette, 'delta': delta_stats,
                       'index_sha256': sha(current), 'palette_sha256': sha(palette),
                       'audio_end_sample_byte': len(audio)})
    require(len(audio_kinds) <= 1, 'mixed audio channel modes')
    return {'header': header, 'groups': groups, 'frames': frames, 'audio_u8': bytes(audio),
            'channels': 2 if 7 in audio_kinds else 1, 'packet_types': dict(packet_types)}

def export_movie(source: Path, output: Path, relative_name: str, verify_source: bool = True) -> dict:
    from PIL import Image
    raw = source.read_bytes()
    if verify_source:
        require(relative_name in SOURCE_SHA and sha(raw) == SOURCE_SHA[relative_name], 'source hash mismatch')
    movie = decode_movie(raw)
    output.mkdir(parents=True, exist_ok=True)
    unique, sequence = {}, []
    w, h = movie['header']['width'], movie['header']['height']
    for i, frame in enumerate(movie['frames']):
        rgb_palette = bytes((v << 2) | (v >> 4) for v in frame['palette'])
        key = sha(frame['indices'] + rgb_palette)
        if key not in unique:
            image = Image.frombytes('P', (w, h), frame['indices']); image.putpalette(rgb_palette)
            rgb = image.convert('RGB')
            name = 'frame_' + str(i).zfill(4) + '.png'; rgb.save(output / name)
            unique[key] = {'file': name, 'file_sha256': sha((output / name).read_bytes()),
                           'rgb_sha256': sha(rgb.tobytes())}
        sequence.append({'frame': i, **unique[key], 'index_sha256': frame['index_sha256'],
                         'palette_sha256': frame['palette_sha256'], 'delta': frame['delta'],
                         'audio_end_sample_byte': frame['audio_end_sample_byte']})
    audio_meta = None
    if movie['audio_u8']:
        with wave.open(str(output / 'audio.wav'), 'wb') as wav:
            wav.setnchannels(movie['channels']); wav.setsampwidth(1); wav.setframerate(22050)
            wav.writeframes(movie['audio_u8'])
        audio_meta = {'file': 'audio.wav', 'pcm_u8_sha256': sha(movie['audio_u8']),
                      'pcm_bytes': len(movie['audio_u8']), 'channels': movie['channels'],
                      'sample_rate': 22050, 'file_sha256': sha((output / 'audio.wav').read_bytes()),
                      'sample_rate_authority': 'prior-art azmov + 2205-sample frame cadence; runtime HOLD'}
    result = {'schema': 'openazrael.intro_movie.v311', 'source': relative_name, 'source_sha256': sha(raw),
              **movie['header'], 'unique_images': len(unique), 'sequence': sequence, 'audio': audio_meta,
              'packet_types': movie['packet_types'], 'nominal_fps': 10,
              'timing_authority': 'NihAV azmov reference; not derived from opaque_u16_at_6',
              'palette_policy': 'VGA6 to RGB8 by bit replication',
              'decode_status': 'DECODED', 'original_runtime_fidelity': 'HOLD',
              'groups': [{k: v for k, v in g.items() if k != 'packets'} for g in movie['groups']]}
    (output / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus', type=Path); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    for name in FILES:
        result = export_movie(args.corpus / name, args.out / name.replace('/', '_').replace('.MOV', ''), name)
        print(json.dumps({'file': name, 'frames': result['frames'], 'unique_images': result['unique_images'],
                          'audio': result['audio'], 'decode_status': result['decode_status']}))
if __name__ == '__main__':
    main()
