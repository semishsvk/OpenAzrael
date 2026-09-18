#!/usr/bin/env python3
import json, pathlib, re, sys
root=pathlib.Path(__file__).resolve().parents[1]
g=json.loads((root/'data/gameplay_event_graph_v87.json').read_text())
checks=[]
def ck(name, cond): checks.append((name,bool(cond)))
allowed={'set_flag','set_puzzle_node','add_inventory','remove_inventory','play_sound'}
for gid,graph in g['graphs'].items():
    ck(gid+':actions', bool(graph.get('actions')))
    for i,a in enumerate(graph['actions']):
        ck(f'{gid}:{i}:op', a.get('op') in allowed)
        if a.get('op')=='play_sound':
            ck(f'{gid}:{i}:asset', (root/'assets/audio'/a['asset']).is_file())
runner=(root/'scripts/legacy_event_runner_v87.gd').read_text()
ck('runner loads graph', 'gameplay_event_graph_v87.json' in runner)
ck('autoload registered', 'LegacyEvents="*res://scripts/legacy_event_runner_v87.gd"' in (root/'project.godot').read_text())
for f,ids in {
 'scripts/r8_bible_interaction.gd':['R8_LENS_PLACE','R8_OPTICAL_START','R8_SECRET_DOOR_OPEN'],
 'scripts/r8_shield_interaction.gd':['R8_TAKE_SHIELD'],
 'scripts/demo_state.gd':['R7_WATER_SWITCHBOARD_SOLVED']}.items():
    s=(root/f).read_text()
    for gid in ids: ck(f'{f}:{gid}', f'LegacyEvents.run("{gid}")' in s)
failed=[n for n,v in checks if not v]
out={'version':87,'checks':len(checks),'passed':len(checks)-len(failed),'failed':failed,'status':'PASS' if not failed else 'FAIL'}
(root/'data/gameplay_event_graph_validation_v87.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
sys.exit(1 if failed else 0)
