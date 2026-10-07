from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1]
s=json.loads((root/"data/tests/kg001_niamh_conversation_fidelity_status_v280.json").read_text())
ir=json.loads((root/"data/runtime_generated/niamh_conversation_ir_v209.json").read_text())
# Filename is legacy; content version 253 is the canonical ATDEMO-only parse.
fam=ir["families"]["1A"]["records"]
ids=[str(x["id"]) for x in fam]
visible=[str(x["id"]) for x in fam if str(x.get("player_text","")).strip()!="DO NOT DISPLAY"]
retail_only={"28","29","31","32","33","34","35","36"}
checks={
 "demo_source_bound":ir["source"]["sha256"]==s["source"]["sha256"] and ir["source"]["bytes"]==342,
 "demo_1A_exact":ids==["30","999","A"],
 "demo_visible_exact":visible==["30","999"],
 "hidden_A":next(x for x in fam if str(x["id"])=="A").get("player_text")=="DO NOT DISPLAY" and ir.get("policy",{}).get("do_not_display_hidden_records") is True,
 "retail_expansion_absent":not(retail_only & set(ids)),
 "exit_999_present":"999" in visible,
 "status_fail_closed":s["status"]=="PARTIAL_VERIFIED_DEMO_ONLY",
}
bad=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.niamh_demo_authority_gate","version":280,"status":"PASS" if not bad else "FAIL","checks":checks,"failed":bad}))
raise SystemExit(0 if not bad else 1)
