extends SceneTree
var failed:Array[String]=[]
var checks:=0
func check(name:String,value:bool):
    checks+=1
    if not value:failed.append(name)
func _initialize():call_deferred("run")
func run():
    var scene=load("res://main.tscn").instantiate()
    root.add_child(scene)
    for i in range(8):await process_frame
    var menu=scene.get_node("LegacyMenuV145")
    var scanner=menu.scanner_runtime
    var camera=scene.get_node("Player/Camera3D")
    var before:Vector3=camera.global_position
    menu._dismiss_title()
    for i in range(8):await process_frame
    check("physical_initial_zxentry_dispatch",scanner.startup_requested and scanner.startup_started)
    before = camera.global_position
    scanner.set_process(false)
    for i in range(1500):scanner._process(0.016)
    check("source_counter_completed",scanner.hint_counter==4)
    check("source_timer_stopped",not scanner.hint_timer_active)
    check("source_queue_drained",scanner.pending_tokens.is_empty())
    check("source_origin",scanner.position==Vector2(425,84))
    check("source_size",scanner.size==Vector2(170,206))
    var indexed:=PackedByteArray()
    var unknown:=0
    for y in range(206):
        for x in range(170):
            var c:Color=scanner.panel_image.get_pixel(x,y)
            if c.a==0:indexed.append(0)
            elif c.r8==0 and c.g8==0 and c.b8==0:indexed.append(54)
            elif c.r8==248 and c.g8==176 and c.b8==24:indexed.append(56)
            else:
                unknown+=1
                indexed.append(255)
    check("source_palette",unknown==0)
    var hash:=HashingContext.new()
    hash.start(HashingContext.HASH_SHA256)
    hash.update(indexed)
    var contract:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://data/ui/legacy_hud_startup_v215.json"))
    var actual:=hash.finish().hex_encode()
    check("all_35020_source_panel_pixels",actual==contract.final_buffer_indexed_sha256)
    check("source_text_cursor",scanner.text_cursor==Vector2i(0,194))
    scanner.request_source_startup()
    check("one_shot_no_requeue",scanner.pending_tokens.is_empty() and scanner.hint_counter==4)
    check("camera_unmodified",camera.global_position.distance_to(before)<1.0)
    check("no_fixed_source_hz_claim",contract.fixed_source_hz_claimed==false)
    print(JSON.stringify({"status":"PASS" if failed.is_empty() else "FAIL","checks":checks,"failed":failed,"panel_sha256":actual,"unknown_pixels":unknown}))
    scene.queue_free()
    quit(0 if failed.is_empty() else 1)
