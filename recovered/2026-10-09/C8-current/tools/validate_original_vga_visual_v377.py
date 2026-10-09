#!/usr/bin/env python3
"""Validate actual original DOSBox-X VGA captures against source-decoded intro images.

Native DOSBox framebuffer is the reference, not RDC remote desktop.
This verifies five source, original VGA, and real Godot OpenGL framebuffer triples.
Only selected frames, NOT global rendering/animation/wallclock/Well Room fidelity.
"""
from __future__ import annotations
import hashlib,json,os,subprocess,sys
from pathlib import Path
from PIL import Image
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"data/tests/original_vga_visual_contract_v377.json"
CAPTURES=Path(os.environ.get("OPENAZRAEL_ORIGINAL_CAPTURES",
                    "F:/OpenRemaster/captures/OpenAzrael_C8_20261009"))
ORACLE=Path(os.environ.get("OPENAZRAEL_DOSBOXX_ORACLE",
                    "F:/Remaster Framework/work/OpenAzrael/oracle/atdemo_dosboxx_v369"))
DOSBOX=Path(os.environ.get("OPENAZRAEL_DOSBOXX_EXE",
                    "F:/Remaster Framework/tools/third_party/dosbox-x/2026.10.01/unpacked/bin/x64/Release SDL2/dosbox-x.exe"))
ATDEMO=Path(os.environ.get("OPENAZRAEL_CORPUS",
                    "F:/OpenRemaster/sources/materialized/openazrael_demo_atdemo_v1/bf0c87f731bb4e87/layer2/ATDEMO"))

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def strict_rgb_canvas(path:Path,clip:str)->np.ndarray:
    image=Image.open(path).convert("RGB")
    if image.size==(640,480):
        return np.asarray(image,dtype=np.uint8)
    if clip=="TITLE" and image.size==(631,474):
        canvas=Image.new("RGB",(640,480))
        canvas.paste(image,(0,0))
        return np.asarray(canvas,dtype=np.uint8)
    raise ValueError(f"unexpected original frame dimensions {clip} {image.size}: {path}")

def validate()->dict:
    contract=json.loads(CONTRACT.read_text(encoding="utf8"))
    if contract["schema"]!="openazrael.original_vga_visual_contract.v377":
        raise ValueError("unsupported oracle contract")
    for path,digest in ((DOSBOX,contract["dosbox_exe_sha256"]),
                        (ATDEMO/"R.EXE",contract["original_exe_sha256"])):
        if not path.is_file() or sha(path)!=digest:
            raise ValueError("emulator/original corpus missing or hash drift: "+str(path))
    guest=json.loads((ORACLE/"FULL_GUEST_CORPUS_PROVENANCE_V370.json").read_text(encoding="utf8"))
    if guest["source_tree_canonical_sha256"]!=contract["full_source_tree_manifest_sha256"]:
        raise ValueError("full guest source manifest hash drift")
    capture_report=ROOT/contract["godot_capture_report"].replace("res://","")
    godot_report=json.loads(capture_report.read_text(encoding="utf8"))
    if godot_report.get("status")!="PASS" or godot_report.get("failed")!=0:
        raise ValueError("Godot original startup framebuffer capture test did not pass")
    if godot_report.get("display")!="Windows" or len(godot_report.get("captures",[]))<11:
        raise ValueError("Godot capture was not from graphical OpenGL Windows runtime")
    godot_capture_map={row["name"]:row for row in godot_report["captures"]}
    results=[]
    for spec in contract["frames"]:
        original=CAPTURES/contract["original_capture_dir_relative_to_capture_root"]/spec["original"]
        frame=ROOT/"assets/intro_v311"/spec["clip"]/(spec.get("display_file") or f'frame_{spec["index"]:04d}.png')
        if not original.is_file() or sha(original)!=spec["original_sha256"]:
            raise ValueError("missing/tampered original emulator screenshot: "+str(original))
        if not frame.is_file():
            raise ValueError("missing generated clip resource: "+str(frame))
        expected=strict_rgb_canvas(original,spec["clip"])
        reconstructed=strict_rgb_canvas(frame,spec["clip"])
        if not np.array_equal(expected,reconstructed):
            raise ValueError("original vs decoded source framebuffer mismatch: "+str(spec))
        godot_frame_name=spec.get("godot_frame")
        if not isinstance(godot_frame_name,str) or not godot_frame_name.endswith(".png"):
            raise ValueError("missing Godot framebuffer identity in source contract")
        viewport_capture=ROOT/".tmp/intro_decode_v311"/godot_frame_name
        receipt=godot_capture_map.get(viewport_capture.stem)
        if not receipt or not receipt.get("pixel_exact") or receipt.get("source_clip")!=spec["clip"] or receipt.get("source_frame")!=spec["index"]:
            raise ValueError("Godot framebuffer capture receipt missing, wrong clip or not exact")
        if not viewport_capture.is_file():
            raise ValueError("missing Godot graphical framebuffer image: "+str(viewport_capture))
        godot=strict_rgb_canvas(viewport_capture,spec["clip"])
        if not np.array_equal(expected,godot):
            raise ValueError("ORIGINAL_VGA_VS_GODOT_PIXEL_MISMATCH: "+str(viewport_capture))
        if not np.array_equal(reconstructed,godot):
            raise ValueError("SOURCE_DECODER_VS_GODOT_PIXEL_MISMATCH: "+str(viewport_capture))
        if spec["clip"]=="TITLE":
            rawpath=ROOT/"assets/intro_v311/TITLE"/spec["source_raw_file"]
            raw=np.asarray(Image.open(rawpath).convert("RGB"),dtype=np.uint16)
            processed=np.asarray(((raw>>2)<<2)|((raw>>2)>>4),dtype=np.uint8)
            title=np.asarray(Image.open(frame).convert("RGB"),dtype=np.uint8)
            if not np.array_equal(processed,title):
                raise ValueError("TITLE DAC6 conversion policy mismatches original")
        results.append({"clip":spec["clip"],"frame":spec["index"],
            "source_png_sha256":sha(frame),"original_png_sha256":sha(original),
            "godot_frame":godot_frame_name,"godot_png_sha256":sha(viewport_capture),
            "matching_pixels":int(np.all(expected==reconstructed,axis=2).sum()),
            "godot_matching_pixels":int(np.all(expected==godot,axis=2).sum()),
            "total_pixels":640*480,"pixel_exact":True,"godot_pixel_exact":True})
    state=ORACLE/"states"/contract["r1_state"]["source_file"]
    if not state.is_file() or sha(state)!=contract["r1_state"]["sha256"]:
        raise ValueError("independent original R1 savestate missing or changed")
    r1=CAPTURES/contract["r1_state"]["original_reload_png"]
    if not r1.is_file() or sha(r1)!=contract["r1_state"]["original_reload_png_sha256"]:
        raise ValueError("R1 restorable baseline screenshot changed")
    receipt=json.loads((ORACLE/"R1_RELOAD_V374.json").read_text(encoding="utf8"))
    if not receipt.get("savestate_unchanged") or receipt["savestate_sha256_before"]!=sha(state):
        raise ValueError("independent original R1 state restore evidence is not valid")
    video=CAPTURES/contract["r1_video"]["file"]
    if not video.is_file() or sha(video)!=contract["r1_video"]["sha256"]:
        raise ValueError("original gameplay video SHA mismatch")
    probe=subprocess.run(["ffprobe","-v","error","-show_entries",
        "format=duration,size:stream=codec_name,width,height,nb_frames,r_frame_rate",
        "-of","json",str(video)],text=True,capture_output=True,timeout=15)
    if probe.returncode:
        raise ValueError("ffprobe cannot decode original ZMBV AVI: "+probe.stderr[-500:])
    info=json.loads(probe.stdout)
    streams=info["streams"]
    v=next((x for x in streams if x.get("codec_name")=="zmbv"),None)
    a=next((x for x in streams if x.get("codec_name")=="pcm_s16le"),None)
    if not v or not a or (v["width"],v["height"],int(v["nb_frames"]))!=(640,480,579):
        raise ValueError("original gameplay native movie stream contract mismatch")
    result={"schema":"openazrael.c8.original_vga_native_validation.v377",
        "status":"PASS","checks":len(results)*2+5,
        "pixel_exact_source_frames":len(results),"pixel_exact_godot_frames":len(results),
        "total_verified_rgb_pixels":len(results)*640*480,
        "pixel_mismatches":0,"clip_comparisons":results,
        "r1_original_emulator_savestate_verified":True,
        "original_native_gameplay_avi_verified":True,
        "video_codec":"zmbv","video_frames":579,"video_audio_codec":"pcm_s16le",
        "video_duration_seconds":float(info["format"]["duration"]),
        "original_reference_authority":"DOSBOX_X_NATIVE_EMULATED_ORIGINAL_R.EXE",
        "godot_framebuffer_fidelity":"STATIC_FIVE_ORIGINAL_INTRO_FRAMES_PIXEL_EXACT",
        "godot_graphical_capture_checks":godot_report["checks"].__len__(),
        "godot_graphical_capture_count":len(godot_report["captures"]),
        "original_well_room_runtime_fidelity":"HOLD",
        "original_time_dependent_fades_and_intro_audio_sync":"HOLD",
        "fidelity_promotion_allowed":False}
    return result

def main()->int:
    try:
        result=validate()
    except Exception as exc:
        result={"schema":"openazrael.c8.original_vga_native_validation.v377",
                "status":"BLOCKED_OR_FAIL","reason":str(exc),"fidelity_promotion_allowed":False}
    out=ROOT/".tmp/original_vga_validation_v377.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print("OPENAZRAEL_ORIGINAL_VGA_V377 "+json.dumps(result))
    return 0 if result["status"]=="PASS" else 1

if __name__=="__main__":sys.exit(main())