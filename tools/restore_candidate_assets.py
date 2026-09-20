"""Restore excluded KG-001 Candidate assets from a locally extracted ATDEMO directory.

Requires numpy, Pillow and trimesh (validated with trimesh 5.1.0).
Original files and generated room/texture/audio binaries remain outside Git.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/texture_pipeline'))
from azf_decode_v14 import save_png
from export_xaf_glb_v8 import parse
from prepare_candidate_audio import prepare

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('demo_dir', type=Path)
    a = ap.parse_args(); src = a.demo_dir.resolve()
    textures = ROOT / 'assets/textures/classic'; textures.mkdir(parents=True, exist_ok=True)
    rooms = ROOT / 'assets/rooms'; rooms.mkdir(parents=True, exist_ok=True)
    audio = ROOT / 'assets/audio'; audio.mkdir(parents=True, exist_ok=True)
    azfs = sorted((src/'TEXTURES').glob('*.AZF'))
    if len(azfs) != 86: raise ValueError('Expected canonical demo corpus: 86 AZF textures')
    colorkey_rows = []
    for p in azfs:
        decoded = save_png(p, textures/(p.stem+'.png'))
        if decoded.get('legacy_colorkey_candidate'):
            colorkey_rows.append({
                'texture': p.stem + '.png',
                'applied': bool(decoded.get('legacy_colorkey_applied')),
                'transparent_pixels': int(decoded.get('legacy_colorkey_pixels', 0)),
                'key_index': decoded.get('legacy_colorkey_key_index'),
                'key_candidates': decoded.get(
                    'legacy_colorkey_key_candidates',
                    [],
                ),
                'detection': decoded.get('legacy_colorkey_detection'),
            })
    expected = {'R1':(69,593,62), 'R7':(48,689,40), 'R8':(87,1050,74)}
    for room, counts in expected.items():
        scene, objs, prims, mats, resolved, missing = parse(src/'TEXTURES'/(room+'.XAF'), textures)
        actual = (len(prims), sum(x['triangles'] for x in prims), sum(x['resolved_png'] is not None for x in prims))
        if actual != counts or missing: raise ValueError((room, actual, missing))
        scene.export(rooms/(room+'.glb'))
        manifest = dict(source=room+'.XAF', exporter_version=8, objects=objs, primitives=prims,
                        missing_textures=missing, textured_primitives=actual[2], primitive_count=actual[0], triangles=actual[1],
                        legacy_colorkey_primitives=sum(bool(x.get('legacy_colorkey')) for x in prims))
        (ROOT/'data'/f'{room}.textured.v44.manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    fingerprints = json.loads((ROOT/'data/backup/source_fingerprints.json').read_text(encoding='utf-8'))
    for entry in fingerprints['entries']:
        if not entry['path'].startswith('assets/audio/'): continue
        p = src/Path(entry['path']).name
        if hashlib.sha256(p.read_bytes()).hexdigest() != entry['sha256']: raise ValueError('Audio fingerprint mismatch: '+p.name)
        shutil.copyfile(p, ROOT/entry['path'])
    prepare(src/'797TAP.WAV', audio/'797TAP.WAV')
    prepare(src/'S137.WAV', audio/'S137.WAV')
    subprocess.run([sys.executable, str(ROOT/'tools/legacy_export/export_legacy_world_v21.py'), str(src), str(ROOT/'data/audio')], check=True)
    (ROOT/'.tmp/kg001').mkdir(parents=True, exist_ok=True)
    (ROOT/'.tmp/kg001/legacy_colorkey_restore.json').write_text(
        json.dumps({
            'schema':'openazrael.kg001.legacy_colorkey_restore',
            'version':117,
            'policy':'EXACTLY_ONE_USED_INDEXED_MAGENTA_KEY_PER_HASH_TEXTURE',
            'textures':colorkey_rows
        }, indent=2) + '\n',
        encoding='utf-8'
    )
    subprocess.run([sys.executable, str(ROOT/'tools/validate_graphics_pipeline_v44.py')], check=True)
    subprocess.run([sys.executable, str(ROOT/'tools/validate_kg001_texture_colorkey_v116.py')], check=True)
    print('KG-001 Candidate assets restored; legacy # color-key masks rebuilt; all raw/commercial binaries remain Git-ignored.')

if __name__ == '__main__': main()
