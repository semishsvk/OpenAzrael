#!/usr/bin/env python3
"""Reject compile-time preloads of Git-ignored Candidate commercial assets."""
from pathlib import Path
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN_PREFIXES=(
    "res://assets/audio/",
    "res://assets/rooms/",
    "res://assets/textures/classic/",
)
pattern=re.compile(r'''\bpreload\s*\(\s*["']([^"']+)["']\s*\)''')
violations=[]
scanned=0
for path in sorted((ROOT/"scripts").glob("*.gd")):
    scanned+=1
    text=path.read_text(encoding="utf-8")
    for match in pattern.finditer(text):
        resource=match.group(1)
        if any(resource.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            line=text.count("\n",0,match.start())+1
            violations.append({
                "script":str(path.relative_to(ROOT)).replace("\\","/"),
                "line":line,
                "resource":resource,
            })

result={
    "schema":"openazrael.kg001.source_safe_asset_loading",
    "version":117,
    "status":"PASS" if not violations else "FAIL",
    "scanned_scripts":scanned,
    "forbidden_compile_time_prefixes":list(FORBIDDEN_PREFIXES),
    "violations":violations,
    "policy":"Git-ignored Candidate room/audio/Classic texture payloads must be runtime-loaded after explicit existence/preflight checks, never preload()ed at GDScript parse time.",
}
print(json.dumps(result,indent=2))
sys.exit(1 if violations else 0)
