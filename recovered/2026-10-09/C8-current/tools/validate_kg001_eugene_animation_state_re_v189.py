#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
c=json.loads((ROOT/"data/tests/kg001_eugene_animation_state_re_contract_v189.json").read_text())
checks={
"contract":c.get("version")==189 and c.get("status")=="EXECUTABLE_STRUCTURE_VERIFIED",
"record_size":c["animation_table"]["record_size_bytes"]==19,
"selector":c["animation_table"]["selector_function"]=="0x8393C",
"runtime_pointer":c["character_state"]["animation_runtime_pointer"]=="0x25C",
"clock_hold":c["clock"]["status"]=="HOLD_SOURCE_CLOCK_PROOF",
"speed_separation":any("SPEED" in x for x in c["negative_proof"])
}
bad=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.eugene_animation_state_re_validation","version":189,"status":"STRUCTURAL_PASS" if not bad else "FAIL","checks":checks,"failed":bad,"runtime_status":"NOT_EXECUTED"},indent=2))
sys.exit(1 if bad else 0)
