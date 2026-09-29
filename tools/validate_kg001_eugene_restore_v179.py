#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
restore=(ROOT/"tools/restore_eugene_animation_v179.py").read_text(encoding="utf-8")
candidate=(ROOT/"tools/restore_candidate_assets.py").read_text(encoding="utf-8")
room=(ROOT/"scripts/room_manager.gd").read_text(encoding="utf-8")
checks={
 "canonical_source_resolution":'resolve_source("demo"' in restore,
 "source_files":all(x in restore for x in ["EUGBLD.XAF","EUGENB.ANI","EUGENE.XAF","EUGENE.ANI"]),
 "known_eugbld_census":all(x in restore for x in ['"animated_nodes":30','"rotation_keys":849','"scale_keys":199','"position_keys":275']),
 "source_ranges":all(x in restore for x in ['"RUN":(2,7)','"ATTACK":(53,70)','"SHOT":(130,163)','"DEATH_TWITCH":(160,163)','"DEAD":(163,163)']),
 "no_invented_pinned_hashes":'OBSERVED_FROM_REGISTERED_CANONICAL_CORPUS_NOT_YET_PINNED_IN_GIT' in restore,
 "atomic_restore_binding":'restore_eugene_animation_v179.py' in candidate,
 "runtime_models":all(x in room for x in ['SourceCharacter_" + character','runtime_model']),
 "source_animation_binding":'bind_source_player' in room and '_collect_animation_players(model' in room,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.eugene_restore_validation","version":179,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","checks":checks,"failed":failed,
 "runtime_status":"NOT_EXECUTED"},indent=2))
sys.exit(1 if failed else 0)
