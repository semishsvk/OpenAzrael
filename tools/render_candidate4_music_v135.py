#!/usr/bin/env python3
"""Render required Candidate 4 XMIDI music to local Ogg/Vorbis with FluidSynth.

Inputs are the user's official demo XMI files plus an explicitly supplied
SoundFont. Outputs under assets/audio/music are generated, Git-ignored runtime
assets. The receipt contains hashes/metadata only.

The render clock is inherited from xmi_to_midi_v134: 120 XMIDI ticks/second.
AIL loop markers 116/117 define a loop start and (when present) render end;
non-looped tracks receive a short release tail.
"""
from __future__ import annotations
from pathlib import Path
import argparse, ctypes, ctypes.util, hashlib, importlib.metadata, json, os, sys

import numpy as np
try:
    import soundfile as sf
except ImportError as exc:
    raise SystemExit("python package 'soundfile' is required for Candidate 4 music rendering") from exc

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.xmi_to_midi_v134 import parse_xmi_events

IR=ROOT/"data/audio/legacy_world_ir.json"
DEFAULT_ROUTE=ROOT/".tmp/kg001/candidate4_music_route_v133.json"
DEFAULT_RECEIPT=ROOT/".tmp/kg001/candidate4_music_runtime_v135.json"
DEFAULT_OUTPUT=ROOT/"assets/audio/music"
DEFAULT_MANIFEST=ROOT/"data/runtime_generated/candidate4_music_manifest_v135.json"
CLOCK_HZ=120.0

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "UNKNOWN"

def codec_identity() -> dict:
    return {
        "container": "OGG",
        "codec": "VORBIS",
        "python_soundfile_version": _package_version("soundfile"),
        "libsndfile_version": str(getattr(sf, "__libsndfile_version__", "UNKNOWN")),
        "note": "libsndfile performs OGG/Vorbis encoding; byte-identical output is not asserted across platforms/toolchain builds.",
    }

def locate(base: Path,name: str) -> Path|None:
    target=name.upper()
    for p in (base/name,base/name.upper(),base/name.lower(),base/"GAME"/"AZRAEL"/name):
        if p.is_file():return p
    for p in base.rglob("*"):
        if p.is_file() and p.name.upper()==target:return p
    return None

class FluidRenderer:
    def __init__(self, soundfont: Path, sample_rate: int, gain: float, explicit_lib: str|None):
        libname=explicit_lib or os.environ.get("OPENAZRAEL_FLUIDSYNTH_LIB") or ctypes.util.find_library("fluidsynth")
        if not libname:
            raise RuntimeError("FluidSynth shared library not found; use --fluidsynth-lib or OPENAZRAEL_FLUIDSYNTH_LIB")
        self.lib=ctypes.CDLL(libname)
        L=self.lib
        self.lib_identity=Path(str(libname)).name or str(libname)
        self.lib_version="UNKNOWN"
        if hasattr(L,"fluid_version_str"):
            L.fluid_version_str.restype=ctypes.c_char_p
            raw_version=L.fluid_version_str()
            if raw_version:
                self.lib_version=raw_version.decode("utf-8",errors="replace")
        self.lib_sha256=None
        self.lib_hash_scope="UNAVAILABLE_NO_STABLE_RESOLVED_FILE"
        lib_path=Path(str(libname)).expanduser()
        if lib_path.is_file():
            self.lib_sha256=sha256(lib_path.resolve())
            self.lib_hash_scope="EXACT_RESOLVED_NATIVE_LIBRARY_FILE"
        L.new_fluid_settings.restype=ctypes.c_void_p
        L.new_fluid_synth.argtypes=[ctypes.c_void_p];L.new_fluid_synth.restype=ctypes.c_void_p
        L.delete_fluid_synth.argtypes=[ctypes.c_void_p]
        L.delete_fluid_settings.argtypes=[ctypes.c_void_p]
        L.fluid_settings_setnum.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_double]
        L.fluid_synth_sfload.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int];L.fluid_synth_sfload.restype=ctypes.c_int
        L.fluid_synth_noteon.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int]
        L.fluid_synth_noteoff.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int]
        L.fluid_synth_cc.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int]
        L.fluid_synth_program_change.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int]
        L.fluid_synth_pitch_bend.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int]
        L.fluid_synth_channel_pressure.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int]
        if hasattr(L,"fluid_synth_key_pressure"):
            L.fluid_synth_key_pressure.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int]
        L.fluid_synth_write_float.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int]
        self.settings=L.new_fluid_settings()
        if not self.settings:raise RuntimeError("new_fluid_settings failed")
        L.fluid_settings_setnum(self.settings,b"synth.sample-rate",float(sample_rate))
        L.fluid_settings_setnum(self.settings,b"synth.gain",float(gain))
        self.synth=L.new_fluid_synth(self.settings)
        if not self.synth:raise RuntimeError("new_fluid_synth failed")
        sfid=L.fluid_synth_sfload(self.synth,str(soundfont).encode(),1)
        if sfid<0:raise RuntimeError("FluidSynth failed to load SoundFont")
        self.sample_rate=sample_rate

    def identity(self) -> dict:
        return {
            "library_identity": self.lib_identity,
            "version": self.lib_version,
            "native_library_sha256": self.lib_sha256,
            "native_library_hash_scope": self.lib_hash_scope,
        }

    def close(self):
        if getattr(self,"synth",None):self.lib.delete_fluid_synth(self.synth);self.synth=None
        if getattr(self,"settings",None):self.lib.delete_fluid_settings(self.settings);self.settings=None

    def send(self,kind,args):
        L=self.lib;s=self.synth
        if kind=="note_on":L.fluid_synth_noteon(s,*args)
        elif kind=="note_off":L.fluid_synth_noteoff(s,args[0],args[1])
        elif kind=="control_change":L.fluid_synth_cc(s,*args)
        elif kind=="program_change":L.fluid_synth_program_change(s,*args)
        elif kind=="pitch_bend":L.fluid_synth_pitch_bend(s,*args)
        elif kind=="channel_pressure":L.fluid_synth_channel_pressure(s,*args)
        elif kind=="poly_pressure" and hasattr(L,"fluid_synth_key_pressure"):L.fluid_synth_key_pressure(s,*args)
        # meta/sysex do not directly drive the GM synth here.

    def frames(self,count: int):
        left=np.empty(count,dtype=np.float32);right=np.empty(count,dtype=np.float32)
        self.lib.fluid_synth_write_float(self.synth,count,left.ctypes.data,0,1,right.ctypes.data,0,1)
        return np.column_stack((left,right))

def event_json_arg(value):
    """Canonical JSON-safe representation for deterministic XMIDI schedule hashing."""
    if isinstance(value,(bytes,bytearray,memoryview)):
        return {"bytes_hex":bytes(value).hex()}
    if isinstance(value,(tuple,list)):
        return [event_json_arg(item) for item in value]
    if isinstance(value,dict):
        return {str(key):event_json_arg(value[key]) for key in sorted(value,key=lambda item:str(item))}
    if value is None or isinstance(value,(str,int,float,bool)):
        return value
    raise TypeError(f"unsupported schedule argument type: {type(value).__name__}")

def render_one(xmi: Path, out: Path, soundfont: Path, sample_rate: int, gain: float, explicit_lib: str|None, release_tail_seconds: float):
    events,meta=parse_xmi_events(xmi.read_bytes())
    loop_start=meta.get("loop_start_tick");loop_end=meta.get("loop_end_tick")
    render_end_tick=loop_end if loop_end is not None else meta["end_tick"]
    render_end_frame=round(render_end_tick*sample_rate/CLOCK_HZ)
    schedule_payload={
        "clock_hz":CLOCK_HZ,
        "render_end_tick":render_end_tick,
        "loop_start_tick":loop_start,
        "loop_end_tick":loop_end,
        "events":[[int(tick),int(order),kind,[event_json_arg(arg) for arg in args]] for tick,order,kind,args in events],
    }
    event_schedule_sha256=sha256_bytes(json.dumps(schedule_payload,sort_keys=True,separators=(",",":")).encode("utf-8"))
    renderer=FluidRenderer(soundfont,sample_rate,gain,explicit_lib)
    renderer_identity=renderer.identity()
    out.parent.mkdir(parents=True,exist_ok=True)
    current=0;peak=0.0;sum_sq=0.0;samples=0
    pcm_sha=hashlib.sha256()
    def observe(block: np.ndarray) -> None:
        nonlocal peak,sum_sq,samples
        if not block.size:
            return
        canonical=block.astype("<f4",copy=False)
        pcm_sha.update(canonical.tobytes(order="C"))
        peak=max(peak,float(np.max(np.abs(block))))
        sum_sq+=float(np.sum(block.astype(np.float64)**2))
        samples+=block.size
    try:
        with sf.SoundFile(str(out),"w",samplerate=sample_rate,channels=2,format="OGG",subtype="VORBIS") as sink:
            for tick,order,kind,args in events:
                target=round(tick*sample_rate/CLOCK_HZ)
                if target>render_end_frame:break
                while current<target:
                    n=min(8192,target-current)
                    block=renderer.frames(n);sink.write(block);current+=n
                    observe(block)
                renderer.send(kind,args)
            while current<render_end_frame:
                n=min(8192,render_end_frame-current)
                block=renderer.frames(n);sink.write(block);current+=n
                observe(block)
            if loop_end is None and release_tail_seconds>0:
                tail=round(release_tail_seconds*sample_rate)
                while tail>0:
                    n=min(8192,tail);block=renderer.frames(n);sink.write(block);tail-=n
                    observe(block)
    finally:
        renderer.close()
    rms=(sum_sq/samples)**0.5 if samples else 0.0
    if peak<=1e-7 or rms<=1e-8:raise RuntimeError(f"rendered music is silent: {xmi.name}")
    return {
        "source_xmi":xmi.name,
        "output":str(out.relative_to(ROOT)).replace("\\","/"),
        "output_bytes":out.stat().st_size,
        "output_sha256":sha256(out),
        "sample_rate":sample_rate,
        "channels":2,
        "duration_seconds":sf.info(str(out)).duration,
        "peak":peak,
        "rms":rms,
        "loop":loop_start is not None and loop_end is not None,
        "loop_offset_seconds":loop_start/CLOCK_HZ if loop_start is not None else 0.0,
        "source_loop_start_tick":loop_start,
        "source_loop_end_tick":loop_end,
        "source_end_tick":meta["end_tick"],
        "event_schedule_sha256":event_schedule_sha256,
        "pcm_f32le_sha256":pcm_sha.hexdigest(),
        "fluidsynth":renderer_identity,
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("demo_dir",type=Path)
    ap.add_argument("--soundfont",type=Path,required=True)
    ap.add_argument("--route-evidence",type=Path,default=DEFAULT_ROUTE)
    ap.add_argument("--out-dir",type=Path,default=DEFAULT_OUTPUT)
    ap.add_argument("--receipt",type=Path,default=DEFAULT_RECEIPT)
    ap.add_argument("--runtime-manifest",type=Path,default=DEFAULT_MANIFEST)
    ap.add_argument("--fluidsynth-lib")
    ap.add_argument("--sample-rate",type=int,default=44100)
    ap.add_argument("--gain",type=float,default=0.5)
    ap.add_argument("--release-tail-seconds",type=float,default=2.0)
    ap.add_argument("--all",action="store_true",help="Render all 24 canonical XMI files, not only route-required files.")
    args=ap.parse_args()
    demo=args.demo_dir.resolve();soundfont=args.soundfont.resolve()
    if not soundfont.is_file():raise SystemExit("SoundFont not found")
    ir=json.loads(IR.read_text(encoding="utf-8"))
    canonical={row["filename"].upper():row for row in ir.get("audio",{}).get("music_assets",[])}
    if len(canonical)!=24:raise SystemExit("canonical XMI inventory drift")
    route=json.loads(args.route_evidence.read_text(encoding="utf-8"))
    if route.get("status")!="PASS" or route.get("resolution")!="REQUIRES_RUNTIME_MUSIC":
        raise SystemExit("music route evidence must be PASS/REQUIRES_RUNTIME_MUSIC before rendering")
    route_data=route.get("accepted_demo_route",{})
    music_by_room=route_data.get("music_by_room",{})
    if not all(isinstance(music_by_room.get(room),list) and len(music_by_room[room])==1 for room in ("R1","R7","R8")):
        raise SystemExit("route evidence does not contain exactly one binding for R1/R7/R8")
    room_map={room:music_by_room[room][0].upper() for room in ("R1","R7","R8")}
    route_required=[x.upper() for x in route_data.get("required_xmi",[])]
    selected_all=sorted(canonical) if args.all else sorted(set(route_required))
    if not selected_all:raise SystemExit("no route-required XMI tracks")
    unknown=sorted(set(selected_all)-set(canonical))
    if unknown:raise SystemExit("unknown canonical XMI: "+",".join(unknown))
    silence_xmi=sorted(name for name in selected_all if name=="BLANK.XMI")
    selected=[name for name in selected_all if name!="BLANK.XMI"]
    args.out_dir.mkdir(parents=True,exist_ok=True)
    for stale in args.out_dir.glob("*.ogg"):
        stale.unlink()
    rows=[]
    for name in selected:
        source=locate(demo,name)
        if not source:raise SystemExit("missing source XMI: "+name)
        observed=sha256(source)
        if observed!=canonical[name].get("sha256"):raise SystemExit("XMI fingerprint mismatch: "+name)
        out=args.out_dir/(Path(name).stem+".ogg")
        row=render_one(source,out,soundfont,args.sample_rate,args.gain,args.fluidsynth_lib,args.release_tail_seconds)
        row["source_sha256"]=observed
        rows.append(row)
    track_map={row["source_xmi"].upper():row for row in rows}
    runtime_manifest={
        "schema":"openazrael.kg001.candidate4_music_manifest",
        "version":135,
        "status":"PASS",
        "music_by_room":room_map,
        "silence_identity":"BLANK.XMI",
        "tracks":{
            name:{
                "path":"res://"+track_map[name]["output"],
                "sha256":track_map[name]["output_sha256"],
                "loop":track_map[name]["loop"],
                "loop_offset_seconds":track_map[name]["loop_offset_seconds"],
                "duration_seconds":track_map[name]["duration_seconds"],
            }
            for name in track_map
        },
    }
    args.runtime_manifest.parent.mkdir(parents=True,exist_ok=True)
    args.runtime_manifest.write_text(json.dumps(runtime_manifest,indent=2)+"\n",encoding="utf-8")
    receipt={
        "schema":"openazrael.kg001.candidate4_music_runtime",
        "version":135,
        "status":"PASS",
        "runtime_playback_test":"PENDING_GODOT",
        "rendered_xmi":[row["source_xmi"].upper() for row in rows],
        "silence_xmi":silence_xmi,
        "required_xmi":route_required,
        "music_by_room":room_map,
        "all_canonical_rendered":len(selected_all)==24,
        "soundfont":{"bytes":soundfont.stat().st_size,"sha256":sha256(soundfont)},
        "renderer":{
            "backend":"FluidSynth",
            "sample_rate":args.sample_rate,
            "gain":args.gain,
            "fluidsynth":rows[0]["fluidsynth"] if rows else {},
            "codec":codec_identity(),
        },
        "reproducibility_boundary":{
            "event_timing_identity":"event_schedule_sha256 is canonical and codec-independent",
            "pcm_content_identity":"pcm_f32le_sha256 hashes the exact interleaved little-endian float32 PCM produced before encoding",
            "ogg_output_identity":"output_sha256 identifies the exact OGG artifact produced by this invocation",
            "cross_platform_pcm_bit_identity_guaranteed":False,
            "cross_platform_ogg_bit_identity_guaranteed":False,
            "reason":"FluidSynth floating-point behavior and libsndfile/Vorbis container/codec output may vary across platform or toolchain builds.",
        },
        "tracks":rows,
        "runtime_manifest":{
            "path":str(args.runtime_manifest.relative_to(ROOT)).replace("\\","/"),
            "sha256":sha256(args.runtime_manifest),
        },
        "source_safe_receipt":True,
    }
    args.receipt.parent.mkdir(parents=True,exist_ok=True)
    args.receipt.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
