extends RefCounted
class_name BugReportFrameworkContext

const SCHEMA := "remaster.bug_report_framework_context"
const VERSION := 1
const MAX_CONTEXT_BYTES := 2 * 1024 * 1024

const OPTIONAL_ARTIFACTS := [
    {
        "id": "build_provenance",
        "path": "res://data/runtime/build_provenance.json",
        "schema": "remaster.build_provenance",
        "zip_name": "build_provenance.json"
    },
    {
        "id": "release_gate_summary",
        "path": "res://data/runtime/release_gate_summary.json",
        "schema": "remaster.release_gate_summary",
        "zip_name": "release_gate_summary.json"
    },
    {
        "id": "pppv_coverage",
        "path": "res://data/runtime/pppv_coverage.json",
        "schema": "remaster.validation_coverage",
        "zip_name": "pppv_coverage.json"
    },
    {
        "id": "pppv_playthrough_evaluation",
        "path": "res://data/runtime/pppv_playthrough_evaluation.json",
        "schema": "remaster.playthrough_evaluation",
        "zip_name": "pppv_playthrough_evaluation.json"
    }
]

func _sha256_text(value: String) -> String:
    var context := HashingContext.new()
    context.start(HashingContext.HASH_SHA256)
    context.update(value.to_utf8_buffer())
    return context.finish().hex_encode()

func _summary_fields(artifact_id: String, payload: Dictionary) -> Dictionary:
    match artifact_id:
        "build_provenance":
            return {
                "commit_sha": String(payload.get("commit_sha", "")),
                "project_version": String(payload.get("project_version", "")),
                "provenance_sha256": String(payload.get("provenance_sha256", ""))
            }
        "release_gate_summary":
            return {
                "status": String(payload.get("status", "")),
                "target_tag": String(payload.get("target_tag", "")),
                "summary_sha256": String(payload.get("summary_sha256", ""))
            }
        "pppv_coverage":
            return {
                "status": String(payload.get("status", "")),
                "required_target_count": int(payload.get("required_target_count", 0)),
                "covered_target_count": int(payload.get("covered_target_count", 0)),
                "coverage_ratio": float(payload.get("coverage_ratio", 0.0))
            }
        "pppv_playthrough_evaluation":
            return {
                "status": String(payload.get("status", "")),
                "plan_id": String(payload.get("plan_id", "")),
                "step_count": int(payload.get("step_count", 0)),
                "final_state_sha256": String(
                    payload.get("final_state_sha256", "")
                )
            }
    return {}

func _read_artifact(spec: Dictionary) -> Dictionary:
    var artifact_id := String(spec.get("id", ""))
    var path := String(spec.get("path", ""))
    var expected_schema := String(spec.get("schema", ""))
    var zip_name := String(spec.get("zip_name", ""))

    var result := {
        "id": artifact_id,
        "path": path,
        "zip_name": zip_name,
        "expected_schema": expected_schema,
        "available": false,
        "included": false,
        "reason": "missing"
    }

    if not FileAccess.file_exists(path):
        return result

    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        result["reason"] = "unreadable"
        return result

    var byte_count := file.get_length()
    if byte_count > MAX_CONTEXT_BYTES:
        result["reason"] = "too_large"
        result["byte_count"] = byte_count
        file.close()
        return result

    var text := file.get_as_text()
    file.close()
    var parsed = JSON.parse_string(text)
    if not parsed is Dictionary:
        result["reason"] = "invalid_json"
        return result
    if String(parsed.get("schema", "")) != expected_schema:
        result["reason"] = "schema_mismatch"
        result["actual_schema"] = String(parsed.get("schema", ""))
        return result

    result["available"] = true
    result["included"] = true
    result["reason"] = "included"
    result["byte_count"] = text.to_utf8_buffer().size()
    result["sha256"] = _sha256_text(text)
    result["schema"] = expected_schema
    result["summary"] = _summary_fields(artifact_id, parsed)
    result["text"] = text
    return result

func collect() -> Dictionary:
    var artifacts: Array[Dictionary] = []
    var entries: Array[Dictionary] = []
    for spec in OPTIONAL_ARTIFACTS:
        var item := _read_artifact(spec)
        var public_item := item.duplicate(true)
        public_item.erase("text")
        artifacts.append(public_item)
        if bool(item.get("included", false)):
            entries.append({
                "zip_name": String(item.get("zip_name", "")),
                "text": String(item.get("text", "")),
                "sha256": String(item.get("sha256", "")),
                "schema": String(item.get("schema", ""))
            })

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "artifacts": artifacts,
        "entries": entries,
        "source_safe": true,
        "commercial_assets_included": false
    }
