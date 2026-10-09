#!/usr/bin/env python3
"""Source-pinned original DOSBox-X navigation probes with branchable savestates.

All game data are used through an isolated guest copy; every input branch
has its own cloned DOSBox save file. Only emulator-native PNGs are evidence.
No gameplay-room conclusion is inferred from a scene change alone.
"""
from __future__ import annotations
from pathlib import Path
import ctypes,hashlib,json,os,shutil,struct,subprocess,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[1]
BASE=Path(os.environ.get("OPENAZRAEL_ORACLE_ROOT",r"F:\Remaster Framework\work\OpenAzrael\oracle\atdemo_dosboxx_v369"))
EXEC=Path(os.environ.get("OPENAZRAEL_DOSBOXX_EXE",r"F:\Remaster Framework\tools\third_party\dosbox-x\2026.10.01\unpacked\bin\x64\Release SDL2\dosbox-x.exe"))
CAPBASE=Path(os.environ.get("OPENAZRAEL_CAPTURE_ROOT",r"F:\OpenRemaster\captures\OpenAzrael_C8_20261009"))
ORIGINAL_EXE_SHA="381e4f5c61e4bb8c27f06b1944e6673bbebad568dd3dd01" # replaced by validated lookup below
DOSBOX_SHA="a82adcfa7af2784566cfeff74c077cefed08505396db2948b7e6aa7d4cee0832"
KNOWN_R_EXE="381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00"
KEYS={
 "UP":(0x26,0x48),"DOWN":(0x28,0x50),"LEFT":(0x25,0x4b),
 "RIGHT":(0x27,0x4d),"MAP":(0x4d,0x32),"HOME":(0x24,0x47),
 "X":(0x58,0x2d),"ENTER":(0x0d,0x1c),"ESC":(0x1b,0x01)
}
U=ctypes.windll.user32
U.SendMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t]
U.SendMessageW.restype=ctypes.c_ssize_t
U.GetWindowThreadProcessId.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
U.GetWindowThreadProcessId.restype=ctypes.c_ulong
U.GetClientRect.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
CB=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_long)
class RECT(ctypes.Structure):_fields_=[("left",ctypes.c_long),("top",ctypes.c_long),("right",ctypes.c_long),("bottom",ctypes.c_long)]
class POINT(ctypes.Structure):_fields_=[("x",ctypes.c_long),("y",ctypes.c_long)]
U.ClientToScreen.argtypes=[ctypes.c_void_p,ctypes.POINTER(POINT)]
U.ClientToScreen.restype=ctypes.c_int
U.GetCursorPos.argtypes=[ctypes.POINTER(POINT)]
U.GetCursorPos.restype=ctypes.c_int
U.SetCursorPos.argtypes=[ctypes.c_int,ctypes.c_int]
U.SetCursorPos.restype=ctypes.c_int
DPI_AWARE=bool(U.SetProcessDPIAware())  # Required to avoid 150%-scaled Win32 mouse coordinates.
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1048576),b""):h.update(c)
 return h.hexdigest()
def win_for_pid(pid):
 hits=[]
 def enum(hwnd,_):
  p=ctypes.c_ulong()
  U.GetWindowThreadProcessId(hwnd,ctypes.byref(p))
  if p.value==pid and U.IsWindowVisible(hwnd):hits.append(int(hwnd))
  return True
 cb=CB(enum);U.EnumWindows(cb,0)
 return hits[0] if hits else None
def run(plan):
 tag=str(plan.get("id",""))
 if not tag or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-." for c in tag):raise ValueError("unsafe tag")
 if len(plan.get("actions",[]))>30:raise ValueError("action limit")
 state=BASE/"states"/str(plan["start_state"])
 if not state.is_file() or state.suffix.lower()!=".sav":raise ValueError("input state unavailable")
 with zipfile.ZipFile(state) as z:
  if "Memory" not in z.namelist() or "CPU" not in z.namelist():raise ValueError("not an actual DOSBox-X state")
 state_sha=sha(state)
 assert sha(EXEC)==DOSBOX_SHA and sha(BASE/"drive_c/ATDEMO/R.EXE")==KNOWN_R_EXE
 folder=BASE/"nav_runs"/tag
 if folder.exists():raise ValueError("refuse to overwrite previous probe: "+str(folder))
 folder.mkdir(parents=True)
 cap=CAPBASE/("original_navigation_"+tag)
 cap.mkdir(parents=True,exist_ok=False)
 ownstate=folder/("NAV_"+tag+".sav")
 shutil.copy2(state,ownstate)
 assert sha(ownstate)==state_sha
 cfg=folder/("dosboxx_"+tag+".conf")
 cfg.write_text("[sdl]\nfullscreen=false\noutput=surface\nautolock=false\n"
 "[dosbox]\nmemsize=64\ncaptures="+str(cap)+"\nmachine=svga_s3\n"
 "savefile="+str(ownstate)+"\nsaveremark=false\nforceloadstate=false\n"
 "[cpu]\ncore=normal\ncycles=auto\n[mixer]\nnosound=false\n"
 "[autoexec]\n"+'mount c "'+str(BASE/"drive_c")+'"\n'
 "c:\ncd \\ATDEMO\nR.EXE\nexit\n",encoding="ascii")
 env=os.environ.copy()
 env["SDL_AUDIODRIVER"]="dummy";env.pop("SDL_VIDEODRIVER",None)
 stdout=folder/"emulator_stdout.log";stderr=folder/"emulator_stderr.log"
 events=[];start=time.monotonic()
 with stdout.open("w",encoding="utf8") as fout,stderr.open("w",encoding="utf8") as ferr:
  original_mouse=POINT()
  U.GetCursorPos(ctypes.byref(original_mouse))
  proc=subprocess.Popen([str(EXEC),"-conf",str(cfg),"-exit"],cwd=EXEC.parent,env=env,stdout=fout,stderr=ferr)
  try:
   time.sleep(2.4)
   h=win_for_pid(proc.pid)
   if not h:raise RuntimeError("DOSBox-X real host window missing")
   U.SendMessageW(h,0x111,5205,0)
   time.sleep(.65)
   if "Loaded. (Slot 1)" not in stderr.read_text(encoding="utf8",errors="replace"):
    raise RuntimeError("DOSBox-X did not authenticate native saved-state load")
   def snap(label):
    if not label or len(label)>100:return
    before=set(f.name for f in cap.glob("*.png"))
    U.SendMessageW(h,0x111,5220,0)
    time.sleep(.24)
    added=[f for f in cap.glob("*.png") if f.name not in before]
    if len(added)!=1:raise RuntimeError("native screenshot not saved: "+label)
    img=added[0]
    header=img.read_bytes()[:24]
    if header[:8]!=b"\x89PNG\r\n\x1a\n" or struct.unpack_from(">II",header,16)!=(640,480):
     raise RuntimeError("bad native original 640x480 screenshot: "+label)
    events.append({"action":"CAPTURE","label":label,"t":round(time.monotonic()-start,3),
         "file":str(img),"sha256":sha(img),"bytes":img.stat().st_size})
   snap("BASELINE_AFTER_NATIVE_STATE_LOAD")
   for item in plan["actions"]:
    kind=item["type"]
    if kind=="key":
     key=str(item["key"]).upper()
     if key not in KEYS:raise RuntimeError("unsupported key "+key)
     secs=float(item.get("seconds",.12))
     if not .04<=secs<=8:raise RuntimeError("hold outside bounded range")
     U.ShowWindow(h,9);U.SetForegroundWindow(h)
     time.sleep(.10)
     foreground=(U.GetForegroundWindow()==h)
     vk,scan=KEYS[key]
     U.keybd_event(vk,scan,1,0)
     time.sleep(secs)
     U.keybd_event(vk,scan,3,0)
     events.append({"action":"KEY","key":key,"seconds":secs,"foreground":foreground,"t":round(time.monotonic()-start,3)})
     if not foreground:raise RuntimeError("game was not foreground during input")
    elif kind=="pointer":
     x=int(item["x"]);y=int(item["y"])
     if not 0<=x<640 or not 0<=y<480:
      raise ValueError("unsafe native pointer coordinates")
     client=RECT();origin=POINT()
     U.GetClientRect(h,ctypes.byref(client))
     width=client.right-client.left;height=client.bottom-client.top
     assert width>0 and height>0 and U.ClientToScreen(h,ctypes.byref(origin))
     to_x=origin.x+round(x*width/640)
     to_y=origin.y+round(y*height/480)
     result=U.SetCursorPos(to_x,to_y)
     time.sleep(.4)
     actual=POINT();U.GetCursorPos(ctypes.byref(actual))
     events.append({"action":"NATIVE_POINTER",
       "requested_game_pixels":[x,y],"dpi_aware":DPI_AWARE,
       "client_pixels":[width,height],"screen_origin":[origin.x,origin.y],
       "sent_screen":[to_x,to_y],
       "actual_screen":[actual.x,actual.y],"set_cursor_result":bool(result),
       "t":round(time.monotonic()-start,3)})
    elif kind=="hover":
     x=int(item["x"]);y=int(item["y"])
     if not 0<=x<640 or not 0<=y<480:raise ValueError("unsafe hover coordinates")
     rc=RECT()
     U.GetClientRect(h,ctypes.byref(rc))
     width=rc.right-rc.left;height=rc.bottom-rc.top
     client_x=int(x*width/640);client_y=int(y*height/480)
     lp=(client_y<<16)|(client_x&0xffff)
     U.SendMessageW(h,0x200,0,lp)
     time.sleep(.28)
     events.append({"action":"HOVER","requested_native":[x,y],
                    "window_client":[width,height],
                    "sent_client":[client_x,client_y],"t":round(time.monotonic()-start,3)})
    elif kind=="click":
     x=int(item["x"]);y=int(item["y"])
     if not 0<=x<640 or not 0<=y<480:raise ValueError("unsafe click coordinates")
     rc=RECT()
     U.GetClientRect(h,ctypes.byref(rc))
     width=rc.right-rc.left;height=rc.bottom-rc.top
     lp=(int(y*height/480)<<16)|int(x*width/640)
     U.SendMessageW(h,0x200,0,lp)
     time.sleep(.15)
     U.SendMessageW(h,0x201,1,lp)
     time.sleep(.16)
     U.SendMessageW(h,0x202,0,lp)
     events.append({"action":"CLICK","screen":[x,y],"t":round(time.monotonic()-start,3)})
    elif kind=="pause":
     secs=float(item["seconds"])
     if not 0<=secs<=5:raise ValueError("unbounded pause")
     time.sleep(secs)
    elif kind=="capture":
     snap(str(item["label"]))
    else:raise ValueError("unsupported action "+str(kind))
   if plan.get("save_at_end"):
    U.SendMessageW(h,0x111,5204,0)
    deadline=time.monotonic()+14.0
    saved=False
    while time.monotonic()<deadline and proc.poll() is None:
     time.sleep(.20)
     if "Saved. (Slot 1)" not in stderr.read_text(encoding="utf8",errors="replace"):
      continue
     if not zipfile.is_zipfile(ownstate):
      continue
     try:
      with zipfile.ZipFile(ownstate) as archive:
       saved=(archive.testzip() is None
        and "CPU" in archive.namelist() and "Memory" in archive.namelist())
     except (OSError,zipfile.BadZipFile):
      saved=False
     if saved:break
    if not saved:
     raise RuntimeError("native save did not complete as a valid ZIP; incomplete output MUST NOT be reused")
    events.append({"action":"SAVE_STATE","saved_sha256":sha(ownstate),
                   "native_log_confirmed":True,"zip_crc_verified":True,
                   "save_validation_wait_seconds":round(14.0-max(0,deadline-time.monotonic()),2)})
  finally:
   if proc.poll() is None:
    proc.terminate()
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:proc.kill();proc.wait()
   U.SetCursorPos(original_mouse.x,original_mouse.y)
 if sha(state)!=state_sha:raise RuntimeError("original nav branch input changed")
 report={"schema":"openazrael.original_emulator_navigation.v399","status":"NATIVE_INPUT_AND_CAPTURE_PASS",
   "branch_id":tag,"source_state":str(state),"source_state_sha256":state_sha,
   "output_state":str(ownstate),"output_state_sha256":sha(ownstate),
   "source_exe_sha256":KNOWN_R_EXE,"emulator_binary_sha256":DOSBOX_SHA,
   "original_source_unchanged":True,
   "actions":events,"r7_room_confirmed":False,
   "scope":"original emulator with native framebuffer capture, gameplay location classification separate"}
 (folder/"NAV_REPORT.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
 print("OPENAZRAEL_ORIGINAL_NAV_V385 "+json.dumps(report),flush=True)
 return 0
if __name__=="__main__":
 try:
  plan=json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))
  sys.exit(run(plan))
 except Exception as ex:
  try:
   name=str(plan.get("id",""))
   folder=BASE/"nav_runs"/name
   if folder.is_dir():
    (folder/"INVALID_OR_BLOCKED_RUN.txt").write_text(
      "Navigation/restore failed; DO NOT use output save as fidelity evidence. Reason: "+str(ex)+"\n",encoding="utf8")
  except Exception:
   pass
  print(json.dumps({"status":"FAIL","reason":str(ex)}),flush=True)
  sys.exit(1)
