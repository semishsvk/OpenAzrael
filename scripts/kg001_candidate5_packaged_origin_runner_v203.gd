extends SceneTree
const IDENTITY := "res://data/runtime_build_identity.json"
func _initialize() -> void:
 var failures:Array[String]=[]
 if OS.has_feature("editor"): failures.append("EDITOR_FEATURE_PRESENT")
 if not OS.has_feature("kg001_candidate5"): failures.append("CANDIDATE5_FEATURE_MISSING")
 if not FileAccess.file_exists(IDENTITY): failures.append("RUNTIME_BUILD_IDENTITY_MISSING")
 var identity={}
 if failures.is_empty():
  identity=JSON.parse_string(FileAccess.get_file_as_string(IDENTITY))
  if not identity is Dictionary: failures.append("RUNTIME_BUILD_IDENTITY_INVALID")
  else:
   if String(identity.get("candidate",""))!="KG-001 Candidate 5": failures.append("CANDIDATE_IDENTITY_MISMATCH")
   if String(identity.get("preset",""))!="Windows Candidate 5": failures.append("PRESET_IDENTITY_MISMATCH")
   if String(identity.get("commit_sha","")).length()!=40: failures.append("COMMIT_IDENTITY_INVALID")
 var out={"schema":"openazrael.kg001.candidate5_packaged_origin","version":203,"status":"PASS" if failures.is_empty() else "FAIL","failed":failures,"identity":identity,"execution_boundary":"exported executable resource pack"}
 print("OPENAZRAEL_KG001_C5_PACKAGED_ORIGIN_V203 "+JSON.stringify(out)); quit(0 if failures.is_empty() else 1)
