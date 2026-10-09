#!/usr/bin/env python3
"""Compare proprietary MOV headers without assigning unverified field meanings."""
import argparse, hashlib, json, struct
from pathlib import Path
FILES=("MINDLOGO.MOV","INTRO.MOV","MOV/INTRO.MOV","MOV/DEMO.MOV")
def analyze(blob, name):
    if len(blob)<80 or blob[:4]!=bytes.fromhex("90ef12ab"): raise ValueError("bad MOV header: "+name)
    frames,depth,width,height=struct.unpack_from("<4H",blob,4)
    if not (frames>0 and depth==12 and 0<width<=4096 and 0<height<=4096): raise ValueError("implausible geometry: "+name)
    words=[]
    for off in range(12,64,4):
        v=struct.unpack_from("<I",blob,off)[0]
        labels=[]
        if v==width:labels.append("width")
        if v==width-1:labels.append("width_minus_one")
        if v==height:labels.append("height")
        if v==height-1:labels.append("height_minus_one")
        if v>=80 and v<len(blob) and not labels:labels.append("in_file_numeric_candidate_not_proven_offset")
        words.append({"offset":off,"u32":v,"classifications":labels})
    return {"file":name,"sha256":hashlib.sha256(blob).hexdigest(),"bytes":len(blob),"frame_count_candidate":frames,"depth_candidate":depth,"width_candidate":width,"height_candidate":height,"header_words":words,"frame_boundaries_verified":False,"decoded_frames":0,"audio_verified":False}
def main():
    p=argparse.ArgumentParser();p.add_argument("corpus",type=Path);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    entries=[analyze((a.corpus/f).read_bytes(),f) for f in FILES]
    result={"schema":"openazrael.mov_header_field_classification.v310","status":"STRUCTURAL_PASS_FIDELITY_HOLD","entries":entries,"warning":"Numeric in-file candidates are NOT frame offsets without independent validation."}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"status":result["status"],"files":len(entries),"ambiguous_candidates":[sum("in_file_numeric_candidate_not_proven_offset" in w["classifications"] for w in e["header_words"]) for e in entries]}))
if __name__=="__main__":main()