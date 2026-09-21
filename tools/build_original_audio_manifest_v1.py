#!/usr/bin/env python3
"""Generate source-safe import manifest from a locally restored original audio directory."""
import argparse, hashlib, json, wave
from pathlib import Path
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
 return h.hexdigest()
ap=argparse.ArgumentParser(); ap.add_argument("audio_dir",type=Path); ap.add_argument("--out",type=Path,required=True); a=ap.parse_args()
rows=[]
for p in sorted(a.audio_dir.rglob("*"),key=lambda x:x.as_posix().lower()):
 if not p.is_file() or p.suffix.lower()!=".wav": continue
 row={"name":p.name,"stem":p.stem.lower(),"sha256":sha(p),"bytes":p.stat().st_size}
 try:
  with wave.open(str(p),"rb") as w:
   row.update(channels=w.getnchannels(),sample_rate=w.getframerate(),frames=w.getnframes(),sample_width=w.getsampwidth())
 except Exception as e: row["wav_probe_error"]=type(e).__name__
 rows.append(row)
payload={"schema_version":1,"generator":"build_original_audio_manifest_v1.py","files":rows}
a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
print(f"wrote {a.out}: {len(rows)} WAV files")
