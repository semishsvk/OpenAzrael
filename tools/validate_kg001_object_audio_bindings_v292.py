from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[1]
g=json.loads((R/"data/gameplay_event_graph_v87.json").read_text())["graphs"]
expected={
 "R1_DOOR_OPEN_SOUND":"995.WAV",
 "R7_SWITCH_LEVER_PUSH_SOUND":"982PUSH.WAV",
 "R7_SWITCH_WHEEL_TURN_SOUND":"977TURN.WAV",
 "R7_SWITCH_LEVER_PULL_SOUND":"981PULL.WAV",
 "R7_WATER_CONNECTED_SOUND":"S16.WAV",
 "R7_WATER_SWITCHBOARD_SOLVED":"S152V2.WAV",
 "R7_WELL_TONGS_USE":"979TONGS.WAV",
 "R8_LENS_PLACE":"S137.WAV",
 "R8_OPTICAL_START":"S121.WAV",
 "R8_SECRET_DOOR_OPEN":"799SECDR.WAV",
 "R8_TAPESTRY_ROTATE_SOUND":"S25.WAV",
 "R8_TAPESTRY_FRAME_TAP_SOUND":"797TAP.WAV",
 "R1_PARCHMENT_PREVIEW_SOUND":"SPAPER.WAV",
}
scripts={
 "R1_DOOR_OPEN_SOUND":"scripts/r1_door_interaction.gd",
 "R7_SWITCH_LEVER_PUSH_SOUND":"scripts/r7_switch_control.gd",
 "R7_SWITCH_WHEEL_TURN_SOUND":"scripts/r7_switch_control.gd",
 "R7_SWITCH_LEVER_PULL_SOUND":"scripts/r7_switch_control.gd",
 "R7_WATER_CONNECTED_SOUND":"scripts/r7_switch_control.gd",
 "R7_WELL_TONGS_USE":"scripts/well_key_interaction.gd",
 "R8_LENS_PLACE":"scripts/r8_bible_interaction.gd",
 "R8_OPTICAL_START":"scripts/r8_bible_interaction.gd",
 "R8_SECRET_DOOR_OPEN":"scripts/r8_bible_interaction.gd",
 "R8_TAPESTRY_ROTATE_SOUND":"scripts/r8_tapestry_interaction.gd",
 "R8_TAPESTRY_FRAME_TAP_SOUND":"scripts/r8_tapestry_frame.gd",
 "R1_PARCHMENT_PREVIEW_SOUND":"scripts/pickup_preview_v226.gd",
}
bad=[]; rows=[]
for event,wav in expected.items():
 actions=g.get(event,{}).get("actions",[])
 assets=[a.get("asset") for a in actions if a.get("op")=="play_sound"]
 graph_ok=wav in assets
 file_ok=(R/"assets/audio"/wav).is_file()
 script_ok=True
 if event in scripts:
  script_ok=f'LegacyEvents.run("{event}")' in (R/scripts[event]).read_text()
 ok=graph_ok and file_ok and script_ok
 rows.append({"event":event,"wav":wav,"graph":graph_ok,"asset":file_ok,"runtime_call":script_ok,"ok":ok})
 if not ok: bad.append(event)
print(json.dumps({"schema":"openazrael.kg001.object_audio_bindings","version":292,"status":"PASS" if not bad else "FAIL","count":len(rows),"rows":rows,"hold":["983TUNK.WAV wheel movement timing remains source-context verified but runtime sequencing HOLD"],"failed":bad},indent=2))
sys.exit(1 if bad else 0)
