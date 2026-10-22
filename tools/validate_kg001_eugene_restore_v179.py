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
 "source_ranges":all(x in restore for x in ['"REST":(0,0)','"RUN":(2,7)','"ATTACK":(53,70)','"SHOT":(130,163)','"DEATH_TWITCH":(160,163)','"DEAD":(163,163)']),
 "canonical_fingerprints":all(x in restore for x in ["1533e24af2729f6a9ccbc4e791fec92617b44f709a3f1dc31ce7a71763be51af","0004eaac87202d2487c72f43008cf5c6cec15241d07a95dc550737889d5bb62f","4125d9693137f74020209fc2f7f834cb64ce232cbabd4e7a8fe0199d9933b636","PINNED_CANONICAL_ATDEMO"]),
 "per_ani_source_ranges":'for name,(start,end) in rr.items()' in restore and '"ani_ranges"' in restore,
 "no_assumed_eugene_eugenb_symmetry":'if name in rr and rr[name]!=bounds' in restore,
 "ani_xaf_cross_validation":'ANI_RANGE_OUTSIDE_XAF' in restore and 'stats["frame_min"]' in restore and 'stats["frame_max"]' in restore,
 "stale_clip_purge":'glob("*.tres")' in restore and 'stale.unlink()' in restore,
 "fingerprint_fail_closed":'CANONICAL_SOURCE_FINGERPRINT_MISMATCH' in restore,
 "atomic_restore_binding":'restore_eugene_animation_v179.py' in candidate,
 "runtime_models":all(x in room for x in ['SourceCharacter_" + character','runtime_model']),
 "source_animation_binding":'bind_source_player' in room and 'SourceCharacterAnimation' in room and 'source_library.add_animation' in room,
 "runtime_track_root":'NodePath("../" + character + "_Model")' in room,
 "runtime_fail_closed_clips":'HOLD_SOURCE_CLIPS_MISSING' in room,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.eugene_restore_validation","version":179,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","checks":checks,"failed":failed,
 "runtime_status":"NOT_EXECUTED"},indent=2))
sys.exit(1 if failed else 0)
