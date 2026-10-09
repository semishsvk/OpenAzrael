extends SceneTree
var failures:Array[String]=[]
func check(n:String,v:bool)->void:
 if not v: failures.append(n)
func _initialize()->void: call_deferred("run")
func run()->void:
 await process_frame
 var ds=root.get_node("DemoState")
 var loc=root.get_node("LocalizationManager")
 var ev=root.get_node("LegacyEvents")
 var scene=load("res://main.tscn").instantiate()
 root.add_child(scene)
 await process_frame; await process_frame
 var hud=scene.get_node("HUD")
 var before=ds.canonical_state_hash()
 loc.set_locale("en",false)
 ev.conversation_requested.emit({"character":"Niamh","family":"1A","source_required":true})
 await process_frame
 check("en_opening",hud.dialogue_label.text==loc.tr_key("dialog.demo.niamh.0001"))
 loc.set_locale("sk",false)
 check("locale_switch_does_not_mutate_state",before==ds.canonical_state_hash())
 hud._show_dialogue_key(hud.dialogue_keys[hud.dialogue_index])
 check("active_dialogue_relocalizes",hud.dialogue_label.text==loc.tr_key("dialog.demo.niamh.0001"))
 check("five_source_lines",hud.dialogue_keys.size()==5)
 check("sk_diacritics_registry",loc.tr_key("dialog.demo.niamh.0030").unicode_at(0)==0x010C and loc.tr_key("item.rusty_tongs.inventory").unicode_at(6)==0x00E9)
 loc.set_locale("en",false); hud._show_dialogue_key(hud.dialogue_keys[hud.dialogue_index])
 for i in range(4): hud.advance_dialogue()
 check("en_last",hud.dialogue_label.text==loc.tr_key("dialog.demo.niamh.a"))
 var after_en=ds.canonical_state_hash()
 loc.set_locale("sk",false)
 ev.conversation_requested.emit({"character":"Niamh","family":"1A","source_required":true})
 await process_frame
 check("sk_opening",hud.dialogue_label.text==loc.tr_key("dialog.demo.niamh.0001"))
 for i in range(4): hud.advance_dialogue()
 check("sk_last",hud.dialogue_label.text==loc.tr_key("dialog.demo.niamh.a"))
 var after_sk=ds.canonical_state_hash()
 check("state_invariant_en",before==after_en)
 check("state_invariant_sk",after_en==after_sk)
 print("OPENAZRAEL_LOCALIZATION_PRESENTATION_V203 "+JSON.stringify({"status":"PASS" if failures.is_empty() else "FAIL","checks":10,"failed":failures,"state_hash":after_sk}))
 scene.queue_free()
 await process_frame; await process_frame; await process_frame
 quit(0 if failures.is_empty() else 1)
