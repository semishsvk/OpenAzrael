#!/usr/bin/env python3
from pathlib import Path
import json,re,sys

ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_menu_cursor_context_contract_v146.json").read_text(encoding="utf-8"))
hud=(ROOT/"scripts/hud.gd").read_text(encoding="utf-8")
menu=(ROOT/"scripts/legacy_menu_runtime_v145.gd").read_text(encoding="utf-8")
runner=(ROOT/"scripts/kg001_menu_cursor_context_runner_v146.gd").read_text(encoding="utf-8")
cursor_runner=(ROOT/"scripts/kg001_interaction_cursor_runner_v143.gd").read_text(encoding="utf-8")

def rects_overlap(a,b):
    ax,ay,aw,ah=a; bx,by,bw,bh=b
    return not (ax+aw<=bx or bx+bw<=ax or ay+ah<=by or by+bh<=ay)

actions=contract["service_action_policy"]["actions"]
names=list(actions)
overlaps=[]
for i,name in enumerate(names):
    for other in names[i+1:]:
        if rects_overlap(actions[name],actions[other]):
            overlaps.append([name,other])

samples={
 "LOAD":[50,35],
 "SAVE":[60,100],
 "MUSIC":[120,45],
 "SFX":[120,80],
 "QUIT":[80,60],
 "CONFIRM":[40,130],
}
def contains(rect,p):
    x,y,w,h=rect; px,py=p
    return x<=px<x+w and y<=py<y+h

checks={
 "schema":contract.get("schema")=="openazrael.kg001.menu_cursor_context_contract" and contract.get("version")==146,
 "dedicated_cursor_layer":all(token in hud for token in ('InteractionCursorLayerV146','interaction_cursor_layer.layer = 100','interaction_cursor_layer.add_child(interaction_cursor)')),
 "menu_layer_50":"layer = 50" in menu,
 "cursor_above_menu":int(contract["layering"]["interaction_cursor_layer"])>int(contract["layering"]["classic_menu_layer"]),
 "graphical_mouse_follow":"get_viewport().get_mouse_position()" in hud and 'Input.mouse_mode == Input.MOUSE_MODE_VISIBLE' in hud,
 "modal_cursor_block":all(token in hud for token in ('legacy_menu.has_method("blocks_world_cursor")','menu_blocks_world','if not menu_blocks_world')),
 "menu_exposes_block":"func blocks_world_cursor() -> bool:" in menu and "return title_open or service_open" in menu,
 "probe_still_dynamic":"interaction_probe.call(\"current_cursor_id\")" in hud,
 "service_regions_nonoverlap":not overlaps,
 "v145_samples_preserved":all(contains(actions[k],v) for k,v in samples.items()),
 "v143_runner_recursive_cursor":"find_child(\"InteractionCursorV143\", true, false)" in cursor_runner,
 "runtime_marker":"OPENAZRAEL_KG001_MENU_CURSOR_V146" in runner,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
 "schema":"openazrael.kg001.menu_cursor_context_validation",
 "version":146,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL",
 "runtime_status":"NOT_EXECUTED",
 "checks":checks,
 "overlaps":overlaps,
 "failed":failed,
},indent=2))
sys.exit(1 if failed else 0)
