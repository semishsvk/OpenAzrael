#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
tool=(ROOT/"tools/render_candidate4_music_v135.py").read_text(encoding="utf-8")
converter=(ROOT/"tools/xmi_to_midi_v134.py").read_text(encoding="utf-8")
checks={
 "fixed_120hz":"CLOCK_HZ=120.0" in tool and "PPQN=60" in converter and "TEMPO_US_PER_QUARTER=500000" in converter,
 "source_hash_check":"XMI fingerprint mismatch" in tool,
 "soundfont_hash":"sha256(soundfont)" in tool,
 "derived_output_local":'assets/audio/music' in tool,
 "ogg_output":'format="OGG"' in tool and 'subtype="VORBIS"' in tool,
 "silence_gate":"rendered music is silent" in tool,
 "loop_metadata":"loop_offset_seconds" in tool and "source_loop_end_tick" in tool,
 "fluid_backend":"FluidSynth" in tool and "ctypes.util.find_library" in tool,
 "godot_runtime_pending":'"runtime_playback_test":"PENDING_GODOT"' in tool,
 "no_raw_commit":'"source_safe_receipt":True' in tool,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({"schema":"openazrael.kg001.candidate4_music_renderer_validation","version":135,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL","checks":checks,"failed":failed},indent=2))
sys.exit(1 if failed else 0)
