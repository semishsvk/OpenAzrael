#!/usr/bin/env python3
import argparse, json
from pathlib import Path
SIG='53 51 52 56 57 C8 30 00 00 50 C7 45 F0 01 00 00'

def main():
 ap=argparse.ArgumentParser(description='Build a DOSBox-X debugger recipe for the first real OpenAzrael audio capture.')
 ap.add_argument('--out-dir',required=True); ap.add_argument('--scan-seg',default='0'); ap.add_argument('--scan-off',default='0'); ap.add_argument('--scan-bytes',default='1000000',help='hex byte count; default 16 MiB')
 a=ap.parse_args(); out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
 recipe=f'''OpenAzrael v85 - DOSBox-X read-only capture recipe\n\nPRECONDITION\n- Use a DOSBox-X build with the debugger enabled.\n- Run the exact bound demo R.EXE.\n- Pause at the room/pose you want to measure (Alt+Pause normally enters the debugger).\n\nPHASE A - broad memory dump\nDebugger command:\n  MEMDUMPBIN {a.scan_seg} {a.scan_off} {a.scan_bytes}\n\nDOSBox-X writes MEMDUMP.BIN. Copy/rename it to memory.bin before issuing another MEMDUMPBIN, because the command writes the same filename.\nThe byte represented by memory.bin[0] must correspond to the linear/physical base supplied later as --dump-base. For the default 0:0 scan this is 0.\n\nOFFLINE LOCATE\n  python tools/locate_runtime_audio_anchor_v83.py --memory-dump memory.bin --dump-base 0 --out-dir anchor --emit-kit\n\nThe locator must report exactly one signature hit. Zero or multiple hits are NOT_EVIDENCE_READY.\n\nPHASE B - independent context confirmation\nUse the runtime_cde1 reported by anchor/runtime_anchor_v83.json and inspect the code/data around that address in the paused process. The first 16 bytes must be:\n  {SIG}\nDo not promote the anchor beyond OBSERVED_CANDIDATE unless the paused process agrees.\n\nPHASE C - Miles trace + OpenAzrael reference\nPreserve the bounded AIL_DEBUG trace interval corresponding to this paused state and an OpenAzrael F9 JSONL capture at the same room/listener pose. Record the inclusive trace start/end line numbers.\n\nEND-TO-END PROCESSOR\n  python tools/process_memory_audio_capture_v84.py --memory-dump memory.bin --dump-base 0 --miles-log AIL_DEBUG.LOG --reference-capture openazrael_audio_capture_v71.jsonl --room-id <ROOM> --trace-start-line <START> --trace-end-line <END> --out-dir parity\n\nEvidence rule: synthetic tests validate tooling only. Classic Audio parity remains UNOBSERVED until these inputs come from the real paused R.EXE.\n'''
 (out/'DOSBOXX_CAPTURE_RECIPE_V85.txt').write_text(recipe)
 manifest={'schema':'openazrael.dosboxx_capture_recipe','version':85,'debugger':'DOSBox-X','signature_hex':SIG.replace(' ',''),'commands':{'broad_dump':f'MEMDUMPBIN {a.scan_seg} {a.scan_off} {a.scan_bytes}'},'evidence_status':'PROTOCOL_READY_REAL_CAPTURE_UNOBSERVED'}
 (out/'dosboxx_capture_recipe_v85.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 print(json.dumps(manifest,indent=2))
if __name__=='__main__': main()
