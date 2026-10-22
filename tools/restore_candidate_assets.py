"""Restore excluded KG-001 Candidate assets from a locally extracted ATDEMO directory.

Requires numpy, Pillow and trimesh (validated with trimesh 5.1.0).
Original files and generated room/texture/audio binaries remain outside Git.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools/texture_pipeline'))
from tools.remaster_framework.source_registry import resolve_source
from azf_decode_v14 import save_png

RESTORE_RECEIPT = ROOT / '.tmp/kg001/candidate_asset_restore_v177.json'
RUNTIME_ASSET_ROOTS = (
    ROOT/'assets/rooms', ROOT/'assets/audio', ROOT/'assets/textures/classic',
    ROOT/'assets/ui/mice', ROOT/'assets/ui/legacy_menu', ROOT/'assets/characters',
)

def _runtime_files():
    files=[]
    for root in RUNTIME_ASSET_ROOTS:
        if root.is_dir(): files.extend(p for p in root.rglob('*') if p.is_file())
    return sorted(set(files), key=lambda p:str(p.relative_to(ROOT)).lower())

def _asset_identity():
    return {str(p.relative_to(ROOT)).replace('\\\\','/'):{
        'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()
    } for p in _runtime_files()}

def _identity_digest(identity):
    return hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()
from export_xaf_glb_v8 import parse
from prepare_candidate_audio import prepare

def main():
    RESTORE_RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RESTORE_RECEIPT.unlink(missing_ok=True)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        'demo_dir',
        type=Path,
        nargs='?',
        help=(
            'Extracted ATDEMO directory. If omitted, resolve the persistent '
            'registered demo corpus automatically.'
        ),
    )
    ap.add_argument(
        '--source-home',
        type=Path,
        help='Optional OPENAZRAEL_SOURCE_HOME override.',
    )
    a = ap.parse_args()
    src = (
        a.demo_dir.resolve()
        if a.demo_dir is not None
        else resolve_source('demo', home=a.source_home)
    )
    textures = ROOT / 'assets/textures/classic'; textures.mkdir(parents=True, exist_ok=True)
    rooms = ROOT / 'assets/rooms'; rooms.mkdir(parents=True, exist_ok=True)
    audio = ROOT / 'assets/audio'; audio.mkdir(parents=True, exist_ok=True)
    azfs = sorted((src/'TEXTURES').glob('*.AZF'))
    if len(azfs) != 86: raise ValueError('Expected canonical demo corpus: 86 AZF textures')
    colorkey_rows = []
    texture_restore_rows = []
    for p in azfs:
        png_path = textures/(p.stem+'.png')
        decoded = save_png(p, png_path)
        texture_restore_rows.append({
            'texture': p.stem + '.png',
            'source_azf': p.name,
            'source_azf_sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
            'runtime_png_sha256': hashlib.sha256(png_path.read_bytes()).hexdigest(),
            'width': int(decoded['width']),
            'height': int(decoded['height']),
            'palette_count': int(decoded['palette_count']),
            'output_mode': decoded.get('output_mode', 'RGB'),
            'legacy_colorkey_candidate': bool(decoded.get('legacy_colorkey_candidate')),
            'legacy_colorkey_applied': bool(decoded.get('legacy_colorkey_applied')),
        })
        if decoded.get('legacy_colorkey_candidate'):
            colorkey_rows.append({
                'texture': p.stem + '.png',
                'applied': bool(decoded.get('legacy_colorkey_applied')),
                'key_index': decoded.get('legacy_colorkey_index'),
                'key_source_rgba': decoded.get('legacy_colorkey_source_rgba'),
                'key_output_rgb': decoded.get('legacy_colorkey_output_rgb'),
                'transparent_pixels': int(decoded.get('legacy_colorkey_pixels', 0)),
                'used_sentinel_indices': decoded.get('legacy_colorkey_used_sentinel_indices', []),
                'used_broad_magenta_indices': decoded.get('legacy_colorkey_used_broad_magenta_indices', []),
                'rule': decoded.get('legacy_colorkey_rule'),
            })
    expected = {'R1':(69,593,62), 'R7':(48,689,40), 'R8':(87,1050,74)}
    room_restore_rows = []
    for room, counts in expected.items():
        xaf_path = src/'TEXTURES'/(room+'.XAF')
        scene, objs, prims, mats, resolved, missing = parse(xaf_path, textures)
        actual = (len(prims), sum(x['triangles'] for x in prims), sum(x['resolved_png'] is not None for x in prims))
        if actual != counts or missing: raise ValueError((room, actual, missing))
        glb_path = rooms/(room+'.glb')
        scene.export(glb_path)
        manifest = dict(source=room+'.XAF', exporter_version=8,
                        source_xaf_sha256=hashlib.sha256(xaf_path.read_bytes()).hexdigest(),
                        output_glb_sha256=hashlib.sha256(glb_path.read_bytes()).hexdigest(),
                        objects=objs, primitives=prims,
                        missing_textures=missing, textured_primitives=actual[2], primitive_count=actual[0], triangles=actual[1],
                        uv_export_policy='TRIMESH_PRE_FLIP_V_PRESERVE_XAF_GLTF',
                        legacy_colorkey_primitives=sum(bool(x.get('legacy_colorkey')) for x in prims))
        manifest_path = ROOT/'data'/f'{room}.textured.v44.manifest.json'
        manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        room_restore_rows.append({
            'room': room,
            'source_xaf': xaf_path.name,
            'source_xaf_sha256': manifest['source_xaf_sha256'],
            'runtime_glb_sha256': manifest['output_glb_sha256'],
            'primitive_count': actual[0],
            'triangle_count': actual[1],
            'textured_primitive_count': actual[2],
            'manifest': str(manifest_path.relative_to(ROOT)).replace('\\\\','/'),
        })

    (ROOT/'.tmp/kg001').mkdir(parents=True, exist_ok=True)
    (ROOT/'.tmp/kg001/candidate4_texture_restore_v133.json').write_text(
        json.dumps({
            'schema': 'openazrael.kg001.candidate4_texture_restore',
            'version': 133,
            'status': 'PASS',
            'source': 'original ATDEMO AZF/XAF corpus',
            'texture_count': len(texture_restore_rows),
            'room_count': len(room_restore_rows),
            'textures': texture_restore_rows,
            'rooms': room_restore_rows,
        }, indent=2) + '\n',
        encoding='utf-8'
    )

    canonical_audio_ir = json.loads((ROOT/'data/audio/legacy_world_ir.json').read_text(encoding='utf-8'))
    sound_rows = canonical_audio_ir.get('audio', {}).get('sounds', [])
    if len(sound_rows) != 30:
        raise ValueError(f'Expected canonical demo WAV corpus: 30 files, got {len(sound_rows)}')
    audio_restore_rows = []
    for row in sound_rows:
        name = row['filename']
        p = src / name
        if not p.is_file():
            raise FileNotFoundError('Missing canonical demo WAV: ' + name)
        source_sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if source_sha != row['sha256']:
            raise ValueError('Audio fingerprint mismatch: ' + name)
        destination = audio / name
        shutil.copyfile(p, destination)
        audio_restore_rows.append({
            'filename': name,
            'source_sha256': source_sha,
            'expected_source_sha256': row['sha256'],
        })
    prepare(src/'797TAP.WAV', audio/'797TAP.WAV')
    prepare(src/'S137.WAV', audio/'S137.WAV')
    prepare(src/'981PULL.WAV', audio/'981PULL.WAV')
    for row in audio_restore_rows:
        runtime_path = audio / row['filename']
        row['runtime_sha256'] = hashlib.sha256(runtime_path.read_bytes()).hexdigest()
        row['runtime_bytes'] = runtime_path.stat().st_size
    (ROOT/'.tmp/kg001').mkdir(parents=True, exist_ok=True)
    (ROOT/'.tmp/kg001/candidate4_audio_restore_v132.json').write_text(
        json.dumps({
            'schema': 'openazrael.kg001.candidate4_audio_restore',
            'version': 132,
            'status': 'PASS',
            'expected_wav_count': 30,
            'restored_wav_count': len(audio_restore_rows),
            'files': audio_restore_rows,
        }, indent=2) + '\n',
        encoding='utf-8'
    )
    subprocess.run([sys.executable, str(ROOT/'tools/legacy_export/export_legacy_world_v21.py'), str(src), str(ROOT/'data/audio')], check=True)
    (ROOT/'.tmp/kg001').mkdir(parents=True, exist_ok=True)
    (ROOT/'.tmp/kg001/legacy_colorkey_restore.json').write_text(
        json.dumps({'schema':'openazrael.kg001.legacy_colorkey_restore','version':116,'textures':colorkey_rows}, indent=2) + '\n',
        encoding='utf-8'
    )
    subprocess.run([sys.executable, str(ROOT/'tools/validate_graphics_pipeline_v44.py')], check=True)
    subprocess.run([sys.executable, str(ROOT/'tools/validate_kg001_texture_colorkey_v116.py')], check=True)
    subprocess.run([sys.executable, '-m', 'tools.audit_demo_texture_orientation_v133'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(ROOT/'tools/restore_legacy_cursors_v143.py'), str(src)], check=True)
    subprocess.run([sys.executable, str(ROOT/'tools/restore_legacy_menu_v144.py'), str(src)], check=True)
    subprocess.run([sys.executable, str(ROOT/'tools/restore_legacy_scanner_v164.py'), str(src)], check=True)
    subprocess.run([sys.executable, str(ROOT/'tools/restore_character_animation_v166.py'), str(src)], check=True)
    subprocess.run([sys.executable, str(ROOT/'tools/restore_eugene_animation_v179.py'), str(src)], check=True)
    identity=_asset_identity()
    RESTORE_RECEIPT.write_text(json.dumps({
        'schema':'openazrael.kg001.candidate_asset_restore',
        'version':177,
        'status':'PASS',
        'asset_file_count':len(identity),
        'asset_identity_sha256':_identity_digest(identity),
        'assets':identity,
    },indent=2)+'\\n',encoding='utf-8')
    print('KG-001 Candidate assets restored; complete restore receipt v177 written only after all source restorers and validators passed.')

if __name__ == '__main__': main()
