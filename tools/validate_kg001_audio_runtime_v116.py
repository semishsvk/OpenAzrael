#!/usr/bin/env python3
from pathlib import Path
import json, struct, sys, wave

ROOT=Path(__file__).resolve().parents[1]
errors=[]

def read(path):
    p=ROOT/path
    if not p.is_file():
        errors.append("missing: "+path)
        return ""
    return p.read_text(encoding="utf-8")

REQUIRED_AUDIO = [
    "979TONGS.WAV",
    "S152V2.WAV",
    "S137.WAV",
    "S121.WAV",
    "799SECDR.WAV",
    "S174ELP1.WAV",
    "S174ELP2.WAV",
    "S186.WAV",
]

def wav_pcm_peak(path: Path):
    with wave.open(str(path), "rb") as wav:
        channels=wav.getnchannels()
        sample_width=wav.getsampwidth()
        frame_count=wav.getnframes()
        raw=wav.readframes(frame_count)
    if frame_count <= 0 or channels <= 0 or not raw:
        return {"frames":frame_count,"channels":channels,"peak":0}
    if sample_width == 1:
        peak=max(abs(int(value)-128) for value in raw)
    elif sample_width == 2:
        usable=len(raw)-(len(raw)%2)
        peak=max(
            (abs(value[0]) for value in struct.iter_unpack("<h",raw[:usable])),
            default=0,
        )
    elif sample_width == 3:
        peak=0
        for offset in range(0,len(raw)-2,3):
            value=int.from_bytes(raw[offset:offset+3],"little",signed=False)
            if value & 0x800000:
                value-=1<<24
            peak=max(peak,abs(value))
    elif sample_width == 4:
        usable=len(raw)-(len(raw)%4)
        peak=max(
            (abs(value[0]) for value in struct.iter_unpack("<i",raw[:usable])),
            default=0,
        )
    else:
        raise ValueError(f"unsupported PCM sample width: {sample_width}")
    return {
        "frames":frame_count,
        "channels":channels,
        "sample_width":sample_width,
        "peak":int(peak),
    }

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
        "979TONGS.WAV","S152V2.WAV","S137.WAV","S121.WAV","799SECDR.WAV",
        "S174ELP1.WAV","S174ELP2.WAV","S186.WAV"
    ]),
    "runtime_master_bus": "master_bus_not_muted" in runner and "master_bus_not_silent" in runner,
    "runtime_master_capture": all(x in runner for x in [
        "AudioEffectCapture",
        "master_capture_frames_nonzero",
        "master_capture_peak_nonzero",
        "get_frames_available",
        "get_buffer",
    ]),
    "runtime_ambient_counts": all(x in runner for x in ['"R1": 2','"R7": 3','"R8": 2']),
    "runtime_event_players": all(x in runner for x in [
        "R7_WELL_TONGS_USE",
        "979TONGS.WAV",
        "R7_WATER_SWITCHBOARD_SOLVED",
        "S152V2.WAV",
        "_physical_player_created",
        "_player_playing",
    ]),
    "restore_audio_fingerprints": "Audio fingerprint mismatch" in restore,
    "restore_legacy_ir": "export_legacy_world_v21.py" in restore,
    "wav_pcm_preserved": "pcm_unchanged" in prepare,
}
for name,value in checks.items():
    if not value:
        errors.append("check failed: "+name)

audio_dir=ROOT/"assets/audio"
asset_rows=[]
asset_backed=any((audio_dir/name).is_file() for name in REQUIRED_AUDIO)
if asset_backed:
    for name in REQUIRED_AUDIO:
        path=audio_dir/name
        if not path.is_file():
            errors.append("missing required audio asset: "+name)
            continue
        try:
            row=wav_pcm_peak(path)
            row["asset"]=name
            asset_rows.append(row)
            if row["frames"] <= 0:
                errors.append("empty PCM frames: "+name)
            if row["peak"] <= 0:
                errors.append("silent PCM payload: "+name)
        except Exception as exc:
            errors.append("PCM audit "+name+": "+str(exc))

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
print(" event physical-player readiness: 979TONGS + S152V2 WIRED")
print(" Master-bus non-silent frame capture: WIRED")
print(" asset-backed PCM non-silence:", "PASS" if asset_backed else "NOT_EXECUTED_NO_LOCAL_AUDIO")
if asset_backed:
    for row in asset_rows:
        print("  -",row["asset"],"frames=",row["frames"],"peak=",row["peak"])
print(" human audibility/quality: MANUAL_PENDING")
print(" original Miles parity: HOLD")
