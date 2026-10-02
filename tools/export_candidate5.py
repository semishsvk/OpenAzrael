#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / ".tmp/kg001"
PREFLIGHT = TMP / "candidate5_preflight_receipt.json"
FREEZE = TMP / "candidate5_frozen_release_receipt.json"
IDENTITY = ROOT / "data/runtime_build_identity.json"

def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def marker(stdout, prefix):
    for line in reversed(stdout.splitlines()):
        if prefix in line:
            try:
                return json.loads(line.split(prefix, 1)[1].strip())
            except Exception:
                return {"status":"FAIL"}
    return {"status":"FAIL"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--godot", required=True)
    ap.add_argument("--out", default="exports/OpenAzrael-KG001-Candidate5.exe")
    args = ap.parse_args()
    if not PREFLIGHT.is_file() or not FREEZE.is_file():
        print('{"status":"FAIL","reason":"C5_PREFLIGHT_OR_FREEZE_MISSING"}'); return 1
    p = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    f = json.loads(FREEZE.read_text(encoding="utf-8"))
    head = run(["git","rev-parse","HEAD"]).stdout.strip()
    if p.get("status") != "PASS" or p.get("build_allowed") is not True or p.get("commit_sha") != head:
        print('{"status":"FAIL","reason":"C5_PREFLIGHT_NOT_BOUND_TO_HEAD"}'); return 1
    if f.get("status") != "PASS" or f.get("commit_sha") != head or f.get("preflight_receipt_sha256") != sha(PREFLIGHT):
        print('{"status":"FAIL","reason":"C5_FREEZE_NOT_BOUND_TO_PREFLIGHT"}'); return 1
    if run(["git","status","--porcelain","--untracked-files=normal"]).stdout.strip():
        print('{"status":"FAIL","reason":"DIRTY_GIT"}'); return 1
    identity = {"schema":"openazrael.runtime_build_identity","version":1,"candidate":"KG-001 Candidate 5","commit_sha":head,"preset":"Windows Candidate 5"}
    IDENTITY.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
    out = ROOT / args.out
    pck = out.with_suffix(".pck")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True); pck.unlink(missing_ok=True)
    exported = run([args.godot,"--headless","--path",str(ROOT),"--export-release","Windows Candidate 5",str(out)])
    errors = [x for x in exported.stdout.splitlines() if x.lstrip().startswith(("ERROR:","SCRIPT ERROR:"))]
    if exported.returncode or errors or not out.is_file() or not pck.is_file():
        IDENTITY.unlink(missing_ok=True)
        print(json.dumps({"status":"FAIL","reason":"EXPORT_FAILED","engine_errors":errors,"output_tail":exported.stdout[-12000:]}, indent=2)); return 1
    specs = [
        ("origin","res://scripts/kg001_candidate5_packaged_origin_runner_v203.gd","OPENAZRAEL_KG001_C5_PACKAGED_ORIGIN_V203"),
        ("parity","res://scripts/kg001_packaged_parity_runner_v128.gd","OPENAZRAEL_KG001_PACKAGED_PARITY_V128"),
        ("transitions","res://scripts/kg001_all_transition_runner_v141.gd","OPENAZRAEL_KG001_ALL_TRANSITIONS_V141"),
        ("cursor","res://scripts/kg001_interaction_cursor_runner_v143.gd","OPENAZRAEL_KG001_CURSOR_V143"),
        ("menu","res://scripts/kg001_legacy_menu_runner_v145.gd","OPENAZRAEL_KG001_MENU_V145"),
        ("inventory","res://scripts/kg001_inventory_hud_runner_v157.gd","OPENAZRAEL_KG001_INVENTORY_HUD_V157"),
    ]
    results = {}
    for name, script, prefix in specs:
        q = run([str(out),"--headless","--script",script])
        result = marker(q.stdout, prefix); results[name] = result
        if q.returncode or result.get("status") != "PASS":
            IDENTITY.unlink(missing_ok=True)
            print(json.dumps({"status":"FAIL","reason":"PACKAGED_RUNTIME_FAILED","test":name,"result":result,"output_tail":q.stdout[-12000:]}, indent=2)); return 1
    IDENTITY.unlink(missing_ok=True)
    payload = {
        "schema":"openazrael.kg001.candidate5_export","version":205,"status":"PASS","commit_sha":head,
        "preflight_receipt_sha256":sha(PREFLIGHT),"freeze_receipt_sha256":sha(FREEZE),
        "artifacts":{
            str(out.relative_to(ROOT)):{"bytes":out.stat().st_size,"sha256":sha(out)},
            str(pck.relative_to(ROOT)):{"bytes":pck.stat().st_size,"sha256":sha(pck)}
        },"packaged":results
    }
    print(json.dumps(payload, indent=2)); return 0

if __name__ == "__main__":
    sys.exit(main())
