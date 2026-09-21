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
FORBIDDEN_TRACKED_PREFIXES=(
    "original/","raw/","source_original/","data/audio/original_audio/",
    "assets/audio/","assets/rooms/","assets/textures/classic/"
)
FORBIDDEN_TRACKED_NAMES={"R.EXE","r.exe"}

SOURCE_COMMANDS=[
    [sys.executable,"tools/validate_project_context.py"],
    [sys.executable,"tools/validate_kg001_contract.py"],
    [sys.executable,"-m","tools.remaster_framework.cli","validate"],
    [sys.executable,"-m","unittest","discover","-s","tools/remaster_framework/tests","-v"],
    [sys.executable,"-m","tools.openazrael_adapters.runtime_capabilities",".","--require-core"],
    [sys.executable,"tools/validate_demo_runtime_ir.py"],
    [sys.executable,"tools/audit_gameplay_event_graph_v87.py","--source-only"],
    [sys.executable,"tools/kg001_state_space_v108.py"],
    [sys.executable,"tools/validate_kg001_headless_v109.py"],
    [sys.executable,"tools/validate_kg001_room_trigger_v110.py"],
    [sys.executable,"tools/validate_kg001_full_demo_v111.py"],
    [sys.executable,"tools/validate_candidate_diagnostics_v116.py"],
]

RUNTIMES=[
    ("v109","scripts/kg001_headless_runner_v109.gd","OPENAZRAEL_KG001_V109"),
    ("v110","scripts/kg001_room_trigger_runner_v110.gd","OPENAZRAEL_KG001_V110"),
    ("v111","scripts/kg001_full_demo_runner_v111.gd","OPENAZRAEL_KG001_V111"),
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
    ap.add_argument("--promote-results",action="store_true",help="After verification, copy runtime/fresh-checkout/framework summaries into data/tests for review/commit.")
    ap.add_argument("--stage-framework-metadata",action="store_true",help="After G09 observation, stage ignored source-safe provenance/release/PPPV metadata under data/runtime for a subsequent manual Candidate/F11 run.")
    args=ap.parse_args()

    TMP.mkdir(parents=True,exist_ok=True)
    clean_before=git_clean()
    head=git_head()
    bad_tracked=repository_safety()
    asset_present={str(p.relative_to(ROOT)):p.is_file() for p in ROOMS}
    asset_ignored={str(p.relative_to(ROOT)):ignored(p) for p in ROOMS}

    source=[]
    source_ok=True
    for cmd in SOURCE_COMMANDS:
        proc=run(cmd)
        item={"command":cmd,"returncode":proc.returncode,"status":"PASS" if proc.returncode==0 else "FAIL","output":proc.stdout[-12000:]}
        source.append(item)
        if proc.returncode!=0:
            source_ok=False

    godot=find_godot(args.godot)
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
            if name in ("v110","v111") and not all(asset_present.values()):
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

    clean_after=git_clean()
    full_runtime_pass=all(runtimes.get(name,{}).get("status")=="PASS" for name,_,_ in RUNTIMES)
    fresh_pass=(
        args.fresh_checkout and clean_before and clean_after and not bad_tracked and source_ok
        and godot is not None and import_status=="PASS" and full_runtime_pass
        and all(asset_present.values()) and all(asset_ignored.values())
    )

    fresh={
        "schema":"openazrael.kg001.fresh_checkout",
        "version":112,
        "status":"PASS" if fresh_pass else ("NOT_REQUESTED" if not args.fresh_checkout else "FAIL"),
        "commit_sha":head,
        "godot_executable":godot or "",
        "godot_version":godot_version,
        "godot_import_status":import_status,
        "clean_before":clean_before,
        "clean_after":clean_after,
        "forbidden_tracked_files":bad_tracked,
        "source_validators_pass":source_ok,
        "room_assets_present":asset_present,
        "room_assets_git_ignored":asset_ignored,
        "runtime_status":{k:v.get("status","") for k,v in runtimes.items()}
    }
    write_json(TMP/"kg001_source_validation_v112.json",{"status":"PASS" if source_ok else "FAIL","commands":source})
    write_json(TMP/"kg001_fresh_checkout.json",fresh)

    overall={
        "schema":"openazrael.kg001.candidate_run",
        "version":112,
        "status":"PASS" if source_ok and full_runtime_pass and (not args.fresh_checkout or fresh_pass) else "INCOMPLETE_OR_FAIL",
        "commit_sha":head,
        "godot_version":godot_version,
        "godot_import_status":import_status,
        "source_validators":"PASS" if source_ok else "FAIL",
        "runtimes":{k:v.get("status","") for k,v in runtimes.items()},
        "fresh_checkout":fresh["status"],
        "evidence_dir":str(TMP.relative_to(ROOT))
    }
    write_json(TMP/"kg001_candidate_v112.json",overall)

    framework_cmd=[
        sys.executable,
        "-m",
        "tools.openazrael_adapters.kg001_candidate_framework",
        "--repo-root",str(ROOT),
        "--evidence-root",str(TMP),
        "--commit-sha",head,
        "--godot-version",godot_version,
    ]
    manual_path=ROOT/"data/tests/kg001_manual_sanity.json"
    if manual_path.is_file():
        framework_cmd += ["--manual",str(manual_path)]
    framework_proc=run(framework_cmd)
    framework_bundle_path=TMP/"kg001_framework_bundle.json"
    framework_status="PASS" if framework_proc.returncode==0 and framework_bundle_path.is_file() else "FAIL"

    metadata_stage_status="NOT_REQUESTED"
    if args.stage_framework_metadata:
        metadata_cmd=[
            sys.executable,
            "-m",
            "tools.remaster_framework.runtime_metadata",
            "stage",
            "--project-root",str(ROOT),
            "--build-provenance",str(TMP/"build_provenance.json"),
            "--release-gate-summary",str(TMP/"release_gate_summary.json"),
            "--pppv-coverage",str(TMP/"pppv_coverage.json"),
            "--output",str(TMP/"runtime_metadata_stage.json"),
        ]
        metadata_proc=run(metadata_cmd)
        metadata_stage_status="PASS" if metadata_proc.returncode==0 else "FAIL"

    if args.promote_results:
        mapping={
            TMP/"kg001_v109_runtime.json":ROOT/"data/tests/kg001_headless_runtime_v109.json",
            TMP/"kg001_v110_runtime.json":ROOT/"data/tests/kg001_room_trigger_runtime_v110.json",
            TMP/"kg001_v111_runtime.json":ROOT/"data/tests/kg001_full_demo_runtime_v111.json",
            TMP/"kg001_source_validation_v112.json":ROOT/"data/tests/kg001_source_validation_v112.json",
            TMP/"kg001_fresh_checkout.json":ROOT/"data/tests/kg001_fresh_checkout.json",
            TMP/"kg001_release_gate_results.json":ROOT/"data/tests/kg001_release_gate_results.json",
            TMP/"release_gate_summary.json":ROOT/"data/tests/kg001_release_gate_summary.json",
            TMP/"pppv_coverage.json":ROOT/"data/tests/kg001_pppv_coverage.json",
            TMP/"build_provenance.json":ROOT/"data/tests/kg001_build_provenance.json",
            TMP/"kg001_framework_bundle.json":ROOT/"data/tests/kg001_framework_bundle.json",
        }
        for src,dst in mapping.items():
            if src.is_file():
                dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(src,dst)

    console_summary=overall.copy()
    console_summary["framework_bundle"]=framework_status
    console_summary["framework_metadata_stage"]=metadata_stage_status
    print(json.dumps(console_summary,indent=2))
    framework_ok = framework_status == "PASS"
    metadata_ok = (
        not args.stage_framework_metadata
        or metadata_stage_status == "PASS"
    )
    if args.fresh_checkout:
        sys.exit(0 if fresh_pass and framework_ok and metadata_ok else 1)
    sys.exit(0 if source_ok and framework_ok and metadata_ok else 1)

if __name__=="__main__":
    main()
