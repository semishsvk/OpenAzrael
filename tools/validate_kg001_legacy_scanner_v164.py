#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/ui/legacy_scanner_manifest_v164.json"
RESTORE = ROOT / "tools/restore_legacy_scanner_v164.py"
RUNTIME = ROOT / "scripts/legacy_scanner_runtime_v164.gd"
MENU = ROOT / "scripts/legacy_menu_runtime_v145.gd"
BOOTSTRAP = ROOT / "tools/restore_candidate_assets.py"


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    restore = RESTORE.read_text(encoding="utf-8")
    runtime = RUNTIME.read_text(encoding="utf-8")
    menu = MENU.read_text(encoding="utf-8")
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    failed: list[str] = []

    def check(name: str, ok: bool) -> None:
        if not ok:
            failed.append(name)

    check("manifest_schema", manifest.get("schema") == "openazrael.legacy_scanner.source_manifest" and manifest.get("version") == 164)
    check("source_fingerprints", all(len(str(spec.get("sha256", ""))) == 64 for spec in manifest.get("files", {}).values()))
    check("boot_message_ids", manifest.get("boot_message_ids") == list(range(3, 16)))
    bindings = manifest.get("demo_room_message_binding", {})
    check("demo_room_bindings", {key: int(value["hud_message_id"]) for key, value in bindings.items()} == {"R1": 87, "R7": 101, "R8": 97})
    check("audio_event_timing_only", "SOURCE_AUDIO_EVENT_BOUNDARIES_ONLY_NO_GUESSED_PER_LINE_OR_PER_CHARACTER_TIMING" in json.dumps(manifest))
    check("scanner_upper_right", manifest["presentation"]["upper_right_readout_rect"] == [452, 54, 172, 246])
    check("rect_provenance_honest", "NOT_CLAIMED_PIXEL_EXACT" in manifest["presentation"]["rect_provenance"])
    check("evidence_boundary_present", "per-line/per-character boot timing" in manifest.get("evidence_boundary", {}).get("unresolved_exactness", []))
    check("no_unproven_resource_substitution", "REPLAY0-7.PCX" in manifest.get("evidence_boundary", {}).get("explicit_non_substitutions", []) and "RANIM0-4.ANM" in manifest.get("evidence_boundary", {}).get("explicit_non_substitutions", []))
    check("restore_exact_hudmes_parser", 'struct.unpack_from("<I"' in restore and 'struct.unpack_from("<H"' in restore and 'table_offset + index * entry_size' in restore)
    check("restore_source_audio", 'HUD3.WAV' in restore and 'SCAN.WAV' in restore and 'shutil.copyfile' in restore)
    check("restore_gold_font", 'RUSGLD2.PCX' in restore and 'PALETTE_INDEX' not in restore and 'rgba.putalpha' in restore)
    check("runtime_source_font", 'RUSGLD2.png' in runtime and 'FONT_CELL := Vector2(10, 12)' in runtime)
    check("runtime_source_audio", 'HUD3.wav' not in runtime and '_audio_stream("hud_boot")' not in runtime)
    # Paths come from restored source JSON, not hard-coded replacement media.
    check("runtime_audio_from_source_json", '_audio_stream(kind' in runtime and 'source.get("audio"' in runtime)
    check("room_changed_hook", 'room_manager.connect("room_changed", callback)' in runtime)
    check("boot_on_title_dismiss", 'scanner_runtime.start_boot_sequence()' in menu)
    check("candidate_restore_wired", 'restore_legacy_scanner_v164.py' in bootstrap)
    check("no_gameplay_mutation", all(token not in runtime for token in ('player.global_position =', 'player.rotation.y =', 'player.velocity =', 'load_room_at_portal(', '_transition_room_through_portal(')))
    check("no_ai_or_synthetic_wire", 'image_gen' not in runtime.lower() and 'EUGENE' not in runtime and 'EUGENB' not in runtime)
    check("headless_nonblocking", 'DisplayServer.get_name() == "headless"' in runtime and '_show_environment_result(room_id)' in runtime)
    check("source_scan_boundary", 'await audio_player.finished' in runtime and '_set_display("environment_scan", _scan_status()' in runtime and '_show_environment_result(room_id)' in runtime)
    check("boot_preserves_source_indentation", 'var text := String(row.get("text", ""))' in runtime and 'text.strip_edges().is_empty()' in runtime)

    payload = {
        "schema": "openazrael.kg001.legacy_scanner_source_validation",
        "version": 164,
        "status": "PASS" if not failed else "FAIL",
        "failed": failed,
    }
    print(json.dumps(payload, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
