#!/usr/bin/env python3
"""Register and resolve the pinned OpenAzrael demo corpus into persistent private cache.

The orchestration layer fetches the pinned Drive file ID from
data/source_corpora_contract_v1.json when the archive is not already available.
This script owns verification, mirroring, materialization and registry binding.
"""
from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.remaster_framework.source_registry import (
    load_contract, register_source, resolve_source, verify_registered_source, registry_status
)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--archive",type=Path,help="Fetched canonical atdemo.zip; required only for first registration.")
    ap.add_argument("--source-home",type=Path)
    ap.add_argument("--status",action="store_true")
    a=ap.parse_args()
    contract=load_contract()
    spec=contract["corpora"]["demo"]
    if a.status:
        print(json.dumps(registry_status(home=a.source_home),indent=2))
        return 0
    if a.archive is not None:
        row=register_source("demo",a.archive,mirror=True,home=a.source_home)
        print(json.dumps({"registration":"PASS","row":row},indent=2))
    try:
        verify=verify_registered_source("demo",home=a.source_home)
        if verify["status"]!="PASS":
            raise RuntimeError(json.dumps(verify))
        root=resolve_source("demo",home=a.source_home)
    except FileNotFoundError:
        drive=spec["canonical_archive"].get("drive",{})
        print(json.dumps({
          "status":"CACHE_MISS",
          "drive_file_id":drive.get("file_id"),
          "drive_folder_id":drive.get("folder_id"),
          "archive_name":spec["canonical_archive"]["name"],
          "bytes":spec["canonical_archive"]["bytes"],
          "sha256":spec["canonical_archive"]["sha256"]
        },indent=2))
        return 2
    print(json.dumps({
      "status":"PASS",
      "kind":"demo",
      "root":str(root),
      "archive_sha256":spec["canonical_archive"]["sha256"],
      "restore_tool":spec["runtime_restore"]["tool"]
    },indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
