#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
R=Path(__file__).resolve().parents[1]; ID=R/"data/runtime_build_identity.json"
def run(c): return subprocess.run(c,cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""): h.update(b)
 return h.hexdigest()
def marker(s,p):
 for line in reversed(s.splitlines()):
  if p in line:
   try:return json.loads(line.split(p,1)[1].strip())
   except Exception:return {"status":"FAIL"}
 return {"status":"FAIL"}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--godot",required=True); ap.add_argument("--out",default="exports/OpenAzrael-KG001-Candidate8.exe"); a=ap.parse_args()
 head=run(["git","rev-parse","HEAD"]).stdout.strip()
 if run(["git","status","--porcelain","--untracked-files=normal"]).stdout.strip():
  print(json.dumps({"status":"FAIL","reason":"DIRTY_GIT"})); return 1
 ver=run([a.godot,"--version"])
 if ver.returncode: print(json.dumps({"status":"FAIL","reason":"GODOT_UNAVAILABLE"})); return 1
 identity={"schema":"openazrael.runtime_build_identity","version":1,"candidate":"KG-001 Candidate 8","commit_sha":head,"godot_version":ver.stdout.strip(),"preset":"Windows Candidate 8"}
 ID.write_text(json.dumps(identity,indent=2)+"\n",encoding="utf-8")
 out=R/a.out; pck=out.with_suffix(".pck"); out.parent.mkdir(parents=True,exist_ok=True); out.unlink(missing_ok=True); pck.unlink(missing_ok=True)
 try:
  q=run([a.godot,"--headless","--path",str(R),"--export-release","Windows Candidate 8",str(out)])
  errors=[x for x in q.stdout.splitlines() if x.lstrip().startswith(("ERROR:","SCRIPT ERROR:"))]
  if q.returncode or errors or not out.is_file() or not pck.is_file():
   print(json.dumps({"status":"FAIL","reason":"EXPORT_FAILED","errors":errors,"tail":q.stdout[-12000:]},indent=2)); return 1
  smoke=run([str(out),"--headless","--quit-after","120"])
  serr=[x for x in smoke.stdout.splitlines() if x.lstrip().startswith(("ERROR:","SCRIPT ERROR:"))]
  if smoke.returncode or serr:
   print(json.dumps({"status":"FAIL","reason":"STARTUP_SMOKE_FAILED","errors":serr,"tail":smoke.stdout[-12000:]},indent=2)); return 1
  specs=[
   ("transitions","res://scripts/kg001_all_transition_runner_v141.gd","OPENAZRAEL_KG001_ALL_TRANSITIONS_V141"),
   ("cursor","res://scripts/kg001_interaction_cursor_runner_v143.gd","OPENAZRAEL_KG001_CURSOR_V143"),
   ("menu","res://scripts/kg001_legacy_menu_runner_v145.gd","OPENAZRAEL_KG001_MENU_V145"),
   ("menu_cursor","res://scripts/kg001_menu_cursor_context_runner_v146.gd","OPENAZRAEL_KG001_MENU_CURSOR_V146"),
   ("inventory","res://scripts/kg001_inventory_hud_runner_v157.gd","OPENAZRAEL_KG001_INVENTORY_HUD_V157"),
   ("parchment","res://scripts/kg001_parchment_fullscreen_runner_v255.gd","OPENAZRAEL_PARCHMENT_FULLSCREEN_V255")]
  results={}
  for n,s,m in specs:
   x=run([str(out),"--headless","--script",s]); z=marker(x.stdout,m); results[n]=z
   if x.returncode or z.get("status")!="PASS":
    print(json.dumps({"status":"FAIL","reason":"PACKAGED_RUNTIME_FAILED","test":n,"result":z,"tail":x.stdout[-12000:]},indent=2)); return 1
  print(json.dumps({"schema":"openazrael.kg001.candidate8_export","version":1,"status":"PASS","commit_sha":head,"godot_version":ver.stdout.strip(),"artifacts":{str(out.relative_to(R)):{"bytes":out.stat().st_size,"sha256":sha(out)},str(pck.relative_to(R)):{"bytes":pck.stat().st_size,"sha256":sha(pck)}},"packaged":results},indent=2)); return 0
 finally: ID.unlink(missing_ok=True)
if __name__=="__main__": sys.exit(main())
