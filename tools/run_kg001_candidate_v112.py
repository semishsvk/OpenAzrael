#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
TMP=ROOT/".tmp/kg001"
ROOMS=[ROOT/"assets/rooms/R1.glb",ROOT/"assets/rooms/R7.glb",ROOT/"assets/rooms/R8.glb"]
VISUAL_AUDIO=[
    ROOT/"assets/audio/797TAP.WAV",
    ROOT/"assets/audio/S152V2.WAV",
    ROOT/"assets/audio/S137.WAV",
    ROOT/"assets/audio/S121.WAV",
    ROOT/"assets/audio/799SECDR.WAV",
    ROOT/"assets/audio/S174ELP1.WAV",
    ROOT/"assets/audio/S174ELP2.WAV",
    ROOT/"assets/audio/S186.WAV",
]
BUILD_MANIFEST=ROOT/"data/generated/kg001_candidate_build_manifest.json"
FORBIDDEN_TRACKED_PREFIXES=(
    "original/","raw/","source_original/","data/audio/original_audio/",
    "assets/audio/","assets/rooms/","assets/textures/classic/"
)
FORBIDDEN_TRACKED_NAMES={"R.EXE","r.exe"}

SOURCE_COMMANDS=[
    [sys.executable,"tools/validate_project_context.py"],
    [sys.executable,"tools/validate_demo_runtime_ir.py"],
    [sys.executable,"tools/audit_gameplay_event_graph_v87.py","--source-only"],
    [sys.executable,"tools/kg001_state_space_v108.py"],
    [sys.executable,"tools/validate_kg001_headless_v109.py"],
    [sys.executable,"tools/validate_kg001_room_trigger_v110.py"],
    [sys.executable,"tools/validate_kg001_full_demo_v111.py"],
    [sys.executable,"tools/validate_candidate_diagnostics_v116.py"],
    [sys.executable,"tools/validate_kg001_audio_runtime_v116.py"],
    [sys.executable,"tools/validate_kg001_texture_colorkey_v116.py"],
    [sys.executable,"tools/validate_kg001_export_preset_v117.py"],
    [sys.executable,"tools/validate_kg001_visual_capture_v117.py"],
    [sys.executable,"tools/validate_source_safe_asset_loading_v117.py"],
    [sys.executable,"tools/validate_candidate2_windows_wrapper_v117.py"],
    [sys.executable,"tools/validate_kg001_candidate2_asset_set_v118.py"],
    [sys.executable,"tools/validate_kg001_test_build_contract_v118.py"],
]

RUNTIMES=[
    ("v109","scripts/kg001_headless_runner_v109.gd","OPENAZRAEL_KG001_V109"),
    ("v110","scripts/kg001_room_trigger_runner_v110.gd","OPENAZRAEL_KG001_V110"),
    ("v111","scripts/kg001_full_demo_runner_v111.gd","OPENAZRAEL_KG001_V111"),
    ("audio_v116","scripts/kg001_audio_runtime_runner_v116.gd","OPENAZRAEL_KG001_AUDIO_V116"),
]

def run(cmd, check=False):
    proc=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if check and proc.returncode!=0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}")
    return proc

def git_clean():
    proc=run(["git","status","--porcelain","--untracked-files=normal"])
    return proc.returncode==0 and proc.stdout.strip()==""

def git_head():
    proc=run(["git","rev-parse","HEAD"])
    return proc.stdout.strip() if proc.returncode==0 else ""

def tracked_files():
    proc=run(["git","ls-files"])
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()] if proc.returncode==0 else []

def repository_safety():
    bad=[]
    for path in tracked_files():
        if path in FORBIDDEN_TRACKED_NAMES or any(path.startswith(prefix) for prefix in FORBIDDEN_TRACKED_PREFIXES):
            bad.append(path)
    return sorted(bad)

def find_godot(explicit):
    candidates=[]
    if explicit:
        candidates.append(explicit)
    if os.environ.get("GODOT_BIN"):
        candidates.append(os.environ["GODOT_BIN"])
    candidates += ["godot4","godot"]
    for candidate in candidates:
        resolved=shutil.which(candidate) if not Path(candidate).is_file() else str(Path(candidate))
        if resolved:
            return resolved
    return None

def parse_marker(output, marker):
    for line in reversed(output.splitlines()):
        if marker in line:
            payload=line.split(marker,1)[1].strip()
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                return {"status":"FAIL","parse_error":payload}
    return {"status":"FAIL","error":"result marker missing"}

def ignored(path):
    rel=str(path.relative_to(ROOT))
    proc=run(["git","check-ignore","-q",rel])
    return proc.returncode==0

def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser(description="Run the OpenAzrael KG-001 candidate suite.")
    ap.add_argument("--godot",help="Godot executable path/name. Otherwise GODOT_BIN, godot4, godot are tried.")
    ap.add_argument("--fresh-checkout",action="store_true",help="Require clean Git state before/after and full v109-v111 runtime PASS.")
    ap.add_argument("--promote-results",action="store_true",help="After verification, copy runtime/fresh-checkout summaries into data/tests for review/commit.")
    ap.add_argument("--visual-capture",action="store_true",help="Also run the graphical canonical R1/R7/R8 capture contract. Requires a non-headless display plus restored room/audio assets.")
    args=ap.parse_args()

    TMP.mkdir(parents=True,exist_ok=True)
    clean_before=git_clean()
    head=git_head()
    bad_tracked=repository_safety()
    asset_present={str(p.relative_to(ROOT)):p.is_file() for p in ROOMS}
    asset_ignored={str(p.relative_to(ROOT)):ignored(p) for p in ROOMS}

    godot=find_godot(args.godot)
    source=[]
    source_ok=True

    toolchain_cmd=[
        sys.executable,
        "tools/validate_kg001_toolchain_v117.py",
    ]
    if godot:
        toolchain_cmd += ["--godot",godot,"--require-godot"]
    toolchain_proc=run(toolchain_cmd)
    toolchain_item={
        "command":toolchain_cmd,
        "returncode":toolchain_proc.returncode,
        "status":"PASS" if toolchain_proc.returncode==0 else "FAIL",
        "output":toolchain_proc.stdout[-12000:],
    }
    source.append(toolchain_item)
    if toolchain_proc.returncode!=0:
        source_ok=False

    manifest_cmd=[
        sys.executable,
        "tools/write_kg001_build_manifest.py",
    ]
    if godot:
        manifest_cmd += ["--godot",godot]
    manifest_proc=run(manifest_cmd)
    manifest_item={
        "command":manifest_cmd,
        "returncode":manifest_proc.returncode,
        "status":"PASS" if manifest_proc.returncode==0 and BUILD_MANIFEST.is_file() else "FAIL",
        "output":manifest_proc.stdout[-12000:],
    }
    source.append(manifest_item)
    if manifest_item["status"]!="PASS":
        source_ok=False

    for cmd in SOURCE_COMMANDS:
        proc=run(cmd)
        item={"command":cmd,"returncode":proc.returncode,"status":"PASS" if proc.returncode==0 else "FAIL","output":proc.stdout[-12000:]}
        source.append(item)
        if proc.returncode!=0:
            source_ok=False

    if not source_ok:
        print("KG-001 source validator failures:", file=sys.stderr)
        for item in source:
            if item.get("status") == "PASS":
                continue
            print(" - " + " ".join(item.get("command", [])), file=sys.stderr)
            print(item.get("output", ""), file=sys.stderr)

    asset_gate={"status":"NOT_REQUIRED","local_asset_status":"UNOBSERVED"}
    if args.fresh_checkout:
        asset_gate_cmd=[
            sys.executable,
            "tools/validate_kg001_candidate2_asset_set_v118.py",
            "--require-complete",
            "--out",
            str(TMP/"kg001_candidate2_asset_set_v118.json"),
        ]
        asset_gate_proc=run(asset_gate_cmd)
        try:
            asset_gate=json.loads(asset_gate_proc.stdout)
        except json.JSONDecodeError:
            asset_gate={
                "status":"FAIL",
                "local_asset_status":"PARSE_ERROR",
                "output":asset_gate_proc.stdout[-12000:],
            }
        asset_gate["_process_returncode"]=asset_gate_proc.returncode

    godot_version=""
    import_status="NOT_RUN"
    runtimes={}
    if godot:
        ver=run([godot,"--version"])
        godot_version=ver.stdout.strip()
        if all(asset_present.values()):
            imported=run([godot,"--headless","--path",str(ROOT),"--import"])
            import_status="PASS" if imported.returncode==0 else "FAIL"
            write_json(TMP/"kg001_godot_import_v112.json",{
                "status":import_status,
                "returncode":imported.returncode,
                "output":imported.stdout[-12000:]
            })
        else:
            import_status="BLOCKED_MISSING_ASSETS"
        for name,script,marker in RUNTIMES:
            if name in ("v110","v111","audio_v116") and not all(asset_present.values()):
                runtimes[name]={"status":"BLOCKED_MISSING_ASSETS","missing":[p for p,v in asset_present.items() if not v]}
                continue
            proc=run([godot,"--headless","--path",str(ROOT),"--script",f"res://{script}"])
            parsed=parse_marker(proc.stdout,marker)
            parsed["_process_returncode"]=proc.returncode
            parsed["_output_tail"]=proc.stdout[-12000:]
            runtimes[name]=parsed
            write_json(TMP/f"kg001_{name}_runtime.json",parsed)
    else:
        for name,_,_ in RUNTIMES:
            runtimes[name]={"status":"BLOCKED_GODOT_NOT_FOUND"}

    visual_capture={"status":"NOT_REQUESTED"}
    if args.visual_capture:
        missing_visual=[
            str(path.relative_to(ROOT))
            for path in [*ROOMS,*VISUAL_AUDIO]
            if not path.is_file()
        ]
        if godot is None:
            visual_capture={"status":"BLOCKED_GODOT_NOT_FOUND"}
        elif missing_visual:
            visual_capture={
                "status":"BLOCKED_MISSING_ASSETS",
                "missing":missing_visual,
            }
        else:
            proc=run([
                godot,
                "--path",str(ROOT),
                "--script","res://scripts/kg001_visual_capture_v117.gd",
            ])
            visual_capture=parse_marker(
                proc.stdout,
                "OPENAZRAEL_KG001_VISUAL_V117",
            )
            visual_capture["_process_returncode"]=proc.returncode
            visual_capture["_output_tail"]=proc.stdout[-12000:]
            write_json(
                TMP/"kg001_visual_capture_v117.json",
                visual_capture,
            )

    clean_after=git_clean()
    full_runtime_pass=all(runtimes.get(name,{}).get("status")=="PASS" for name,_,_ in RUNTIMES)
    visual_pass=(not args.visual_capture) or visual_capture.get("status")=="PASS"
    fresh_pass=(
        args.fresh_checkout and clean_before and clean_after and not bad_tracked and source_ok
        and godot is not None and import_status=="PASS" and full_runtime_pass
        and all(asset_present.values()) and all(asset_ignored.values())
        and asset_gate.get("status")=="PASS"
        and asset_gate.get("local_asset_status")=="COMPLETE"
    )

    fresh={
        "schema":"openazrael.kg001.fresh_checkout",
        "version":112,
        "status":"PASS" if fresh_pass else ("NOT_REQUESTED" if not args.fresh_checkout else "FAIL"),
        "commit_sha":head,
        "build_manifest":str(BUILD_MANIFEST.relative_to(ROOT)) if BUILD_MANIFEST.is_file() else "",
        "build_manifest_present":BUILD_MANIFEST.is_file(),
        "godot_executable":godot or "",
        "godot_version":godot_version,
        "godot_import_status":import_status,
        "clean_before":clean_before,
        "clean_after":clean_after,
        "forbidden_tracked_files":bad_tracked,
        "source_validators_pass":source_ok,
        "room_assets_present":asset_present,
        "room_assets_git_ignored":asset_ignored,
        "candidate2_asset_set_status":asset_gate.get("status"),
        "candidate2_asset_local_status":asset_gate.get("local_asset_status"),
        "runtime_status":{k:v.get("status","") for k,v in runtimes.items()}
    }
    write_json(TMP/"kg001_source_validation_v112.json",{"status":"PASS" if source_ok else "FAIL","commands":source})
    write_json(TMP/"kg001_fresh_checkout.json",fresh)

    overall_pass=(
        source_ok
        and full_runtime_pass
        and (not args.fresh_checkout or fresh_pass)
        and visual_pass
    )
    if args.fresh_checkout:
        exit_pass=fresh_pass and visual_pass
    elif args.visual_capture:
        exit_pass=source_ok and full_runtime_pass and visual_pass
    else:
        # Preserve the historical source-safe/default runner contract: missing
        # ignored commercial assets block runtime evidence but do not make the
        # source-only CI invocation fail.
        exit_pass=source_ok
    overall={
        "schema":"openazrael.kg001.candidate_run",
        "version":112,
        "status":"PASS" if overall_pass else "INCOMPLETE_OR_FAIL",
        "commit_sha":head,
        "build_manifest":str(BUILD_MANIFEST.relative_to(ROOT)) if BUILD_MANIFEST.is_file() else "",
        "godot_version":godot_version,
        "godot_import_status":import_status,
        "source_validators":"PASS" if source_ok else "FAIL",
        "runtimes":{k:v.get("status","") for k,v in runtimes.items()},
        "candidate2_asset_set":asset_gate.get("status",""),
        "candidate2_asset_local_status":asset_gate.get("local_asset_status",""),
        "visual_capture":visual_capture.get("status",""),
        "visual_capture_requested":args.visual_capture,
        "fresh_checkout":fresh["status"],
        "evidence_dir":str(TMP.relative_to(ROOT))
    }
    write_json(TMP/"kg001_candidate_v112.json",overall)

    if args.promote_results:
        mapping={
            TMP/"kg001_v109_runtime.json":ROOT/"data/tests/kg001_headless_runtime_v109.json",
            TMP/"kg001_v110_runtime.json":ROOT/"data/tests/kg001_room_trigger_runtime_v110.json",
            TMP/"kg001_v111_runtime.json":ROOT/"data/tests/kg001_full_demo_runtime_v111.json",
            TMP/"kg001_audio_v116_runtime.json":ROOT/"data/tests/kg001_audio_runtime_v116.json",
            TMP/"kg001_source_validation_v112.json":ROOT/"data/tests/kg001_source_validation_v112.json",
            TMP/"kg001_fresh_checkout.json":ROOT/"data/tests/kg001_fresh_checkout.json",
            TMP/"kg001_visual_capture_v117.json":ROOT/"data/tests/kg001_visual_capture_runtime_v117.json",
        }
        for src,dst in mapping.items():
            if src.is_file():
                dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(src,dst)

    print(json.dumps(overall,indent=2))
    sys.exit(0 if exit_pass else 1)

if __name__=="__main__":
    main()
