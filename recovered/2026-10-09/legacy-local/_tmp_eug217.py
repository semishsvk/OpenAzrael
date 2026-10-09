from pathlib import Path
root=Path(r"F:\Remaster Framework\work\OpenAzrael")
p=root/"scripts/eugene_controller_v193.gd"; s=p.read_text(encoding="utf-8")
s=s.replace('var source_animation_player: AnimationPlayer = null\n','var source_animation_player: AnimationPlayer = null\nvar source_frame_driver: Node = null\n',1)
s=s.replace('''func bind_source_animation_player(player: AnimationPlayer) -> void:
    source_animation_player = player
    _play_source_family("REST")
''','''func bind_source_animation_player(player: AnimationPlayer) -> void:
    source_animation_player = player
    _play_source_family("REST")

func bind_source_frame_driver(driver: Node) -> void:
    source_frame_driver = driver
    _request_source_family("REST", "", true)

func _request_source_family(family: String, next_family: String = "", loop_family: bool = false) -> void:
    if source_frame_driver != null and is_instance_valid(source_frame_driver):
        if String(source_frame_driver.call("source_family")) == family and not bool(source_frame_driver.call("is_finished")):
            return
        source_frame_driver.call("request_family", family, next_family, loop_family)
''',1)
s=s.replace('''    source_movement_armed = false
    _play_source_family("REST")
''','''    source_movement_armed = false
    _play_source_family("REST")
    _request_source_family("REST", "", true)
''',1)
s=s.replace('''        _play_source_family("REST")
        _source_recovery_update()
''','''        _play_source_family("REST")
        _request_source_family("REST", "", true)
        _source_recovery_update()
''',1)
s=s.replace('''        _play_source_family("REST")
        return
''','''        _play_source_family("REST")
        _request_source_family("REST", "", true)
        return
''',1)
s=s.replace('''        _play_source_family("REST")
        _arm_recovery()
''','''        _play_source_family("REST")
        _request_source_family("REST", "", true)
        _arm_recovery()
''',1)
s=s.replace('''    _play_source_family("RUN")
    move_and_collide(motion)
''','''    _play_source_family("RUN")
    _request_source_family("RUN", "REST", false)
    move_and_collide(motion)
''',1)
p.write_text(s,encoding="utf-8")

p=root/"scripts/room_manager.gd"; s=p.read_text(encoding="utf-8")
needle='''            root.call("bind_source_animation_player", source_player)
            result["animation_clock_adapter_fps"] = null
'''
repl='''            root.call("bind_source_animation_player", source_player)
            var source_frame_driver := Node.new()
            source_frame_driver.name = "SourceFrameDriverV217"
            source_frame_driver.set_script(preload("res://scripts/source_frame_animation_driver_v195.gd"))
            root.add_child(source_frame_driver)
            var family_bounds := {
                "REST":[0,0], "RUN":[2,7], "ATTACK":[53,70],
                "SHOT":[130,163], "DEATH_TWITCH":[160,163], "DEAD":[163,163]
            }
            var driver_ok := bool(source_frame_driver.call("configure", source_player, family_bounds, 1.0 / 15.0))
            var audio_bound := bool(animation_audio.call("bind_source_frame_driver", source_frame_driver)) if driver_ok else false
            if driver_ok:
                root.call("bind_source_frame_driver", source_frame_driver)
            result["source_frame_driver"] = "BOUND_FAIL_CLOSED_NO_WALL_CLOCK_TICK" if driver_ok and audio_bound else "FAIL_BIND"
            result["render_encoding_seconds_per_frame"] = 1.0 / 15.0
            result["animation_clock_adapter_fps"] = null
'''
if needle not in s: raise SystemExit("room needle missing")
s=s.replace(needle,repl,1)
p.write_text(s,encoding="utf-8")
print("EUGENE_SOURCE_FRAME_DRIVER_V217_PATCHED")
