#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_CHECKPOINT="v116-context-v32"
errors=[]

def req(p):
    p=ROOT/p
    if not p.exists():
        errors.append(f"missing: {p.relative_to(ROOT)}")

def validate_runtime_evidence(quality):
    """Accept recorded automation without clearing human release blockers."""
    runtime_specs=(
        ("v109",109,"kg001_headless_runtime","headless","headless"),
        ("v110",110,"kg001_room_trigger_runtime","room_trigger","room_trigger"),
        ("v111",111,"kg001_full_demo_runtime","full_demo","full_demo"),
        ("audio_v116",116,"kg001_physical_audio_runtime","audio","audio_runtime"),
    )
    evidence_commit=quality.get("kg001_runtime_evidence_commit")
    promoted=(
        evidence_commit or any(quality.get(field)=="PASS" for _,_,field,_,_ in runtime_specs)
        or quality.get("kg001_candidate_build_runtime")=="V32_AUTOMATED_PASS_MANUAL_PENDING"
        or quality.get("kg001_legacy_colorkey_runtime")=="ASSET_VALIDATION_PASS_MANUAL_PENDING"
        or any(quality.get(field)=="AUTOMATED_PASS_MANUAL_RETEST_REQUIRED" for field in
               ("kg001_collision_issue_6","kg001_audio_issue_9","kg001_texture_issue_11"))
    )
    if not promoted:
        return
    if (not isinstance(evidence_commit,str) or len(evidence_commit)!=40
            or any(char not in "0123456789abcdef" for char in evidence_commit)):
        errors.append("runtime promotion requires a full tested commit SHA")
        return

    def read_json(path):
        return json.loads((ROOT/path).read_text(encoding="utf-8"))

    oracle=read_json("data/tests/kg001_state_space_v108.json")
    for name,version,field,stem,schema in runtime_specs:
        runtime=read_json(f"data/tests/kg001_{stem}_runtime_v{version}.json")
        if (quality.get(field)!="PASS" or runtime.get("status")!="PASS"
                or runtime.get("_process_returncode")!=0 or runtime.get("failed")!=[]
                or runtime.get("schema")!=f"openazrael.kg001.{schema}"
                or runtime.get("version")!=version or runtime.get("_commit_sha")!=evidence_commit
                or runtime.get("engine_errors",[])!=[]
                or any(line.lstrip().startswith(("ERROR:","SCRIPT ERROR:"))
                       for line in runtime.get("_output_tail","").splitlines())):
            errors.append(f"{name} PASS requires successful runtime evidence at the tested commit")
        if version in (109,111) and (
                runtime.get("persistent_hash")!=oracle.get("shortest_success_persistent_state_sha256")
                or runtime.get("logical_audio_events")!=oracle.get("shortest_success_audio_events")):
            errors.append(f"{name} hash/audio must match the v108 oracle")
        if name=="audio_v116" and (
                runtime.get("ambient_counts")!={"R1":2,"R7":3,"R8":2}
                or runtime.get("event_assets")!=["979TONGS.WAV","S152V2.WAV"]):
            errors.append("physical audio evidence must match the recovered demo topology")

    fresh=read_json("data/tests/kg001_fresh_checkout.json")
    rooms={f"assets/rooms/{room}.glb" for room in ("R1","R7","R8")}
    def room_evidence_pass(mapping):
        return isinstance(mapping,dict) and {
            key.replace("\\","/") for key,value in mapping.items() if value is True
        }==rooms
    runtime_status=fresh.get("runtime_status")
    base_runtime_names={name for name,_,_,_,_ in runtime_specs}
    runtime_status_ok=(
        isinstance(runtime_status,dict)
        and all(runtime_status.get(name)=="PASS" for name in base_runtime_names)
        and set(runtime_status).issubset(
            base_runtime_names | {"physical_v117", "well_tongs_v118", "r1_route_v119"}
        )
        and runtime_status.get("physical_v117","PASS")=="PASS"
        and runtime_status.get("well_tongs_v118","PASS")=="PASS"
        and runtime_status.get("r1_route_v119","PASS")=="PASS"
    )
    if (fresh.get("status")!="PASS" or fresh.get("commit_sha")!=evidence_commit
            or fresh.get("schema")!="openazrael.kg001.fresh_checkout" or fresh.get("version")!=112
            or fresh.get("clean_before") is not True or fresh.get("clean_after") is not True
            or fresh.get("godot_import_status")!="PASS" or fresh.get("source_validators_pass") is not True
            or fresh.get("forbidden_tracked_files")!=[]
            or not runtime_status_ok
            or not room_evidence_pass(fresh.get("room_assets_present"))
            or not room_evidence_pass(fresh.get("room_assets_git_ignored"))):
        errors.append("runtime promotion requires complete clean-checkout PASS evidence")

    physical_path=ROOT/"data/tests/kg001_physical_traversal_runtime_v117.json"
    physical_required=isinstance(runtime_status,dict) and "physical_v117" in runtime_status
    if physical_required:
        if not physical_path.is_file():
            errors.append("physical traversal fresh-checkout PASS requires v117 runtime evidence")
        else:
            physical=read_json("data/tests/kg001_physical_traversal_runtime_v117.json")
            if (physical.get("status")!="PASS" or physical.get("failed")!=[]
                    or physical.get("schema")!="openazrael.kg001.physical_traversal"
                    or physical.get("version")!=117 or physical.get("_commit_sha")!=evidence_commit
                    or physical.get("_process_returncode")!=0 or physical.get("engine_errors",[])!=[]
                    or any(line.lstrip().startswith(("ERROR:","SCRIPT ERROR:"))
                           for line in physical.get("_output_tail","").splitlines())):
                errors.append("physical traversal v117 PASS requires successful runtime evidence at the tested commit")

    well_tongs_path=ROOT/"data/tests/kg001_well_tongs_animation_runtime_v118.json"
    well_tongs_required=isinstance(runtime_status,dict) and "well_tongs_v118" in runtime_status
    if well_tongs_required:
        if not well_tongs_path.is_file():
            errors.append("well+tongs fresh-checkout PASS requires v118 runtime evidence")
        else:
            well_tongs=read_json("data/tests/kg001_well_tongs_animation_runtime_v118.json")
            if (well_tongs.get("status")!="PASS" or well_tongs.get("failed")!=[]
                    or well_tongs.get("schema")!="openazrael.kg001.well_tongs_animation"
                    or well_tongs.get("version")!=118 or well_tongs.get("_commit_sha")!=evidence_commit
                    or well_tongs.get("_process_returncode")!=0 or well_tongs.get("engine_errors",[])!=[]
                    or any(line.lstrip().startswith(("ERROR:","SCRIPT ERROR:"))
                           for line in well_tongs.get("_output_tail","").splitlines())):
                errors.append("well+tongs v118 PASS requires successful runtime evidence at the tested commit")

    r1_route_path=ROOT/"data/tests/kg001_r1_route_runtime_v119.json"
    r1_route_required=isinstance(runtime_status,dict) and "r1_route_v119" in runtime_status
    if r1_route_required:
        if not r1_route_path.is_file():
            errors.append("R1 route fresh-checkout PASS requires v119 runtime evidence")
        else:
            r1_route=read_json("data/tests/kg001_r1_route_runtime_v119.json")
            if (r1_route.get("status")!="PASS" or r1_route.get("failed")!=[]
                    or r1_route.get("schema")!="openazrael.kg001.r1_route"
                    or r1_route.get("version")!=119 or r1_route.get("_commit_sha")!=evidence_commit
                    or r1_route.get("_process_returncode")!=0 or r1_route.get("engine_errors",[])!=[]
                    or any(line.lstrip().startswith(("ERROR:","SCRIPT ERROR:"))
                           for line in r1_route.get("_output_tail","").splitlines())):
                errors.append("R1 route v119 PASS requires successful runtime evidence at the tested commit")

    source=read_json("data/tests/kg001_source_validation_v112.json")
    required={
        "validate_project_context.py","validate_demo_runtime_ir.py","audit_gameplay_event_graph_v87.py",
        "kg001_state_space_v108.py","validate_kg001_headless_v109.py","validate_kg001_room_trigger_v110.py",
        "validate_kg001_full_demo_v111.py","validate_candidate_diagnostics_v116.py",
        "validate_kg001_audio_runtime_v116.py","validate_kg001_texture_colorkey_v116.py",
    }
    if physical_required:
        required.add("validate_kg001_physical_traversal_v117.py")
    if well_tongs_required:
        required.add("validate_kg001_well_tongs_animation_v118.py")
    if r1_route_required:
        required.add("validate_kg001_r1_route_v119.py")
    commands=source.get("commands",[])
    passed={Path(arg).name for item in commands if item.get("status")=="PASS" and item.get("returncode")==0
            for arg in item.get("command",[])}
    if (source.get("status")!="PASS" or source.get("commit_sha")!=evidence_commit or not required.issubset(passed)
            or any(item.get("status")!="PASS" or item.get("returncode")!=0 for item in commands)):
        errors.append("runtime promotion requires successful source validators at the tested commit")
    marker="OPENAZRAEL_KG001_TEXTURE_COLORKEY_V116 "
    color_records=[json.loads(line.split(marker,1)[1]) for item in commands
                   if any(Path(arg).name=="validate_kg001_texture_colorkey_v116.py" for arg in item.get("command",[]))
                   for line in item.get("output","").splitlines() if line.startswith(marker)]
    expected=read_json("data/tests/kg001_texture_colorkey_contract_v116.json")["expected_demo_hash_textures"]
    if (len(color_records)!=1 or color_records[0].get("status")!="PASS"
            or color_records[0].get("failed")!=[] or color_records[0].get("asset_backed") is not True
            or color_records[0].get("selection_space")!="ORIGINAL_INDEXED_AZF"
            or {row.get("texture") for row in color_records[0].get("asset_rows",[])}!=set(expected)):
        errors.append("runtime promotion requires the restored texture corpus and GLB color-key checks")

for p in [
    "OPENAZRAEL_CONTEXT.md",
    "docs/PROJECT_STATE.md",
    "docs/LAST_SESSION.md",
    "docs/DECISIONS.md",
    "docs/BACKUP_VERSIONING_POLICY.md",
    "docs/GIT_BASELINE.md",
    "docs/KG001_ACCEPTANCE_PLAN.md",
    "data/project_context.json",
    "data/kg001_acceptance_contract.json",
    "data/gameplay_event_graph_v87.json",
    "data/xaf_trigger_evidence.json",
    "GAMEPLAY_EVENT_GRAPH_V87.md",
    "tools/validate_demo_runtime_ir.py",
    "tools/kg001_state_space_v108.py",
    "data/tests/kg001_state_space_v108.json",
    "docs/KG001_STATE_SPACE_V108.md",
    "scripts/kg001_headless_runner_v109.gd",
    "tools/validate_kg001_headless_v109.py",
    "data/tests/kg001_headless_contract_v109.json",
    "docs/KG001_HEADLESS_V109.md",
    "scripts/kg001_room_trigger_runner_v110.gd",
    "tools/validate_kg001_room_trigger_v110.py",
    "data/tests/kg001_room_trigger_contract_v110.json",
    "docs/KG001_ROOM_TRIGGER_V110.md",
    "scripts/kg001_physical_traversal_runner_v117.gd",
    "tools/validate_kg001_physical_traversal_v117.py",
    "data/tests/kg001_physical_traversal_contract_v117.json",
    "scripts/kg001_well_tongs_animation_runner_v118.gd",
    "tools/validate_kg001_well_tongs_animation_v118.py",
    "data/tests/kg001_well_tongs_animation_contract_v118.json",
    "data/tests/kg001_well_tongs_demo_evidence_v118.json",
    "scripts/kg001_r1_route_runner_v119.gd",
    "tools/validate_kg001_r1_route_v119.py",
    "data/tests/kg001_r1_route_contract_v119.json",
    "scripts/kg001_full_demo_runner_v111.gd",
    "tools/validate_kg001_full_demo_v111.py",
    "data/tests/kg001_full_demo_contract_v111.json",
    "tools/kg001_status_v111.py",
    "data/tests/kg001_status_v111.json",
    "docs/KG001_FULL_DEMO_V111.md",
    "docs/KG001_STATUS_V111.md",
    "tools/run_kg001_candidate_v112.py",
    "tools/validate_kg001_candidate_v112.py",
    "data/tests/kg001_candidate_runner_contract_v112.json",
    "tools/kg001_status_v112.py",
    "data/tests/kg001_status_v112.json",
    "docs/KG001_CANDIDATE_RUNNER_V112.md",
    "docs/KG001_MANUAL_SANITY_CHECKLIST.md",
    "data/tests/kg001_manual_sanity_template.json",
    "data/evidence/evidence_registry.json",
    "data/backup/source_fingerprints.json",
    "WORLD_RUNTIME_SERIALIZATION_V106.md",
    "WORLD_PUZZLE_SOUND_BRIDGE_V107.md",
    "docs/HISTORY_PRE_V116.md",
    "WORLD_SOUND_RECORD_FIELDS_V113.md",
    "tools/analyze_world_sound_record_fields_v113.py",
    "tools/validate_world_sound_record_fields_v113.py",
    "data/world_sound_record_fields_v113.json",
    "WORLD_SOUND_SERIALIZER_V114.md",
    "tools/analyze_world_sound_serializer_v114.py",
    "tools/validate_world_sound_serializer_v114.py",
    "data/world_sound_serializer_v114.json",
    "WORLD_ACTION_RECORD_LIFECYCLE_V115.md",
    "tools/analyze_world_action_lifecycle_v115.py",
    "tools/validate_world_action_lifecycle_v115.py",
    "data/world_action_lifecycle_v115.json",
    "docs/LOCALIZATION_ARCHITECTURE.md",
    "docs/KG001_CANDIDATE_DIAGNOSTICS_V116.md",
    "scripts/candidate_diagnostics_v116.gd",
    "scripts/kg001_trigger_debug_v116.gd",
    "tools/validate_candidate_diagnostics_v116.py",
    "data/tests/kg001_candidate_diagnostics_contract_v116.json",
    "scripts/kg001_audio_runtime_runner_v116.gd",
    "tools/validate_kg001_audio_runtime_v116.py",
    "data/tests/kg001_audio_runtime_contract_v116.json",
    "tools/texture_pipeline/legacy_colorkey.py",
    "tools/validate_kg001_texture_colorkey_v116.py",
    "tools/validate_public_release_safety.py",
    "data/tests/kg001_texture_colorkey_contract_v116.json",
    "data/tests/kg001_colorkey_corpus_audit_v116.json",
    "data/audio/legacy_world_ir.json",
    "tools/restore_candidate_assets.py",
    "tools/prepare_candidate_audio.py",
    "docs/BUG_REPORTING.md",
    "docs/PUBLIC_RELEASE_AUDIT.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
]:
    req(p)

try:
    c=json.loads((ROOT/"data/project_context.json").read_text(encoding="utf-8"))
    if c.get("checkpoint")!=EXPECTED_CHECKPOINT:
        errors.append("checkpoint drift")
    if c.get("current_forensics",{}).get("world_runtime_loader")!="VERIFIED":
        errors.append("WORLD loader status drift")
    if c.get("current_forensics",{}).get("puzzles_world_sound_exact_correspondence")!="VERIFIED":
        errors.append("v107 sound bridge status drift")
    if c.get("quality",{}).get("kg001_acceptance_plan")!="ACCEPTED":
        errors.append("KG-001 acceptance status drift")
    if c.get("quality",{}).get("kg001_state_model")!="SOURCE_MODEL_PASS":
        errors.append("KG-001 v108 state-model status drift")
    if c.get("quality",{}).get("kg001_headless_source_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 v109 headless source-contract drift")
    if c.get("quality",{}).get("kg001_headless_runtime") not in ("NOT_EXECUTED","PASS"):
        errors.append("KG-001 v109 runtime status drift")
    if c.get("quality",{}).get("kg001_room_trigger_source_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 v110 room/trigger source-contract drift")
    if c.get("quality",{}).get("kg001_room_trigger_runtime") not in ("NOT_EXECUTED","PASS"):
        errors.append("KG-001 v110 runtime status drift")
    if c.get("quality",{}).get("kg001_full_demo_source_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 v111 full-demo source-contract drift")
    if c.get("quality",{}).get("kg001_full_demo_runtime") not in ("NOT_EXECUTED","PASS"):
        errors.append("KG-001 v111 runtime status drift")
    if c.get("quality",{}).get("kg001_candidate_runner")!="SOURCE_CONTRACT_READY":
        errors.append("KG-001 v112 candidate runner drift")
    if c.get("quality",{}).get("kg001_status_engine")!="EVIDENCE_DRIVEN_V112":
        errors.append("KG-001 v112 status-engine drift")
    if c.get("quality",{}).get("kg001_overall_status") not in (
            "BLOCKED_ISSUES_6_9_11_RETEST",
            "BLOCKED_CANDIDATE2_CRITICAL_TRAVERSAL",
            "BLOCKED_CANDIDATE3_RUNTIME_RETEST",
            "BLOCKED_CANDIDATE3_CRITICAL_R1_OBJECT02",
        ):
        errors.append("KG-001 v112 overall status drift")
    if c.get("quality",{}).get("kg001_final_tag_allowed") is not False:
        errors.append("KG-001 tag unexpectedly allowed")
    if c.get("quality",{}).get("kg001_collision_issue_6") not in (
            "SOURCE_FIX_READY_MULTIROOM_RUNTIME_RETEST_REQUIRED",
            "AUTOMATED_PASS_MANUAL_RETEST_REQUIRED",
            "MANUAL_FAIL_CANDIDATE2",
            "SOURCE_FIX_READY_CANDIDATE3_RUNTIME_RETEST_REQUIRED",
            "SOURCE_FIX_READY_R1_OBJECT02_V119_RUNTIME_RETEST_REQUIRED",
        ):
        errors.append("KG-001 Issue #6 collision status drift")
    if c.get("quality",{}).get("kg001_release_blocked_by_issue_6") is not True:
        errors.append("KG-001 Issue #6 release blocker drift")
    if c.get("quality",{}).get("kg001_audio_issue_9") not in (
            "SOURCE_FIX_READY_RUNTIME_RETEST_REQUIRED",
            "AUTOMATED_PASS_MANUAL_RETEST_REQUIRED",
            "AMBIENT_AUDIBLE_TRIGGERED_EVENT_AUDIO_NOT_YET_MANUALLY_TESTED",
        ):
        errors.append("KG-001 Issue #9 audio status drift")
    if c.get("quality",{}).get("kg001_release_blocked_by_issue_9") is not True:
        errors.append("KG-001 Issue #9 release blocker drift")
    if c.get("quality",{}).get("kg001_physical_audio_source_contract")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 physical audio source-contract drift")
    if c.get("quality",{}).get("kg001_physical_audio_runtime") not in ("NOT_EXECUTED","PASS"):
        errors.append("KG-001 physical audio runtime status drift")
    if c.get("quality",{}).get("kg001_texture_issue_11") not in ("SOURCE_FIX_READY_AUDITED_SENTINEL_RUNTIME_RETEST_REQUIRED","AUTOMATED_PASS_MANUAL_RETEST_REQUIRED"):
        errors.append("KG-001 Issue #11 texture status drift")
    if c.get("quality",{}).get("kg001_release_blocked_by_issue_11") is not True:
        errors.append("KG-001 Issue #11 release blocker drift")
    if c.get("quality",{}).get("kg001_legacy_colorkey_source_contract")!="AUDITED_SOURCE_SENTINEL_CONTRACT_PASS":
        errors.append("KG-001 legacy color-key source-contract drift")
    if c.get("quality",{}).get("kg001_candidate_source_freeze") not in (
            "REFROZEN_V32_AFTER_EMPIRICAL_COLORKEY_AUDIT",
            "POST_CANDIDATE2_FIX_BRANCH_RUNTIME_RETEST_REQUIRED",
            "CANDIDATE3_SOURCE_HARDENED_RUNTIME_RETEST_REQUIRED",
            "POST_CANDIDATE3_OBJECT02_FIX_V119_RUNTIME_RETEST_REQUIRED",
        ):
        errors.append("KG-001 Candidate/source-freeze drift")
    if c.get("quality",{}).get("kg001_legacy_colorkey_runtime") not in ("NOT_EXECUTED","ASSET_VALIDATION_PASS_MANUAL_PENDING"):
        errors.append("KG-001 legacy color-key evidence boundary drift")
    if c.get("quality",{}).get("kg001_legacy_colorkey_expected_hash_textures")!=10:
        errors.append("KG-001 legacy color-key texture-class drift")
    if "COMPLETE_ORIGINAL_RENDERER_TRANSPARENCY_SEMANTICS" not in c.get("hard_holds",[]):
        errors.append("legacy transparency HOLD boundary missing")
    if c.get("quality",{}).get("kg001_candidate_build_runtime") not in (
            "V32_NOT_EXECUTED",
            "V32_AUTOMATED_PASS_MANUAL_PENDING",
            "V32_MANUAL_FAIL",
            "CANDIDATE3_NOT_EXECUTED",
            "CANDIDATE3_G10_FAIL_R1_OBJECT02",
        ):
        errors.append("KG-001 candidate runtime boundary drift")
    if c.get("quality",{}).get("kg001_stair_traversal") not in (None,"MANUAL_FAIL_CANDIDATE2","SOURCE_FIX_READY_CANDIDATE3_RUNTIME_RETEST_REQUIRED"):
        errors.append("KG-001 stair traversal status drift")
    if c.get("quality",{}).get("kg001_release_blocked_by_stair_traversal") not in (None,True):
        errors.append("KG-001 stair traversal release blocker drift")
    if c.get("quality",{}).get("kg001_physical_traversal_v117") not in (
            None,
            "SOURCE_CONTRACT_READY_RUNTIME_PENDING",
            "PASS",
        ):
        errors.append("KG-001 physical traversal v117 status drift")
    if c.get("quality",{}).get("kg001_r1_route_v119") not in (
            None,
            "SOURCE_CONTRACT_READY_RUNTIME_PENDING",
            "PASS",
        ):
        errors.append("KG-001 R1 route v119 status drift")
    if c.get("quality",{}).get("kg001_well_tongs_animation_v118") not in (
            None,
            "SOURCE_FIX_READY_EXACT_DEMO_ACTION_STREAM_RUNTIME_RETEST_REQUIRED",
            "PASS",
        ):
        errors.append("KG-001 well+tongs v118 status drift")
    if c.get("quality",{}).get("kg001_release_blocked_by_well_tongs_animation") not in (None,True):
        errors.append("KG-001 well+tongs release blocker drift")
    if c.get("quality",{}).get("documentation_consistency") not in (
            "PASS_V32",
            "PASS_POST_CANDIDATE2_FIX_BRANCH",
            "PASS_CANDIDATE3_HARDENED",
        ):
        errors.append("documentation consistency drift")
    if c.get("quality",{}).get("documentation_runtime_claim_boundary")!="NO_RUNTIME_PROMOTION":
        errors.append("documentation/runtime boundary drift")
    if c.get("quality",{}).get("kg001_bug_reporting")!="SOURCE_CONTRACT_PASS":
        errors.append("KG-001 bug-reporting source-contract drift")
    if c.get("quality",{}).get("kg001_candidate_debug_keys",{}).get("F11")!="bug_report_capture":
        errors.append("KG-001 F11 bug-report key drift")
    if c.get("quality",{}).get("kg001_bug_report_source_safe") is not True:
        errors.append("KG-001 bug-report source-safety drift")
    validate_runtime_evidence(c.get("quality",{}))
    manual_path=ROOT/"data/tests/kg001_manual_sanity.json"
    if manual_path.is_file() and json.loads(manual_path.read_text(encoding="utf-8")).get("status")=="PASS":
        errors.append("manual PASS conflicts with active release blockers; review G10 explicitly")
    loc=c.get("localization",{})
    if loc.get("status")!="ARCHITECTURE_APPROVED_IMPLEMENTATION_DEFERRED":
        errors.append("localization architecture status drift")
    if loc.get("key_strategy")!="STABLE_SEMANTIC_IDS":
        errors.append("localization key strategy drift")
    if loc.get("authoring_format")!="GETTEXT_POT_PO":
        errors.append("localization authoring-format drift")
    if loc.get("distribution_format")!="EXTERNAL_VERSIONED_PCK":
        errors.append("localization distribution-format drift")
    if loc.get("runtime_fallback")!="EN":
        errors.append("localization fallback drift")
    if loc.get("resource_pack_replace_core") is not False:
        errors.append("localization core-replacement safety drift")
except Exception as e:
    errors.append(f"context json: {e}")

try:
    # The source mirror retains compact summaries, not the full forensic
    # payload. This validates context integrity without rerunning that analysis.
    summary=(ROOT/"WORLD_RUNTIME_SERIALIZATION_V106.md").read_text(encoding="utf-8")
    forensic=c.get("current_forensics",{})
    if "96,425 / 96,425" not in summary or "[1303, 12, 37, 3, 101, 8, 15]" not in summary:
        errors.append("v106 tracked EOF/section-count summary missing")
    if forensic.get("world_exact_eof") is not True or forensic.get("world_section_counts")!=[1303,12,37,3,101,8,15]:
        errors.append("v106 machine-readable EOF/section-count evidence drift")
    if "## v105" not in (ROOT/"docs/HISTORY_PRE_V116.md").read_text(encoding="utf-8"):
        errors.append("v105 tracked summary missing")
except Exception as e:
    errors.append(f"v106 evidence json: {e}")

try:
    k=json.loads((ROOT/"data/kg001_acceptance_contract.json").read_text(encoding="utf-8"))
    if k.get("target_tag")!="demo-known-good-001":
        errors.append("KG-001 target tag drift")
    gates=k.get("gates",[])
    if [g.get("id") for g in gates] != [f"G{i:02d}" for i in range(11)]:
        errors.append("KG-001 gate set drift")
    if not all(g.get("required") is True for g in gates):
        errors.append("KG-001 required-gate drift")
except Exception as e:
    errors.append(f"KG-001 contract: {e}")

try:
    t=json.loads((ROOT/"data/tests/kg001_texture_colorkey_contract_v116.json").read_text(encoding="utf-8"))
    expected=t.get("expected_demo_hash_textures",[])
    if t.get("status")!="SOURCE_CONTRACT_PASS" or len(expected)!=10:
        errors.append("KG-001 texture color-key contract drift")
    policy=t.get("policy",{})
    if policy.get("runtime_material")!="MASK" or policy.get("alpha_cutoff")!=0.5:
        errors.append("KG-001 texture material policy drift")
    if t.get("evidence_boundary","").find("HOLD")<0:
        errors.append("KG-001 texture evidence boundary drift")
except Exception as e:
    errors.append(f"KG-001 texture contract: {e}")

gitignore=(ROOT/".gitignore").read_text(encoding="utf-8")
for marker in [
    "data/audio/original_audio/",
    "data/*.DAT",
    "assets/audio/",
    "assets/rooms/",
    "assets/textures/classic/",
    "data/*.textured.v44.manifest.json",
    "data/audio/*.legacy.json",
    "data/graphics_pipeline_validation_v44.json",
]:
    if marker not in gitignore:
        errors.append(f"gitignore safety missing: {marker}")

if errors:
    print("OpenAzrael context validation: FAIL")
    for x in errors:
        print(" -",x)
    sys.exit(1)

print("OpenAzrael context validation: PASS")
print(" checkpoint:",EXPECTED_CHECKPOINT)
print(" KG-001 contract: ACCEPTED")
