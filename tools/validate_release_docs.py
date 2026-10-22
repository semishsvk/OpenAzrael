#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
project=(ROOT/"docs/PROJECT_STATE.md").read_text(encoding="utf-8")
last=(ROOT/"docs/LAST_SESSION.md").read_text(encoding="utf-8")
matrix=(ROOT/"docs/TEST_MATRIX.md").read_text(encoding="utf-8")
criteria=(ROOT/"docs/CANDIDATE4_RELEASE_CRITERIA.md").read_text(encoding="utf-8")
baseline=(ROOT/"docs/GIT_BASELINE.md").read_text(encoding="utf-8")
frozen=(ROOT/"docs/CANDIDATE4_FROZEN_RELEASE.md").read_text(encoding="utf-8")
orchestrator=(ROOT/"docs/VERIFY_RELEASE_ORCHESTRATOR.md").read_text(encoding="utf-8")
c3=json.loads((ROOT/"data/tests/kg001_candidate3_preflight_contract_v1.json").read_text(encoding="utf-8"))
c4=json.loads((ROOT/"data/tests/kg001_candidate4_release_contract_v132.json").read_text(encoding="utf-8"))
stale="Source CI remains UNOBSERVED"
checks={
    "no_stale_unobserved_claim":all(stale not in text for text in (project,last,matrix)),
    "evidence_tiers":all(token in project for token in ("SOURCE CONTRACT","ASSET-BACKED RUNTIME","PACKAGED / EXPORT","MANUAL G10")),
    "known_good_not_claimed":"Known Good: **NO**" in project and "NOT Known Good" in last,
    "recent_source_ci_observation":"34d5b2077079854c52bac8d8071c98fd40748f3d" in project and "34d5b2077079854c52bac8d8071c98fd40748f3d" in last,
    "new_runtime_layers":all(token in matrix for token in ("v148","v149","v150")),
    "music_boundary":all(token in criteria for token in ("cross-platform bit-identical PCM","cross-platform bit-identical OGG")),
    "freeze_documented":"freeze_candidate4_release.py" in criteria and "freeze_candidate4_release.py" in frozen,
    "verify_orchestrator_documented":(
        "run_verify_release_orchestrator.py" in project
        and "LOCAL_VERIFY_PASS_CI_CONFIRMATION_REQUIRED" in project
        and "SOURCE_CHECKPOINT_READY_FOR_ASSET_PREFLIGHT" in project
        and "FAST" in orchestrator
        and "VERIFY" in orchestrator
    ),
    "git_baseline_current":"integration/kg001-candidate3-pppv-v2" in baseline and "v106-context-v12" not in baseline,
    "contract_freeze_required":c4.get("frozen_release",{}).get("required") is True,
    "contract_manifest_exact":c3.get("local_preflight",{}).get("contract_runner_consistency")=="EXACT_ORDERED_MATCH_REQUIRED" and c4.get("inherited_candidate3",{}).get("contract_runner_consistency")=="EXACT_ORDERED_MATCH_REQUIRED",
}
failed=[name for name,ok in checks.items() if not ok]
print(json.dumps({
    "schema":"openazrael.release_docs_validation",
    "version":1,
    "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL",
    "checks":checks,
    "failed":failed,
},indent=2))
sys.exit(1 if failed else 0)
