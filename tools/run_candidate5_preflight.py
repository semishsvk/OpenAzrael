#!/usr/bin/env python3
from pathlib import Path
import argparse, json, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/tests/kg001_candidate5_release_contract_v202.json"
OUT = ROOT / ".tmp/kg001/candidate5_preflight_receipt.json"

def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

def head():
    return run(["git", "rev-parse", "HEAD"]).stdout.strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--godot")
    ap.add_argument("--demo-dir")
    ap.add_argument("--soundfont")
    ap.add_argument("--fluidsynth-lib")
    args = ap.parse_args()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.unlink(missing_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    source_rows = []
    for tool in ["tools/validate_candidate5_release_contract_v202.py", *contract["additional_source_gates"]]:
        p = run([sys.executable, tool])
        source_rows.append({"tool": tool, "returncode": p.returncode, "status": "PASS" if p.returncode == 0 else "FAIL", "output_tail": p.stdout[-8000:]})
    if any(x["status"] != "PASS" for x in source_rows):
        payload = {"schema":"openazrael.kg001.candidate5_preflight","version":205,"status":"FAIL","build_allowed":False,"commit_sha":head(),"stage":"SOURCE_GATES","source":source_rows}
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2)); return 1
    if not args.godot:
        payload = {"schema":"openazrael.kg001.candidate5_preflight","version":205,"status":"BLOCKED","build_allowed":False,"commit_sha":head(),"stage":"GODOT_RUNTIME_REQUIRED","source":source_rows}
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2)); return 2
    runtime_rows = []
    for name, script in [
        ("SOURCE_FRAME_HEADLESS_V195", "res://tools/validate_kg001_source_frame_animation_v195.gd"),
        ("LEGACY_SCENE_UPDATE_CLOCK_HEADLESS_V198", "res://tools/validate_kg001_legacy_scene_update_clock_v198.gd"),
    ]:
        q = run([args.godot, "--headless", "--path", str(ROOT), "--script", script])
        ok = q.returncode == 0 and '"status":"PASS"' in q.stdout.replace(" ", "")
        runtime_rows.append({"name":name,"status":"PASS" if ok else "FAIL","returncode":q.returncode,"output_tail":q.stdout[-8000:]})
    if any(x["status"] != "PASS" for x in runtime_rows):
        payload = {"schema":"openazrael.kg001.candidate5_preflight","version":205,"status":"FAIL","build_allowed":False,"commit_sha":head(),"stage":"C5_HEADLESS_RUNTIME","source":source_rows,"runtime":runtime_rows}
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2)); return 1
    base = [sys.executable, "tools/run_candidate4_preflight.py", "--godot", args.godot]
    if args.demo_dir: base += ["--demo-dir", args.demo_dir]
    if args.soundfont: base += ["--soundfont", args.soundfont]
    if args.fluidsynth_lib: base += ["--fluidsynth-lib", args.fluidsynth_lib]
    inherited = run(base)
    v201 = run([sys.executable, "tools/validate_kg001_c4_runtime_evidence_v201.py"])
    allowed = inherited.returncode == 0 and v201.returncode == 0
    payload = {
        "schema":"openazrael.kg001.candidate5_preflight","version":205,
        "status":"PASS" if allowed else "BLOCKED","build_allowed":allowed,"commit_sha":head(),
        "source":source_rows,"c5_headless_runtime":runtime_rows,
        "candidate4_preflight_returncode":inherited.returncode,"candidate4_preflight_output_tail":inherited.stdout[-12000:],
        "v201_returncode":v201.returncode,"v201_output_tail":v201.stdout[-12000:],
        "rule":"C5 build requires inherited C4 preflight plus exact-current-HEAD v201 runtime evidence."
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2)); return 0 if allowed else 2

if __name__ == "__main__":
    sys.exit(main())
