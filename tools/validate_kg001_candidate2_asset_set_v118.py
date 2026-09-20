#!/usr/bin/env python3
"""Validate completeness of the restored KG-001 Candidate 2 runtime asset set.

Default mode is source-safe and observational: it validates the contract and
reports local presence without requiring excluded commercial-derived files.
--require-complete is the pre-build/fresh-checkout gate and fails closed unless
all canonical Candidate 2 runtime assets and restore evidence are present,
consistent and Git-ignored.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json
import struct
import subprocess
import sys
import wave

ROOT=Path(__file__).resolve().parents[1]
ROOM_EXPECTED={
    "R1":{"primitives":69,"triangles":593,"textured_primitives":62},
    "R7":{"primitives":48,"triangles":689,"textured_primitives":40},
    "R8":{"primitives":87,"triangles":1050,"textured_primitives":74},
}
AUDIO_NAMES=[
    "797TAP.WAV",
    "799SECDR.WAV",
    "S121.WAV",
    "S137.WAV",
    "S152V2.WAV",
    "S174ELP1.WAV",
    "S174ELP2.WAV",
    "S186.WAV",
]
TEXTURE_COUNT=86
COLORKEY_CONTRACT=ROOT/"data/tests/kg001_texture_colorkey_contract_v116.json"
RESTORE_EVIDENCE=ROOT/".tmp/kg001/legacy_colorkey_restore.json"
AUDIO_RESTORE_EVIDENCE=ROOT/".tmp/kg001/audio_restore_v118.json"
SOURCE_FINGERPRINTS=ROOT/"data/backup/source_fingerprints.json"


def ignored(path: Path) -> bool:
    try:
        rel=str(path.relative_to(ROOT)).replace("\\","/")
    except ValueError:
        return False
    proc=subprocess.run(
        ["git","check-ignore","-q",rel],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode==0


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_audio_hashes() -> dict[str,str]:
    payload=read_json(SOURCE_FINGERPRINTS)
    return {
        Path(str(entry["path"])).name:str(entry["sha256"])
        for entry in payload.get("entries",[])
        if isinstance(entry,dict)
        and str(entry.get("path","")).startswith("assets/audio/")
    }


def wav_pcm_summary(path: Path) -> dict:
    with wave.open(str(path),"rb") as wav:
        channels=wav.getnchannels()
        sample_width=wav.getsampwidth()
        frame_rate=wav.getframerate()
        frame_count=wav.getnframes()
        compression=wav.getcomptype()
        raw=wav.readframes(frame_count)
    if frame_count<=0 or channels<=0 or frame_rate<=0 or not raw:
        peak=0
    elif sample_width==1:
        peak=max(abs(int(value)-128) for value in raw)
    elif sample_width==2:
        usable=len(raw)-(len(raw)%2)
        peak=max(
            (abs(value[0]) for value in struct.iter_unpack("<h",raw[:usable])),
            default=0,
        )
    elif sample_width==3:
        peak=0
        for offset in range(0,len(raw)-2,3):
            value=int.from_bytes(raw[offset:offset+3],"little",signed=False)
            if value & 0x800000:
                value-=1<<24
            peak=max(peak,abs(value))
    elif sample_width==4:
        usable=len(raw)-(len(raw)%4)
        peak=max(
            (abs(value[0]) for value in struct.iter_unpack("<i",raw[:usable])),
            default=0,
        )
    else:
        peak=0
    return {
        "channels":channels,
        "sample_width":sample_width,
        "frame_rate":frame_rate,
        "frames":frame_count,
        "compression":compression,
        "peak":int(peak),
    }


def room_manifest_check(room: str, expected: dict) -> dict:
    glb=ROOT/"assets/rooms"/f"{room}.glb"
    manifest=ROOT/"data"/f"{room}.textured.v44.manifest.json"
    row={
        "room":room,
        "glb":str(glb.relative_to(ROOT)),
        "glb_present":glb.is_file(),
        "glb_nonempty":glb.is_file() and glb.stat().st_size>0,
        "glb_git_ignored":glb.is_file() and ignored(glb),
        "manifest":str(manifest.relative_to(ROOT)),
        "manifest_present":manifest.is_file(),
        "expected":expected,
        "manifest_matches":False,
    }
    if manifest.is_file():
        try:
            payload=read_json(manifest)
            row["manifest_matches"]=(
                int(payload.get("primitive_count",-1))==expected["primitives"]
                and int(payload.get("triangles",-1))==expected["triangles"]
                and int(payload.get("textured_primitives",-1))
                == expected["textured_primitives"]
                and payload.get("missing_textures")==[]
            )
        except Exception as exc:
            row["manifest_error"]=str(exc)
    row["complete"]=all([
        row["glb_present"],
        row["glb_nonempty"],
        row["glb_git_ignored"],
        row["manifest_present"],
        row["manifest_matches"],
    ])
    return row


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-complete",action="store_true")
    ap.add_argument("--out",type=Path,default=None)
    args=ap.parse_args()

    contract=read_json(COLORKEY_CONTRACT)
    expected_hash=sorted(str(v) for v in contract.get(
        "expected_demo_hash_textures",[]
    ))
    contract_checks={
        "colorkey_contract_schema":contract.get("schema")
        =="openazrael.kg001.texture_colorkey_contract",
        "expected_hash_texture_count":len(expected_hash)==10,
        "expected_room_count":len(ROOM_EXPECTED)==3,
        "expected_audio_count":len(AUDIO_NAMES)==8,
        "expected_classic_texture_count":TEXTURE_COUNT==86,
    }

    room_rows=[
        room_manifest_check(room,expected)
        for room,expected in ROOM_EXPECTED.items()
    ]

    canonical_audio=canonical_audio_hashes()
    audio_restore={
        "path":str(AUDIO_RESTORE_EVIDENCE.relative_to(ROOT)),
        "present":AUDIO_RESTORE_EVIDENCE.is_file(),
        "schema_ok":False,
        "version_ok":False,
        "status_ok":False,
        "asset_count":0,
        "exact_asset_set":False,
        "source_hashes_match_canonical":False,
        "runtime_hashes_recorded":False,
        "prepared_pcm_unchanged":False,
        "rows":{},
    }
    if AUDIO_RESTORE_EVIDENCE.is_file():
        try:
            payload=read_json(AUDIO_RESTORE_EVIDENCE)
            rows={
                str(row.get("asset")):row
                for row in payload.get("assets",[])
                if isinstance(row,dict) and row.get("asset")
            }
            audio_restore.update({
                "schema_ok":payload.get("schema")=="openazrael.kg001.audio_restore",
                "version_ok":payload.get("version")==118,
                "status_ok":payload.get("status")=="PASS",
                "asset_count":int(payload.get("asset_count",-1)),
                "exact_asset_set":sorted(rows)==sorted(AUDIO_NAMES),
                "source_hashes_match_canonical":(
                    sorted(canonical_audio)==sorted(AUDIO_NAMES)
                    and all(
                        str(rows.get(name,{}).get("source_sha256",""))
                        == canonical_audio.get(name,"")
                        and str(rows.get(name,{}).get("canonical_source_sha256",""))
                        == canonical_audio.get(name,"")
                        for name in AUDIO_NAMES
                    )
                ),
                "runtime_hashes_recorded":all(
                    len(str(rows.get(name,{}).get("runtime_sha256","")))==64
                    for name in AUDIO_NAMES
                ),
                "prepared_pcm_unchanged":all(
                    rows.get(name,{}).get("pcm_unchanged") is True
                    for name in ("797TAP.WAV","S137.WAV")
                ),
                "rows":rows,
            })
        except Exception as exc:
            audio_restore["error"]=str(exc)
    audio_restore["complete"]=all([
        audio_restore["present"],
        audio_restore["schema_ok"],
        audio_restore["version_ok"],
        audio_restore["status_ok"],
        audio_restore["asset_count"]==len(AUDIO_NAMES),
        audio_restore["exact_asset_set"],
        audio_restore["source_hashes_match_canonical"],
        audio_restore["runtime_hashes_recorded"],
        audio_restore["prepared_pcm_unchanged"],
    ])

    audio_rows=[]
    for name in AUDIO_NAMES:
        path=ROOT/"assets/audio"/name
        row={
            "asset":name,
            "path":str(path.relative_to(ROOT)),
            "present":path.is_file(),
            "nonempty":path.is_file() and path.stat().st_size>0,
            "git_ignored":path.is_file() and ignored(path),
            "wav_valid":False,
            "pcm_non_silent":False,
            "canonical_source_sha256":canonical_audio.get(name,""),
            "restore_source_sha256":str(
                audio_restore.get("rows",{}).get(name,{}).get("source_sha256","")
            ),
            "restore_runtime_sha256":str(
                audio_restore.get("rows",{}).get(name,{}).get("runtime_sha256","")
            ),
            "runtime_sha256":"",
            "source_fingerprint_bound":False,
            "runtime_fingerprint_matches_restore":False,
        }
        if path.is_file():
            row["runtime_sha256"]=sha256(path)
            row["source_fingerprint_bound"]=(
                len(row["canonical_source_sha256"])==64
                and row["restore_source_sha256"]==row["canonical_source_sha256"]
            )
            row["runtime_fingerprint_matches_restore"]=(
                len(row["restore_runtime_sha256"])==64
                and row["runtime_sha256"]==row["restore_runtime_sha256"]
            )
            try:
                summary=wav_pcm_summary(path)
                row["wav"]=summary
                row["wav_valid"]=(
                    summary["compression"]=="NONE"
                    and summary["frames"]>0
                    and summary["channels"]>0
                    and summary["frame_rate"]>0
                    and summary["sample_width"] in (1,2,3,4)
                )
                row["pcm_non_silent"]=summary["peak"]>0
            except Exception as exc:
                row["wav_error"]=str(exc)
        row["complete"]=all([
            row["present"],
            row["nonempty"],
            row["git_ignored"],
            row["wav_valid"],
            row["pcm_non_silent"],
            row["source_fingerprint_bound"],
            row["runtime_fingerprint_matches_restore"],
        ])
        audio_rows.append(row)

    texture_dir=ROOT/"assets/textures/classic"
    pngs=sorted(texture_dir.glob("*.png")) if texture_dir.is_dir() else []
    png_names={path.name for path in pngs}
    texture_rows={
        "directory":str(texture_dir.relative_to(ROOT)),
        "present_count":len(pngs),
        "expected_count":TEXTURE_COUNT,
        "exact_count":len(pngs)==TEXTURE_COUNT,
        "all_nonempty":bool(pngs) and all(path.stat().st_size>0 for path in pngs),
        "all_git_ignored":bool(pngs) and all(ignored(path) for path in pngs),
        "expected_hash_textures":expected_hash,
        "hash_textures_present":sorted(
            name for name in expected_hash if name in png_names
        ),
        "all_hash_textures_present":all(name in png_names for name in expected_hash),
    }
    texture_rows["complete"]=all([
        texture_rows["exact_count"],
        texture_rows["all_nonempty"],
        texture_rows["all_git_ignored"],
        texture_rows["all_hash_textures_present"],
    ])

    restore={
        "path":str(RESTORE_EVIDENCE.relative_to(ROOT)),
        "present":RESTORE_EVIDENCE.is_file(),
        "schema_ok":False,
        "version_ok":False,
        "policy_ok":False,
        "row_count":0,
        "exact_texture_set":False,
        "all_applied":False,
        "all_single_key":False,
        "all_indexed_detection":False,
    }
    if RESTORE_EVIDENCE.is_file():
        try:
            payload=read_json(RESTORE_EVIDENCE)
            rows=payload.get("textures",[])
            by_name={
                str(row.get("texture")):row
                for row in rows if isinstance(row,dict)
            }
            restore.update({
                "schema_ok":payload.get("schema")
                =="openazrael.kg001.legacy_colorkey_restore",
                "version_ok":payload.get("version")==117,
                "policy_ok":payload.get("policy")
                =="EXACTLY_ONE_USED_INDEXED_MAGENTA_KEY_PER_HASH_TEXTURE",
                "row_count":len(rows),
                "exact_texture_set":sorted(by_name)==expected_hash,
                "all_applied":len(by_name)==10 and all(
                    row.get("applied") is True for row in by_name.values()
                ),
                "all_single_key":len(by_name)==10 and all(
                    isinstance(row.get("key_index"),int)
                    and row.get("key_candidates")==[row.get("key_index")]
                    for row in by_name.values()
                ),
                "all_indexed_detection":len(by_name)==10 and all(
                    row.get("detection")=="USED_INDEXED_PALETTE_ENTRY"
                    for row in by_name.values()
                ),
            })
        except Exception as exc:
            restore["error"]=str(exc)
    restore["complete"]=all([
        restore["present"],
        restore["schema_ok"],
        restore["version_ok"],
        restore["policy_ok"],
        restore["row_count"]==10,
        restore["exact_texture_set"],
        restore["all_applied"],
        restore["all_single_key"],
        restore["all_indexed_detection"],
    ])

    local_complete=all(contract_checks.values()) and all(
        row["complete"] for row in room_rows
    ) and bool(audio_restore["complete"]) and all(
        row["complete"] for row in audio_rows
    ) and bool(
        texture_rows["complete"]
    ) and bool(restore["complete"])

    result={
        "schema":"openazrael.kg001.candidate2_asset_set",
        "version":118,
        "status":(
            "PASS"
            if args.require_complete and local_complete
            else "FAIL"
            if args.require_complete
            else "SOURCE_CONTRACT_PASS"
        ),
        "require_complete":args.require_complete,
        "local_asset_status":"COMPLETE" if local_complete else "INCOMPLETE_OR_NOT_RESTORED",
        "contract_checks":contract_checks,
        "rooms":room_rows,
        "audio_restore_evidence":audio_restore,
        "audio":audio_rows,
        "classic_textures":texture_rows,
        "indexed_colorkey_restore":restore,
        "source_safe":True,
        "commercial_asset_bytes_embedded":False,
        "boundary":(
            "SOURCE_CONTRACT_PASS without --require-complete does not claim "
            "local restored assets exist. Fresh-checkout/test-build flow must "
            "use --require-complete."
        ),
    }
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    return 0 if result["status"] in {"PASS","SOURCE_CONTRACT_PASS"} else 1


if __name__=="__main__":
    raise SystemExit(main())
