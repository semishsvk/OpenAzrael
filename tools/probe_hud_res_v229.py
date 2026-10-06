#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import hashlib,json,collections
DEMO=Path(r"F:\OpenRemaster\sources\materialized\openazrael_demo_atdemo_v1\bf0c87f731bb4e87\layer2\ATDEMO")
OUT=Path("data/runtime_generated/hud_res_probe_v229.json")
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def probe(name):
 p=DEMO/name; b=p.read_bytes()
 pairs=[(b[i],b[i+1]) for i in range(0,len(b)-1,2)]
 return {"file":name,"bytes":len(b),"sha256":sha(p),"head_hex":b[:64].hex(),
  "byte_histogram":collections.Counter(b).most_common(16),
  "u16le_head":[int.from_bytes(b[i:i+2],"little") for i in range(0,min(64,len(b)-1),2)],
  "pair_histogram":collections.Counter(pairs).most_common(12)}
hud=Image.open(DEMO/"HUD3.PCX")
payload={"schema":"openazrael.kg001.hud_res_probe","version":229,
 "blocker":"original conversation/HUD compositing unknown",
 "hypothesis":"HUDTOP.RES/HUDBOT.RES are custom raster/overlay streams composited with HUD3.PCX",
 "expected_unlock":"source-authentic Niamh conversation frame/layout",
 "authority":"CORPUS_AUTHORITY",
 "reference":{"file":"HUD3.PCX","size":list(hud.size),"mode":hud.mode,"sha256":sha(DEMO/"HUD3.PCX")},
 "resources":[probe("HUDTOP.RES"),probe("HUDBOT.RES")],
 "status":"STRUCTURAL_FORMAT_PROBE_ONLY_NOT_PIXEL_VERIFIED",
 "acceptance":"decoder may be promoted only after deterministic raster reconstruction and pixel/compositing match against canonical runtime/source evidence"}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2),encoding="utf-8")
print(json.dumps(payload,indent=2))
