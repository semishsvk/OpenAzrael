from pathlib import Path
import json,re,sys
root=Path(__file__).resolve().parents[1]
src=Path(r"F:\OpenRemaster\sources\materialized\openazrael_demo_atdemo_v1\bf0c87f731bb4e87\layer2\ATDEMO")
dat=(src/"NIAMH.DAT").read_text("latin1")
wavs=sorted(p.name for p in src.glob("*.WAV"))
niamh_named=[n for n in wavs if "NIAMH" in n.upper() or n.upper().startswith("NI")]
checks={
 "canonical_demo_wav_count":len(wavs)==30,
 "no_wav_token_in_niamh_dat":".WAV" not in dat.upper(),
 "no_niamh_named_voice_asset":not niamh_named,
 "dialogue_source_is_text":all(x in dat for x in ["Good Lord. What are you?","Please look for Oisin for me.","Ni1A_30","Ni1A_999"]),
}
bad=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.niamh_audio","version":289,"status":"PASS_TEXT_ONLY_SOURCE" if not bad else "FAIL","checks":checks,"niamh_named_wavs":niamh_named,"failed":bad},indent=2))
sys.exit(1 if bad else 0)
