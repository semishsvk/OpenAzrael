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
    audio_restore_rows = []
    for entry in fingerprints['entries']:
        if not entry['path'].startswith('assets/audio/'): continue
        p = src/Path(entry['path']).name
        source_hash = hashlib.sha256(p.read_bytes()).hexdigest()
        if source_hash != entry['sha256']: raise ValueError('Audio fingerprint mismatch: '+p.name)
        destination = ROOT/entry['path']
        shutil.copyfile(p, destination)
        audio_restore_rows.append({
            'asset': Path(entry['path']).name,
            'source_sha256': source_hash,
            'canonical_source_sha256': entry['sha256'],
            'runtime_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
            'operation': 'verified byte-for-byte runtime copy'
        })
    prepared_797 = prepare(src/'797TAP.WAV', audio/'797TAP.WAV')
    prepared_137 = prepare(src/'S137.WAV', audio/'S137.WAV')
    for asset_name, prepared in (
        ('797TAP.WAV', prepared_797),
        ('S137.WAV', prepared_137),
    ):
        runtime_path = audio/asset_name
        row = next(row for row in audio_restore_rows if row['asset'] == asset_name)
        row.update({
            'source_sha256': prepared['source_sha256'],
            'runtime_sha256': prepared['prepared_sha256'],
            'pcm_sha256': prepared['pcm_sha256'],
            'pcm_bytes': prepared['pcm_bytes'],
            'pcm_unchanged': prepared['pcm_unchanged'],
            'operation': prepared['operation'],
        })
        if hashlib.sha256(runtime_path.read_bytes()).hexdigest() != row['runtime_sha256']:
            raise ValueError('Prepared audio runtime fingerprint mismatch: '+asset_name)
    subprocess.run([sys.executable, str(ROOT/'tools/legacy_export/export_legacy_world_v21.py'), str(src), str(ROOT/'data/audio')], check=True)
    (ROOT/'.tmp/kg001').mkdir(parents=True, exist_ok=True)
    (ROOT/'.tmp/kg001/audio_restore_v118.json').write_text(
        json.dumps({
            'schema':'openazrael.kg001.audio_restore',
            'version':118,
            'status':'PASS',
            'asset_count':len(audio_restore_rows),
            'assets':sorted(audio_restore_rows, key=lambda row: row['asset']),
            'source_safe_metadata_only':True
        }, indent=2) + '\n',
        encoding='utf-8'
    )
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
    print('KG-001 Candidate assets restored; audio/runtime fingerprints recorded; legacy # color-key masks rebuilt; all raw/commercial binaries remain Git-ignored.')

if __name__ == '__main__': main()
