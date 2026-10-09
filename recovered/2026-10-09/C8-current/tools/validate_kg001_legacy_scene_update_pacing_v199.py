#!/usr/bin/env python3
import argparse, hashlib, json, sys
from pathlib import Path

EXPECTED_R_EXE_SHA256 = "381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00"
EXPECTED_PROFILE = {
    "name": "AZRAEL_DOSBOX_0_74_3_REFERENCE",
    "machine": "svga_s3",
    "frameskip": 0,
    "core": "dynamic",
    "cputype": "auto",
    "cycles": "max limit 280000",
}

def main():
    ap = argparse.ArgumentParser(description="Validate a v199 original-runtime legacy scene-update pacing capture.")
    ap.add_argument("--capture", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    p = Path(a.capture)
    if not p.exists():
        print(json.dumps({"schema":"openazrael.kg001.legacy_scene_update_pacing_validation","version":199,"status":"INCOMPLETE","reason":"CAPTURE_MISSING"}, indent=2))
        return 2
    c = json.loads(p.read_text())
    profile = c.get("profile", {})
    interval = c.get("interval_seconds")
    passes = c.get("eligible_scene_update_passes")
    checks = {
        "original_runtime": c.get("runtime") == "ORIGINAL_R_EXE",
        "r_exe_sha256": c.get("r_exe_sha256") == EXPECTED_R_EXE_SHA256,
        "dosbox_version_recorded": bool(c.get("dosbox_version")),
        "host_recorded": bool(c.get("host")),
        "resolution_mode_recorded": bool(c.get("resolution_mode")),
        "profile_exact": all(profile.get(k) == v for k,v in EXPECTED_PROFILE.items()),
        "interval_positive": isinstance(interval, (int,float)) and not isinstance(interval,bool) and interval > 0,
        "passes_positive": isinstance(passes, int) and not isinstance(passes,bool) and passes > 0,
        "not_claimed_source_authority": c.get("authority") == "REPRODUCIBILITY_REFERENCE_NOT_SOURCE_AUTHORITY",
    }
    failed = [k for k,v in checks.items() if not v]
    status = "PASS" if not failed else "INCOMPLETE"
    rate = (float(passes) / float(interval)) if not failed else None
    out = {
        "schema":"openazrael.kg001.legacy_scene_update_pacing_validation",
        "version":199,
        "status":status,
        "capture_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
        "checks":checks,
        "failed":failed,
        "measurement":{
            "eligible_scene_update_passes":passes,
            "interval_seconds":interval,
            "eligible_passes_per_second":rate,
            "resolution_mode":c.get("resolution_mode"),
        } if rate is not None else None,
        "authority":"REPRODUCIBILITY_REFERENCE_NOT_SOURCE_AUTHORITY",
        "fixed_source_hz_claimed":False,
        "production_clock_binding":"READY_FOR_POLICY_BINDING" if status=="PASS" else "HOLD",
    }
    s=json.dumps(out,indent=2,sort_keys=True)+"\n"
    if a.out: Path(a.out).write_text(s)
    print(s,end="")
    return 0 if status=="PASS" else 2

if __name__=="__main__":
    sys.exit(main())
