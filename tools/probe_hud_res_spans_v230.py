from pathlib import Path
from PIL import Image
import collections,json
d=Path(r"F:\OpenRemaster\sources\materialized\openazrael_demo_atdemo_v1\bf0c87f731bb4e87\layer2\ATDEMO")
im=Image.open(d/"HUD3.PCX")
pix=list(im.getdata())
hist=collections.Counter(pix)
pal=im.getpalette()
def rgb(i): return pal[i*3:i*3+3]
out={"hud3_top_indices":hist.most_common(20),"index54":{"count":hist[54],"rgb":rgb(54)}}
for n in ["HUDTOP.RES","HUDBOT.RES"]:
 b=(d/n).read_bytes()
 non=[(i,x) for i,x in enumerate(b) if x!=54]
 out[n]={"non54_count":len(non),"first_non54":non[:100],"runs54":[]}
 start=None
 for i,x in enumerate(b+bytes([0])):
  if x==54 and start is None:start=i
  if x!=54 and start is not None:
   out[n]["runs54"].append([start,i-start]);start=None
 out[n]["runs54"]=sorted(out[n]["runs54"],key=lambda z:z[1],reverse=True)[:40]
Path("data/runtime_generated/hud_res_span_probe_v230.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2)[:7000])
