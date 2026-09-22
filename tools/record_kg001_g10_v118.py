#!/usr/bin/env python3
"""Record and finalize receipt-bound KG-001 G10 manual sanity evidence."""
from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
from datetime import date as date_type

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT=ROOT/"exports/OpenAzrael-KG001-Candidate2-v116.test-build.json"
DEFAULT_OUT=ROOT/".tmp/kg001/kg001_manual_sanity_v118.json"
PROMOTED=ROOT/"data/tests/kg001_manual_sanity.json"
PROMOTED_VALIDATION=ROOT/"data/tests/kg001_manual_sanity_validation_v118.json"

sys.path.insert(0,str(ROOT/"tools"))
from validate_kg001_manual_sanity_v118 import (
    REQUIRED_BLOCKERS,
    REQUIRED_CHECKS,
    validate as validate_manual,
)


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")


def relative_or_absolute(path: Path) -> str:
    resolved=path.resolve()
    try:
        return str(resolved.relative_to(ROOT)).replace("\\","/")
    except ValueError:
        return str(resolved).replace("\\","/")


def init_result(receipt_path: Path) -> dict:
    receipt=load_json(receipt_path)
    if receipt.get("schema")!="openazrael.kg001.test_build_receipt":
        raise RuntimeError("not a KG-001 test-build receipt")
    if receipt.get("version")!=118:
        raise RuntimeError("test-build receipt version is not 118")
    if receipt.get("status")!="READY_FOR_G10_MANUAL_TEST":
        raise RuntimeError(
            "test-build receipt is not READY_FOR_G10_MANUAL_TEST"
        )
    if receipt.get("startup_smoke",{}).get("status")!="PASS":
        raise RuntimeError("test-build startup smoke is not PASS")
    return {
        "schema":"openazrael.kg001.manual_sanity",
        "version":2,
        "status":"PENDING",
        "test_build_receipt":relative_or_absolute(receipt_path),
        "test_build_receipt_sha256":sha256(receipt_path),
        "candidate_commit":receipt.get("commit_sha",""),
        "executable_sha256":receipt.get("executable_sha256",""),
        "pck_sha256":receipt.get("pck_sha256",""),
        "godot_version":receipt.get("godot",{}).get("version",""),
        "tester":"",
        "date":"",
        "checks":{name:"PENDING" for name in REQUIRED_CHECKS},
        "blocker_checks":{name:"PENDING" for name in REQUIRED_BLOCKERS},
        "critical_bugs":[],
        "reproducible_softlocks":[],
        "notes":"",
        "boundary":(
            "PASS is valid only when every required check and blocker check is "
            "PASS and this result validates against the exact v118 receipt."
        ),
    }


def parse_assignment(value: str) -> tuple[str,str]:
    if "=" not in value:
        raise ValueError(f"expected NAME=PASS|FAIL, got {value!r}")
    name,status=value.split("=",1)
    name=name.strip()
    status=status.strip().upper()
    if status not in {"PASS","FAIL"}:
        raise ValueError(f"{name}: status must be PASS or FAIL")
    return name,status


def command_init(args) -> int:
    if not args.receipt.is_file():
        raise RuntimeError(f"receipt missing: {args.receipt}")
    result=init_result(args.receipt)
    write_json(args.out,result)
    print(json.dumps({
        "status":"PASS",
        "action":"init",
        "out":relative_or_absolute(args.out),
        "candidate_commit":result["candidate_commit"],
        "required_checks":len(REQUIRED_CHECKS),
        "required_blocker_checks":len(REQUIRED_BLOCKERS),
    },indent=2))
    return 0


def command_record(args) -> int:
    if not args.input.is_file():
        raise RuntimeError(f"manual result missing: {args.input}")
    result=load_json(args.input)
    if result.get("schema")!="openazrael.kg001.manual_sanity" or result.get("version")!=2:
        raise RuntimeError("manual result is not v2 KG-001 G10 evidence")
    if result.get("status") not in {"PENDING","FAIL"}:
        raise RuntimeError("cannot modify finalized PASS G10 evidence")

    for raw in args.check:
        name,status=parse_assignment(raw)
        if name not in REQUIRED_CHECKS:
            raise RuntimeError(f"unknown required check: {name}")
        result["checks"][name]=status
    for raw in args.blocker:
        name,status=parse_assignment(raw)
        if name not in REQUIRED_BLOCKERS:
            raise RuntimeError(f"unknown blocker check: {name}")
        result["blocker_checks"][name]=status

    if args.critical_bug:
        result["critical_bugs"].extend(args.critical_bug)
    if args.softlock:
        result["reproducible_softlocks"].extend(args.softlock)
    if args.note:
        previous=str(result.get("notes","")).strip()
        result["notes"]="\n".join(
            value for value in [previous,*args.note] if value
        )
    result["status"]="PENDING"
    write_json(args.input,result)

    pending=[
        name for name,value in result["checks"].items()
        if value=="PENDING"
    ]
    pending_blockers=[
        name for name,value in result["blocker_checks"].items()
        if value=="PENDING"
    ]
    print(json.dumps({
        "status":"PASS",
        "action":"record",
        "out":relative_or_absolute(args.input),
        "pending_checks":pending,
        "pending_blocker_checks":pending_blockers,
        "critical_bug_count":len(result["critical_bugs"]),
        "softlock_count":len(result["reproducible_softlocks"]),
    },indent=2))
    return 0


def command_finalize(args) -> int:
    if not args.input.is_file():
        raise RuntimeError(f"manual result missing: {args.input}")
    if not args.receipt.is_file():
        raise RuntimeError(f"receipt missing: {args.receipt}")
    result=load_json(args.input)
    receipt=load_json(args.receipt)

    pending=[
        name for name in REQUIRED_CHECKS
        if result.get("checks",{}).get(name)=="PENDING"
    ]
    pending_blockers=[
        name for name in REQUIRED_BLOCKERS
        if result.get("blocker_checks",{}).get(name)=="PENDING"
    ]
    if pending or pending_blockers:
        raise RuntimeError(
            "cannot finalize with pending checks: "
            + ", ".join([*pending,*pending_blockers])
        )

    result["tester"]=args.tester.strip()
    result["date"]=args.date
    all_pass=(
        all(result.get("checks",{}).get(name)=="PASS" for name in REQUIRED_CHECKS)
        and all(
            result.get("blocker_checks",{}).get(name)=="PASS"
            for name in REQUIRED_BLOCKERS
        )
        and result.get("critical_bugs")==[]
        and result.get("reproducible_softlocks")==[]
    )
    result["status"]="PASS" if all_pass else "FAIL"
    write_json(args.input,result)

    validation=validate_manual(result,receipt,args.receipt.resolve())
    validation_path=args.input.with_name(
        args.input.stem+"_validation.json"
    )
    write_json(validation_path,validation)

    promoted=False
    if args.promote:
        if validation.get("status")!="PASS":
            raise RuntimeError(
                "refusing promotion because receipt-bound G10 validation failed: "
                + ", ".join(validation.get("failed",[]))
            )
        shutil.copyfile(args.input,PROMOTED)
        shutil.copyfile(validation_path,PROMOTED_VALIDATION)
        promoted=True

    print(json.dumps({
        "status":validation.get("status"),
        "manual_status":result["status"],
        "action":"finalize",
        "result":relative_or_absolute(args.input),
        "validation":relative_or_absolute(validation_path),
        "promoted":promoted,
        "promoted_result":(
            str(PROMOTED.relative_to(ROOT)).replace("\\","/")
            if promoted else ""
        ),
    },indent=2))
    return 0 if validation.get("status")=="PASS" else 1


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest="command",required=True)

    p_init=sub.add_parser("init")
    p_init.add_argument("--receipt",type=Path,default=DEFAULT_RECEIPT)
    p_init.add_argument("--out",type=Path,default=DEFAULT_OUT)

    p_record=sub.add_parser("record")
    p_record.add_argument("--input",type=Path,default=DEFAULT_OUT)
    p_record.add_argument("--check",action="append",default=[])
    p_record.add_argument("--blocker",action="append",default=[])
    p_record.add_argument("--critical-bug",action="append",default=[])
    p_record.add_argument("--softlock",action="append",default=[])
    p_record.add_argument("--note",action="append",default=[])

    p_finalize=sub.add_parser("finalize")
    p_finalize.add_argument("--input",type=Path,default=DEFAULT_OUT)
    p_finalize.add_argument("--receipt",type=Path,default=DEFAULT_RECEIPT)
    p_finalize.add_argument("--tester",required=True)
    p_finalize.add_argument(
        "--date",
        default=date_type.today().isoformat(),
    )
    p_finalize.add_argument("--promote",action="store_true")

    args=ap.parse_args()
    try:
        if args.command=="init":
            return command_init(args)
        if args.command=="record":
            return command_record(args)
        return command_finalize(args)
    except Exception as exc:
        print(json.dumps({
            "status":"FAIL",
            "action":args.command,
            "error":str(exc),
        },indent=2))
        return 1


if __name__=="__main__":
    raise SystemExit(main())
