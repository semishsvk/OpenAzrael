from pathlib import Path
import json,hashlib,sys
root=Path(__file__).resolve().parents[1]
src=Path(r"F:\OpenRemaster\sources\materialized\openazrael_demo_atdemo_v1\bf0c87f731bb4e87\layer2\ATDEMO")
manifest=json.loads((root/".tmp/kg001/candidate4_audio_restore_v132.json").read_text())
bad=[]; rows=[]
for rec in manifest["files"]:
 n=rec["filename"]; a=src/n; b=root/"assets/audio"/n
 ah=hashlib.sha256(a.read_bytes()).hexdigest() if a.is_file() else None
 bh=hashlib.sha256(b.read_bytes()).hexdigest() if b.is_file() else None
 ok=ah==rec["source_sha256"]==bh
 rows.append({"file":n,"ok":ok,"source":ah,"runtime":bh})
 if not ok: bad.append(n)
print(json.dumps({"schema":"openazrael.kg001.audio_source_exact","version":288,"status":"PASS" if not bad else "FAIL","count":len(rows),"failed":bad},indent=2))
sys.exit(1 if bad else 0)
