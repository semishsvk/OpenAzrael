#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]

def read(path):
    p=ROOT/path
    if not p.is_file():
        errors.append("missing: "+path)
        return ""
    return p.read_text(encoding="utf-8")

ambient=read("scripts/legacy_ambient_audio.gd")
events=read("scripts/legacy_event_runner_v87.gd")
diag=read("scripts/candidate_diagnostics_v116.gd")
runner=read("scripts/kg001_audio_runtime_runner_v116.gd")
restore=read("tools/restore_candidate_assets.py")
prepare=read("tools/prepare_candidate_audio.py")
ir_text=read("data/audio/legacy_world_ir.json")

checks={
    "ambient_null_fallback": 'if position_value == null:' in ambient and 'legacy_position' in ambient,
    "ambient_snapshot_playing": '"playing": p.playing' in ambient and '"stream_valid": p.stream != null' in ambient,
    "event_physical_tracking": "physical_audio_snapshot" in events and "physical_audio_started" in events,
    "event_current_scene_guard": "cannot start event sound without current_scene" in events,
    "candidate_ambient_ir_preflight": "data/audio/legacy_world_ir.json" in diag,
    "candidate_all_audio_preflight": all(x in diag for x in [
        "S152V2.WAV","S137.WAV","S121.WAV","799SECDR.WAV",
        "S174ELP1.WAV","S174ELP2.WAV","S186.WAV"
    ]),
    "runtime_master_bus": "master_bus_not_muted" in runner and "master_bus_not_silent" in runner,
    "runtime_ambient_counts": all(x in runner for x in ['"R1": 2','"R7": 3','"R8": 2']),
    "runtime_event_player": "event_physical_player_created" in runner and "event_player_playing" in runner,
    "restore_audio_fingerprints": "Audio fingerprint mismatch" in restore,
    "restore_legacy_ir": "export_legacy_world_v21.py" in restore,
    "wav_pcm_preserved": "pcm_unchanged" in prepare,
}
for name,value in checks.items():
    if not value:
        errors.append("check failed: "+name)

try:
    ir=json.loads(ir_text)
    emitters=ir.get("audio",{}).get("ambient_emitters",[])
    counts={0:0,1:0,2:0}
    samples=set()
    for e in emitters:
        rid=int(e.get("room_id",-1))
        if rid in counts:
            counts[rid]+=1
        samples.add(str(e.get("sample","")))
    if counts != {0:2,1:3,2:2}:
        errors.append("ambient IR room counts drift: "+repr(counts))
    if not {"S174ELP1.WAV","S174ELP2.WAV","S186.WAV"}.issubset(samples):
        errors.append("ambient IR sample set drift")
except Exception as e:
    errors.append("ambient IR parse: "+str(e))

if errors:
    print("OpenAzrael KG-001 physical audio source contract: FAIL")
    for e in errors:
        print(" -",e)
    sys.exit(1)

print("OpenAzrael KG-001 physical audio source contract: PASS")
print(" ambient emitters: R1=2 R7=3 R8=2")
print(" event physical-player readiness: WIRED")
print(" human audibility: MANUAL_PENDING")
print(" original Miles parity: HOLD")
