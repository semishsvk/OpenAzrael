from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
s=json.loads((root/"data/tests/kg001_niamh_conversation_fidelity_status_v210.json").read_text())
ir=json.loads((root/"data/runtime_generated/niamh_conversation_ir_v209.json").read_text())
checks={
"status_not_false_verified":s["status"]=="PARTIAL_VERIFIED",
"source_hash_bound":ir["source"]["sha256"]==s["source"]["sha256"],
"source_size_bound":ir["source"]["bytes"]==s["source"]["bytes"],
"holds_flag_semantics":all(x in s["hold"] for x in ["typed prerequisite flag semantics","typed action flag semantics"]),
"canonical_exe_distinct":s["evidence"]["canonical_r_exe_required_sha256"]!=s["evidence"]["currently_available_r_exe_sha256"],
"1A_source_complete":len(ir["families"]["1A"]["records"])==11,
"1B_source_complete":len(ir["families"]["1B"]["records"])==36,
}
bad=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.niamh_fidelity_gate","version":210,"status":"PASS" if not bad else "FAIL","checks":checks,"failed":bad}))
raise SystemExit(0 if not bad else 1)
