from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[1]
menu=(R/"scripts/legacy_menu_runtime_v145.gd").read_text()
player=(R/"scripts/player.gd").read_text()
project=(R/"project.godot").read_text()
checks={
 "title_avoids_global_pause":'Do not pause the entire SceneTree for the startup title' in menu,
 "title_dismiss_unpauses":'_dismiss_title()' in menu and 'get_tree().paused = false' in menu,
 "enter_continue":'KEY_ENTER' in menu,
 "space_continue":'KEY_SPACE' in menu,
 "interact_continue":'KEY_E' in menu,
 "wasd_continue":all(k in menu for k in ["KEY_W","KEY_A","KEY_S","KEY_D"]),
 "paused_title_uses_input":'func _input(event: InputEvent)' in menu and '_title_continue_event(event)' in menu,
 "movement_not_consumed":'if not movement_key:' in menu,
 "player_unblocked_after_title":'return title_open or service_open or help_open' in menu and '_controls_blocked()' in player,
 "wasd_inputmap":all(x in project for x in ['move_forward={','physical_keycode":87','move_back={','physical_keycode":83','move_left={','physical_keycode":65','move_right={','physical_keycode":68']),
 "e_interact_inputmap":'interact={' in project and 'physical_keycode":69' in project,
 "physics_reads_actions":'Input.get_vector("move_left", "move_right", "move_forward", "move_back")' in player,
}
bad=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.packaged_input","version":291,"status":"PASS" if not bad else "FAIL","checks":checks,"failed":bad},indent=2))
sys.exit(1 if bad else 0)
