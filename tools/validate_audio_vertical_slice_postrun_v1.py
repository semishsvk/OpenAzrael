#!/usr/bin/env python3
import argparse,json
from pathlib import Path

EXPECTED_ROOMS=["R1","R7","R1","R8"]
EXPECTED_AUDIO=["S152V2.WAV","S137.WAV","S121.WAV","799SECDR.WAV"]
EXPECTED_DETAIL={
 "S152V2.WAV":"R7_WATER_SWITCHBOARD_SOLVED",
 "S137.WAV":"R8_LENS_PLACE",
 "S121.WAV":"R8_OPTICAL_START",
 "799SECDR.WAV":"R8_SECRET_DOOR_OPEN",
}

ap=argparse.ArgumentParser()
ap.add_argument("event_log",type=Path)
a=ap.parse_args()
entries=[]
for n,line in enumerate(a.event_log.read_text(encoding="utf-8").splitlines(),1):
 if not line.strip(): continue
 try: entries.append(json.loads(line))
 except Exception as e: raise SystemExit(f"invalid JSONL line {n}: {e}")

fail=[]
seq=[int(e.get("seq",-1)) for e in entries]
if seq!=sorted(seq) or len(seq)!=len(set(seq)): fail.append("event seq is not strictly unique/ordered")
rooms=[e.get("data",{}).get("room") for e in entries if e.get("kind")=="room_loaded"]
# Ignore repeated initial/debug loads, but require expected route as ordered subsequence.
i=0
for r in rooms:
 if i<len(EXPECTED_ROOMS) and r==EXPECTED_ROOMS[i]: i+=1
if i!=len(EXPECTED_ROOMS): fail.append(f"missing ordered room route {EXPECTED_ROOMS}; saw {rooms}")
audio=[e.get("data",{}).get("asset") for e in entries if e.get("kind")=="logical_audio"]
i=0
for s in audio:
 if i<len(EXPECTED_AUDIO) and s==EXPECTED_AUDIO[i]: i+=1
if i!=len(EXPECTED_AUDIO): fail.append(f"missing ordered logical audio {EXPECTED_AUDIO}; saw {audio}")
details=[e.get("data",{}) for e in entries if e.get("kind")=="logical_audio_detail"]
for asset,graph in EXPECTED_DETAIL.items():
 hit=[d for d in details if d.get("asset")==asset and d.get("graph_id")==graph]
 if not hit: fail.append(f"missing detail {graph}->{asset}")
 else:
  d=hit[-1]
  for k in ("sound_id","emitter_id","confidence","provenance"):
   if not d.get(k): fail.append(f"{graph}->{asset} missing {k}")
# Tongs/well: gameplay state is testable; original 979tongs playback remains HOLD.
flags=[e.get("data",{}) for e in entries if e.get("kind")=="flag_changed"]
puzzles=[e.get("data",{}) for e in entries if e.get("kind")=="puzzle_node_changed"]
inventories=[e.get("data",{}).get("inventory",[]) for e in entries if e.get("kind")=="inventory_changed"]
if not any("well_key" in x for x in inventories): fail.append("well_key acquisition not observed")
if not any(x.get("node")=="R7KeyTake" and x.get("value") is True for x in puzzles): fail.append("R7KeyTake true not observed")
if not any(x.get("flag")=="R7key" and x.get("value") is True for x in flags): fail.append("R7key true not observed")
if any(x=="979tongs.WAV" for x in audio):
 print("INFO: 979tongs.WAV observed; forensic promotion still requires correlation review")

print(json.dumps({"schema":"openazrael.audio_vertical_slice_postrun","status":"PASS" if not fail else "FAIL","entries":len(entries),"failures":fail,"tongs_audio_binding":"HOLD"},indent=2))
raise SystemExit(0 if not fail else 1)
