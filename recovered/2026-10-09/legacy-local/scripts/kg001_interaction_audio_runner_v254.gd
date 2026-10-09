extends SceneTree
var fail:Array[String]=[]
var checks:=0
func ck(n:String,v:bool): checks+=1; if not v: fail.append(n)
func _initialize(): call_deferred("run")
func run():
 var ev=root.get_node("LegacyEvents"); ev.set_capture_only(true)
 var cases={"R1_CORRIDOR_DOOR_OPEN":["995.WAV"],"R7_WELL_TONGS_USE":["979TONGS.WAV"],"R7_SWITCH_LEVER_PULL":["981PULL.WAV"],"R7_SWITCH_WHEEL_TURN":["977TURN.WAV"],"R7_WATER_SWITCHBOARD_SOLVED":["S152V2.WAV"],"R8_TAPESTRY_PLACE":["797TAP.WAV"],"R8_TAPESTRY_ROTATE":["S25.WAV"],"R8_LENS_PLACE":["S137.WAV"],"R8_OPTICAL_START":["S121.WAV"],"R8_SECRET_DOOR_OPEN":["799SECDR.WAV"],"R7_NIAMH_ACTIVATE":[]}
 for g in cases:
  ev.clear_capture(); ck(g+"_exists",ev.has_graph(g)); ev.run(g); await process_frame; ck(g+"_audio",ev.captured_audio()==cases[g])
 var m=JSON.parse_string(FileAccess.get_file_as_string("res://data/audio/interaction_audio_matrix_v254.json"))
 ck("matrix_parse",m is Dictionary); ck("matrix_22",m.get("interactions",[]).size()==22)
 var n=JSON.parse_string(FileAccess.get_file_as_string("res://data/tests/kg001_niamh_conversation_1a_contract_v180.json"))
 ck("niamh_audio_absent",String(n.get("audio",{}).get("status",""))=="NOT_PRESENT_AS_STANDALONE_NIAMH_VOICE_WAV_IN_CANONICAL_DEMO")
 print("OPENAZRAEL_INTERACTION_AUDIO_V254 "+JSON.stringify({"status":"PASS" if fail.is_empty() else "FAIL","checks":checks,"failed":fail}))
 quit(0 if fail.is_empty() else 1)
