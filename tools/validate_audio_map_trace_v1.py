#!/usr/bin/env python3
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
db=json.loads((R/"data/audio/sound_database_r1_r7_r8_v1.json").read_text())
mp=json.loads((R/"data/audio/original_audio_map_r1_r7_r8_v1.json").read_text())
ts=json.loads((R/"data/tests/audio_interaction_trace_r1_r7_r8_v1.json").read_text())
errs=[]
ids={x["sound_id"] for x in db["records"]}
if len(ids)!=len(db["records"]): errs.append("duplicate sound_id")
for x in db["records"]:
 if not x.get("provenance") or x.get("confidence") not in {"VERIFIED","HIGH","MEDIUM","LOW","HOLD"}: errs.append("bad evidence "+x.get("sound_id","?"))
for e in mp["emitters"]:
 refs=e.get("sound_ids",[e.get("sound_id")])
 for s in refs:
  if s not in ids: errs.append("dangling emitter sound "+str(s))
for b in mp["event_bindings"]:
 if b["sound_id"] not in ids: errs.append("dangling event sound "+b["sound_id"])
for c in ts["cases"]:
 if c["sound_id"] not in ids: errs.append("dangling test sound "+c["sound_id"])
 if c["confidence"]=="HOLD" and c["expected_state"]!="HOLD": errs.append("HOLD case claims state")
if ts["required_trace"] != ["player_action","trigger","audio_event","emitter","asset_request","state_change"]: errs.append("trace contract changed")
if errs:
 print("AUDIO MAP/TRACE: FAIL"); [print(" -",e) for e in errs]; raise SystemExit(1)
print("AUDIO MAP/TRACE: PASS")
print(f" sounds={len(ids)} emitters={len(mp['emitters'])} cases={len(ts['cases'])} tongs_well=HOLD")
