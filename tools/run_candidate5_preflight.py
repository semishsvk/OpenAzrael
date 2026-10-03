#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/tests/kg001_candidate5_release_contract_v202.json"
OUT = ROOT / ".tmp/kg001/candidate5_preflight_receipt.json"

def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def resolve_demo_root(explicit):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.remaster_framework.source_registry import resolve_source
    return Path(explicit).expanduser().resolve() if explicit else resolve_source("demo")

def resolve_original_rexe(demo_root):
    matches = [p for p in demo_root.rglob("*") if p.is_file() and p.name.casefold() == "r.exe"]
    expected = "381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00"
    exact = [p for p in matches if sha256(p) == expected]
    if len(exact) != 1:
        raise RuntimeError(f"ORIGINAL_R_EXE_RESOLUTION_FAILED matches={len(matches)} exact={len(exact)}")
    return exact[0]

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
        payload = {"schema":"openazrael.kg001.candidate5_preflight","version":207,"status":"FAIL","build_allowed":False,"commit_sha":head(),"stage":"SOURCE_GATES","source":source_rows}
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2)); return 1
    try:
        demo_root = resolve_demo_root(args.demo_dir)
        rexe = resolve_original_rexe(demo_root)
    except Exception as exc:
        payload = {"schema":"openazrael.kg001.candidate5_preflight","version":206,"status":"BLOCKED","build_allowed":False,"commit_sha":head(),"stage":"ORIGINAL_R_EXE_REQUIRED","source":source_rows,"error":str(exc)}
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2)); return 2
    re_rows = []
    for gate in contract.get("asset_backed_re_gates", []):
        tool = gate["tool"]
        out_path = ROOT / ".tmp/kg001" / (Path(tool).stem + "_candidate5.json")
        q = run([sys.executable, tool, "--exe", str(rexe), "--out", str(out_path)])
        re_rows.append({"tool":tool,"status":"PASS" if q.returncode == 0 else "FAIL","returncode":q.returncode,"r_exe_sha256":sha256(rexe),"receipt":str(out_path.relative_to(ROOT)),"receipt_sha256":sha256(out_path) if out_path.is_file() else None,"output_tail":q.stdout[-8000:]})
    if any(x["status"] != "PASS" for x in re_rows):
        payload = {"schema":"openazrael.kg001.candidate5_preflight","version":206,"status":"FAIL","build_allowed":False,"commit_sha":head(),"stage":"ASSET_BACKED_RE_GATES","source":source_rows,"asset_backed_re":re_rows}
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2)); return 1
    if not args.godot:
        payload = {"schema":"openazrael.kg001.candidate5_preflight","version":205,"status":"BLOCKED","build_allowed":False,"commit_sha":head(),"stage":"GODOT_RUNTIME_REQUIRED","source":source_rows,"asset_backed_re":re_rows}
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2)); return 2
    godot_probe = run([args.godot, "--version"])
    godot_version = godot_probe.stdout.strip()
    if godot_probe.returncode != 0 or not godot_version:
        payload = {"schema":"openazrael.kg001.candidate5_preflight","version":207,"status":"FAIL","build_allowed":False,"commit_sha":head(),"stage":"GODOT_VERSION_PROBE","source":source_rows,"asset_backed_re":re_rows,"godot_probe_returncode":godot_probe.returncode,"godot_probe_output_tail":godot_probe.stdout[-8000:]}
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2)); return 1
    runtime_rows = []
    for name, script in [
        ("SOURCE_FRAME_HEADLESS_V195", "res://tools/validate_kg001_source_frame_animation_v195.gd"),
        ("LEGACY_SCENE_UPDATE_CLOCK_HEADLESS_V198", "res://tools/validate_kg001_legacy_scene_update_clock_v198.gd"),
    ]:
        q = run([args.godot, "--headless", "--path", str(ROOT), "--script", script])
        ok = q.returncode == 0 and '"status":"PASS"' in q.stdout.replace(" ", "")
        runtime_rows.append({"name":name,"status":"PASS" if ok else "FAIL","returncode":q.returncode,"output_tail":q.stdout[-8000:]})
    if any(x["status"] != "PASS" for x in runtime_rows):
        payload = {"schema":"openazrael.kg001.candidate5_preflight","version":205,"status":"FAIL","build_allowed":False,"commit_sha":head(),"stage":"C5_HEADLESS_RUNTIME","source":source_rows,"asset_backed_re":re_rows,"runtime":runtime_rows}
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2)); return 1
    base = [sys.executable, "tools/run_candidate4_preflight.py", "--godot", args.godot]
    if args.demo_dir: base += ["--demo-dir", args.demo_dir]
    if args.soundfont: base += ["--soundfont", args.soundfont]
    if args.fluidsynth_lib: base += ["--fluidsynth-lib", args.fluidsynth_lib]
    inherited = run(base)
    v201 = run([sys.executable, "tools/validate_kg001_c4_runtime_evidence_v201.py"])
    c4_receipt = ROOT / ".tmp/kg001/candidate4_preflight_receipt.json"
    v201_receipt = ROOT / ".tmp/kg001_c4_closure/c4_runtime_evidence_v201.json"
    allowed = inherited.returncode == 0 and v201.returncode == 0 and c4_receipt.is_file() and v201_receipt.is_file()
    payload = {
        "schema":"openazrael.kg001.candidate5_preflight","version":205,
        "status":"PASS" if allowed else "BLOCKED","build_allowed":allowed,"commit_sha":head(),
        "source":source_rows,"asset_backed_re":re_rows,"c5_headless_runtime":runtime_rows,
        "godot_version":godot_version,
        "candidate4_preflight_returncode":inherited.returncode,"candidate4_preflight_output_tail":inherited.stdout[-12000:],
        "candidate4_preflight_receipt_sha256":sha256(c4_receipt) if c4_receipt.is_file() else None,
        "v201_returncode":v201.returncode,"v201_receipt_sha256":sha256(v201_receipt) if v201_receipt.is_file() else None,"v201_output_tail":v201.stdout[-12000:],
        "rule":"C5 build requires inherited C4 preflight plus exact-current-HEAD v201 runtime evidence."
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2)); return 0 if allowed else 2

if __name__ == "__main__":
    sys.exit(main())
