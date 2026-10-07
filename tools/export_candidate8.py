#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,time
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
  # Exported project executables do not provide the editor's --script override.
  # Validate packaged startup as a real process-health smoke; detailed runtime
  # scenarios are already executed against this exact source/asset state before export.
  proc=subprocess.Popen([str(out)],cwd=R,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  time.sleep(5.0)
  alive=proc.poll() is None
  if alive:
   proc.terminate()
   try: proc.wait(timeout=3)
   except subprocess.TimeoutExpired:
    proc.kill(); proc.wait(timeout=3)
  if not alive:
   print(json.dumps({"status":"FAIL","reason":"PACKAGED_STARTUP_EARLY_EXIT","returncode":proc.returncode},indent=2)); return 1
  packaged={"startup_process_health":{"status":"PASS","alive_after_seconds":5}}
  print(json.dumps({"schema":"openazrael.kg001.candidate8_export","version":2,"status":"PASS","commit_sha":head,"godot_version":ver.stdout.strip(),"artifacts":{str(out.relative_to(R)):{"bytes":out.stat().st_size,"sha256":sha(out)},str(pck.relative_to(R)):{"bytes":pck.stat().st_size,"sha256":sha(pck)}},"packaged":packaged},indent=2)); return 0
 finally: ID.unlink(missing_ok=True)
if __name__=="__main__": sys.exit(main())
