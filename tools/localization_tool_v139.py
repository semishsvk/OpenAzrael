#!/usr/bin/env python3
"""Generic source-safe localization toolchain for OpenAzrael/remaster projects.

Subcommands:
  extract   Scan configured source files into a deterministic string registry.
  template  Create/update a locale translation template from a registry.
  validate  Validate locale packs, placeholders, manifest and fallback coverage.
  compile   Emit a compact runtime pack from a validated translation pack.

The tool is game-agnostic. Commercial source payloads are read locally and are
never copied unless the caller explicitly writes the generated registry.
"""
from __future__ import annotations
import argparse, fnmatch, hashlib, json, re, sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.remaster_framework.source_registry import resolve_source

SCHEMA_REGISTRY="openazrael.localization_source_registry"
SCHEMA_PACK="openazrael.localization_pack"
SCHEMA_MANIFEST="openazrael.localization_manifest"
PRINTF_RE=re.compile(r"%(?:\d+\$)?[-+#0 ]*(?:\d+|\*)?(?:\.\d+|\.\*)?[hlLzjt]*[diuoxXfFeEgGaAcspn%]")
BRACE_RE=re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
LOCALE_RE=re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")

def read_json(path:Path)->Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path:Path,obj:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,sort_keys=False)+"\n",encoding="utf-8")

def sha256_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def stable_id(namespace:str,rel:str,anchor:str,domain:str)->str:
    digest=hashlib.sha1(f"{rel}|{anchor}|{domain}".encode("utf-8")).hexdigest()[:16]
    safe=re.sub(r"[^a-z0-9_.-]+","_",namespace.lower()).strip("_.")
    return f"{safe}.{domain}.{digest}"

def looks_localizable(text:str)->bool:
    s=text.strip()
    if len(s)<2 or not re.search(r"[A-Za-zÀ-ž]",s):
        return False
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.:#/-]*",s) and " " not in s:
        return False
    if re.fullmatch(r"[-+0-9,.;: xXa-fA-F]+",s):
        return False
    return True

def iter_glob(root:Path,pattern:str):
    short=pattern[3:] if pattern.startswith("**/") else pattern
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel=str(p.relative_to(root)).replace("\\","/")
        if fnmatch.fnmatch(rel,pattern) or (short!=pattern and fnmatch.fnmatch(rel,short)):
            yield p

def extract_text_lines(root:Path,spec:dict,namespace:str)->list[dict]:
    rows=[]
    enc=spec.get("encoding","latin1")
    domain=spec.get("domain","dialogue")
    inc=re.compile(spec["include_regex"]) if spec.get("include_regex") else None
    exc=re.compile(spec["exclude_regex"]) if spec.get("exclude_regex") else None
    for p in iter_glob(root,spec["glob"]):
        raw=p.read_bytes()
        rel=str(p.relative_to(root)).replace("\\","/")
        try: text=raw.decode(enc)
        except UnicodeDecodeError: text=raw.decode(enc,errors="replace")
        for i,line in enumerate(text.splitlines(),1):
            s=line.strip("\x00\r\n")
            if not s.strip(): continue
            if inc and not inc.search(s): continue
            if exc and exc.search(s): continue
            localizable=bool(spec.get("localizable","auto") is True or (spec.get("localizable","auto")=="auto" and looks_localizable(s)))
            anchor=f"line:{i}"
            rows.append({
                "id":stable_id(namespace,rel,anchor,domain),"domain":domain,
                "source":rel,"source_hash":sha256_bytes(raw),"line":i,"text":s,
                "status":"EXTRACTED_LINE","localizable":localizable
            })
    return rows

def extract_binary_ascii(root:Path,spec:dict,namespace:str)->list[dict]:
    rows=[]
    domain=spec.get("domain","animation")
    min_len=int(spec.get("min_length",3))
    rx=re.compile(rb"[\x20-\x7e]{"+str(min_len).encode()+rb",}")
    for p in iter_glob(root,spec["glob"]):
        raw=p.read_bytes(); rel=str(p.relative_to(root)).replace("\\","/")
        for m in rx.finditer(raw):
            s=m.group(0).decode("ascii",errors="replace")
            localizable=bool(spec.get("localizable",False))
            if spec.get("localizable")=="auto": localizable=looks_localizable(s)
            rows.append({
                "id":stable_id(namespace,rel,f"offset:{m.start()}",domain),"domain":domain,
                "source":rel,"source_hash":sha256_bytes(raw),"offset":m.start(),"text":s,
                "status":"EXTRACTED_ASCII","localizable":localizable
            })
    return rows

def walk_json(value:Any,path:str=""):
    if isinstance(value,dict):
        for k,v in value.items():
            yield from walk_json(v,f"{path}/{k}")
    elif isinstance(value,list):
        for i,v in enumerate(value):
            yield from walk_json(v,f"{path}/{i}")
    elif isinstance(value,str):
        yield path,value

def extract_json_strings(root:Path,spec:dict,namespace:str)->list[dict]:
    rows=[]; domain=spec.get("domain","text")
    keys=re.compile(spec["path_regex"]) if spec.get("path_regex") else None
    for p in iter_glob(root,spec["glob"]):
        raw=p.read_bytes(); rel=str(p.relative_to(root)).replace("\\","/")
        try: obj=json.loads(raw.decode(spec.get("encoding","utf-8")))
        except Exception: continue
        for jpath,s in walk_json(obj):
            if keys and not keys.search(jpath): continue
            localizable=bool(spec.get("localizable","auto") is True or (spec.get("localizable","auto")=="auto" and looks_localizable(s)))
            rows.append({
                "id":stable_id(namespace,rel,jpath,domain),"domain":domain,
                "source":rel,"source_hash":sha256_bytes(raw),"json_path":jpath,"text":s,
                "status":"EXTRACTED_JSON_STRING","localizable":localizable
            })
    return rows

def cmd_extract(a)->int:
    cfg=read_json(a.config)
    if a.root is not None:
        root=a.root.resolve()
    elif a.registered_corpus is not None:
        root=resolve_source(
            a.registered_corpus,
            home=a.source_home,
        )
    else:
        raise SystemExit(
            "extract requires --root or --registered-corpus"
        )
    namespace=cfg.get("namespace","loc")
    adapters={"text_lines":extract_text_lines,"binary_ascii":extract_binary_ascii,"json_strings":extract_json_strings}
    rows=[]
    for spec in cfg.get("sources",[]):
        adapter=spec.get("adapter")
        if adapter not in adapters:
            raise SystemExit(f"unsupported adapter: {adapter}")
        rows.extend(adapters[adapter](root,spec,namespace))
    rows.sort(key=lambda r:(r["source"],r.get("offset",r.get("line",0)),r["id"]))
    seen=set(); unique=[]
    for row in rows:
        if row["id"] in seen: continue
        seen.add(row["id"]); unique.append(row)
    out={
        "schema":SCHEMA_REGISTRY,"version":139,"source_locale":cfg.get("source_locale","en"),
        "generated_from":str(root),"entries":unique,
        "stats":{"entries":len(unique),"localizable":sum(bool(x.get("localizable")) for x in unique)}
    }
    write_json(a.out,out)
    print(json.dumps(out["stats"],indent=2))
    return 0

def placeholders(text:str)->list[str]:
    vals=[m.group(0) for m in PRINTF_RE.finditer(text) if m.group(0)!="%%"]
    vals += BRACE_RE.findall(text)
    return sorted(vals)

def localizable_entries(reg:dict)->list[dict]:
    return [e for e in reg.get("entries",[]) if e.get("localizable") and str(e.get("status","")).find("FRAGMENT")<0]

def cmd_template(a)->int:
    reg=read_json(a.registry)
    old={}
    if a.out.exists():
        try: old=read_json(a.out).get("strings",{})
        except Exception: old={}
    strings={}
    for e in localizable_entries(reg):
        key=e["id"]; src=e["text"]
        strings[key]=old.get(key,src if a.locale==reg.get("source_locale","en") else "")
    pack={
        "schema":SCHEMA_PACK,"version":139,"locale":a.locale,
        "source_locale":reg.get("source_locale","en"),
        "generated_from_registry_version":reg.get("version"),
        "strings":strings
    }
    write_json(a.out,pack); print(f"{a.locale}: {len(strings)} strings")
    return 0

def validate_pack(reg:dict,pack:dict,allow_missing:bool)->list[str]:
    errs=[]
    if pack.get("schema")!=SCHEMA_PACK: errs.append("bad pack schema")
    src={e["id"]:e["text"] for e in localizable_entries(reg)}
    dst=pack.get("strings",{})
    for key,text in src.items():
        tr=dst.get(key,"")
        if not tr and not allow_missing: errs.append(f"missing:{key}")
        if tr and placeholders(text)!=placeholders(str(tr)):
            errs.append(f"placeholder_mismatch:{key}:{placeholders(text)}!={placeholders(str(tr))}")
    for key in dst:
        if key not in src: errs.append(f"orphan:{key}")
    return errs

def cmd_validate(a)->int:
    reg=read_json(a.registry); manifest=read_json(a.manifest)
    errs=[]
    if manifest.get("schema")!=SCHEMA_MANIFEST: errs.append("bad manifest schema")
    fallback=manifest.get("fallback_locale","en")
    locales=manifest.get("locales",[])
    if not any(x.get("code")==fallback for x in locales): errs.append("fallback locale absent")
    codes=set()
    for row in locales:
        code=str(row.get("code",""))
        if not code or not LOCALE_RE.fullmatch(code) or code in codes: errs.append(f"bad/duplicate locale:{code}")
        codes.add(code)
        if str(row.get("direction","ltr")) not in ("ltr","rtl"): errs.append(f"bad direction:{code}")
        rel_file=str(row.get("file",""))
        if rel_file.startswith(("res://","user://")):
            errs.append(f"built-in manifest must use relative pack path:{code}")
            continue
        path=(a.base / rel_file).resolve()
        if not path.is_file():
            errs.append(f"pack_missing:{code}:{path}"); continue
        pack=read_json(path)
        if pack.get("locale")!=code: errs.append(f"pack_locale_mismatch:{code}")
        errs.extend(f"{code}:{e}" for e in validate_pack(reg,pack,a.allow_missing or code!=fallback))
    out={"schema":"openazrael.localization_validation","version":139,
         "status":"PASS" if not errs else "FAIL","locale_count":len(locales),"errors":errs}
    print(json.dumps(out,indent=2,ensure_ascii=False))
    return 0 if not errs else 1

def cmd_compile(a)->int:
    pack=read_json(a.pack)
    if pack.get("schema")!=SCHEMA_PACK: raise SystemExit("bad pack schema")
    compact={"schema":"openazrael.runtime_localization_pack","version":139,
             "locale":pack["locale"],"strings":pack.get("strings",{})}
    write_json(a.out,compact)
    return 0

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__); sp=ap.add_subparsers(dest="cmd",required=True)
    p=sp.add_parser("extract"); p.add_argument("--config",type=Path,required=True); p.add_argument("--root",type=Path); p.add_argument("--registered-corpus",choices=("demo","retail")); p.add_argument("--source-home",type=Path); p.add_argument("--out",type=Path,required=True); p.set_defaults(fn=cmd_extract)
    p=sp.add_parser("template"); p.add_argument("--registry",type=Path,required=True); p.add_argument("--locale",required=True); p.add_argument("--out",type=Path,required=True); p.set_defaults(fn=cmd_template)
    p=sp.add_parser("validate"); p.add_argument("--registry",type=Path,required=True); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--base",type=Path,default=Path(".")); p.add_argument("--allow-missing",action="store_true"); p.set_defaults(fn=cmd_validate)
    p=sp.add_parser("compile"); p.add_argument("--pack",type=Path,required=True); p.add_argument("--out",type=Path,required=True); p.set_defaults(fn=cmd_compile)
    a=ap.parse_args()
    return a.fn(a)

if __name__=="__main__":
    raise SystemExit(main())
