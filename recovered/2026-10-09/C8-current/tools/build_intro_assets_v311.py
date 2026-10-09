#!/usr/bin/env python3
"""Rebuild source-pinned lossless intro assets and the Godot runtime manifest.
No commercial artwork/audio is committed. A fresh checkout must run this tool.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from intro_source_contract_v312 import extract, TITLE_SHA
from decode_intro_mov_v311 import FILES, SOURCE_SHA, export_movie, require, sha

ROOT = Path(__file__).resolve().parents[1]

def configure_wav_import(file: Path, root: Path) -> None:
    """Pin raw PCM; Godot's default QOA import would otherwise be lossy."""
    import hashlib
    resource = 'res://' + file.relative_to(root).as_posix()
    sample = 'res://.godot/imported/' + file.name + '-' + hashlib.md5(resource.encode()).hexdigest() + '.sample'
    sidecar = file.with_suffix(file.suffix + '.import')
    if sidecar.exists():
        text = sidecar.read_text(encoding='utf-8')
        prefix = text.split('[params]', 1)[0]
    else:
        prefix = ('[remap]\n\nimporter="wav"\ntype="AudioStreamWAV"\npath=' + json.dumps(sample) +
                  '\n\n[deps]\n\nsource_file=' + json.dumps(resource) + '\ndest_files=[' + json.dumps(sample) + ']\n\n')
    settings = ('[params]\n\nforce/8_bit=false\nforce/mono=false\nforce/max_rate=false\n'
                'force/max_rate_hz=44100\nedit/trim=false\nedit/normalize=false\n'
                'edit/loop_mode=1\nedit/loop_begin=0\nedit/loop_end=-1\ncompress/mode=0\n')
    sidecar.write_text(prefix + settings, encoding='utf-8')

def build(corpus: Path, output_root: Path = ROOT, reuse: bool = False) -> dict:
    contract = extract(corpus)
    assets = output_root / 'assets/intro_v311'
    clips = {}
    for name in FILES:
        clip_id = name.replace('/', '_').replace('.MOV', '')
        directory = assets / clip_id
        require(sha((corpus / name).read_bytes()) == SOURCE_SHA[name], 'source hash changed: ' + name)
        if reuse:
            decoded = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
            require(decoded['source_sha256'] == SOURCE_SHA[name], 'cached manifest source mismatch')
        else:
            decoded = export_movie(corpus / name, directory, name)
        sequence = []
        for frame in decoded['sequence']:
            file = directory / frame['file']
            require(file.parent == directory and sha(file.read_bytes()) == frame['file_sha256'],
                    'decoded image hash/path mismatch: ' + str(file))
            sequence.append({'path': 'res://' + file.relative_to(output_root).as_posix(),
                             'rgb_sha256': frame['rgb_sha256'], 'index_sha256': frame['index_sha256']})
        audio = decoded['audio']
        if audio:
            file = directory / audio['file']
            require(file.parent == directory and sha(file.read_bytes()) == audio['file_sha256'],
                    'decoded audio hash/path mismatch')
            configure_wav_import(file, output_root)
            audio = {**audio, 'path': 'res://' + file.relative_to(output_root).as_posix(),
                     'duration': audio['pcm_bytes'] / (audio['channels'] * audio['sample_rate'])}
        clock = contract['clips'][clip_id]
        position = [(640 - decoded['width']) // 2, (480 - decoded['height']) // 2]
        clips[clip_id] = {
            'source': name, 'source_sha256': SOURCE_SHA[name],
            'width': decoded['width'], 'height': decoded['height'], 'frame_count': decoded['frames'],
            'fps': clock['fps'], 'nominal_fps': clock['nominal_fps'],
            'frame_period_us': clock['frame_period_us'], 'source_position': position,
            'kind': 'movie', 'sequence': sequence, 'audio': audio,
            'duration': max(decoded['frames'] * clock['frame_period_us'] / 1_000_000, audio['duration'] if audio else 0),
            'decode_status': 'DECODED', 'original_runtime_fidelity': 'HOLD',
        }
    # Native PCX decoder places this 631x474 image at (0,0) in a 640x480 buffer.
    from PIL import Image
    title_dir = assets / 'TITLE'
    title_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(corpus / 'TITLE.PCX') as source:
        title = source.convert('RGB')
    require(title.size == (631, 474), 'source title geometry mismatch')
    # Preserve raw PCX RGB bytes for source-mechanism oracle. The original
    # R.EXE writes 6-bit VGA DAC channels, truncating each 8-bit PCX palette
    # entry to its upper six bits; DOSBox-X returns the effective displayed
    # eight-bit channel by replicating those bits. Confirmed pixel-exact
    # against native original R.EXE TITLE framebuffer in v377.
    title_file = title_dir / 'frame_0000.png'
    title.save(title_file)
    dac_lut = [((v >> 2) << 2) | ((v >> 2) >> 4) for v in range(256)]
    title_display = title.point(dac_lut * 3)
    title_display_file = title_dir / 'frame_0000_vga6.png'
    title_display.save(title_display_file)
    clips['TITLE'] = {
        'source': 'TITLE.PCX', 'source_sha256': TITLE_SHA, 'kind': 'still',
        'width': 631, 'height': 474, 'frame_count': 1, 'fps': 1.0, 'source_position': [0, 0],
        'sequence': [{'path': 'res://' + title_display_file.relative_to(output_root).as_posix(),
                      'rgb_sha256': sha(title_display.tobytes()),
                      'source_raw_path': 'res://' + title_file.relative_to(output_root).as_posix(),
                      'source_raw_rgb_sha256': sha(title.tobytes()),
                      'display_dac_policy': 'PCX_RGB8_TRUNCATE_TO_DAC6_THEN_BIT_REPLICATE'}], 'audio': None,
        'duration': contract['title']['nominal_hold_seconds'],
        'timing_authority': contract['title']['timing_scope'],
        'decode_status': 'DECODED', 'original_runtime_fidelity': 'SOURCE_TO_EMULATOR_STATIC_DAC_PIXEL_EXACT_FADE_AND_WALLCLOCK_HOLD',
    }
    result = {
        'schema': 'openazrael.intro_runtime.v311',
        'decoder_sha256': sha((ROOT / 'tools/decode_intro_mov_v311.py').read_bytes()),
        'startup_order': contract['startup_order'],
        'startup_includes_title': True, 'logical_canvas': [640, 480],
        'source_contract': contract,
        'startup_order_authority': 'Original R.EXE 0x10799 caller trace; mechanism oracle v312',
        'timing_authority': 'Original 1000000/fps timer call: 15 fps Mindscape, 10 fps other movies, 22050 Hz PCM; DOS wall-clock/fades HOLD',
        'palette_policy': '6-bit VGA RGB expanded by bit replication',
        'fidelity_status': 'ORIGINAL_MECHANISM_PASS_DISPLAY_TIMING_HOLD', 'clips': clips,
    }
    dest = output_root / 'data/runtime_generated/intro_movies_v311.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('corpus', type=Path)
    p.add_argument('--reuse-decoded', action='store_true', help='Validate all cached hashes instead of decoding again.')
    args = p.parse_args()
    result = build(args.corpus, reuse=args.reuse_decoded)
    print(json.dumps({'status': 'ASSETS_READY', 'clips': len(result['clips']),
                      'frames': sum(c['frame_count'] for c in result['clips'].values()),
                      'startup_order': result['startup_order'], 'fidelity': result['fidelity_status']}))
if __name__ == '__main__': main()
