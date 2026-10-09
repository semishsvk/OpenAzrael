#!/usr/bin/env python3
"""Bounded C8 R7 source+Godot regression; no release/fidelity promotion."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GODOT=Path(os.environ.get("OPENAZRAEL_GODOT_BIN",
    "F:/Remaster Framework/source/Godot/Godot_v4.7.2-stable_win64.exe"))
PY=Path(os.environ.get("OPENAZRAEL_PYTHON",sys.executable))
TESTS=[
 ("well_source_gate",[str(PY),"tools/run_well_source_gate_v347.py"],None),
 ("r7_axis_replay",[str(GODOT),"--headless","--path",str(ROOT),"--script","res://scripts/kg001_r7_source_axis_replay_runner_v361.gd"],"OPENAZRAEL_C8_AXIS_REPLAY_V361 "),
 ("r7_source_action_ir",[str(GODOT),"--headless","--path",str(ROOT),"--script","res://scripts/kg001_r7_source_action_ir_runner_v358.gd"],"OPENAZRAEL_C8_ACTION_IR_V358 "),
 ("r7_condition_branch",[str(GODOT),"--headless","--path",str(ROOT),"--script","res://scripts/kg001_r7_condition_branch_runner_v363.gd"],"OPENAZRAEL_C8_CONDITION_BRANCH_V363 "),
 ("r7_action_selector",[str(GODOT),"--headless","--path",str(ROOT),"--script","res://scripts/kg001_r7_source_selector_runner_v359.gd"],"OPENAZRAEL_C8_SELECTOR_V359 "),
 ("r7_activation_guard",[str(GODOT),"--headless","--path",str(ROOT),"--script","res://scripts/kg001_r7_activation_guard_runner_v360.gd"],"OPENAZRAEL_C8_ACTIVATION_GUARD_V360 "),
 ("r7_bridge_lifecycle",[str(GODOT),"--headless","--path",str(ROOT),"--script","res://scripts/kg001_r7_bridge_lifecycle_runner_v357.gd"],"OPENAZRAEL_C8_R7_BRIDGE_V357 "),
 ("r7_scheduler",[str(GODOT),"--headless","--path",str(ROOT),"--script","res://scripts/kg001_r7_scheduler_runner_v354.gd"],"OPENAZRAEL_C8_SCHEDULER "),
 ("r7_executor",[str(GODOT),"--headless","--path",str(ROOT),"--script","res://scripts/kg001_r7_transform_executor_runner_v355.gd"],"OPENAZRAEL_C8_EXECUTOR_V355 "),
 ("r7_bridge",[str(GODOT),"--headless","--path",str(ROOT),"--script","res://scripts/kg001_r7_bridge_runner_v356.gd"],"OPENAZRAEL_C8_BRIDGE_V356 "),
 ("r7_baseline",[str(GODOT),"--headless","--path",str(ROOT),"--script","res://scripts/kg001_r7_restore_baseline_v353.gd"],"OPENAZRAEL_C8_R7_BASELINE "),
 ("full_demo",[str(GODOT),"--headless","--path",str(ROOT),"--script","res://scripts/kg001_full_demo_runner_v111.gd"],"OPENAZRAEL_KG001_V111 "),
 ("save_compat",[str(GODOT),"--headless","--path",str(ROOT),"--script","res://scripts/kg001_save_compat_runner_v150.gd"],"OPENAZRAEL_KG001_SAVE_COMPAT_V150 "),
 ("static_transform",[str(GODOT),"--headless","--path",str(ROOT),"--script","res://scripts/kg001_transform_parity_runner_v125.gd"],"OPENAZRAEL_KG001_TRANSFORM_V125 ")
]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()
def run():
    configs={n:digest(ROOT/n) for n in ("project.godot","export_presets.cfg")}
    head=git("rev-parse","HEAD")
    entries=[]
    for name,cmd,marker in TESTS:
        start=time.monotonic()
        p=subprocess.run(cmd,cwd=ROOT,text=True,encoding="utf8",errors="replace",stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        result={}
        if marker:
            matches=[line.split(marker,1)[1] for line in p.stdout.splitlines() if marker in line]
            if matches:
                try:result=json.loads(matches[-1])
                except Exception:pass
            ok=p.returncode==0 and result.get("status")=="PASS" and not result.get("failed")
        else:
            matches=[line for line in p.stdout.splitlines() if '"status": "STRUCTURAL_PASS_FIDELITY_HOLD"' in line]
            ok=p.returncode==0 and bool(matches)
            result={"status":"STRUCTURAL_PASS_FIDELITY_HOLD"} if ok else {}
        entry={"name":name,"pass":ok,"exit":p.returncode,"time_s":round(time.monotonic()-start,2),"result":result,"output_tail":p.stdout[-700:]}
        entries.append(entry)
        print(json.dumps({"test":name,"pass":ok,"exit":p.returncode,"checks":result.get("checks"),"status":result.get("status")}),flush=True)
        if not ok:break
    after={n:digest(ROOT/n) for n in configs}
    report={"schema":"openazrael.c8.r7_test_campaign.v363","head":head,"godot":"4.7.2-stable","protected_configs_unchanged":configs==after,"source_contracts_passed":bool(entries and entries[0]["pass"]),"fidelity_pass":False,"status":"REGRESSION_PASS_FIDELITY_HOLD" if len(entries)==len(TESTS) and all(e["pass"] for e in entries) and configs==after else "FAIL","entries":entries}
    output=ROOT/".tmp/c8_r7_test_campaign_v363.json"
    output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"summary":report["status"],"passed":sum(e["pass"] for e in entries),"total":len(TESTS),"protected_unchanged":configs==after,"output":str(output)}))
    return 0 if report["status"]=="REGRESSION_PASS_FIDELITY_HOLD" else 1
if __name__=="__main__":sys.exit(run())