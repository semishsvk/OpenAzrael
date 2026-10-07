from pathlib import Path
import hashlib,json,sys,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
status=json.loads((root/"data/tests/kg001_niamh_conversation_fidelity_status_v280.json").read_text())
demo=Path(r"F:\OpenRemaster\sources\materialized\openazrael_demo_atdemo_v1\bf0c87f731bb4e87\layer2\ATDEMO\NIAMH.DAT")
raw=demo.read_bytes(); text=raw.decode("latin1")
out=root/".tmp/niamh_demo_ir_v280.json"
subprocess.run([sys.executable,str(root/"tools/extract_demo_niamh_ir_v253.py"),str(demo),str(out)],check=True,capture_output=True,text=True)
ir=json.loads(out.read_text("utf-8")); records=ir["families"]["1A"]["records"]; ids=[str(x["id"]) for x in records]
checks={
 "demo_size":len(raw)==342,
 "demo_hash":hashlib.sha256(raw).hexdigest()==status["authority"]["sha256"],
 "three_1A_records":ids==["30","999","A"],
 "two_displayable_by_source_semantics":[x["id"] for x in records if x["player_text"]!="DO NOT DISPLAY"]==["30","999"],
 "hidden_A":next(x for x in records if x["id"]=="A")["player_text"]=="DO NOT DISPLAY",
 "retail_28_36_absent":all(("Ni1A_"+x) not in text for x in ["28","29","31","32","33","34","35","36"]),
 "exit_999_text":next(x for x in records if x["id"]=="999")["niamh_text"]=="Please look for Oisin for me.",
 "extractor_demo_bound":ir["source"]["bytes"]==342 and ir["source"]["sha256"]==status["authority"]["sha256"]
}
bad=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.niamh_demo_authority","version":280,"status":"PASS" if not bad else "FAIL","checks":checks,"failed":bad},indent=2))
sys.exit(0 if not bad else 1)
