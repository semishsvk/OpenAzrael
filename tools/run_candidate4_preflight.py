#!/usr/bin/env python3
"""Fail-closed KG-001 Candidate 4 end-to-end preflight (v136).

Order is intentionally fail-fast:
1) source contracts,
2) official-demo MUSIC.DAT/XMI route proof,
3) deterministic complete music render,
4) inherited asset-backed Candidate 3 + v117-v131 + PPPV v2 suite,
5) Godot music playback/loop routing,
6) complete 30-WAV + 24-XMI audio gate,
7) final v131 room-forensic evidence.

Only then is Candidate 4 export_allowed.
"""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.remaster_framework.source_registry import resolve_source
TMP=ROOT/".tmp/kg001"
C3=TMP/"candidate3_preflight_receipt.json"
OUT=TMP/"candidate4_preflight_receipt.json"
AUDIO_RESULT=TMP/"candidate4_audio_v132_runtime.json"
MUSIC_ROUTE=TMP/"candidate4_music_route_v133.json"
MUSIC_RUNTIME=TMP/"candidate4_music_runtime_v135.json"
MUSIC_GODOT=TMP/"candidate4_music_godot_v136.json"
MUSIC_MANIFEST=ROOT/"data/runtime_generated/candidate4_music_manifest_v135.json"

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def run(cmd):
    return subprocess.run(cmd,cwd=ROOT,text=True,encoding="utf-8",errors="replace",
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

def parse_marker(output: str, marker: str) -> dict:
    for line in reversed(output.splitlines()):
        if marker in line:
            payload=line.split(marker,1)[1].strip()
            try:return json.loads(payload)
            except json.JSONDecodeError:return {"status":"FAIL","parse_error":payload}
    return {"status":"FAIL","error":"result marker missing"}

def engine_errors(output: str) -> list[str]:
    return [line for line in output.splitlines()
            if line.lstrip().startswith(("ERROR:","SCRIPT ERROR:"))]

def fail(reason,details=None):
    OUT.unlink(missing_ok=True)
    out={"schema":"openazrael.kg001.candidate4_preflight","version":136,
         "status":"FAIL","candidate":"KG-001 Candidate 4","export_allowed":False,
         "reason":reason}
    if details is not None:out["details"]=details
    print(json.dumps(out,indent=2))
    return 1

def load_json(path: Path):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return None

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--godot")
    ap.add_argument(
        "--demo-dir",
        type=Path,
        help=(
            "Optional extracted ATDEMO directory. If omitted, use the "
            "persistent registered demo corpus."
        ),
    )
    ap.add_argument("--soundfont",type=Path)
    ap.add_argument("--fluidsynth-lib")
    args=ap.parse_args()

    for path in (OUT,AUDIO_RESULT,MUSIC_ROUTE,MUSIC_RUNTIME,MUSIC_GODOT,MUSIC_MANIFEST):
        path.unlink(missing_ok=True)

    # Cheap source-level blockers first.
    for tool in (
        "tools/validate_kg001_trigger_events_v137.py",
        "tools/validate_candidate4_release_contract_v132.py",
        "tools/validate_candidate4_music_route_v133.py",
        "tools/validate_xmi_to_midi_v134.py",
        "tools/validate_candidate4_music_renderer_v135.py",
    ):
        proc=run([sys.executable,tool])
        if proc.returncode!=0:
            return fail("CANDIDATE4_SOURCE_CONTRACT_FAILED",{
                "tool":tool,"returncode":proc.returncode,"output_tail":proc.stdout[-12000:]
            })

    try:
        demo=(
            args.demo_dir.resolve()
            if args.demo_dir is not None
            else resolve_source("demo")
        )
    except Exception as exc:
        return fail("DEMO_SOURCE_NOT_REGISTERED_OR_INVALID",{
            "error":str(exc),
            "hint":(
                "Run: python tools/bootstrap_openazrael_sources.py "
                "register demo <atdemo.zip-or-extracted-dir>"
            ),
        })

    route_run=run([
        sys.executable,"tools/analyze_candidate4_music_route_v133.py",
        str(demo),"--out",str(MUSIC_ROUTE),
    ])
    route=load_json(MUSIC_ROUTE)
    if route_run.returncode!=0 or not isinstance(route,dict) or route.get("status")!="PASS":
        return fail("CANDIDATE4_MUSIC_ROUTE_UNRESOLVED",{
            "returncode":route_run.returncode,
            "route":route,
            "output_tail":route_run.stdout[-12000:],
        })
    if route.get("resolution")!="REQUIRES_RUNTIME_MUSIC":
        return fail("CANDIDATE4_MUSIC_ROUTE_RESOLUTION_UNEXPECTED",route)

    soundfont=args.soundfont
    if soundfont is None and os.environ.get("OPENAZRAEL_SOUNDFONT"):
        soundfont=Path(os.environ["OPENAZRAEL_SOUNDFONT"])
    if soundfont is None or not soundfont.expanduser().resolve().is_file():
        return fail("CANDIDATE4_SOUNDFONT_REQUIRED",{
            "usage":"--soundfont <redistributable-or-local.sf2> or OPENAZRAEL_SOUNDFONT",
            "note":"SoundFont bytes are not committed; exact hash is bound into the render receipt."
        })
    soundfont=soundfont.expanduser().resolve()

    render_cmd=[
        sys.executable,"tools/render_candidate4_music_v135.py",str(demo),
        "--soundfont",str(soundfont),
        "--route-evidence",str(MUSIC_ROUTE),
        "--receipt",str(MUSIC_RUNTIME),
        "--runtime-manifest",str(MUSIC_MANIFEST),
        "--all",
    ]
    if args.fluidsynth_lib:
        render_cmd += ["--fluidsynth-lib",args.fluidsynth_lib]
    render=run(render_cmd)
    music_runtime=load_json(MUSIC_RUNTIME)
    if (
        render.returncode!=0
        or not isinstance(music_runtime,dict)
        or music_runtime.get("status")!="PASS"
        or music_runtime.get("all_canonical_rendered") is not True
        or not MUSIC_MANIFEST.is_file()
    ):
        return fail("CANDIDATE4_MUSIC_RENDER_FAILED",{
            "returncode":render.returncode,
            "receipt":music_runtime,
            "output_tail":render.stdout[-16000:],
        })

    # Now snapshot/test the complete asset set, including rendered OGG music.
    cmd=[sys.executable,"tools/run_candidate3_preflight.py"]
    if args.godot:cmd += ["--godot",args.godot]
    cmd += ["--demo-dir",str(demo)]
    inherited=run(cmd)
    if inherited.returncode!=0 or not C3.is_file():
        return fail("INHERITED_RUNTIME_PREFLIGHT_FAILED",{
            "returncode":inherited.returncode,"output_tail":inherited.stdout[-20000:]
        })
    c3=load_json(C3)
    if not isinstance(c3,dict) or c3.get("status")!="PASS" or c3.get("export_allowed") is not True:
        return fail("INHERITED_RUNTIME_PREFLIGHT_NOT_PASS",c3)

    if not MUSIC_MANIFEST.is_file():
        return fail("CANDIDATE4_MUSIC_MANIFEST_LOST_DURING_PREFLIGHT")

    godot=str(c3.get("godot_executable",""))
    if not godot:
        return fail("CANDIDATE4_GODOT_EXECUTABLE_MISSING_FROM_INHERITED_RECEIPT")
    music_godot=run([
        godot,"--headless","--path",str(ROOT),"--script",
        "res://scripts/kg001_music_runtime_runner_v136.gd",
    ])
    godot_errors=engine_errors(music_godot.stdout)
    music_result=parse_marker(music_godot.stdout,"OPENAZRAEL_KG001_MUSIC_V136")
    MUSIC_GODOT.write_text(json.dumps(music_result,indent=2)+"\n",encoding="utf-8")
    if music_godot.returncode!=0 or godot_errors or music_result.get("status")!="PASS":
        return fail("CANDIDATE4_MUSIC_GODOT_V136_FAILED",{
            "returncode":music_godot.returncode,
            "engine_errors":godot_errors,
            "result":music_result,
            "output_tail":music_godot.stdout[-16000:],
        })

    # Promote the local render receipt only after Godot proves resource/player/loop routing.
    music_runtime=load_json(MUSIC_RUNTIME)
    if not isinstance(music_runtime,dict):
        return fail("CANDIDATE4_MUSIC_RUNTIME_RECEIPT_LOST")
    music_runtime["runtime_playback_test"]="PASS"
    music_runtime["godot_runtime_v136"]={
        "path":str(MUSIC_GODOT.relative_to(ROOT)).replace("\\","/"),
        "sha256":sha256(MUSIC_GODOT),
        "status":"PASS",
    }
    music_runtime["runtime_manifest_sha256"]=sha256(MUSIC_MANIFEST)
    MUSIC_RUNTIME.write_text(json.dumps(music_runtime,indent=2)+"\n",encoding="utf-8")

    audio=run([sys.executable,"tools/validate_candidate4_audio_corpus_v132.py"])
    try:audio_payload=json.loads(audio.stdout)
    except Exception:audio_payload={"status":"FAIL","raw":audio.stdout[-12000:]}
    AUDIO_RESULT.write_text(json.dumps(audio_payload,indent=2)+"\n",encoding="utf-8")
    if audio.returncode!=0 or audio_payload.get("status")!="PASS":
        return fail("CANDIDATE4_COMPLETE_AUDIO_FAILED",audio_payload)

    forensic_meta=c3.get("evidence",{}).get("room_forensic_v131",{})
    forensic_path=ROOT/str(forensic_meta.get("path",""))
    if not forensic_path.is_file() or sha256(forensic_path)!=forensic_meta.get("sha256"):
        return fail("ROOM_FORENSIC_V131_EVIDENCE_CHANGED")
    forensic=load_json(forensic_path)
    if (
        not isinstance(forensic,dict)
        or forensic.get("status")!="PASS"
        or any(forensic.get("rooms",{}).get(room,{}).get("status")!="PASS"
               for room in ("R1","R7","R8"))
    ):
        return fail("ROOM_FORENSIC_V131_NOT_PASS",forensic)

    receipt=dict(c3)
    receipt.update({
        "schema":"openazrael.kg001.candidate4_preflight",
        "version":136,
        "candidate":"KG-001 Candidate 4",
        "status":"PASS",
        "export_allowed":True,
        "candidate3_preflight_receipt_sha256":sha256(C3),
        "candidate4_audio_v132":"PASS",
        "candidate4_music_route_v133":"PASS",
        "candidate4_music_render_v135":"PASS",
        "candidate4_music_godot_v136":"PASS",
        "room_forensic_v131":"PASS",
    })
    evidence=receipt.setdefault("evidence",{})
    evidence["candidate4_audio_v132"]={"path":str(AUDIO_RESULT.relative_to(ROOT)),"sha256":sha256(AUDIO_RESULT)}
    evidence["candidate4_music_route_v133"]={"path":str(MUSIC_ROUTE.relative_to(ROOT)),"sha256":sha256(MUSIC_ROUTE)}
    evidence["candidate4_music_runtime_v135"]={"path":str(MUSIC_RUNTIME.relative_to(ROOT)),"sha256":sha256(MUSIC_RUNTIME)}
    evidence["candidate4_music_godot_v136"]={"path":str(MUSIC_GODOT.relative_to(ROOT)),"sha256":sha256(MUSIC_GODOT)}
    evidence["candidate4_music_manifest_v135"]={"path":str(MUSIC_MANIFEST.relative_to(ROOT)),"sha256":sha256(MUSIC_MANIFEST)}
    receipt["build_rule"]=(
        "Candidate 4 export is permitted only while exact Git HEAD, clean tree, Godot, "
        "all inherited v109-v131/PPPV evidence, complete 30-WAV corpus, complete rendered "
        "24-XMI identity set (23 audible + BLANK), Godot v136 music routing, the v131 "
        "room-forensic report and the exact runtime asset set remain identical."
    )
    OUT.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
