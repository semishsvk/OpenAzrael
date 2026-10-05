extends SceneTree
var failed:Array[String]=[]
func ck(v:bool,n:String): 
    if not v: failed.append(n)
func _initialize(): call_deferred("_run")
func _run():
    var ir=JSON.parse_string(FileAccess.get_file_as_string("res://data/runtime_generated/niamh_conversation_ir_v209.json"))
    ck(ir is Dictionary,"ir_load")
    ck(String(ir.source.sha256)=="a7c3f14d8a76c9c8255f26f77e31ca9a860263697376afaf042469d4eb0f671a","canonical_hash")
    ck(ir.families["1A"].records.size()==11,"1A_11_records")
    ck(ir.families["1B"].records.size()==36,"1B_36_records")
    var s=load("res://main.tscn").instantiate(); root.add_child(s); current_scene=s
    await process_frame; await process_frame
    var rm=s.get_node("RoomManager"); var ui=s.get_node("ConversationUIV208")
    rm.call("_on_conversation_requested",{"character":"Niamh","family":"1A","source_required":true})
    await process_frame
    ck(bool(ui.get("active")),"ui_open")
    var choices:Array=ui.get("choices")
    ck(choices.size()==10,"1A_visible_choices_excludes_A")
    ck(String(choices[0].player_text)=="No, I'm not Oisin. Who are you?","player_speaker_text")
    ck(String(choices[0].niamh_text).begins_with("(despair)"),"niamh_response_text")
    var found999=false
    for row in choices:
        if String(row.id)=="999": found999=true
    ck(found999,"leave_choice_present")
    ui.call("_show_response",choices[0])
    ck(bool(ui.get("response_mode")),"response_mode")
    var next=ui.call("_load_family","1B")
    ck(next.size()<36 and next.size()>0,"1B_missing_answers_filtered")
    print("OPENAZRAEL_NIAMH_FLOW_V209 "+JSON.stringify({"status":"PASS" if failed.is_empty() else "FAIL","failed":failed,"1A_source":11,"1A_visible":choices.size(),"1B_source":36,"1B_playable":next.size()}))
    quit(0 if failed.is_empty() else 1)
