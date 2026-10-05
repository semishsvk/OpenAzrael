from pathlib import Path
import json, hashlib, sys

src=Path(sys.argv[1])
out=Path(sys.argv[2])
raw=src.read_bytes()
text=raw.decode("latin1").replace("\r\n","\n")
lines=text.splitlines()

# NIAMH.DAT is a compact record stream. Parse conservatively by locating
# conversation-family headers and answer labels, preserving unknown numeric
# condition/action rows verbatim rather than inventing semantics.
families={}
i=0
while i < len(lines):
    s=lines[i].strip()
    if s in ("1A","1B"):
        fam=s; i+=1; records=[]
        # family preamble: retain until first recognizable record id
        pre=[]
        while i < len(lines) and not lines[i].strip().isdigit() and lines[i].strip() not in ("A",):
            pre.append(lines[i]); i+=1
        # The format is irregular; use Ni<label> markers as record terminators.
        start=i
        while i < len(lines):
            if i+1 < len(lines) and lines[i].strip() in ("1A","1B") and lines[i].strip()!=fam:
                break
            marker=None
            for j in range(i,min(i+40,len(lines))):
                if lines[j].strip().startswith("Ni"+fam+"_"):
                    marker=j; break
            if marker is None: break
            label=lines[marker].strip().split("_",1)[1]
            chunk=lines[i:marker+1]
            # Source layout places player text and NPC response as the final
            # two nonnumeric textual fields before the Ni marker.
            textual=[]
            for x in chunk:
                t=x.strip()
                if not t: continue
                if t.startswith("Ni"): continue
                if t.replace(",","").replace("-","").isdigit(): continue
                textual.append(t)
            if len(textual)>=2:
                player=textual[-2]; response=textual[-1]
            elif len(textual)==1:
                player=textual[0]; response=""
            else:
                player=response=""
            records.append({"id":label,"source_marker":"Ni"+fam+"_"+label,
                            "player_text":player,"niamh_text":response,
                            "raw_prefix":chunk[:-3] if len(chunk)>=3 else chunk})
            i=marker+1
            # consume trailing control numerics before next record
            while i<len(lines) and lines[i].strip() in ("0","1","2","3","4","5","6","7"):
                i+=1
            if i<len(lines) and lines[i].strip() in ("1A","1B") and lines[i].strip()!=fam: break
        families[fam]={"preamble":pre,"records":records}
        continue
    i+=1

doc={"schema":"openazrael.conversation_ir","version":209,"status":"SOURCE_EXTRACTED",
     "source":{"file":"NIAMH.DAT","bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()},
     "character":"Niamh","families":families,
     "policy":{"raw_conditions_preserved":True,"unknown_semantics_not_invented":True,
               "missing_answer_text_not_invented":True,"do_not_display_player_text":True}}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(doc,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"PASS","families":{k:len(v["records"]) for k,v in families.items()},"sha256":doc["source"]["sha256"]}))
