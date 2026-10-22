#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TMP=ROOT/".tmp/kg001"
ROOMS=[ROOT/"assets/rooms/R1.glb",ROOT/"assets/rooms/R7.glb",ROOT/"assets/rooms/R8.glb"]
FORBIDDEN_TRACKED_PREFIXES=(
    "original/","raw/","source_original/","data/audio/original_audio/",
    "assets/audio/","assets/characters/","assets/rooms/","assets/textures/classic/","assets/ui/mice/","assets/ui/legacy_menu/"
)
FORBIDDEN_TRACKED_NAMES={"R.EXE","r.exe"}

from tools.kg001_gate_manifest import SOURCE_COMMANDS, RUNTIMES

def run(cmd, check=False):
    try:
        proc=subprocess.run(cmd,cwd=ROOT,text=True,encoding="utf-8",errors="replace",stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
    except subprocess.TimeoutExpired as exc:
        output=exc.stdout or ""
        if isinstance(output,bytes):
            output=output.decode("utf-8",errors="replace")
        proc=subprocess.CompletedProcess(cmd,124,output+"\nERROR: Candidate command timed out after 180 seconds\n")
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

def engine_errors(output):
    errors=[]
    for line in output.splitlines():
        stripped=line.lstrip()
        # Godot 4.7.2 can report reference-counted resources still alive during
        # immediate headless shutdown even when the runtime marker and process
        # return code are clean. Treat only this exact teardown diagnostic as
        # non-fatal; all other ERROR/SCRIPT ERROR lines remain fail-closed.
        if re.fullmatch(
            r"ERROR: \d+ resources still in use at exit \(run with --verbose for details\)\.",
            stripped,
        ):
            continue
        if stripped.startswith(("ERROR:", "SCRIPT ERROR:")):
            errors.append(line)
    return errors

def ignored(path):
    rel=str(path.relative_to(ROOT))
    proc=run(["git","check-ignore","-q",rel])
    return proc.returncode==0

def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8",newline="\n")

def main():
    ap=argparse.ArgumentParser(description="Run the OpenAzrael KG-001 candidate suite.")
    ap.add_argument("--godot",help="Godot executable path/name. Otherwise GODOT_BIN, godot4, godot are tried.")
    ap.add_argument("--fresh-checkout",action="store_true",help="Require clean Git state before/after and v109-v111, audio-v116, physical-v117, well-tongs-v118 and R1-route-v119, collision-parity-v120, surface-coverage-v121 and geometry-render-parity-v122 object-visibility-v123, material/UV-v124, transform-v125 and reachable-state-visibility-v127 runtime PASS.")
    ap.add_argument("--promote-results",action="store_true",help="After verification, copy runtime/fresh-checkout summaries into data/tests for review/commit.")
    ap.add_argument("--source-only",action="store_true",help="Run source-safe validators and repository tracking checks only; do not require Godot or local commercial assets.")
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
        display_cmd=[Path(arg).name if index==0 else arg for index,arg in enumerate(cmd)]
        item={"command":display_cmd,"returncode":proc.returncode,"status":"PASS" if proc.returncode==0 else "FAIL","output":proc.stdout[-12000:]}
        source.append(item)
        if proc.returncode!=0:
            source_ok=False

    source_receipt={
        "schema":"openazrael.kg001.source_gate",
        "version":112,
        "status":"PASS" if source_ok and not bad_tracked else "FAIL",
        "commit_sha":head,
        "source_validators_pass":source_ok,
        "forbidden_tracked_files":bad_tracked,
        "commands":source,
    }
    write_json(TMP/"kg001_source_validation_v112.json",source_receipt)
    if args.source_only:
        print(json.dumps(source_receipt,indent=2))
        sys.exit(0 if source_receipt["status"]=="PASS" else 1)

    generated_inputs={}
    generation_commands=[
        ("fidelity_v124",[sys.executable,"tools/build_demo_room_fidelity_manifest_v124.py"]),
        ("state_matrix_v127",[sys.executable,"tools/kg001_state_matrix_v127.py"]),
        ("asset_manifest_v128",[sys.executable,"tools/build_runtime_asset_manifest_v128.py"]),
        ("texture_orientation_v133",[sys.executable,"tools/audit_demo_texture_orientation_v133.py"]),
    ]
    for name,cmd in generation_commands:
        proc=run(cmd)
        generated_inputs[name]={
            "status":"PASS" if proc.returncode==0 else "FAIL",
            "returncode":proc.returncode,
            "output":proc.stdout[-12000:],
        }
    generated_ok=all(item["status"]=="PASS" for item in generated_inputs.values())

    godot=find_godot(args.godot)
    godot_version=""
    import_status="NOT_RUN"
    runtimes={}
    if godot:
        ver=run([godot,"--version"])
        godot_version=ver.stdout.strip()
        if all(asset_present.values()):
            imported=run([godot,"--headless","--path",str(ROOT),"--import"])
            import_status="PASS" if imported.returncode==0 and not engine_errors(imported.stdout) else "FAIL"
            write_json(TMP/"kg001_godot_import_v112.json",{
                "status":import_status,
                "returncode":imported.returncode,
                "output":imported.stdout[-12000:]
            })
        else:
            import_status="BLOCKED_MISSING_ASSETS"
        for name,script,marker in RUNTIMES:
            if name in ("v110","trigger_v137","v111","audio_v116","physical_v117","well_tongs_v118","r1_route_v119","collision_v120","surface_v121","geometry_v122","visibility_v123","material_v124","transform_v125","reachable_visibility_v127","portal_v129","interaction_v130","save_compat_v150","inventory_hud_v157") and not all(asset_present.values()):
                runtimes[name]={"status":"BLOCKED_MISSING_ASSETS","missing":[p for p,v in asset_present.items() if not v]}
                continue
            proc=run([godot,"--headless","--fixed-fps","60","--path",str(ROOT),"--script",f"res://{script}"])
            parsed=parse_marker(proc.stdout,marker)
            errors=engine_errors(proc.stdout)
            if proc.returncode!=0 or errors:
                parsed["status"]="FAIL"
                parsed["engine_errors"]=errors
            parsed["_process_returncode"]=proc.returncode
            parsed["_output_tail"]=proc.stdout[-12000:]
            runtimes[name]=parsed
            write_json(TMP/f"kg001_{name}_runtime.json",parsed)
    else:
        for name,_,_ in RUNTIMES:
            runtimes[name]={"status":"BLOCKED_GODOT_NOT_FOUND"}

    # Replace every result, including skipped tests, so promotion cannot reuse
    # an earlier PASS. Bind the evidence to the checkout that ran this suite.
    for name,result in runtimes.items():
        result["_commit_sha"]=head
        write_json(TMP/f"kg001_{name}_runtime.json",result)
    if not godot or not all(asset_present.values()):
        write_json(TMP/"kg001_godot_import_v112.json",{"status":import_status,"commit_sha":head})

    clean_after=git_clean()
    full_runtime_pass=all(runtimes.get(name,{}).get("status")=="PASS" for name,_,_ in RUNTIMES)
    fresh_pass=(
        args.fresh_checkout and clean_before and clean_after and not bad_tracked and source_ok
        and godot is not None and import_status=="PASS" and full_runtime_pass
        and all(asset_present.values()) and all(asset_ignored.values()) and generated_ok
    )

    fresh={
        "schema":"openazrael.kg001.fresh_checkout",
        "version":112,
        "status":"PASS" if fresh_pass else ("NOT_REQUESTED" if not args.fresh_checkout else "FAIL"),
        "commit_sha":head,
        "godot_executable":Path(godot).name if godot else "",
        "godot_version":godot_version,
        "godot_import_status":import_status,
        "clean_before":clean_before,
        "clean_after":clean_after,
        "forbidden_tracked_files":bad_tracked,
        "source_validators_pass":source_ok,
        "generated_inputs":generated_inputs,
        "generated_inputs_pass":generated_ok,
        "room_assets_present":asset_present,
        "room_assets_git_ignored":asset_ignored,
        "runtime_status":{k:v.get("status","") for k,v in runtimes.items()}
    }
    write_json(TMP/"kg001_fresh_checkout.json",fresh)

    overall={
        "schema":"openazrael.kg001.candidate_run",
        "version":112,
        "status":"PASS" if source_ok and import_status=="PASS" and full_runtime_pass and (not args.fresh_checkout or fresh_pass) else "INCOMPLETE_OR_FAIL",
        "commit_sha":head,
        "godot_version":godot_version,
        "godot_import_status":import_status,
        "source_validators":"PASS" if source_ok else "FAIL",
        "runtimes":{k:v.get("status","") for k,v in runtimes.items()},
        "fresh_checkout":fresh["status"],
        "evidence_dir":str(TMP.relative_to(ROOT))
    }
    write_json(TMP/"kg001_candidate_v112.json",overall)

    if args.promote_results:
        mapping={
            TMP/"kg001_v109_runtime.json":ROOT/"data/tests/kg001_headless_runtime_v109.json",
            TMP/"kg001_v110_runtime.json":ROOT/"data/tests/kg001_room_trigger_runtime_v110.json",
            TMP/"kg001_trigger_v137_runtime.json":ROOT/"data/tests/kg001_trigger_event_runtime_v137.json",
            TMP/"kg001_localization_v139_runtime.json":ROOT/"data/tests/localization_runtime_v139.json",
            TMP/"kg001_v111_runtime.json":ROOT/"data/tests/kg001_full_demo_runtime_v111.json",
            TMP/"kg001_audio_v116_runtime.json":ROOT/"data/tests/kg001_audio_runtime_v116.json",
            TMP/"kg001_physical_v117_runtime.json":ROOT/"data/tests/kg001_physical_traversal_runtime_v117.json",
            TMP/"kg001_well_tongs_v118_runtime.json":ROOT/"data/tests/kg001_well_tongs_animation_runtime_v118.json",
            TMP/"kg001_r1_route_v119_runtime.json":ROOT/"data/tests/kg001_r1_route_runtime_v119.json",
            TMP/"kg001_collision_v120_runtime.json":ROOT/"data/tests/kg001_collision_parity_runtime_v120.json",
            TMP/"kg001_surface_v121_runtime.json":ROOT/"data/tests/kg001_surface_collision_runtime_v121.json",
            TMP/"kg001_geometry_v122_runtime.json":ROOT/"data/tests/kg001_geometry_render_parity_runtime_v122.json",
            TMP/"kg001_visibility_v123_runtime.json":ROOT/"data/tests/kg001_object_visibility_runtime_v123.json",
            TMP/"kg001_material_v124_runtime.json":ROOT/"data/tests/kg001_material_texture_runtime_v124.json",
            TMP/"kg001_transform_v125_runtime.json":ROOT/"data/tests/kg001_transform_parity_runtime_v125.json",
            TMP/"kg001_reachable_visibility_v127_runtime.json":ROOT/"data/tests/kg001_reachable_visibility_runtime_v127.json",
            TMP/"kg001_portal_v129_runtime.json":ROOT/"data/tests/kg001_portal_geometry_runtime_v129.json",
            TMP/"kg001_interaction_v130_runtime.json":ROOT/"data/tests/kg001_interaction_reachability_runtime_v130.json",
            TMP/"kg001_all_transitions_v141_runtime.json":ROOT/"data/tests/kg001_all_transition_traversal_runtime_v141.json",
            TMP/"kg001_cursor_v143_runtime.json":ROOT/"data/tests/kg001_interaction_cursor_runtime_v143.json",
            TMP/"kg001_menu_v145_runtime.json":ROOT/"data/tests/kg001_legacy_menu_runtime_v145.json",
            TMP/"kg001_menu_cursor_v146_runtime.json":ROOT/"data/tests/kg001_menu_cursor_context_runtime_v146.json",
            TMP/"kg001_classic_v147_runtime.json":ROOT/"data/tests/kg001_classic_presentation_runtime_v147.json",
            TMP/"kg001_interaction_probe_v148_runtime.json":ROOT/"data/tests/kg001_interaction_probe_determinism_runtime_v148.json",
            TMP/"kg001_save_compat_v150_runtime.json":ROOT/"data/tests/kg001_save_compat_runtime_v150.json",
            TMP/"kg001_inventory_hud_v157_runtime.json":ROOT/"data/tests/kg001_inventory_hud_runtime_v157.json",
            TMP/"kg001_menu_toggle_v149_runtime.json":ROOT/"data/tests/kg001_legacy_menu_toggle_runtime_v149.json",
            TMP/"kg001_source_validation_v112.json":ROOT/"data/tests/kg001_source_validation_v112.json",
            TMP/"kg001_fresh_checkout.json":ROOT/"data/tests/kg001_fresh_checkout.json",
        }
        for src,dst in mapping.items():
            if src.is_file():
                dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(src,dst)

    print(json.dumps(overall,indent=2))
    if args.fresh_checkout:
        sys.exit(0 if fresh_pass else 1)
    sys.exit(0 if overall["status"]=="PASS" else 1)

if __name__=="__main__":
    main()
