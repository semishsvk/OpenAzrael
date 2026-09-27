#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_save_compat_contract_v150.json").read_text(encoding="utf-8"))
save=(ROOT/"scripts/legacy_save_system_v145.gd").read_text(encoding="utf-8")
runner=(ROOT/"scripts/kg001_save_compat_runner_v150.gd").read_text(encoding="utf-8")
checks={
    "schema":contract.get("schema")=="openazrael.kg001.save_compat_contract" and contract.get("version")==150,
    "current_save_identity":contract.get("save_schema")=="openazrael.demo_save" and contract.get("save_version")==145,
    "filename_unchanged":contract.get("filename_pattern")=="SAVE%d.dat" and '"user://SAVE%d.dat"' in save,
    "slot_names_unchanged":contract.get("slot_names")==["FILE ALPHA","FILE BETA","FILE GAMMA","FILE DELTA","FILE EPSILON"],
    "exact_version_guard":all(token in save for token in (
        '"UNSUPPORTED_SAVE_VERSION"','observed_version != VERSION','"migration_available": false'
    )),
    "schema_guard":'"INCOMPATIBLE_SCHEMA"' in save and 'String(parsed.get("schema", "")) != SCHEMA' in save,
    "json_guard": all(token in save for token in (
        '"INVALID_JSON_OR_ROOT_TYPE"', 'var parser := JSON.new()',
        'parser.parse(FileAccess.get_file_as_string(path)) != OK', 'var parsed = parser.data'
    )),
    "state_guard":'"INCOMPATIBLE_STATE_PAYLOAD"' in save and "restore_canonical_state_payload" in save,
    "diagnostic_rejection":'"legacy_menu_load_rejected"' in save and "_reject_load" in save,
    "current_roundtrip":all(token in runner for token in (
        "current_save_write","current_save_load","current_state_restored","current_room_restored",
        "current_position_restored","current_yaw_restored","current_pitch_restored"
    )),
    "negative_cases":all(token in runner for token in (
        "older_version","unknown_version","corrupt_json","wrong_schema","incompatible_state_payload"
    )),
    "rejections_preserve_live_state":all(token in runner for token in (
        "state_unchanged","room_unchanged","position_unchanged"
    )),
    "no_migration_claim":contract.get("migration_available") is False and '"migration_available": false' in save,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
    "schema":"openazrael.kg001.save_compat_validation",
    "version":150,
    "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "checks":checks,
    "failed":failed,
},indent=2))
sys.exit(1 if failed else 0)
