#!/usr/bin/env python3
"""Canonical KG-001 gate declarations shared by runners, preflights and validators.

Keep executable behavior in the owning runner.  This module only declares the
ordered gate identities/commands that define the current source and runtime
contracts so machine-readable contracts cannot silently drift from execution.
"""
from __future__ import annotations

import sys

SOURCE_COMMANDS = [
    [sys.executable, "tools/validate_public_release_safety.py"],
    [sys.executable, "tools/validate_source_geometry_policy.py"],
    [sys.executable, "tools/validate_project_context.py"],
    [sys.executable, "-m", "tools.remaster_framework.cli", "validate"],
    [sys.executable, "-m", "unittest", "discover", "-s", "tools/remaster_framework/tests", "-v"],
    [sys.executable, "-m", "tools.openazrael_adapters.runtime_capabilities", ".", "--require-core"],
    [sys.executable, "tools/validate_demo_runtime_ir.py"],
    [sys.executable, "tools/audit_gameplay_event_graph_v87.py", "--source-only"],
    [sys.executable, "tools/kg001_state_space_v108.py"],
    [sys.executable, "tools/validate_kg001_headless_v109.py"],
    [sys.executable, "tools/validate_kg001_room_trigger_v110.py"],
    [sys.executable, "tools/validate_kg001_trigger_events_v137.py"],
    [sys.executable, "tools/validate_kg001_character_animation_v138.py"],
    [sys.executable, "tools/validate_kg001_trigger_action_census_v142.py"],
    [sys.executable, "tools/validate_localization_v139.py"],
    [sys.executable, "tools/validate_kg001_full_demo_v111.py"],
    [sys.executable, "tools/validate_candidate_diagnostics_v116.py"],
    [sys.executable, "tools/validate_kg001_audio_runtime_v116.py"],
    [sys.executable, "tools/validate_kg001_texture_colorkey_v116.py"],
    [sys.executable, "tools/validate_kg001_physical_traversal_v117.py"],
    [sys.executable, "tools/validate_kg001_well_tongs_animation_v118.py"],
    [sys.executable, "tools/validate_kg001_r1_route_v119.py"],
    [sys.executable, "tools/validate_kg001_collision_parity_v120.py"],
    [sys.executable, "tools/validate_kg001_surface_collision_v121.py"],
    [sys.executable, "tools/validate_kg001_geometry_render_parity_v122.py"],
    [sys.executable, "tools/validate_kg001_object_visibility_v123.py"],
    [sys.executable, "tools/validate_kg001_material_texture_v124.py"],
    [sys.executable, "tools/validate_kg001_transform_parity_v125.py"],
    [sys.executable, "tools/validate_kg001_visual_census_v126.py"],
    [sys.executable, "tools/validate_kg001_reachable_visibility_v127.py"],
    [sys.executable, "tools/validate_kg001_packaged_parity_v128.py"],
    [sys.executable, "tools/validate_kg001_portal_geometry_v129.py"],
    [sys.executable, "tools/validate_kg001_interaction_reachability_v130.py"],
    [sys.executable, "tools/validate_kg001_room_forensic_report_v131.py"],
    [sys.executable, "tools/validate_kg001_texture_orientation_v133.py"],
    [sys.executable, "tools/validate_kg001_demo_connectivity_v140.py"],
    [sys.executable, "tools/validate_kg001_all_transition_v141.py"],
    [sys.executable, "tools/validate_kg001_interaction_cursors_v143.py"],
    [sys.executable, "tools/validate_menu_lab_v144.py"],
    [sys.executable, "tools/validate_kg001_legacy_menu_runtime_v145.py"],
    [sys.executable, "tools/validate_kg001_legacy_scanner_v164.py"],
    [sys.executable, "tools/validate_kg001_menu_cursor_context_v146.py"],
    [sys.executable, "tools/validate_kg001_classic_presentation_v147.py"],
    [sys.executable, "tools/validate_interaction_probe_determinism_v148.py"],
    [sys.executable, "tools/validate_kg001_legacy_menu_toggle_v149.py"],
    [sys.executable, "tools/validate_kg001_save_compat_v150.py"],
    [sys.executable, "tools/validate_kg001_inventory_hud_v157.py"],
    [sys.executable, "tools/validate_release_docs.py"],
    [sys.executable, "tools/validate_verify_release_orchestrator.py"],
    [sys.executable, "tools/validate_candidate3_preflight.py"],
    [sys.executable, "tools/validate_candidate3_pppv_integration.py"],
]

RUNTIMES = [
    ("v109", "scripts/kg001_headless_runner_v109.gd", "OPENAZRAEL_KG001_V109"),
    ("v110", "scripts/kg001_room_trigger_runner_v110.gd", "OPENAZRAEL_KG001_V110"),
    ("trigger_v137", "scripts/kg001_trigger_event_runner_v137.gd", "OPENAZRAEL_KG001_V137"),
    ("localization_v139", "scripts/localization_runtime_runner_v139.gd", "OPENAZRAEL_LOCALIZATION_V139"),
    ("v111", "scripts/kg001_full_demo_runner_v111.gd", "OPENAZRAEL_KG001_V111"),
    ("audio_v116", "scripts/kg001_audio_runtime_runner_v116.gd", "OPENAZRAEL_KG001_AUDIO_V116"),
    ("physical_v117", "scripts/kg001_physical_traversal_runner_v117.gd", "OPENAZRAEL_KG001_PHYSICAL_V117"),
    ("well_tongs_v118", "scripts/kg001_well_tongs_animation_runner_v118.gd", "OPENAZRAEL_KG001_WELL_TONGS_V118"),
    ("r1_route_v119", "scripts/kg001_r1_route_runner_v119.gd", "OPENAZRAEL_KG001_R1_ROUTE_V119"),
    ("collision_v120", "scripts/kg001_collision_parity_runner_v120.gd", "OPENAZRAEL_KG001_COLLISION_PARITY_V120"),
    ("surface_v121", "scripts/kg001_surface_collision_runner_v121.gd", "OPENAZRAEL_KG001_SURFACE_COLLISION_V121"),
    ("geometry_v122", "scripts/kg001_geometry_render_parity_runner_v122.gd", "OPENAZRAEL_KG001_GEOMETRY_RENDER_PARITY_V122"),
    ("visibility_v123", "scripts/kg001_object_visibility_runner_v123.gd", "OPENAZRAEL_KG001_OBJECT_VISIBILITY_V123"),
    ("material_v124", "scripts/kg001_material_texture_runner_v124.gd", "OPENAZRAEL_KG001_MATERIAL_TEXTURE_V124"),
    ("transform_v125", "scripts/kg001_transform_parity_runner_v125.gd", "OPENAZRAEL_KG001_TRANSFORM_V125"),
    ("reachable_visibility_v127", "scripts/kg001_reachable_visibility_runner_v127.gd", "OPENAZRAEL_KG001_REACHABLE_VISIBILITY_V127"),
    ("portal_v129", "scripts/kg001_portal_geometry_runner_v129.gd", "OPENAZRAEL_KG001_PORTAL_GEOMETRY_V129"),
    ("interaction_v130", "scripts/kg001_interaction_reachability_runner_v130.gd", "OPENAZRAEL_KG001_INTERACTION_REACHABILITY_V130"),
    ("all_transitions_v141", "scripts/kg001_all_transition_runner_v141.gd", "OPENAZRAEL_KG001_ALL_TRANSITIONS_V141"),
    ("cursor_v143", "scripts/kg001_interaction_cursor_runner_v143.gd", "OPENAZRAEL_KG001_CURSOR_V143"),
    ("menu_v145", "scripts/kg001_legacy_menu_runner_v145.gd", "OPENAZRAEL_KG001_MENU_V145"),
    ("legacy_scanner_v164", "scripts/kg001_legacy_scanner_runner_v164.gd", "OPENAZRAEL_KG001_LEGACY_SCANNER_V164"),
    ("menu_cursor_v146", "scripts/kg001_menu_cursor_context_runner_v146.gd", "OPENAZRAEL_KG001_MENU_CURSOR_V146"),
    ("classic_v147", "scripts/kg001_classic_presentation_runner_v147.gd", "OPENAZRAEL_KG001_CLASSIC_PRESENTATION_V147"),
    ("interaction_probe_v148", "scripts/kg001_interaction_probe_determinism_runner_v148.gd", "OPENAZRAEL_KG001_INTERACTION_PROBE_DETERMINISM_V148"),
    ("menu_toggle_v149", "scripts/kg001_legacy_menu_toggle_runner_v149.gd", "OPENAZRAEL_KG001_MENU_TOGGLE_V149"),
    ("save_compat_v150", "scripts/kg001_save_compat_runner_v150.gd", "OPENAZRAEL_KG001_SAVE_COMPAT_V150"),
    ("inventory_hud_v157", "scripts/kg001_inventory_hud_runner_v157.gd", "OPENAZRAEL_KG001_INVENTORY_HUD_V157"),
]

CANDIDATE3_REQUIRED_RUNTIME = tuple(name for name, _script, _marker in RUNTIMES)
CANDIDATE3_ADDITIONAL_RUNTIME_EVIDENCE = ("visual_v126", "room_forensic_v131")

PPPV_EVIDENCE_FILES = {
    "scenario_suite": ".tmp/kg001_pppv_v2/kg001_pppv_scenario_suite.json",
    "scenario_suite_integrity": ".tmp/kg001_pppv_v2/pppv_scenario_suite_integrity.json",
    "playthrough_evaluation": ".tmp/kg001_pppv_v2/kg001_pppv_playthrough_evaluation.json",
    "determinism": ".tmp/kg001_pppv_v2/kg001_pppv_determinism.json",
    "determinism_integrity": ".tmp/kg001_pppv_v2/pppv_determinism_integrity.json",
}
PPPV_REQUIRED_EVIDENCE = tuple(PPPV_EVIDENCE_FILES)

CANDIDATE4_SOURCE_VALIDATORS = (
    "tools/test_rejection_export_v165.py",
    "tools/validate_kg001_trigger_events_v137.py",
    "tools/validate_candidate4_release_contract_v132.py",
    "tools/validate_candidate4_music_route_v133.py",
    "tools/validate_xmi_to_midi_v134.py",
    "tools/validate_candidate4_music_renderer_v135.py",
)

CANDIDATE4_REQUIRED_PREFLIGHT = (
    *CANDIDATE3_REQUIRED_RUNTIME,
    *CANDIDATE3_ADDITIONAL_RUNTIME_EVIDENCE,
    *(f"pppv_v2:{name}" for name in PPPV_REQUIRED_EVIDENCE),
    "candidate4_music_route_v133",
    "candidate4_music_render_v135",
    "candidate4_music_godot_v136",
    "candidate4_audio_v132",
)
