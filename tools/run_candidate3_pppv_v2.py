#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
TMP=ROOT/".tmp/kg001_pppv_v2"
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
    [sys.executable,"tools/validate_kg001_physical_traversal_v117.py"],
    [sys.executable,"tools/validate_kg001_well_tongs_animation_v118.py"],
]

RUNTIMES=[
    ("v109","scripts/kg001_headless_runner_v109.gd","OPENAZRAEL_KG001_V109"),
    ("v110","scripts/kg001_room_trigger_runner_v110.gd","OPENAZRAEL_KG001_V110"),
    ("v111","scripts/kg001_full_demo_runner_v111.gd","OPENAZRAEL_KG001_V111"),
    ("v117","scripts/kg001_physical_traversal_runner_v117.gd","OPENAZRAEL_KG001_PHYSICAL_V117"),
    ("v118","scripts/kg001_well_tongs_animation_runner_v118.gd","OPENAZRAEL_KG001_WELL_TONGS_V118"),
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

def sha256_file(path):
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()

def run_well_pppv(godot):
    scenario_root=TMP/"pppv_scenarios"
    bundle_path=TMP/"pppv_scenarios_preflight.json"
    materialize=run([
        sys.executable,
        "-m",
        "tools.openazrael_adapters.pppv",
        "--well-contract",str(ROOT/"data/tests/kg001_well_tongs_animation_contract_v118.json"),
        "--output",str(bundle_path),
        "--split-dir",str(scenario_root),
    ])
    if materialize.returncode!=0:
        return {
            "status":"FAIL",
            "materialization":"FAIL",
            "output":materialize.stdout[-12000:],
            "scenarios":{}
        }

    cases={
        "positive":scenario_root/"openazrael_r7_well_tongs_positive.json",
        "negative":scenario_root/"openazrael_r7_well_tongs_negative_without_tongs.json",
    }
    results={}
    all_pass=True
    for name,scenario_path in cases.items():
        runtime_path=TMP/f"pppv_well_{name}_runtime.json"
        evaluation_path=TMP/f"pppv_well_{name}_evaluation.json"
        proc=run([
            godot,
            "--headless",
            "--fixed-fps","60",
            "--path",str(ROOT),
            "--script","res://scripts/validation/pppv_scenario_runner.gd",
            "--",
            f"--pppv-scenario={scenario_path}",
            f"--pppv-output={runtime_path}",
        ])
        evaluation=None
        evaluator_returncode=None
        if runtime_path.is_file():
            evaluator=run([
                sys.executable,
                "-m",
                "tools.remaster_framework.evaluate_validation",
                "--runtime-bundle",str(runtime_path),
                "--output",str(evaluation_path),
            ])
            evaluator_returncode=evaluator.returncode
            if evaluation_path.is_file():
                try:
                    evaluation=json.loads(evaluation_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError,OSError):
                    evaluation=None
        status=(
            "PASS"
            if proc.returncode==0
            and evaluator_returncode==0
            and isinstance(evaluation,dict)
            and evaluation.get("status")=="PASS"
            else "FAIL"
        )
        if status!="PASS":
            all_pass=False
        results[name]={
            "status":status,
            "godot_returncode":proc.returncode,
            "evaluator_returncode":evaluator_returncode,
            "scenario":str(scenario_path.relative_to(ROOT)),
            "runtime":str(runtime_path.relative_to(ROOT)) if runtime_path.is_file() else "",
            "evaluation":evaluation or {},
            "output_tail":proc.stdout[-12000:],
        }

    summary={
        "schema":"openazrael.kg001.well_tongs_pppv",
        "version":1,
        "status":"PASS" if all_pass else "FAIL",
        "materialization":"PASS",
        "final_pppv_oracle":True,
        "scenarios":results,
    }
    write_json(TMP/"kg001_well_tongs_pppv.json",summary)
    return summary



def run_pppv_scenario_suite(godot):
    bundle_path=TMP/"pppv_scenarios.json"
    suite_root=TMP/"pppv_suite"
    scenario_root=suite_root/"scenarios"
    runtime_root=suite_root/"runtime"
    evaluation_root=suite_root/"evaluation"
    summary_path=TMP/"kg001_pppv_scenario_suite.json"

    if suite_root.exists():
        shutil.rmtree(suite_root)
    scenario_root.mkdir(parents=True,exist_ok=True)
    runtime_root.mkdir(parents=True,exist_ok=True)
    evaluation_root.mkdir(parents=True,exist_ok=True)

    if not bundle_path.is_file():
        summary={
            "schema":"openazrael.kg001.pppv_scenario_suite",
            "version":1,
            "status":"FAIL",
            "reason":"MISSING_PPPV_SCENARIO_BUNDLE",
            "scenario_count":0,
            "passed":0,
            "scenarios":{},
        }
        write_json(summary_path,summary)
        return summary

    try:
        bundle=json.loads(bundle_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError,OSError) as exc:
        summary={
            "schema":"openazrael.kg001.pppv_scenario_suite",
            "version":1,
            "status":"FAIL",
            "reason":"INVALID_PPPV_SCENARIO_BUNDLE",
            "error":str(exc),
            "scenario_count":0,
            "passed":0,
            "scenarios":{},
        }
        write_json(summary_path,summary)
        return summary

    rows=bundle.get("scenarios",[]) if isinstance(bundle,dict) else []
    bundle_sha256=sha256_file(bundle_path)
    if not isinstance(rows,list) or not rows:
        summary={
            "schema":"openazrael.kg001.pppv_scenario_suite",
            "version":1,
            "status":"FAIL",
            "reason":"EMPTY_PPPV_SCENARIO_BUNDLE",
            "scenario_count":0,
            "passed":0,
            "scenarios":{},
        }
        write_json(summary_path,summary)
        return summary

    v117_bridge_path=suite_root/"v117_pppv_bridge.json"
    v117_runtime_path=TMP/"kg001_v117_runtime.json"
    v117_contract_path=(
        ROOT/"data/tests/kg001_physical_traversal_contract_v117.json"
    )
    v117_bridge={}
    v117_rows={}
    if v117_runtime_path.is_file() and v117_contract_path.is_file():
        bridge_proc=run([
            sys.executable,
            "-m",
            "tools.openazrael_adapters.v117_pppv_bridge",
            "--runtime",str(v117_runtime_path),
            "--contract",str(v117_contract_path),
            "--output",str(v117_bridge_path),
        ])
        if v117_bridge_path.is_file():
            try:
                v117_bridge=json.loads(
                    v117_bridge_path.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError,OSError):
                v117_bridge={}
        if isinstance(v117_bridge,dict):
            v117_rows={
                str(row.get("scenario_id","")):row
                for row in v117_bridge.get("generic_scenarios",[])
                if isinstance(row,dict) and row.get("scenario_id")
            }

    results={}
    passed=0
    transition_ids=[]
    guarded_count=0
    v117_bridge_count=0
    for index,scenario in enumerate(rows):
        if not isinstance(scenario,dict):
            scenario_id=f"invalid_{index:03d}"
            results[scenario_id]={
                "status":"FAIL",
                "reason":"INVALID_SCENARIO_ROW",
            }
            continue

        scenario_id=str(scenario.get("scenario_id","")).strip()
        if not scenario_id:
            scenario_id=f"unnamed_{index:03d}"

        bridge_row=v117_rows.get(scenario_id)
        if isinstance(bridge_row,dict):
            status=(
                "PASS"
                if v117_bridge.get("status")=="BRIDGE_PASS"
                and bridge_row.get("status")=="PASS"
                else "FAIL"
            )
            if status=="PASS":
                passed+=1
            v117_bridge_count+=1
            results[scenario_id]={
                "status":status,
                "execution_profile":"v117_real_geometry_input",
                "guarded_replay":False,
                "bridge_status":v117_bridge.get("status","UNKNOWN"),
                "bridge_report":bridge_row,
            }
            continue

        guarded_count+=1
        safe_id="".join(
            ch if ch.isalnum() or ch in "-_" else "_"
            for ch in scenario_id
        )
        scenario_path=scenario_root/f"{index:03d}_{safe_id}.json"
        runtime_path=runtime_root/f"{index:03d}_{safe_id}.json"
        evaluation_path=evaluation_root/f"{index:03d}_{safe_id}.json"
        write_json(scenario_path,scenario)

        if scenario_id.startswith("openazrael.transition."):
            transition_ids.append(scenario_id)

        proc=run([
            godot,
            "--headless",
            "--fixed-fps","60",
            "--path",str(ROOT),
            "--script","res://scripts/validation/pppv_scenario_runner.gd",
            "--",
            f"--pppv-scenario={scenario_path}",
            f"--pppv-output={runtime_path}",
        ])

        evaluation=None
        evaluator_returncode=None
        evaluator_output=""
        if runtime_path.is_file():
            evaluator=run([
                sys.executable,
                "-m",
                "tools.remaster_framework.evaluate_validation",
                "--runtime-bundle",str(runtime_path),
                "--output",str(evaluation_path),
            ])
            evaluator_returncode=evaluator.returncode
            evaluator_output=evaluator.stdout[-12000:]
            if evaluation_path.is_file():
                try:
                    evaluation=json.loads(
                        evaluation_path.read_text(encoding="utf-8")
                    )
                except (json.JSONDecodeError,OSError):
                    evaluation=None

        status=(
            "PASS"
            if proc.returncode==0
            and evaluator_returncode==0
            and isinstance(evaluation,dict)
            and evaluation.get("status")=="PASS"
            else "FAIL"
        )
        if status=="PASS":
            passed+=1
        results[scenario_id]={
            "status":status,
            "execution_profile":"guarded_generic_runtime",
            "guarded_replay":True,
            "scenario":str(scenario_path.relative_to(ROOT)),
            "godot_returncode":proc.returncode,
            "evaluator_returncode":evaluator_returncode,
            "runtime":(
                str(runtime_path.relative_to(ROOT))
                if runtime_path.is_file()
                else ""
            ),
            "evaluation":evaluation or {},
            "output_tail":proc.stdout[-12000:],
            "evaluator_output_tail":evaluator_output,
        }

    scenario_count=len(rows)
    all_pass=passed==scenario_count
    summary={
        "schema":"openazrael.kg001.pppv_scenario_suite",
        "version":1,
        "status":"PASS" if all_pass else "FAIL",
        "scenario_bundle":str(bundle_path.relative_to(ROOT)),
        "scenario_bundle_sha256":bundle_sha256,
        "scenario_count":scenario_count,
        "passed":passed,
        "failed":scenario_count-passed,
        "transition_scenario_count":len(transition_ids),
        "transition_scenario_ids":sorted(transition_ids),
        "guarded_scenario_count":guarded_count,
        "v117_bridge_scenario_count":v117_bridge_count,
        "all_authored_scenarios_executed":len(results)==scenario_count,
        "all_transition_scenarios_guarded":all(
            bool(results.get(scenario_id,{}).get("guarded_replay"))
            for scenario_id in transition_ids
        ),
        "aggregate_validation_oracle":True,
        "final_pppv_oracle":False,
        "guarded_replay_boundary":(
            "Puzzle, interaction and transition scenarios use guarded generic "
            "runtime replay. Physical floor/stair scenarios temporarily use "
            "the v117 real-geometry Input runner with explicit direct setup."
        ),
        "required_for_g04":True,
        "required_for_g05":True,
        "required_for_g09":True,
        "scenarios":results,
    }
    write_json(summary_path,summary)
    return summary

def _run_full_pppv_once(godot, runtime_path, evaluation_path):
    runtime_path.unlink(missing_ok=True)
    evaluation_path.unlink(missing_ok=True)

    proc=run([
        godot,
        "--headless",
        "--fixed-fps","60",
        "--path",str(ROOT),
        "--script","res://scripts/validation/pppv_playthrough_runner.gd",
        "--",
        f"--pppv-plan={TMP/'pppv_playthrough_plan.json'}",
        f"--pppv-scenarios={TMP/'pppv_scenarios.json'}",
        f"--pppv-output={runtime_path}",
    ])

    evaluation=None
    evaluator_returncode=None
    evaluator_output=""
    if runtime_path.is_file():
        evaluator=run([
            sys.executable,
            "-m",
            "tools.remaster_framework.evaluate_playthrough",
            "--runtime-bundle",str(runtime_path),
            "--output",str(evaluation_path),
        ])
        evaluator_returncode=evaluator.returncode
        evaluator_output=evaluator.stdout[-12000:]
        if evaluation_path.is_file():
            try:
                evaluation=json.loads(
                    evaluation_path.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError,OSError):
                evaluation=None

    status=(
        "PASS"
        if proc.returncode==0
        and evaluator_returncode==0
        and isinstance(evaluation,dict)
        and evaluation.get("status")=="PASS"
        else "FAIL"
    )
    return {
        "status":status,
        "godot_returncode":proc.returncode,
        "evaluator_returncode":evaluator_returncode,
        "runtime":(
            str(runtime_path.relative_to(ROOT))
            if runtime_path.is_file()
            else ""
        ),
        "evaluation_path":(
            str(evaluation_path.relative_to(ROOT))
            if evaluation_path.is_file()
            else ""
        ),
        "evaluation":evaluation or {},
        "output_tail":proc.stdout[-12000:],
        "evaluator_output_tail":evaluator_output,
    }


def run_full_pppv(godot, repeat_count=2):
    plan_path=TMP/"pppv_playthrough_plan.json"
    scenarios_path=TMP/"pppv_scenarios.json"
    missing=[
        str(path.relative_to(ROOT))
        for path in (plan_path,scenarios_path)
        if not path.is_file()
    ]
    if missing:
        return {
            "status":"FAIL",
            "reason":"MISSING_PPPV_PLAN_OR_SCENARIOS",
            "missing":missing,
            "evaluation":{},
            "determinism_status":"NOT_RUN",
        }

    repeats=max(1,int(repeat_count))
    runs=[]
    for index in range(repeats):
        if index==0:
            runtime_path=TMP/"kg001_pppv_playthrough.json"
            evaluation_path=TMP/"kg001_pppv_playthrough_evaluation.json"
        else:
            run_number=index+1
            runtime_path=TMP/f"kg001_pppv_playthrough_repeat{run_number}.json"
            evaluation_path=(
                TMP/f"kg001_pppv_playthrough_repeat{run_number}_evaluation.json"
            )
        run_result=_run_full_pppv_once(
            godot,
            runtime_path,
            evaluation_path,
        )
        run_result["run_number"]=index+1
        runs.append(run_result)

    all_runs_pass=all(row.get("status")=="PASS" for row in runs)
    fingerprints=[
        str(row.get("evaluation",{}).get("semantic_replay_sha256",""))
        for row in runs
    ]
    final_hashes=[
        str(row.get("evaluation",{}).get("final_state_sha256",""))
        for row in runs
    ]
    fingerprint_complete=all(bool(value) for value in fingerprints)
    final_hash_complete=all(bool(value) for value in final_hashes)
    deterministic=(
        repeats>=2
        and all_runs_pass
        and fingerprint_complete
        and final_hash_complete
        and len(set(fingerprints))==1
        and len(set(final_hashes))==1
    )
    determinism_status=(
        "PASS"
        if deterministic
        else ("NOT_RUN" if repeats<2 and all_runs_pass else "FAIL")
    )
    plan_payload=json.loads(plan_path.read_text(encoding="utf-8"))
    determinism={
        "schema":"openazrael.kg001.pppv_determinism",
        "version":1,
        "status":determinism_status,
        "plan_sha256":str(plan_payload.get("plan_sha256","")),
        "plan_document_sha256":sha256_file(plan_path),
        "scenario_bundle_sha256":sha256_file(scenarios_path),
        "repeat_count":repeats,
        "all_runs_pass":all_runs_pass,
        "semantic_replay_sha256":fingerprints,
        "final_state_sha256":final_hashes,
        "semantic_replay_match":(
            fingerprint_complete and len(set(fingerprints))==1
        ),
        "final_state_match":(
            final_hash_complete and len(set(final_hashes))==1
        ),
        "runs":[
            {
                "run_number":row.get("run_number"),
                "status":row.get("status"),
                "runtime":row.get("runtime",""),
                "evaluation_path":row.get("evaluation_path",""),
                "semantic_replay_sha256":row.get(
                    "evaluation",{}
                ).get("semantic_replay_sha256",""),
                "final_state_sha256":row.get(
                    "evaluation",{}
                ).get("final_state_sha256",""),
            }
            for row in runs
        ],
    }
    write_json(TMP/"kg001_pppv_determinism.json",determinism)

    primary=runs[0] if runs else {}
    status=(
        "PASS"
        if all_runs_pass and determinism_status=="PASS"
        else "FAIL"
    )
    return {
        **primary,
        "status":status,
        "repeat_count":repeats,
        "runs":runs,
        "determinism_status":determinism_status,
        "determinism":determinism,
        "final_pppv_oracle":status=="PASS",
        "required_for_g08":True,
        "required_for_g09":True,
    }


def write_pppv_failure_reproducer(suite_summary, playthrough_summary):
    path=TMP/"kg001_pppv_failure_reproducer.json"
    failure=None

    if isinstance(suite_summary,dict) and suite_summary.get("status")=="FAIL":
        scenarios=suite_summary.get("scenarios",{})
        if isinstance(scenarios,dict):
            for scenario_id,row in scenarios.items():
                if not isinstance(row,dict) or row.get("status")=="PASS":
                    continue
                failure={
                    "kind":"isolated_scenario",
                    "scenario_id":scenario_id,
                    "scenario":row.get("scenario",""),
                    "runtime":row.get("runtime",""),
                    "evaluation":row.get("evaluation",{}),
                    "godot_returncode":row.get("godot_returncode"),
                    "evaluator_returncode":row.get("evaluator_returncode"),
                    "output_tail":row.get("output_tail",""),
                    "evaluator_output_tail":row.get("evaluator_output_tail",""),
                }
                execution_profile=row.get("execution_profile","")
                failure["execution_profile"]=execution_profile
                scenario_path=row.get("scenario","")
                if execution_profile=="v117_real_geometry_input":
                    failure["rerun"]=[
                        "<godot>",
                        "--headless",
                        "--path",".",
                        "--script",
                        "res://scripts/kg001_physical_traversal_runner_v117.gd",
                    ]
                    failure["bridge_report"]=row.get("bridge_report",{})
                elif scenario_path:
                    failure["rerun"]=[
                        "<godot>",
                        "--headless",
                        "--path",".",
                        "--script","res://scripts/validation/pppv_scenario_runner.gd",
                        "--",
                        f"--pppv-scenario={scenario_path}",
                        "--pppv-output=.tmp/kg001/reproducer_runtime.json",
                    ]
                break

    if failure is None and isinstance(playthrough_summary,dict) and playthrough_summary.get("status")=="FAIL":
        evaluation=playthrough_summary.get("evaluation",{})
        failed_step=None
        if isinstance(evaluation,dict):
            for row in evaluation.get("steps",[]):
                if isinstance(row,dict) and row.get("status")!="PASS":
                    failed_step=row
                    break
        determinism=playthrough_summary.get("determinism",{})
        determinism_failed=(
            playthrough_summary.get("determinism_status")=="FAIL"
        )
        failure={
            "kind":(
                "chained_playthrough_determinism"
                if determinism_failed and failed_step is None
                else "chained_playthrough"
            ),
            "failed_step":failed_step,
            "runtime":playthrough_summary.get("runtime",""),
            "evaluation":evaluation if isinstance(evaluation,dict) else {},
            "determinism":(
                determinism if isinstance(determinism,dict) else {}
            ),
            "godot_returncode":playthrough_summary.get("godot_returncode"),
            "evaluator_returncode":playthrough_summary.get("evaluator_returncode"),
            "output_tail":playthrough_summary.get("output_tail",""),
            "evaluator_output_tail":playthrough_summary.get("evaluator_output_tail",""),
            "rerun":[
                "<godot>",
                "--headless",
                "--path",".",
                "--script","res://scripts/validation/pppv_playthrough_runner.gd",
                "--",
                "--pppv-plan=.tmp/kg001/pppv_playthrough_plan.json",
                "--pppv-scenarios=.tmp/kg001/pppv_scenarios.json",
                "--pppv-output=.tmp/kg001/reproducer_playthrough.json",
            ],
        }
        if determinism_failed:
            failure["rerun_note"]=(
                "Run the chained playthrough at least twice and compare "
                "semantic_replay_sha256 plus final_state_sha256."
            )

    if failure is None:
        path.unlink(missing_ok=True)
        return None

    payload={
        "schema":"openazrael.kg001.pppv_failure_reproducer",
        "version":1,
        "status":"READY",
        "commit_sha":git_head(),
        "failure":failure,
    }
    write_json(path,payload)
    return payload


def main():
    ap=argparse.ArgumentParser(description="Run Candidate 3 PPPV v2 supplemental runtime verification.")
    ap.add_argument("--godot",help="Godot executable path/name. Otherwise GODOT_BIN, godot4, godot are tried.")
    ap.add_argument("--fresh-checkout",action="store_true",help="Require clean Git state plus v109/v110/v111/v117/v118, full guarded PPPV scenario suite, and chained PPPV playthrough PASS.")
    ap.add_argument("--promote-results",action="store_true",help="Do not use for Candidate 3 promotion; this supplemental runner keeps evidence in .tmp/kg001_pppv_v2.")
    ap.add_argument("--stage-framework-metadata",action="store_true",help="After G09 observation, stage ignored source-safe provenance/release/PPPV metadata under data/runtime for a subsequent manual Candidate/F11 run.")
    args=ap.parse_args()

    TMP.mkdir(parents=True,exist_ok=True)
    for stale_name in (
        "kg001_pppv_scenario_suite.json",
        "kg001_pppv_playthrough.json",
        "kg001_pppv_playthrough_evaluation.json",
        "kg001_pppv_playthrough_repeat2.json",
        "kg001_pppv_playthrough_repeat2_evaluation.json",
        "kg001_pppv_determinism.json",
        "kg001_pppv_failure_reproducer.json",
    ):
        (TMP/stale_name).unlink(missing_ok=True)
    shutil.rmtree(TMP/"pppv_suite",ignore_errors=True)
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
            if name in ("v110","v111","v117","v118") and not all(asset_present.values()):
                runtimes[name]={"status":"BLOCKED_MISSING_ASSETS","missing":[p for p,v in asset_present.items() if not v]}
                continue
            proc=run([godot,"--headless","--path",str(ROOT),"--script",f"res://{script}"])
            parsed=parse_marker(proc.stdout,marker)
            parsed["_process_returncode"]=proc.returncode
            parsed["_output_tail"]=proc.stdout[-12000:]
            runtimes[name]=parsed
            write_json(TMP/f"kg001_{name}_runtime.json",parsed)
        well_pppv_audio=ROOT/"assets/audio/979TONGS.WAV"
        if all(asset_present.values()) and well_pppv_audio.is_file():
            well_pppv=run_well_pppv(godot)
        else:
            missing=[
                path for path,present in asset_present.items() if not present
            ]
            if not well_pppv_audio.is_file():
                missing.append("assets/audio/979TONGS.WAV")
            well_pppv={
                "status":"BLOCKED_MISSING_ASSETS",
                "missing":missing,
                "final_pppv_oracle":True,
                "scenarios":{}
            }
            write_json(TMP/"kg001_well_tongs_pppv.json",well_pppv)
    else:
        for name,_,_ in RUNTIMES:
            runtimes[name]={"status":"BLOCKED_GODOT_NOT_FOUND"}
        well_pppv={
            "status":"BLOCKED_GODOT_NOT_FOUND",
            "final_pppv_oracle":True,
            "scenarios":{}
        }
        write_json(TMP/"kg001_well_tongs_pppv.json",well_pppv)

    clean_after=git_clean()
    legacy_runtime_pass=all(
        runtimes.get(name,{}).get("status")=="PASS"
        for name,_,_ in RUNTIMES
    )
    fresh_pass=(
        args.fresh_checkout and clean_before and clean_after and not bad_tracked and source_ok
        and godot is not None and import_status=="PASS" and legacy_runtime_pass
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
        "runtime_status":{k:v.get("status","") for k,v in runtimes.items()},
        "supplemental_runtime_status":{
            "well_tongs_real_input_pppv":well_pppv.get("status","")
        }
    }
    write_json(TMP/"kg001_source_validation_v112.json",{"status":"PASS" if source_ok else "FAIL","commands":source})
    write_json(TMP/"kg001_fresh_checkout.json",fresh)

    overall={
        "schema":"openazrael.kg001.candidate_run",
        "version":112,
        "status":"PASS" if source_ok and legacy_runtime_pass and (not args.fresh_checkout or fresh_pass) else "INCOMPLETE_OR_FAIL",
        "commit_sha":head,
        "godot_version":godot_version,
        "godot_import_status":import_status,
        "source_validators":"PASS" if source_ok else "FAIL",
        "runtimes":{k:v.get("status","") for k,v in runtimes.items()},
        "supplemental_runtimes":{
            "well_tongs_real_input_pppv":well_pppv.get("status","")
        },
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

    if (
        framework_status=="PASS"
        and godot is not None
        and import_status=="PASS"
        and all(asset_present.values())
    ):
        pppv_scenario_suite=run_pppv_scenario_suite(godot)
        pppv_playthrough=run_full_pppv(godot)
    else:
        if godot is None:
            block_status="BLOCKED_GODOT_NOT_FOUND"
            block_details={}
        elif not all(asset_present.values()):
            block_status="BLOCKED_MISSING_ASSETS"
            block_details={
                "missing":[p for p,v in asset_present.items() if not v]
            }
        elif import_status!="PASS":
            block_status="BLOCKED_GODOT_IMPORT"
            block_details={"import_status":import_status}
        else:
            block_status="BLOCKED_FRAMEWORK_PREFLIGHT"
            block_details={"framework_status":framework_status}

        pppv_scenario_suite={
            "status":block_status,
            **block_details,
            "aggregate_validation_oracle":False,
            "final_pppv_oracle":False,
            "required_for_g04":True,
            "required_for_g05":True,
            "required_for_g09":True,
            "scenarios":{},
        }
        write_json(
            TMP/"kg001_pppv_scenario_suite.json",
            pppv_scenario_suite,
        )
        pppv_playthrough={
            "status":block_status,
            **block_details,
            "final_pppv_oracle":False,
            "required_for_g08":True,
            "required_for_g09":True,
        }

    pppv_scenario_suite_pass=(
        pppv_scenario_suite.get("status")=="PASS"
    )
    pppv_playthrough_pass=pppv_playthrough.get("status")=="PASS"
    identity_path=TMP/"c4_current_head_pppv_identity.json"
    identity_path.unlink(missing_ok=True)
    eval_path=TMP/"kg001_pppv_playthrough_evaluation.json"
    det_path=TMP/"kg001_pppv_determinism.json"
    if pppv_playthrough_pass and pppv_playthrough.get("determinism_status")=="PASS" and eval_path.is_file() and det_path.is_file():
        write_json(identity_path,{
            "schema":"openazrael.kg001.current_head_pppv_identity","version":201,"status":"PASS",
            "commit_sha":head,"godot_version":godot_version,
            "pppv_evaluation_sha256":sha256_file(eval_path),
            "pppv_determinism_sha256":sha256_file(det_path),
            "transition_scenario_count":pppv_scenario_suite.get("transition_scenario_count"),
            "fresh_checkout_requested":bool(args.fresh_checkout),
        })
    pppv_failure_reproducer=write_pppv_failure_reproducer(
        pppv_scenario_suite,
        pppv_playthrough,
    )
    full_runtime_pass=(
        legacy_runtime_pass
        and pppv_scenario_suite_pass
        and pppv_playthrough_pass
    )

    clean_after=git_clean()
    fresh_pass=(
        args.fresh_checkout
        and clean_before
        and clean_after
        and not bad_tracked
        and source_ok
        and godot is not None
        and import_status=="PASS"
        and full_runtime_pass
        and all(asset_present.values())
        and all(asset_ignored.values())
    )
    fresh["status"]=(
        "PASS"
        if fresh_pass
        else ("NOT_REQUESTED" if not args.fresh_checkout else "FAIL")
    )
    fresh["clean_after"]=clean_after
    fresh["runtime_status"]["pppv_scenario_suite"]=pppv_scenario_suite.get(
        "status",""
    )
    fresh["runtime_status"]["pppv_playthrough"]=pppv_playthrough.get(
        "status",""
    )
    fresh["required_pppv_scenario_suite"]=pppv_scenario_suite
    fresh["required_pppv_playthrough"]=pppv_playthrough
    write_json(TMP/"kg001_fresh_checkout.json",fresh)

    overall["status"]=(
        "PASS"
        if source_ok
        and full_runtime_pass
        and (not args.fresh_checkout or fresh_pass)
        else "INCOMPLETE_OR_FAIL"
    )
    overall["runtimes"]["pppv_scenario_suite"]=pppv_scenario_suite.get(
        "status",""
    )
    overall["runtimes"]["pppv_playthrough"]=pppv_playthrough.get("status","")
    overall["required_pppv_scenario_suite"]=pppv_scenario_suite
    overall["required_pppv_playthrough"]=pppv_playthrough
    if pppv_failure_reproducer is not None:
        overall["pppv_failure_reproducer"]="kg001_pppv_failure_reproducer.json"
    write_json(TMP/"kg001_candidate_v112.json",overall)

    # Rebuild the framework bundle after the real-input chained PPPV runtime
    # exists so release gates and provenance bind to the evaluated evidence.
    framework_proc=run(framework_cmd)
    framework_status=(
        "PASS"
        if framework_proc.returncode==0 and framework_bundle_path.is_file()
        else "FAIL"
    )

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
            TMP/"kg001_v117_runtime.json":ROOT/"data/tests/kg001_physical_traversal_runtime_v117.json",
            TMP/"kg001_v118_runtime.json":ROOT/"data/tests/kg001_well_tongs_animation_runtime_v118.json",
            TMP/"kg001_well_tongs_pppv.json":ROOT/"data/tests/kg001_well_tongs_pppv.json",
            TMP/"kg001_pppv_scenario_suite.json":ROOT/"data/tests/kg001_pppv_scenario_suite.json",
            TMP/"kg001_pppv_playthrough.json":ROOT/"data/tests/kg001_pppv_playthrough.json",
            TMP/"kg001_pppv_playthrough_evaluation.json":ROOT/"data/tests/kg001_pppv_playthrough_evaluation.json",
            TMP/"kg001_pppv_playthrough_repeat2.json":ROOT/"data/tests/kg001_pppv_playthrough_repeat2.json",
            TMP/"kg001_pppv_playthrough_repeat2_evaluation.json":ROOT/"data/tests/kg001_pppv_playthrough_repeat2_evaluation.json",
            TMP/"kg001_pppv_determinism.json":ROOT/"data/tests/kg001_pppv_determinism.json",
            TMP/"pppv_scenario_suite_integrity.json":ROOT/"data/tests/pppv_scenario_suite_integrity.json",
            TMP/"pppv_determinism_integrity.json":ROOT/"data/tests/pppv_determinism_integrity.json",
            TMP/"kg001_pppv_failure_reproducer.json":ROOT/"data/tests/kg001_pppv_failure_reproducer.json",
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
