from pathlib import Path
import json,sys,hashlib
R=Path(__file__).resolve().parents[1]
lens=(R/"scripts/r8_lens_interaction.gd").read_text()
bible=(R/"scripts/r8_bible_interaction.gd").read_text()
preview=(R/"scripts/pickup_preview_v226.gd").read_text()
runner=(R/"scripts/kg001_parchment_fullscreen_runner_v255.gd").read_text()
full=(R/"scripts/kg001_full_demo_runner_v111.gd").read_text()
checks={
 "lens_requires_drain":'DemoState.flag("R8BathDrain")' in lens,
 "lens_acquire_and_flag":'DemoState.acquire("r8_lens")' in lens and 'DemoState.set_flag("R8Lens")' in lens,
 "lens_place_distinct":'LegacyEvents.run("R8_LENS_PLACE")' in bible and 'return' in bible,
 "optical_requires_zone":'if not _on_activation_zone()' in bible and 'LegacyEvents.run("R8_OPTICAL_START")' in bible,
 "secret_door_event":'LegacyEvents.run("R8_SECRET_DOOR_OPEN")' in bible,
 "door_exposes_shield":'shield_visual.visible = true' in bible and 'shield_interaction.collision_layer = 2' in bible,
 "timing_explicit_reconstruction":'only the interpolation/timing remains reconstruction' in bible,
 "parchment_source_asset":'PARCHMENT_R1.png' in preview and 'PARCHMENT_R1.png' in runner,
 "parchment_640x480":'get_width()==640' in runner and 'get_height()==480' in runner,
 "parchment_aspect":'STRETCH_KEEP_ASPECT_CENTERED' in runner,
 "full_demo_lens_progression":all(x in full for x in ["r8_lens","R8LensPlace","DoorR8","shield"]),
}
bad=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.lens_parchment_preflight","version":290,"status":"PASS" if not bad else "FAIL","checks":checks,"failed":bad},indent=2))
sys.exit(1 if bad else 0)
