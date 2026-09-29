extends SceneTree

const IDENTITY := "res://data/runtime_build_identity.json"

func _initialize() -> void:
    var failures: Array[String] = []
    if OS.has_feature("editor"):
        failures.append("EDITOR_FEATURE_PRESENT")
    if not OS.has_feature("kg001_candidate4"):
        failures.append("CANDIDATE4_FEATURE_MISSING")
    if not FileAccess.file_exists(IDENTITY):
        failures.append("RUNTIME_BUILD_IDENTITY_MISSING")
    var identity = {}
    if failures.is_empty():
        identity = JSON.parse_string(FileAccess.get_file_as_string(IDENTITY))
        if not identity is Dictionary:
            failures.append("RUNTIME_BUILD_IDENTITY_INVALID")
        else:
            if String(identity.get("candidate","")) != "KG-001 Candidate 4":
                failures.append("CANDIDATE_IDENTITY_MISMATCH")
            if String(identity.get("preset","")) != "Windows Candidate 4":
                failures.append("PRESET_IDENTITY_MISMATCH")
            if String(identity.get("commit_sha","")).length() != 40:
                failures.append("COMMIT_IDENTITY_INVALID")
    var out := {
        "schema":"openazrael.kg001.packaged_origin",
        "version":178,
        "status":"PASS" if failures.is_empty() else "FAIL",
        "failed":failures,
        "editor_feature":OS.has_feature("editor"),
        "candidate4_feature":OS.has_feature("kg001_candidate4"),
        "identity":identity,
        "execution_boundary":"exported executable resource pack",
    }
    print("OPENAZRAEL_KG001_PACKAGED_ORIGIN_V178 " + JSON.stringify(out))
    quit(0 if failures.is_empty() else 1)
