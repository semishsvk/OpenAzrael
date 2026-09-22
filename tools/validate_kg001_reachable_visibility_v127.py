#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
gen=(ROOT/"tools/kg001_state_matrix_v127.py").read_text(encoding="utf-8")
runner=(ROOT/"scripts/kg001_reachable_visibility_runner_v127.gd").read_text(encoding="utf-8")
contract=json.loads((ROOT/"data/tests/kg001_reachable_visibility_contract_v127.json").read_text(encoding="utf-8"))
checks={
 "schema":contract.get("schema")=="openazrael.kg001.reachable_visibility_contract" and contract.get("version")==127,
 "state_count":contract.get("expected_reachable_states")==104 and "len(records)!=104" in gen,
 "uses_v108":"from kg001_state_space_v108 import Model, explore" in gen,
 "canonical_restore":"restore_canonical_state_payload" in runner and "canonical_state_hash" in runner,
 "no_direct_mutation":all(x not in runner for x in ("set_flag(","set_puzzle_node(","acquire(","remove(")),
 "visibility_oracle":"expected_visibility" in gen and 'record["expected_visibility"]' in runner,
 "marker":"OPENAZRAEL_KG001_REACHABLE_VISIBILITY_V127" in runner,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.reachable_visibility_contract_validation","version":127,"status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","runtime_status":"NOT_EXECUTED","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
