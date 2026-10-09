from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(r"F:\OpenRemaster\sources\materialized\openazrael_demo_atdemo_v1\bf0c87f731bb4e87\layer2\ATDEMO\PUZZLES.DAT")
EXPECTED_SHA="b8131cf823edb184f04740d5af0a457f4d684e7b0be654b529ec7cdfde1739d1"
NAMES={"R7HotPipeOut":38,"R7HotParent":4,"RotateHotUp":7,"R7HotPos":111,"R7ColdPos":112}
STAGES=("corpus_identity","record_boundaries","action_grouping","operand_decoding","object_binding","state_machine","animation_transform","audio_timing","persistence","original_runtime_replay_diff")
def audit():
    if not SOURCE.is_file():
        return {"status":"BLOCKED","reason":"CANONICAL_SOURCE_MISSING"}
    raw=SOURCE.read_bytes(); sha=hashlib.sha256(raw).hexdigest()
    counts={k:raw.count(k.encode("ascii")) for k in NAMES}
    structural=(sha==EXPECTED_SHA and counts==NAMES)
    stages={s:{"state":"VERIFIED" if s=="corpus_identity" and structural else "HOLD"} for s in STAGES}
    return {"schema":"openremaster.multistate_interaction_evidence","version":1,
      "project":"OpenAzrael","scene":"R7_WellRoom","interaction":"pipe_switchboard",
      "source":"ATDEMO/PUZZLES.DAT","sha256":sha,"expected_sha256":EXPECTED_SHA,
      "observed_occurrences":counts,"expected_occurrences":NAMES,
      "structural_status":"PASS" if structural else "FAIL",
      "fidelity_status":"HOLD","stages":stages,
      "rule":"Occurrence counts and string adjacency are structural evidence only; do not infer operands, transforms, animation timing or state transitions without source/runtime proof.",
      "promotion_allowed":False}
if __name__=="__main__":
    report=audit()
    out=ROOT/".tmp/r7_multistate_evidence_v305.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"structural_status":report.get("structural_status"),"fidelity_status":report.get("fidelity_status"),"occurrences":report.get("observed_occurrences"),"promotion_allowed":report.get("promotion_allowed")}))
    sys.exit(0 if report.get("structural_status")=="PASS" and not report["promotion_allowed"] else 1)
