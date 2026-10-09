#!/usr/bin/env python3
"""Two fresh, isolated source->assets->Godot intro restores (not full KG-001)."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from build_intro_assets_v311 import build, ROOT
from decode_intro_mov_v311 import FILES, SOURCE_SHA, require, sha
from intro_source_contract_v312 import EXE_SHA, TITLE_SHA, RESOURCE_CFG_SHA
INPUTS = {**SOURCE_SHA, "R.EXE": EXE_SHA, "TITLE.PCX": TITLE_SHA, "RESOURCE.CFG": RESOURCE_CFG_SHA}

PROJECT = """config_version=5
[application]
config/name="OpenAzrael Intro Rehydration Test"
run/main_scene="res://scripts/validation/intro_runtime_test_v311.tscn"
[display]
window/size/viewport_width=640
window/size/viewport_height=480
[rendering]
renderer/rendering_method="gl_compatibility"
"""
SCRIPTS = ('scripts/intro_player_v311.gd', 'scripts/validation/intro_runtime_test_v311.gd',
           'scripts/validation/intro_runtime_test_v311.tscn')

def fingerprint(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): sha(p.read_bytes())
            for directory in (root/'assets/intro_v311', root/'data/runtime_generated')
            for p in sorted(directory.rglob('*')) if p.is_file() and p.suffix in ('.png','.wav','.json')}

def checked_run(command: list[str], log_path: Path, timeout: int) -> dict:
    with log_path.open('w', encoding='utf-8') as log:
        proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
    text = log_path.read_text(encoding='utf-8')
    require(proc.returncode == 0 and 'SCRIPT ERROR' not in text and 'Parse Error' not in text and 'ERROR:' not in text and 'were leaked at exit' not in text,
            'Godot failed: ' + str(log_path))
    return {'exit': proc.returncode, 'log': log_path.name, 'log_sha256': sha(log_path.read_bytes())}

def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('corpus', type=Path); ap.add_argument('--godot', type=Path, required=True)
    ap.add_argument('--work-root', type=Path, required=True)
    args=ap.parse_args()
    require(not args.work_root.exists(), 'refusing to overwrite a previous restore')
    require(args.godot.is_file(), 'missing pinned Godot')
    args.work_root.mkdir(parents=True)
    sources = {name: sha((args.corpus/name).read_bytes()) for name in INPUTS}
    require(sources == INPUTS, 'wrong source corpus')
    fingerprints, runs = [], []
    for name in ('restore_a','restore_b'):
        work=args.work_root/name;work.mkdir()
        (work/'project.godot').write_text(PROJECT,encoding='utf-8')
        for script in SCRIPTS:
            dest=work/script;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/script,dest)
        report_dir=work/'.tmp/intro_decode_v311';report_dir.mkdir(parents=True)
        build(args.corpus,work)
        fingerprints.append(fingerprint(work))
        imported=checked_run([str(args.godot),'--headless','--path',str(work),'--editor','--import'],work/'import.log',120)
        played=checked_run([str(args.godot),'--headless','--path',str(work)],work/'runtime.log',90)
        report=json.loads((report_dir/'godot_intro_tests.json').read_text(encoding='utf8'))
        require(report['status']=='PASS' and report['frame_hashes_checked']==245, 'fresh runtime evidence failed')
        runs.append({'restore':name,'assets':len(fingerprints[-1]),'import':imported,'runtime':played,
                     'checks':report['check_count'],'frames':report['frame_hashes_checked']})
        print(json.dumps(runs[-1]),flush=True)
    require(fingerprints[0]==fingerprints[1], 'two restores produced different asset bytes')
    require(sources=={name:sha((args.corpus/name).read_bytes()) for name in INPUTS},'source files changed')
    canonical=json.dumps(fingerprints[0],sort_keys=True,separators=(',',':')).encode()
    result={'schema':'openazrael.intro_rehydration.v311','status':'PASS','runs':runs,
            'source_sha256':sources,'equivalent_assets':len(fingerprints[0]),'asset_set_sha256':sha(canonical),
            'godot_sha256':sha(args.godot.read_bytes()),'copied_code_sha256':{s:sha((ROOT/s).read_bytes()) for s in SCRIPTS},
            'scope':'isolated intro harness; NOT full Candidate 8 fresh-checkout or original-runtime fidelity'}
    (args.work_root/'fresh_restore_report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','restores':2,'equivalent_assets':len(fingerprints[0]),'asset_set_sha256':result['asset_set_sha256']}))
if __name__=='__main__':main()
