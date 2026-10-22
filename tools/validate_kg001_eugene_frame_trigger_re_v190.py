#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"data/tests/kg001_eugene_frame_trigger_re_contract_v190.json"
EXE_SHA="381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00"
def main():
 c=json.loads(C.read_text())
 checks=[
  c.get("status")=="EXECUTABLE_CODE_VERIFIED",
  c["frame_domain"]["current_frame_field"]=="character+0x284",
  c["frame_domain"]["rule"]=="CURRENT_FRAME_INT16_CONVERTED_DIRECTLY_TO_FLOAT_XAF_TIME",
  c["frame_domain"]["increment_rule"]=="CURRENT_FRAME_PLUS_ONE_PER_CHARACTER_UPDATE",
  c["trigger"]["frame"]==60,c["trigger"]["sound"]=="EUGROAR.WAV",
  c["trigger"]["effect_value"]==200,c["trigger"]["audio_parameter"] is False,
  c["trigger"]["semantics"]=="PLAY_EUGROAR_THEN_SUBTRACT_200_FROM_PLAYER_HEALTH",
  c["player_health"]["initial_value"]==500,
  c["runtime_policy"]["trigger_order"]=="EVALUATE_FRAME_THEN_TRIGGER_THEN_INCREMENT",
 ]
 if len(sys.argv)>1:
  b=Path(sys.argv[1]).read_bytes()
  checks += [hashlib.sha256(b).hexdigest()==EXE_SHA]
  # filds current frame; call evaluator
  checks += [b[0x8252a:0x8254c].hex().startswith("8b4204668b80840200008945fc83ec04df45fcd91c248b02")]
  # trigger frame compare against current frame
  checks += [b[0x826b4:0x826c1].hex()=="668b1432663b938402000075cf"]
  # subtract per-trigger int16 effect from global player state +0x18
  checks += [b[0x8270d:0x82717].hex()=="8b158838040066294218"]
  # current frame increment
  checks += [b[0x82771:0x8277b].hex()=="89c24266899384020000"]
 if not all(checks):
  print("EXECUTABLE_FRAME_TRIGGER_FAIL"); return 1
 print("EXECUTABLE_FRAME_TRIGGER_PASS")
 print("runtime=NOT_EXECUTED")
 return 0
if __name__=="__main__": raise SystemExit(main())
