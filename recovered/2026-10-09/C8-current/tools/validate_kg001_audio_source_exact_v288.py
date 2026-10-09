from pathlib import Path
import json,hashlib,sys,struct,tempfile
root=Path(__file__).resolve().parents[1]
src=Path(r"F:\OpenRemaster\sources\materialized\openazrael_demo_atdemo_v1\bf0c87f731bb4e87\layer2\ATDEMO")
manifest=json.loads((root/".tmp/kg001/candidate4_audio_restore_v132.json").read_text())
repaired={"981PULL.WAV","S137.WAV"}
bad=[]; rows=[]
def pcm(b):
    if b[:4]!=b"RIFF" or b[8:12]!=b"WAVE" or b[36:40]!=b"data": return None
    n=struct.unpack_from("<I",b,40)[0]
    return b[44:44+n]
for rec in manifest["files"]:
    n=rec["filename"]; a=src/n; b=root/"assets/audio"/n
    ab=a.read_bytes(); bb=b.read_bytes()
    ah=hashlib.sha256(ab).hexdigest(); bh=hashlib.sha256(bb).hexdigest()
    source_ok=ah==rec["source_sha256"]
    if n in repaired:
        expected=ab+(b"\0" if len(ab)%2 else b"")
        expected=expected[:4]+struct.pack("<I",len(expected)-8)+expected[8:]
        ok=source_ok and bb==expected and pcm(ab)==pcm(bb)
        mode="DETERMINISTIC_RIFF_PAD_PCM_EXACT"
    else:
        ok=source_ok and ab==bb
        mode="BYTE_EXACT"
    rows.append({"file":n,"ok":ok,"mode":mode,"source":ah,"runtime":bh})
    if not ok: bad.append(n)
print(json.dumps({"schema":"openazrael.kg001.audio_source_fidelity","version":288,"status":"PASS" if not bad else "FAIL","count":len(rows),"repaired":sorted(repaired),"failed":bad},indent=2))
sys.exit(1 if bad else 0)
