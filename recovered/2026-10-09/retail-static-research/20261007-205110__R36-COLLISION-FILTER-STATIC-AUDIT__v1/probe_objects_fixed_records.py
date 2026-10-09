from pathlib import Path
import struct,json,hashlib,math,re
src=Path(r"F:\Remaster Framework\source\Azrael's Tear\GAME\AZRAEL\OBJECTS.DAT")
b=src.read_bytes()
candidates=[]
for header in range(0,16):
    rem=len(b)-header
    if rem>0 and rem%603==0:
        candidates.append({"header":header,"records":rem//603})
first32=b[:32].hex()
# inspect first possible count values
header_values={"u8_0":b[0],"u16_0":struct.unpack_from("<H",b,0)[0],"u32_0":struct.unpack_from("<I",b,0)[0]}
# score each possible alignment 0..602 by how many records begin with printable-ish interface marker at small offset
scores=[]
for base in range(0,16):
    n=(len(b)-base)//603
    if n<100:continue
    score=0; examples=[]
    for i in range(min(n,1024)):
        rec=b[base+i*603:base+(i+1)*603]
        # common record starts appear to contain I<Class> near beginning 0..16.
        m=re.search(rb"I[A-Za-z][A-Za-z0-9 _-]{2,30}\x00",rec[:80])
        if m:
            score+=1
            if len(examples)<5:examples.append({"i":i,"rel":m.start(),"text":m.group()[:-1].decode("latin1")})
    scores.append({"base":base,"n":n,"interface_marker_records":score,"examples":examples})
scores=sorted(scores,key=lambda x:x["interface_marker_records"],reverse=True)
out={"schema":"OpenAzrael.RetailObjectsFixedRecordProbe.v1","sha256":hashlib.sha256(b).hexdigest(),
 "bytes":len(b),"first32":first32,"header_values":header_values,
 "exact_603_candidates":candidates,"alignment_scores":scores[:16]}
Path(__file__).with_name("objects_fixed_record_probe.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
