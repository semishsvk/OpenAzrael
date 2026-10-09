from pathlib import Path
import json,hashlib,string
src=Path(r"F:\Remaster Framework\source\Azrael's Tear\GAME\AZRAEL\WORLD.DAT")
b=src.read_bytes()
targets={"tun_conn01":13073,"tun_conn02_a":6861,"tun_conn02_b":27245,"tun_conn02_c":42903,"Object02":28582}
rows={}
for name,off in targets.items():
    lo=max(0,off-256);hi=min(len(b),off+384);chunk=b[lo:hi]
    # Extract all printable zero-terminated fragments with absolute offsets.
    strings=[];i=0
    while i<len(chunk):
        if 32<=chunk[i]<127:
            j=i
            while j<len(chunk) and 32<=chunk[j]<127:j+=1
            if j-i>=3:
                strings.append({"offset":lo+i,"text":chunk[i:j].decode("latin1")})
            i=j
        else:i+=1
    rows[name]={"match_offset":off,"window_start":lo,"window_hex":chunk.hex(),"strings":strings}
out={"schema":"OpenAzrael.RetailWorldNameContext.v1","source":str(src),
     "sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b),"contexts":rows,
     "claim_limits":["Byte/string adjacency is structural evidence; field semantics require serializer/runtime binding."]}
Path(__file__).with_name("world_name_context.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({k:{"match_offset":v["match_offset"],"strings":v["strings"]} for k,v in rows.items()},indent=2))
