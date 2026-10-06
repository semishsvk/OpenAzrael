extends SceneTree
var failed:Array[String]=[]
func ck(v:bool,n:String): 
    if not v: failed.append(n)
func _initialize(): call_deferred("_run")
func _run():
    var ir=JSON.parse_string(FileAccess.get_file_as_string("res://data/runtime_generated/niamh_conversation_ir_v209.json"))
    ck(ir is Dictionary,"ir_load")
    ck(String(ir.source.sha256)=="e3f0b14b64682f0e621f7f52fb998ccf8ddba4febd0ac0df4aa201f371939f71","canonical_atdemo_hash")
    ck(String(ir.get("scope",""))=="ATDEMO","demo_scope")
    ck(ir.families["1A"].records.size()==3,"1A_demo_3_records")
    ck(not ir.families.has("1B"),"retail_1B_not_required")
    var s=load("res://main.tscn").instantiate(); root.add_child(s); current_scene=s
    await process_frame; await process_frame
    var rm=s.get_node("RoomManager"); var ui=s.get_node("ConversationUIV208")
    rm.call("_on_conversation_requested",{"character":"Niamh","family":"1A","source_required":true})
    await process_frame
    ck(bool(ui.get("active")),"ui_open")
    var choices:Array=ui.get("choices")
    ck(choices.size()==2,"1A_demo_visible_choices_excludes_A")
    ck(String(choices[0].id)=="30","first_choice_30")
    ck(String(choices[0].player_text)=="Good Lord. What are you?","player_speaker_text")
    ck(String(choices[0].niamh_text).begins_with("What do you mean?"),"niamh_response_text")
    var found999=false
    for row in choices:
        if String(row.id)=="999": found999=true
    ck(found999,"leave_choice_present")
    ui.call("_show_response",choices[0])
    ck(bool(ui.get("response_mode")),"response_mode")
    var next=ui.call("_load_family","1B")
    ck(next.is_empty(),"retail_1B_absent")
    print("OPENAZRAEL_NIAMH_FLOW_V209 "+JSON.stringify({"status":"PASS" if failed.is_empty() else "FAIL","failed":failed,"scope":"ATDEMO","1A_source":3,"1A_visible":choices.size(),"1B_source":0}))
    quit(0 if failed.is_empty() else 1)
